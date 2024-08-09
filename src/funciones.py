import os

import serial
from pyubx2 import UBXReader, UBXMessage, POLL
import time


import matplotlib.pyplot as plt
import matplotlib.dates as md
import numpy as np
import pandas as pd

import simplekml # Create .kml files 
import pymap3d as pm

import folium
from IPython.display import display

import folium
import webbrowser
import tempfile


# Borrar 
def guardar_array_en_txt(array, nombre_archivo):
    """
    Guarda un array de numpy en un archivo de texto.

    Parámetros:
    - array: El array de numpy que se desea guardar.
    - nombre_archivo: Nombre del archivo de texto donde se guardará el array.
    """
    np.savetxt(nombre_archivo + ".txt", array, fmt='%f')

def createKML(llh_coordinates, name):
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
    kml.save('data/kml/' + name +  '.kml')

def delete_nan(sol_):
    sol = sol_[~np.isnan(sol_).any(axis=1)]
    sol = sol[~((sol[:, 0] == 0) & (sol[:, 1] == 0))]    
    return sol

def show_kml(sol_):
    delete_nan(sol_)

    # Check if any latitude or longitude coordinate is out of valid ranges
    invalid_latitudes = np.any((sol_[:, 0] < -90) | (sol_[:, 0] > 90))
    invalid_longitudes = np.any((sol_[:, 1] < -180) | (sol_[:, 1] > 180))

    if invalid_latitudes or invalid_longitudes:
        # If any coordinate is out of range, convert it from ECEF to LLA
        for i in range(len(sol_)):
            # Assuming ecef2lla is a defined function that converts from ECEF to LLA
            sol_[i, :] = ecef2lla(sol_[i, :])

    trail_coordinates = [(coord[0], coord[1]) for coord in sol_]

    m = folium.Map(location=[sol_[0][0], sol_[0][1]], zoom_start=11)
    folium.PolyLine(trail_coordinates, tooltip="Coast").add_to(m)

    with tempfile.NamedTemporaryFile('w', delete=False, suffix='.html') as temp_html:
        m.save(temp_html.name)
        temp_html.close()

        webbrowser.open(f'file://{os.path.abspath(temp_html.name)}')
    

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


def check_and_create_folders():
    """
    Checks capital folders for the toolbox. 
    """
    base_path='data/'
    folders = ['fig', 'kml', 'log', 'rinex', 'ublox']
    
    for folder in folders:
        folder_path = os.path.join(base_path, folder)
        
        if not os.path.exists(folder_path):
            os.makedirs(folder_path)
            print(f"Folder '{folder}' created '{base_path}'.")
        else:
            continue