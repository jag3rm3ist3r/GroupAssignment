# arg 1 : serial device
# arg 2 : edge address
# arg 3 : edge name
# arg 4 : cloud server address

# CLI arguments
import sys
# MQTT for communication with the server.
import paho.mqtt.publish as mqttpublish
import paho.mqtt.client as mqttclient

import serial
import time

#no longer using this dict
node1 = {"watered": 0,
        "button": 0,
        "water_level": 0,
        "light_level": 0,
        "time_record": 0,
        "last_update": 0}

#cloud subscription, edge does need to know which one it is
def on_connect(client, userdata, flags, rc):
    print("Connected with result code " + str(rc))
    #arg 3 is edge id
    client.subscribe(sys.argv[3] + "/#")

#topics are pump and light
#send serial instructions to node for pump or led
def on_message(client, userdata, msg):
    if (msg.topic == (sys.argv[3] + "/pump")):
        print("pump")
        userdata['ser'].write(b"1")
    if (msg.topic == (sys.argv[3] + "/led")):
        userdata['ser'].write(b"2")
        print ("led")

#hostname is sender ip
def sendData(topic, message):
    hostip = sys.argv[2]
    print(topic + " " + message)
    mqttpublish.single(topic, message, hostname=hostip)

def serialDataFiltering(text):

    #the string without node1/
    key = text[0]
    #Watered might not need to be here
    if (
            key == "watered" or
            key == "button" or
            key == "water_level" or
            key == "light_level"
        ):
        #send the correct node's data directly
        topic = sys.argv[3] + "data/{key}"
        sendData(topic, text[1])

def main():
    # Grab serial device (argument 1)
    ser = serial.Serial(sys.argv[1], 9600, timeout = 10)
    ser.flush()
    
    #pass serial as user data
    client_userdata = {'ser':ser}
    client = mqttclient.Client(userdata=client_userdata)
    client.on_connect = on_connect
    client.connect(sys.argv[4], 1883, 60)
    #non-blocking loop (runs on background thread)
    client.loop_start()

    while(True):
        # Read serial data if there is data in the buffer and send it.
        while(ser.in_waiting > 0):
            #change from do 4 times to for every line in serial
            text = ser.readline().decode('utf-8').strip().split(" = ")
            #data coming in will have node name in front (ex: node1/)
            serialDataFiltering(text)

    # Receive MQTT signal to turn pump/LED on and off.
    # (ser.write(b"2"))
        
        client.on_message = on_message

if __name__ == '__main__':
    # Thank you Mario!
    # But our main() is in another castle. 
    while(1):
        main()
        # Wait a bit before restarting the loop.
        delay(2)
