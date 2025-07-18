"""
utilities - module for miscellaneous utilities

contains:

find_imports() - find locations of QETpy and optimal_filter directories

find_folder() - searches list of candidates for folder with given name

to_ADC() - convert from picoscope-measured voltage to ADC current (current through TES line)

pico_to_ibias() - convert from picoscope-measured voltage to bias current

func_to_ibias() - convert from function generator display voltage to bias current

get_Rp() - return total resistance along SQUID line given bias current, TES current, and shunt resistance

get_Rn() - return normal-state resistance along SQUID line given bias current, shunt resistance, and TES line current in SC and normal states

"""

import os as _os
import sys as _sys


def find_imports(maxdepth = 2):
    """
    function to find folders named "QETpy" and "optimal_filter" in parent folders (or in the Documents folder, if Documents is found in a parent folder)
    """
    qp_found = False
    of_found = False

    def _get_stuff(checkdir):
        if 'QETpy' in _os.listdir(checkdir):
            _sys.path.append(checkdir + '/QETpy')
            qp_found = True        
        if 'optimal_filter' in _os.listdir(checkdir):
            _sys.path.append(checkdir + '/optimal_filter')
            of_found = True

    for d in range(maxdepth+1):

        if qp_found and of_found:
            return

        checkdir = '/'.join(d*['..']) if d  else '.'

        _get_stuff(checkdir)

        if 'Documents' in _os.listdir(checkdir):
            checkdir += '/Documents'
            _get_stuff(checkdir)



def find_folder(folder, *candidates):
    """
    function to find path with given name in list of candidate paths

    returns candidate where folder was successfully found, i.e., '{candidate}/{folder}' exists (if folder exists in more than one of the candidates, the first one will be returned)
    """

    for candidate in candidates:
        if _os.path.isdir(candidate) and folder in _os.listdir(candidate):
            return candidate




def to_ADC(x, config = None):
    """
    function to return ADC current from x, the input voltage read by picoscope

    optional argument 'config' should have config['gain'] equal to the SQUID gain (default: 50)

    function assumes 10x SQUID pickup gain and feedback resistance of 1.2 kOhm

    function has been confirmed to within a factor of ~2 with 0.5-ohm calibration device (measured 0.7 ohm) - see RpRn.ipynb
    """
    if config and 'gain' in config:
        Gdigital = config['gain']
    else:
        Gdigital = 50
    Gsquid = 10 # squid gain (10 loops)
    Rfdbck = 1.2e3 # feedback resistor
    return x/(Rfdbck*Gsquid*Gdigital)


def pico_to_ibias(x, n = 4):
    """
    function to return bias current based on voltage measured by picoscope directly wired to output

    function assumes 1 kOhm resistance along each channel and 50-Ohm terminated source

    inputs:
        x - Vpp displayed in picoscope
        n - number of channels connected when measuring
    """
    return x/(n*50 + 1e3)


def func_to_ibias(x, n = 4):
    """
    function to return bias current based on voltage displayed on function generator

    function assumes 1 kOhm resistance along each channel and 50-Ohm terminated source

    inputs:
        x - Vpp displayed in function generator
        n - number of channels connected when measuring
    """
    return 2*x/(n*50 + 1e3)



def get_Rp(Ib, I_super, Rs = 20e-3):
    """
    return parasitic resistance from bias current Ib, superconducting current I_super, with shunt resistor Rs (default 20 mOhm)
    """
    return Rs*(Ib/I_super - 1 )

def get_Rn(Ib, I_super, I_normal, Rs = 20e-3):
    """
    return normal resistance from bias current Ib, superconducting current I_super, with shunt resistor Rs (default 20 mOhm)
    """
    Rp = get_Rp(Ib, I_super, Rs)
    return Rs*(Ib/I_normal - 1 ) - Rp
