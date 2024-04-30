// Author: Amro Farag
// Date: March 2024

#include <Adafruit_MAX31865.h> // PT100 library
#include <Wire.h>  // Wire library for I2C communication
#include <RTClib.h>  // Real Time Clock library
#include "DFRobot_GP8XXX.h" // Digital-to-Analog Converter (DAC) library

// Initialize the MAX31865 RTD sensor, RTC, and DAC with their respective settings
Adafruit_MAX31865 max = Adafruit_MAX31865(53); // CS pin for MAX31865
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
  Serial.begin(9600); // Begin Serial communication at 9600 baud rate
  while (!Serial) { ; } // Wait for the serial port to connect. 

  max.begin(MAX31865_4WIRE); // Initialize the MAX31865 RTD sensor in 4-wire configuration
  Serial.println("PT100 sensor initialized.");

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

  float temperature = readTemperature(); // Read the current temperature from the RTD sensor
  float resistance = calculateResistance(); // Calculate resistance based on RTD reading 
  float sensorVoltage = readAnalogVoltage(A0); // Read the analog voltage from a sensor 

  flowRate = calculateFlowRate(sensorVoltage); // Calculate flow rate based on sensor voltage
  
  setDACVoltage(desiredVoltage); // Update the DAC output voltage
  controlHeating(temperature, targetTemperature, tolerance); // Control heating element based on temperature

  sendSerialData(temperature, resistance, desiredVoltage, sensorVoltage, flowRate); // Send data over serial

  delay(1000); // Delay for a second before repeating the loop
}

// Function to read temperature from the RTD sensor
float readTemperature() {
  uint16_t rtd = max.readRTD();
  float ratio = rtd / 32768.0;
  float resistance = ratio * 430; // Assuming a 430 Ohm reference resistor
  float temperature = max.temperature(100, 430); // Calculate temperature (100 Ohm at 0°C, 430 Ohm reference resistor)
  return temperature;
}

// Function to calculate resistance (Optional if you need direct resistance values)
float calculateResistance() {
  uint16_t rtd = max.readRTD();
  float ratio = rtd / 32768.0;
  return ratio * 430; // Assuming a 430 Ohm reference resistor
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
  correctedVoltage = constrain(correctedVoltage, 0.0, 10.0); // Assuming the DAC's range is 0-10V

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
void sendSerialData(float temperature, float resistance, float dacVoltage, float sensorVoltage, float flowRate) {
  // Ensure the correct variables are being sent
  Serial.print("Temp:");
  Serial.print(temperature);
  Serial.print(", Res:");
  Serial.print(resistance);
  Serial.print(", DACVolt:");
  Serial.print(dacVoltage); // Ensure this is the DAC voltage
  Serial.print(", SensorVolt:");
  Serial.print(sensorVoltage);
  Serial.print(", FlowRate:");
  Serial.println(flowRate, 3); // Ensure this is the flow rate
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
  } else if (command == "activateVirtualHeater") {
    // Logic to activate the virtual heater
    Serial.println("Virtual Heater Activated");
  } else if (command == "activateSSRHeater") {
    // Logic to switch back to SSR heating mode
    Serial.println("SSR Heater Activated");
  } else {
    Serial.println("Unknown command");
  }
}
