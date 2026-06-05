import cherrypy
import random
import json
import time
from datetime import datetime, timezone
from SW.Lab1.server_SmartHomeSensorService.Es01_02 import SmartHomeSensorService
from SW.Lab1.server_SmartHomeLogService.Es04 import SmartHomeLogService
from SW.Lab1.server_SmartHomeActuatorService.Es03 import SmartHomeActuatorService
from SW.Lab1.server_Catalog.Es05 import Catalog

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
    cherrypy.tree.mount(SmartHomeActuatorService(), '/actuators/', conf)
    cherrypy.tree.mount(SmartHomeLogService(), '/log', conf)
    cherrypy.tree.mount(Catalog(), "/catalog", conf)

    cherrypy.config.update({'server.socket_host': '0.0.0.0'})
    cherrypy.config.update({'server.socket_port': 9099})
    cherrypy.engine.start()
    cherrypy.engine.block()