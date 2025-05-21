# PicoscopeData - read in csv data from picoscope

import numpy as np
import pandas as pd
import os
import glob
from utilities import to_ADC

x_left = [2500 + i * 10_000 for i in range(10)]
x_right = [7500 + i * 10_000 for i in range(10)]

def good_trace(trace, chan):
    sa = trace[2500]
    sb = trace[7500]
    s1, s2 = sorted((sa, sb))
    p2 = trace[:7500].max()
    p1 = trace[:7500].min()

    SA = trace[x_left]
    SB = trace[x_right]

    DSB = np.mean(np.abs(SB - SA))
    DSstd = np.std(SB - SA)

    slope_left = np.polyfit(x_left, SA, 1)[0]
    slope_right = np.polyfit(x_right, SB, 1)[0]

    boolean = {
        "A": (s2 - s1 > 0.55) and (abs(slope_right) < 2.5e-6),
        "B": (s2 - s1 < 3) and (abs(s1+s2)/2 < 0.1) and (abs(slope_right) < 2e-6),
        "C": (s2 - s1 > 0.25) and (abs(slope_right) < 2.5e-6),
        "D": (s2 - s1 > 2.5) and (abs(slope_right) < 5e-6)
    }

    return boolean[chan]

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


    def __init__(self, fbase, data_dir, idx = None, shift_times = True, vertical_stack = False, glob_pattern = None, row_avg = 0, throw_nans = False):
        """
        shift_time - if True, add shifts to portions of 'Time' column so that column is monotonically increasing

        vertical_stack: stack data into (nfiles x nsamples arrays in self.arrs)

        row_avg: if vstack, average rows in bundles of row_avg 
        """

        self.vstack = vertical_stack
        self.channels = None
        self.row_avg = row_avg

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

            if os.path.isfile(self.trace_file):

                self.traces_df = pd.read_csv(self.trace_file, skiprows = (1,2), na_values = ["∞", "-∞"])

                self.__get_channels__(self.traces_df)

            else:
                raise Exception(f'could not find {self.trace_file}')

                
        elif hasattr(idx, '__iter__'):
            if glob_pattern:
                files = glob.glob(glob_pattern)
                self.trace_file = lambda i: files[i]
                print('collecting', len(files), 'files with glob')
            else:
                self.trace_file = lambda i: f'{data_dir}/{fbase}_' + str(i).rjust(int(np.ceil(np.log10(len(idx)))), '0') + '.csv'

            self.conv = PicoscopeData.__get_conv__(self.trace_file(list(idx)[0]))

            try:

                if throw_nans:

                    df = pd.read_csv(self.trace_file(idx[0]), skiprows = (1,2), na_values = ["∞", "-∞"]) 
                    self.ts = df['Time'].values/1e3 # seconds
                    self.__get_channels__(df)

                    self.arrs = {chan: [] for chan in self.channels}

                    self.arrs['H'] = df['Channel H'].values

                    thisrow = {chan: self.row_avg for chan in self.channels}

                    for i, ix in enumerate(idx):

                        df = pd.read_csv(self.trace_file(ix), skiprows = (1,2), na_values = ["∞", "-∞"])                        
                    

                        for chan in self.channels:
                            if thisrow[chan] == self.row_avg and chan != 'H':
                                self.arrs[chan].append(np.zeros(len(df)))
                                thisrow[chan] = 0

                        for chan in self.channels:

                            trace = df[f'Channel {chan}'].values
                            if (chan != 'H') and (not any(np.isnan(trace))) and good_trace(trace, chan):
                                self.arrs[chan][-1] += trace
                                thisrow[chan] += 1

                    for chan in self.channels:
                        if chan != 'H':
                            if thisrow[chan] < self.row_avg:
                                self.arrs[chan].pop(-1)

                            self.arrs[chan] = to_ADC(np.array(self.arrs[chan])/self.row_avg, self.config)


                else:

                    if self.vstack:

                        self.arrs = {}

                        for i, ix in enumerate(idx):
                            
                            df = pd.read_csv(self.trace_file(ix), skiprows = (1,2), na_values = ["∞", "-∞"])

                            if i == 0:
                                self.ts = df['Time'].values/1e3 # seconds
                                self.__get_channels__(df)

                            for chan in self.channels:

                                if chan not in self.arrs:
                                    if self.row_avg < 1:
                                        self.arrs[chan] = np.zeros((len(idx), len(df)))
                                        self.rownum = 1
                                    else:
                                        self.rownum = int(len(idx)//row_avg)
                                        self.arrs[chan] = np.zeros((self.rownum, len(df)))
                                
                                if i//self.row_avg < self.rownum:
                                    trace = df[f'Channel {chan}'].values/self.row_avg
                                    nans = np.isnan(trace)

                                    self.arrs[chan][i//self.row_avg][~nans] += trace[~nans]

                    else:

                        self.traces_df = pd.concat([pd.read_csv(self.trace_file(i), skiprows = (1,2)) for i in idx])

                        self.__get_channels__(self.traces_df)


            except Exception as e:
                raise Exception(f'Tried to do list-like PicoscopeData initialization. Raised {e}')
        else:
            self.trace_file = f'{data_dir}/{fbase}_{idx}.csv'

            self.conv = PicoscopeData.__get_conv__(self.trace_file)
            
            if os.path.isfile(self.trace_file):

                self.traces_df = pd.read_csv(self.trace_file, skiprows = (1,2))
                self.__get_channels__(self.traces_df)

            else:
                raise Exception(f'could not find {self.trace_file}')


        # take out time array
        if not self.vstack and 'Time' in self.traces_df.keys():
            self.ts = self.traces_df['Time'].values/1e3 # seconds

            if shift_times:

                backward_jumps = np.where(np.diff(self.ts) < 0)[0][::-1]

                for j in backward_jumps:
                    self.ts[j+1:] += self.ts[j]

        try:
            self.N = len(self.ts)

        except: 
            pass

        if self.vstack:
            for chan in self.arrs:
                try:
                    self.arrs[chan] *= self.conv[chan]
                except KeyError: # chan not in self.conv
                    pass
                except Exception as e:
                    print(self.conv)
                    raise Exception(e)

        print(f'Created new PicoscopeData object with {self.N} data points\nChannels: {self.channels}')


    def __call__(self, chan):
        if self.vstack:
            return self.arrs[chan]
        else:
            chan_name = f'Channel {chan}'
            if chan_name in self.traces_df.keys():
                return self.conv[chan]*self.traces_df[chan_name].values
            else:
                raise Exception(f'No channel {chan}')

    def __get_channels__(self, df):
        self.channels = []
        for key in df.keys():
            if 'Channel' in key:
                x = key.split()[1]
                if key == f'Channel {x}':
                    self.channels.append(x)

    def resize(self, start, stop, step = 1):
        """
        resize data arrays, i.e., by array[start:stop:step]
        """
        keep = slice(start,stop,step)
        if self.vstack:
            for k in self.arrs:
                self.arrs[k] = self.arrs[k][keep]
            self.ts = self.ts[keep]
            self.N = self.ts.size
        else:
            self.traces_df = self.traces_df[keep]
            self.ts = self.traces_df['Time'].values/1e3
            self.N = self.ts.size


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





