# PicoscopeData - read in csv data from picoscope

import numpy as np
import pandas as pd
import os


class PicoscopeData: 

    def __init__(self, fbase, data_dir, idx = None, shift_times = True):
        """
        shift_time - if True, add shifts to portions of 'Time' column so that column is monotonically increasing
        """


        # read configuration info
        self.config_file = f'{data_dir}/{fbase}_config.txt'

        if os.path.isfile(self.config_file):
            self.config = pd.read_csv(self.config_file, index_col = 0, header = None).to_dict()[1]
        else:
            raise Exception(f'No config file for {self.traces_file}')

        # read trace file(s)
        if idx is None:
            self.trace_file = f'{data_dir}/{fbase}.csv'
        elif hasattr(idx, '__iter__'):
            self.trace_file = lambda i: f'{data_dir}/{fbase}_{i}.csv'

            try:

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
        if 'Time' in self.traces_df.keys():
            self.ts = self.traces_df['Time'].values/1e3 # seconds

            if shift_times:

                backward_jumps = np.where(np.diff(self.ts) < 0)[0][::-1]

                for j in backward_jumps:
                    self.ts[j+1:] += self.ts[j]




    def __call__(self, chan):
        chan_name = f'Channel {chan}'
        if chan_name in self.traces_df.keys():
            return self.traces_df[chan_name].values
        else:
            raise Exception(f'No channel {chan}')


