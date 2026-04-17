import cherrypy
import random
import json

class MyService:
    exposed = True

    def GET(self):
        return b'{"message": "Server attivo (ciao)"}'


class FirstSensor(object):
    exposed = True
    def GET(self):
        # return b'{"message": "Sensore 1"}'
        # return random.choice([True, False])
        return json.dumps({"value": random.choice([True, False])}).encode("utf-8")


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
    cherrypy.tree.mount(MyService(), '/', conf)
    cherrypy.tree.mount(FirstSensor(), '/sensor', conf)

    cherrypy.config.update({'server.socket_host': '127.0.0.1'})
    cherrypy.config.update({'server.socket_port': 9090})
    cherrypy.engine.start()
    cherrypy.engine.block()