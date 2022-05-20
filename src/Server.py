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
    # !!! IMPLEMENT !!!
    # Try to make this return "rows" instead of whatever result from execute()

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
        

        # Clear old database entries.
        if not (persist):
            self.__execQuery("DROP TABLE IF EXISTS water;")

        # Data table.
        self.__execQuery(
            "CREATE TABLE IF NOT EXISTS water(" +
            "readingId SERIAL PRIMARY KEY NOT NULL, " +
            "timestamp VARCHAR(20) NOT NULL," +
            "moisture VARCHAR(20) NOT NULL);"
        )

        # Clear old database entries.
        if not (persist):
            self.__execQuery("DROP TABLE IF EXISTS light;")

        self.__execQuery(
            "CREATE TABLE IF NOT EXISTS light("
            "readingId SERIAL PRIMARY KEY NOT NULL, " +
            "timestamp VARCHAR(20) NOT NULL," +
            "light VARCHAR(20) NOT NULL);"
        )

        # Clear old database entries.
        if not (persist):
            self.__execQuery("DROP TABLE IF EXISTS button;")

        self.__execQuery(
            "CREATE TABLE IF NOT EXISTS button("
            "readingId SERIAL PRIMARY KEY NOT NULL, " +
            "timestamp VARCHAR(20) NOT NULL," +
            "state VARCHAR(20) NOT NULL);"
        )

        # Settings table.
        #if not (persist):
            #self.__execQuery("DROP TABLE IF EXISTS settings;")

        #self.__execQuery(
            #"CREATE TABLE IF NOT EXISTS settings" +
            #"(name VARCHAR(22) PRIMARY KEY NOT NULL, " +
            #"state VARCHAR(22) NOT NULL);"
        #)
        
        # Set defaults.
        #with self.__conn:
            #cursor = self.__conn.cursor()
            # This is wrapped in a try because it will fail when
            #+persistence is turned on and we don't really care as long as it
            #+exists.
            #try:
                #cursor.execute(
                    #"INSERT INTO settings VALUES('target', '25.00');" +
                    #"INSERT INTO settings VALUES('power', '0');" +
                    #"INSERT INTO settings VALUES('heating', '0');")
                #self.__conn.commit()
            #except:
                #pass
            #cursor.close()

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
        
        print("mqtt loop init complete")

    # !!! IMPLEMENT !!!
    # Filter for which sensor the data has come from using message.topic.
    # Jam into database.
    # Do some logic to determine whether something should turn on or off.
    # Time getter
    def getTime(self):
        return datetime.now().strftime("%H:%M:%S")

    # !!! FIX !!!
    # THIS IS BROKEN DUE TO DATABASE CHANGES.
    # Most recent readings DB getter.
    def getDBRecent(self, ammount):
        query =  "SELECT timestamp, moisture, light FROM statistics "
        query += "ORDER BY readingId DESC LIMIT " + str(ammount) + ";"

        return __execQuery(query)

    def setDBMoisture(self, moisture):
        __execQuery(
            "INSERT INTO moisture VALUES('" +
            getTime() + "', '" + moisture + "');"
        )
    
    def setDBLight(self, light):
        __execQuery(
            "INSERT INTO light VALUES('" +
            getTime() + "', '" + light + "');"
        )

    # !!! IMPLEMENT !!!
    def getDBRecMoist(self, ammount):
        pass
    
    # !!! IMPLEMENT !!!
    def getDBRecLight(self, ammount):
        pass

    # !!! IMPLEMENT !!!
    def getDBAveMoist(self, ammount):
        pass

    # !!! IMPLEMENT !!!
    def getDBAveLight(self, ammount):
        pass
    
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
    # Subscribe to arduino[number]/#
    # # : denotes wildcard
    topic = "arduino" + str(userdata) + "/#"
    #topic = "arduino1" 
    # Resub here so it doesn't lose subscriptions on reconnect.
    #print(  "Subscribing to " + topic + " on " + str(sys.argv[userdata]) + ".")
    print("Attempting subscription to " + topic + ".")
    thisclient.subscribe(topic)
    print("Subscribed.")

# Function bound to pahoMQTT
# thisclient : ?
# userdata : ?
# message : The message that was received.
def on_message(thisclient, userdata, message):
    global sl
    # Debug code to display messages as they're received.
    print(str(message.topic) + " " + str(message.payload))


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
