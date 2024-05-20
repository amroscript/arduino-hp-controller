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

const int avgPeriod = 4000; // Averaging period in milliseconds
const int avgSamples = avgPeriod / 1000; // Number of samples for averaging (1 sample per second)
float tempSamples[avgSamples]; // Array to hold temperature samples
float returnTempSamples[avgSamples]; // Array to hold return temperature samples
float flowRateSamples[avgSamples]; // Array to hold flow rate samples
int sampleIndex = 0; // Current index in the sample array
unsigned long lastSampleTime = 0; // Last time a sample was taken

void setup() {
  Serial.begin(115200); // Begin Serial communication at 115200 baud rate
  while (!Serial) { ; } // Wait for the serial port to connect

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

  // Initialize the temperature and flow rate sample arrays with the initial sensor readings
  float initialTemp = readTemperature(A2);
  float initialReturnTemp = readReturnTemperature(A1);
  float initialFlowRate = readFlowRate(A0); // Assuming A0 is used for flow rate sensor

  for (int i = 0; i < avgSamples; i++) {
    tempSamples[i] = initialTemp;
    returnTempSamples[i] = initialReturnTemp;
    flowRateSamples[i] = initialFlowRate;
  }
}

void loop() {
  if (Serial.available() > 0) { // Check if data is available to read from the serial port
    String command = Serial.readStringUntil('\n'); // Read the incoming string until newline
    processSerialCommand(command); // Process the received serial command
  }

  if (millis() - lastSampleTime >= 1000) { // Take a sample every second
    lastSampleTime = millis();
    tempSamples[sampleIndex] = readTemperature(A2);
    returnTempSamples[sampleIndex] = readReturnTemperature(A1);
    flowRateSamples[sampleIndex] = readFlowRate(A0);
    sampleIndex = (sampleIndex + 1) % avgSamples;
  }

  float temperature = calculateRunningAverage(tempSamples, avgSamples);
  float returnTemperature = calculateRunningAverage(returnTempSamples, avgSamples);
  float averagedFlowRate = calculateRunningAverage(flowRateSamples, avgSamples);

  flowRate = averagedFlowRate;

  setDACVoltage(desiredVoltage); // Update the DAC output voltage
  controlHeating(temperature, targetTemperature, tolerance); // Control heating element based on temperature

  sendSerialData(temperature, desiredVoltage, averagedFlowRate, flowRate, returnTemperature); // Send data over serial

  delay(1000); // Delay for a second before repeating the loop
}

// Function to read supply temperature
float readTemperature(int pin) {
  int supSensorValue = analogRead(pin);
  float voltage = supSensorValue * (5.0 / 1023.0); // Convert the sensor reading to a voltage (0V to 5V)
  float temperature = (1.01552 * ((voltage * 70.0) / 5.0)) + 0.20325; // Corrected conversion formula
  return temperature;
}

// Function to read return temperature
float readReturnTemperature(int pin) { 
  int retsensorValue = analogRead(pin);
  float voltage = retsensorValue * (5.0 / 1023.0); // Convert the sensor reading to a voltage (0V to 5V)
  float returnTemperature = (1.01652 * ((voltage * 70.0) / 5.0)) + 0.32448; // Corrected conversion formula
  return returnTemperature;
}

// Function to read flow rate
float readFlowRate(int pin) {
  int sensorValue = analogRead(pin);
  float voltage = sensorValue * (5.0 / 1023.0); // Convert the sensor reading to a voltage (0V to 5V)
  float flowRate = voltage * (1.0 / 5.0); // Example calculation, adjust according to your sensor
  return flowRate;
}

// Function to calculate running average
float calculateRunningAverage(float* samples, int sampleCount) {
  float sum = 0.0;
  for (int i = 0; i < sampleCount; i++) {
    sum += samples[i];
  }
  return sum / sampleCount;
}

// Function to read analog voltage
float readAnalogVoltage(int pin) {
  int sensorValue = analogRead(pin);
  float voltage = sensorValue * (5.0 / 1023.0); // Convert to voltage (assuming 5V reference)
  return voltage;
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
void sendSerialData(float temperature, float dacVoltage, float averagedFlowRate, float flowRate, float returnTemperature) {
  Serial.print("STemp:");
  Serial.print(temperature);
  Serial.print(", DACVolt:");
  Serial.print(dacVoltage);
  Serial.print(", AveragedFlowRate:");
  Serial.print(averagedFlowRate, 3);
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
