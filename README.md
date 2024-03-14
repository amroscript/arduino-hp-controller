# arduino-hp-controller for heat pump systems
This repository consists of an Arduino-driven controller is designed to monitor and control heat-pump parameters in real-time, offering an interface for initialization, settings updates, and operations management with feedback through a terminal display.

## Installation 

In order to use this package, you can download the Python/Arduino files and use them in your own script. 

Download or clone the repository via git: 
`git clone https://github.com/amroscript/arduino-hp-controller/`

## Documentation


1. If using mock-arduino.py to mimick an arduino environment for the controller:

– Establish a bidirectional serial stream using socat. This command will create two interconnected virtual serial ports. Open a terminal and enter:
 `socat -d -d pty,raw,echo=0 pty,raw,echo=0`
  Note the output from this command, which will give you the paths to the virtual serial ports.

Update the Arduino port in your script. With the virtual serial ports created, you'll need to update the ARDUINO_PORT variable in your Python script(s) to match one of the virtual ports created by socat.

For example, if socat outputted /dev/pts/3 and /dev/pts/4, you would set ARDUINO_PORT = '/dev/pts/3' in your Python script.

