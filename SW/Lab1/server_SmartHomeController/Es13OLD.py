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

#stat(?)

STANDARD_TEMPERATURE_THRESHOLD=26

#standard thresholds

FAN_LOWER_THRESHOLD_OCCUPIED_STANDARD=25
FAN_HIGHER_THRESHOLD_OCCUPIED_STANDARD=30
LED_LOWER_THRESHOLD_OCCUPIED_STANDARD=15
LED_HIGHER_THRESHOLD_OCCUPIED_STANDARD=20
FAN_LOWER_THRESHOLD_NOT_OCCUPIED_STANDARD=30
FAN_HIGHER_THRESHOLD_NOT_OCCUPIED_STANDARD=35
LED_LOWER_THRESHOLD_NOT_OCCUPIED_STANDARD=10
LED_HIGHER_THRESHOLD_NOT_OCCUPIED_STANDARD=15

class SmartHomeController:

    def __init__(self):
        
        self.Client = mqtt.Client(callback_api_version=mqtt.CallbackAPIVersion.VERSION2, client_id=SERVICE_ID)
        self.Client.on_connect=self.connect
        self.Client.on_message=self.message

        self.temperature_history=[]
        self.current_motion=False
        self.dispositivi_scoperti={}

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

        #TODO: remove this
        #default threshold
        self.temperature_threshold=STANDARD_TEMPERATURE_THRESHOLD

    def connect(self, client, userdata, flags, code, properties=None):

        if code==0:
            print(f"Connected")

            # Iscrizione ai topic dei dispositivi scoperti
            try:
                url = f"{self.CATALOG_REST_URL}/devices"
                response = requests.get(url, timeout=5)
            
                if response.status_code == 200:
                    dispositivi = response.json() 
                    self.dispositivi_scoperti.clear()
                    for dev in dispositivi:
                        # Adattamento per la struttura del tuo catalogo: i topic sono dentro l'oggetto "mqtt"
                        mqtt_info = dev.get("mqtt", {})
                        topic_data = mqtt_info.get("topic", {})
                        
                        # Gestione flessibile: controlla se 'topic' è un dizionario o una stringa diretta
                        actual_topic = None
                        if isinstance(topic_data, dict):
                            actual_topic = topic_data.get("sensor_topic")
                        elif isinstance(topic_data, str):
                            actual_topic = topic_data
                        
                        # Se abbiamo trovato un topic valido, ci iscriviamo
                        if actual_topic:
                            self.Client.subscribe(actual_topic)
                            print(f"Iscritto con successo a: {actual_topic}")
                        else:
                            print(f"Dispositivo {dev.get('id')} trovato ma senza un topic valido.")
                else:
                    print(f"Errore di risposta dal catalogo: {response.status_code}")
                
            except Exception as e:
                print(f"Errore di connessione al catalogo: {e}")

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

            if float(value)==1.0:

                self.current_motion=True

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
        if value>=self.temperature_threshold:

            body={
                "alert": "CRITICAL_TEMPERATURE_EXCEEDED",
                "current_value": value,
                "threshold": self.temperature_threshold,
                "timestamp": time.time()
            }
            topic=f"/tiot/{GROUP_ID}/alert"

            self.Client.publish(topic, json.dumps(body))
            print(f"\nAlert message sent on {topic}")

        self.actions()

    def actions(self):

        if not self.temperature_history:

            print("\nNo temperature value recieved yet")
            return

        led=0

        if self.current_motion:
            if self.temperature_history[-1]>=self.temperature_threshold:

                led=0

            else:

                led=255
        
        topic=f"/tiot/{GROUP_ID}/command_topic"
        body={
            "e": [{
                    "n": "led",
                    "v": led
                      }
                      ]}

        self.Client.publish(topic, json.dumps(body))
        print(f"\nLed command sent on {topic}")

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

        #starts the threshold setting menu
        menu_thread=threading.Thread(target=self.menu_set_temperature, daemon=True)
        menu_thread.start()

        try:
            while True:

                time.sleep(60)
                self.send_rest_keep_alive()
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
            strchoice=input()

            try:
                choice=int(strchoice)

            except ValueError:
                print("\nInvalid value")
                continue

            if choice not in (1, 2, 3, 4, 5, 6, 7, 8):

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


