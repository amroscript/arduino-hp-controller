import time
import serial
import random

port = '/dev/ttys035'  # Replace with the correct port for your virtual serial port
baud_rate = 9600

def mock_arduino():
    with serial.Serial(port, baud_rate, timeout=1) as ser:
        print(f"Mock Arduino on {ser.name} started")
        while True:
            # Simulate sensor data
            temperature = round(random.uniform(20, 30), 2)
            resistance = round(random.uniform(100, 200), 2)
            voltage = round(random.uniform(0, 5), 2)
            flow_rate = round(random.uniform(0, 1), 2)
            
            # Send a formatted string back to the GUI
            response = f"Temp:{temperature},Res:{resistance},Volt:{voltage},Flow:{flow_rate}\n"
            ser.write(response.encode('utf-8'))
            print(f"Sent mock data: {response.strip()}")
            
            time.sleep(1)  # Adjust this sleep time if needed

if __name__ == "__main__":
    mock_arduino()
