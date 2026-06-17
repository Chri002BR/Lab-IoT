import cherrypy
import json
import time
import paho.mqtt.client as PahoMQTT

#TODO: dare un occhiata a gestione versione mqtt, tolta gestione in es09
#TODO: da rivedere chiedere chi lo ha fatto, se mio è solo generato e non testato
#TODO NON DOVREBBE BASARSI SULL'ES04 SENZA RIFARE TUTTO DA CAPO ??????????????????

# --- NUOVA CLASSE SUBSCRIBER MQTT INTEGRATA PER L'ESERCIZIO 12 ---
class MQTTSubscriber:
    def __init__(self, clientID, broker, port, topic, log_service):
        self.clientID = clientID
        self.broker = broker
        self.port = port
        self.topic = topic
        self.log_service = log_service  # Riferimento all'istanza del servizio web
        
        # Configurazione conforme a Paho-MQTT v2.0+
        self._paho_mqtt = PahoMQTT.Client(PahoMQTT.CallbackAPIVersion.VERSION2, client_id=clientID)
        self._paho_mqtt.on_connect = self.on_connect
        self._paho_mqtt.on_message = self.on_message

    def start(self):
        try:
            self._paho_mqtt.connect(self.broker, self.port, keepalive=60)
            self._paho_mqtt.loop_start()  # Avvia il loop MQTT in un thread in background
            self._paho_mqtt.subscribe(self.topic, 2)
            print(f"MQTT Subscriber avviato. In ascolto sul topic: {self.topic}")
        except Exception as e:
            print(f"Impossibile avviare il subscriber MQTT: {e}")

    def stop(self):
        self._paho_mqtt.unsubscribe(self.topic)
        self._paho_mqtt.loop_stop()
        self._paho_mqtt.disconnect()
        print("MQTT Subscriber arrestato correttamente.")

    def on_connect(self, client, userdata, flags, reason_code, properties):
        if reason_code == 0:
            print(f"Connesso con successo al broker MQTT: {self.broker}")
        else:
            print(f"Connessione MQTT fallita con codice d'errore: {reason_code}")

    def on_message(self, client, userdata, msg):
        print(f"[MQTT] Messaggio ricevuto sul topic '{msg.topic}'")
        try:
            raw = msg.payload.decode('utf-8')
            body = json.loads(raw)
            
            # Stessi identici controlli di validazione SenML presenti nel metodo POST
            if "bn" not in body or "e" not in body:
                print("[MQTT] Errore: Validazione SenML fallita (Manca bn o e)")
                return
            if not isinstance(body["e"], list) or len(body["e"]) != 1:
                print("[MQTT] Errore: Validazione SenML fallita ('e' deve essere una lista con 1 elemento)")
                return
            if len(body["e"][0]) != 3:
                print("[MQTT] Errore: Validazione SenML fallita (L'elemento interno a 'e' deve avere 3 campi)")
                return
            if "n" not in body["e"][0] or "v" not in body["e"][0] or "u" not in body["e"][0]:
                print("[MQTT] Errore: Validazione SenML fallita (Mancano n, v o u)")
                return
            
            # Gestione del parametro temporale 'bt' (identica alla POST)
            timestamp = time.time()
            if "bt" not in body:
                body = {"bt": timestamp, **body}
            else:
                body["bt"] = timestamp

            service_class = self.log_service.__class__
            
            # Assegnazione ID e incremento (usando le variabili condivise della classe)
            body = {"id": service_class.id, **body}
            service_class.id += 1
            
            # Aggiunta del log ricevuto tramite MQTT nella lista centrale
            self.log_service.AddLog(body)
            print(f"[MQTT] Nuovo log salvato con successo! (ID: {body['id']})")
            
        except json.JSONDecodeError:
            print("[MQTT] Attenzione: Ricevuto un payload non in formato JSON valido")
        except Exception as e:
            print(f"[MQTT] Errore imprevisto durante l'elaborazione: {e}")