from umqtt.simple import MQTTClient

def connectMQTT():
    client = MQTTClient(client_id=b"raspberrypi_picow",
    server=b"test.mosquitto.org",
    port=1883,
    #user= None #b"smartPlug",
    #password= None #b"smartPlug123",
    keepalive=7200
    )

    client.connect()
    return client

def publish(client, topic, value):
    client.publish(topic, value)
    print ("sent mqtt")
