import cherrypy
import random
import json
import time
from datetime import datetime, timezone

class MyService:
    exposed = True

    def GET(self):
        return b'{"message": "Server attivo (ciao)"}'


class SmartHomeSensorService(object):
    exposed = True

    def get_room(self, room):
        timestamp = time.time()

        response = [
            {
                "bn": self.nome_stanza + '/',
                "n": "temperature",
                "v": self.rooms[room]["temperature"],
                "bt": timestamp
            },
            {
                "n": "humidity",
                "v": self.rooms[room]["humidity"],
            },
            {
                "n": "motion_sensor",
                "v": self.rooms[room]["motion_sensor"],
            }
        ]
        return response


    def get_room_sens(self, room, sens):
        if(room not in self.rooms):
            raise cherrypy.HTTPError(400, "Bad request: Nome della stanza non presente")

        if(sens not in self.rooms[room]):
            raise cherrypy.HTTPError(400, "Bad request: Nome del sensore non presente")
        
        match sens:
            case "temperature":
                value = random.uniform(10, 40)
            case "humidity":
                value = random.uniform(10, 40)
            case "motion_sensor":
                value = random.choice([True, False])
    
        timestamp = time.time()

        response = {
            "bn": room + '/',
            "n": sens,
            "v": self.rooms[room][sens],
            "bt": timestamp
        }
        return response


    rooms = {"living_room": {"temperature": None,
                        "humidity": None,
                        "motion_sensor": None},
            "kitchen": {"temperature": None,
                        "humidity": None,
                        "motion_sensor": None},
            "bedroom": {"temperature": None,
                        "humidity": None,
                        "motion_sensor": None},
            }    

    def InitSens(self):
        for room in self.rooms.values():
            for sens in room.keys():
                if(sens == "temperature" or sens == "humidity"):
                    room[sens] = random.uniform(10, 40)
                else:
                    room[sens] = random.choice([True, False])


    def GET(self, *uri, **params):
        self.InitSens()
        
        if(len(uri)==0):
            return json.dumps(self.rooms).encode("utf-8")
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
    



if __name__ == '__main__':
    conf = {
        '/': {
            'request.dispatch': cherrypy.dispatch.MethodDispatcher(),
            'tools.sessions.on': True,
            'tools.response_headers.on': True,
            'tools.response_headers.headers': [('Content-Type',
            'application/json')]
        }
    }
    cherrypy.tree.mount(SmartHomeSensorService(), '/sensors/', conf)

    cherrypy.config.update({'server.socket_host': '127.0.0.1'})
    cherrypy.config.update({'server.socket_port': 9090})
    cherrypy.engine.start()
    cherrypy.engine.block()