import cherrypy
import random
import json
import time
import requests

class SmartHomeSensorService(object):
    exposed = True
    
    url_log = "http://127.0.0.1:9092/log/"

    rooms_sens = {"living_room": {
                        "temperature": None,
                        "humidity": None,
                        "motion_sensor": None,},
            "kitchen": {
                        "temperature": None,
                        "humidity": None,
                        "motion_sensor": None,},
            "bedroom": {
                        "temperature": None,
                        "humidity": None,
                        "motion_sensor": None},
            }
    
    units = {
        "temperature": "Cel",
        "humidity": "%RH",
        "motion_sensor": "bool"
    }
    
    ## Funzione per inizializzare la classe, utile per la simulazione, in questo modo i sensori hanno già dei valori random al primo avvio del server
    def __init__(self):
        self.InitSens()
    
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
    
    # DA CONTROLLARE
    # Da aggiungere il tipo di richiesta (GET, POST, ...) non richiesto ma così non si capisce nulla
    def createSenML_URI(self, uri):
        finalURI = {
            "s": "sensors" 
        }
        
        if len(uri) > 0:
            finalURI["bn"] = uri[0]  # Stanza
            
        if len(uri) > 1:
            finalURI["n"] = uri[1]   # Sensore

        return finalURI