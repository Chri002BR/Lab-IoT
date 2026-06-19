import json
import time
import threading
import requests
import paho.mqtt.client as mqtt
from pathlib import Path

# Configurazione Broker MQTT e Costanti
BROKER_MQTT = "broker.hivemq.com"
PORTA_MQTT = 1883
ID_SERVIZIO = "smart-home-event-log-service"


class MQTT_log_service:
    def __init__(self):
        # Inizializzazione del client MQTT (versione 2)
        self.client = mqtt.Client(callback_api_version=mqtt.CallbackAPIVersion.VERSION2, client_id=ID_SERVIZIO)
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        self.stop_event = threading.Event()

        # Set per tracciare i topic a cui siamo già iscritti
        self.subscribed_topics = set()

        # Lettura dell'URL del catalogo dal file di configurazione
        uri_path = Path(__file__).parent / "config-uri-client.json"
        try:
            with open(uri_path, "r") as f:
                config = json.load(f)
            self.CATALOG_BASE_URL = config.get("uri_catalog", "http://localhost:9093/catalog")
            self.URL_LOG_SERVICE = config.get("uri_log_REST", "http://127.0.0.1:9092/log")
        except FileNotFoundError:
            self.CATALOG_BASE_URL = "http://localhost:9093/catalog"
            self.URL_LOG_SERVICE = "http://127.0.0.1:9092/log"

        # Avvio del thread per l'aggiornamento periodico dei topic
        self.update_thread = threading.Thread(target=self.periodic_topic_update, daemon=True)
        self.update_thread.start()

        print("[SISTEMA] Avvio del servizio MQTT in corso...")
        self.client.connect(BROKER_MQTT, PORTA_MQTT, 60)
        self.client.loop_start()

    def on_connect(self, client, userdata, flags, reason_code, properties):
        """Callback eseguita al momento della connessione al broker MQTT."""
        if reason_code == 0:
            print(f"\n[MQTT] Connesso con successo al broker {BROKER_MQTT}.")
            # Effettua l'iscrizione ai topic nel catalog
            self.fetch_and_subscribe_topics()
        else:
            print(f"\n[MQTT - ERRORE] Connessione fallita. Codice: {reason_code}")

    def on_message(self, client, userdata, msg):
        """Callback eseguita alla ricezione di un messaggio sui topic sottoscritti."""
        try:
            payload_str = msg.payload.decode("utf-8")
            print(f"\n[LOG] Ricevuto messaggio MQTT su {msg.topic}: {payload_str}")
            
            # 1. Parso la stringa per assicurarmi che sia un JSON valido
            try:
                payload_json = json.loads(payload_str)
            except json.JSONDecodeError:
                print("[LOG - ERRORE] Il messaggio non è un JSON valido. Impossibile inoltrare a Es04.")
                return

            # 2. Inoltro il pacchetto JSON tramite POST a Es04.py
            try:
                response = requests.post(self.URL_LOG_SERVICE, json=payload_json, timeout=5)
                
                if response.status_code == 200:
                    resp_data = response.json()
                    print(f"[REST] Log inoltrato e salvato correttamente (ID assegnato: {resp_data.get('log_id')})")
                else:
                    print(f"[REST - WARNING] Errore dal server Es04. Codice: {response.status_code}")
                    print(f"       Dettaglio: {response.text}")
                    
            except requests.exceptions.RequestException as req_err:
                print(f"[REST - ERRORE] Impossibile contattare il servizio di Log (Es04) all'indirizzo {self.URL_LOG_SERVICE}: {req_err}")

        except Exception as e:
            print(f"[LOG - ERRORE] Errore imprevisto durante l'elaborazione: {e}")

    # Funzione per prendere i topic dal catalog alla quale iscriversi       
    def fetch_and_subscribe_topics(self):
        """Interroga il catalogo per ottenere i dispositivi e si iscrive ai nuovi topic."""
        try:
            # Faccio una GET al catalogo. 
            # (Se il tuo catalogo richiede di specificare l'endpoint, ad es. '/devices', aggiungilo all'URL)
            response = requests.get(self.CATALOG_BASE_URL, timeout=5)
            
            if response.status_code == 200:
                catalog_data = response.json()
                
                # Estraiamo la lista dei dispositivi
                devices = catalog_data.get("devices", [])
                
                # Raccogliamo tutti i sensor_topic trovati in questo momento
                current_catalog_topics = set()
                
                for device in devices:
                    # Estraiamo la lista (o il dizionario) dei dispositivi
                    devices = catalog_data.get("devices", [])
                    
                    # Se il catalogo restituisce un dizionario invece di una lista, prendiamo solo i valori
                    if isinstance(devices, dict):
                        devices = devices.values()
                    
                    # Raccogliamo tutti i sensor_topic trovati in questo momento
                    current_catalog_topics = set()
                    
                    for device in devices:
                        # Controllo di sicurezza: ignoriamo l'elemento se non è un dizionario (es. se è una stringa)
                        if not isinstance(device, dict):
                            continue

                    # Navighiamo in modo sicuro il dizionario (evita crash se mancano campi)
                    mqtt_info = device.get("mqtt", {})
                    topic_info = mqtt_info.get("topic", {})
                    sensor_topic = topic_info.get("sensor_topic")
                    
                    if sensor_topic:
                        current_catalog_topics.add(sensor_topic)
                
                # Controlliamo quali topic sono nuovi rispetto a quelli già iscritti
                new_topics = current_catalog_topics - self.subscribed_topics
                
                for topic in new_topics:
                    self.client.subscribe(topic)
                    self.subscribed_topics.add(topic)
                    print(f"[MQTT] Nuova sottoscrizione effettuata dinamicamente al topic: {topic}")
            else:
                print(f"[CATALOG - WARNING] Errore durante il recupero dei topic. Codice: {response.status_code}")
                
        except requests.exceptions.RequestException as req_err:
            print(f"[CATALOG - ERRORE] Impossibile contattare il catalogo all'indirizzo {self.CATALOG_BASE_URL}: {req_err}")
        except Exception as e:
            print(f"[CATALOG - ERRORE] Errore imprevisto durante l'estrazione dei topic: {e}")

    # Aggiornamento periodico dei topic dal catalog
    def periodic_topic_update(self):
        """Thread in background che aggiorna i topic ogni 60 secondi."""
        while not self.stop_event.is_set():
            # Aspetta 60 secondi prima di ri-controllare (si sblocca subito se viene chiamato stop())
            self.stop_event.wait(60)
            if not self.stop_event.is_set():
                self.fetch_and_subscribe_topics()



    def stop(self):
        """Arresta in modo pulito il servizio."""
        print("\n[SISTEMA] Arresto del servizio in corso...")
        self.stop_event.set()
        self.client.loop_stop()
        self.client.disconnect()
