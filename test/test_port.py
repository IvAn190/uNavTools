"""
Test to check serial port availability and find which is connected with the u-blox receiver.

"""

import serial
from pyubx2 import UBXReader
import pyubx2
import serial.tools.list_ports

def check_ublox_in_port(num_port):
    for port_number in num_port:
        PORT = port_number
        try:
            with serial.Serial(PORT, 115200, timeout=3) as ser:
                print(f"Testing {PORT}...")
                ubr = UBXReader(ser)
                no_data_count = 0
                for _ in range(10):  # Try to read up to 10 times
                    (raw_data, parsed_data) = ubr.read()
                    print(parsed_data)
                    #print(raw_data)
                    if raw_data:
                        if 'u-blox' in str(raw_data) or 'UBX' in str(parsed_data):  # Assuming 'u-blox' can be searched in the string-converted raw_data
                            print(f"'u-blox' found in {PORT}")
                            return PORT  # Returns the port where it was found
                        no_data_count = 0  # Reset counter if any data is received
                    else:
                        no_data_count += 1
                        if no_data_count >= 10:
                            print(f"No useful information in {PORT}, switching to the next port...")
                            break  # Exits the for loop and tries the next port
        except serial.SerialException as e:
            print(f"Error opening serial port {PORT}: {e}")

    print("No 'u-blox' found in the tested ports.")
    return None

def list_serial_ports():
    ports = serial.tools.list_ports.comports()
    available_ports = [port.device for port in ports]
    print("Available serial ports:")
    for port in available_ports:
        print(port)
    print("\n")
    return available_ports

available_ports = list_serial_ports()

num_port = []
for port in available_ports:
    num_port.append(str(port))

check_ublox_in_port(num_port)