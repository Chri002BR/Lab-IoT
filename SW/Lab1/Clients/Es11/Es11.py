import json
import time
import threading
import requests
import paho.mqtt.client as mqtt
from pathlib import Path

# Configurazione Broker MQTT
BROKER_MQTT = "broker.hivemq.com"  
PORTA_MQTT = 1883
ID_DISPOSITIVO = "MQTT_Command_Publisher_TeamX"

class ActuatorPublisher:
    def __init__(self):
        self.client = mqtt.Client(callback_api_version=mqtt.CallbackAPIVersion.VERSION2, client_id=ID_DISPOSITIVO)
        self.dispositivi_scoperti = {}
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        self.running = True

        uri_path = Path(__file__).parent / "config-uri-client.json"
        try:
            with open(uri_path, "r") as f:
                config = json.load(f)
            self.CATALOG_BASE_URL = config.get("url_catalog", "http://localhost:9093/catalog")
        except FileNotFoundError:
            self.CATALOG_BASE_URL = "http://localhost:9093/catalog"

    def registra_nel_catalogo(self):
        """[ESERCIZIO 05] Invia la registrazione con i campi obbligatori richiesti dal tuo Catalogo"""
        # Modificato per includere 'description' e 'resources' al fine di evitare l'HTTP Error 400
        payload = {
            "id": ID_DISPOSITIVO,
            "description": "MQTT Actuator Command Publisher Node",
            "resources": ["attuatori"]
        }

        while self.running:
            try:
                url = f"{self.CATALOG_BASE_URL}/services" 
                response = requests.post(url, json=payload, timeout=5)
                
                if response.status_code in [200, 201]:
                    print(f"\n[REST] Registrazione/Keep-alive aggiornato sul Catalogo.")
                else:
                    print(f"\n[REST - WARNING] Il catalogo ha risposto con codice di stato: {response.status_code}")
            except Exception as e:
                print(f"\n[REST - ERRORE] Impossibile inviare keep-alive al Catalogo a {self.CATALOG_BASE_URL}: {e}")
            
            # Invia il keep-alive ogni 60 secondi (ampiamente prima dei 120s del timeout di rimozione)
            time.sleep(60)

    def scopri_dispositivi(self):
        """Interroga il Catalogo estraendo i topic dall'oggetto 'mqtt' del JSON"""
        print(f"[REST] Interrogazione del Catalogo a {self.CATALOG_BASE_URL}/devices ...")
        try:
            url = f"{self.CATALOG_BASE_URL}/devices"
            response = requests.get(url, timeout=5)
            
            if response.status_code == 200:
                dispositivi = response.json() 
                self.dispositivi_scoperti.clear()
                
                for dev in dispositivi:
                    # Adattamento per la struttura del tuo catalogo: i topic sono dentro l'oggetto "mqtt"
                    mqtt_info = dev.get("mqtt", {})
                    if "command_topic" in mqtt_info and "feedback_topic" in mqtt_info:
                        self.dispositivi_scoperti[dev["id"]] = {
                            "tipo": dev.get("resources", ["generico"])[0],
                            "command_topic": mqtt_info["command_topic"],
                            "feedback_topic": mqtt_info["feedback_topic"]
                        }
                print(f"[CATALOGO] Scoperti {len(self.dispositivi_scoperti)} attuatori reali pronti al controllo.")
                
                if self.client.is_connected():
                    for dev_id, info in self.dispositivi_scoperti.items():
                        self.client.subscribe(info["feedback_topic"])
            else:
                print(f"[REST - ERRORE] Errore di risposta dal catalogo: {response.status_code}")
                
        except Exception as e:
            print(f"[REST - ERRORE] Errore di connessione al catalogo durante la scoperta: {e}")

    def on_connect(self, client, userdata, flags, reason_code, properties):
        if reason_code == 0:
            print(f"[MQTT] Connesso con successo al Broker: {BROKER_MQTT}")
            for dev_id, info in self.dispositivi_scoperti.items():
                feedback_t = info["feedback_topic"]
                client.subscribe(feedback_t)
                print(f"[MQTT] Iscritto al feedback topic: {feedback_t}")
        else:
            print(f"[MQTT] Connessione fallita. Codice d'errore: {reason_code}")

    def on_message(self, client, userdata, msg):
        try:
            payload_decodificato = json.loads(msg.payload.decode())
            print(f"\n[FEEDBACK RICEVUTO] Topic: {msg.topic} -> Stato attuale: {payload_decodificato}")
        except Exception:
            print(f"\n[MQTT] Messaggio di feedback non JSON ricevuto su {msg.topic}: {msg.payload.decode()}")

    def invia_comando(self, device_id, valore):
        if device_id not in self.dispositivi_scoperti:
            print("[ERRORE] Dispositivo non trovato.")
            return

        topic = self.dispositivi_scoperti[device_id]["command_topic"]
        payload_comando = {
            "sender": ID_DISPOSITIVO,
            "timestamp": time.time(),
            "target": device_id,
            "command": valore
        }
        
        stringa_json = json.dumps(payload_comando)
        self.client.publish(topic, stringa_json)
        print(f"[MQTT] Comando inviato a {topic}: {stringa_json}")

    def interfaccia_utente(self):
        time.sleep(1) 
        while self.running:
            print("\n" + "="*45)
            if not self.dispositivi_scoperti:
                print(" NESSUN DISPOSITIVO RILEVATO DAL CATALOGO.")
                print(" Assicurati che gli attuatori siano registrati.")
            else:
                print(" DISPOSITIVI DISPONIBILI PER IL CONTROLLO:")
                for i, dev_id in enumerate(self.dispositivi_scoperti.keys(), 1):
                    print(f" {i}. {dev_id} ({self.dispositivi_scoperti[dev_id]['tipo']})")
            print("---------------------------------------------")
            print(" r. Ricarica/Aggiorna lista dal Catalogo")
            print(" 0. Esci dall'applicazione")
            print("="*45)
            
            scelta = input("Seleziona un'opzione: ").strip()
            if scelta == "0":
                self.running = False
                break
            elif scelta.lower() == 'r':
                self.scopri_dispositivi()
                continue
                
            try:
                if not self.dispositivi_scoperti:
                    print("[ERRORE] Nessun dispositivo disponibile per il controllo.")
                    continue

                chiavi = list(self.dispositivi_scoperti.keys())
                dev_selezionato = chiavi[int(scelta) - 1]
                tipo_dev = self.dispositivi_scoperti[dev_selezionato]["tipo"]
                
                print(f"\nStai controllando l'attuatore: {dev_selezionato}")
                if tipo_dev in ["led", "luce"]:
                    valore = input("Inserisci comando (ON / OFF): ").strip().upper()
                elif tipo_dev == "termostato":
                    valore = input("Inserisci la temperatura desiderata (es. 22.5): ").strip()
                elif tipo_dev == "tapparella":
                    valore = input("Inserisci livello apertura (es. APERTA / CHIUSA / 50%): ").strip()
                else:
                    valore = input("Inserisci comando generico: ").strip()
                
                self.invia_comando(dev_selezionato, valore)
                time.sleep(1) 
            except (ValueError, IndexError):
                print("[ERRORE] Selezione non valida. Riprova.")

    def start(self):
        self.scopri_dispositivi()
        thread_rest = threading.Thread(target=self.registra_nel_catalogo, daemon=True)
        thread_rest.start()
        self.client.connect(BROKER_MQTT, PORTA_MQTT, 60)
        self.client.loop_start()
        self.interfaccia_utente()
        
        print("Chiusura dell'applicazione in corso...")
        self.client.loop_stop()
        self.client.disconnect()


if __name__ == "__main__":
    publisher = ActuatorPublisher()
    publisher.start()
