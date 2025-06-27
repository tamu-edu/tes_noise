# PicoscopeData - read in csv data from picoscope

import numpy as np
import pandas as pd
import os
import glob
from utilities import to_ADC, pico_to_ibias

x_left = [2500 + i * 10_000 for i in range(10)]
x_right = [7500 + i * 10_000 for i in range(10)]

def good_trace(trace, chan):
    if 1:
        return True
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
    """
    class to read .csv files output by picoscope

    NOTE: requires config file at "{data_dir}/{fbase}_config.txt"

    NOTE: assumes all data files have the same shape (number of channels/number of data points) and units

    NOTE: assumes sigchan (signal generator) signal has integer multiple frequency of sampling frequency

    constructor arguments:
        fbase: string present in base of all filenames (i.e., runnum)
        data_dir: innermost directory containing all data files
        glob_pattern (optional): pattern for glob to find all data files (default: {data_dir}*{fbase}*.csv)
        row_avg (int, optional): average rows in bundles of row_avg (default 1, no averaging)
        sigchan (optional): channel of signal generator input to picoscope (will use utilities.pico_to_ibias instead of utilities.to_ADC) (default 'H') (set sigchan = None to disable)
    
    attributes:
        config_file: file containing configuration info
        config: dictionary of config data kept in self.config_file
        arrs: dictionary of data arrays, indexed by channel name (A-H) [amps] (shape something like (Nfiles//row_avg, N) depending on cuts)
        channels: list of channels (not including sigchan) contained in data arrays
        file_list: list of filenames returned by glob pattern
        row_avg: row averaging (see constructor)
        ts: array of time series data [sec]
        N: number of 
    """

    def __init__(self, fbase, data_dir, glob_pattern = None, row_avg = 0, sigchan = 'H'):
        
        # read configuration info
        self.config_file = f'{data_dir}/{fbase}_config.txt'

        if os.path.isfile(self.config_file):
            self.config = pd.read_csv(self.config_file, index_col = 0, header = None).to_dict()[1]
        else:
            raise Exception(f'No config file for {self.config_file}')

        self.channels = None
        self.file_list = []
        self.sigchan = sigchan
        self.row_avg = max((row_avg, 1))

        # collect files
        if glob_pattern is None:
            glob_pattern = data_dir + '*' + fbase + '*.csv'

        self.glob_pattern = glob_pattern
                
        self.file_list = glob.glob(self.glob_pattern)
        self.Nfiles = len(self.file_list)
        if self.Nfiles:
            print(f'collecting {self.Nfiles} files with glob')
        else:
            raise Exception(f'{self.Nfiles} files found with glob pattern {self.glob_pattern}')

        self.__get_channels__(self.file_list[0])

        # initial dataframe - collect time grid, initialize self.arrs, get signal gen data
        df = self.__get_data__(0)

        t_conv = {'ms': 1e-3}
        self.ts = df['Time'].values*t_conv[self.units[0]] # seconds
        self.N = self.ts.size

        self.arrs = {chan: [] for chan in self.channels}
        if self.sigchan is not None:
            self.arrs[sigchan] = pico_to_ibias(df[f'Channel {sigchan}'].values*self.conv[sigchan])
       
        thisrow = {chan: self.row_avg for chan in self.channels}

        #for i, ix in enumerate(idx):
        for i, file in enumerate(self.file_list):
            df = self.__get_data__(i)

            for chan in self.channels:
                if thisrow[chan] == self.row_avg:
                    self.arrs[chan].append(np.zeros(len(df)))
                    thisrow[chan] = 0

                trace = df[f'Channel {chan}'].values
                if (not any(np.isnan(trace))) and good_trace(trace, chan):
                    self.arrs[chan][-1] += trace
                    thisrow[chan] += 1


        for chan in self.channels:
            if thisrow[chan] < self.row_avg:
                self.arrs[chan].pop(-1)

            self.arrs[chan] = to_ADC(np.array(self.arrs[chan])/self.row_avg, self.config)

        print(f'Created new PicoscopeData object with {self.N} data points\nChannels: {self.channels}')
        # end of PicoscopeData constructor


    def __call__(self, chan):
        if chan in self.arrs.keys():
            return self.arrs[chan]
        else:
            raise Exception(f'no channel "{chan}" in PicoscopeData object. Available channels: {self.channels}')

    
    def __get_data__(self, i):
        if i < self.Nfiles:
            return pd.read_csv(self.file_list[i], skiprows = (1,2), na_values = ["∞", "-∞"]) 
        else:
            raise Exception(f'no file number {i} in PicoscopeData object with {self.Nfiles} files')


    def __get_channels__(self, filename):
        # conversions to V
        # defines self.conv, self.units, and self.channels
        if self.channels is None:
            with open(filename, 'r') as f:
                for i, l in enumerate(f):
                    if i == 0:
                        header = l.split(',')
                        
                    elif i == 1:
                        self.units = [s.strip().strip('(').strip(')').strip() for s in l.split(',')]

                        self.channels = [c.split()[1][0] for c in header if 'Channel' in c]

                        self.conv = {c: (1. if u == 'V' else 1e-3 if u == 'mV' else 0.) for c, u in zip(self.channels, self.units)} 

                        if self.sigchan in self.channels:
                            self.channels.remove(self.sigchan)

                        return 
        else:
            raise Exception('channels already assigned')


    def resize(self, keep):
        """
        resize data arrays, i.e., by array[keep]
        """
        for k in self.arrs:
            self.arrs[k] = self.arrs[k][keep]
        self.ts = self.ts[keep]
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





