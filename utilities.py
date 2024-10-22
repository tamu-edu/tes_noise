"""
utilities - module for miscellaneous utilities

contains:

find_imports() - find locations of QETpy and optimal_filter directories

find_folder() - searches list of candidates for folder with given name

"""

import os as _os
import sys as _sys


def find_imports(maxdepth = 2):
    """
    function to find folders named "QETpy" and "optimal_filter" in 
    """
    qp_found = False
    of_found = False

    def _get_stuff(checkdir):
        if 'QETpy' in _os.listdir(checkdir):
            _sys.path.append(checkdir + '/QETpy')
            qp_found = True        
        if 'QETpy' in _os.listdir(checkdir):
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
    if config and 'gain' in config:
        Gdigital = config['gain']
    else:
        Gdigital = 50
    Gsquid = 10 # squid gain (10 loops)
    Rfdbck = 1.2e3 # feedback resistor
    return x/(Rfdbck*Gsquid*Gdigital)

def to_ibias(x):
    return x/1.2e3
