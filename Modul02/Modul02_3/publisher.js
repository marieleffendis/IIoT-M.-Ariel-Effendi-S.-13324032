const http = require("http");
const mqtt = require('mqtt');
const fs = require("fs");
const host = 'localhost';
const port = 8000;

const broker_address = 'mqtt://localhost:1883'

const client = mqtt.connect(broker_address);

var t = 0;

client.on('connect',function(){
    console.log("Publishing to $s",broker_address);
    setInterval(function(){
        t++;
        let y = Math.round(50+20*Math.sin(0.2*t));
        let message = y.toString();
        let topic = "topik";
    client.publish(topic, message);
    },100)
})