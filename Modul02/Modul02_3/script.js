// GANTI DENGAN IP KOMPUTER YANG MENJALANKAN BROKER
const brokerIp = "172.20.10.9"; 
const port = 8888;
const topic = "prak/chat/room";

const client = new Paho.MQTT.Client(brokerIp, port, "clientId_" + Math.random());

client.onMessageArrived = function(message) {
    const msgDiv = document.getElementById("messages");
    msgDiv.innerHTML += "<p><b>Teman:</b> " + message.payloadString + "</p>";
};

client.connect({
    onSuccess: () => {
        console.log("Connected!");
        client.subscribe(topic);
    }
});

function sendMessage() {
    const input = document.getElementById("userInput");
    const message = new Paho.MQTT.Message(input.value);
    message.destinationName = topic;
    client.send(message);

    // Tampilkan pesan sendiri di layar
    const msgDiv = document.getElementById("messages");
    msgDiv.innerHTML += "<p style='color:blue'><b>Saya:</b> " + input.value + "</p>";
    input.value = "";
}