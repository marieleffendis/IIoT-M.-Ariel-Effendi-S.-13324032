const aedes = require('aedes')()
const broker = require('net').createServer(aedes.handle)
const broker_port = 1883

broker.listen(broker_port, function () {
    console.log('MQTT broker started and listening on port ', broker_port)
})