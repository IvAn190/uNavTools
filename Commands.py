import argparse
import os
import re

from src.funciones import *
from src.PPPsolution import ParametrosPPP, pppModule
from src.RTKsolution import ParametrosRTK, rtkModule
from src.plot import *
from src.ubx_parser import *

from cssrlib.plot import skyplot


## Posibles inputs para test:
#
# python.exe .\Commands.py -getdata -t 1 -port 'COM4'
# python .\Commands.py -rtk -folder 'D:\Programacion\TFG\TFG---Updated\data\rinex\RTK' -f 2 -t 10 -plot
# 
# Sin correcciones: python.exe .\Commands.py -ppp -t 30 -f 2 -folder '.\data\rinex\mantener\SinCorrections\' -plot -xyz -3962108.6726 3381309.4719 3668678.6264
# Con correcciones: python.exe .\Commands.py -ppp -t 30 -f 2 -folder '.\data\rinex\file_creator\' -plot -xyz -3962108.6726 3381309.4719 3668678.6264
# 
# 
# 
def parse_arguments():
    parser = argparse.ArgumentParser(description='Process GNSS data.')
    parser.add_argument('-printhelp', '--printhelp', action='store_true', help='Print extended help message')

    parser.add_argument('-nav', '--navfile', type=str, default=None, help='Navigation file for PPP solution.')
    parser.add_argument('-obs', '--obsfile', type=str, default=None, help='Observation file for PPP solution.')

    parser.add_argument('-orb', '--orbfile', type=str, default=None, help='.SP3 file.')
    parser.add_argument('-clk', '--clkfile', type=str, default=None, help='.CLK file.')
    parser.add_argument('-bsx', '--bsxfile', type=str, default=None, help='.BIA file.')
    parser.add_argument('-atx', '--atxfile', type=str, default='data/rinex/file_creator/I20.ATX', help='ATX file.')

    parser.add_argument('-folder', '--folder', type=str, default=None, help='Folder path.')

    parser.add_argument('-ppp', '--ppp', action='store_true', help='Run PPP solution.')
    parser.add_argument('-rtk', '--rtk', action='store_true', help='Run RTK solution.')

    parser.add_argument('-b', '--basefile', type=str, default=None, help='Base station observation file for RTK solution.')
    parser.add_argument('-y', '--xyz_ref_base', type=float, nargs=3, default=None, help='Base station XYZ reference for RTK solution.')
    parser.add_argument('-g', '--armode', type=int, default=3, help='AR mode for RTK solution.')

    parser.add_argument('-f', '--freq', type=int, default=None, help='System frequency.')
    parser.add_argument('-e', '--ep', type=str, default=None, help='Epoch. [YYYY, MM, DD, HH, mm, ss]')
    parser.add_argument('-t', '--time', type=int, default=15, help='Time in minuts for processing GNSS data.')
    parser.add_argument('-xyz', '--xyz_ref', type=float, nargs=3, help='XYZ reference. ENU: X Y Z')
    
    parser.add_argument('-port', '--port', type=str, default='COM10', help='Port for the GNSS receiver (to handle errors, run test/test_port.py).')
    parser.add_argument('-model', '--model', type=str, default=None, help='Model of the GNSS receiver.')

    parser.add_argument('-getdata', '--getdata', action='store_true', help='Get data form UBLOX reciever. Must input too: -t <int> -port <str>')

    parser.add_argument('-plot', '--plot', action='store_true', help='Plot all the data computed by the rtk or ppp module.')
    parser.add_argument('-kml', '--kml', action='store_true', help='Plot kml map.')

    parser.add_argument('-nocheck', '--nocheck', action='store_false', help='No check if the model is a U-blox.')
    parser.add_argument('-simul', '--simul', action='store_true', help='Simulate the hardware with COM8 and COM9')



    return parser.parse_args() 

def get_name_file(folder):
    """
    Get all the name files in a folder.

    :param folder: Folder path
    :return file_name: Array with all the name files inside the folder.
    """
    file_name = None

    if not os.path.isdir(folder):
        raise ValueError("Folder path: {folder}. Empty or not created!")

    if folder == '' or folder is None:
        raise ValueError("Folder path empty or None. Don't use -folder without path.")

    
    file_name = [file for file in os.listdir(folder) if os.path.isfile(os.path.join(folder, file))]
    return file_name

