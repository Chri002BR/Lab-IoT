import paho.mqtt.client as mqtt
import threading, time, json, cherrypy, os
import SW.Lab1.server_Catalog.Es07 as Es07

#TODO: Da rivedere punto 3 campi opzionali degli endpoint e MQTT (ip,...) (non dovrebbero essere gestiti da qui, ma solo salvati nel Json)
# PERCHE' NO ???????????????? NO NBASTA RENDERE PIù STRINGENTE IL CONTROLLO DEL BODY?????????????????
#TODO: modificare da AI (COMMENTI, OUTPUT, IL CODICE E' DIFFICILMENTE LEGGIBILE)

    # Catalogo di default
DEFAULT_CATALOG = {
    "broker": {
        "ip":   "broker.hivemq.com",
        "port": 1883
    },
    "devices":  [],
    "services": []
}

    # Costanti per la gestione del file di persistenza e della pulizia delle entry scadute
CATALOG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "catalog.json")
CLEANUP_INTERVAL = 60    # seconds between each cleanup pass
STALE_THRESHOLD  = 120   # seconds before a registration is considered stale

class Catalog(object):


    ### INIZIALIZZAZIONE ###


    exposed = True

    def __init__(self):
        self._lock = threading.Lock() # Lock per la persistenza (da chiamare prima di fare accessi al file). Serve a evitare che due thread (es. main thread + cleanup thread) accedano contemporaneamente al file causando corruzione dei dati o eccezioni.
        self._data = self._load()

        # Thread per la pulizia delle entry scadute
        threading.Thread(target=self._cleanup_loop, daemon=True).start()
        print("[Catalog] Inizializzato. In ascolto su /catalog ...")

        # Inizializziamo il bridge MQTT passando le informazioni del broker (che possono essere caricate da catalog.json o usare quelle di default)
        broker_info = self._data.get("broker", DEFAULT_CATALOG["broker"])
        broker_host = broker_info["ip"]
        broker_port = broker_info["port"]

        # Istanziamo il Bridge passando 'self' (questa istanza di Catalog)
        self.mqtt_bridge = Es07.MQTTCatalogBridge(
            catalog=self, 
            broker_host=broker_host, 
            broker_port=broker_port
        )
        # Avviamo il bridge (che farà partire internamente il secondo Thread tramite loop_start())
        self.mqtt_bridge.start()


    ### GESTIONE PERSISTENZA ###


    ## Funzione privata che carica il catalogo da disco (catalog.json) o restituisce la struttura di default se il file non esiste
    def _load(self):
        if os.path.exists(CATALOG_FILE):
            with open(CATALOG_FILE, "r") as f:
                data = json.load(f)
            print(f"[Catalog] Caricato {CATALOG_FILE} da disco.")
            return data
 
        print(f"[Catalog] {CATALOG_FILE} non trovato, inizializzato con il catalogo di default.")
        return json.loads(json.dumps(DEFAULT_CATALOG))  

    ## Funzione privata che salva il catalogo su disco (catalog.json)
    def _save(self):
        with open(CATALOG_FILE, "w") as f:
            json.dump(self._data, f, indent=2)


    ### GESTIONE THREAD ###


    ## Funzione privata che rimuove le entry scadute dal catalogo. Viene eseguita ogni CLEANUP_INTERVAL secondi su un thread separato
    def _cleanup_loop(self):
        while True:
            time.sleep(CLEANUP_INTERVAL)
            now = time.time()
 
            with self._lock:
                for section in ("devices", "services"):
                    before = len(self._data[section])
 
                    self._data[section] = [
                        entry for entry in self._data[section]
                        if (now - entry.get("insert_timestamp", 0)) < STALE_THRESHOLD
                    ]
 
                    removed = before - len(self._data[section])
                    if removed:
                        print(f"[Cleanup] Removed {removed} stale entry/entries from '{section}'.")
 
                self._save()


    ### UTILITIES ###


    ## Funzione statica che converte un dizionario Python in una JSON response
    @staticmethod
    def _json_response(data, status=200):
        return json.dumps(data).encode("utf-8")

    ## Funzione privata che cerca un entry per id in una sezione (devices o services) e la restituisce, oppure None se non trovata
    def _find(self, section, item_id):
        return next(
            (x for x in self._data[section] if x["id"] == item_id), None
        )


    ### GESTIONE DELLE RICHIESTE REST ###

 
    ## Funzione che gestisce le richieste GET
    def GET(self, *uri, **params):
        # Pattern URI:
        #   GET /catalog -> ritorna l'intero catalogo (broker, devices, services)
        #   GET /catalog/broker -> ritorna le informazioni del broker
        #   GET /catalog/devices -> ritorna la lista di tutti i devices
        #   GET /catalog/devices/<id> -> ritorna un singolo device
        #   GET /catalog/services -> ritorna la lista di tutti i services
        #   GET /catalog/services/<id> -> ritorna un singolo service

        with self._lock:
            # Snapshot so we release the lock quickly
            data = json.loads(json.dumps(self._data))
 
        # /catalog
        if len(uri) == 0:
            return self._json_response(data)
 
        section = uri[0]  # "broker" | "devices" | "services"
 
        # /catalog/broker
        if section == "broker":
            return self._json_response(data["broker"])
 
        # /catalog/devices  or  /catalog/services
        if section in ("devices", "services"):
            if len(uri) == 1:
                return self._json_response(data[section])
 
            # /catalog/devices/<id>  or  /catalog/services/<id>
            item_id = uri[1]
            item = next((x for x in data[section] if x["id"] == item_id), None)
            if item is None:
                raise cherrypy.HTTPError(404, f"error: '{item_id}' not found in {section}")
            
            return self._json_response(item)
 
        raise cherrypy.HTTPError(404, f"error: Unknown section '{section}'")
 
    ## Funzione che gestisce le richieste POST
    def POST(self, *uri, **params):
        """ esempio body JSON:
          {
            "id": "sensor-01",
            "description": "Living room temperature sensor",
            "endpoint": "http://localhost:9090/sensors", #OPZIONALE
            "mqtt": { # OPZIONALE
                "ip": "broker.hivemq.com",
                "port": 1883,
                "topic": "/tiot/group14/living_room/temperature"
                },
            "resources": ["temperature", "humidity"]
          }
        """

        if len(uri) < 1 or uri[0] not in ("devices", "services"):
            raise cherrypy.HTTPError(400, f"error: Use /catalog/devices or /catalog/services")
 
        section = uri[0]
 
        # Parse request body
        try:
            body = json.loads(cherrypy.request.body.read().decode("utf-8"))
        except (json.JSONDecodeError, ValueError) as e:
            raise cherrypy.HTTPError(400, f"error: Invalid JSON: {e}")


        if "id" not in body:        # Verifica che i campi obbligatori siano presenti
            raise cherrypy.HTTPError(400, f"error: Field 'id' is required")
        if "description" not in body:
            raise cherrypy.HTTPError(400, f"error: Field 'description' is required")
        if "resources" not in body:
            raise cherrypy.HTTPError(400, f"error: Field 'resources' is required")
 
        # Catalog always controls the timestamp
        body["insert_timestamp"] = time.time()
 
        with self._lock:
            existing = self._find(section, body["id"])
 
            if existing is not None:
                # Already registered: just refresh the timestamp
                existing["insert_timestamp"] = body["insert_timestamp"]
                self._save()
                print(f"[POST] Refreshed {section[:-1]} '{body['id']}'")
                return self._json_response({"status": "refreshed", "id": body["id"]})
            else:
                # New entry: add it
                self._data[section].append(body)
                self._save()
                print(f"[POST] Registered new {section[:-1]} '{body['id']}'")
                return self._json_response(
                    {"status": "registered", "id": body["id"]}, 201
                )
 
    ## Funzione che gestisce le richieste PUT. Esegue il refresh del timestamp di un device o service esistente
    def PUT(self, *uri, **params):
        if len(uri) < 2:
            raise cherrypy.HTTPError(400, f"error: Use /catalog/devices/<id> or /catalog/services/<id>")
 
        section = uri[0]
        item_id = uri[1]
 
        if section not in ("devices", "services"):
            raise cherrypy.HTTPError(400, f"error: Unknown section '{section}'")
 
        with self._lock:
            item = self._find(section, item_id)
            if item is None:
                raise cherrypy.HTTPError(404, f"error: '{item_id}' not found in {section}")
            
            item["insert_timestamp"] = time.time()
            self._save()
 
        print(f"[PUT] Refreshed {section[:-1]} '{item_id}'")
        return self._json_response({"status": "refreshed", "id": item_id})
 
    ##   ## Funzione che gestisce le richieste DELETE. Rimuove un device o service esistente
    def DELETE(self, *uri, **params):
        if len(uri) < 2:
            raise cherrypy.HTTPError(400, f"error: Use /catalog/devices/<id> or /catalog/services/<id>")
        
 
        section, item_id = uri[0], uri[1]
 
        if section not in ("devices", "services"):
            raise cherrypy.HTTPError(400, f"error: Unknown section '{section}'")
 
        with self._lock:
            before = len(self._data[section])
            self._data[section] = [     # Scorre la lista mantenendo solo gli elementi con id diverso
                x for x in self._data[section] if x["id"] != item_id
            ]
            if len(self._data[section]) == before:
                raise cherrypy.HTTPError(404, f"error: '{item_id}' not found in {section}")
            
            self._save()
 
        print(f"[DELETE] Removed {section[:-1]} '{item_id}'")
        return self._json_response({"status": "deleted", "id": item_id})