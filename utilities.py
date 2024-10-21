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

    for d in range(maxdepth+1):

        checkdir = '/'.join(d*['..']) if d  else '.'

        if 'QETpy' in _os.listdir(checkdir):
            _sys.path.append(checkdir + '/QETpy')
        
        if 'QETpy' in _os.listdir(checkdir):
            _sys.path.append(checkdir + '/optimal_filter')


def find_folder(folder, *candidates):
    """
    function to find path with given name in list of candidate paths

    returns candidate where folder was successfully found, i.e., '{candidate}/{folder}' exists (if folder exists in more than one of the candidates, the first one will be returned)
    """

    for candidate in candidates:
        if _os.path.isdir(candidate) and folder in _os.listdir(candidate):
            return folder

