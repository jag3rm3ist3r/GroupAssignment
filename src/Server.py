# IOT Assignment RPI python script
# arg 1 : serial device file

#import serial
import time
from datetime import datetime
# postgresql
import psycopg2
#import thread
# CLI arguments
import sys
# regex
#import re
# Floating point logic is complete garbage so I'm trying Decimal.
from decimal import Decimal
# Flask for webpage
from flask import Flask, render_template
# MQTT for communication with ThingsBoard and both Nodes.
import paho.mqtt.publish as mqttpublish
import paho.mqtt.client as mqttclient
# pdb debugger
#import pdb; pdb.set_trace()




# Flask init.
app = Flask(__name__)




# Brains of the Flask website.
class SiteLogic:
    # Generic function for executing queries that
    #+don't require much any extra interaction.
    def __execQuery(self, query):
        rows = None
        
        with self.__conn:
            cursor = self.__conn.cursor()
            result = cursor.execute(query)
            self.__conn.commit()
            # Sometimes this will complain that there are no rows, ignore it.
            try:
                rows = cursor.fetchall()
            except:
                pass
            cursor.close()
        
        return rows
            

    # siteLogic constructor
    def __init__(self, persist):
        # SQL connection
        self.__conn = psycopg2.connect(
            database="pi",
            user = "pi",
            password = "pi",
            host = "127.0.0.1",
            port = "5432")
        
        # WATER
        # Clear old database entries.
        if not (persist):
            self.__execQuery("DROP TABLE IF EXISTS water;")

        # Data table.
        self.__execQuery(
            "CREATE TABLE IF NOT EXISTS water(" +
            "readingId SERIAL PRIMARY KEY NOT NULL, " +
            "timestamp VARCHAR(20) NOT NULL," +
            "source VARCHAR(20) NOT NULL," +
            "state VARCHAR(20) NOT NULL);"
        )

        # LIGHT
        # Clear old database entries.
        if not (persist):
            self.__execQuery("DROP TABLE IF EXISTS light;")

        self.__execQuery(
            "CREATE TABLE IF NOT EXISTS light("
            "readingId SERIAL PRIMARY KEY NOT NULL, " +
            "timestamp VARCHAR(20) NOT NULL," +
            "source VARCHAR(20) NOT NULL," +
            "state VARCHAR(20) NOT NULL);"
        )

        # BUTTON
        # Clear old database entries.
        if not (persist):
            self.__execQuery("DROP TABLE IF EXISTS button;")

        self.__execQuery(
            "CREATE TABLE IF NOT EXISTS button("
            "readingId SERIAL PRIMARY KEY NOT NULL, " +
            "timestamp VARCHAR(20) NOT NULL," +
            "source VARCHAR(20) NOT NULL," +
            "state BOOLEAN NOT NULL);"
        )

        # Settings table.
        if not (persist):
            self.__execQuery("DROP TABLE IF EXISTS settings;")

        self.__execQuery(
            "CREATE TABLE IF NOT EXISTS settings" +
            "(name VARCHAR(22) PRIMARY KEY NOT NULL, " +
            "state VARCHAR(22) NOT NULL);"
        )
        
        # Set defaults.
        with self.__conn:
            cursor = self.__conn.cursor()
            #This is wrapped in a try because it will fail when
            #+persistence is turned on and we don't really care as long as it
            #+exists.
            try:
                cursor.execute(
                    "INSERT INTO settings VALUES('edge_count', '0');"
                )
                self.__conn.commit()
            except:
                pass
            cursor.close()

    def initMQTT(self):
        # MQTT Client initializaiton.
        self.__client = []
        # argv[0] : this file
        # argv[1] : ammount of instances
        # argv[2] : ip address of this computer
        # Add a client for every IP passed as an argument.
        for i in range(int(sys.argv[1])):
            # User userdata as the index for if we don't know which client is
            #+calling a function.
            self.__client.append(mqttclient.Client(userdata=str(i)))
            print("Creating MQTT client instance " + str(i))
            self.__client[i].on_connect = on_connect
            self.__client[i].on_message = on_message

            # Initialize MQTT connection.
            port = 1883
            print("Attempting to connect on " + sys.argv[2] + ":" + str(port))
            # args: host, port, keepalive
            self.__client[i].connect(sys.argv[2], port, 60)

        # Start MQTT loop(s).
        for i in range(len(self.__client)):
            print("Starting loop " + str(self.__client[i]))
            self.__client[i].loop_start()
        
        self.setDBEdgeCount(len(self.__client))
        
        print("mqtt init loop complete")

    # Time getter
    def getTime(self):
        return datetime.now().strftime("%H:%M:%S")

    # Setter for DB edge count.
    def setDBEdgeCount(self, count):
        self.__execQuery(
            "UPDATE settings SET state='" + str(count) +
            "' WHERE name='edge_count';"
        )
    
    # Getter for DB edge count.
    def getDBEdgeCount(self):
        return self.__execQuery(
            "SELECT state FROM settings " +
            "WHERE name='edge_count';"
        )

    # Setter for DB moisture readings.
    def setDBMoisture(self, source, moisture):
        self.__execQuery(
            "INSERT INTO moisture VALUES('" +
            self.getTime() + "', '" +
            str(source) + "', '" +
            str(moisture) + "');"
        )
    
    # Setter for DB light readings.
    def setDBLight(self, source, light):
        self.__execQuery(
            "INSERT INTO light VALUES('" +
            self.getTime() + "', '" +
            str(source) + "', '" +
            str(light) + "');"
        )

    # Setter for DB moisture readings.
    def setDBButton(self, source, state):
        self.__execQuery(
            "INSERT INTO button VALUES('" +
            self.getTime() + "', '" +
            str(source) + "', '" +
            str(state) + "');"
        )

    # Getter for most recent DB moisture reading.
    def getDBMoisture(self):
        # Buffer result.
        result = self.__execQuery(
            "SELECT state FROM water " +
            "ORDER BY readingId DESC LIMIT 2;"
        )
        # Only return first row.
        return result[0]

    # Getter for most recent DB light reading.
    def getDBLight(self):
        result = self.__execQuery(
            "SELECT state FROM light " +
            "ORDER BY readingId DESC LIMIT 2;"
        )
        return result[0]

    # Getter for most recent # DB moisture readings.
    def getDBRecMoist(self, ammount):
        return self._execQuery(
            "SELECT timestamp, source, state FROM water " +
            "ORDER BY readingId DESC LIMIT " + str(ammount) + ";"
        )
    
    # Getter for most recent # DB light readings.
    def getDBRecLight(self, ammount):
        return self.__execQuery(
            "SELECT timestamp, source, state FROM light " +
            "ORDER BY readingId DESC LIMIT " + str(ammount) + ";"
        )

    # Getter for average of last # DB moisture readings.
    def getDBAveMoist(self, ammount):
        return self.__execQuery(
            "SELECT AVG(state) FROM water " +
            "ORDER BY readingId DESC LIMIT " + str(ammount) + ";"
        )

    # Getter for average of last # DB light readings.
    def getDBAveLight(self, ammount):
        return self.__execQuery(
            "SELECT AVG(state) FROM light " +
            "ORDER BY readingId DESC LIMIT " + str(ammount) + ";"
        )
    
    # Template data getter
    # I am aware that using separate functions to make multiple
    #+SQL queries is inefficient but this doesn't need to be perfect.
    def getTemplateData(self):
        return {
            'moisture' : self.getDBMoisture(),
            'light' : self.getDBLight(),
            'recentmoist' : self.getDBRecMoist(20),
            'recentlight' : self.getDBRecLight(20),
            'time' : self.getTime(),
            'averagemoist' : self.getDBAveMoist(100),
            'averagelight' : self.getDBAveLight(100)
        }


