# ibis_data.py - module for ibis_data class to hold data for ibis sweep (from picoscope .mat files)

import numpy as np
import scipy.io as io
import pandas as pd
import os


class ibis_data:

    def __init__(self, fbase, data_dir = './ibis_data/'):

        self.config_file = f'{data_dir}/{fbase}_config.txt'
        self.trace_file = f'{data_dir}/{fbase}.mat'
        
        if os.path.isfile(self.trace_file):

            self.traces = io.loadmat(self.trace_file)

            if os.path.isfile(self.config_file):

                self.config = pd.read_csv(self.config_file, index_col = 0, header = None).to_dict()[1]
            
            else:
                raise Exception(f'No config file for {self.traces_file}')

            self.freq = self.config['freq'] # Hz
            self.offset = self.config['offset'] # V
            self.amp = self.config['amp'] # V
            self.rsh = self.config['rsh'] # 


            self.N = self.traces['Length'][0,0]

            self.dt = self.traces['Tinterval'][0,0]
            self.fs = 1/self.dt
            self.ts = self.traces['Tstart'][0,0] + np.linspace(0, (self.N+1)*self.dt, self.N)

        else:
            raise Exception(f'could not find files {self.config_file} and {self.trace_file}')


    def __call__(self, chan):
        if chan in 'ABCDH':
            return self.convert_ADC(self.traces[chan][:,0])
        else:
            raise Exception(f'No channel {chan}')

    def convert_ADC(self, V): 
        # return amps from volts 

        Rb = 1.2e3
        g_squid = 10
        g_digital = 50
        g_other = 2

        return V/(Rb*g_squid*g_digital*g_other)
