import sys
import os
from pathlib import Path
import json

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))

import cherrypy
from Es04 import SmartHomeLogService
from Es12 import MQTT_log_service

GROUP_ID = "group14"

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

    log_service_instance = SmartHomeLogService()
    log_service_instance_MQTT = MQTT_log_service()

    cherrypy.tree.mount(log_service_instance, '/log', conf)
    cherrypy.tree.mount(log_service_instance_MQTT, '/log-MQTT', conf)

    
    uri_path = Path(__file__).parent / "config-uri-server.json"
    try:
        with open(uri_path, "r") as f:
            config = json.load(f)
        indirizzo = config.get("server_address", "0.0.0.0")
        porta = config.get("server_port", "9092")
    except FileNotFoundError:
        indirizzo = "0.0.0.0"
        porta = "9092"

    cherrypy.config.update({'server.socket_host': indirizzo})
    cherrypy.config.update({'server.socket_port': int(porta)})
    cherrypy.engine.subscribe('stop', log_service_instance_MQTT.stop)
    cherrypy.engine.start()
    cherrypy.engine.block()
