import cherrypy
import random
import json
import time
from datetime import datetime, timezone
from Es04 import SmartHomeLogService


class SmartHomeSensorService(object):
    exposed = True

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
    
    logs = SmartHomeLogService()

    # Da usare: curl.exe -X POST http://127.0.0.1:9090/sensors -H "Content-Length: 0"
    def POST(self, *uri, **params):
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
            if room not in self.rooms_sens:
                raise cherrypy.HTTPError(404, "Room not found")

            sensor = list(body.values())[1]    # prima chiave
            value = list(body.values())[2]  # primo valore
            
            if sensor not in self.rooms_sens[room]:
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
                    


            self.rooms_sens[room][sensor] = value
            # Aggiunta del Json nel log
            self.logs.AddLog(body)


        self.InitSens()

        return json.dumps({
            "status": "ok",
            "message": "Tutti i sensori inizializzati",
        }).encode("utf-8")

    def InitSens(self):
        for room in self.rooms_sens.values():
            for sens in room.keys():
                if(sens == "temperature"):
                    room[sens] = round(random.uniform(10, 30), 2)
                elif(sens == "motion_sensor"):
                    room[sens] = random.choice([True, False])
                elif(sens == "humidity"):
                    room[sens] = round(random.uniform(10, 90), 2)


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

        self.logs.AddLog(self.createSenML_URI(uri))
        return json.dumps(response).encode("utf-8")
    
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
        return response