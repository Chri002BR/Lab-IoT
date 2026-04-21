import cherrypy
import random
import json
from datetime import datetime, timezone

# class MyService:
#     exposed = True

#     def GET(self):
#         return b'{"message": "Server attivo (ciao)"}'


class FirstSensor(object):
    exposed = True

    sensori = {"temperature", "presence"}
    actions = {"alert", "threshold"}

    # Dati memorizzati:
    thresholds = {}
    allerts = []


    def GET(self, *uri, **params):
        # return b'{"message": "Sensore 1"}'
        # return random.choice([True, False])

        if(len(uri)==0):
            raise cherrypy.HTTPError(404, "Bad request: Specificare il nome del sensore")

        nome_sensore = uri[0]

        if(nome_sensore not in self.sensori):
            raise cherrypy.HTTPError(404, "Bad request: Nome del sensore non presente")

        azione = uri[1] # Può indicare alert oppure trashold

        if(action not in self.actions):
            raise cherrypy.HTTPError(404, "Bad request: Azione non esistente")

        if(azione == "alert"){
            response = {
                "sensor": nome_sensore,
                "value": 
            }
        }else if(azione == "trashold"){
            return json.dumps(self.thresholds).encode("utf-8")
        }else:
            raise cherrypy.HTTPError(404, "Bad request: Azione non esistente")



        response = {
            "sensor": nome_sensore,
            "status": status,
            "timestamp": timestamp
        }

        return json.dumps(response).encode("utf-8")


    def POST (self, *uri, **params):
        if(len(uri)==0):
            raise cherrypy.HTTPError(404, "Bad request: Specificare il nome del sensore")

        action = uri[0]
        body = cherrypy.request.json

        nome_sensore = body["sensor"]
        valore_sensore = body["value"]

        if(action=="threshold"){
            min_val = body.get("min")
            MAX_val = body.get("max")

            if min_val is None or max_val is None or min_val >= MAX_val:
                raise cherrypy.HTTPError(404, "Bad request: min_val deve essere < max_val")


            # Salvo la configurazione nel dizionario
            self.thresholds[nome_sensore] = {"min": min_val, "max": MAX_val}

            return json.dumps({"message": f"Soglia salvata per {nome_sensore}"}).encode("utf-8")        }else if(action=="check"){

        }else:
            raise cherrypy.HTTPError(404, "Bad request: Azione non consentita")




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
    cherrypy.tree.mount(FirstSensor(), '/', conf)

    cherrypy.config.update({'server.socket_host': '127.0.0.1'})
    cherrypy.config.update({'server.socket_port': 9090})
    cherrypy.engine.start()
    cherrypy.engine.block()