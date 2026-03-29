const brokerIp = "192.168.x.x"; // IP Laptop Anda
const port = 8888;
const topicSub = "itb/iot/counter";
const topicPub = "itb/iot/led";

const client = new Paho.MQTT.Client(brokerIp, port, "web_client_" + Math.random());

        client.onMessageArrived = (message) => {
            if (message.destinationName === topicSub) {
                document.getElementById("counterDisp").innerText = message.payloadString;
            }
        };

        client.connect({
            onSuccess: () => {
                console.log("Connected to Broker");
                client.subscribe(topicSub);
            }
        });

        function sendControl(val) {
            const msg = new Paho.MQTT.Message(val);
            msg.destinationName = topicPub;
            client.send(msg);
        }