# -*- coding: utf-8 -*-
"""
Created on Wed Jun 13 19:56:00 2018

@author: llavi
"""

import os
from os.path import join
import pandas as pd
import numpy as np
import time

start_time = time.time()
cwd = os.getcwd()
data_path = join(cwd, 'data')

rates_path = join(data_path, 'Raw_OpenEI_Rate_Data.csv')

# load the rates csv
rates = pd.read_csv(rates_path)

# the inputs
input_year = 2016
input_peak_kW = 51
input_utility = "Georgia Power Co"
input_sector = "Commercial"
input_voltage = "Transmission"

# Pacific Gas & Electric Co / Georgia Power Co / Baltimore Gas & Electric Co / Southern California Edison Co
# Pennsylvania Electric Co (Pennsylvania) / Austin Energy / Duke Energy Carolinas, LLC

def rate_options(rates, year, peak_kW, utility, sector, voltage):
    # for the years
    rates['startdate'].fillna('1/1/2000 0:00', inplace=True)
    start_dates = pd.to_datetime(rates['startdate'])
    rates['startyear'] = pd.DatetimeIndex(start_dates).year

    rates['enddate'].fillna('1/1/2100 0:00', inplace=True)
    end_dates = pd.to_datetime(rates['enddate'])
    rates['endyear'] = pd.DatetimeIndex(end_dates).year

    # for the max/min kW
    rates['peakkwcapacitymin'].fillna(0, inplace=True)
    rates['peakkwcapacitymax'].fillna(1000000000, inplace=True)
    
    # to erase N/A's for voltage
    rates['voltagecategory'].fillna('None', inplace=True)

    rate_options = rates[(rates['utility'] == utility) &
          (rates['sector'] == sector) & (rates['startyear'] <= year)
          & (rates['endyear'] >= year) & (rates['peakkwcapacitymin'] <= peak_kW) 
          & (rates['peakkwcapacitymax'] >= peak_kW)
          & (pd.isnull(rates['energyratestructure/period0/tier0rate'])==False)
          & (rates['name'].str.contains('Agricultur')==False)
          & (rates['name'].str.contains('AGRICULTUR')==False)
          & (rates['voltagecategory'].isin([voltage, 'None']))]
    
    return (rate_options)

test_output = rate_options(rates, input_year, input_peak_kW, input_utility, input_sector, input_voltage)
#print(test_output)
# write this to a csv you can check, just for now
test_output.to_csv('test.csv')

end_time = time.time() - start_time
print ("time elapsed during run is " + str(end_time) + " seconds")