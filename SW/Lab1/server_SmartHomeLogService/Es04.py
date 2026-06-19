import cherrypy
import json
import time
import threading
import requests
from pathlib import Path

# Configurazione Broker MQTT e Costanti
BROKER_MQTT = "broker.hivemq.com"
PORTA_MQTT = 1883
ID_SERVIZIO = "smart-home-event-log-service"

class SmartHomeLogService(object):
    exposed = True


    ### GESTIONE DELLE RICHIESTE REST ###

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
            
            #controllo che il pacchetto contenga i campi necessari (bn, e) e che e sia una lista con almeno un elemento che contenga i campi n, v, u
            
            if "bn" not in body or "e" not in body:
                raise cherrypy.HTTPError(422, "Bad request: Unprocessable Entity")
            
            if not isinstance(body["e"], list):
                raise cherrypy.HTTPError(422, "Bad request: Unprocessable Entity")
            
            if len(body["e"]) != 1:
                raise cherrypy.HTTPError(422, "Bad request: Unprocessable Entity")
            
            if "n" not in body["e"][0] or "v" not in body["e"][0] or "u" not in body["e"][0]:
                raise cherrypy.HTTPError(422, "Bad request: Unprocessable Entity")
            
            if "bt" not in body:
                timestamp = time.time()
                body = {"bt": timestamp, **body}
            else:
                body["bt"] = timestamp

            assigned_id = self.thread_lock(body)
            return json.dumps({"status": "success", "log_id": assigned_id}).encode("utf-8")
    
    def thread_lock(self, body): #Serve a rendere thread-safe l'incremento dell'id e l'aggiunta del log alla lista dei log
        with self._lock:
            body = {"id": self.log_id_counter, **body}
            assigned_id = self.log_id_counter      
            self.log_id_counter += 1                 
            self.AddLog(body)
            return assigned_id

    ## Funzione per ottenere tutti i log, con la possibilità di filtrare per stanza e per timestamp
    def GET(self, *uri, **params): 
        #estraggo il log corrente con la protezione del lock per evitare che venga modificato mentre lo sto leggendo
        with self._lock: 
            log = list(self.logs) 

        # GET /log
        if(len(uri) == 0 and len(params) == 0):
            return json.dumps(log).encode("utf-8")
        
        # GET /log/{room}
        if (len(uri) == 1 and len(params) == 0):
            return json.dumps(self.get_logs_by_room(log, uri[0])).encode("utf-8")
        
        # GET /log?room={room}&since={timestamp}
        response = log
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
        error_Cherrypy=False

        try:
            if(len(uri) == 0 and len(params) == 1 and ("before" in params)):
                epoch = float(params.get("before"))

                with self._lock: #protezione del thread con lock
                # Sovrascrive la lista mantenendo solo gli elementi con EPOCH >= epoch
                    self.logs[:] = [log for log in self.logs if log["bt"] >= epoch]
                return json.dumps({"status": "success", "deleted_before": epoch}).encode("utf-8")
            else:
                error_Cherrypy=True
        except:
            if not error_Cherrypy:
                raise cherrypy.HTTPError(500, "Server error")
            else:
                raise cherrypy.HTTPError(400, "Bad request: Not found")
                


    ### utilities ###

    
    ## Funzione per aggiungere un log alla lista dei log
    def AddLog(self, value):
        self.logs.append(value)

    ## Funzione per filtrare i log in base alla stanza
    def get_logs_by_room(self, paramLogs, room):
        response = []
        for log in paramLogs:
            if room in log["bn"]:
                response.append(log)
        return response
    
    ## Funzione per filtrare i log in base al timestamp
    def get_logs_by_time(self, paramLogs, since):
        response = []
        for log in paramLogs:
            if log["bt"] >= since:
                response.append(log)
        return response
    
    def __init__(self): #AGGIUNTO SU RICHIESTA ES06
        self.log_id_counter = 0
        self.logs = [] #clear lista log
        self._lock = threading.Lock() #gestione thread della lista log, per non creare sovrapposizioni


        config_path = Path(__file__).parent.parent / "config-uri-client.json" 
        self.service_endpoint = "/log"  # endpoint messo nel payload del catalog


        #Prendo dal file la configurazione, altrimenti imposto un valore di default
        try:
            with open(config_path, "r") as f:
                config = json.load(f)
            self.CATALOG_BASE_URL = config.get("uri_catalog", "http://localhost:9093/catalog")
        except Exception:
            self.CATALOG_BASE_URL = "http://localhost:9093/catalog"

        #Creo e avvio il thread per la registrazione e il mantenimento con il catalog
        self.stop_event = threading.Event()
        
        catalog_thread = threading.Thread(target=self.register_and_keep_alive, daemon=True)
        catalog_thread.start()

    def register_and_keep_alive(self):#AGGIUNTO SU RICHIESTA ES06
        """Gestisce la registrazione e il keep-alive del servizio nel Resource Catalog tramite REST."""
       
        while not self.stop_event.is_set():
            payload = {
                "id": "servizio_di_log",
                "description": "Servizio di logging dei topic MQTT per letture dei sensori e i comandi degli attuatori.",
                "endpoint": {
                    "get_logs": f"{self.service_endpoint}",
                    "post_log": f"{self.service_endpoint}",
                    "delete_logs": f"{self.service_endpoint}?before={{timestamp}}"
                },
                "resources": 
                    {
                        "methods": ["GET", "POST", "DELETE"]
                    },
                "insert_timestamp": time.time()
                }
             
            try:
                url = f"{self.CATALOG_BASE_URL}/services" 
                response = requests.post(url, json=payload, timeout=5)
                
                if response.status_code in [200, 201]:
                    print("[REST] Registrazione/Keep-alive aggiornato sul Catalogo.")
                else:
                    print(f"[REST - WARNING] Il catalogo ha risposto con codice di stato: {response.status_code}")
            except Exception as e:
                print(f"[REST - ERRORE] Impossibile inviare keep-alive a {self.CATALOG_BASE_URL}: {e}")
            
            # Attesa di 60 secondi prima del prossimo invio di keep-alive
            time.sleep(60)

    # Funzioni per stoppare il thread che gestisce il catalog
    def stop(self):
            """Arresta in modo pulito il thread del catalogo."""
            print("\n[SISTEMA] Arresto del thread di keep-alive in corso...")
            self.stop_event.set() # Ferma il ciclo e sblocca la wait()
            
            if self.catalog_thread.is_alive():
                self.catalog_thread.join(timeout=2)
            print("[SISTEMA] Servizio arrestato correttamente.")