# PicoscopeData - read in csv data from picoscope

import numpy as np
import pandas as pd
import os


class PicoscopeData: 

    @staticmethod
    def __get_conv__(filename):
        # conversions to V
        with open(filename, 'r') as f:
            for i, l in enumerate(f):
                if i ==0:
                    header = l.split(',')
                    
                elif i == 1:
                    units = [s.strip().strip('(').strip(')').strip() for s in l.split(',')]
                    break

        channels = [c.split()[1][0] if 'Channel' in c else '' for c in header]

        conv = {c: (1. if u == 'V' else 1e-3 if u == 'mV' else 0.) for c, u in zip(channels, units)}
        return conv     


    def __init__(self, fbase, data_dir, idx = None, shift_times = True, vertical_stack = False):
        """
        shift_time - if True, add shifts to portions of 'Time' column so that column is monotonically increasing

        vertical_stack: stack data into (nfiles x nsamples arrays in self.arrs)
        """

        self.vstack = vertical_stack

        # read configuration info
        self.config_file = f'{data_dir}/{fbase}_config.txt'

        if os.path.isfile(self.config_file):
            self.config = pd.read_csv(self.config_file, index_col = 0, header = None).to_dict()[1]
        else:
            raise Exception(f'No config file for {self.config_file}')

        # read trace file(s)
        if idx is None:
            self.trace_file = f'{data_dir}/{fbase}.csv'

            self.conv = PicoscopeData.__get_conv__(self.trace_file)

                
        elif hasattr(idx, '__iter__'):
            self.trace_file = lambda i: f'{data_dir}/{fbase}_' + str(i).rjust(int(np.ceil(np.log10(len(idx)))), '0') + '.csv'

            self.conv = PicoscopeData.__get_conv__(self.trace_file(list(idx)[0]))

            try:

                if self.vstack:

                    self.arrs = {}

                    for i, ix in enumerate(idx):

                        df = pd.read_csv(self.trace_file(ix), skiprows = (1,2))

                        if i == 0:
                            self.ts = df['Time'].values/1e3 # seconds

                        for chan in 'ABCDH':

                            if chan not in self.arrs:
                                self.arrs[chan] = np.zeros((len(idx), len(df)))
                            
                            self.arrs[chan][i,:] = df[f'Channel {chan}'].values
                            


                else:

                    self.traces_df = pd.concat([pd.read_csv(self.trace_file(i), skiprows = (1,2)) for i in idx])


            except Exception as e:
                raise Exception(f'Tried to do list-like PicoscopeData initialization. Raised {e}')
        else:
            self.trace_file = f'{data_dir}/{fbase}_{idx}.csv'
            
            if os.path.isfile(self.trace_file):

                self.traces_df = pd.read_csv(self.trace_file, skiprows = (1,2))

            else:
                raise Exception(f'could not find {self.trace_file}')


        # take out time array
        if not self.vstack and 'Time' in self.traces_df.keys():
            self.ts = self.traces_df['Time'].values/1e3 # seconds

            if shift_times:

                backward_jumps = np.where(np.diff(self.ts) < 0)[0][::-1]

                for j in backward_jumps:
                    self.ts[j+1:] += self.ts[j]


    def __call__(self, chan):
        if self.vstack:
            return self.conv[chan]*self.arrs[chan]
        else:
            chan_name = f'Channel {chan}'
            if chan_name in self.traces_df.keys():
                return self.conv[chan]*self.traces_df[chan_name].values
            else:
                raise Exception(f'No channel {chan}')


# signal conversion notes
# 
# picoscope measures voltage
# 
# channel H - signal gen to picoscope
# signal gen generates waveform of specified voltage
# chanH = measured voltage through picoscope hooked directly up to second line of picoscope
# chanH = 2Vps (2.017Vps + 5.36)
# then Ibias = chanH/1.2 kOhm (four 1kOhm in parallel + 50Ohm termination times factor of two)
# 
# channel ABCD - output from SQUIDs
# we don't know what is happening
# we measured a 200 mVpp signal in the picoscope with a 408 mVpp amplitude
# voltage through picoscope = I_TES x 1.2kOhm x 10 (SQUID gain) x 50 (digital gain) x 2 (?)
# so current through TES line with some gain & polarity
# = chan(ABCD)/(1.2e3*10*50*2)





