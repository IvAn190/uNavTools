import subprocess
import os
import sys

import serial
from pyubx2 import UBXReader, UBXMessage, POLL
import pyubx2
import time


import matplotlib.pyplot as plt
import matplotlib.dates as md
import numpy as np
import pandas as pd

import simplekml # Create .kml files 
import pymap3d as pm



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


# Borrar 
def guardar_array_en_txt(array, nombre_archivo):
    """
    Guarda un array de numpy en un archivo de texto.

    Parámetros:
    - array: El array de numpy que se desea guardar.
    - nombre_archivo: Nombre del archivo de texto donde se guardará el array.
    """
    np.savetxt(nombre_archivo + ".txt", array, fmt='%f')

def createKML(llh_coordinates, name: str):
    """
    Creates .kml file from a LLH vector.  

    :llh_coordinates: must be an ecef vector  
    """

    if name == None or name.strip() == '':
        raise ValueError("No name to creat the .kml file!")


    # Check if any latitude or longitude coordinate is out of valid ranges
    invalid_latitudes = np.any((llh_coordinates[:, 0] < -90) | (llh_coordinates[:, 0] > 90))
    invalid_longitudes = np.any((llh_coordinates[:, 1] < -180) | (llh_coordinates[:, 1] > 180))

    if invalid_latitudes or invalid_longitudes:
        # If any coordinate is out of range, convert it from ECEF to LLA
        for i in range(len(llh_coordinates)):
            # Assuming ecef2lla is a defined function that converts from ECEF to LLA
            llh_coordinates[i, :] = ecef2lla(llh_coordinates[i, :])
    
    # KML obj
    kml = simplekml.Kml()

    style = simplekml.Style()
    
    style.iconstyle.color = 'ff0000ff'  # Red
    style.iconstyle.scale = 0.2  # Icon scale
    
    style.iconstyle.icon.href = 'http://maps.google.com/mapfiles/kml/pal2/icon18.png'

    for lat, lon, alt in llh_coordinates:
        point = kml.newpoint(coords=[(lon, lat, alt)])
        point.style = style  # Apply style at each point

    # Save kml into the folder
    kml.save('data/rinex/' + name + '/' + name +  '.kml')

def ecef2lla(vector):   
    """
    Convert ECEF coordinates to LLA (Latitude, Longitude, Altitude)
    :param x: X coordinate in ECEF
    :param y: Y coordinate in ECEF
    :param z: Z coordinate in ECEF
    :return: Tuple (latitude, longitude, altitude)
    """

    # Converts ECEF to LLA
    lat, lon, alt = pm.ecef2geodetic(vector[0], vector[1], vector[2])
    return lat, lon, alt

def checkSystemFrequency(sigs):
    """
    Checks frequency for each GNSS system to determine if they are using single or dual/multiple frequencies.

    :sigs: [str] contains all selected signals to be processed.
    """
    # Diccionario para almacenar las frecuencias especificas utilizadas por cada sistema GNSS
    system_frequencies = {}

    # Mapear las letras iniciales a los sistemas GNSS.
    systems = {"G": "GPS", "E": "Galileo", "R": "GLONASS", "B": "BeiDou", "Q": "QZSS", "I": "IRNSS"}

    for sig in sigs:
        system_key = sig[0]  # Primera letra del identificador
        system = systems.get(system_key, "Unknown")
        frequency_number = sig[2]  # Asume que el tercer carácter indica el numero de la frecuencia
        
        if system not in system_frequencies:
            system_frequencies[system] = set()
        
        system_frequencies[system].add(frequency_number)
    
    # Determinar si cada sistema utiliza single o dual frequency basado en el numero de frecuencias unicas identificadas.
    system_usage = {system: "dual-frequency" if len(frequencies) > 1 else "single-frequency"
                    for system, frequencies in system_frequencies.items()}

    return system_usage

def saveTest(archivo, nav, system_freq, sol_, enu, ztd, smode, nep, file_path):
    # TODO: Rehacer esta funcion porque creo que a nivel practico, por ejemplo el enu 
    #       se puede evitar guardarlo metiendo el sol_ y xyz_ref --> enu = sol_ - xyz_ref
    """
    Save config in .txt and data in .csv.

    :archivo = "Single" + str(int(nep/60)) + "m": [str]
    :system_freq:   [int]
    :sol_:          [array]
    :enu:           [array]
    :ztd:           [array]
    :smode:         [array]
    :nep = nep/60:  [int]
    :file_path =    [navfile, obsfile, orbfile, clkfile, bsxfile, csfile, atxfile]: [str]

    """

    with open("data/test/".replace("/", "\\") + archivo + ".txt", 'w') as file:
        file.write("SETUP: \n\n")
        for path in file_path:
            file.write("File: {}\n".format(path))
        file.write("Minimum elevation: {}\n".format(nav.elmin * 180/np.pi))
        file.write("Ambiguity: {}\n".format(nav.thresar))
        file.write("ARmode: {} (0:float-ppp,1:continuous,2:instantaneous,3:fix-and-hold)\n".format(nav.armode))
        file.write("Ephemeris: {} (0: BRDC, 1: SBAS, 2: SSR-APC, 3: SSR-CG, 4: PREC)\n".format(nav.ephopt))
        file.write("Position mode: {} (0:static, 1:kinematic)\n".format(nav.pmode))
        file.write("Frequency: {}\n".format(system_freq))
        file.write("Duration: {} min\n".format(nep))
        file.write("\n")


    # Crear el DataFrame
    df = pd.DataFrame({
        "sol_x": sol_[:, 0],
        "sol_y": sol_[:, 1],
        "sol_z": sol_[:, 2],
        "enu_x": enu[:, 0],
        "enu_y": enu[:, 1],
        "enu_z": enu[:, 2],
        "ztd": ztd[:,0], 
        "mode": smode
    })

    # Guardar el DataFrame en un archivo CSV
    df_csv_path = "data/test/" + archivo + ".csv"
    df.to_csv(df_csv_path, index=False)

