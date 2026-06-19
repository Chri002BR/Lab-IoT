import json
import time
import threading
import requests
import paho.mqtt.client as mqtt
from pathlib import Path



# Configurazione Broker MQTT
BROKER_MQTT = "broker.hivemq.com"  
PORTA_MQTT = 1883
ID_DISPOSITIVO = "MQTT_Command_Publisher_Team14"

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
            self.CATALOG_BASE_URL = config.get("uri_catalog", "http://localhost:9093/catalog")
        except FileNotFoundError:
            self.CATALOG_BASE_URL = "http://localhost:9093/catalog"

    def registra_nel_catalogo(self):
        """[ESERCIZIO 05] Invia la registrazione con i campi obbligatori richiesti dal tuo Catalogo"""
        # Modificato per includere 'description' e 'resources' al fine di evitare l'HTTP Error 400
        payload = {
            "id": ID_DISPOSITIVO,
            "description": "MQTT Actuator Command Publisher Node",
            "resources": []
        }

        # Si registra come service e invia keep-alive ogni 60 secondi
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
                    if "command_topic" in mqtt_info["topic"] and "feedback_topic" in mqtt_info["topic"]:
                        self.dispositivi_scoperti[dev["id"]] = {
                            "tipo": dev.get("resources", ["generico"])[0],
                            "command_topic": mqtt_info["topic"]["command_topic"],
                            "feedback_topic": mqtt_info["topic"]["feedback_topic"]
                        }
                print(f"[CATALOGO] Scoperti {len(self.dispositivi_scoperti)} attuatori reali pronti al controllo.")
                
                if self.client.is_connected():
                    for dev_id, info in self.dispositivi_scoperti.items():
                        self.client.subscribe(info["feedback_topic"])
            else:
                print(f"[REST] Errore di risposta dal catalogo: {response.status_code}")
                
        except Exception as e:
            print(f"[REST] Errore di connessione al catalogo durante la scoperta: {e}")

        # recupero l'es03
        try:
            url = f"{self.CATALOG_BASE_URL}/services/smart-home-actuator-service"
            response = requests.get(url, timeout=5)
            
            if response.status_code == 200:
                servizio = response.json()
                self.dispositivi_scoperti["smart-home-actuator-service"] = {
                    "tipo": "servizio",
                    "endpoint": servizio.get("endpoint", "")
                }
                print(f"[CATALOGO] Scoperto 1 servizio reale pronto al controllo.")
                # Appena ottenuto l'endpoint, interrogo subito il servizio con una GET per popolare la struttura interna con lo stato attuale degli attuatori
                self.aggiorna_stato_servizio("smart-home-actuator-service")
            else:
                print(f"[REST] Errore di risposta dal catalogo: {response.status_code}")
                
        except Exception as e:
            print(f"[REST] Errore di connessione al catalogo durante la scoperta: {e}")
            

    def on_connect(self, client, userdata, flags, reason_code, properties):
        if reason_code == 0:
            print(f"[MQTT] Connesso con successo al Broker: {BROKER_MQTT}")
            
            for dev_id, info in self.dispositivi_scoperti.items():
                if "feedback_topic" in info:
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
        # 1. Recupero il topic di comando dal dizionario
        topic = self.dispositivi_scoperti[device_id].get("command_topic")
        if not topic:
            print("[ERRORE] Nessun command_topic disponibile per questo dispositivo.")
            return

        # 2. Costruisco il payload. 
        # Trasformo "ON"/"OFF" in un booleano (True/False)
        # value = (valore == "ON")
        # if (value == "on"):
        #     value = 1
        # elif (value == "off"):
        #     value = 0
        value = 1 if valore == "ON" else 0

        # Struttura in stile SenML
        payload_comando = {
            "bn" : "ArduinoGroup14",
            "e": [
                {
                    "n": "led",
                    "v": value,
                    "u": "bool"
                }
            ]
        }
        
        # 3. Converto in stringa JSON
        stringa_json = json.dumps(payload_comando)
        
        # 4. Pubblico il messaggio tramite il client MQTT
        try:
            self.client.publish(topic, stringa_json)
            print(f"[MQTT] Comando pubblicato con successo sul topic: {topic}")
            print(f"[MQTT] Payload: {stringa_json}")
            self.send_log(payload_comando)
        except Exception as e:
            print(f"[MQTT - ERRORE] Impossibile pubblicare il messaggio: {e}")

        
    def gestisci_servizio_rest(self, dev_id):
        """Gestisce l'interazione REST con il servizio Es03 (smart-home-actuator-service):
        aggiorna lo stato corrente con una GET e, se l'utente lo desidera, invia una PUT
        per modificare un attuatore. NB: Es03 espone solo GET e PUT, non POST."""
 
        info = self.dispositivi_scoperti.get(dev_id)
 
        endpoint = info["endpoint"]
        endpoint = endpoint.replace("0.0.0.0", "127.0.0.1")
        if not endpoint.startswith("http"):
            endpoint = "http://" + endpoint
 
        # stanza = input("Inserisci la stanza (living_room / kitchen / bedroom): ").strip()
        print("\n--- Selezione Stanza ---\/\n" \
        " 1. living_room\n" \
        " 2. kitchen\n" \
        " 3. bedroom")
        scelta_stanza = input("Inserisci il numero della stanza (1/2/3): ").strip()
        mappa_stanze = {"1": "living_room", "2": "kitchen", "3": "bedroom"}
        if scelta_stanza not in mappa_stanze:
            print("[ERRORE] Selezione della stanza non valida.")
            return
        stanza = mappa_stanze[scelta_stanza]

        print("\n Selezione Attuatore:\n" \
        "  1. thermostat\n" \
        "  2. lights\n" \
        "  3. blinds")
        scelta_attuatore = input("Inserisci il numero dell'attuatore (1/2/3): ").strip()
        
        mappa_attuatori = {"1": "thermostat", "2": "lights", "3": "blinds"}
        if scelta_attuatore not in mappa_attuatori:
            print("[ERRORE] Selezione dell'attuatore non valida.")
            return
        sensore = mappa_attuatori[scelta_attuatore]
        # sensore = input("Inserisci l'attuatore (thermostat / lights / blinds): ").strip()
 
        if sensore == "thermostat":
            valore_raw = input("Nuova temperatura desiderata (10-30): ").strip()
            try:
                valore = float(valore_raw)
            except ValueError:
                print("[ERRORE] Valore non numerico.")
                return
            unita = "Cel"
        elif sensore == "lights":
            valore_raw = input("Nuovo stato luci (ON / OFF): ").strip().upper()
            if valore_raw not in ("ON", "OFF"):
                print("[ERRORE] Valore non valido, usare ON o OFF.")
                return
            valore = (valore_raw == "ON")
            unita = "bool"
        elif sensore == "blinds":
            valore_raw = input("Nuovo livello apertura tapparelle (0-100): ").strip()
            try:
                valore = float(valore_raw)
            except ValueError:
                print("[ERRORE] Valore non numerico.")
                return
            unita = "pct"
        else:
            print("[ERRORE] Attuatore non riconosciuto.")
            return
 
        payload = {
            "bn": stanza + "/",
            "e": [
                {
                    "n": sensore,
                    "v": valore,
                    "u": unita
                }
            ]
        }
        
        # Invio la richiesta PUT tramite REST 
        try:
            print(f"[REST] Invio comando PUT a {endpoint}...")
            response = requests.put(endpoint, json=payload, timeout=5)
            if response.status_code == 200:
                print(f"[REST] Comando applicato con successo!")
            else:
                print(f"[REST] Errore nell'invio del comando. Codice: {response.status_code}")
        except Exception as e:
            print(f"[REST - ERRORE] Impossibile inviare il comando: {e}")


    def interfaccia_utente(self):
        time.sleep(1) # Per evitare problemi nel print dell'interfaccia
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

                print(self.dispositivi_scoperti[dev_selezionato])
                print(f"\nStai controllando l'attuatore: {dev_selezionato}")

                if tipo_dev in ["led", "luce"]:
                    valore = input("Inserisci comando (ON / OFF): ").strip().upper()
                    self.invia_comando(dev_selezionato, valore)
                elif tipo_dev == "servizio":
                    self.gestisci_servizio_rest(dev_selezionato)
                    continue
                else:
                    raise ValueError("Tipo di dispositivo non riconosciuto per il comando.")
                
            except (ValueError, IndexError):
                print("[ERRORE] Selezione non valida. Riprova.")

    def aggiorna_stato_servizio(self, dev_id):
        """Invia una GET al servizio REST Es03 (smart-home-actuator-service) e salva
        il risultato nella struttura interna self.dispositivi_scoperti, sotto la
        chiave 'stato'."""
        info = self.dispositivi_scoperti.get(dev_id)
        if not info or not info.get("endpoint"):
            print("[ERRORE] Endpoint del servizio non disponibile.")
            return None
 
        endpoint = info["endpoint"]
        endpoint = endpoint.replace("0.0.0.0", "127.0.0.1")
        if not endpoint.startswith("http"):
            endpoint = "http://" + endpoint
 
        try:
            response = requests.get(endpoint, timeout=5)
            if response.status_code == 200:
                stato = response.json()
                # Salvataggio nella struttura interna
                info["stato"] = stato
                # print(f"[REST] Stato attuale ricevuto da '{dev_id}':")
                # print(json.dumps(stato, indent=2))
                return stato
            else:
                print(f"[REST] Errore nella richiesta GET a {endpoint}: status code {response.status_code}")
                return None
        except Exception as e:
            print(f"[REST - ERRORE] Impossibile contattare il servizio a {endpoint}: {e}")
            return None

    def send_log(self, payload):
        """Compone un pacchetto in formato SenML e lo invia a un server di log.
        Ritorna True se l'invio ha successo, False altrimenti."""
        
        url_log="http://127.0.0.1:9092/log/"
        timestamp = time.time()
        
        # Aggiunta del timestamp al log
        payload["t"] = timestamp

        # Invio tramite POST
        try:
            # json=payload converte automaticamente il dizionario in stringa JSON e imposta l'header
            resp = requests.post( url_log, json=payload, headers={"Content-Type": "application/json"}, timeout=5 )
            
            # Controllo se il server ha risposto con successo (200 OK o 201 Created)
            if resp.status_code in (200, 201):
                print(f"[LOG SUCCESS] Inviato log correttamente")
                return True
            else:
                print(f"[LOG ERROR] Fallito invio log. Status code: {resp.status_code}")
                return False

        except requests.exceptions.RequestException as e:
            # Cattura problemi di rete, timeout o server irraggiungibile
            print(f"[LOG EXCEPTION] Impossibile contattare il server di log: {e}")
            return False



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
