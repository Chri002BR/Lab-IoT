import sys
import os
from pathlib import Path
import json

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))

import cherrypy
from Es04 import SmartHomeLogService
from Es12 import MQTTSubscriber

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

    cherrypy.tree.mount(log_service_instance, '/log', conf)

    MQTT_BROKER = "broker.hivemq.com" 
    MQTT_PORT = 1883
    
    # Sfruttiamo i caratteri jolly (wildcard '+') per ascoltare con un unico topic sia i sensori che i comandi.
    # Es. "smarthome/+/sensor" e "smarthome/+/actuator". Usando '#' ascoltiamo tutto ciò che sta sotto quel livello.
    MQTT_TOPIC = f"tiot/{GROUP_ID}/smarthome/#"  # Personalizza la radice (es. metti il tuo numero di gruppo al posto di 7)

    # 3. Istanziamo il Subscriber passando il riferimento a 'log_service_instance'
    mqtt_sub = MQTTSubscriber(
        clientID="SmartHomeLogService_Sub_2026", 
        broker=MQTT_BROKER, 
        port=MQTT_PORT, 
        topic=MQTT_TOPIC, 
        log_service=log_service_instance
    )

    # 4. Colleghiamo il Subscriber al ciclo di vita di CherryPy
    # Quando CherryPy parte, avvia l'MQTT; quando si stoppa, lo spegne in sicurezza.
    cherrypy.engine.subscribe('start', mqtt_sub.start)
    cherrypy.engine.subscribe('stop', mqtt_sub.stop)

    # 5. Avvio del Server
    # Carico il file contenente le config per il server
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
    cherrypy.engine.start()
    cherrypy.engine.block()
