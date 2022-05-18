# IOT Assignment RPI python script
# arg 1 : serial device file

# Must be serial communication to the arduino
import serial
import time
from datetime import datetime
# postgresql
import psycopg2
import thread
# CLI arguments
import sys
# Floating point logic is complete garbage so I'm trying Decimal.
from decimal import Decimal
# Flask for webpage
from flask import Flask, render_template
# MQTT for communication with ThingsBoard and both Nodes.
import paho.mqtt.publish as mqttpublish
import paho.mqtt.client as mqttclient


# Flask init.
app = Flask(__name__)


# index.html file operation
@app.route("/")
def index():
    global sl
    # This data will be sent to index.html
    templateData = sl.getTemplateData()
    return render_template('index.html', **templateData)


# Brains of the Flask website.
class SiteLogic():
    # !!! IMPLEMENT !!!
    # Try to make this return "rows" instead of whatever result from execute()

    # Generic function for executing queries that
    #+don't require much any extra interaction.
    def __execQuery(self, query):
        global conn
        result = None
        
        with self.__conn:
            cursor = self.__conn.cursor()
            result = cursor.execute(query)
            self.__conn.commit()
            cursor.close()
        
        return result
            

    # siteLogic constructor
    def __init__(self, persist):
        # SQL connection
        self.__conn = psycopg2.connect(
            database="pi",
            user = "pi",
            password = "pi",
            host = "127.0.0.1",
            port = "5432")
        

        # Clear old database entries.
        if not (persist):
            self.__execQuery("DROP TABLE IF EXISTS statistics;")
        
        # Data table.
        self.__execQuery(
            "CREATE TABLE IF NOT EXISTS statistics(" +
            "readingId SERIAL PRIMARY KEY NOT NULL, " +
            "moisture VARCHAR(20) NOT NULL, " +
            "light VARCHAR(20) NOT NULL, " +
            "timestamp VARCHAR(20) NOT NULL);")
        
        # Settings table.
        if not (persist):
            self.__execQuery("DROP TABLE IF EXISTS settings;")

        self.__execQuery(
            "CREATE TABLE IF NOT EXISTS settings" +
            "(name VARCHAR(22) PRIMARY KEY NOT NULL, " +
            "state VARCHAR(22) NOT NULL);")
        
        # Set defaults.
        with self.__conn:
            cursor = self.__conn.cursor()
            # This is wrapped in a try because it will fail when
            #+persistence is turned on and we don't really care as long as it
            #+exists.
            try:
                cursor.execute(
                    "INSERT INTO settings VALUES('target', '25.00');" +
                    "INSERT INTO settings VALUES('power', '0');" +
                    "INSERT INTO settings VALUES('heating', '0');")
                self.__conn.commit()
            except:
                pass
            cursor.close()

        # MQTT Client initializaiton.
        self.__client = []
        # argv[0]  : this file
        # argv[1]  : serial device
        # argv[>1] : ip addresses of nodes
        # Add a client for every IP passed as an argument.
        for i in range(len(sys.argv)):
            # Make sure we ignore the autopassed 0th argument.
            if i == 0:
                continue

            # User userdata as the index for if we don't know which client is
            #+calling a function.
            self.__client[i] = mqttclient.Client(userdata=i-1)
            self.__client[i].on_connect = self.on_connect
            self.__client[i].on_message = self.on_message

            # Initialize MQTT connection.
            # args: host, port, keepalive
            # !!! IMPLEMENT !!!
            # Change first argument to the correct address.
            self.__client[i].connect(sys.argv[i], 1883, 60)

    # Function bound to pahoMQTT
    # This function should not have "self" as an argument.
    # thisclient : ?
    # userdata : ?
    # flags : ?
    # rc : Result code
    def on_connect(thisclient, userdata, flags, rc):
        print("Connected with result code: " + str(rc))
        topic = "arduino"
        # Resub here so it doesn't lose subscriptions on reconnect.
        print(  "Subscribing to " + topic +
                " on " + str(sys.argv[userdata]) + ".")
        thisclient.subscribe(topic)

    # Function bound to pahoMQTT
    # This function should not have "self" as an argument.
    # thisclient : ?
    # userdata : ?
    # message : The message that was received.
    def on_message(thisclient, userdata, message):
        # Debug code to display messages as they're received.
        print(str(message.topic) + " " + str(message.payload))

        # !!! IMPLEMENT !!!
        # Filter for which sensor the data has come from using message.topic.
        # Jam into database.
        # Do some logic to determine whether something should turn on or off.


    # Time getter
    def getTime(self):
        return datetime.now().strftime("%H:%M:%S")

    # Average sensor reading DB getter
    def getDBAverage(self, ammount):
        with self.__conn:
            cursor = self.__conn.cursor()
            cursor.execute(
                "SELECT AVG(moisture), AVG(light) FROM statistics " +
                "ORDER BY readingId DESC LIMIT " + str(ammount) + ";")
            self.__conn.commit()
            rows = cursor.fetchall()
            cursor.close()
                        
            # !!! IMPLEMENT !!!
            # Not sure what format it will return, might need typecasting.
            return rows
    
    # Most recent readings DB getter.
    def getDBRecent(self, ammount):
        query =  "SELECT timestamp, moisture, light FROM statistics "
        query += "ORDER BY readingId DESC LIMIT " + str(ammount) + ";"

        # !!! IMPLEMENT !!!
        # Do query.

        #return rows

    # Template data getter
    # I am aware that using separate functions to make multiple
    #+SQL queries is inefficient but this doesn't need to be perfect.
    def getTemplateData(self):
        # !!! IMPLEMENT !!!
        # "moisture" and "light" are both equal to the most recent readings from
        #+"recent" so we may not need them as they just waste the SQL server's time
        #+with an unnecessary query.
        #recent = getDBRecent(20)
        # Get latest moisture and light readings from recent.
        #moisture = recent[?]
        #light = recent[?]

        return { 'moisture' : self.getDBmoisture(),
                 'light' : self.getDBlight(),
                 'recent' : self.getDBRecent(20),
                 'time' : self.getTime(),
                 'average' : self.getDBAverage(100)}

    # Loop for MQTT from sensors.
    def sensorLoop(self):
        # Enter MQTT loop.
        for c in self.__client:
            print("Starting thread " + str(c))
            thread.start_new_thread(c.loop_forever(), ())
        
        print("mqtt loop init complete")

# Main object, must be global for Flask to access it.
# Set argument to true if you would like to retain existing data in table.
#sl = SiteLogic(True)
sl = SiteLogic(False)


def main():
    global sl
    sl.sensorLoop()

    # Start flask.
    app.run(host='0.0.0.0', port = 80, debug = True, threaded = False)


if __name__ == '__main__':
    # Thank you Mario!
    # But our main() is in another castle. 
    main()
