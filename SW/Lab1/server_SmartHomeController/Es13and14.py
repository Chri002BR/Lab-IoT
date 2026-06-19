import paho.mqtt.client as mqtt
import json
import time
import requests
import threading
from pathlib import Path

CATALOG_REST_URL = "http://localhost:9093"
GROUP_ID = "group14"
SERVICE_ID = "smart_home_controller"
MQTT_BROKER = "broker.hivemq.com"
MQTT_PORT = 1883

#standard thresholds
FAN_LOWER_THRESHOLD_OCCUPIED_STANDARD=25.0
FAN_HIGHER_THRESHOLD_OCCUPIED_STANDARD=30.0
LED_LOWER_THRESHOLD_OCCUPIED_STANDARD=15.0
LED_HIGHER_THRESHOLD_OCCUPIED_STANDARD=20.0
FAN_LOWER_THRESHOLD_NOT_OCCUPIED_STANDARD=30.0
FAN_HIGHER_THRESHOLD_NOT_OCCUPIED_STANDARD=35.0
LED_LOWER_THRESHOLD_NOT_OCCUPIED_STANDARD=10.0
LED_HIGHER_THRESHOLD_NOT_OCCUPIED_STANDARD=15.0
ALERT_TEMPERATURE_THRESHOLD_STANDARD=26.0

#timeout for pir
PIR_TIMEOUT=1800.0
#timeout for mic
MIC_TIMEOUT=3600.0

