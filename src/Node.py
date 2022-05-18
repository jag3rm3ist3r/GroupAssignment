# arg 1 : serial device
# arg 2 : server address

# CLI arguments
import sys
# MQTT for communication with the server.
import paho.mqtt.publish as mqttpublish

data = {"watered": 0,
        "button": 0,
        "water_level": 0,
        "light_level": 0,
        "time_record": 0,
        "last_update": 0}


def main():
    # Grab serial device (argument 1)
    ser = serial.Serial(sys.argv[1], 9600, timeout = 10)
    ser.flush()
    new_data = False
    
    # Read serial data into data dict. but only if there is data in the buffer.
    while(ser.in_waiting > 0):
        new_data = True
        for i in range(0, 4):
            text = ser.readline().decode('utf-8').strip().split(" = ")
            if (
                    text[0] == "watered" or
                    text[0] == "button" or
                    text[0] == "water_level" or
                    text[0] == "light_level"
                ):
                data[text[0]] = text[1]
    
    # Do something with data if some was read.
    if new_data:
        seconds = time.time()
        last_update = time.ctime(seconds)
        data["time_record"] = seconds
        data["last_update"] = time.ctime(seconds)

        # Send data over MQTT.
        topic = "arduino1/moisture"
        message = "test"
        targetip = sys.argv[2]
        mqttpublish.single(topic, message, hostname=targetip)


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
