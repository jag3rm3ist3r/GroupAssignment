data = {"watered": 0,
        "button": 0,
        "water_level": 0,
        "light_level": 0,
        "time_record": 0,
        "last_update": 0}


def main():
    new_data = False
    
    # Read serial data into data dict.
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
    
    if new_data:
        seconds = time.time()
        last_update = time.ctime(seconds)
        data["time_record"] = seconds
        data["last_update"] = time.ctime(seconds)

        # !!! IMPLEMENT !!!
        # Send data over MQTT instead of storing to SQL database.


    # !!! IMPLEMENT !!!
    # Receive MQTT signal to turn pump/LED on and off.
    # (ser.write(b"2"))
 

if __name__ == '__main__':
    # Thank you Mario!
    # But our main() is in another castle. 
    main()