def get_files(args, folder):
    """
    Assign the names of specific file types found in the 'folder' to their corresponding attributes in 'args'.

    :param args: An object (typically argparse.Namespace) that contains attributes to store file names.
    :param folder: A list of file names (strings) to be searched for specific file types.
    """
    pattern_obs = re.compile(r'.*\.\d{2}O$')  
    pattern_nav = re.compile(r'.*\.\d{2}P$') 

    pattern_basefile = re.compile(r'base')

    if args.ppp and args.folder and folder is not None:
        for file in folder:
            if '.obs' in file or pattern_obs.match(file):
                args.obsfile = file
            elif '.nav' in file or pattern_nav.match(file):
                args.navfile = file
            elif '.rnx' in file:
                args.navfile = file
            elif '.SP3' in file:
                args.orbfile = file
            elif '.CLK' in file:
                args.clkfile = file
            elif '.BIA' in file:
                args.bsxfile = file
            elif '.atx' in file:
                args.atxfile = file

    if args.rtk and args.folder and folder is not None:
        for file in folder:
            if ('.obs' in file and not 'base' in file) or (pattern_obs.match(file) and not 'base' in file): 
                args.obsfile = file
            elif 'base' in file and (pattern_obs.match(file) or '.obs' in file):
                args.basefile = file
            elif '.nav' in file or pattern_nav.match(file):
                args.navfile = file
            elif '.rnx' in file:
                args.navfile = file
            elif '.SP3' in file:
                args.orbfile = file
            elif '.CLK' in file:
                args.clkfile = file
            elif '.BIA' in file:
                args.bsxfile = file
            elif '.atx' in file:
                args.atxfile = file

def print_help():
    print( 
    """ 
    HELP MENU
    
    Module divided into three main tools:

        - Get data from UBX and parse to RINEX 3.04 [command: -getdata]
        - Compute PVT with PPP                      [command: -ppp]
        - Compute PVT with RTK                      [command: -rtk]
    
    Usage examples:
    
        getdata: python.exe .\Commands.py -getdata -t 5 -port 'COM4'
        ppp: python .\Commands.py -ppp -model 'FP9' -folder 'C:/Users/ivanr/Desktop/TFG - Updated/data/rinex/COM3___115200_202432_103932'
        rtk: python .\Commands.py -rtk -folder 'D:\Programacion\TFG\TFG---Updated\data\rinex\RTK' -f 2 -t 10 
             (warning! The basefile must have 'base' in their name in order to get the file with -folder)
    
Occasionally, warnings such as "Missing parameters" may appear. In these cases, the program can run without problems but for optimal user experience, the input provided can be further customized.

Use -folder to process the data, it is easier to make it work. :) 
    """
    ) 

def print_missing_parameters(args):
    """
    Print the parameters that are missing (i.e., have value None) in the args object.

    :param args: An object that contains attributes to store file names.
    """
    missing_params = []
    
    if args.ppp:
        args.rtk = False
    elif args.rtk:
        args.ppp = False

    excluded_params_ppp = ['basefile', 'xyz_ref_base']  # Excluded parameters when ppp == True
    excluded_params_rtk = []  # Excluded parameters when rtk == True

    if args.ppp:
        excluded_params = excluded_params_ppp
    elif args.rtk:
        excluded_params = excluded_params_rtk
    else:
        excluded_params = []

    for arg in vars(args):
        if arg in ['ppp', 'rtk'] + excluded_params:
            continue
        if getattr(args, arg) is None:
            missing_params.append(arg)

    if missing_params:
        print("Missing parameters:")
        for param in missing_params:
            print(f"- {param}")
    else:
        print("All parameters are provided.")


def check_parameters(args):
    """
    Check crucial parameters 

    :param args: An object that contains attributes to data to e process.
    """
    if not args.folder:
        return False
    
    if args.ppp and (not args.navfile or not args.obsfile):
        return False

    if args.rtk and (not args.navfile or not args.obsfile or not args.basefile):
        return False

    if not args.time:
        print("Time not set by user! [default: 6 * 3600 seconds == 6h]")
        args.time = 6 * 3600
    
    if not args.model and not args.freq:
        print("Model and frequency not set by user! [set to single frequency model]")
        args.freq = 1
    else:
        if not args.freq and args.model:  # NOTE: get frequency with model
            args.freq = freqModel(args.model)
            print(f"Frequency set to: {args.freq}, with model: {args.model}.")
        elif args.freq: 
            if args.freq < 1 or args.freq > 2:
                print("Frequency must be 1 or 2!")
                return False
        else:
            print("Frequency not set. Please specify a valid frequency.")
            return False
    return True


def construct_file_paths(folder, navfile, obsfile, orbfile, clkfile, bsxfile):

    navfile_path = f"{folder}\\{navfile}" if navfile else None
    obsfile_path = f"{folder}\\{obsfile}" if obsfile else None
    orbfile_path = f"{folder}\\{orbfile}" if orbfile else None
    clkfile_path = f"{folder}\\{clkfile}" if clkfile else None
    bsxfile_path = f"{folder}\\{bsxfile}" if bsxfile else None

    return navfile_path, obsfile_path, orbfile_path, clkfile_path, bsxfile_path

def get_current_script_path():
    return os.path.dirname(os.path.abspath(__file__))
