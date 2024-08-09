"""
Module to compute PPP solution

Corrections: https://cddis.nasa.gov/archive/gnss/products/
"""

import sys
from sys import stdout
import os

import pandas as pd

from cssrlib.plot import *


from copy import deepcopy
import matplotlib.pyplot as plt
import matplotlib.dates as md
import numpy as np

from cssrlib.ephemeris import findeph, eph2pos
import cssrlib.gnss as gn
from cssrlib.gnss import ecef2pos, Nav, Obs
from cssrlib.gnss import time2doy, time2str, timediff, epoch2time, time2epoch, satazel, geodist
from cssrlib.gnss import rSigRnx
from cssrlib.gnss import sys2str
from cssrlib.peph import atxdec, searchpcv
from cssrlib.peph import peph, biasdec


from cssrlib.rinex import rnxdec
from cssrlib.pppssr import pppos

from src.funciones import *
from src.plot import *

class ParametrosPPP():
    """
    Class for PPP module
    """
    def __init__(self):
        self.navfile = None
        self.obsfile = None
        self.orbfile = None
        self.clkfile = None
        self.bsxfile = None
        self.atxfile = None
        self.csfile = None

        self.xyz_ref = None
        self.ep = None

        self.freq = 2           # 1:single-frequency, 2:dual-frequency
        self.nep = 0            
        self.pmode = 0          # 0:static, 1:kinematic
        self.armode = 3         # 0:float-ppp,1:continuous,2:instantaneous,3:fix-and-hold
        self.ephopt = 4         # ephemeris option 0: BRDC, 1: SBAS, 2: SSR-APC, 3: SSR-CG, 4: PREC (4)

    
    def setParametersPPP(self, **kwargs):
        """
        Set parameters for PPP module using keyword arguments.
        
        Possible parameters:
        :navfile:   [str] Navigation file
        :obsfile:   [str] Observation file
        :orbfile:   [str] Orbit file
        :clkfile:   [str] Clock file
        :bsxfile:   [str] Bias-SINEX file
        :atxfile:   [str] Antenna file
        :csfile:    [str] Code-space file
        :xyz_ref:   [list of int] Reference coordinates [x, y, z]
        :ep:        [list of float] Epochs
        :pmode:     [int] Processing mode
        :freq:      [int] Frequency
        :nep:       [int] Number of epochs
        """
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
            else:
                print(f"Warning: {key} is not a valid parameter of ParametrosPPP")

    def verify_parameters(self):
        # TODO: update this function
        flag = True
        # Verifica que los archivos sean arrays o None
        for attr in ['navfile', 'obsfile', 'orbfile', 'clkfile', 'bsxfile', 'atxfile', 'csfile']:
            if getattr(self, attr) is not None and not isinstance(getattr(self, attr), str):
                flag =  False
        
        # Verifica que xyz_ref sea una lista o tupla de tres flotantes
        if not (isinstance(self.xyz_ref, (list, tuple)) and len(self.xyz_ref) == 3 and all(isinstance(coord, float) for coord in self.xyz_ref)):
            flag =  False
        
        # Verifica que ep sea una lista o tupla de seis enteros
        if not (isinstance(self.ep, (list, tuple)) and len(self.ep) == 6 and all(isinstance(num, int) for num in self.ep)):
            flag =  False
        
        # Verifica que freq y nep sean enteros
        if not all(isinstance(getattr(self, attr), int) for attr in ['freq', 'nep', 'pmode']):
            flag =  False
        
        if not flag:
            print("""
                :navfile:   [str] 
                :obsfile:   [str]
                :orbfile:   [str]
                :clkfile:   [str]
                :bsxfile:   [str]
                :atxfile:   [str]
                :csfile:    [str]
                :xyz_ref:   [int array [3]]
                :ep:        [float array [6]]
                :pmode:     [int]
                :freq:      [int]
                :nep:       [int]
                """)
            raise ValueError("Different parameter format")

    def print_parameters(self):
        for attr, value in self.__dict__.items():
            print(f"{attr}: {value} \n")

