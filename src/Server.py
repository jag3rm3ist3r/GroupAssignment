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
# Required for weather.
import requests
import json
# pdb debugger
#import pdb; pdb.set_trace()




# Flask init.
app = Flask(__name__)

# Global constants
EDGE_COUNT=int(sys.argv[1])
HOSTNAME=sys.argv[2]
EDGE_NUMBERING_OFFSET = 1
WEATHER_URL = "https://api.open-meteo.com/v1/forecast?latitude=-37.840&longitude=144.946&daily=precipitation_sum&timezone=Australia%2FSydney"
ACCESS_TOKEN = '7JXPZYpKiPk3gLl8wyhM'
THINGSBOARD_ADDRESS = 'thingsboard.cloud'



# Brains of the Flask website.
class SiteLogic:
	# Generic function for executing queries that
	#+don't require much any extra interaction.
	def __execQuery(self, query):
		# !!! DEBUG !!!
		#print(query)
		rows = None
		
		with self.__conn:
			cursor = self.__conn.cursor()
			cursor.execute(query)
			# Sometimes this will complain that there are no rows, ignore it.
			try:
				rows = cursor.fetchall()
			except:
				pass
			self.__conn.commit()
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
		
		# MOISTURE
		# Clear old database entries.
		if not (persist):
			self.__execQuery("DROP TABLE IF EXISTS moisture;")

		self.__execQuery(
			"CREATE TABLE IF NOT EXISTS moisture(" +
			"readingId SERIAL PRIMARY KEY NOT NULL, " +
			"timestamp VARCHAR(20) NOT NULL," +
			"source VARCHAR(20) NOT NULL," +
			"state DECIMAL NOT NULL);"
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
			"state DECIMAL NOT NULL);"
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
		# Always drop.
		#if not (persist):
		self.__execQuery("DROP TABLE IF EXISTS settings;")

		self.__execQuery(
			"CREATE TABLE IF NOT EXISTS settings" +
			"(settingId SERIAL PRIMARY KEY NOT NULL, "
			"name VARCHAR(22) NOT NULL, " +
			"state VARCHAR(22) NOT NULL,"
			"edgeId VARCHAR(22));"
		)

		# Go get the latest weather.
		self.updateAPIWeather()

	def initMQTT(self):
		global EDGE_NUMBERING_OFFSET
		global HOSTNAME
		global EDGE_COUNT
		# MQTT Client initializaiton.
		self.__client = []
		# argv[0] : this file
		# argv[1] : ammount of instances
		# argv[2] : ip address of this computer
		# Add a client for every IP passed as an argument.
		for i in range(int(EDGE_COUNT)):
			# User userdata as the index for if we don't know which client is
			#+calling a function.
			self.__client.append(
				mqttclient.Client(userdata=str(i + EDGE_NUMBERING_OFFSET))
			)
			#print("Creating MQTT client instance " + str(i))
			self.__client[i].on_connect = on_connect
			self.__client[i].on_message = on_message

			# Initialize MQTT connection.
			port = 1883
			#print("Attempting to connect on " + HOSTNAME + ":" + str(port))
			# args: host, port, keepalive
			self.__client[i].connect(HOSTNAME, port, 60)

		# Start MQTT loop(s).
		for i in range(len(self.__client)):
			#print("Starting loop " + str(self.__client[i]))
			self.__client[i].loop_start()
		
		# Little sanity check.
		assert len(self.__client) == EDGE_COUNT
				
		# Set defaults for settings table.
		# This is done here since we don't know how many edge devices there are
		#+up until this point.
		for i in range(EDGE_COUNT):
			j = i + EDGE_NUMBERING_OFFSET
			'''
			with self.__conn:
				cursor = self.__conn.cursor()
				#This is wrapped in a try because it will fail when
				#+persistence is turned on and we don't really care as long as
                #+it exists.
				try:
					# Changes what number we start counting from.
					cursor.execute(
						"INSERT INTO settings (name, state, edgeId) " +
						"VALUES('target_moisture', '0', '" + j + "');"
					)
					self.__conn.commit()
				except:
					pass
				cursor.close()
			'''
			self.__execQuery(
				"INSERT INTO settings (name, state, edgeId) " +
				"VALUES('target_moisture', '0', '" + str(j) + "');"
			)
			self.__execQuery(
				"INSERT INTO settings (name, state, edgeId) " +
				"VALUES('target_light', '50', '" + str(j) + "');"
			)
			self.__execQuery(
				"INSERT INTO settings (name, state, edgeId) " +
				"VALUES('target_rain', '0', '" + str(j) + "');"
			)
			

		self.__tbClient = mqttclient.Client("ThingsBoard")
		self.__tbClient.username_pw_set(ACCESS_TOKEN)
		self.__tbClient.connect(THINGSBOARD_ADDRESS, 1883, 60) 

		#print("mqtt init loop complete")

	# Time getter
	def getTime(self):
		return datetime.now().strftime("%H:%M:%S")

	# Getter for DB moisture target.
	def getDBTargetMoistById(self, edgeId):
		return self.__execQuery(
			"SELECT state FROM settings " +
			"WHERE name='target_moisture' " +
			"AND edgeId='" + str(edgeId) + "';"
		)[0][0]
	def getDBTargetMoist(self):
		return self.__execQuery(
			"SELECT state, edgeId FROM settings " +
			"WHERE name='target_moisture' " +
			"ORDER BY edgeId;"
		)

	# Setter for DB moisture target.
	def setDBTargetMoist(self, edgeId, state):
		self.__execQuery(
			"UPDATE settings SET " +
			"state='" + str(state) + "' " +
			"WHERE name='target_moisture' " +
			"AND edgeId='" + str(edgeId) + "';"
		)

	# Getter for DB rain target.
	def getDBTargetRainById(self, edgeId):
		return self.__execQuery(
			"SELECT state FROM settings " +
			"WHERE name='target_rain' " +
			"AND edgeId='" + str(edgeId) + "';"
		)[0][0]

	# Getter for DB rain targets.
	def getDBTargetRain(self):
		return self.__execQuery(
			"SELECT state, edgeId FROM settings " +
			"WHERE name='target_rain' " +
			"ORDER BY edgeId;"
		)

	# Setter for DB rain target.
	def setDBTargetRain(self, edgeId, state):
		self.__execQuery(
			"UPDATE settings SET " +
			"state='" + str(state) + "' " +
			"WHERE name='target_rain' " +
			"AND edgeId='" + str(edgeId) + "';"
		)

	# Getter for DB light target
	def getDBTargetLightById(self, edgeId):
		return self.__execQuery(
			"SELECT state FROM settings " +
			"WHERE name='target_light' " +
			"AND edgeId='" + str(edgeId) + "';"
		)[0][0]
	def getDBTargetLight(self):
		return self.__execQuery(
			"SELECT state, edgeId FROM settings " +
			"WHERE name='target_light' " +
			"ORDER BY edgeId;"
		)
 
	# Setter for DB light target.
	def setDBTargetLight(self, edgeId, state):
		self.__execQuery(
			"UPDATE settings SET " +
			"state='" + str(state) + "' " +
			"WHERE name='target_light' " +
			"AND edgeId='" + str(edgeId) + "';"
		)

	# Setter for DB moisture readings.
	def setDBMoisture(self, source, state):
		self.__execQuery(
			"INSERT INTO moisture (timestamp, source, state) VALUES('" +
			self.getTime() + "', '" +
			str(source) + "', '" +
			str(state) + "');"
		)
	
	# Setter for DB light readings.
	def setDBLight(self, source, state):
		self.__execQuery(
			"INSERT INTO light (timestamp, source, state) VALUES('" +
			self.getTime() + "', '" +
			str(source) + "', '" +
			str(state) + "');"
		)

	# Setter for DB moisture readings.
	def setDBButton(self, source, state):
		self.__execQuery(
			"INSERT INTO button (timestamp, source, state) VALUES('" +
			self.getTime() + "', '" +
			str(source) + "', '" +
			str(state) + "');"
		)

	# Getter for most recent DB moisture reading.
	def getDBMoisture(self):
		# Buffer result.
		return self.__execQuery(
			"SELECT s.readingId, s.state, s.source " +
			"FROM moisture s " +
			"JOIN (SELECT MAX(readingId) AS id " +
			"FROM moisture " +
			"GROUP BY source) max " +
			"ON s.readingId = max.id " +
			"ORDER BY s.source;"
		)

	# Getter for most recent DB light reading.
	def getDBLight(self):
		return self.__execQuery(
			"SELECT s.readingId, s.state, s.source " +
			"FROM light s " +
			"JOIN (SELECT MAX(readingId) AS id " +
			"FROM light " +
			"GROUP BY source) max " +
			"ON s.readingId = max.id " +
			"ORDER BY s.source;"
		)

	# Getter for most recent # DB moisture readings.
	def getDBRecMoist(self, ammount):
		return self.__execQuery(
			"SELECT timestamp, source, state FROM moisture " +
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
			"SELECT AVG(state) FROM moisture " +
			"GROUP BY state LIMIT " + str(ammount) + ";"
		)[0]
	
	def getDBAveMoistById(self, source, ammount):
		return self.__execQuery(
			"SELECT AVG(state) " +
			"FROM moisture "
			"WHERE source='" + str(source) + "' " +
			"LIMIT " + str(ammount) + ";"
		)

	def getDBAveLightById(self, source, ammount):
		return self.__execQuery(
			"SELECT AVG(state) " +
			"FROM light "
			"WHERE source='" + str(source) + "' " +
			"LIMIT " + str(ammount) + ";"
		)

	# Getter for average of last # DB light readings.
	def getDBAveLight(self, ammount):
		return self.__execQuery(
			"SELECT AVG(state) FROM light " +
			"GROUP BY state LIMIT " + str(ammount) + ";"
		)[0]
	
	# Template data getter
	# I am aware that using separate functions to make multiple
	#+SQL queries is inefficient but this doesn't need to be perfect.
	def getTemplateData(self):
		return {
			'time' : self.getTime(),
			'moisture' : self.getDBMoisture(),
			'light' : self.getDBLight(),
			'moisttarget' : self.getDBTargetMoist(),
			'lighttarget' : self.getDBTargetLight(),
			'recentmoist' : self.getDBRecMoist(10),
			'recentlight' : self.getDBRecLight(10),
			'weather' : self.getAPIWeatherRain(),
			'raintarget' : self.getDBTargetRain()
		}
	
	# Fetch new weather data.
	def updateAPIWeather(self):
		global WEATHER_URL

		self.request = requests.get(WEATHER_URL, timeout=5)
		self.weather = json.loads(self.request.content)

	# Returns an array where rain[0] is today's rain in mm and rain[1] is
	#+tomorrow etc.
	def getAPIWeatherRain(self):
		return self.weather['daily']['precipitation_sum']
	
	# Supply water to the specified plant.
	def supplyWater(self, client):
		global HOSTNAME
		topic = "edge" + str(client) + "actions/pump"
		payload = "THIS IS IGNORED."
		# !!! DEBUG MESSAGE !!!
		print("Topic: " + topic + " | Payload: " + payload)
		mqttpublish.single(topic, payload, hostname=HOSTNAME)

	def sendMQTTThingsBoard(self, data):
		#print("DEBUG inside")
		#print(data)
		#print(json.dumps(data))
		self.__tbClient.publish("v1/devices/me/telemetry", json.dumps(data))


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
	'''
	print("")
	print("DEBUG on_message debug info")
	print("message.topic : " + str(message.topic))
	print("message.payload : " + str(message.payload))
	print("topicSplit[0] : " + str(topicSplit[0]))
	print("topicSplit[1] : " + str(topicSplit[1]))
	print("source : " + str(source))
	'''

	# Check what the topic is, store information in that table.
	# Sadly match - case was introduced in a later version of python.
	if(topicSplit[1] == "water_level"):
		#print("Logging moisture : " + message.payload)
		sl.setDBMoisture(source, message.payload)

	print("1")

	if(topicSplit[1] == "light_level"):
		#print("Logging light level : " + message.payload)
		sl.setDBLight(source, message.payload)

	print("2")

	if(topicSplit[1] == "button"):
		#print("Logging button press : " + message.payload)
		sl.setDBButton(source, message.payload)

	print("3")

	needsWater = False
	willRain = False
	tooSunny = False
	# Check if the plant needs water.
	if(sl.getDBAveMoistById(source, 20) < sl.getDBTargetMoistById(source)):
		needsWater = True

	print("4")

	# Check if there will be enough water today to water the plant.
	if(sl.getAPIWeatherRain()[0] > sl.getDBTargetRainById(source)):
		willRain = True

	print("5")

    # Check if it's too sunny to bother with watering the plants.
	if(sl.getDBAveLightById(source) > sl.getDBTargetLightById(source)):
		tooSunny = True

	print("6")

	# Supply water if needed.
	if(needsWater == True and willRain == False and tooSunny == False):
		sl.supplyWater(source)

	# !!! DEBUG CODE !!!
	#sl.supplyWater(source)
	# !!! END DEBUG CODE !!!

	# Send data to ThingsBoard.
	data = {}
	#print("Populate: dict data")
	data[message.topic] = message.payload
	if(needsWater):
		data["watered"] = "0"
	else:
		data["watered"] = "1"

	# Check if the button was pressed and assume watered if it was since that's
	#+what the button does.
	if(topicSplit[1] == "button"):
		data["watered"] = str(message.payload)

	# Send data onward to ThingsBoard.
	sl.sendMQTTThingsBoard(data)


@app.route("/pumpbutton/<source>")
def pumpButton(source):
	global sl
	sl.supplyWater(source)
	templateData = sl.getTemplateData()
	return render_template('index.html', **templateData)

# index.html file operation
@app.route("/")
def index():
	global sl
	# This data will be sent to index.html
	templateData = sl.getTemplateData()
	return render_template('index.html', **templateData)

# Increment/decrement the specified target.
@app.route("/<targetName>/<edgeId>/<direction>")
def adjustTarget(targetName, edgeId, direction):
	global sl
	newVal = 0
	# Adjust moisture.
	if (targetName == 'moisture'):
		if(direction == 'up'):
			newVal = Decimal(sl.getDBTargetMoistById(edgeId)) + Decimal(1.00)
		else:
			newVal = Decimal(sl.getDBTargetMoistById(edgeId)) - Decimal(1.00)
		
		sl.setDBTargetMoist(edgeId, newVal)

	# Adjust light.
	if (targetName == 'light'):
		if(direction == 'up'):
			newVal = Decimal(sl.getDBTargetLightById(edgeId)) + Decimal(1.00)
		else:
			newVal = Decimal(sl.getDBTargetLightById(edgeId)) - Decimal(1.00)
	
		sl.setDBTargetLight(edgeId, newVal)

	# Adjust rain.
	if (targetName == 'rain'):
		if(direction == 'up'):
			newVal = Decimal(sl.getDBTargetRainById(edgeId)) + Decimal(1.00)
		else:
			newVal = Decimal(sl.getDBTargetRainById(edgeId)) - Decimal(1.00)

		sl.setDBTargetRain(edgeId, newVal)

	templateData = sl.getTemplateData()
	return render_template('index.html', **templateData)


def main():
	global sl
	# Set argument to true if you would like to retain existing data in table.
	sl = SiteLogic(False)
	# Setup MQTT, which relies on sl being defined first.
	sl.initMQTT()

	# This delay is here so init messages don't get mixed up with flask ones.
	time.sleep(3)

	# Start flask.
	app.run(
		host = '0.0.0.0',
		port = 80,
		debug = True,
		threaded = False,
		use_reloader=False
	)


if __name__ == '__main__':
	# Thank you Mario!
	# But our main() is in another castle. 
	main()


'''
# MQTT example code

import paho.mqtt.client as mqtt
import time
import json

ACCESS_TOKEN = '7JXPZYpKiPk3gLl8wyhM'
THINGSBOARD_ADDRESS = 'thingsboard.cloud'

client = mqtt.Client()

client.username_pw_set(ACCESS_TOKEN)
client.connect(THINGSBOARD_ADDRESS, 1883, 60)
client.loop_start()
data = {}
data['water_level'] = 7

while(True):
	client.publish("v1/devices/me/telemetry", json.dumps(data))
	time.sleep(5)

'''
