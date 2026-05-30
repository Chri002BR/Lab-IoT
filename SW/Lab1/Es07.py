import Es05 
import paho.mqtt.client as mqtt
import json
import time

GROUP_ID = "group14" 

class MQTTCatalogBridge(object):

    def __init__(self, catalog, broker_host, broker_port):

        self.catalog=catalog
        self.broker_host=broker_host
        self.broker_port=broker_port

        self.client=mqtt.Client(callback_api_version=mqtt.CallbackAPIVersion.VERSION2)

        #topics declaration
        self.registration_topic = f"tiot/{GROUP_ID}/catalog/register" 
        self.response_topic_prefix = f"tiot/{GROUP_ID}/catalog/register/response/"
        self.query_topic = f"tiot/{GROUP_ID}/catalog/query"

        
        self.client.on_connect=self.connect 
        self.client.on_message=self.message

        # connect and message are communication methods

    #start connection
    def start(self):

            self.client.connect(self.broker_host, self.broker_port, 60)
            self.client.loop_start()          

    #subscription to topics
    def connect(self, client, userdata, flags, code, properties=None):

        if code==0:

            print(f"Connected to {self.broker_host}")
            self.client.subscribe(self.registration_topic) #gestisce messaggi pubblicati su questo topic
            self.client.subscribe(self.query_topic)

        else: 

            print(f"Connection failed with code {code}")

    def message(self, client, userdata, msg): #msg.topic e msg.payload
        # JSON format 
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
        #type added to the es 5 format

        try:

            body=json.loads(msg.payload.decode("utf-8"))

            if msg.topic==self.registration_topic:

                if "id" not in body:       
                    raise ValueError(f"error: Field 'id' is required")
                if "description" not in body:
                    raise ValueError(f"error: Field 'description' is required")
                if "resources" not in body:
                    raise ValueError(f"error: Field 'resources' is required")
                
                item_type=body["type"]
                if item_type not in ("services", "devices"):
                    raise ValueError(f"error: Field 'type' should be 'services' or 'devices'")

                del body["type"] #so we don't insert it in the file
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
                #send acknowledge
                self.ACKresponse(response_topic, ack_message)
            
            elif msg.topic==self.query_topic:

                request_type=body["request_type"]
                response=body["response_topic"]
                
                if request_type=="all":

                    with self.catalog._lock:

                        data=self.catalog._data.get("devices")

                elif request_type=="one":

                    if body["target_id"]:

                        with self.catalog._lock:

                            data=self.catalog._find("devices", body["target_id"])

                    else:
                        
                        print("\nMissing terget id")

                else:

                    print("\nInvalid type")

                self.client.publish(response, json.dumps(data))
                print(f"\nAnswered query on topic: {response}")

        except json.JSONDecodeError:
            print("Error: Payload is not a valid JSON")
        except Exception as e:
            print(f"Error processing message: {e}")


    def ACKresponse(self, topic, message):
        
        self.client.publish(topic, json.dumps(message)) #pubblication
        print(f"Published ACK to topic: {topic}")


                