def pppModule(parameters: ParametrosPPP):
    # Navigation and observation files
    navfile = parameters.navfile
    obsfile = parameters.obsfile

    # Specify PPP correction files
    orbfile = parameters.orbfile
    clkfile = parameters.clkfile
    bsxfile = parameters.bsxfile

    atxfile = parameters.atxfile
    csfile = parameters.csfile

    rnx = rnxdec() # RINEX decoder

    # Define signals to be processed
    # Pasamos las frecuencias escogidas como un array de str
    freq = parameters.freq
    if freq == 1:
        sigs_str = [
            "GC1C", "EC1X",
            "GL1C", "EL1X",
            "GD1C", "ED1X",
            "GS1C", "ES1X"  
        ]  # single-frequency
    else:
        sigs_str = [
            "GC1C", "GC5X",
            "GL1C", "GL5X",
            "GS1C", "GS5X",
            "EC1X", "EC5X",
            "EL1X", "EL5X",
            "ES1X", "ES5X",
        ]  # dual-frequency





    # Converting to an "rSigRnx" obj
    sigs = []
    for sig in sigs_str:
        sigs.append(rSigRnx(sig))

    rnx.setSignals(sigs)

    if navfile is None or obsfile is None:
        raise ValueError("Navfile or Obsfile are missing!!!")

    nav = Nav()
    obs = Obs()


    # Decode RINEX NAV data
    nav = rnx.decode_nav(navfile, nav)

    # Load precise orbits and clock offsets
    if orbfile is not None:
        orb = peph()
        nav = orb.parse_sp3(orbfile, nav)
    else: orb = None 

    # Load CLK file
    if clkfile is not None:
        nav = rnx.decode_clk(clkfile, nav)    

    # Load code and phase biases from Bias-SINEX
    if bsxfile is not None:
        bsx = biasdec()
        bsx.parse(bsxfile)
    else: bsx = None

    # Load ANTEX data for satellites and stations
    if atxfile is not None:
        atx = atxdec()
        atx.readpcv(atxfile)
    else:
        raise ValueError("Missing ATX file!!!")
    #TODO: hacer una funcion que cree un archivo .atx y meta los parametros .atx, quizas meto en data permanentemente el archivo no? 

    #TODO: añadir el modulo de carga de los archivos cssr, el csfile. 
    if csfile is not None:
        pass
    else: cs = None


    nav.monlevel = 1  # Logging level

    # Load RINEX OBS file header
    if rnx.decode_obsh(obsfile) >= 0:

        # Set user reference position
        if parameters.xyz_ref is not None:
            xyz_ref = parameters.xyz_ref # == rnx.pos
        else:
            try:
                if obsfile is not None:
                    rnx.decode_obsh(obsfile)
                    xyz_ref = rnx.pos

                else:
                    raise ValueError("Obs file missing!!!")

            except Exception as error:
                print("Error: {}".format(error))

        pos_ref = ecef2pos(xyz_ref) # ECEF to LLH position conversion

        ### Start epoch, number of epochs
        if parameters.ep is not None:
            ep = parameters.ep
        else: 
            try:
                if obsfile is not None:
                    rnx.decode_obsh(obsfile)
                    ep = time2epoch(rnx.ts)
                
            except Exception as error:
                print("Error: {}".format(error))
        
        time = epoch2time(ep)
        year = ep[0]
        doy = int(time2doy(time))


        # Auto-substitute signals
        rnx.autoSubstituteSignals()

        # Initialize position
        pppPosition = pppos(nav, rnx.pos, 'data\\log\\ppp-igs.log')


        # change default settings
        nav.elmin = np.deg2rad(5.0)     # min sat elevation (5.0)
        nav.thresar = 2.0               # ambiguity resolution threshold (2.0) 

        nav.pmode = parameters.pmode    # Positioning mode: 0:static, 1:kinematic

        if orbfile is not None:         #(IGS file corrections)
            nav.ephopt = 4              # ephemeris option 0: BRDC, 1: SBAS, 2: SSR-APC, 3: SSR-CG, 4: PREC (4)
            if freq == 1:               # Single-frequency
                nav.armode = 1          # 0:float-ppp,1:continuous,2:instantaneous,3:fix-and-hold
            else: 
                nav.armode = 3       
        else:
            nav.armode = 1              # 0:float-ppp,1:continuous,2:instantaneous,3:fix-and-hold
          
        system_freq = checkSystemFrequency(sigs_str)

        if system_freq["GPS"] == 'single-frequency': # TODO: add other systems 
            nav.nf = 1     # Numero de frecuencias (default == 2)
            nav.niono = 0  # NOTE: Este parametro es importante para el calculo de ionofree utilizando dual-frequency

        if csfile is None or csfile == '': # Missing cssr file 
            nav.trop_opt = 0         # 0: use trop-model, 1: estimate, 2: use cssr correction
            nav.iono_opt = 0         # 0: use iono-model, 1: estimate, 2: use cssr correction
        else:
            nav.trop_opt = 2         # 0: use trop-model, 1: estimate, 2: use cssr correction
            nav.iono_opt = 2         # 0: use iono-model, 1: estimate, 2: use cssr correction


        # Set PCO/PCV information 
        if rnx.ant is None or rnx.ant.strip() == "":
            nav.fout.write("ERROR: missing antenna type <{}> in ANTEX file! Changing to ANTENA_INVENTADA...\n"
                           .format(rnx.ant))
            rnx.ant = 'ANTENA_INVENTADA    '

            nav.sat_ant = atx.pcvs
            nav.rcv_ant = searchpcv(atx.pcvr, rnx.ant,  rnx.ts)
        else:
            nav.sat_ant = atx.pcvs
            nav.rcv_ant = searchpcv(atx.pcvr, rnx.ant,  rnx.ts)



    #############################################
    # Get equipment information
    #
    nav.fout.write("FileName: {}\n".format(obsfile))
    nav.fout.write("Start   : {}\n".format(time2str(rnx.ts)))
    if rnx.te is not None:
        nav.fout.write("End     : {}\n".format(time2str(rnx.te)))
    nav.fout.write("Receiver: {}\n".format(rnx.rcv))
    nav.fout.write("Antenna : {}\n".format(rnx.ant))
    nav.fout.write("\n")

    if 'UNKNOWN' in rnx.ant or rnx.ant.strip() == "":
        nav.fout.write("ERROR: missing antenna type in RINEX OBS header!\n")


    nav.fout.write("\n")

    nav.fout.write("SETUP:\n") 
    #TODO: guardar la configuracion "nav.@" que haya cambiado en la configuracion arriba (linea 100)
    nav.fout.write("Minimum elevation: {}\n".format(nav.elmin * 180/np.pi))
    nav.fout.write("Ambiguity: {}\n".format(nav.thresar))
    nav.fout.write("ARmode: {} (0:float-ppp,1:continuous,2:instantaneous,3:fix-and-hold)\n".format(nav.armode))
    nav.fout.write("Ephemeris: {} (0: BRDC, 1: SBAS, 2: SSR-APC, 3: SSR-CG, 4: PREC)\n".format(nav.ephopt))
    nav.fout.write("Position mode: {} (0:static, 1:kinematic)\n".format(nav.pmode))
    nav.fout.write("Frequency: {}\n".format(system_freq))
    nav.fout.write("\n")


    print("Available signals")
    nav.fout.write("Available signals\n")
    for sys, sigs in rnx.sig_map.items():
        txt = "{:7s} {}\n".format(sys2str(sys),
                                  ' '.join([sig.str() for sig in sigs.values()]))
        nav.fout.write(txt)
        print(txt)
    nav.fout.write("\n")

    print("\nSelected signals")
    nav.fout.write("Selected signals\n")
    for sys, tmp in rnx.sig_tab.items():
        txt = "{:7s} ".format(sys2str(sys))
        for _, sigs in tmp.items():
            txt += "{} ".format(' '.join([sig.str() for sig in sigs]))
        nav.fout.write(txt+"\n")
        print(txt)
    nav.fout.write("\n")

    nav.fout.write("PPP SOLUTION:\n")
    #############################################


    # Simulation time 
    nep = parameters.nep * 60  

    # Intialize data structures for results
    t = np.zeros(nep)
    tc = np.zeros(nep)
    enu = np.ones((nep, 3))*np.nan
    sol = np.zeros((nep, 4))
    dop = np.zeros((nep, 4))
    ztd = np.zeros((nep, 1))
    smode = np.zeros(nep, dtype=int)

    sol_ = np.ones((nep, 3))*np.nan # Variable de prueba para comprobar "sol"

    azm = np.ones((nep, uGNSS.MAXSAT))*np.nan # Needed to skyplot 
    elv = np.ones((nep, uGNSS.MAXSAT))*np.nan
    snr_plt = np.ones((nep, uGNSS.MAXSAT))*np.nan

    # Skip epochs until start time
    obs = rnx.decode_obs() # NOTE: Aqui se hace un update al obs.lli
    while time > obs.t and obs.t.time != 0:
        obs = rnx.decode_obs()

    ionosfera_ = np.empty(nep, dtype=object)

    #NOTE: La funcion "process" calcula "nav.xa" && "nav.x" y segun el modo que estemos ejecutando "smode", 
    #      escogemos una u otra como solucion. 
    #NOTE: Me interesa un mode de 4, ya que smode = 4 indica una mayor precisión y confianza en la resolución de ambigüedades, 
    #      mientras que smode = 5 indica que las ambigüedades se están utilizando en el cálculo, pero con un nivel de precisión menor. 
    #NOTE: accuracy --> nav.xa > nav.x --> nav.xa == mode=4 (valor entero --> ++precision)
    #                                  --> nav.x  == mode=5 (valor flotante --> --precision)
    #NOTE: matriz obs.lli --> cada fila corresponde a un satélite y cada columna a una señal de fase de portadora (L). Al tener
    #      un receptor songle-frequency (L1), la matriz obs.lli es de Mx1, dando error ya que se necesita de Mx2. 


    # TODO: Encontrar un archivo de ionosfera
    #       En el codigo, el archivo se llama cs (cssr) y se mete en la funcion porcess() y se ejecuta en pppssr.py line 491
    #       Aqui hay un ejemoplo de como utilizar el cs --> (https://github.com/hirokawa/cssrlib-data/blob/main/samples/test_ppprtcm.py)
    # TODO: Comprobar que hacen los paramtros de na. relacionados con la iono y tropo.  

    # Loop over number of epoch from file start
    for ne in range(nep):

        # Set initial epoch
        if ne == 0:
            nav.t = deepcopy(obs.t)
            t0 = deepcopy(obs.t)


        # Call PPP module with IGS products
        pppPosition.process(obs, cs=cs, orb=orb, bsx=bsx, obsb=None)   
        # Save output
        t[ne] = timediff(nav.t, t0) / 86400.0

        sol = nav.xa[0:3] if nav.smode == 4 else nav.x[0:3] # Guarda la posicion calculada en "process"

        sol_[ne, :] = sol # ECEF --> LLA (needed to .kml)


        if nav.pmode == 0: # Static
            enu[ne, :] = gn.ecef2enu(pos_ref, sol-xyz_ref)  # ENU -->  East, North, Up 
                                                            # ECEF --> Earth-Centered, Earth-Fixed


        indice_IT = pppPosition.IT(nav.na)
        ztd[ne] = nav.xa[indice_IT] if nav.smode == 4 else nav.x[indice_IT]
        # TODO: implementar tambien "II(self, s, na)" --> (nav.x[pppPosition.II(obs.sat,nav.na)])

        smode[ne] = nav.smode

        if freq > 1: # No disponible para Single-frequency
            ionosfera_[ne] = nav.xa[pppPosition.II(obs.sat,nav.na)] if nav.smode == 4 else nav.x[pppPosition.II(obs.sat,nav.na)]
    
        
        ## NOTE: el SNR = obs.S
        #for sat, snr in enumerate(obs.S):
        #    snr_plt[ne, sat-1] = snr

        # NOTE: skyplot module 
        for k, sat in enumerate(obs.sat):
            eph = findeph(nav.eph, obs.t, sat)
            if eph is None:
                continue
            rs, dts = eph2pos(obs.t, eph)
            r, e = geodist(rs, xyz_ref)
            azm[ne, sat-1], elv[ne, sat-1] = satazel(pos_ref, e)


        # Log to standard output #TODO: add "sol" in the output
        stdout.write('\r {} ENU: {:7.3f} {:7.3f} {:7.3f}, 2D {:6.3f}, mode {:1d} \n'
                     .format(time2str(obs.t),
                             enu[ne, 0], enu[ne, 1], enu[ne, 2],
                             np.sqrt(enu[ne, 0]**2+enu[ne, 1]**2),
                             smode[ne]))
    
        ################################################### All in ECEF
        nav.fout.write("{}Sol: [{:14.4f}, {:14.4f}, {:14.4f}] "
                       "ENU: [{:7.3f}, {:7.3f}, {:7.3f}] "
                       "ZTD: [{:9.7f}] "  
                       "mode [{:1d}]\n"
                       .format(time2str(obs.t) + " ",  
                               sol[0], sol[1], sol[2],
                               enu[ne, 0], enu[ne, 1], enu[ne, 2],    
                               ztd[ne].item(),  
                               smode[ne]))

        ###################################################

        # Get new epoch, exit after last epoch
        obs = rnx.decode_obs()
        if obs.t.time == 0:
            break

    # Close RINEX observation file
    rnx.fobs.close() 
    
    if nav.fout is not None:
        nav.fout.close()
    



    return t, enu, sol_, ztd, smode, azm, elv, xyz_ref