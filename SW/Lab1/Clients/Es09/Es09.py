import paho.mqtt.client as mqtt
import requests
import json
import time
import random
import threading

#TODO: generato da gemini

# Configurazione puntata al tuo Catalogo CherryPy (Es05.py)
CATALOG_BASE_URL = "http://localhost:8080/catalog"
DEVICE_ID = "sensor-01"  # ID del dispositivo richiesto

class MQTTTemperaturePublisher:
    def __init__(self):
        self.device_id = DEVICE_ID
        self.broker_host = None
        self.broker_port = None
        self.pub_interval = 30  # Intervallo di default richiesto (30 secondi)
        self.running = True

        # Configurazione dei topic in linea con le specifiche
        self.base_topic = f"/tiot/g01/{self.device_id}"
        self.pub_topic = f"{self.base_topic}/temperature"
        self.cmd_topic = f"{self.base_topic}/commands"

    def get_broker_from_catalog(self):
        """
        Interroga il catalogo via REST (GET /catalog/broker) 
        per recuperare l'indirizzo e la porta del broker MQTT.
        """
        url = f"{CATALOG_BASE_URL}/broker"
        print(f"[REST] Recupero info broker da: {url}")
        try:
            response = requests.get(url, timeout=5)
            if response.status_code == 200:
                broker_data = response.json()
                # Nel tuo Es05.py i campi nel dizionario predefinito sono 'ip' e 'port'
                self.broker_host = broker_data.get("ip")
                self.broker_port = int(broker_data.get("port", 1883))
                print(f"[REST] Broker individuato nel catalogo: {self.broker_host}:{self.broker_port}")
            else:
                raise Exception(f"Status code {response.status_code}")
        except Exception as e:
            print(f"[REST] Errore di connessione al catalogo ({e}). Uso fallback locale.")
            # Fallback se il catalogo non risponde (usando test.mosquitto.org dato che iot.eclipse.org è spento)
            self.broker_host = "test.mosquitto.org"
            self.broker_port = 1883

    def register_and_keep_alive(self):
        """
        Esegue la prima registrazione (POST) e mantiene il dispositivo attivo 
        inviando periodicamente un ping (PUT) ogni 60 secondi, 
        prima che scatti lo STALE_THRESHOLD (120s) del tuo Catalogo.
        """
        # Creazione del payload rispettando i campi obbligatori del tuo Es05.py
        registration_payload = {
            "id": self.device_id,
            "description": "Sensore di temperatura IoT emulato per Esercizio 09",
            "resources": ["temperature"],
            "mqtt": {
                "ip": self.broker_host,
                "port": self.broker_port,
                "topic": self.pub_topic
            }
        }

        # 1. Prima Registrazione tramite POST
        url_post = f"{CATALOG_BASE_URL}/devices"
        registered = False
        while self.running and not registered:
            try:
                print(f"[REST] Tentativo di registrazione iniziale su {url_post}...")
                response = requests.post(url_post, json=registration_payload, timeout=5)
                if response.status_code in [200, 201]:
                    print(f"[REST] Dispositivo registrato con successo! Risposta: {response.text}")
                    registered = True
                else:
                    print(f"[REST] Errore registrazione ({response.status_code}): {response.text}")
            except Exception as e:
                print(f"[REST] Impossibile raggiungere il catalogo per la POST: {e}")
            
            if not registered:
                time.sleep(5) # Riprova tra 5 secondi se il catalogo è spento

        # 2. Loop di Keep-Alive tramite PUT /catalog/devices/<id>
        url_put = f"{CATALOG_BASE_URL}/devices/{self.device_id}"
        while self.running:
            # Il ciclo di cleanup del tuo Es05 gira ogni 60s, noi inviamo il refresh ogni 60s
            time.sleep(60)
            if not self.running:
                break
            try:
                print(f"[REST] Invio Keep-Alive (PUT) a: {url_put}")
                response = requests.put(url_put, timeout=5)
                if response.status_code == 200:
                    print("[REST] Keep-alive accettato dal catalogo.")
                else:
                    print(f"[REST] Catalogo ha rifiutato la PUT ({response.status_code}): {response.text}")
            except Exception as e:
                print(f"[REST] Errore durante l'invio del Keep-Alive: {e}") 

    def on_connect(self, client, userdata, flags, rc):
        """Callback di connessione MQTT"""
        if rc == 0:
            print(f"[MQTT] Connesso al broker! Iscrizione al topic comandi: {self.cmd_topic}")
            client.subscribe(self.cmd_topic)
        else:
            print(f"[MQTT] Errore di connessione. Codice: {rc}")

    def on_message(self, client, userdata, msg):
        """Callback ricezione comandi MQTT per la configurazione dinamica"""
        try:
            print(f"[MQTT] Ricevuto comando su {msg.topic}: {msg.payload.decode()}")
            payload = json.loads(msg.payload.decode())
            
            # Gestione cambio dinamico dell'intervallo di pubblicazione
            if "pub_interval" in payload:
                new_interval = int(payload["pub_interval"])
                if new_interval > 0:
                    self.pub_interval = new_interval
                    print(f"[CONFIG] Intervallo aggiornato dinamicamente a: {self.pub_interval} secondi")
        except Exception as e:
            print(f"[MQTT] Errore nel parsing del messaggio di comando: {e}")   

    def generate_senml_record(self):
        """Genera payload stringa in formato SenML standard"""
        temperature_val = round(random.uniform(19.5, 24.5), 2)
        senml_payload = [
            {
                "bn": f"{self.device_id}/",
                "t": int(time.time()),
                "n": "temperature",
                "u": "Cel",
                "v": temperature_val
            }
        ]
        return json.dumps(senml_payload)             

    def start(self):
        # Passo 1: Recupera il broker dal Catalogo (GET)
        self.get_broker_from_catalog()
        
        # Passo 2: Avvia il thread per la registrazione e i successivi ping di Keep-Alive (POST/PUT)
        catalog_thread = threading.Thread(target=self.register_and_keep_alive, daemon=True)
        catalog_thread.start()
        
        # Passo 3: Setup del client MQTT Paho
        self.mqtt_client = mqtt.Client()
        self.mqtt_client.on_connect = self.on_connect
        self.mqtt_client.on_message = self.on_message
        
        print(f"[MQTT] Connessione al broker {self.broker_host}:{self.broker_port}...")
        self.mqtt_client.connect(self.broker_host, self.broker_port, 60)
        
        # Avvia il loop di rete in background per non bloccare il loop principale
        self.mqtt_client.loop_start()
        
        # Passo 4: Ciclo di invio dati temporizzato (ogni 30 secondi di default)
        print("[SYSTEM] Avvio ciclo di invio dati SenML...")
        try:
            while self.running:
                payload = self.generate_senml_record()
                print(f"[MQTT] Pubblicazione su {self.pub_topic} -> {payload}")
                self.mqtt_client.publish(self.pub_topic, payload)
                
                # Attesa non bloccante per intercettare subito variazioni di intervallo
                current_interval = self.pub_interval
                for _ in range(current_interval):
                    if not self.running or current_interval != self.pub_interval:
                        break
                    time.sleep(1)
                    
        except KeyboardInterrupt:
            print("\n[SYSTEM] Chiusura del client in corso...")
            self.running = False
            
            # (Opzionale) Rimuove il dispositivo dal catalogo prima di uscire per pulizia immediata
            try:
                print(f"[REST] Invio DELETE al catalogo per rimuovere {self.device_id}...")
                requests.delete(f"{CATALOG_BASE_URL}/devices/{self.device_id}", timeout=3)
            except Exception:
                pass
                
            self.mqtt_client.loop_stop()
            self.mqtt_client.disconnect()
            print("[SYSTEM] Client arrestato correttamente.")   

if __name__ == "__main__":
    node = MQTTTemperaturePublisher()
    node.start()        