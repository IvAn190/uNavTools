import os, sys, subprocess
import time
from pyubx2 import UBXReader, UBXMessage, POLL
import serial

from src.funciones import *


def runconvbin(name: str, model=None, bforce=True):
    """
    Converts a UBX file to RINEX format using the convbin tool

    :param name: Name of the file to be converted
    :param model: Optional model name to include in the header comment section of the RINEX file
    :param bforce: If True, forces the creation of the output file even if it already exists
    :return: None
    """
    # Gets the absolute path to the current script's directory
    current_dir = os.path.dirname(os.path.abspath(__file__))

    if name is None or name.strip() == "":
        raise ValueError("Name file empty!")

    if model is None:
        model = 'unknown'

    model = "model:{}".format(model)
    
    # Builds the complete paths to the .ubx file and the convbin.exe executable
    ubx_path = 'data\\ublox\\' + name + '.ubx'
    folder = 'data\\rinex\\' + name
    
    if not os.path.exists(folder):
        os.mkdir(folder)
    
    out_path = os.path.join(folder, name + ".obs")
    
    if bforce or not os.path.exists(out_path):
        # Assumes that convbin.exe is located in the same directory as the script
        convbin_path = "convbin.exe"
        rlist = [convbin_path, ubx_path]
        
        if sys.platform == "linux":  # NOTE: not tested, might be incorrect
            rlist = ["wine"] + rlist  # Prepares the command to run with Wine on Linux

        print("\nconvbin on {}\n".format(rlist))
        # Executes the command with the arguments

        obsfile = os.path.join(folder, name + ".obs")
        navfile = os.path.join(folder, name + ".nav")
        gnavfile = os.path.join(folder, name + ".gnav")
        lnavfile = os.path.join(folder, name + ".lnav")
        sbasfile = os.path.join(folder, name + ".sbas")
        model = str(model)
        #sigmask = 'EL1X,EL7X'
        sigmask = ''#'GC1C,GL1C,GD1C,GS1C,GC2X,GL2X,GD2X,GS2X,EC1X,EL1X,ED1X,ES1X,EC7X,EL7X,ED7X,ES7X'

        runconvbinCMD = '%s -r ubx  %s -f 3 -v 3.04 -od -os -oi -ot -ol -scan -hc %s -o %s -n %s -g %s -l %s -s %s %s -trace 3' % \
            (convbin_path, sigmask, model, obsfile, navfile, gnavfile, lnavfile, sbasfile, ubx_path)

        subprocess.run(runconvbinCMD,check=True)

        if not os.path.exists(out_path):
            print(f"\nWARNING: {out_path} not created (ubx file probably empty)\n")
        else:
            print(f"\n{out_path} exists")


def rawData2ubx(duration: int, PORT='COM3', BAUD_RATE = 115200, UBX=True):

    """
    Get raw data from u-blox reciever and converts to .ubx binary format. 

    :duration:  [int] Duration in minutes
    :PORT:      [str] Port
    :BAUD_RATE: [int] Baud rate

    :return --> name [str]
    """
    # NOTE: to handle errors, run test/test_port.py
    if not UBX:
        print("\nMode selected: don't check u-blox (UBX=false)\n")
        model, hw = None, True
    else:
        model, hw = checkUBX(PORT, BAUD_RATE, UBX) # [str or None], [bool]
        if not hw:
            raise ValueError("GNSS hardware not supported (only u-blox) or not detected, try to run test/test_port.py in order to find the correct COM port.")
    
    check_and_create_folders()

    print("Collecting data...\n")

    # Configura el puerto serie.
    ser = serial.Serial(PORT, BAUD_RATE, timeout=3)

    h = time.localtime()

    start_time = time.time()
    final_time = time.time() + duration * 60

    path = 'data\\ublox\\'
    name = PORT + '___' + str(BAUD_RATE) + '_' + str(h.tm_year) + str(h.tm_mon) +str(h.tm_mday) + '_' + str(h.tm_hour) + str(h.tm_min) + str(h.tm_sec)

    fpath = path + name + '.ubx'
    
    # Save UBX file
    with open(fpath, 'wb') as file:
        ubr = UBXReader(ser)

        try:
            while time.time() < final_time:
                (raw_data, parsed_data) = ubr.read()
                if raw_data:
                    file.write(raw_data)
                    file.flush()    
                
                elapsed_time = time.time() - start_time
                percentage = (elapsed_time / (duration * 60)) * 100
                print(f"\rProgress: {percentage:.2f}%", end="")
        except KeyboardInterrupt:
            print("Stopped by user. Incomplete UBX file!!!!!")
        finally:
            ser.close()  
    
    print("\t Data collected!\n\n")
    
    return name, model