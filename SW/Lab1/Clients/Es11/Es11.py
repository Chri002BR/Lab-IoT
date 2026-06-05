import json
import time
import threading
import requests
import paho.mqtt.client as mqtt

CATALOG_URL = "http://localhost:8080"  # Cambia con l'URL reale del tuo Catalogo
BROKER_MQTT = "broker.hivemq.com"      # Sostituto funzionante di iot.eclipse.org
PORTA_MQTT = 1883
ID_DISPOSITIVO = "MQTT_Command_Publisher_TeamX"

class ActuatorPublisher:
    def __init__(self):
        # Configurazione obbligatoria per Paho-MQTT >= 2.0
        self.client = mqtt.Client(callback_api_version=mqtt.CallbackAPIVersion.VERSION2, client_id=ID_DISPOSITIVO)
        self.dispositivi_scoperti = {}
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        self.running = True

    def registra_nel_catalogo(self):
        """Invia una richiesta REST POST/PUT per registrarsi al Catalogo e mantiene il keep-alive"""
        payload = {
            "id": ID_DISPOSITIVO,
            "tipo": "publisher-manager",
            "risorse": ["attuatori"],
            "timestamp": time.time()
        }

        while self.running:
            try:
                # Simulazione di invio (Esercizio 05)
                # Sostituisci con l'endpoint corretto, es: f"{CATALOG_URL}/registry"
                print(f"\n[REST] Invio keep-alive/registrazione al Catalogo per {ID_DISPOSITIVO}...")
                # response = requests.post(f"{CATALOG_URL}/devices", json=payload, timeout=5)
                pass 
            except Exception as e:
                print(f"[REST - ERRORE] Impossibile raggiungere il Catalogo: {e}")
            
            # Invia la registrazione periodicamente (es. ogni 60 secondi)
            time.sleep(60)

    def scopri_dispositivi(self):
        """Interroga il Catalogo via REST per scoprire i topic dei dispositivi"""
        print("[REST] Interrogazione del Catalogo per scoprire i dispositivi...")
        try:
            # Chiamata GET reale (decommentare quando il catalogo è attivo):
            # response = requests.get(f"{CATALOG_URL}/devices")
            # dati = response.json()
            
            # Simulazione dati ricevuti dal Catalogo (Esercizio 03 & Arduino)
            dati_simulati = [
                {"id": "arduino_led", "tipo": "led", "command_topic": "smarthome/teamX/arduino/led/set", "feedback_topic": "smarthome/teamX/arduino/led/state"},
                {"id": "termostato_1", "tipo": "termostato", "command_topic": "smarthome/teamX/thermostat/set", "feedback_topic": "smarthome/teamX/thermostat/state"},
                {"id": "luce_salotto", "tipo": "luce", "command_topic": "smarthome/teamX/lights/lounge/set", "feedback_topic": "smarthome/teamX/lights/lounge/state"},
                {"id": "tapparella_1", "tipo": "tapparella", "command_topic": "smarthome/teamX/blinds/1/set", "feedback_topic": "smarthome/teamX/blinds/1/state"}
            ]
            
            for dev in dati_simulati:
                self.dispositivi_scoperti[dev["id"]] = {
                    "tipo": dev["tipo"],
                    "command_topic": dev["command_topic"],
                    "feedback_topic": dev["feedback_topic"]
                }
            print(f"[CATALOGO] Scoperti {len(self.dispositivi_scoperti)} attuatori pronti al controllo.")
        except Exception as e:
            print(f"[REST - ERRORE] Errore durante la scoperta dei dispositivi: {e}")

    # FIX: Firma aggiornata per le API v2 (on_connect riceve flags, reason_code, properties)
    def on_connect(self, client, userdata, flags, reason_code, properties):
        if reason_code == 0:
            print(f"[MQTT] Connesso con successo al Broker: {BROKER_MQTT}")
            # Si iscrive ai topic di feedback di tutti i dispositivi scoperti
            for dev_id, info in self.dispositivi_scoperti.items():
                feedback_t = info["feedback_topic"]
                client.subscribe(feedback_t)
                print(f"[MQTT] Iscritto al feedback topic: {feedback_t}")
        else:
            print(f"[MQTT] Connessione fallita. Codice d'errore: {reason_code}")

    def on_message(self, client, userdata, msg):
        """Riceve e mostra la conferma dello stato dall'attuatore (Feedback)"""
        try:
            payload_decodificato = json.loads(msg.payload.decode())
            print(f"\n[FEEDBACK RICEVUTO] Topic: {msg.topic} -> Stato attuale: {payload_decodificato}")
        except Exception as e:
            print(f"\n[MQTT] Messaggio di feedback non JSON ricevuto su {msg.topic}: {msg.payload.decode()}")

    def invia_comando(self, device_id, valore):
        """Costruisce il JSON e pubblica il comando sul topic dell'attuatore"""
        if device_id not in self.dispositivi_scoperti:
            print("[ERRORE] Dispositivo non trovato.")
            return

        topic = self.dispositivi_scoperti[device_id]["command_topic"]
        
        # Struttura del JSON definita dal Team
        payload_comando = {
            "sender": ID_DISPOSITIVO,
            "timestamp": time.time(),
            "target": device_id,
            "command": valore
        }
        
        stringa_json = json.dumps(payload_comando)
        # FIX: cambiato da self.client_mqtt a self.client
        self.client.publish(topic, stringa_json)
        print(f"[MQTT] Comando inviato a {topic}: {stringa_json}")

    def interfaccia_utente(self):
        """CLI Interattiva per il controllo manuale degli attuatori"""
        time.sleep(2) # Lascia il tempo alle stampe iniziali di stabilizzarsi
        while self.running:
            print("\n" + "="*40)
            print(" DISPOSITIVI DISPONIBILI PER IL CONTROLLO:")
            for i, dev_id in enumerate(self.dispositivi_scoperti.keys(), 1):
                print(f" {i}. {dev_id} ({self.dispositivi_scoperti[dev_id]['tipo']})")
            print(" 0. Esci dall'applicazione")
            print("="*40)
            
            scelta = input("Seleziona il numero del dispositivo da controllare: ")
            if scelta == "0":
                self.running = False
                break
                
            try:
                chiavi = list(self.dispositivi_scoperti.keys())
                dev_selezionato = chiavi[int(scelta) - 1]
                tipo_dev = self.dispositivi_scoperti[dev_selezionato]["tipo"]
                
                print(f"\nStai controllando: {dev_selezionato}")
                if tipo_dev == "led" or tipo_dev == "luce":
                    valore = input("Inserisci comando (ON / OFF): ").strip().upper()
                elif tipo_dev == "termostato":
                    valore = input("Inserisci la temperatura desiderata (es. 22.5): ").strip()
                elif tipo_dev == "tapparella":
                    valore = input("Inserisci livello apertura (es. APERTA / CHIUSA / 50%): ").strip()
                else:
                    valore = input("Inserisci comando generico: ").strip()
                
                self.invia_comando(dev_selezionato, valore)
                time.sleep(1.5) # Pausa per leggere l'eventuale feedback asincrono
            except (ValueError, IndexError):
                print("[ERRORE] Selezione non valida. Riprova.")

    def start(self):
        # 1. Recupera i dispositivi dal catalogo
        self.scopri_dispositivi()
        
        if not self.dispositivi_scoperti:
            print("[ATTENZIONE] Nessun dispositivo configurato. Uscita.")
            return

        # 2. Avvia thread per la registrazione periodica REST (Esercizio 05)
        thread_rest = threading.Thread(target=self.registra_nel_catalogo, daemon=True)
        thread_rest.start()

        # 3. Connessione MQTT ed avvio loop in background
        # FIX: cambiato da self.client_mqtt a self.client
        self.client.connect(BROKER_MQTT, PORTA_MQTT, 60)
        self.client.loop_start()

        # 4. Avvia la CLI sul thread principale
        self.interfaccia_utente()

        # Pulizia alla chiusura
        print("Chiusura dell'applicazione in corso...")
        self.client.loop_stop()
        self.client.disconnect()

if __name__ == "__main__":
    publisher = ActuatorPublisher()
    publisher.start()