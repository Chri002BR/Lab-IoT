import sys
import os
from pathlib import Path
import json
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))

import cherrypy
from Es01_02 import SmartHomeSensorService

if __name__ == '__main__':

    # Carico il file contenente le config per il server
    uri_path = Path(__file__).parent / "config-uri-server.json"
    try:
        with open(uri_path, "r") as f:
            config = json.load(f)
        indirizzo = config.get("indirizzo_server", "0.0.0.0")
        porta = config.get("porta_server", "9090")
    except FileNotFoundError:
        indirizzo = "0.0.0.0"
        porta = "9090"
    
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
    cherrypy.config.update({'server.socket_host': indirizzo})
    cherrypy.config.update({'server.socket_port': int(porta)})
    cherrypy.engine.start()
    cherrypy.engine.block()
    