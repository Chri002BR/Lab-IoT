import cherrypy
import random
import json
import time
from datetime import datetime, timezone

class SmartHomeSensorService(object):
    exposed = True  

    log = []

    def GET(self, *uri, **params):
        
        if(len(uri)==1):
            uri_1 = uri[0]
            if(uri_1 != "log"):
                raise cherrypy.HTTPError(400, "Bad request: Link non esistente (usare \"/log\")")
            return json.dumps(self.log).encode("utf-8")
        else:
            raise cherrypy.HTTPError(400, "Bad request: Link non esistente")

    def POST(self, *uri, **param):
        body = cherrypy.request.body.read()
        if body:
            data = json.loads(body)
            self.log.append(data)
        


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

    # cherrypy.config.update({'server.socket_host': '127.0.0.1'})
    cherrypy.config.update({'server.socket_host': '10.251.62.1'})
    cherrypy.config.update({'server.socket_port': 8080})
    cherrypy.engine.start()
    cherrypy.engine.block()