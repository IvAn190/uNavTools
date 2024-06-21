import subprocess
import os
import sys

import serial
from pyubx2 import UBXReader
import time

import pyubx2

import matplotlib.pyplot as plt
import matplotlib.dates as md
import numpy as np
import pandas as pd

import simplekml # Create .kml files 
import pymap3d as pm


try:
    hw = False
    with serial.Serial('COM4', 115200, timeout=3) as ser:
        ubr = UBXReader(ser)
        for _ in range(10):
            (raw_data, parsed_data) = ubr.read()
            print(raw_data)
            
            if raw_data:
                # Comprueba el tipo de parsed_data antes de proceder
                if isinstance(parsed_data, pyubx2.UBXMessage) :#and 'UBX' in parsed_data.identity:
                    print("U-BLOX detected!")
                    hw = True
                #elif isinstance(parsed_data, pyubx2.NMEAMessage) and 'u-blox' in str(parsed_data):
                    #print("U-BLOX detected!")
                    #hw = True
                # Agrega más condiciones si es necesario para otros tipos de mensajes

except serial.SerialException as e:
    print(f"Error opening serial port: {e}")
except Exception as e:
    print(f"Error: {e}")
