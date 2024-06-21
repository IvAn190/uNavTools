import sys
from sys import stdout
import os

import pandas as pd


from copy import deepcopy
import matplotlib.pyplot as plt
import matplotlib.dates as md
import numpy as np


import cssrlib.gnss as gn
from cssrlib.gnss import ecef2pos, Nav, Obs
from cssrlib.gnss import time2doy, time2str, timediff, epoch2time
from cssrlib.gnss import rSigRnx
from cssrlib.gnss import sys2str
from cssrlib.peph import atxdec, searchpcv
from cssrlib.peph import peph, biasdec


from cssrlib.rinex import rnxdec
from cssrlib.pppssr import pppos

from cssrlib.plot import plot_nsat

from src.funciones import *

def run_ppp_calculation(armode, ephopt):
    #Navigation and observation files
    navfile = 'data\\rinex\\_2\\COM3___115200_240127_154648_2.nav' 
    obsfile = 'data\\rinex\\_2\\COM3___115200_240127_154648_2.obs' 

    # Specify PPP correction files
    orbfile = 'data\\rinex\\_2\\GRG0OPSRAP_20240270000_01D_05M_ORB.SP3'
    clkfile = 'data\\rinex\\_2\\GRG0OPSRAP_20240270000_01D_30S_CLK.CLK'
    bsxfile = 'data\\rinex\\_2\\GRG0OPSRAP_20240270000_01D_01D_OSB.BIA'

    atxfile = 'data\\rinex\\file_creator\\I20.ATX'
    csfile = None

    # Set user reference position
    xyz_ref = [4780096.3977 ,  179965.3669 , 4204974.9618] # == rnx.pos
    pos_ref = ecef2pos(xyz_ref) # ECEF to LLH position conversion

    ### Start epoch, number of epochs
    ep = [2024,1,    27 ,   15 ,   47 ,  8.9970000]
    time = epoch2time(ep)
    year = ep[0]
    doy = int(time2doy(time))

    ## Navigation and observation files
    #navfile = 'data\\rinex\\file_creator\\BRD400DLR_S_20232230000_01D_MN.rnx'
    #obsfile = 'data\\rinex\\file_creator\\SEPT223Y_copy.23O' 
#
    ## Specify PPP correction files
    #orbfile = 'data\\rinex\\file_creator\\COD0MGXFIN_20232230000_01D_05M_ORB.SP3'
    #clkfile = 'data\\rinex\\file_creator\\COD0MGXFIN_20232230000_01D_30S_CLK.CLK'
    #bsxfile = 'data\\rinex\\file_creator\\COD0MGXFIN_20232230000_01D_01D_OSB.BIA'
#
    #atxfile = 'data\\rinex\\file_creator\\I20.ATX'
    #csfile = None
#
    ## Set user reference position
    #xyz_ref = [-3962109.1468, 3381310.3630, 3668679.4312] # == rnx.pos
    #pos_ref = ecef2pos(xyz_ref) # ECEF to LLH position conversion
