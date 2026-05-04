import paho.mqtt.client as mqtt

class MQTTClient:
    def __init__(self, broker="localhost", port=1883):
        self.client = mqtt.Client()
        self.client.on_message = self.on_message

        self.callbacks = {}

        self.client.connect(broker, port)

    def subscribe(self, topic, callback):
        self.callbacks[topic] = callback
        self.client.subscribe(topic)

    def publish(self, topic, message):
        self.client.publish(topic, message)

    def on_message(self, client, userdata, msg):
        topic = msg.topic
        payload = msg.payload.decode()

        if topic in self.callbacks:
            self.callbacks[topic](payload)

    def start(self):
        self.client.loop_start()