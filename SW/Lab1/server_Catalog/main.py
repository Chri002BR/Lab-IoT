import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))

import cherrypy
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
    cherrypy.tree.mount(Catalog(), '/catalog/', conf)

    cherrypy.config.update({'server.socket_host': '0.0.0.0'})
    cherrypy.config.update({'server.socket_port': 9093})
    cherrypy.engine.start()
    cherrypy.engine.block()
    