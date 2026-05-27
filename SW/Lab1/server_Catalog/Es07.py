import SW.Lab1.server_Catalog.Es05 as Es05 
import paho.mqtt.client as mqtt
import json
import time

class MQTTCatalogBridge(object):

    def __init__(self, catalog, broker_host, broker_port):

        self.catalog=catalog
        self.broker_host=broker_host
        self.broker_port=broker_port

        self.client=mqtt.Client()

        self.registration_topic = "tiot/group14/catalog/register" 
        # Prefisso per le risposte 
        self.response_topic_prefix = "tiot/group14/catalog/register/response/"
        
        self.client.on_connect=self.connect 
        self.client.on_message=self.message

        # connect e message sono le funzioni che sìgestiscono la comunicazione

    #avvia la connessione
    def start(self):

            self.client.connect(self.broker_host, self.broker_port, 60)
            self.client.loop_start()          

    #iscrizione al topic
    def connect(self, client, userdata, flags, code):

        if code==0:

            print(f"Connected to {self.broker_host}")
            self.client.subscribe(self.registration_topic) #gestisce messaggi pubblicati su questo topic

        else: 

            print(f"Connection failed with code {code}")

    def message(self, client, userdata, msg): #msg.topic e msg.payload
        # formato JSON 
        #{
        #    "type": "devices",
        #    "id": "sensor-test",
        #    "description": "Temperature sensor in bedroom",
        #    "resources": ["temperature"],
        #    "mqtt": {
        #        "ip": "test.mosquitto.org",
        #        "port": 1883,
        #        "topic": "tiot/group01/bedroom/temp"
        #    }
        #}
        # campo type aggiunto perchè la distinzione in es 5 è fatta tramite uri e non nel json

        #try perchè non supporta raise error ma solleva exception, che bloccherebbe il programma
        try:

            body=json.loads(msg.payload.decode("utf-8"))

            if "id" not in body:        # Verifica che i campi obbligatori siano presenti
                raise ValueError(f"error: Field 'id' is required")
            if "description" not in body:
                raise ValueError(f"error: Field 'description' is required")
            if "resources" not in body:
                raise ValueError(f"error: Field 'resources' is required")
            
            item_type=body["type"]
            if item_type not in ("services", "devices"):
                raise ValueError(f"error: Field 'type' should be 'services' or 'devices'")

            del body["type"] #così da non inserire il campo nel file
            body["insert_timestamp"] = time.time()
    
            with self.catalog._lock:
                existing = self.catalog._find(item_type, body["id"])
    
                if existing is not None:
                    # Already registered: just refresh the timestamp
                    existing["insert_timestamp"] = body["insert_timestamp"]
                    self.catalog._save()
                    print(f"[POST] Refreshed {item_type[:-1]} '{body['id']}'")
                    
                else:
                    # New entry: add it
                    self.catalog._data[item_type].append(body)
                    self.catalog._save()
                    print(f"[POST] Registered new {item_type[:-1]} '{body['id']}'")

            response_topic = f"{self.response_topic_prefix}{body['id']}"
            ack_message = {
                "id": body["id"],
                "timestamp": body["insert_timestamp"]
            }
            #invia acknowledge
            self.ACKresponse(response_topic, ack_message)

        except json.JSONDecodeError:
            print("Error: Payload is not a valid JSON")
        except Exception as e:
            print(f"Error processing message: {e}")
            #invio messaggio di errore al sensore(?)

    def ACKresponse(self, topic, message):
        
        self.client.publish(topic, json.dumps(message)) #pubblicazione
        print(f"Published ACK to topic: {topic}")
                