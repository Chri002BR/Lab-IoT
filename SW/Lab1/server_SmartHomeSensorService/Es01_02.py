import cherrypy
import random
import json
import time
import requests
import threading  # MODIFICATO DA CLAUDE: aggiunto import threading per il thread di refresh periodico (Es06 - Requisito 4)

#TODO mettere il json con IP anche per il catalog
#TODO modificare da CLAUDE e rivedere commenti

# MODIFICATO DA CLAUDE: importiamo CatalogClient da Es06 per poter registrare il servizio
# e fare il refresh periodico. (Es06 - Requisiti 3 e 4)
# NOTA: assicurarsi che Es06.py sia nella stessa directory o nel PYTHONPATH
from SW.Lab1.CatalogClient import CatalogClient #cambiato import perchè spostato

class SmartHomeSensorService(object):
    exposed = True
    
    url_log = "http://127.0.0.1:9092/log/"

    # MODIFICATO DA CLAUDE: spostati rooms_sens e units a livello di istanza (dentro __init__)
    # per evitare che siano attributi di classe condivisi tra istanze diverse. (buona pratica OOP)
    # I dizionari come attributi di classe sono condivisi tra tutte le istanze e possono causare
    # comportamenti inattesi in ambienti multi-thread o con più istanze.

    units = {
        "temperature": "Cel",
        "humidity": "%RH",
        "motion_sensor": "bool"
    }

    # MODIFICATO DA CLAUDE: aggiunto SERVICE_ID e SERVICE_DESCRIPTION come costanti di classe
    # per identificare univocamente questo servizio nel Catalog. (Es06 - Requisito 3)
    SERVICE_ID          = "smart-home-sensor-service"
    SERVICE_DESCRIPTION = "Servizio REST che espone le letture dei sensori della smart home (temperatura, umidità, movimento)"
    SERVICE_ENDPOINT    = "http://localhost:9090/sensors"   # endpoint REST di questo servizio
    SERVICE_RESOURCES   = ["temperature", "humidity", "motion_sensor"]

    # MODIFICATO DA CLAUDE: aggiunto CATALOG_ADDRESS e REFRESH_INTERVAL come costanti di classe
    # per centralizzare la configurazione del catalog e del periodo di refresh. (Es06 - Requisito 4)
    CATALOG_ADDRESS  = "http://localhost:9093"
    REFRESH_INTERVAL = 60   # secondi tra un refresh e il successivo (come da specifica Es06)

    ## Funzione per inizializzare la classe, utile per la simulazione, in questo modo i sensori hanno già dei valori random al primo avvio del server
    def __init__(self):
        self.rooms_sens = {                         # MODIFICATO DA CLAUDE: spostato da attributo di classe
            "living_room": {                        # ad attributo di istanza per evitare condivisione
                "temperature":  None,               # involontaria dello stato tra istanze. (buona pratica OOP)
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

        self.InitSens()

        # Carico il file contenente gli uri, così da prendere uri_log
        uri_path = Path(__file__).parent / "config-uri-client.json"
        
        try:
            with open(uri_path, "r") as f:
                config = json.load(f)
            self.url_log = config.get("url_log", "http://127.0.0.1:9092/log/")
        except FileNotFoundError:
            self.url_log = "http://127.0.0.1:9092/log/"

        # MODIFICATO DA CLAUDE: creazione dell'istanza di CatalogClient che verrà usata
        # per la registrazione iniziale e i refresh periodici. (Es06 - Requisito 3)
        self._catalog_client = CatalogClient(self.CATALOG_ADDRESS)

        # MODIFICATO DA CLAUDE: registrazione del servizio al Catalog al momento dell'avvio.
        # Se il Catalog non è raggiungibile il servizio parte comunque (warning stampato
        # da CatalogClient.register_service); il thread di refresh riproverà al ciclo successivo.
        # (Es06 - Requisiti 3 e 5)
        self._register_on_catalog()

        # MODIFICATO DA CLAUDE: avvio del thread daemon di refresh periodico.
        # daemon=True garantisce che il thread si fermi automaticamente quando il
        # processo principale termina, senza bisogno di join esplicito. (Es06 - Requisito 4)
        self._refresh_thread = threading.Thread(
            target=self._refresh_loop,
            daemon=True,
            name="CatalogRefreshThread"
        )
        self._refresh_thread.start()

    # ── CATALOG HELPERS ──────────────────────────────────────────────────────

    # MODIFICATO DA CLAUDE: nuovo metodo privato che costruisce il payload di registrazione
    # e lo invia al Catalog tramite CatalogClient.register_service().
    # Centralizza la logica di registrazione per evitare duplicazione di codice tra
    # __init__ e _refresh_loop. (Es06 - Requisiti 3 e 4)
    def _register_on_catalog(self):
        payload = {
            "id":          self.ScmdERVICE_ID,
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
    # In caso di errore di connessione, CatalogClient.refresh_service() logga già
    # un warning e restituisce None, quindi qui ci limitiamo a riprovare al ciclo
    # successivo senza interrompere il thread. (Es06 - Requisiti 4 e 5)
    def _refresh_loop(self):
        while True:
            time.sleep(self.REFRESH_INTERVAL)
            result = self._catalog_client.refresh_service(self.SERVICE_ID)
            if not isinstance(result, int):  # Se il risultato non è un codice di errore, consideriamo il refresh riuscito
                print(f"[CatalogClient] Refresh di '{self.SERVICE_ID}' eseguito con successo: {result}")
            else:
                print(f"[CatalogClient] WARNING: refresh di '{self.SERVICE_ID}' non riuscito. Verrà riprovato al prossimo ciclo. - Status code: {result}")

    # ── REST HANDLERS ────────────────────────────────────────────────────────

    ## Funzione che gestisce le richieste GET, in base alla presenza o meno di parametri e alla loro tipologia (URI o query parameters) decide quale funzione chiamare per ottenere i dati richiesti
    def GET(self, *uri, **params):
        ## ESERCIZIO 1
        if(len(uri) == 0 and len(params) != 0):
            keys = list(params.keys())
            if (len(keys) == 1 and keys[0] == "room"):
                response = self.get_room(params["room"])
            elif (len(keys) == 2 and keys[0] == "room" and keys[1] == "sens"):
                response = self.get_room_sens(params["room"], params["sens"])
            else:
                raise cherrypy.HTTPError(400, "Bad request: Invalid query parameters. Valid parameters are 'room' and 'sens'. Example: ?room=living_room&sens=temperature")

        ## ESERCIZIO 2
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


