# Arduino Heat Pump Controller

This repository contains a comprehensive Arduino-driven controller designed to monitor and control heat pump systems in real-time. The interface supports initialization, settings updates, operational management, and data export, with feedback provided through a terminal display.

## Installation 

To use this package, follow these steps:

1. **Download or Clone the Repository:**

    ```bash
    git clone https://github.com/amroscript/arduino-hp-controller/
    ```

2. **Install Required Python Libraries:**
   
    Navigate to the cloned repository directory and install the required Python packages using pip:

    ```bash
    pip install -r requirements.txt
    ```

    If using VSCode, ensure you have the Arduino extension (e.g., "Arduino for Visual Studio Code" by Microsoft) installed.

3. **Install Required Arduino Libraries:**

    - **Adafruit_MAX31865**
    - **Wire** (bundled with the Arduino IDE)
    - **RTClib**
    - **DFRobot_GP8XXX**

    Steps to install:
    
    1. Open the Arduino IDE.
    2. Go to `Sketch` > `Include Library` > `Manage Libraries...`
    3. Search for each library listed above and install it.

## Software Documentation

### Mock Testing (Simulated Environment)

1. **Establish Virtual Serial Ports:**

    - **macOS (using `socat`):**

        ```bash
        socat -d -d pty,raw,echo=0 pty,raw,echo=0
        ```

        Note the paths to the virtual serial ports provided in the output.

    - **Windows (using `com0com`):**

        Follow [com0com instructions](https://com0com.sourceforge.net/).

2. **Update Arduino Port in Script:**

    Set the `ARDUINO_PORT` variable in your Python script to match one of the virtual ports created. For example, if `socat` outputted `/dev/pts/3` and `/dev/pts/4`, set:

    ```python
    ARDUINO_PORT = '/dev/pts/3'
    ```

### Direct Heat Pump Setup

1. **Connect the Arduino:**
   
    Ensure the Arduino is connected to the PC via USB and properly configured with sensors and actuators.

2. **Launch the Application:**

    Run the Python script to open the GUI.

3. **Set COM Port:**

    Adjust the `ARDUINO_PORT` variable to match the Arduino's COM port.

4. **Initialize System:**

    Click the "Initialize" button to start communication with the Arduino.

5. **Adjust Settings:**

    Set the target temperature, tolerance, and DAC voltage as required.

6. **Monitor Data:**

    Observe real-time data updates in both table and graph views.

7. **Export Data:**

    Click the "Export to CSV" button to save the data for offline analysis.

## User-Interface Preview

![Controls Monitor](https://github.com/amroscript/arduino-hp-controller/assets/163342561/13029a2c-b871-45f4-9e02-091b37506d1f)

![Data Spreadsheet](https://github.com/amroscript/arduino-hp-controller/assets/163342561/f0497dc6-36da-463b-af0d-a7eab23dbe00)

![Graph Tab](https://github.com/amroscript/arduino-hp-controller/assets/163342561/b4c5cabd-6ee5-4875-ae28-ea13b2ec5138)

## Hardware Documentation

### Components Required

- **Arduino Mega 2560:** Central processing unit for the controller, managing sensor data readings and actuator responses.
- **Adafruit MAX31865 RTD Sensor:** Essential for monitoring heat pump performance.
- **RTC DS3231 Real-Time Clock Module:** Provides accurate timekeeping for data logging and scheduling tasks.
- **DFRobot GP8403 DAC Module:** Controls analog variables such as outputting voltage levels.
- **Digital Relay Module (Optional):** Controls higher power components like heaters or pumps.
- **Wiring and Connectors:** Ensure proper connection between the Arduino, sensors, actuators, and peripherals.
- **Power Supply:** Adequate power source for the Arduino and all connected hardware components.

**Initialization checks in `_read-temp.ino` script verify wiring and integration before testing.**

### Wiring Overview

- **MAX31865 RTD Sensor:**
  
  - VCC to Mega 5V.
  - GND to Mega GND.
  - SDI (MOSI) to Mega pin 51.
  - SDO (MISO) to Mega pin 50.
  - CLK to Mega pin 52.
  - CS to a selectable digital pin, e.g., pin 10.
  - RTD wires connected to the RTD screw terminals.

- **DFRobot GP8403 DAC:**

  - VCC to Mega 5V.
  - GND to Mega GND.
  - SCL to Mega pin 21 (SCL).
  - SDA to Mega pin 20 (SDA).
  - DAC's analog output to your actuator's control input.

- **RTC DS3231:**

  - VCC to Mega 5V.
  - GND to Mega GND.
  - SCL to Mega pin 21 (SCL).
  - SDA to Mega pin 20 (SDA).

- **Heating Control (Relay Module):**

  - VCC (Relay module) to Mega 5V.
  - GND (Relay module) to Mega GND.
  - IN (Relay module) to a digital pin on Mega, e.g., pin 5.
  - Heating element's power circuit connected through the relay.

_The Mega 2560 offers multiple ground and voltage pins for easy expansion with additional sensors or actuators. It has a dedicated SPI header convenient for devices like the MAX31865 and specific I2C pins for the DS3231 RTC and DAC module._