class SmartHomeController:

    def __init__(self):
        
        self.Client = mqtt.Client(callback_api_version=mqtt.CallbackAPIVersion.VERSION2, client_id=SERVICE_ID)
        self.Client.on_connect=self.connect
        self.Client.on_message=self.message

        self.temperature_history=[]
        self.current_motion=False
        self.motion_timer=None
        self.current_voice=False
        self.voice_timer=None
        self.current_fan_state=0
        self.current_led_state=0
        self.dispositivi_scoperti={}
        self.command_topic=None
        self.timer_lock = threading.Lock()

        # Leggo l'uri del catalog dal file di config
        uri_path = Path(__file__).parent / "config-uri-server.json"
        
        # Recupero l'URL del catalogo dal file di configurazione, con fallback al default se non trovato
        try:
            with open(uri_path, "r") as f:
                config = json.load(f)
            self.CATALOG_REST_URL = config.get("uri_catalog", "http://localhost:9093/catalog")
            print(f"Catalog URL: {self.CATALOG_REST_URL}")
        except Exception: #se non trova su config, usa il default:
            self.CATALOG_REST_URL = "http://localhost:9093/catalog"
            print(f"Impossibile leggere {uri_path}, uso default {self.CATALOG_REST_URL}")

        #thresholds definitions
        self.fan_lower_occupied=FAN_LOWER_THRESHOLD_OCCUPIED_STANDARD
        self.fan_higher_occupied=FAN_HIGHER_THRESHOLD_OCCUPIED_STANDARD
        self.led_lower_occupied=LED_LOWER_THRESHOLD_OCCUPIED_STANDARD
        self.led_higher_occupied=LED_HIGHER_THRESHOLD_OCCUPIED_STANDARD
        self.fan_lower_not_occupied=FAN_LOWER_THRESHOLD_NOT_OCCUPIED_STANDARD
        self.fan_higher_not_occupied=FAN_HIGHER_THRESHOLD_NOT_OCCUPIED_STANDARD
        self.led_lower_not_occupied=LED_LOWER_THRESHOLD_NOT_OCCUPIED_STANDARD
        self.led_higher_not_occupied=LED_HIGHER_THRESHOLD_NOT_OCCUPIED_STANDARD
        self.alert_temperature_threshold=ALERT_TEMPERATURE_THRESHOLD_STANDARD

    def connect(self, client, userdata, flags, code, properties=None):

        if code == 0:
            print("Connected successfully to MQTT Broker")
        else:
            print(f"Connection failed with code {code}")
    
    def message(self, client, userdata, msg):

        body = json.loads(msg.payload.decode("utf-8"))

        topic=msg.topic.split("/") #tiot/groupXX/<type>

        sensor_type=body["e"][0]["n"]

        value=body["e"][0]["v"]

        if sensor_type=="temp":

            self.temperature_stat(float(value)) #calls actions

        elif sensor_type=="pir":
            with self.timer_lock:
                if float(value)==1.0:

                    self.current_motion=True
                    print("\nMotion detected")

                    if self.motion_timer is not None:
                        self.motion_timer.cancel()

                    self.motion_timer=threading.Timer(PIR_TIMEOUT, self.no_movement)
                    self.motion_timer.start()
                    
            self.actions()

        elif sensor_type=="mic":

            with self.timer_lock:
                if float(value)==1.0:

                    self.current_voice=True
                    print("\nVoice Detected")

                    if self.voice_timer is not None:
                        self.voice_timer.cancel()

                    self.voice_timer=threading.Timer(MIC_TIMEOUT, self.no_voice)
                    self.voice_timer.start()

            self.actions()

    def temperature_stat(self, value):

        if len(self.temperature_history)>=10:

            self.temperature_history.pop(0)

        self.temperature_history.append(value)

        #statistics
        min_temp=min(self.temperature_history)
        max_temp=max(self.temperature_history)
        avg_temp=sum(self.temperature_history)/len(self.temperature_history)

        print(f"\nStatistics: min={min_temp}, max={max_temp}, avg={avg_temp}")

        #alert
        if value>=self.alert_temperature_threshold:

            body={
                    "bn": f"/tiot/{GROUP_ID}/smart_home_controller/",
                    "t": time.time(),
                    "e": [
                        {"n": "alert", "v": "CRITICAL_TEMPERATURE_EXCEEDED", "u": "text"},
                        {"n": "current_value", "v": value, "u": "Cel"},
                        {"n": "threshold", "v": self.alert_temperature_threshold, "u": "Cel"}
                    ]
                }
            topic=f"/tiot/{GROUP_ID}/alert"

            self.Client.publish(topic, json.dumps(body))
            print(f"\nAlert message sent on {topic}")

        self.actions()

    def actions(self):

        if not self.command_topic:
            return

        #control for first pir message
        if not self.temperature_history:

            print("\nNo temperature value recieved yet")
            return

        led=0.0
        fan=0.0
        current_temperature=self.temperature_history[-1]

        if self.current_motion or self.current_voice:

            if current_temperature<self.led_lower_occupied:

                #switch on led at maximum
                self.switch_on_led(self.led_lower_occupied, self.led_lower_occupied, self.led_higher_occupied)
                self.switch_off_fan()

            elif current_temperature>=self.led_lower_occupied and current_temperature<=self.led_higher_occupied:

                self.switch_on_led(current_temperature, self.led_lower_occupied, self.led_higher_occupied)
                self.switch_off_fan()
            
            elif current_temperature>self.led_higher_occupied and current_temperature<self.fan_lower_occupied:

                self.switch_off_fan()
                self.switch_off_led()

            elif current_temperature>=self.fan_lower_occupied and current_temperature<=self.fan_higher_occupied:
                
                self.switch_on_fan(current_temperature, self.fan_lower_occupied, self.fan_higher_occupied)
                self.switch_off_led()

            elif current_temperature>self.fan_higher_occupied:

                #switch on fan at maximum
                self.switch_on_fan(self.fan_higher_occupied, self.fan_lower_occupied, self.fan_higher_occupied)
                self.switch_off_led()

        else:

            if current_temperature<self.led_lower_not_occupied:

                #switch on led at maximum
                self.switch_on_led(self.led_lower_not_occupied, self.led_lower_not_occupied, self.led_higher_not_occupied)
                self. switch_off_fan()

            elif current_temperature>=self.led_lower_not_occupied and current_temperature<=self.led_higher_not_occupied:

                self.switch_on_led(current_temperature, self.led_lower_not_occupied, self.led_higher_not_occupied)
                self.switch_off_fan()

            elif current_temperature>self.led_higher_not_occupied and current_temperature<self.fan_lower_not_occupied:

                self.switch_off_fan()
                self.switch_off_led()

            elif current_temperature>=self.fan_lower_not_occupied and current_temperature<=self.fan_higher_not_occupied:
                
                self.switch_on_fan(current_temperature, self.fan_lower_not_occupied, self.fan_higher_not_occupied)
                self.switch_off_led()

            elif current_temperature>self.fan_higher_not_occupied:

                #switch on fan at maximum
                self.switch_on_fan(self.fan_higher_not_occupied, self.fan_lower_not_occupied, self.fan_higher_not_occupied)
                self.switch_off_led()

    def rest_registration(self):

        uri=f"{CATALOG_REST_URL}/catalog/services"

        topic=f"/tiot/{GROUP_ID}"

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

        time.sleep(1)
        self.update_devices_to_catalog()

        #starts the threshold setting menu
        menu_thread=threading.Thread(target=self.menu_set_temperature, daemon=True)
        menu_thread.start()

        lcd_thread = threading.Thread(target=self.lcd_messages, daemon=True)
        lcd_thread.start()

        try:
            while True:

                time.sleep(60)
                self.send_rest_keep_alive()
                self.update_devices_to_catalog()
        except KeyboardInterrupt:
            
            self.Client.loop_stop()


    def menu_set_temperature(self):

        while True:

            print("\nTemperature thresholds menu:")
            print("\nChoose the threshold to change")
            print(f"1) Fan lower threshold (room occupied) (current={self.fan_lower_occupied})")
            print(f"2) Fan higher threshold (room occupied) (current={self.fan_higher_occupied})")
            print(f"3) LED lower threshold (room occupied) (current={self.led_lower_occupied})")
            print(f"4) LED higher threshold (room occupied) (current={self.led_higher_occupied})")
            print(f"5) Fan lower threshold (room not occupied) (current={self.fan_lower_not_occupied})")
            print(f"6) Fan higher threshold (room not occupied) (current={self.fan_higher_not_occupied})")
            print(f"7) LED lower threshold (room not occupied) (current={self.led_lower_not_occupied})")
            print(f"8) LED higher threshold (room not occupied) (current={self.led_higher_not_occupied})")
            print(f"9) Alert temperature threshold (only if room occupied) (current={self.alert_temperature_threshold})")

            strchoice=input()

            try:
                choice=int(strchoice)

            except ValueError:
                print("\nInvalid value")
                continue

            if choice not in (1, 2, 3, 4, 5, 6, 7, 8, 9):

                print("\nInvalid choice")
                continue

            strtemp=input("\nSet new temperature threshold: ")

            try:
                temp=float(strtemp)

            except ValueError:
                print("\nInvalid value")
                continue

            if choice==1:
                self.fan_lower_occupied=temp

            elif choice==2:
                self.fan_higher_occupied=temp

            elif choice==3:
                self.led_lower_occupied=temp

            elif choice==4:
                self.led_higher_occupied=temp

            elif choice==5:
                self.fan_lower_not_occupied=temp

            elif choice==6:
                self.fan_higher_not_occupied=temp

            elif choice==7:
                self.led_lower_not_occupied=temp

            elif choice==8:
                self.led_higher_not_occupied=temp

            elif choice==9:
                self.alert_temperature_threshold=temp

    def switch_off_led(self):

        self.current_led_state=0

        body={
                "e": [{
                        "n": "led",
                        "v": self.current_led_state
                        }
                        ]}

        self.Client.publish(self.command_topic, json.dumps(body))
        print(f"\nLed command sent on {self.command_topic}")

    def switch_off_fan(self):

        self.current_fan_state=0

        body={
                "e": [{
                        "n": "fan",
                        "v": self.current_fan_state
                        }
                        ]}

        self.Client.publish(self.command_topic, json.dumps(body))
        print(f"\nFan command sent on {self.command_topic}")

    def switch_on_led(self, current, lower, higher):

        temperature_span=higher-lower
        if temperature_span==0:
            temperature_span=1.0
        purified_temp=higher-current
        self.current_led_state=(purified_temp*255)/temperature_span

        body={
                "e": [{
                        "n": "led",
                        "v": self.current_led_state
                        }
                        ]}

        self.Client.publish(self.command_topic, json.dumps(body))
        print(f"\nLed command sent on {self.command_topic}")

    def switch_on_fan(self, current, lower, higher):


        temperature_span=higher-lower
        if temperature_span==0:
            temperature_span=1.0
        purified_temp=current-lower
        self.current_fan_state=(purified_temp*255)/temperature_span

        body={
                "e": [{
                        "n": "fan",
                        "v": self.current_fan_state
                        }
                        ]}

        self.Client.publish(self.command_topic, json.dumps(body))
        print(f"\nFan command sent on {self.command_topic}")

    def no_movement(self):

        with self.timer_lock:
            self.current_motion=False
            self.motion_timer=None
            print("\nMovement timeout")
        self.actions()

    def no_voice(self):

        with self.timer_lock:
            self.current_voice=False
            self.voice_timer=None
            print("\nVoice timeout")
        self.actions()

    def lcd_messages(self):

        time.sleep(2)

        while True:

            if not self.command_topic:
                time.sleep(2)
                continue

            #setting parameters
            if not self.temperature_history:
                current_temperature=0.0
            else:
                current_temperature=self.temperature_history[-1]

            if self.current_motion or self.current_voice:
                pres=1
                acm=self.fan_lower_occupied
                acM=self.fan_higher_occupied
                htm=self.led_lower_occupied
                htM=self.led_higher_occupied

            else:
                pres=0
                acm=self.fan_lower_not_occupied
                acM=self.fan_higher_not_occupied
                htm=self.led_lower_not_occupied
                htM=self.led_higher_not_occupied


            ac=(self.current_fan_state*100)/255
            ht=(self.current_led_state*100)/255

            body={
                "e": [{
                    "n": "lcd", 
                    "v": [f"T:{current_temperature:.2f} Pres:{pres}", f"AC:{ac:.2f}% HT: {ht:.2f}%"]
                    }]
                    }
            self.Client.publish(self.command_topic, json.dumps(body))
            print(f"\nFirst monitor sent on {self.command_topic}")

            time.sleep(5)

            body={
                "e": [{
                    "n": "lcd", 
                    "v": [f"AC: m:{acm:.2f} M:{acM:.2f}", f"HT: m:{htm:.2f} M:{htM:.2f}"]
                    }]
                    }
            self.Client.publish(self.command_topic, json.dumps(body))
            print(f"\nSecond monitor sent on {self.command_topic}")

            time.sleep(5)

    def update_devices_to_catalog(self):
        try:
            uri = f"{self.CATALOG_REST_URL}/devices"  # Se hai seguito il consiglio precedente, usa self.CATALOG_REST_URL
            response = requests.get(uri, timeout=5)
            
            if response.status_code == 200:
                dispositivi = response.json()
                
                for dev in dispositivi:
                    mqtt_info = dev.get("mqtt", {})
                    topic_data = mqtt_info.get("topic", {})
                    
                    sensor_topic = topic_data.get("sensor_topic")
                    cmd_topic = topic_data.get("command_topic")
                    
                    if cmd_topic:
                        self.command_topic = cmd_topic

                    if sensor_topic and sensor_topic not in self.dispositivi_scoperti:
                        self.Client.subscribe(sensor_topic)
                        self.dispositivi_scoperti[sensor_topic] = True 
                        print(f"Nuovo dispositivo scoperto! Iscritto a: {sensor_topic}")
            else:
                print(f"\nErrore aggiornamento dispositivi dal catalogo: {response.status_code}")
                        
        except Exception as e:
            print(f"\nCouldn't update devices from catalog: {e}")