def getUBXModel(PORT, BAUD_RATE, ser):
    """
    Get u-blox model. 
    """
    #TODO: el mensaje no es el de MON-VER
    msg = UBXMessage('MON', 'MON-VER', POLL)

    ser.write(msg.serialize())

    ubr = UBXReader(ser)

    ublox_models ={
        'M8': ['T', 'N', 'U', 'C', 'F', 'L'],  
        'F9': ['P', 'T'], 
        'M10':['1', '1C']
    }

    (raw_data, _) = ubr.read()

    for model, variants in ublox_models.items():
        for variant in variants:
            model_variant = model + variant
            if model_variant in str(raw_data):
                print(f"Model: {model_variant} detected!")
                return model_variant
    return None


def checkUBX(PORT: str, BAUD_RATE: int, UBX: bool):
    """
    Checks GNSS hardware.

    :param PORT:      [str] Port
    :param BAUD_RATE: [int] Baud rate
    :param UBX:       [bool] 

    :return: (str or None, bool) Tuple containing the model detected and a boolean indicating if u-blox hardware is detected.
    if isinstance(parsed_data, pyubx2.UBXMessage)
    """
    try:
        hw = False 
        model = None
        
        with serial.Serial(PORT, BAUD_RATE, timeout=3) as ser:
            ubr = UBXReader(ser)

            for _ in range(10):  
                (raw_data, parsed_data) = ubr.read()
                if 'u-blox' in str(raw_data) or 'UBX' in str(parsed_data):  # Assuming 'u-blox' can be searched in the string-converted raw_data
                    print("U-BLOX detected!")
                    hw = True
                    break
            if not hw:
                return (model, hw) # U-blox not detected
                
            for _ in range(10):
                model = getUBXModel(PORT, BAUD_RATE, ser)
                if model:
                    return (model, hw)  # Return model and True if a u-blox model is detected

        return (model, hw)  
    
    except serial.SerialException as e:
        print(f"Error opening serial port: {e}")
        return (None, False)
    
    except Exception as e:
        print(f"Error: {e}")
        return (None, False)
    


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

def freqModel(model):
    if not model:
        return 2
    if 'M8' in model:
        return 1
    elif model == '':
        n = int(input("Select single or dual frequency. opt = 1, 2: "))
        if n > 2 or n <= 0:
            raise ValueError("Frequency must be 1 or 2!")
        return n
    else:
        return 2


class Measurement:
    #NOTE: Para la funcion getDatafromLOG(...)
    """
    
    """
    def __init__(self, sol, enu, ztd, mode):
        self.sol = sol
        self.enu = enu
        self.ztd = ztd
        self.mode = mode

def getDatafromLOG(filePath="data/log/ppp-igs.log"):
    # TODO: ver como seguir esta funcion
    """
    
    """
    measurements = []
    sol, enu, ztd, mode, fecha_hora = None, None, None, None, None

    with open(filePath, 'r') as file:
        for line in file:
            if 'Sol:' in line:
                fecha_hora = line.split('Sol:')[0].strip()
                sol = [float(x) for x in line.split('Sol:')[1].strip("[]\n ").split(',')]
            elif 'ENU:' in line:
                enu = [float(x) for x in line.split('ENU:')[1].strip("[]\n ").split(',')]
            elif 'ZTD:' in line:
                ztd = [float(x) for x in line.split('ZTD:')[1].strip("[]\n ").split(',')]
            elif 'mode' in line:
                mode = int(line.split('mode')[1].strip("[]\n "))
                # Asumiendo que tenemos un conjunto completo de datos para una medición
                if all(v is not None for v in [fecha_hora, sol, enu, ztd, mode]):
                    measurements.append(Measurement(fecha_hora, sol, enu, ztd[0], mode))
                    sol, enu, ztd, mode, fecha_hora = None, None, None, None, None  # Reset para la siguiente medición

    return measurements

def getDataFromCSV(csv_path):
    """
    Get data from .csv file.
    """
    # Leer el archivo CSV
    df = pd.read_csv(csv_path)
    
    # Extraer las columnas para sol_ y enu
    sol_ = df[['sol_x', 'sol_y', 'sol_z']].to_numpy()
    enu = df[['enu_x', 'enu_y', 'enu_z']].to_numpy()
    
    # Extraer ztd y smode
    ztd = df['ztd'].to_numpy()
    smode = df['mode'].to_numpy()
    
    return sol_, enu, ztd, smode


