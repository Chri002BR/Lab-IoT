import cherrypy
import random
import json
import time
from datetime import datetime, timezone
import threading  # MODIFICATO DA CLAUDE: aggiunto import threading per il thread di refresh periodico (Es06 - Requisito 4)

import requests
from SW.Lab1.CatalogClient import CatalogClient
#from SW.Lab1.Clients.Es06.Es06 import CatalogClient  # MODIFICATO DA CLAUDE: import di CatalogClient da Es06 per registrazione e refresh sul Catalog (Es06 - Requisiti 3 e 4)

#TODO mettere il json con IP anche per il catalog

class SmartHomeActuatorService(object):
    exposed = True
    
    url_log = "http://127.0.0.1:9092/log/"

    units = {
        "thermostat": "Cel",
        "lights": "bool",
        "blinds": "pct"
    }

    # MODIFICATO DA CLAUDE: aggiunte costanti di classe per identificare il servizio nel Catalog
    # e centralizzare la configurazione (Es06 - Requisito 3)
    SERVICE_ID          = "smart-home-actuator-service"
    SERVICE_DESCRIPTION = "Servizio REST che espone il controllo degli attuatori della smart home (termostato, luci, tapparelle)"
    SERVICE_ENDPOINT    = "http://localhost:8083/actuators"
    SERVICE_RESOURCES   = ["thermostat", "lights", "blinds"]

    # MODIFICATO DA CLAUDE: aggiunte costanti per indirizzo Catalog e intervallo di refresh (Es06 - Requisito 4)
    CATALOG_ADDRESS  = "http://localhost:9093"
    REFRESH_INTERVAL = 60   # secondi tra un refresh e il successivo (come da specifica Es06)

    ## Funzione per inizializzare la classe, utile per la simulazione, in questo modo i sensori hanno già dei valori random al primo avvio del server
    def __init__(self):
        self.rooms_act = {                          # MODIFICATO DA CLAUDE: spostato da attributo di classe
            "living_room": {                        # ad attributo di istanza per evitare condivisione
                "thermostat": None,                 # involontaria dello stato tra istanze (buona pratica OOP)
                "lights":     None,
                "blinds":     None,
            },
            "kitchen": {
                "thermostat": None,
                "lights":     None,
                "blinds":     None,
            },
            "bedroom": {
                "thermostat": None,
                "lights":     None,
                "blinds":     None,
            },
        }

        self.InitAct()

        # Leggo l'URI dal file di config
        uri_path = Path(__file__).parent / "config-uri-client.json"

        try:
            with open(uri_path, "r") as f:
                config = json.load(f)
            self.url_log = config.get("url_log", "http://127.0.0.1:9092/log/")
        except FileNotFoundError:
            self.url_log = "http://127.0.0.1:9092/log/"

        # MODIFICATO DA CLAUDE: creazione dell'istanza di CatalogClient per registrazione e refresh (Es06 - Requisito 3)
        self._catalog_client = CatalogClient(self.CATALOG_ADDRESS)

        # MODIFICATO DA CLAUDE: registrazione del servizio al Catalog all'avvio.
        # Se il Catalog non è raggiungibile il servizio parte comunque; il thread riproverà al ciclo successivo. (Es06 - Requisiti 3 e 5)
        self._register_on_catalog()

        # MODIFICATO DA CLAUDE: avvio del thread daemon di refresh periodico.
        # daemon=True garantisce che il thread si fermi automaticamente alla chiusura del processo. (Es06 - Requisito 4)
        self._refresh_thread = threading.Thread(
            target=self._refresh_loop,
            daemon=True,
            name="CatalogRefreshThread"
        )
        self._refresh_thread.start()

    # ── CATALOG HELPERS ──────────────────────────────────────────────────────

    # MODIFICATO DA CLAUDE: nuovo metodo privato che costruisce il payload e chiama
    # CatalogClient.register_service() all'avvio, centralizzando la logica di registrazione. (Es06 - Requisito 3)
    def _register_on_catalog(self):
        payload = {
            "id":          self.SERVICE_ID,
            "description": self.SERVICE_DESCRIPTION,
            "endpoint":    self.SERVICE_ENDPOINT,
            "resources":   self.SERVICE_RESOURCES,
        }
        result = self._catalog_client.register_service(payload)
        if not isinstance(result, int):  # Se il risultato non è un codice di errore, consideriamo la registrazione riuscita
            print(f"[CatalogClient] Servizio '{self.SERVICE_ID}' registrato sul Catalog: {result}")
        else:
            print(f"[CatalogClient] WARNING: registrazione di '{self.SERVICE_ID}' non riuscita. Verrà riprovata al prossimo ciclo. - Status code: {result}")
            time.sleep(self.REFRESH_INTERVAL)
            self._register_on_catalog()  # Riprova la registrazione al prossimo ciclo

    # MODIFICATO DA CLAUDE: nuovo metodo privato che gira in loop e chiama
    # CatalogClient.refresh_service() ogni REFRESH_INTERVAL secondi.
    # In caso di errore viene stampato un warning e il thread continua senza interrompersi. (Es06 - Requisiti 4 e 5)
    def _refresh_loop(self):
        while True:
            time.sleep(self.REFRESH_INTERVAL)
            result = self._catalog_client.refresh_service(self.SERVICE_ID)
            if not isinstance(result, int):  # Se il risultato non è un codice di errore, consideriamo il refresh riuscito
                print(f"[CatalogClient] Refresh di '{self.SERVICE_ID}' eseguito con successo: {result}")
            else:
                print(f"[CatalogClient] WARNING: refresh di '{self.SERVICE_ID}' non riuscito. Verrà riprovato al prossimo ciclo.")

    # ── REST HANDLERS ────────────────────────────────────────────────────────

    ## Funzione che gestisce le richieste GET, in base alla presenza o meno di parametri e alla loro tipologia (URI o query parameters) decide quale funzione chiamare per ottenere i dati richiesti  
    def GET(self, *uri, **params):
        if(len(uri) == 0 and len(params) != 0):
            keys = list(params.keys())
            if (len(keys) == 1 and keys[0] == "room"):
                response = self.get_room(params["room"])
            elif (len(keys) == 2 and keys[0] == "room" and keys[1] == "act"):
                response = self.get_room_act(params["room"], params["act"])
            else:
                raise cherrypy.HTTPError(400, "Bad request: Invalid query parameters. Valid parameters are 'room' and 'act'. Example: ?room=living_room&act=thermostat")

        elif(len(params) == 0):
            if(len(params) == 0 and len(uri)==0):
                response = self.get_allAct()
            elif(len(uri)==1):
                response = self.get_room(uri[0])
            elif(len(uri)==2):
                response = self.get_room_act(uri[0], uri[1])
            else:
                raise cherrypy.HTTPError(400, "Bad request: Invalid URI format. Valid formats are /actuators/, /actuators/{room}, /actuators/{room}/{act}. Example: /actuators/living_room/thermostat")

        return json.dumps(response).encode("utf-8")
    
    #STRUTTURA DEL BODY DA INVIARE PER AGGIORNARE UN ATTUATORE: 
    #{
    #    "bn": "kitchen/",
    #    "e": [
    #        {
    #        "n": "lights",
    #        "v": True,
    #        "u": "bool"
    #        }
    #    ]
    #}
    
    ## Funzione che gestisce le richieste PUT, si aspetta un body in formato JSON con i campi bn (base name), e (array di elementi) dove ogni elemento deve contenere i campi n (name), v (value) e u (unit). In base al contenuto del body aggiorna il valore dell'attuatore specificato e aggiunge un log della modifica effettuata
    def PUT(self, *uri, **params):
        
        # Controllo che il Content-Type sia application/json, altrimenti ritorna un errore 415 Unsupported Media Type
        if cherrypy.request.headers.get("Content-Type", "") != "application/json":
            raise cherrypy.HTTPError(415, "Bad request: Content-Type must be application/json")
        
        if(len(uri) == 0):
            raw = cherrypy.request.body.read()
            
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
            
            room = body["bn"].rstrip('/')  # Rimuove eventuale slash finale
            sensor = body["e"][0]["n"]
            value = body["e"][0]["v"]
            
            # Controllo che la stanza e il sensore esistano, altrimenti ritorna un errore 404 Not Found
            # Controllo che il valore sia corretto (es. se è un termostato deve essere compreso tra 10 e 30, se sono le luci deve essere on o off, se sono le tapparelle deve essere compreso tra 0 e 100), altrimenti ritorna un errore 400 Bad Request
             
            if room not in self.rooms_act:
                raise cherrypy.HTTPError(404, "Room not found")
            
            if sensor not in self.rooms_act[room]:
                raise cherrypy.HTTPError(404, "Sensor not found in this room")
                
            # Controllo correttezza value (se in range)
             
            if sensor == "thermostat":
                if value < 10 or value > 30:
                    raise cherrypy.HTTPError(400, "Bad request: Value out of range for thermostat (10-30)")
            elif sensor == "lights":
                if value != True and value != False:
                    raise cherrypy.HTTPError(400, "Bad request: Value for lights must be True or False")
            elif sensor == "blinds":
                if value < 0 or value > 100:
                    raise cherrypy.HTTPError(400, "Bad request: Value out of range for blinds (0-100)")

            self.rooms_act[room][sensor] = value
            # Aggiunta del Json nel log
            self.send_log(room, sensor, value)

            return json.dumps(self.get_room_act(room, sensor)).encode("utf-8")

    ## Funzione per inizializzare gli attuatori con valori random, utile per la simulazione
    def InitAct(self):
        for room in self.rooms_act.values():
            for sens in room.keys():
                if(sens == "temperature" or sens == "humidity"):
                    room[sens] = random.uniform(10, 40)
                elif(sens == "motion_sensor"):
                    room[sens] = random.choice([True, False])
    
    ## funzione per inviare un log al server di log, in caso di fallimento dell'invio ritorna un errore 500 Internal Server Error; il log contiene la stanza, il sensore, il nuovo valore e l'unità di misura
    def send_log(self, room, sensor, value):
        timestamp = time.time()
        payload = {
            "bn": room + '/' + sensor + '/',
            "bt": timestamp,
            "e": [
                {
                    "n": "status",
                    "v": value,
                    "u": self.units.get(sensor, None)
                }
            ]
        }

        # Invia il log al server di log via POST; se fallisce, lo salva localmente
        try:
            resp = requests.post(self.url_log, json=payload, headers={"Content-Type": "application/json"}, timeout=5)
            if resp.status_code not in (200, 201):
                raise cherrypy.HTTPError(404, json.dumps({"error": "Failed to send log to log server, status code: " + str(resp.status_code)}))

        except Exception:
            raise cherrypy.HTTPError(500, json.dumps({"error": "Failed to send log"}))

    ## Funzione per ottenere tutti i sensori di tutte le stanze, utile per il GET senza parametri    
    def get_allAct(self):
        response = []
        for room in self.rooms_act:
            response.append(self.get_room(room))
        
        return response
    
    ## Funzione per ottenere tutti i sensori di una stanza, utile per il GET con un parametro (nome stanza)
    def get_room(self, room):
        if(room not in self.rooms_act):
            raise cherrypy.HTTPError(404, json.dumps({"error": "room not found", "available_rooms": list(self.rooms_act.keys())}))
        
        timestamp = time.time()   
        elem = []
        
        # Creazione del pacchetto SenML con tutti i sensori della stanza
        for sens in self.rooms_act[room]:
            elem.append(
                {
                    "n": sens,
                    "v": self.rooms_act[room][sens],
                    "u": self.units.get(sens, None)
                }
            )
        
        response = {
            "bn": room + '/',
            "bt": timestamp,
            "e": elem
        }

        return response
    
    # Funzione per ottenere il valore di un sensore specifico in una stanza specifica, utile per il GET con due parametri (nome stanza e nome sensore)
    def get_room_act(self, room, sens):
        if(room not in self.rooms_act):
            raise cherrypy.HTTPError(404, json.dumps({"error": "room not found", "available_rooms": list(self.rooms_act.keys())}))

        if(sens not in self.rooms_act[room]):
            raise cherrypy.HTTPError(400, json.dumps({"error": "unknown actuator type", "valid_types": list(self.rooms_act[room].keys())}))

        timestamp = time.time()

        response = {
            "bn": room + '/',
            "bt": timestamp,
            "e": [
                {
                    "n": sens,
                    "v": self.rooms_act[room][sens],
                    "u": self.units.get(sens, None)
                }
            ]
        }
        return response


# ── AVVIO DEL SERVER CHERRYPY ────────────────────────────────────────────────
if __name__ == "__main__":
    conf = {
        "/": {
            "request.dispatch": cherrypy.dispatch.MethodDispatcher(),
            "tools.response_headers.on": True,
            "tools.response_headers.headers": [("Content-Type", "application/json")],
        }
    }
    cherrypy.tree.mount(SmartHomeActuatorService(), "/actuators", conf)
    cherrypy.config.update({"server.socket_port": 8083})
    cherrypy.engine.start()
    cherrypy.engine.block()