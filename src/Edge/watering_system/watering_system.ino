/*  IOT Individual Practical Assignment 
 *   Etienne Bovet 103168804
*/
const int buttonPin = 6;
int buttonState;

int lastButtonState = LOW;

unsigned long lastDebounceTime = 0;  // the last time the output pin was toggled
unsigned long debounceDelay = 50;    // the debounce time; increase if the output flickers

float soilVal = 0; //value for storing moisture value
float lightVal = 0;
const int lightPin = A0;
const int soilPin = A2;
const int soilPower = 2;//Soil Moisture Sensor Power
const int pumpPower = 4;
const int ledPower = 8;

bool shouldPump = false;
bool buttonPressed = false;
bool shouldFlash = false;

void setup() 
{
  Serial.begin(9600);   // open serial

  pinMode(buttonPin, INPUT);
  //  Set Digital power pins as output and initialized as off
  pinMode(soilPower, OUTPUT);
  pinMode(pumpPower, OUTPUT);
  pinMode(ledPower, OUTPUT);
  digitalWrite(soilPower, LOW);
  digitalWrite(pumpPower, LOW);
}

void loop() 
{

  //Check if there is serial input data available 
   while (Serial.available()>0)
   {
      //Read serial input
      int value = Serial.read();
      if (value == '1')
      {
        shouldPump = true;
      }
      if (value == '2')
      {
        shouldFlash = true;
      }
   }
  int reading = digitalRead(buttonPin);
  if (reading != lastButtonState) 
  {
    // reset the debouncing timer
    lastDebounceTime = millis();
  }
  if ((millis() - lastDebounceTime) > debounceDelay) 
  {
    // whatever the reading is at, it's been there for longer
    // than the debounce delay, so take it as the actual current state:

    // if the button state has changed:
    buttonState = reading;
    if (buttonState == HIGH) 
    {
      buttonPressed = true;
      shouldPump = true;
      digitalWrite(pumpPower, LOW);
    }
  }
  
  lastButtonState = reading;
  
  soilVal = (readSoil())/900*100; //Value in percent of max
  lightVal = (readLight())/1030*100; //Value in percent of max
  
  
  //Rate of sensor readings
  delay(5000);

  serialPrint();
  activatePump();
  flashLED();

  buttonPressed = false;
  shouldPump = false;
  shouldFlash = false;

}

float readSoil()
{

    digitalWrite(soilPower, HIGH);
    delay(10);//wait 10 milliseconds 
    soilVal = analogRead(soilPin);
    digitalWrite(soilPower, LOW);
    return soilVal;
}

float readLight()
{
    lightVal = analogRead(lightPin);//Read the SIG value form sensor 
    return lightVal;
}

void serialPrint()
{
  if(shouldPump)
  {
     Serial.println("watered = 1");
  }
  else
  {
     Serial.println("watered = 0");
  }
  if(buttonPressed)
  {
     Serial.println("button = 1");
  }
  else
  {
     Serial.println("button = 0");
  }
  Serial.print("water_level = ");
  Serial.println(soilVal);
  Serial.print("light_level = ");
  Serial.println(lightVal);
}

void flashLED()
{
  if(shouldFlash)
  {
    digitalWrite(ledPower, HIGH);
    delay(1000);
    digitalWrite(ledPower, LOW);
  }
}

void activatePump()
{
  if(shouldPump)
  {
    digitalWrite(pumpPower, HIGH);
    delay(2000);
    digitalWrite(pumpPower, LOW);
  }
}