# Function bound to pahoMQTT
# thisclient : ?
# userdata : ?
# flags : ?
# rc : Result code
def on_connect(thisclient, userdata, flags, rc):
    global sl
    print("Connected with result code: " + str(rc))
    # Subscribe to edge[number]data/#
    # # : denotes wildcard
    topic = "edge" + str(userdata) + "data/#"
    # Resub here so it doesn't lose subscriptions on reconnect.
    print("Attempting subscription to " + topic + ".")
    thisclient.subscribe(topic)
    print("Subscribed.")

# Function bound to pahoMQTT
# thisclient : ?
# userdata : ?
# message : The message that was received.
def on_message(thisclient, userdata, message):
    global sl

    # Create an array of the topic sections.
    topicSplit = message.topic.split("/")
    # Get 5th character of first section of topic.
    #
    # edge#data
    #     ^
    # 012345678
    #
    # This is the number of the edge device.
    # This number may not correspond to the index it is stored at on this end.
    source = topicSplit[0][4]

    # !!! DEBUG CODE !!!
    # Debug code to display messages as they're received.
    print("")
    print("DEBUG on_message debug info")
    print("message.topic : " + str(message.topic))
    print("message.payload : " + str(message.payload))
    print("topicSplit[0] : " + str(topicSplit[0]))
    print("topicSplit[1] : " + str(topicSplit[1]))
    print("source : " + str(source))
    print("")


    # Check what the topic is, store information in that table.
    # Sadly match - case was introduced in a later version of python.
    if(topicSplit[1] == "water_level"):
        sl.setDBMoisture(source, message.payload)

    if(topicSplit[1] == "light_level"):
        sl.setDBLight(source, message.payload)

    if(topicSplit[1] == "button"):
        sl.setDBButton(source, message.payload)


# index.html file operation
@app.route("/")
def index():
    #global sl
    # This data will be sent to index.html
    templateData = sl.getTemplateData()
    return render_template('index.html', **templateData)


def main():
    #global sl
    # Set argument to true if you would like to retain existing data in table.
    sl = SiteLogic(False)
    # Setup MQTT, which relies on sl being defined first.
    sl.initMQTT()

    # This delay is here so init messages don't get mixed up with flask ones.
    time.sleep(5)

    # Start flask.
    app.run(
        host = '0.0.0.0',
        port = 80,
        debug = True,
        threaded = False,
        use_reloader=False)


if __name__ == '__main__':
    # Thank you Mario!
    # But our main() is in another castle. 
    main()
