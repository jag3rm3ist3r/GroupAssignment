# arg 1 : serial device
# arg 2 : server address

# CLI arguments
import sys
# MQTT for communication with the server.
import paho.mqtt.publish as mqttpublish

node1 = {"watered": 0,
        "button": 0,
        "water_level": 0,
        "light_level": 0,
        "time_record": 0,
        "last_update": 0}

node2 = node1.copy()

def sendData(topic, message):
    targetip = sys.argv[2]
    mqttpublish.single(topic, message, hostname=targetip)


def serialDataFiltering(text):
    #organize serial data as node dictionary
    if (text[0].slice(0, 7) == "node1/"):
        node = node1
    if (text[0].slice(0, 7) == "node2/"):
         node = node2

    key = text[0].slice(7, -1)

    if (
            key == "watered" or
            key == "button" or
            key == "water_level" or
            key == "light_level"
        ):
        #send the correct node's data
        topic = f"{node}/{key}"
        sendData(topic, text[1])

def main():
    # Grab serial device (argument 1)
    ser = serial.Serial(sys.argv[1], 9600, timeout = 10)
    ser.flush()
    new_data = False
    
    # Read serial data into data dict. but only if there is data in the buffer.
    while(ser.in_waiting > 0):
        new_data = True
        #change from do 4 times to for every line in serial
        for i in ser.in_waiting):
            text = ser.readline().decode('utf-8').strip().split(" = ")
            #data coming in will have node name in front (ex: node1/)
            serialDataFiltering(text)

    # !!! IMPLEMENT !!!
    # Receive MQTT signal to turn pump/LED on and off.
    # (ser.write(b"2"))
 

if __name__ == '__main__':
    # Thank you Mario!
    # But our main() is in another castle. 
    while(1):
        main()
        # Wait a bit before restarting the loop.
        delay(2)
