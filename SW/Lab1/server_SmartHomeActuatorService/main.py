import sys
import os
from pathlib import Path
import json
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

    # Carico il file contenente le config per il server
    uri_path = Path(__file__) / "config-uri-server.json"
    try:
        with open(uri_path, "r") as f:
            config = json.load(f)
        indirizzo = config.get("indirizzo", "0.0.0.0")
        porta = config.get("porta", "9091")
    except FileNotFoundError:
        indirizzo = "0.0.0.0"
        porta = "9091"

    cherrypy.config.update({'server.socket_host': indirizzo})
    cherrypy.config.update({'server.socket_port': int(porta)})
    cherrypy.engine.start()
    cherrypy.engine.block()