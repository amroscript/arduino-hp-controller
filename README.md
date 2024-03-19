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

    - Adafruit_MAX31865
    - Wire (bundled with the Arduino IDE)
    - RTClib
    - DFRobot_GP8XXX

    1. Open the Arduino IDE.
    2. Go to `Sketch` > `Include Library` > `Manage Libraries...`
    3. In the Library Manager, search for each library listed above and install it.

## Documentation

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






