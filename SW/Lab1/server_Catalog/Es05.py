import paho.mqtt.client as mqtt
import threading, time, json, cherrypy, os

import SW.Lab1.server_Catalog.Es07 as Es07

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CATALOG_FILE = os.path.join(SCRIPT_DIR, "catalog.json")
CLEANUP_INTERVAL = 60    # seconds between each cleanup pass
STALE_THRESHOLD  = 120   # seconds before a registration is considered stale


# Da rivedere punto 3 campi opzionali degli endpoint e MQTT (ip,...) (non dovrebbero essere gestiti da qui, ma solo salvati nel Json)
#TODO: modificare da AI (commenti generati)

# ── Default catalog structure (used when catalog.json does not exist) ────────

DEFAULT_CATALOG = {
    "broker": {
        "ip":   "broker.hivemq.com",
        "port": 1883
    },
    "devices":  [],
    "services": []
}



class Catalog(object):
    exposed = True  # required for MethodDispatcher

    def __init__(self):
        # threading.Lock protects _data and catalog.json from concurrent access
        self._lock = threading.Lock()   # Lock per la persistenza (da chiamare prima di fare accessi al file)
        self._data = self._load()

        # Background cleanup thread (daemon=True so it dies with the process)
        threading.Thread(target=self._cleanup_loop, daemon=True).start()
        print("[Catalog] Started. Listening on http://localhost:9093/catalog")

        # per far partire il bridge con questa classe
        broker_info = self._data.get("broker", {"ip": "broker.hivemq.com", "port": 1883})
        broker_host = "broker.hivemq.com"
        broker_port = 1883

        # Istanziamo il Bridge passando 'self' (questa istanza di Catalog)
        self.mqtt_bridge = Es07.MQTTCatalogBridge(
            catalog=self, 
            broker_host=broker_host, 
            broker_port=broker_port
        )
        # Avviamo il bridge (che farà partire internamente il secondo Thread tramite loop_start())
        self.mqtt_bridge.start()

    # ── Persistence helpers ──────────────────────────────────────────────────
 
    def _load(self):
        """
        Load catalog.json from disk.
        If the file does not exist, return the default structure.
        """
        if os.path.exists(CATALOG_FILE):
            with open(CATALOG_FILE, "r") as f:
                data = json.load(f)
            print(f"[Catalog] Loaded {CATALOG_FILE} from disk.")
            return data
 
        print(f"[Catalog] {CATALOG_FILE} not found, starting with empty catalog.")
        return json.loads(json.dumps(DEFAULT_CATALOG))  

    def _save(self):
        """
        Write the current state to catalog.json.
        Must always be called while self._lock is held.
        """
        with open(CATALOG_FILE, "w") as f:
            json.dump(self._data, f, indent=2)

    # ── Cleanup thread ───────────────────────────────────────────────────────
 
    def _cleanup_loop(self):
        """
        Runs every CLEANUP_INTERVAL seconds.
        Removes devices and services whose insert_timestamp is older than
        STALE_THRESHOLD seconds (i.e. they missed their periodic refresh).
        """
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

    # ── Internal helpers ─────────────────────────────────────────────────────
 
    @staticmethod
    def _json_response(data, status=200):
        """Return JSON string."""
        return json.dumps(data).encode("utf-8")
 
    def _find(self, section, item_id):
        """Return the entry with the given id in section, or None."""
        return next(
            (x for x in self._data[section] if x["id"] == item_id),
            None
        )
    

    # ── GET ──────────────────────────────────────────────────────────────────
 
    def GET(self, *uri, **params):
        """
        URI patterns:
          GET /catalog                -> full catalog (broker + devices + services)
          GET /catalog/broker         -> MQTT broker info
          GET /catalog/devices        -> list of all devices
          GET /catalog/devices/<id>   -> single device
          GET /catalog/services       -> list of all services
          GET /catalog/services/<id>  -> single service
        """
        with self._lock:
            # Snapshot so we release the lock quickly
            data = json.loads(json.dumps(self._data))
 
        # /catalog  (no extra segments)
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
    
    # ── POST ─────────────────────────────────────────────────────────────────
 
    def POST(self, *uri, **params):
        """
        Register (or refresh) a device or service.
        URI: POST /catalog/devices  or  POST /catalog/services
 
        Body (JSON):
          {
            "id":          "sensor-01",
            "description": "Living room temperature sensor",
            "endpoint":    "http://localhost:8081/sensors",   <- optional
            "mqtt": {                                          <- optional
              "ip":    "iot.eclipse.org",
              "port":  1883,
              "topic": "/tiot/group14/living_room/temperature"
            },
            "resources": ["temperature", "humidity"]
          }
 
        Behavior:
          - If id already exists -> update insert_timestamp (refresh)
          - If id is new         -> create new record
        The insert_timestamp is always set by the Catalog, never by the client.
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
            
    # ── PUT ──────────────────────────────────────────────────────────────────
 
    def PUT(self, *uri, **params):
        """
        Refresh the insert_timestamp of an existing device or service.
        URI: PUT /catalog/devices/<id>  or  PUT /catalog/services/<id>
 
        Clients must call this every ~60 s to keep their registration alive.
        """
        if len(uri) < 2:
            raise cherrypy.HTTPError(400, f"error: Use /catalog/devices/<id> or /catalog/services/<id>")
        
 
        section, item_id = uri[0], uri[1]
 
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
 
    # ── DELETE ───────────────────────────────────────────────────────────────
 
    def DELETE(self, *uri, **params):
        """
        Remove a device or service by id.
        URI: DELETE /catalog/devices/<id>  or  DELETE /catalog/services/<id>
        """
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