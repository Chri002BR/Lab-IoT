import cherrypy
import random
import json
from datetime import datetime, timezone

class MyService:
    exposed = True

    def GET(self):
        return b'{"message": "Server attivo (ciao)"}'


class SmartHomeSensorService(object):
    exposed = True

    sensori = {"temperature", "humidity"}

    def GET(self, *uri, **params):
        # return b'{"message": "Sensore 1"}'
        # return random.choice([True, False])

        if(len(uri)==0):
            raise cherrypy.HTTPError(404, "Bad request: Specificare il nome del sensore")

        nome_sensore = uri[0]
        if(nome_sensore not in self.sensori):
            raise cherrypy.HTTPError(404, "Bad request: Nome del sensore non presente")
        
        status = random.choice([True, False])

        timestamp = datetime.now(timezone.utc).isoformat()
        response = {
            "sensor": nome_sensore,
            "status": status,
            "timestamp": timestamp
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
    cherrypy.tree.mount(SmartHomeSensorService(), '/', conf)

    cherrypy.config.update({'server.socket_host': '127.0.0.1'})
    cherrypy.config.update({'server.socket_port': 9090})
    cherrypy.engine.start()
    cherrypy.engine.block()