import paho.mqtt.client as mqtt
import json
import time
import requests

CATALOG_REST_URL = "http://localhost:9093"
GROUP_ID = "group14"
SERVICE_ID = "smart_home_controller"
MQTT_BROKER = "broker.hivemq.com"
MQTT_PORT = 1883

STANDARD_TEMPERATURE_THRESHOLD=26

class SmartHomeController:

    def __init__(self):
        
        self.Client = mqtt.Client(callback_api_version=mqtt.CallbackAPIVersion.VERSION2, client_id=SERVICE_ID)
        self.Client.on_connect=self.connect
        self.Client.on_message=self.message

        self.temperature_history={}
        self.current_motion={}

    def connect(self, client, userdata, flags, code, properties=None):

        if code==0:

            print(f"Connected")
            sensor_topic_filter = f"tiot/{GROUP_ID}/+/sensor/+"
            self.Client.subscribe(sensor_topic_filter)

        else: 

            print(f"Connection failed with code {code}")
    
    def message(self, client, userdata, msg):

        body = json.loads(msg.payload.decode("utf-8"))

        topic=msg.topic.split("/") #tiot/groupXX/<room>/sensor/<type>

        room=topic[2]
        sensor_type=topic[4]

        value=body.get("value")

        if sensor_type=="temperature":

            self.temperature_stat(room, float(value))

        elif sensor_type=="motion":

            self.current_motion[room]=bool(value)

            self.actions(room)

    def temperature_stat(self, room, value):
        
        if room not in self.temperature_history:

            self.temperature_history[room]=[]

        past_temperatures=self.temperature_history[room]

        if len(past_temperatures)>=10:

            past_temperatures.pop(0)

        past_temperatures.append(value)

        #statistics
        min_temp=min(past_temperatures)
        max_temp=max(past_temperatures)
        avg_temp=sum(past_temperatures)/len(past_temperatures)

        print(f"\nStatistics room={room}: min={min_temp}, max={max_temp}, avg={avg_temp}")

        current_threshold=self.get_threshold_from_actuator_service(room)

        if value>=current_threshold:

            body={
                "alert": "CRITICAL_TEMPERATURE_EXCEEDED",
                "current_value": value,
                "threshold": current_threshold,
                "timestamp": time.time()
            }
            topic=f"tiot/{GROUP_ID}/{room}/alert"

            self.Client.publish(topic, json.dumps(body))
            print(f"\nAlert message sent on {topic}")

        self.actions(room)

    def actions(self, room):

        motion = self.current_motion.get(room, False)

        if room not in self.temperature_history:

            print("\nError: Room not present")
            return

        temperature=self.temperature_history[room][-1]
        current_threshold = self.get_threshold_from_actuator_service(room)

        led="OFF"

        if motion:
            if temperature>=current_threshold:

                led="OFF"

            else:

                led="ON"
        
        topic=f"tiot/{GROUP_ID}/{room}/actuator/led"
        body={
            "command": led,
            "timestamp": time.time()
        }

        self.Client.publish(topic, json.dumps(body))
        print(f"\nLed command sent on {topic}")

    def rest_registration(self):

        uri=f"{CATALOG_REST_URL}/catalog/services"

        topic=f"tiot/{GROUP_ID}"

        body={
            "id": SERVICE_ID,
            "description": "Central Smart Home Controller for Rules and Stats",
            "resources": ["temperature_controller", "statistics"],
            "mqtt": {
                "ip": MQTT_BROKER,
                "port": MQTT_PORT,
                "base_topic": topic
            }
        }

        try:
            response = requests.post(uri, json=body, timeout=5)
            if response.status_code in [200, 201]:
                print(f"\nRegistered, response: {response.text}")
                return True
            else:
                print(f"\nRegistration Error. Status code: {response.status_code}")
                return False
        except requests.exceptions.RequestException as e:
            print(f"\nConnection Error: {e}")
            return False

    def send_rest_keep_alive(self):
        url = f"{CATALOG_REST_URL}/catalog/services/{SERVICE_ID}"
        try:
            response = requests.put(url, timeout=5)
            if response.status_code == 200:
                print("\nKeep alive sent")
        except requests.exceptions.RequestException as e:
            print(f"\nKeep alive not sent: {e}")

    def run(self):

        if not self.rest_registration():

            print("\nError: Impossible to proceed further")
            return
        
        self.Client._connect_timeout = 20.0
        self.Client.connect(MQTT_BROKER, MQTT_PORT, 60)
        self.Client.loop_start()

        try:
            while True:

                time.sleep(60)
                self.send_rest_keep_alive()
        except KeyboardInterrupt:
            
            self.Client.loop_stop()

    #temperature threshold definition
    def get_actuator_service_url(self):

        uri = f"{CATALOG_REST_URL}/catalog/services/actuator_service"

        try:
            response = requests.get(uri, timeout=5)

            if response.status_code == 200:

                data = response.json()
                return data.get("url", "http://127.0.0.1:9091") 
            
        except Exception as e:

            print("\nError: Could not get the url")

        return "http://127.0.0.1:9091"
    
    #asks the SmartHomeActuatorService for the threshold
    def get_threshold_from_actuator_service(self, room):

        base_url = self.get_actuator_service_url()
        
        url = f"{base_url}/actuators/{room}/thermostat"
        
        try:

            response = requests.get(url, timeout=5)

            if response.status_code == 200:

                senml_packet = response.json()
                events = senml_packet.get("e", [])

                for e in events:
                    if e.get("n") == "thermostat":

                        return float(e.get("v"))
                        
        except Exception as e:
            print(f"\nError: {e}")
            
        return STANDARD_TEMPERATURE_THRESHOLD
