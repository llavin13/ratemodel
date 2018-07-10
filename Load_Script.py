# -*- coding: utf-8 -*-
"""
Created on Tue Jun 19 08:17:02 2018

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
#print(time.time() - start_time)

Baltimore = True
SF = True
LA = True
Houston = True
Fisher_data = True


# pickled data check before you run other code
try:
    baltimore_com = pd.read_pickle(".baltimore_com")
except FileNotFoundError:
    Baltimore = False
    
try:
    sanfrancisco_com = pd.read_pickle(".sanfrancisco_com")
except FileNotFoundError:
    SF = False
    
try:
    losangeles_com = pd.read_pickle(".losangeles_com")
except FileNotFoundError:
    LA = False
    
try:
    houston_com = pd.read_pickle(".houston_com")
except FileNotFoundError:
    Houston = False
    
try:
    final_Fisher_data = pd.read_pickle(".Fisher_data")
except FileNotFoundError:
    Fisher_data = False
    
##### DOE COMMERCIAL BUILDING DATA #####

#Baltimore
if Baltimore == False:
    baltimore_path = join(data_path, 'baltimorecom.csv')
    baltimore_com = pd.read_csv(baltimore_path)
    baltimore_com.to_pickle(".baltimore_com")

#SF
if SF == False:
    sanfrancisco_path = join(data_path, 'sanfranciscocom.csv')
    sanfrancisco_com = pd.read_csv(sanfrancisco_path)
    sanfrancisco_com.to_pickle(".sanfrancisco_com")

#LA
if LA == False:
    losangeles_path = join(data_path, 'losangelescom.csv')
    losangeles_com = pd.read_csv(losangeles_path)
    losangeles_com.to_pickle(".losangeles_com")

#Houston
if Houston == False:
    houston_path = join(data_path, 'houstoncom.csv')
    houston_com = pd.read_csv(houston_path)
    houston_com.to_pickle(".houston_com")

#print(time.time() - start_time)

#### FISHER DATA #####
if Fisher_data == False:
    months = ['Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec']
    csv_loc_Jan = "Load Data Jan13.csv"
    path_Jan = join(data_path, csv_loc_Jan)
    final_Fisher_data = pd.read_csv(path_Jan) 
    for month in months:
        csv_loc = "Load Data " + str(month) + "13.csv"
        path = join(data_path, csv_loc)
        read_month = pd.read_csv(path) 
        final_Fisher_data = pd.concat([final_Fisher_data, read_month])
    final_Fisher_data.to_pickle(".Fisher_data")
#final_Fisher_data.to_csv('fisher_concat.csv')
#print(time.time() - start_time)
    
##### SOCORE DATA #####
csv_SoCore = "SoCore_LoadData.csv"
path_SoCore = join(data_path, csv_SoCore)
SoCore_df = pd.read_csv(path_SoCore) 
#print(SoCore_df)

end_time = time.time() - start_time
print ("time elapsed during run is " + str(end_time) + " seconds")