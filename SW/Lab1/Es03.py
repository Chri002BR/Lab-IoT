import cherrypy
import random
import json
import time
from datetime import datetime, timezone


class SmartHomeSensorService(object):
    exposed = True

    rooms = {"living_room": {"temperature": None,
                        "humidity": None,
                        "motion_sensor": None,
                        "thermostat": None,
                        "lights": None,
                        "blinds": None},
            "kitchen": {"temperature": None,
                        "humidity": None,
                        "motion_sensor": None,
                        "thermostat": None,
                        "lights": None,
                        "blinds": None},
            "bedroom": {"temperature": None,
                        "humidity": None,
                        "motion_sensor": None,
                        "thermostat": None,
                        "lights": None,
                        "blinds": None},
            }    
    
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

            if(list(body.keys())[0] != "nb"):
                raise cherrypy.HTTPError(422, "Bad request: Unprocessable Entity")
            if(list(body.keys())[1] != "n"):
                raise cherrypy.HTTPError(422, "Bad request: Unprocessable Entity")
            if(list(body.keys())[2] != "v"):
                raise cherrypy.HTTPError(422, "Bad request: Unprocessable Entity")



            room = list(body.values())[0]
            if room not in self.rooms:
                raise cherrypy.HTTPError(404, "Room not found")

            sensor = list(body.values())[1]    # prima chiave
            value = list(body.values())[2]  # primo valore
            
            if sensor not in self.rooms[room]:
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
                    if(0 < value or value > 100):
                        raise cherrypy.HTTPError(404, "Out of range")
                    


            self.rooms[room][sensor] = value
            # Aggiunta del Json nel log



        self.InitSens()

        return json.dumps({
            "status": "ok",
            "message": "Tutti i sensori inizializzati",
        }).encode("utf-8")



    def get_allSens(self):
        response = []
        for room in self.rooms:
            response.append(self.get_room(room))
        
        return response

    def get_room(self, room):
        timestamp = time.time()

        response = [
            {
                "bn": room + '/',
                "n": "temperature",
                "v": self.rooms[room]["temperature"],
                "bt": timestamp
            }
        ]

        for sens in self.rooms[room]:
            if(sens != "temperature"):
                response.append(
                    {
                        "n": sens,
                        "v": self.rooms[room][sens],
                    }
                )

        return response


    def get_room_sens(self, room, sens):
        if(room not in self.rooms):
            raise cherrypy.HTTPError(400, "Bad request: Nome della stanza non presente")

        if(sens not in self.rooms[room]):
            raise cherrypy.HTTPError(400, "Bad request: Nome del sensore non presente")
    
        timestamp = time.time()

        response = {
            "bn": room + '/',
            "n": sens,
            "v": self.rooms[room][sens],
            "bt": timestamp
        }
        return response

    def InitSens(self):
        for room in self.rooms.values():
            for sens in room.keys():
                if(sens == "temperature" or sens == "humidity"):
                    room[sens] = random.uniform(10, 40)
                elif(sens == "motion_sensor"):
                    room[sens] = random.choice([True, False])


    def GET(self, *uri, **params):
        
        if(len(uri)==0):
            return json.dumps(self.get_allSens()).encode("utf-8")
        elif(len(uri)==1):
            self.nome_stanza = uri[0]

            if(self.nome_stanza not in self.rooms):
                raise cherrypy.HTTPError(404, "Bad request: Nome della stanza non presente")

            response = self.get_room(self.nome_stanza)
        elif(len(uri)==2):
            nome_stanza = uri[0]
            nome_sensore = uri[1]

            response = self.get_room_sens(nome_stanza, nome_sensore)

        return json.dumps(response).encode("utf-8")