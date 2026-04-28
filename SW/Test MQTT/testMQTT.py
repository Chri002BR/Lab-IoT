import paho.mqtt.client as PahoMQTT

class MyMQTT:
    def __init__(self, clientID, broker, port, notifier):
        self.broker = broker
        self.port = port
        self.notifier = notifier
        self._paho_mqtt = PahoMQTT.Client(clientID, False)
        self._paho_mqtt.on_connect = self.myOnConnect
        self._paho_mqtt.on_message = self.myOnMessageReceived

    def myOnConnect(self, paho_mqtt, userdata, flags, rc):
        print('Connected to %s with result code: %d' % (self.broker, rc))

    def myOnMessageReceived(self, paho_mqtt, userdata, msg):
        self.notifier.notify(msg.topic, msg.payload)

    def myPublish(self, topic, msg):
        self._paho_mqtt.publish(topic, msg, 2)

    def mySubscribe(self, topic):
        self._paho_mqtt.subscribe(topic, 2)

    def start(self):
        self._paho_mqtt.connect(self.broker, self.port)
        self._paho_mqtt.loop_start()

    def stop(self):
        self._paho_mqtt.loop_stop()
        self._paho_mqtt.disconnect()



import time

class TestClient:

    def __init__(self):
        self.client = MyMQTT(
            clientID="testClient",
            broker="mqtt.eclipseprojects.io",
            port=1883,
            notifier=self  # IMPORTANTISSIMO
        )

    def start(self):
        self.client.start()

        # iscrizione
        self.client.mySubscribe("test/topic")

        # loop per inviare messaggi
        while True:
            msg = input("Scrivi un messaggio: ")
            self.client.myPublish("test/topic", msg)

    def notify(self, topic, payload):
        print(f"\nRicevuto -> {topic}: {payload.decode()}")



if __name__ == "__main__":
    t = TestClient()
    t.start()