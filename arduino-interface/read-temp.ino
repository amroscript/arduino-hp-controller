#include <Adafruit_MAX31865.h> // PT100 library
#include <Wire.h>  // Wire library for I2C
#include <RTClib.h>  // RTC library
#include "DFRobot_GP8XXX.h" // Updated DAC library

Adafruit_MAX31865 max = Adafruit_MAX31865(53);  // CS pin on Arduino
RTC_DS3231 rtc;  // Create an RTC object
DFRobot_GP8403 dac(DFGP8XXX_I2C_DEVICEADDR, RESOLUTION_12_BIT);

const int heatingPin = 5; // Digital pin for heating control
float flowRate = 0.0; // The calculated flow rate
float targetTemperature = 25.0; // Default target temperature
float tolerance = 0.2; // Temperature tolerance
float desiredVoltage = 5; // Initial voltage

void setup() {
  Serial.begin(9600); // Begin Serial communication
  delay(3000); // Delay for 3s before continuing
  
  max.begin(MAX31865_4WIRE); // Set up PT100 sensor- 4 wire
  Serial.println("PT100 sensor initialized.");

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
  float temperature = readTemperature(); // Read and calculate temperature from PT100
  float resistance = calculateResistance(); // Calculate resistance from RTD reading
  float voltage = readAnalogVoltage(); // Read and convert voltage from analog pin
  
  // DAC voltage setting logic
  setDACVoltage(desiredVoltage);

  // Adjust thermostat control logic based on targetTemperature and tolerance
  controlHeating(temperature);

  // Send temperature, resistance, voltage, and flow rate data to the GUI via serial communication
  sendSerialData(temperature, resistance, voltage, flowRate);

  delay(1000); // Add a delay to control the update rate
}

float readTemperature() {
  uint16_t rtd = max.readRTD();
  float ratio = rtd / 32768.0;
  float resistance = (ratio * 430);
  float R0 = 100.0;
  float A = 3.9083e-3;
  float B = -5.775e-7;
  float temperature = (-R0 * A + sqrt(R0*R0*A*A - 4*R0*B*(R0 - resistance))) / (2*R0*B);
  return temperature;
}

float calculateResistance() {
  uint16_t rtd = max.readRTD();
  float ratio = rtd / 32768.0;
  return (ratio * 430);
}

float readAnalogVoltage() {
  int sensorValue = analogRead(A0);
  return sensorValue * (5.0 / 1023.0); // Assuming a reference voltage of 5V
}

void setDACVoltage(float voltage) {
  uint16_t dacValue = static_cast<uint16_t>((voltage / 10.0) * 4095);
  dac.setDACOutVoltage(dacValue, 0); // Apply the updated voltage to channel 0
}

void controlHeating(float temperature) {
  if (temperature < targetTemperature - tolerance) {
    digitalWrite(heatingPin, HIGH); // Turn on heating
  } else if (temperature > targetTemperature + tolerance) {
    digitalWrite(heatingPin, LOW); // Ensure heating is off
  } else {
    digitalWrite(heatingPin, LOW); // Ensure heating is off
  }
}

void sendSerialData(float temperature, float resistance, float voltage, float flowRate) {
  Serial.print("Temp:");
  Serial.print(temperature);
  Serial.print(",Res:");
  Serial.print(resistance);
  Serial.print(",Volt:");
  Serial.print(voltage);
  Serial.print(",Flow:");
  Serial.println(flowRate);
}
