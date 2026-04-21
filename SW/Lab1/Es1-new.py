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

    stanze = {"living_room", "kitchen", "bedroom"}
    sensori = {"temperature", "humidity", "motion_sensor"}

    def GET(self, *uri, **params):
        if(len(uri)==0):
            raise cherrypy.HTTPError(404, "Bad request: Specificare il nome del sensore")

        nome_stanza = uri[0]

        if(nome_stanza not in self.stanze):
            raise cherrypy.HTTPError(404, "Bad request: Nome della stanza non presente")
        

        
        if(len(uri)==1):
            timestamp = time.time()

            response = [
                {
                    "bn": nome_stanza + '/',
                    "n": "temperature",
                    "v": random.uniform(10, 40),
                    "bt": timestamp
                },
                {
                    "n": "humidity",
                    "v": random.uniform(10, 40),
                },
                {
                    "n": "motion_sensor",
                    "v": random.choice([True, False]),
                }
            ]        
            return json.dumps(response).encode("utf-8")


        nome_sensore = uri[1]

        if(nome_sensore not in self.sensori):
            raise cherrypy.HTTPError(400, "Bad request: Nome del sensore non presente")
        
        match nome_sensore:
            case "temperature":
                value = random.uniform(10, 40)
            case "humidity":
                value = random.uniform(10, 40)
            case "motion_sensor":
                value = random.choice([True, False])

    
        timestamp = time.time()


        response = {
            "bn": nome_stanza + '/',
            "n": nome_sensore,
            "v": value,
            "bt": timestamp
        }

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