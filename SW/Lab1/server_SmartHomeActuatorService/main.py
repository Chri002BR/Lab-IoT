import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))

import cherrypy
from Es03 import SmartHomeActuatorService

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
    cherrypy.tree.mount(SmartHomeActuatorService(), '/actuators/', conf)

    cherrypy.config.update({'server.socket_host': '0.0.0.0'})
    cherrypy.config.update({'server.socket_port': 9091})
    cherrypy.engine.start()
    cherrypy.engine.block()