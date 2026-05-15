import cherrypy
import random
import json
import time
from datetime import datetime, timezone
from Es03 import SmartHomeSensorService
from Es04 import SmartHomeLogService

class MyService:
    exposed = True

    def GET(self):
        return b'{"message": "Server attivo (ciao)"}'



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
    cherrypy.tree.mount(SmartHomeLogService(), '/log', conf)

    cherrypy.config.update({'server.socket_host': '127.0.0.1'})
    cherrypy.config.update({'server.socket_port': 9090})
    cherrypy.engine.start()
    cherrypy.engine.block()