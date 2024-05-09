# arduino-hp-controller for heat pump systems
This repository consists of an Arduino-driven controller is designed to monitor and control heat-pump parameters in real-time, offering an interface for initialization, settings updates, and operations management with feedback through a terminal display and with a functionality to export data.

## Installation 

In order to use this package, you should download the Python/Arduino files. 

1. Download or clone the repository via git: 

    `git clone https://github.com/amroscript/arduino-hp-controller/`

2. Install required Python libraries. Navigate to the cloned repository directory and install the required Python packages using pip:

    `pip install -r requirements.txt`

    If you are using VSCode, ensure you have the Arduino extension (e.g., "Arduino for Visual Studio Code" by Microsoft) installed.

3. This project also requires the following Arduino libraries: 

    - Wire (bundled with the Arduino IDE)
    - RTClib
    - DFRobot_GP8XXX
 
    i. Open the Arduino IDE.
    ii. Go to `Sketch` > `Include Library` > `Manage Libraries...`
    iii. In the Library Manager, search for each library listed above and install it.

## Software Documentation

1. If using _mock-testing_ to mimick an arduino environment for the controller:

    – Establish a bidirectional serial stream using socat (macOS) or com0com (Windows).

    The socat command will create two interconnected virtual serial ports, whilst com0com is a port emulator. If using MacOS a terminal and enter: 

    `socat -d -d pty,raw,echo=0 pty,raw,echo=0` 

    Note the output from this command, which will give you the paths to the virtual serial ports.

    Alternatively follow this link for com0com instructions: https://com0com.sourceforge.net/.

    – Update the Arduino port in your script. With the virtual serial ports created, you'll need to update the ARDUINO_PORT variable in your Python script(s) to match one of the virtual ports created by your emulators.

    For example, if socat outputted /dev/pts/3 and /dev/pts/4, you would set ARDUINO_PORT = '/dev/pts/3' in your Python script.

2. If heat pump set-up is available, use _arduino-interface_ directly:

    – **Connect the Arduino:** Ensure the Arduino is connected to the PC via USB and configured with the correct sensors and actuators.

    – **Launch the Application:** Run the Python script to open the GUI.

    – **Set COM Port:** Adjust the `ARDUINO_PORT` variable if necessary to match the Arduino's COM port.

    – **Initialize System:** Click the "Initialize" button to start communication with the Arduino.

    – **Adjust Settings:** Set the target temperature, tolerance, and DAC voltage as required.

    – **Monitor Data:** Observe real-time data updates in both table and graph views.

    – **Export Data:** Click the "Export to CSV" button to save the data for offline analysis.

## User-interface Preview

![image](https://github.com/amroscript/arduino-hp-controller/assets/163342561/29833f88-8ce5-4f73-8e11-02725690f3c1)

![image](https://github.com/amroscript/arduino-hp-controller/assets/163342561/e670c02f-aac0-450f-af79-779538deb5a3)

## Hardware Documentation

**Components Required**

– Arduino Board (Mega 2560): Central processing unit for the controller, managing sensor data readings and actuator responses.

– Adafruit MAX31865 RTD Sensor: Sensor for reading temperatures, essential for monitoring the heat pump performance.

– RTC DS3231 Real-Time Clock Module: Provides accurate timekeeping for data logging and scheduling tasks.

– DFRobot GP8403 DAC Module: Used for controlling analog variables within the system, such as outputting voltage levels.

– Digital Relay Module (optional): For controlling higher power components such as heaters or pumps, based on the Arduino's output signals.

– Wiring and Connectors: Ensure proper connection between the Arduino, sensors, actuators, and other peripherals.

– Power Supply: Adequate power source for the Arduino and all connected hardware components.

_Note the initilization checks within the _read-temp.ino_ script to verify wiring and integration before testing._


**Wiring Overview**  

MAX31865 RTD Sensor:

    VCC to Mega 5V.

    GND to Mega GND.

    SDI (MOSI) to Mega pin 51.

    SDO (MISO) to Mega pin 50.

    CLK to Mega pin 52.

    CS to a selectable digital pin, e.g., pin 10.
    
    RTD wires connected to the RTD screw terminals.

 DFRobot_GP8XXX DAC:

    VCC to Mega 5V.
  
    GND to Mega GND.
  
    SCL to Mega pin 21 (also labeled as SCL).
  
    SDA to Mega pin 20 (also labeled as SDA).
  
    The DAC's analog output to your actuator's control input.

RTC DS3231:

    VCC to Mega 5V.
  
    GND to Mega GND.
  
    SCL to Mega pin 21 (also labeled SCL).
  
    SDA to Mega pin 20 (also labeled SDA).

Heating Control (Relay Module):

    VCC (Relay module) to Mega 5V.
  
    GND (Relay module) to Mega GND.
  
    IN (Relay module) to a digital pin on Mega, e.g., pin 5.
  
    Heating element's power circuit connected through the relay.



_The Mega 2560 provides multiple ground and voltage pins, so you can easily expand your project with more sensors or actuators._

_The Mega 2560 has a dedicated SPI header close to the digital pins 50 (MISO), 51 (MOSI), and 52 (CLK), which is convenient for SPI devices like the MAX31865._

_The I2C pins (20 for SDA and 21 for SCL) on the Mega are in a different location than on the Uno, so always refer to the Mega's pinout when connecting I2C devices like the DS3231 RTC and the DAC module._




