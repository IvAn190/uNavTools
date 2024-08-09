"""
Module to compute RTK solution
"""

import sys
from sys import stdout
import os


from src.funciones import *


from copy import deepcopy
import matplotlib.pyplot as plt
import numpy as np


from cssrlib.rinex import rnxdec, sync_obs
from cssrlib.ephemeris import findeph, eph2pos
from cssrlib.rtk import rtkpos
from cssrlib.gnss import Nav, Obs, uGNSS
from cssrlib.gnss import time2doy, time2str, timediff, epoch2time, time2epoch, ecef2enu, ecef2pos, sys2str, satazel, geodist
from cssrlib.gnss import rSigRnx
from cssrlib.peph import atxdec, searchpcv
from cssrlib.peph import peph, biasdec

from cssrlib.plot import skyplot

class ParametrosRTK():
    """
    Class for RTK module
    """
    def __init__(self):
        self.navfile = None
        self.obsfile = None     # rov
        self.basefile = None    # base

        self.orbfile = None
        self.clkfile = None
        self.bsxfile = None
        self.atxfile = None
        self.csfile = None

        self.xyz_ref = None         # rov
        self.xyz_ref_base = None    # base
        self.ep = None

        self.freq = 2           # 1:single-frequency, 2:dual-frequency
        self.nep = 0            
        self.pmode = 0          # 0:static, 1:kinematic
        self.armode = 3         # 0:float-ppp,1:continuous,2:instantaneous,3:fix-and-hold
        self.ephopt = 4         # ephemeris option 0: BRDC, 1: SBAS, 2: SSR-APC, 3: SSR-CG, 4: PREC (4)

    
    def setParametersRTK(self, **kwargs):
        """
        Set parameters for RTK module using keyword arguments.
        
        Possible parameters:
        :navfile:   [str] Navigation file
        :obsfile:   [str] Observation file
        :basefile:  [str] Observation base file
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
                print(f"Warning: {key} is not a valid parameter of ParametrosRTK")

def rtkModule(parameters: ParametrosRTK):

    navfile = parameters.navfile
    obsfile = parameters.obsfile    #rov
    basefile = parameters.basefile  #base
    

    orbfile = parameters.orbfile
    bsxfile = parameters.bsxfile
    csfile = parameters.csfile
    clkfile = parameters.clkfile


    atxfile = parameters.atxfile

    # TODO: ver que hacer con el single y dual frequency
    # TODO: estas señales no son buenas para mis datos, pillar otras (ver que señales pilla el F9)
    ##rov
    #
    sigs_str = [
        "GC1C", "GC5X",
        "GL1C", "GL5X",
        "GS1C", "GS5X",
        "EC1X", "EC5X",
        "EL1X", "EL5X",
        "ES1X", "ES5X", 
    ]
    sigs = []
    for sig in sigs_str:
        sigs.append(rSigRnx(sig))

    ##base
    #
    sigsb_str = [
        "GC1C", "GC5X",
        "GL1C", "GL5X",
        "GS1C", "GS5X",
        "EC1X", "EC5X",
        "EL1X", "EL5X",
        "ES1X", "ES5X",
    ]
    sigsb = []
    for sig in sigsb_str:
        sigsb.append(rSigRnx(sig))          

    ##rov
    #
    rov = rnxdec()
    rov.setSignals(sigs)

    nav = Nav()
    rov.decode_nav(navfile, nav)

    ##base
    #
    base = rnxdec()
    base.setSignals(sigsb)

    base.decode_obsh(basefile)
    rov.decode_obsh(obsfile)

    # Load precise orbits and clock offsets
    if orbfile is not None:
        orb = peph()
        nav = orb.parse_sp3(orbfile, nav)
    else: orb = None 

    # Load CLK file
    if clkfile is not None:
        nav = rov.decode_clk(clkfile, nav)
    
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

    #TODO: añadir el modulo de carga de los archivos cssr, el csfile. 
    if csfile is not None:
        pass
    else: cs = None


    nav.monlevel = 1


    if rov.decode_obsh(obsfile) >= 0 or base.decode_obsh(basefile):
        #Meter el approx del rover
        if parameters.xyz_ref is not None:
            xyz_ref = parameters.xyz_ref 
        else:
            try:
                if obsfile is not None:
                    rov.decode_obsh(obsfile)
                    xyz_ref = rov.pos

                else:
                    raise ValueError("Obs file missing!!!")
                
            except Exception as error:
                print("Error: {}".format(error))
        pos_ref = ecef2pos(xyz_ref)

        ### Start epoch, number of epochs
        if parameters.ep is not None:
            ep = parameters.ep #parameters.ep
        else: 
            try:
                if obsfile is not None:
                    rov.decode_obsh(obsfile)
                    ep = time2epoch(rov.ts)
                
            except Exception as error:
                print("Error: {}".format(error))
        
        time = epoch2time(ep)
        year = ep[0]
        doy = int(time2doy(time))
    	
        # Auto-substitute signals
        rov.autoSubstituteSignals()
        base.autoSubstituteSignals()

        rtkPosition = rtkpos(nav, rov.pos, 'data/log/rtk-igs.log')

        # change default settings
        nav.elmin = np.deg2rad(5.0)  # min sat elevation (5.0)
        nav.thresar = 2.0            # ambiguity resolution threshold (2.0)

        nav.pmode = parameters.pmode # Positioning mode: 0:static, 1:kinematic


        # TODO: ver como esta en el PPP y hacerlo igual. Quizas en RTK al ser mas robusto, podemos aplicar mas fix and hold 
        if orbfile is not None:     #(IGS file corrections)
            nav.armode = 4
            if parameters.freq == 1:
                nav.armode = 1      #continous (if single-frequency)
            else:
                nav.armode = 3      #fix-and-hold 
        else:
            nav.armode = 1

        # Check rover frequency
        system_freq = checkSystemFrequency(sigs_str) #rov

        if system_freq["GPS"] == 'single-frequency': # TODO: add other systems 
            nav.nf = 1     # Number of frequencies (default == 2)
            nav.niono = 0  
        
        if csfile is None or csfile == '': # Missing cssr file 
            nav.trop_opt = 0         # 0: use trop-model, 1: estimate, 2: use cssr correction
            nav.iono_opt = 0         # 0: use iono-model, 1: estimate, 2: use cssr correction
        else:
            nav.trop_opt = 2         # 0: use trop-model, 1: estimate, 2: use cssr correction
            nav.iono_opt = 2         # 0: use iono-model, 1: estimate, 2: use cssr correction

        # Set PCO/PCV information 
        #rover
        #
        #rov.ant = None
        #base.ant = None
        if rov.ant is None or rov.ant.strip() == "":
            nav.fout.write("ERROR: missing antenna type <{}> in ANTEX file! Changing to ANTENA_INVENTADA...\n"
                        .format(rov.ant))
            rov.ant = 'ANTENA_INVENTADA    '    
            nav.rcv_ant = searchpcv(atx.pcvr, rov.ant,  rov.ts)

        else:
            nav.rcv_ant = searchpcv(atx.pcvr, rov.ant,  rov.ts)
        #base
        #
        if base.ant is None or base.ant.strip() == "":
            nav.fout.write("ERROR: missing antenna type <{}> in ANTEX file! Changing to ANTENA_INVENTADA...\n"
                            .format(base.ant))
            base.ant = 'ANTENA_INVENTADA    '
            nav.rcv_ant_b = searchpcv(atx.pcvr, base.ant,  base.ts)

        else:
            nav.rcv_ant_b = searchpcv(atx.pcvr, base.ant,  base.ts)


        #base
        #
        if parameters.xyz_ref_base is not None:
            nav.rb = parameters.xyz_ref_base 
        else: 
            nav.rb = base.pos        

    # fout
    
#############################################
    # Get equipment information
    #
    nav.fout.write("FileName: {}\n".format(obsfile))
    nav.fout.write("Start   : {}\n".format(time2str(rov.ts)))
    if rov.te is not None:
        nav.fout.write("End     : {}\n".format(time2str(rov.te)))
    nav.fout.write("Rover: \n")
    nav.fout.write("Receiver: {}\n".format(rov.rcv))
    nav.fout.write("Antenna : {}\n".format(rov.ant))
    nav.fout.write("\n")
    nav.fout.write("Base: \n")
    nav.fout.write("Receiver: {}\n".format(base.rcv))
    nav.fout.write("Antenna : {}\n".format(base.ant))
    nav.fout.write("\n")

    if 'UNKNOWN' in rov.ant or rov.ant.strip() == "":
        nav.fout.write("ERROR: missing antenna type in RINEX ROVER OBS header!\n")
    if 'UNKNOWN' in base.ant or base.ant.strip() == "":
        nav.fout.write("ERROR: missing antenna type in RINEX BASE OBS header!\n")

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


    print("Rover available signals")
    nav.fout.write("Rover available signals\n")
    for sys, sigs in rov.sig_map.items():
        txt = "{:7s} {}\n".format(sys2str(sys), ' '.join([sig.str() for sig in sigs.values()]))
        nav.fout.write(txt)
        print(txt, end='')
    nav.fout.write("\n")
    print()

    print("Rover selected signals")
    nav.fout.write("Rover selected signals\n")
    for sys, tmp in rov.sig_tab.items():
        txt = "{:7s} ".format(sys2str(sys))
        for _, sigs in tmp.items():
            txt += "{} ".format(' '.join([sig.str() for sig in sigs]))
        txt += "\n"
        nav.fout.write(txt)
        print(txt, end='')
    nav.fout.write("\n")
    print()

    print("Base available signals")
    nav.fout.write("Base available signals\n")
    for sys, sigs in base.sig_map.items():
        txt = "{:7s} {}\n".format(sys2str(sys), ' '.join([sig.str() for sig in sigs.values()]))
        nav.fout.write(txt)
        print(txt, end='')
    nav.fout.write("\n")
    print()

    print("Base selected signals")
    nav.fout.write("Base selected signals\n")
    for sys, tmp in base.sig_tab.items():
        txt = "{:7s} ".format(sys2str(sys))
        for _, sigs in tmp.items():
            txt += "{} ".format(' '.join([sig.str() for sig in sigs]))
        txt += "\n"
        nav.fout.write(txt)
        print(txt, end='')
    nav.fout.write("\n")
    print()


    nav.fout.write("RTK SOLUTION:\n")
    #############################################

    # Simulation time 
    nep = parameters.nep * 60  # 5 minutes 

    # Intialize data structures for results
    t = np.zeros(nep)
    tc = np.zeros(nep)
    enu = np.ones((nep, 3))*np.nan
    sol = np.zeros((nep, 4))
    dop = np.zeros((nep, 4))
    ztd = np.zeros((nep, 1))
    smode = np.zeros(nep, dtype=int)

    sol_ = np.ones((nep, 3))*np.nan 

    azm = np.ones((nep, uGNSS.MAXSAT))*np.nan # Needed to skyplot 
    elv = np.ones((nep, uGNSS.MAXSAT))*np.nan
    snr_plt = np.ones((nep, uGNSS.MAXSAT))*np.nan

    # Skip epochs until start time
    rov_obs = rov.decode_obs() 
    while time > rov_obs.t and rov_obs.t.time != 0:
        rov_obs = rov.decode_obs()

    base_obs = base.decode_obs() 
    while time > base_obs.t and base_obs.t.time != 0:
        base_obs = base.decode_obs()



    for ne in range(nep):
        rov_obs, base_obs = sync_obs(rov, base)

        if ne == 0:
            t0 = nav.t = rov_obs.t
        
        rtkPosition.process(rov_obs, obsb=base_obs)
        rtkPosition.process(obs = rov_obs, cs = cs , orb = orb, bsx = bsx, obsb=base_obs)
        t[ne] = timediff(nav.t, t0)

        sol = nav.xa[0:3] if nav.smode == 4 else nav.x[0:3]

        sol_[ne,:] = sol

        if nav.pmode == 0: # Static
            enu[ne, :] = ecef2enu(pos_ref, sol-xyz_ref)     # ENU -->  East, North, Up 
                                                            # ECEF --> Earth-Centered, Earth-Fixed

        smode[ne] = nav.smode

        # NOTE: skyplot module 
        for k, sat in enumerate(rov_obs.sat):
            eph = findeph(nav.eph, rov_obs.t, sat)
            if eph is None:
                continue
            rs, dts = eph2pos(rov_obs.t, eph)
            r, e = geodist(rs, xyz_ref)
            azm[ne, sat-1], elv[ne, sat-1] = satazel(pos_ref, e)



        stdout.write('\r {} ENU: {:7.3f} {:7.3f} {:7.3f}, 2D {:6.3f}, mode {:1d} \n'
                .format(time2str(rov_obs.t),
                        enu[ne, 0], enu[ne, 1], enu[ne, 2],
                        np.sqrt(enu[ne, 0]**2+enu[ne, 1]**2),
                        smode[ne]))
        
        ################################################### All in ECEF
        nav.fout.write("{}Sol: [{:14.4f}, {:14.4f}, {:14.4f}] "
                       "ENU: [{:7.3f}, {:7.3f}, {:7.3f}] "
                       "ZTD: [{:9.7f}] "  
                       "mode [{:1d}]\n"
                       .format(time2str(rov_obs.t) + " ",  
                               sol[0], sol[1], sol[2],
                               enu[ne, 0], enu[ne, 1], enu[ne, 2],    
                               ztd[ne].item(),  
                               smode[ne]))

        ###################################################

        rov_obs = rov.decode_obs()
        if rov_obs.t.time == 0:
            break

    # Close RINEX observation file
    rov.fobs.close() 
    base.fobs.close() 

    if nav.fout is not None:
        nav.fout.close()
    
    return t, enu, sol_, ztd, smode, azm, elv, xyz_ref