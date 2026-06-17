import cherrypy
import random
import json
import time
import requests
import threading
from SW.Lab1.CatalogClient import CatalogClient
from pathlib import Path

#TODO controllare

class SmartHomeSensorService(object):


    ### INIZIALIZZAZIONE ###


    exposed = True
    
    # Variabile di classe per memorizzare l'URL del server di log
    url_log = None # Inizializzata nel'init

    # Variabili di classe per memorizzare le informazioni del servizio da registrare sul Catalog
    service_id = "smart-home-sensor-service"
    service_description = "Servizio che espone le letture dei sensori della smart home"
    service_endpoint = None # Inizializzata nel'init
    service_resources = ["temperature", "humidity", "motion_sensor"]

    # Variabili di classe per memorizzare l'URL del Catalog e l'intervallo di refresh
    url_catalog = None # Inizializzata nel'init
    refresh_interval = 60 # secondi tra un refresh e il successivo

    ## Funzione per inizializzare la classe, carica le configurazioni da file, inizializza i sensori e registra il servizio sul Catalog
    def __init__(self):

        # Inizializzazione dei sensori per ogni stanza, con valori iniziali a None
        self.rooms_sens = {
            "living_room": {
                "temperature":  None,
                "humidity":     None,
                "motion_sensor": None,
            },
            "kitchen": {
                "temperature":  None,
                "humidity":     None,
                "motion_sensor": None,
            },
            "bedroom": {
                "temperature":  None,
                "humidity":     None,
                "motion_sensor": None,
            },
        }

        # Dizionario per mappare i tipi di sensori alle loro unità di misura
        self.units = {
            "temperature": "Cel",
            "humidity": "%RH",
            "motion_sensor": "bool"
        }

        # Inizializzazione dei sensori con valori random
        self.InitSens()

        # Carico il file contenente gli uri
        uri_path = Path(__file__).parent / "config-uri-client.json"
        
        # Leggo le configurazioni dal file JSON; se il file non esiste, uso valori di default
        try:
            with open(uri_path, "r") as f:
                config = json.load(f)
            self.server_address = config.get("server_address", "0.0.0.0")
            self.server_port = config.get("server_port", "9090")
            self.url_log = config.get("url_log", "http://127.0.0.1:9092/log/")
            self.url_catalog = config.get("url_catalog", "http://localhost:9093/catalog/")

        except FileNotFoundError:
            self.url_log = "http://127.0.0.1:9092/log/"
            self.url_catalog = "http://localhost:9093/catalog/"
            self.server_address = "0.0.0.0"
            self.server_port = "9090"
        
        # Creo l'endpoint del servizio combinando l'indirizzo e la porta del server
        self.service_endpoint = f"{self.server_address}:{self.server_port}/sensors"

        # Inizializzo il client per interagire con il Catalog
        self._catalog_client = CatalogClient(self.url_catalog)

        # Registrazione iniziale del servizio sul Catalog. Se la registrazione fallisce, il servizio continuerà a funzionare, ma verrà riprovata al prossimo ciclo di refresh.
        self._register_on_catalog()

        # Avvio del thread di refresh periodico che chiama _refresh_loop() ogni refresh_interval secondi.
        self._refresh_thread = threading.Thread(
            target=self._refresh_loop,
            daemon=True, # Il thread si fermerà automaticamente quando il processo principale termina
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
                print(f"[GestioneCatalog] WARNING: refresh di '{self.service_id}' non riuscito. Verrà riprovato al prossimo ciclo. - Status code: {result}")


    ### GESTIONE DELLE RICHIESTE REST ###

    ## Funzione che gestisce le richieste GET, in base alla presenza o meno di parametri e alla loro tipologia (URI o query parameters) decide quale funzione chiamare per ottenere i dati richiesti
    def GET(self, *uri, **params):
        # ESERCIZIO 1
        if(len(uri) == 0 and len(params) != 0):
            keys = list(params.keys())
            if (len(keys) == 1 and keys[0] == "room"):
                response = self.get_room(params["room"])
            elif (len(keys) == 2 and keys[0] == "room" and keys[1] == "sens"):
                response = self.get_room_sens(params["room"], params["sens"])
            else:
                raise cherrypy.HTTPError(400, "Bad request: Invalid query parameters. Valid parameters are 'room' and 'sens'. Example: ?room=living_room&sens=temperature")

        # ESERCIZIO 2
        elif(len(params) == 0):
            if(len(params) == 0 and len(uri)==0):
                response = self.get_allSens()
            elif(len(uri)==1):
                response = self.get_room(uri[0])
            elif(len(uri)==2):
                response = self.get_room_sens(uri[0], uri[1])
            else:
                raise cherrypy.HTTPError(400, "Bad request: Invalid URI format. Valid formats are /sensors/, /sensors/{room}, /sensors/{room}/{sens}. Example: /sensors/living_room/temperature")

        return json.dumps(response).encode("utf-8")


    ### UTILITIES ###

    ## Funzione per inizializzare i sensori con valori random, utile per la simulazione
    def InitSens(self):
        for room in self.rooms_sens.values():
            for sens in room.keys():
                if(sens == "temperature"):
                    room[sens] = round(random.uniform(10, 30), 2)
                elif(sens == "motion_sensor"):
                    room[sens] = random.choice([True, False])
                elif(sens == "humidity"):
                    room[sens] = round(random.uniform(10, 90), 2)
   
    ## Funzione che invia un log al server di log, in caso di fallimento dell'invio del log, restituisce un errore 500 al client che ha effettuato la richiesta GET, in questo modo si ha la certezza che se il client riceve una risposta positiva, il log è stato salvato correttamente nel server di log
    def send_log(self, room, sensor, value):
        timestamp = time.time()
        payload = {
            "bn": room + '/' + sensor + '/',
            "bt": timestamp,
            "e": [
                {
                    "n": "reading",
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
    def get_allSens(self):
        response = []
        for room in self.rooms_sens:
            response.append(self.get_room(room))
        
        return response
    
    ## Funzione per ottenere tutti i sensori di una stanza, utile per il GET con un parametro (nome stanza)
    def get_room(self, room):
        if(room not in self.rooms_sens):
            raise cherrypy.HTTPError(404, json.dumps({"error": "room not found", "available_rooms": list(self.rooms_sens.keys())}))
        
        timestamp = time.time()   
        elem = []
        
        # Creazione del pacchetto SenML con tutti i sensori della stanza
        for sens in self.rooms_sens[room]:
            elem.append(
                {
                    "n": sens,
                    "v": self.rooms_sens[room][sens],
                    "u": self.units.get(sens, None)
                }
            )
            self.send_log(room, sens, self.rooms_sens[room][sens])
        
        response = {
            "bn": room + '/',
            "bt": timestamp,
            "e": elem
        }

        return response
    
    # Funzione per ottenere il valore di un sensore specifico in una stanza specifica, utile per il GET con due parametri (nome stanza e nome sensore)
    def get_room_sens(self, room, sens):
        if(room not in self.rooms_sens):
            raise cherrypy.HTTPError(404, json.dumps({"error": "room not found", "available_rooms": list(self.rooms_sens.keys())}))

        if(sens not in self.rooms_sens[room]):
            raise cherrypy.HTTPError(400, json.dumps({"error": "unknown sensor type", "valid_types": list(self.rooms_sens[room].keys())}))

        timestamp = time.time()

        response = {
            "bn": room + '/',
            "bt": timestamp,
            "e": [
                {
                    "n": sens,
                    "v": self.rooms_sens[room][sens],
                    "u": self.units.get(sens, None)
                }
            ]
        }
        self.send_log(room, sens, self.rooms_sens[room][sens])
        return response