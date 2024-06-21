import serial
from pyubx2 import UBXReader, UBXMessage, POLL

# En Windows, reemplaza '/dev/ttyACM0' con el puerto correcto 'COM3'
PORT='COM4'  # Ajustado para Windows
BAUD_RATE = 115200

# Abre la conexión serial con el dispositivo
ser = serial.Serial(PORT, BAUD_RATE, timeout=3)

# Crea un mensaje UBX para solicitar la versión del firmware (MON-VER)
msg = UBXMessage('MON', 'MON-VER', POLL)

# Envía el mensaje al dispositivo
ser.write(msg.serialize())

# Crea una instancia de UBXReader para leer y analizar la respuesta
ubr = UBXReader(ser)

# Lee y analiza la respuesta del dispositivo
# Este bucle asume una única respuesta, pero puedes adaptarlo según sea necesario
while True:
    (raw_data, parsed_data) = ubr.read()
    if parsed_data:
        #print(parsed_data)
        print(raw_data)
        break  # Sale del bucle después de recibir y mostrar la respuesta

# Cierra la conexión serial
ser.close()