def process_input(args): 
    name = ''
    ret = -1

    if args.time and args.time > 0 and args.getdata:
        if args.simul:
            subprocess.run(["python.exe", "src/com_simulator_manager.py"])
            name, args.model = rawData2ubx(args.time, PORT="COM9", UBX=False)
        else:
            if args.port:
                name, args.model = rawData2ubx(args.time, PORT=args.port, UBX=args.nocheck) 
            else: 
                print("Error, no port selected with -port 'COMx'")
                ret = 1
                return ret
        runconvbin(name, args.model, True) 
        if not args.ppp and not args.rtk:
            ret = 0
            return ret 


    if args.ppp:
        parameters_ppp = ParametrosPPP()
        
        # NOTE: if user selected -getdata and -ppp post processing mode
        if name != '' and args.getdata == True:
            parameters_ppp.setParametersPPP( 
            navfile= 'data\\rinex\\' + name + '\\' + name + '.nav',
            obsfile= 'data\\rinex\\' + name + '\\' + name + '.obs',
            orbfile= None,
            clkfile= None,
            bsxfile= None,
            atxfile=args.atxfile, 
            csfile=None,
            xyz_ref=args.xyz_ref,
            ep=None,
            pmode=0,
            freq=freqModel(args.model),
            nep=int(args.time)
        )
        else: # NOTE: if user did not set -getdata and wants to compute existing files 

            if args.folder and args.folder != '':
                get_files(args, get_name_file(args.folder))

            if not args.navfile or args.navfile == '' or not args.obsfile or args.obsfile == '':
                print("Missing parameters (nav or obs files)!")
                print_missing_parameters(args)
                return ret

            navfile, obsfile, orbfile, clkfile, bsxfile = construct_file_paths(args.folder, args.navfile, args.obsfile, args.orbfile, args.clkfile, args.bsxfile)

            if not check_parameters(args):
                return ret

            parameters_ppp.setParametersPPP(
                navfile=navfile,
                obsfile=obsfile,
                orbfile=orbfile,
                clkfile=clkfile,
                bsxfile=bsxfile,
                atxfile=args.atxfile, 
                csfile=None,
                xyz_ref=args.xyz_ref,
                ep=None,
                pmode=0,
                freq=args.freq,
                nep=int(args.time)
            )
        
        t, enu, sol_, ztd, smode, azm, elv, xyz_ref = pppModule(parameters_ppp)
        ret = 0

    elif args.rtk:
        parameters_rtk = ParametrosRTK()

        if args.folder and args.folder != '':
            get_files(args, get_name_file(args.folder))

        if not args.navfile or args.navfile == '' or not args.obsfile or args.obsfile == '' or not args.basefile or args.basefile == '':
            print("Missing parameters (nav, obs or base files)!")
            print_missing_parameters(args)
            return ret

        navfile, obsfile, orbfile, clkfile, bsxfile = construct_file_paths(args.folder, args.navfile, args.obsfile, args.orbfile, args.clkfile, args.bsxfile)
        basefile = f"{args.folder}\\{args.basefile}" if args.basefile else None

        if args.atxfile != 'data/rinex/file_creator/I20.ATX':
            atxfile = f"{args.folder}\\{args.atxfile}"
        else:
            atxfile = args.atxfile

        if not check_parameters(args):
            return ret

        parameters_rtk.setParametersRTK(
            navfile=navfile,
            obsfile=obsfile,  # rov
            basefile=basefile,  # base
            orbfile=orbfile,
            clkfile=clkfile,
            bsxfile=bsxfile,
            atxfile=atxfile,  
            csfile=None,
            xyz_ref=args.xyz_ref,
            xyz_ref_base=args.xyz_ref_base,
            ep=args.ep,
            pmode=0,
            armode=args.armode,
            freq=args.freq,
            nep=int(args.time)
        )

        t, enu, sol_, ztd, smode, azm, elv, xyz_ref = rtkModule(parameters_rtk)
        ret = 0
    else:
        print("No PPP or RTK selected ...")
        ret = 0
        return ret

    if args.plot == True:
        plt_northEast(enu, smode)
        plt_error(t, enu, 1)
        # plt.show()
        plt.show()
        _ = skyplot(azm, elv)
        # plt_NorthEastUp(t,enu,ztd,smode)
        
        cdf_horizontal_error([enu], ['solution'])
        histogram_horizontal_error([enu], ['solution'])
        horizontal_error_over_time([enu], ['solution'])
        # trajectory_plot([enu], ['solution']) # NOTE: no me gusta mucho, quizas un refactor o no utilizarlo
        scatter_plot_reference_center([enu], ['solution'])
    
    if args.kml == True:
        if name or (args.getdata and args.ppp): 
            createKML(sol_, name) 
        else:
            createKML(sol_, name = "solution")

        # TODO: issues with long processing time
        show_kml(sol_)

    return ret

def main():
    args = parse_arguments()

    if args.printhelp:
        print_help()
    else:
        ret = process_input(args)
        if ret != 0:
            print("Main returned error ...")

if __name__ == '__main__':
    main()