import cherrypy
import random
import json
import time
from pathlib import Path
import threading
import requests
from SW.Lab1.CatalogClient import CatalogClient

#TODO mettere il json con IP anche per il catalog
#TODO modificare da CLAUDE e rivedere commenti

class SmartHomeActuatorService(object):


    ### INIZIALIZZAZIONE ###


    exposed = True

    # Variabile di classe per memorizzare l'URL del server di log
    url_log = None # Viene inizializzata nel costruttore

    # Variabili di classe per memorizzare le informazioni del servizio da registrare sul Catalog
    service_id = "smart-home-actuator-service"
    service_description = "Servizio REST che espone il controllo degli attuatori della smart home (termostato, luci, tapparelle)"
    service_endpoint = None # Viene inizializzata nel costruttore in base alla configurazione del server
    service_resources = ["thermostat", "lights", "blinds"]

    # Variabili di classe per memorizzare l'URL del Catalog e l'intervallo di refresh
    url_catalog = None # Viene inizializzata nel costruttore
    refresh_interval = 60   # secondi tra un refresh e il successivo (come da specifica Es06)

    ## Funzione per inizializzare la classe
    def __init__(self):
        self.rooms_act = {
            "living_room": {
                "thermostat": None,
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

        self.units = {
            "thermostat": "Cel",
            "lights": "bool",
            "blinds": "pct"
        }

        self.InitAct()

        # Carico il file contenente gli uri
        uri_path = Path(__file__).parent / "config-uri-client.json"
        
        # Leggo le configurazioni dal file JSON; se il file non esiste, uso valori di default
        try:
            with open(uri_path, "r") as f:
                config = json.load(f)
            self.server_address = config.get("server_address", "0.0.0.0")
            self.server_port = config.get("server_port", "9091")
            self.url_log = config.get("url_log", "http://127.0.0.1:9092/log/")
            self.url_catalog = config.get("url_catalog", "http://localhost:9093/catalog/")

        except FileNotFoundError:
            self.url_log = "http://127.0.0.1:9092/log/"
            self.url_catalog = "http://localhost:9093/catalog/"
            self.server_address = "0.0.0.0"
            self.server_port = "9091"
        
        # Creo l'endpoint del servizio combinando l'indirizzo e la porta del server
        self.service_endpoint = f"{self.server_address}:{self.server_port}/actuators"


        # Inizializzo il client per interagire con il Catalog
        self._catalog_client = CatalogClient(self.url_catalog)

        # Registrazione iniziale del servizio sul Catalog. Se la registrazione fallisce, il servizio continuerà a funzionare, ma verrà riprovata al prossimo ciclo di refresh.
        self._register_on_catalog()

        # Avvio del thread di refresh periodico che chiama _refresh_loop() ogni refresh_interval secondi.
        self._refresh_thread = threading.Thread(
            target=self._refresh_loop,
            daemon=True,
            name="CatalogRefreshThread"
        )
        self._refresh_thread.start()


    ### GESTIONE DEL CATALOG ###


    ## Funzione privata per registrare il servizio sul Catalog. Se la registrazione fallisce, verrà riprovata al prossimo ciclo di refresh.
    def _register_on_catalog(self):
        payload = {
            "id":          self.service_id,
            "description": self.service_description,
            "endpoint":    self.service_endpoint,
            "resources":   self.service_resources,
        }
        result = self._catalog_client.register_service(payload)
        if not isinstance(result, int):  # Se il risultato non è un codice di errore, consideriamo la registrazione riuscita
            print(f"[GestioneCatalog] Servizio '{self.service_id}' registrato sul Catalog: {result}")
        else:
            print(f"[GestioneCatalog] WARNING: registrazione di '{self.service_id}' non riuscita. Verrà riprovata al prossimo ciclo. - Status code: {result}")
            time.sleep(self.refresh_interval)
            self._register_on_catalog()  # Riprova la registrazione al prossimo ciclo

    ## Funzione privata che esegue un ciclo infinito di refresh del servizio sul Catalog ogni refresh_interval secondi. Se il refresh fallisce, verrà riprovato al prossimo ciclo.
    def _refresh_loop(self):
        while True:
            time.sleep(self.refresh_interval)
            result = self._catalog_client.refresh_service(self.service_id)
            if not isinstance(result, int):  # Se il risultato non è un codice di errore, consideriamo il refresh riuscito
                print(f"[GestioneCatalog] Refresh di '{self.service_id}' eseguito con successo: {result}")
            else:
                print(f"[GestioneCatalog] WARNING: refresh di '{self.service_id}' non riuscito. Verrà riprovato al prossimo ciclo.")


    ### GESTIONE DELLE RICHIESTE REST ###


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


    ### UTILITIES ###

    
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