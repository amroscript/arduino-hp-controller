// Author: Amro Farag
// Date: March 2024

#include <Adafruit_MAX31865.h> // PT100 library
#include <Wire.h>  // Wire library for I2C communication
#include <RTClib.h>  // Real Time Clock library
#include "DFRobot_GP8XXX.h" // Digital-to-Analog Converter (DAC) library

// Initialize the MAX31865 RTD sensor, RTC, and DAC with their respective settings
RTC_DS3231 rtc; // Real Time Clock (RTC) object
DFRobot_GP8403 dac(DFGP8XXX_I2C_DEVICEADDR, RESOLUTION_12_BIT); // DAC object

// Define pin for heating control and initialize variables for temperature, flow rate, etc.
const int heatingPin = 5; // Digital pin for heating control relay or transistor
float flowRate = 0.0; // Flow rate variable
float targetTemperature = 25.0; // Default target temperature in Celsius
float tolerance = 0.2; // Temperature tolerance in Celsius
float desiredVoltage = 0.0; // Desired voltage to be set on the DAC
float dacVoltage = 0.0;
float correctionFactor = 0.891;

void setup() {
  Serial.begin(115200); // Begin Serial communication at 115200 baud rate
  while (!Serial) { ; } // Wait for the serial port to connect. 

  if (!rtc.begin()) { // Check if the RTC is connected and working
    Serial.println("Couldn't find RTC");
    while (1); // Infinite loop if RTC not found
  }
  if (rtc.lostPower()) { // Check if the RTC lost power and needs its time reset
    rtc.adjust(DateTime(F(__DATE__), F(__TIME__))); // Set RTC to the date & time this sketch was compiled
  }

  if (dac.begin() == 0) { // Initialize the DAC
    Serial.println("DAC initialized successfully.");
    dac.setDACOutRange(DFRobot_GP8XXX::eOutputRange10V); // Set DAC output range 
  } else {
    Serial.println("Couldn't initialize DAC. Check wiring!");
    while (1); // Infinite loop if DAC not found
  }

  pinMode(heatingPin, OUTPUT); // Set the heating control pin as an output
}

void loop() {
  if (Serial.available() > 0) { // Check if data is available to read from the serial port
    String command = Serial.readStringUntil('\n'); // Read the incoming string until newline
    processSerialCommand(command); // Process the received serial command
  }

  float temperature = readTemperature(A2); 
  float sensorVoltage = readAnalogVoltage(A0); // Read the analog voltage from a sensor 
  float returnTemperature = readreturnTemperature(A1);

  flowRate = calculateFlowRate(sensorVoltage); // Calculate flow rate based on sensor voltage
  
  setDACVoltage(desiredVoltage); // Update the DAC output voltage
  controlHeating(temperature, targetTemperature, tolerance); // Control heating element based on temperature

  sendSerialData(temperature, desiredVoltage, sensorVoltage, flowRate, returnTemperature); // Send data over serial

  delay(750); // Delay for a second before repeating the loop
}


float readTemperature(int pin) {
  int supSensorValue = analogRead(pin);
  float voltage = supSensorValue * (5.0 / 1023.0); // Convert the sensor reading to a voltage (0V to 5V)
  float temperature = (voltage * 70.0) / 5.0; // The voltage range 0V to 5V corresponds to temperature range 0°C to 70°C
  return temperature;
}

 // Function to read temperature from (more stable) temperature sensor
float readreturnTemperature(int pin) { 
  int retsensorValue = analogRead(pin);
  float voltage = retsensorValue * (5.0 / 1023.0); // Convert the sensor reading to a voltage (0V to 5V)
  float returnTemperature = (voltage * 70.0) / 5.0; // The voltage range 0V to 5V corresponds to temperature range 0°C to 70°C
  return returnTemperature;
}

// Function to read analog voltage
float readAnalogVoltage(int pin) {
  int sensorValue = analogRead(pin);
  float voltage = sensorValue * (5.0 / 1023.0); // Convert to voltage (assuming 5V reference)
  return voltage;
}


// Function to calculate flow rate based on sensor voltage (Example function, implement according to your sensor)
float calculateFlowRate(float sensorVoltage) {
  flowRate = sensorVoltage * (1.0 / 5.0);
  return flowRate;
}

// Function to set DAC voltage
void setDACVoltage(float voltage) {
  // Apply the correction factor to the commanded voltage
  float correctedVoltage = voltage * correctionFactor;

  // Ensure correctedVoltage is within the DAC's allowable range
  correctedVoltage = constrain(correctedVoltage, 0.0, 10.0); // Assuming the DAC's range is 0-5V

  uint16_t dacValue = static_cast<uint16_t>((correctedVoltage / 10.0) * 4095);
  dac.setDACOutVoltage(dacValue, 0); // Set voltage on DAC channel 0
  
  // Update the global dacVoltage variable to reflect the corrected voltage being set
  dacVoltage = correctedVoltage;
}

// Function to control heating based on the current and target temperature
void controlHeating(float currentTemperature, float targetTemp, float tempTolerance) {
  if (currentTemperature < targetTemp - tempTolerance) {
    digitalWrite(heatingPin, HIGH); // Turn on heating element
  } else if (currentTemperature > targetTemp + tempTolerance) {
    digitalWrite(heatingPin, LOW); // Turn off heating element
  }
}

// Function to send collected data over serial
void sendSerialData(float temperature, float dacVoltage, float sensorVoltage, float flowRate, float returnTemperature) {
  Serial.print("STemp:");
  Serial.print(temperature);
  Serial.print(", DACVolt:");
  Serial.print(dacVoltage);
  Serial.print(", SensorVolt:");
  Serial.print(sensorVoltage);
  Serial.print(", FlowRate:");
  Serial.print(flowRate, 3);
  Serial.print(", RTemp:");
  Serial.println(returnTemperature);
}


// Function to process commands received from the serial port
void processSerialCommand(String command) {
  if (command.startsWith("setTemp ")) {
    targetTemperature = command.substring(8).toFloat();
    Serial.print("New target temperature: ");
    Serial.println(targetTemperature);
  } else if (command.startsWith("setTolerance ")) {
    tolerance = command.substring(13).toFloat();
    Serial.print("New tolerance: ");
    Serial.println(tolerance);
  } else if (command.startsWith("setVoltage ")) {
    desiredVoltage = command.substring(11).toFloat();
    Serial.print("New DAC voltage: ");
    Serial.println(desiredVoltage);
    setDACVoltage(desiredVoltage); // Update the DAC voltage immediately
  } else {
    Serial.println("Unknown command");
  }
}
