import paho.mqtt.client as mqtt
import requests
import json
import time
import random
import threading
from pathlib import Path


class MQTTTemperaturePublisher:
    ## Funzione di inizializzazione del client MQTT per la pubblicazione della temperatura
    def __init__(self):
        self.device_id = "gruppo14_Temp"
        self.broker_host = None
        self.broker_port = None
        self.pub_interval = 30  # Intervallo di default richiesto (30 secondi)
        self.running = True # Flag per controllo del ciclo principale disiscrive quando chiudo e segnala

        # Leggo l'uri del catalog dal file di config
        uri_path = Path(__file__).parent / "config-uri-client.json"
        
        # Recupero l'URL del catalogo dal file di configurazione, con fallback al default se non trovato
        try:
            with open(uri_path, "r") as f:
                config = json.load(f)
            self.CATALOG_BASE_URL = config.get("uri_catalog", "http://localhost:9093/catalog")
            print(f"Catalog URL: {self.CATALOG_BASE_URL}")
        except Exception: #se non trova su config, usa il default:
            self.CATALOG_BASE_URL = "http://localhost:9093/catalog"
            print(f"Impossibile leggere {uri_path}, uso default {self.CATALOG_BASE_URL}")

        # Configurazione dei topic
        self.base_topic = f"/tiot/group14/{self.device_id}"
        self.pub_topic = f"{self.base_topic}/temperature"
        self.cmd_topic = f"{self.base_topic}/commands"

    ## Funzione per ottenere l'host e la porta del broker dal catalogo
    def get_broker_from_catalog(self):
        url = f"{self.CATALOG_BASE_URL}/broker"
        print(f"URL broker: {url}")

        try:
            response = requests.get(url, timeout=5)
            if response.status_code == 200:
                broker_data = response.json()
                self.broker_host = broker_data.get("ip")
                self.broker_port = int(broker_data.get("port", 1883))
                print(f"Broker individuato: {self.broker_host}:{self.broker_port}")
            else:
                raise Exception(f"Status code: {response.status_code}")
        except Exception as e:
            print(f"Errore di connessione al catalogo ({e}).")
            # Fallback se il catalogo non risponde
            self.broker_host = "broker.hivemq.com"
            self.broker_port = 1883

    ## Funzione per registrare il dispositivo e mantenere la connessione attiva con il catalogo
    def register_and_keep_alive(self):
        print("Prima registrazione (POST), mantiene il dispositivo attivo con ping ogni 60 secondi")

        registration_payload = {
            "id": self.device_id,
            "description": "Sensore es09",
            "resources": ["temperature"],
            "mqtt": {
                "ip": self.broker_host,
                "port": self.broker_port,
                "topic": {
                    "sensor_topic": self.pub_topic}
            }
        }

        # Prima Registrazione tramite POST
        url_post = f"{self.CATALOG_BASE_URL}/devices"
        registered = False

        while self.running and not registered:
            try:
                print(f"Tentativo di registrazione iniziale su {url_post}")
                response = requests.post(url_post, json=registration_payload, timeout=5)
                if response.status_code in [200, 201]:
                    print(f"Dispositivo registrato con successo!")
                    registered = True
                else:
                    print(f"Errore registrazione ({response.status_code}): {response.text}")
            except Exception as e:
                print(f" Impossibile raggiungere il catalogo: {e}")
            
            if not registered:
                time.sleep(5) # Riprova tra 5 secondi se il catalogo è spento

        # Loop di Keep-Alive tramite PUT /catalog/devices/<id>
        url_put = f"{self.CATALOG_BASE_URL}/devices/{self.device_id}"
        while self.running:
            # Il ciclo di cleanup del tuo Es05 gira ogni 60s, noi inviamo il refresh ogni 60s
            time.sleep(60)
            if not self.running:
                break
            try:
                print(f"Invio keep-alive  a: {url_put}")
                response = requests.put(url_put, timeout=5)
                if response.status_code == 200:
                    print("Keep-alive accettato dal catalogo")
                else:
                    print(f"Catalogo ha rifiutato la PUT ({response.status_code}): {response.text}")
            except Exception as e:
                print(f"Errore durante l'invio del keep-alive: {e}") 

    def on_connect(self, client, userdata, flags, code, properties=None):
        if code==0:
            print(f"Connesso a {self.device_id}")
            client.subscribe(self.cmd_topic)
        else: 
            print(f"Fallita connessione, codice: {code}")

    def on_message(self, client, userdata, msg):
        try:
            print(f"Ricevuto comando su {msg.topic}: {msg.payload.decode()}")
            payload = json.loads(msg.payload.decode())
            
            # Gestione cambio dinamico dell'intervallo di pubblicazione
            if "pub_interval" in payload:
                new_interval = int(payload["pub_interval"])
                if new_interval > 0:
                    self.pub_interval = new_interval
                    print(f"Intervallo aggiornato a: {self.pub_interval} secondi")
        except Exception as e:
            print(f"Errore: {e}")   

    def generate_senml_record(self):
        #genoro payload SenML
        temperature_val = round(random.uniform(19.5, 24.5), 2)
        senml_payload = {
            "bn": f"{self.device_id}/",
            "bt": int(time.time()),
            "e": [
                {
                    "n": "temperature",
                    "v": temperature_val,
                    "u": "Cel"
                }
            ]
        }
        
        return json.dumps(senml_payload)             

    def start(self):

        self.get_broker_from_catalog()
        
        catalog_thread = threading.Thread(target=self.register_and_keep_alive, daemon=True)#avvio thread
        catalog_thread.start()
        
        #configuro client MQTT Paho
        self.mqtt_client = mqtt.Client()
        self.mqtt_client.on_connect = self.on_connect
        self.mqtt_client.on_message = self.on_message
        
        print(f"Connessione al broker {self.broker_host}:{self.broker_port}...")
        self.mqtt_client.connect(self.broker_host, self.broker_port, 60)
        
        self.mqtt_client.loop_start()#in background per non bloccare principale
        
        print("Avvio ciclo di invio dati") #temporizzato 30 sec
        try:
            while self.running:
                payload = self.generate_senml_record()
                print(f"Pubblicazione su {self.pub_topic}")
                self.mqtt_client.publish(self.pub_topic, payload)
                
                current_interval = self.pub_interval
                for _ in range(current_interval):#ciclo di attesa non bloccante
                    if not self.running or current_interval != self.pub_interval:
                        break
                    time.sleep(1)
                    
        except KeyboardInterrupt:
            print("\nInizio chiusura del client")
            self.running = False
            
            try:
                url_delete = f"{self.CATALOG_BASE_URL}/devices/{self.device_id}"
                print(f"Rimuovo  {self.device_id} - {url_delete} dal catalog")  
                requests.delete(url_delete, timeout=3)  
            except Exception:
                print("Disopositivo non rimosso correttamente")
                
            self.mqtt_client.loop_stop()
            self.mqtt_client.disconnect()
            print("Client arrestato")   

if __name__ == "__main__":
    node = MQTTTemperaturePublisher()
    node.start()        