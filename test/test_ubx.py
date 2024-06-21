from pyubx2 import UBXReader
import pyubx2


fpath = './data/ublox/COM10___115200_2024315_104731.ubx'

with open(fpath, 'rb') as file:
    ubr = UBXReader(file)

    

    for line in ubr:
        (raw_data, parsed_data) = ubr.read()
        print(parsed_data)
        input()