#
    #### Start epoch, number of epochs
    #ep = [2023, 8, 11, 21, 0, 0]
    #time = epoch2time(ep)
    #year = ep[0]
    #doy = int(time2doy(time))



    # Define signals to be processed
    #NOTE: El principal problema es que sigs es un object rSigRnx y no puedo ver su valor de una forma normal.
    #           SOLUCION: pasar las frecuencias primero como un str y luego meterlas en un objeto rSigRnx

    # Pasamos las frecuencias escogidas como un array de str
    freq = 1
    if freq == 1:
        sigs_str = [
            "GC1C", "EC1C", "RC1C",
            "GL1C", "EL1C", "RL1C",
            "GD1C", "ED1C", "RD1C",
            "GS1C", "ES1C", "RS1C"
        ]# single-frequency
    else:
        sigs_str = [
            "GC1C", "GC2W",
            "GL1C", "GL2W",
            "GS1C", "GS2W",
            "EC1C", "EC5Q",
            "EL1C", "EL5Q",
            "ES1C", "ES5Q"
        ]#dual-frequency


    # Converting to an "rSigRnx" obj
    sigs = []
    for sig in sigs_str:
        sigs.append(rSigRnx(sig))


    rnx = rnxdec() # RINEX 
    rnx.setSignals(sigs)

    nav = Nav()
    obs = Obs()
    orb = peph()


    # Decode RINEX NAV data
    nav = rnx.decode_nav(navfile, nav)


    # Load precise orbits and clock offsets
    nav = orb.parse_sp3(orbfile, nav)
    nav = rnx.decode_clk(clkfile, nav)

    # Load code and phase biases from Bias-SINEX
    bsx = biasdec()
    bsx.parse(bsxfile)

    # Load ANTEX data for satellites and stations
    if atxfile is not None:
        atx = atxdec()
        atx.readpcv(atxfile)

    nav.monlevel = 1  # Logging level

    # Load RINEX OBS file header
    if rnx.decode_obsh(obsfile) >= 0:

        # Auto-substitute signals
        rnx.autoSubstituteSignals()

        # Initialize position
        pppPosition = pppos(nav, rnx.pos, 'data\\log\\ppp-igs.log')


        # change default settings
        nav.elmin = np.deg2rad(5.0)  # min sat elevation (5.0)
        nav.thresar = 2.0            # ambiguity resolution threshold (2.0)
        nav.armode = armode               # 0:float-ppp,1:continuous,2:instantaneous,3:fix-and-hold (3)
        nav.ephopt = ephopt               # ephemeris option 0: BRDC, 1: SBAS, 2: SSR-APC, 3: SSR-CG, 4: PREC (4)
        nav.pmode = 0                 # Positioning mode: 0:static, 1:kinematic  
    
        system_freq = checkSystemFrequency(sigs_str)


        if system_freq["GPS"] == 'single-frequency': # TODO: add other systems 
            nav.nf = 1     # Numero de frecuencias (default == 2)
            nav.niono = 0  # Este parámetro es importante para el cálculo de ionofree utilizando dual-frequency

        if csfile is None or csfile == '': # Missing cssr file 
            nav.trop_opt = 0         # 0: use trop-model, 1: estimate, 2: use cssr correction
            nav.iono_opt = 0         # 0: use iono-model, 1: estimate, 2: use cssr correction
        else:
            nav.trop_opt = 2         # 0: use trop-model, 1: estimate, 2: use cssr correction
            nav.iono_opt = 2         # 0: use iono-model, 1: estimate, 2: use cssr correction


        # NOTE: fix-and-hold > continous > instantaneous > float-PPP


        # Set PCO/PCV information # TODO: Crear una funcion que modifique el archivo .atx y al final añada los parametros a +0.0
        if rnx.ant is None or rnx.ant.strip() == "":
            nav.fout.write("ERROR: missing antenna type <{}> in ANTEX file! Changing to ANTENA_INVENTADA...\n"
                           .format(rnx.ant))
            rnx.ant = 'ANTENA_INVENTADA    '

            nav.sat_ant = atx.pcvs
            nav.rcv_ant = searchpcv(atx.pcvr, rnx.ant,  rnx.ts)
        else:
            nav.sat_ant = atx.pcvs
            nav.rcv_ant = searchpcv(atx.pcvr, rnx.ant,  rnx.ts)


    # Simulation time 
    nep = 18 * 60  # 5 minutes

    # Intialize data structures for results
    t = np.zeros(nep)
    tc = np.zeros(nep)
    enu = np.ones((nep, 3))*np.nan
    sol = np.zeros((nep, 4))
    dop = np.zeros((nep, 4))
    ztd = np.zeros((nep, 1))
    smode = np.zeros(nep, dtype=int)

    sol_ = np.ones((nep, 3))*np.nan # Variable de prueba para comprobar "sol"

    # Skip epochs until start time
    obs = rnx.decode_obs() # NOTE: Aqui se hace un update al obs.lli
    while time > obs.t and obs.t.time != 0:
        obs = rnx.decode_obs()



    # Loop over number of epoch from file start
    for ne in range(nep):

        # Set initial epoch
        if ne == 0:
            nav.t = deepcopy(obs.t)
            t0 = deepcopy(obs.t)


        # Call PPP module with IGS products
        pppPosition.process(obs, cs=None, orb=orb, bsx=bsx, obsb=None)   
        # Save output
        t[ne] = timediff(nav.t, t0) / 86400.0

        sol = nav.xa[0:3] if nav.smode == 4 else nav.x[0:3] # Guarda la posicion calculada en "process"

        sol_[ne, :] = sol # ECEF --> LLA (needed to .kml)

        # NOTE: "sol-xyz_ref" porque estamos en "nav.pmode = 0" --> static
        enu[ne, :] = gn.ecef2enu(pos_ref, sol-xyz_ref)  # ENU -->  East, North, Up 
                                                        # ECEF --> Earth-Centered, Earth-Fixed

        indice_IT = pppPosition.IT(nav.na)
        ztd[ne] = nav.xa[indice_IT] if nav.smode == 4 else nav.x[indice_IT]
        # TODO: implementar tambien "II(self, s, na)" --> (nav.x[pppPosition.II(obs.sat,nav.na)])

        smode[ne] = nav.smode

        # Get new epoch, exit after last epoch
        obs = rnx.decode_obs()
        if obs.t.time == 0:
            break



    # Close RINEX observation file
    rnx.fobs.close() 

    ########################################################
    if nav.fout is not None:
        nav.fout.close()
    ########################################################


    resultado = [np.mean(enu[:, 0]), np.mean(enu[:, 1]), np.mean(enu[:, 2])]

    return resultado



# Definir rangos de valores para los parámetros
armode_values = [0, 1, 2, 3]  # 0:float-ppp, 1:continuous, 2:instantaneous, 3:fix-and-hold
ephopt_values = [0, 1, 2, 3, 4]  # 0: BRDC, 1: SBAS, 2: SSR-APC, 3: SSR-CG, 4: PREC

# Diccionario para almacenar los resultados
results = {}

# Bucle anidado para probar todas las combinaciones de parámetros
i = 0
for armode in armode_values:
    for ephopt in ephopt_values:
        # Ejecutar cálculo con la combinación actual de parámetros
        print("{:5.2f}%".format(i/20 * 100))
        result = run_ppp_calculation(armode, ephopt)
        
        # Guardar el resultado
        results[(armode, ephopt)] = result
        i = i + 1 



# Imprimir los resultados
with open("resultados", "w") as file:
    for params, result in results.items():
        print(f"Parámetros: {params}, Resultado: {result}")
        file.write("Parámetros: {}, Resultado: {}\n".format(params, result))

