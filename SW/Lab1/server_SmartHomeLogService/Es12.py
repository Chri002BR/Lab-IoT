import cherrypy
import json
import time
import paho.mqtt.client as PahoMQTT


class SmartHomeLogService(object):
    exposed = True
    
    id = 0
    logs = []

    def createSenML_URI(self, uri, params=None):
        finalURI = {
            "s": "log" 
        }
        
        if len(uri) > 0:
            finalURI["bn"] = uri[0]  # Stanza
            
        if params:
            finalURI["params"] = params

        return finalURI

    def AddLog(self, value):
        self.logs.append(value)

    ## Funzione per ricevere un log da un sensore o attuatore e aggiungerlo alla lista dei log
    def POST(self, *uri, **params):
        if(len(uri) == 0):
            raw = cherrypy.request.body.read()
            timestamp = time.time()
            
            # Controllo correttezza del pacchetto
            if not raw:
                raise cherrypy.HTTPError(400, "Bad request: Empty body")
            
            try:
                body = json.loads(raw)
            except json.JSONDecodeError:
                raise cherrypy.HTTPError(400, "Bad request: Invalid JSON body")
            
            # controllo che il pacchetto contenga i campi necessari (bn, e) e che e sia una lista con almeno un elemento che contenga i campi n, v, u
            if "bn" not in body or "e" not in body:
                raise cherrypy.HTTPError(422, "Bad request: Unprocessable Entity")
            
            if not isinstance(body["e"], list):
                raise cherrypy.HTTPError(422, "Bad request: Unprocessable Entity")
            
            if len(body["e"]) != 1:
                raise cherrypy.HTTPError(422, "Bad request: Unprocessable Entity")
            
            if len(body["e"][0]) != 3:
                raise cherrypy.HTTPError(422, "Bad request: Unprocessable Entity")
            
            if "n" not in body["e"][0] or "v" not in body["e"][0] or "u" not in body["e"][0]:
                raise cherrypy.HTTPError(422, "Bad request: Unprocessable Entity")
            
            if "bt" not in body:
                timestamp = time.time()
                body = {"bt": timestamp, **body}
            else:
                body["bt"] = timestamp
            
            body = {"id": SmartHomeLogService.id, **body}
            SmartHomeLogService.id += 1
            
            self.AddLog(body)
            return json.dumps({"status": "success", "log_id": SmartHomeLogService.id - 1}).encode("utf-8")
    
    ## Funzione per ottenere tutti i log, con la possibilità di filtrare per stanza e per timestamp
    def GET(self, *uri, **params):          
        # GET /log
        if(len(uri) == 0 and len(params) == 0):
            return json.dumps(self.logs).encode("utf-8")
        
        # GET /log/{room}
        if (len(uri) == 1 and len(params) == 0):
            return json.dumps(self.get_logs_by_room(self.logs, uri[0])).encode("utf-8")
        
        # GET /log?room={room}&since={timestamp}
        response = self.logs
        if (len(uri) == 0 and len(params) <= 2):
            for key in params.keys():
                if key not in ["room", "since"]:
                    raise cherrypy.HTTPError(400, "Bad request: Invalid query parameters. Valid parameters are 'room' and 'since'. Example: /log?room=bedroom&since=1234567890")
            if "room" in params:
                response = self.get_logs_by_room(response, params.get("room"))
            if "since" in params:
                response = self.get_logs_by_time(response, float(params.get("since")))
            return json.dumps(response).encode("utf-8")
        
        raise cherrypy.HTTPError(400, "Bad request: Invalid URI format. Valid formats are /log, /log/{room}, /log?room={room}&since={timestamp}. Example: /log?room=bedroom&since=1234567890")

    ## Funzione per eliminare i log precedenti a un certo timestamp
    def DELETE(self, *uri, **params):
        try:
            if(len(uri) == 0 and len(params) == 1 and ("before" in params)):
                epoch = float(params.get("before"))
                self.logs[:] = [log for log in self.logs if log["bt"] >= epoch]
                return json.dumps({"status": "success", "deleted_before": epoch}).encode("utf-8")
            else:
                raise cherrypy.HTTPError(400, "Bad request: Not found")
        except:
            raise cherrypy.HTTPError(500, "Server error")

    def get_logs_by_room(self, paramLogs, room):
        response = []
        for log in paramLogs:
            if room in log["bn"]:
                response.append(log)
        return response
    
    def get_logs_by_time(self, paramLogs, since):
        response = []
        for log in paramLogs:
            if log["bt"] >= since:
                response.append(log)
        return response


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
            
            # Assegnazione ID e incremento (usando le variabili condivise della classe)
            body = {"id": SmartHomeLogService.id, **body}
            SmartHomeLogService.id += 1
            
            # Aggiunta del log ricevuto tramite MQTT nella lista centrale
            self.log_service.AddLog(body)
            print(f"[MQTT] Nuovo log salvato con successo! (ID: {body['id']})")
            
        except json.JSONDecodeError:
            print("[MQTT] Attenzione: Ricevuto un payload non in formato JSON valido")
        except Exception as e:
            print(f"[MQTT] Errore imprevisto durante l'elaborazione: {e}")