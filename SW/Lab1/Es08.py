import json
import threading 
import time
import paho.mqtt.client as mqtt

AUTO_REGISTRATION_LOOP_TIME = 60

GROUP_ID = "group14" 
#device to simulate in this terminal
DEVICE_ID = "device1"
#topics at line 25

class  DeviceMQTTClient(object):

    def __init__(self, client, group, description="IOT device", resources=None):

        self.client_id=client
        self.group_id=group

        #description and resources from the sensor itself
        self.description = description
        self.resources = resources if resources is not None else []

        self.thread_flag=True

        #topic definition
        self.registration_topic = f"tiot/{self.group_id}/catalog/register"
        self.ack_topic = f"tiot/{self.group_id}/catalog/register/response/{self.client_id}"
        self.query_topic = f"tiot/{self.group_id}/catalog/query"
        self.response_topic = f"tiot/{self.group_id}/device/{self.client_id}/response"

        self.client = mqtt.Client(client_id=self.client_id, callback_api_version=mqtt.CallbackAPIVersion.VERSION2)

        #comunication methods       
        self.client.on_connect=self.connect 
        self.client.on_message=self.message

    def start(self):

            #starts the connection
            self.client.connect("broker.hivemq.com", 1883, 60)
            self.client.loop_start()

            #starts the automatic registration thread
            self.bg_thread = threading.Thread(target=self.autoRegistration, daemon=True)
            self.bg_thread.start()

    def stop(self):

        self.thread_flag=False

        self.client.loop_stop()
        self.client.disconnect()
        print("\nClient disconnected")

    def publish_autoReg(self):

        body={
            "type": "devices",
            "id": self.client_id,
            "description": self.description,
            "mqtt_info": {
                "ip": "iot.eclipse.org",
                "port": 1883,
                "topic": f"tiot/{self.group_id}/device/{self.client_id}/data"
            },
            "resources": self.resources
        }

        self.client.publish(self.registration_topic, json.dumps(body))
        print(f"\nRegistered on {self.registration_topic}")

    #thread for autoregistration
    def autoRegistration(self):

        while self.thread_flag:

            self.publish_autoReg()

            time.sleep(AUTO_REGISTRATION_LOOP_TIME)

    def connect(self, client, userdata, flags, code, properties=None):

        if code==0:

            print(f"Connected to {self.client_id}")
            self.client.subscribe(self.response_topic) 
            self.client.subscribe(self.ack_topic)

        else: 

            print(f"Connection failed with code {code}")

    def message(self, client, userdata, msg): #msg.topic and msg.payload


        if msg.topic==self.ack_topic:

            print("\nAck received")

        else:

            body=json.loads(msg.payload.decode("utf-8"))
            print(f"\nMessage received on {msg.topic}")
            print(json.dumps(body))

    #queryies
    def get_all_devices(self):

        #request topic is where to send the response to the query
        body={
            "request_type": "all",
            "response_topic": self.response_topic
        }
        self.client.publish(self.query_topic, json.dumps(body))

    def get_device_by_id(self, id):

        #request topic is where to send the response to the query
        body={
            "request_type": "one",
            "target_id": id,
            "response_topic": self.response_topic
        }
        self.client.publish(self.query_topic, json.dumps(body))

if __name__ == '__main__':

    #description and resources
    
    device = DeviceMQTTClient(client=DEVICE_ID, group=GROUP_ID)
    device.start()
    
    time.sleep(2)

    #menu
    while True:
        print(f"\nDevice: {DEVICE_ID}" \
        "\n1) registration" \
        "\n2) query all" \
        "\n3) query by id" \
        "\n4) quit")

        operation=input("\nChoose an operation(1-4)").strip()

        if operation=="1":

            device.publish_autoReg()

        elif operation=="2":

            device.get_all_devices()

        elif operation=="3":

            target_id=input("\nEnter target id: ")
            if target_id:
                device.get_device_by_id(target_id)
            else:
                print("\nInsert a valid id")

        elif operation=="4":

            device.stop()
            break

        else:

            print("\nInvalid choice")
