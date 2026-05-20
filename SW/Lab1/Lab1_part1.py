import cherrypy
import random
import json
import time
from datetime import datetime, timezone
from Es01_02 import SmartHomeSensorService
from Es04 import SmartHomeLogService

if __name__ == '__main__':
    
    # Simulazione inizializzazione sensori
    SmartHomeSensorService().InitSens()
    
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

    cherrypy.config.update({'server.socket_host': '0.0.0.0'})
    cherrypy.config.update({'server.socket_port': 9090})
    cherrypy.engine.start()
    cherrypy.engine.block()