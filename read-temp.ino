// Library set-up for functions used throughout script

#include <Adafruit_MAX31865.h> // PT100 library
#include <Wire.h>  // Wire library for I2C
#include <RTClib.h>  // RTC library
#include "DFRobot_GP8XXX.h" // Updated DAC library

// Initialize MAX31865, RTC, and DAC

Adafruit_MAX31865 max = Adafruit_MAX31865(53);  // CS pin on Arduino
RTC_DS3231 rtc;  // Create an RTC object
DFRobot_GP8403 dac(DFGP8XXX_I2C_DEVICEADDR, RESOLUTION_12_BIT);

// Global variables- accessible/visible throughout program

const int heatingPin = 5; // Digital pin for heating control

float flowRate = 0.0; // The calculated flow rate
unsigned long lastFlowRateCalc = 0; // Last time the flow rate was calculated

float targetTemperature = 25.0; // Default target temperature
float tolerance = 0.2; // Temperature tolerance
const float maxTolerance = 5.0; // Maximum allowed tolerance

float desiredVoltage = 5; // Initial voltage

unsigned long lastHeartbeatTime = 0; // Stores the last time the heartbeat was sent (Operational check signal)
const unsigned long heartbeatInterval = 60000; // Heartbeat interval 60s

// Function to read and calculate temperature from the PT100 sensor
float readTemperature() {
  uint16_t rtd = max.readRTD();
  float ratio = rtd / 32768.0; // Convert to ratio
  float resistance = (ratio * 430); // Adjust this value based on reference resistor
  float R0 = 100.0;
  float A = 3.9083e-3;
  float B = -5.775e-7;
  float temperature = (-R0 * A + sqrt(R0*R0*A*A - 4*R0*B*(R0 - resistance))) / (2*R0*B);
  return temperature;
}

void setup() {
  
  Serial.begin(9600); // Begin Serial communication
  // Wait for serial port to connect. Needed for native USB
  while (!Serial) {
    ;
  }
  
  delay(3000); // Delay for 3s before continuing
  
  max.begin(MAX31865_4WIRE); // Set up PT100 sensor- 4 wire
  Serial.println("PT100 sensor initialized. Enter target temperature (0-100°C):");

  if (!rtc.begin()) {
    Serial.println("Couldn't find RTC");
    while (1); // Infinite loop if RTC not found
  } else {
    Serial.println("RTC initialized successfully.");
  }

  if (rtc.lostPower()) {
    // If the RTC lost power, let's set the time!
    rtc.adjust(DateTime(F(__DATE__), F(__TIME__)));
  }
  
   if (dac.begin() == 0) {
    Serial.println("DAC initialized successfully.");
    dac.setDACOutRange(DFRobot_GP8XXX::eOutputRange10V); // Set to 0-10V range, adjust if needed
  } else {
    Serial.println("Couldn't initialize DAC. Check wiring!");
    while (1);
  }
  pinMode(heatingPin, OUTPUT); // Set the heating control pin as output
}

void loop() {
  
  DateTime now = rtc.now();  // Get current date and time

  float temperature = readTemperature(); // Read and calculate temperature from PT100
  uint16_t rtd = max.readRTD(); // Read RTD resistance value again for resistance output
  float ratio = rtd / 32768.0; // Convert to ratio
  float resistance = (ratio * 430); // Adjust this value based on your reference resistor
  
  // DAC voltage setting logic
  uint16_t dacValue = static_cast<uint16_t>((desiredVoltage / 10.0) * 4095);
  dac.setDACOutVoltage(dacValue, 0); // Apply the updated voltage to channel 0
  dac.store(); // Optional: Store voltage setting if needed- can comment out.

  // Read and print the DAC voltage for verification
  float dacVoltage = dacValue * 10.0 / 4095; // Convert back to voltage for display
  Serial.print("DAC Voltage Set To: ");
  Serial.println(dacVoltage, 3); // Print with 3 decimal places

  // Adjust thermostat control logic based on targetTemperature and tolerance
  if (temperature < targetTemperature - tolerance) {
    Serial.println("Activating heating.");
    digitalWrite(heatingPin, HIGH); // Turn on heating
  } else if (temperature > targetTemperature + tolerance) {
    Serial.println("Activating cooling.");
    digitalWrite(heatingPin, LOW); // Ensure heating is off
  } else {
    Serial.println("Temperature within target range. Thermostat off.");
    digitalWrite(heatingPin, LOW); // Ensure heating is off
  }

  // Read the voltage from analog pin A0
  int sensorValue = analogRead(A0);
  float voltage = sensorValue * (10.0 / 1023.0); // Convert to 0-10V range
  float flowRate = voltage * (0.35 / 10.0); 

  // Print the results
  Serial.print("Voltage: ");
  Serial.print(voltage, 2);
  Serial.println(" V");

  Serial.print("Flow rate: ");
  Serial.print(flowRate, 3);
  Serial.println(" l/s");

  // Enhanced Serial communication for new target temperature and tolerance adjustment
  if (Serial.available() > 0) {
    String input = Serial.readStringUntil('\n'); // Read the incoming data as a string until newline
    input.trim(); // Remove any leading/trailing whitespace
    
    if (input.startsWith("temp ")) { // Check if command is to set temperature
      float newTemp = input.substring(5).toFloat(); // Extract and convert the temperature value
      if (newTemp >= 0 && newTemp <= 100) {
        targetTemperature = newTemp;
        Serial.print("Target temperature set to: ");
        Serial.print(targetTemperature);
        Serial.println("°C");
      } else {
        Serial.println("Invalid temperature. Please enter a value between 0-100°C.");
      }
    } else if (input.startsWith("tolerance ")) { // Check if command is to set tolerance
      float newTolerance = input.substring(10).toFloat(); // Extract and convert the tolerance value
      if (newTolerance >= 0 && newTolerance <= maxTolerance) {
        tolerance = newTolerance;
        Serial.print("Tolerance updated to: ");
        Serial.print(tolerance);
        Serial.println("°C");
      } else {
        Serial.println("Invalid tolerance. Please enter a positive value within the allowed range.");
      }
    } else if (input.startsWith("setVoltage ")) { // Check if command is to set DAC voltage
      float newVoltage = input.substring(11).toFloat(); // Extract and convert the voltage value
      if (newVoltage >= 0 && newVoltage <= 10) {
        desiredVoltage = newVoltage; // Update desiredVoltage
        Serial.print("Voltage set to: ");
        Serial.print(desiredVoltage);
        Serial.println(" V");
      } else {
        Serial.println("Invalid voltage. Please enter a value between 0-10V.");
      }
    }
    // Clear the serial buffer to prepare for the next command
    while (Serial.available() > 0) Serial.read();
  }

  // Print date, time, resistance, and temperature to serial port
  Serial.print(now.year(), DEC);
  Serial.print("-");
  Serial.print(now.month(), DEC);
  Serial.print("-");
  Serial.print(now.day(), DEC);
  Serial.print(" ");
  Serial.print(now.hour(), DEC);
  Serial.print(":");
  Serial.print(now.minute(), DEC);
  Serial.print(":");
  Serial.print(now.second(), DEC);
  Serial.print(", Resistance: ");
  Serial.print(resistance, 2); // Print resistance with 2 decimal places
  Serial.print(" ohms, Temperature: ");
  Serial.print(temperature);
  Serial.println("°C");

  delay(3000); // Data acquisition delay, 3s
}
