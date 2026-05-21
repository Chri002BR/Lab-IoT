import cherrypy
import random
import json
import time
from datetime import datetime, timezone
from Es04 import SmartHomeLogService


class SmartHomeActuatorService(object):
    exposed = True

    rooms_act = {"living_room": {
                        "thermostat": None,
                        "lights": None,
                        "blinds": None},
            "kitchen": {
                        "thermostat": None,
                        "lights": None,
                        "blinds": None},
            "bedroom": {
                        "thermostat": None,
                        "lights": None,
                        "blinds": None},
            }
    
    units = {
        "thermostat": "Cel",
        "lights": "bool",
        "blinds": "pct"
    }
    
    logs = SmartHomeLogService()
    
    ## Funzione per inizializzare la classe, utile per la simulazione, in questo modo i sensori hanno già dei valori random al primo avvio del server
    def __init__(self):
        self.InitAct()

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

        self.logs.AddLog(self.createSenML_URI(uri))
        return json.dumps(response).encode("utf-8")

    # DA CONTROLLARE
    # Da usare: curl.exe -X POST http://127.0.0.1:9090/sensors -H "Content-Length: 0"
    
    #USARE PUT, NON POST
    
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
    def POST(self, *uri, **params):
        
        # Controllo che il Content-Type sia application/json, altrimenti ritorna un errore 415 Unsupported Media Type
        if cherrypy.request.headers.get("Content-Type", "") != "application/json":
            raise cherrypy.HTTPError(415, "Bad request: Content-Type must be application/json")
        
        # PERCHE' len(uri) == 0 ?? NON DOVREBBE ESSERE SEMPRE 0 PERCHE' L'URI DEVE CONTENERE LA STANZA E IL SENSORE DA AGGIORNARE ?
        if(len(uri) == 0):
            raw = cherrypy.request.body.read()
            
            # Controllo correttezza del pacchetto ----
            if not raw:
                raise cherrypy.HTTPError(400, "Bad request: Empty body")
            
            try:
                body = json.loads(raw)
            except json.JSONDecodeError:
                raise cherrypy.HTTPError(400, "Bad request: Invalid JSON body")
            # fine controllo -----

            if(list(body.keys())[0] != "bn"):
                raise cherrypy.HTTPError(422, "Bad request: Unprocessable Entity")
            if(list(body.keys())[1] != "n"):
                raise cherrypy.HTTPError(422, "Bad request: Unprocessable Entity")
            if(list(body.keys())[2] != "v"):
                raise cherrypy.HTTPError(422, "Bad request: Unprocessable Entity")



            room = list(body.values())[0]
            if room not in self.rooms_act:
                raise cherrypy.HTTPError(404, "Room not found")

            sensor = list(body.values())[1]    # prima chiave
            value = list(body.values())[2]  # primo valore
            
            if sensor not in self.rooms_act[room]:
                raise cherrypy.HTTPError(404, "Sensor not found in this room")
                

            # Controllo correttezza value (se in range)
            match sensor:
                case "thermostat":
                    if(value < 10 or value > 30):
                        raise cherrypy.HTTPError(404, "Out of range")
                case "lights":
                    if(value != "on" and value != "off"):
                        raise cherrypy.HTTPError(404, "Out of range")
                case "blinds":
                    if(value < 0 or value > 100):
                        raise cherrypy.HTTPError(404, "Out of range")
                    


            self.rooms_act[room][sensor] = value
            # Aggiunta del Json nel log
            self.logs.AddLog(body)


        self.InitAct()

        return json.dumps({
            "status": "ok",
            "message": "Tutti i sensori inizializzati",
        }).encode("utf-8")

    ## Funzione per inizializzare gli attuatori con valori random, utile per la simulazione
    def InitAct(self):
        for room in self.rooms_act.values():
            for sens in room.keys():
                if(sens == "temperature" or sens == "humidity"):
                    room[sens] = random.uniform(10, 40)
                elif(sens == "motion_sensor"):
                    room[sens] = random.choice([True, False])

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