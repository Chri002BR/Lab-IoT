import cherrypy
import json
import time
import threading
import requests
from pathlib import Path
#TODO: NON è IMPLEMENTATO IL REQUISITO DELL'ESERCIZIO 6, IL LOGGER NON SI CONNETTE AL CATALOG!!!!!!!!!!!!!!!!!!!!!!!!!


class SmartHomeLogService(object):


    ### INIZIALIZZAZIONE ###    


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
            
            if len(body["e"][0]) != 3:
                raise cherrypy.HTTPError(422, "Bad request: Unprocessable Entity")
            
            if "n" not in body["e"][0] or "v" not in body["e"][0] or "u" not in body["e"][0]:
                raise cherrypy.HTTPError(422, "Bad request: Unprocessable Entity")
            
            if "bt" not in body:
                timestamp = time.time()
                body = {"bt": timestamp, **body}
            else:
                body["bt"] = timestamp

            self.thread_lock(body)
            
            body = {"id": SmartHomeLogService.id, **body}
            SmartHomeLogService.id += 1
            
            self.AddLog(body)
            return json.dumps({"status": "success", "log_id": SmartHomeLogService.id - 1}).encode("utf-8")
    
    def thread_lock(self, body): #Serve a rendere thread-safe l'incremento dell'id e l'aggiunta del log alla lista dei log
        with self._lock:
                body = {"id": self.log_id_counter, **body}
                assigned_id = self.log_id_counter      
                self.log_id_counter += 1                 
                self.AddLog(body)

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
        self.cont_log = 0
        self.logs = [] #clear lista log
        self._lock = threading.Lock() #gestione thread della lista log, per non creare sovrapposizioni
        self.started=True
        config_path = Path(__file__).parent.parent / "config-uri-client.json" #localizzo il file di configurazione del catalog

        #Prendo dal file la configurazione, altrimenti imposto un valore di default
        try:
            with open(config_path, "r") as f:
                config = json.load(f)
            self.CATALOG_BASE_URL = config.get("uri_catalog", "http://localhost:9093/catalog")
        except Exception:
            self.CATALOG_BASE_URL = "http://localhost:9093/catalog"

        #Creo e avvio il thread per la registrazione e il mantenimento con il catalog
        catalog_thread = threading.Thread(target=self.register_and_keep_alive, daemon=True)
        catalog_thread.start()

    def register_and_keep_alive(self):#AGGIUNTO SU RICHIESTA ES06
        #REGISTRAZIONE
        registration_data = {
            "id": "smart-home-sensor-service",
            "description": "Implementazione keep-alive per il catalog",
            "resources": ["log", "storage"]
        }

        url_post = f"{self.CATALOG_BASE_URL}/services"
        self.registered = False #per uscire dal ciclo quando si è registrato
        t_new_tent = 5 #tempo in secondi tra un tentativo di registrazione e l'altro, se fallisce

        while self.started and not self.registered:
            try:
                print("TENTATIVO REGISTRAZIONE AL CATALOG")
                # Registrazione al catalog
                response = requests.post(url_post, json=registration_data, timeout=t_new_tent)
                if response.status_code in [200, 201]:
                    print("Registrazione effettuata")
                else:
                    print(f"Registrazionefallita [code: {response.status_code}]")

            except Exception as e:
                print(f"Errore di registrazione: {e}")

            if not self.registered:
                time.sleep(t_new_tent) #attendo  prima di effettuare un nuovo tentativo
    
        self.keep_alive()#richiamo il metodo di keep-alive dopo la registrazione per mantenerala

    def keep_alive(self):
        while self.started:
            time.sleep(60)
            if self.started:
                try:
                    print("Eseguo keep-alive")
                    requests.put(f"{self.CATALOG_BASE_URL}/services/smart-home-sensor-service/keep-alive", timeout=5)
                except Exception as e:
                    print(f"Errore keep-alive: {e}")