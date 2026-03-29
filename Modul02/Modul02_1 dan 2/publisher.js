const mqtt = require('mqtt');
const port = 8000;
const broker_address = 'mqtt://172.20.10.2:1883'

const client = mqtt.connect(broker_address);

var data = 0;

client.on('connect',function(){
    console.log("Publishing to $s",broker_address);
    setInterval(function(){
        data++;
        let message = `${data}`;
    let topic = "Sent to Rifqi";
    client.publish(topic, message);
    },100)
});