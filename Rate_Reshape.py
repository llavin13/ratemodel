# -*- coding: utf-8 -*-
"""
Created on Tue Jun 19 07:58:36 2018

@author: llavi
"""

import os
from os.path import join
import pandas as pd
import numpy as np
import time
import ast

start_time = time.time()
cwd = os.getcwd()
base_path = cwd 
data_path = join(cwd, 'data')
rates_path = join(data_path, 'Raw_OpenEI_Rate_Data.csv')



def rate_reshape(year, rateid, rates):
    #### 
    date_str = '1/1/' + str(year)
    start = pd.to_datetime(date_str)
    hourly_periods = 8760
    drange = pd.date_range(start, periods=hourly_periods, freq='H')
    data = list(range(len(drange)))
    output_rate = pd.DataFrame(drange, index=data)
    output_rate.columns = ["Datetime"]
    
    output_rate['Daytype'] = output_rate.apply(lambda row: row.Datetime.weekday(), axis=1)
    output_rate['Year'] = output_rate.apply(lambda row: row.Datetime.year, axis=1)
    output_rate['Month'] = output_rate.apply(lambda row: row.Datetime.month, axis=1)
    output_rate['Hour'] = output_rate.apply(lambda row: row.Datetime.hour, axis=1)
    
    #####
    chosen_rate = rates.iloc[rateid,:]
    rate_info = chosen_rate.dropna()
    
    rate_name = rate_info['name'] + ' ' + rate_info['utility']
    output_rate['Rate Name'] = rate_name
    
    
    ### ENERGY ###
    rate_info_list = list(rate_info.index)
    tiers = []
    for x in range(11):
        rate_check = 'energyratestructure/period0/tier' + str(x) + 'rate'
        if rate_check in rate_info_list:
            tiers.append(x)
            Energy_Rate = 'Energy_Tier' + str(x)
            Energy_Adj = 'Energy_Adj' + str(x)
            Energy_Period = 'Energy_Period' + str(x)
            Energy_Max = 'Energy_Max' + str(x)
            output_rate[Energy_Rate] = ''
            output_rate[Energy_Adj] = ''
            output_rate[Energy_Period] = ''
            output_rate[Energy_Max] = ''
            
    ### DEMAND AND CUSTOMER
    output_rate['Demand_Monthly'] = ''
    output_rate['Demand_Monthly_Adj'] = ''
    output_rate['Demand_Daily'] = ''
    output_rate['Demand_Daily_Period'] = ''
    output_rate['Customer'] = rate_info['fixedchargefirstmeter']
    
    month_demand = True
    day_demand = True
    
    tmp_weekday = ast.literal_eval(rate_info['energyweekdayschedule'])
    tmp_weekend = ast.literal_eval(rate_info['energyweekendschedule'])
    
    try:
        demand_charge_mo = [rate_info['flatdemandmonth1'], rate_info['flatdemandmonth2'], rate_info['flatdemandmonth3'],
                       rate_info['flatdemandmonth4'], rate_info['flatdemandmonth5'], rate_info['flatdemandmonth6'],
                       rate_info['flatdemandmonth7'], rate_info['flatdemandmonth8'], rate_info['flatdemandmonth9'], 
                       rate_info['flatdemandmonth10'], rate_info['flatdemandmonth11'], rate_info['flatdemandmonth12']]
    except KeyError:
        month_demand = False
        pass
    
    try:
        rate_info['demandweekdayschedule'] = rate_info['demandweekdayschedule'].replace('L','')
        dmnd_weekday = ast.literal_eval(rate_info['demandweekdayschedule'])
        rate_info['demandweekendschedule'] = rate_info['demandweekendschedule'].replace('L','')
        dmnd_weekend = ast.literal_eval(rate_info['demandweekendschedule'])
    
    except KeyError:
        day_demand = False
        pass    
    
    for i in range(len(output_rate.index)):
        if output_rate.loc[i,'Daytype'] == 5 or output_rate.loc[i,'Daytype'] == 6:
            for x in tiers:
                Energy_Rate = 'Energy_Tier' + str(x)
                Energy_Period = 'Energy_Period' + str(x)
                output_rate.loc[i,Energy_Rate] = tmp_weekend[output_rate.loc[i,'Month']-1][output_rate.loc[i,'Hour']]
                output_rate.loc[i,Energy_Period] = tmp_weekend[output_rate.loc[i,'Month']-1][output_rate.loc[i,'Hour']]
            if day_demand == True:
                output_rate.loc[i,'Demand_Daily'] = dmnd_weekend[output_rate.loc[i,'Month']-1][output_rate.loc[i,'Hour']]
                output_rate.loc[i,'Demand_Daily_Period'] = dmnd_weekend[output_rate.loc[i,'Month']-1][output_rate.loc[i,'Hour']]
        else:
            for x in tiers:
                Energy_Rate = 'Energy_Tier' + str(x)
                Energy_Period = 'Energy_Period' + str(x)
                output_rate.loc[i,Energy_Rate] = tmp_weekday[output_rate.loc[i,'Month']-1][output_rate.loc[i,'Hour']]
                output_rate.loc[i,Energy_Period] = tmp_weekday[output_rate.loc[i,'Month']-1][output_rate.loc[i,'Hour']]
            if day_demand == True:
                output_rate.loc[i,'Demand_Daily'] = dmnd_weekday[output_rate.loc[i,'Month']-1][output_rate.loc[i,'Hour']]
                output_rate.loc[i,'Demand_Daily_Period'] = dmnd_weekday[output_rate.loc[i,'Month']-1][output_rate.loc[i,'Hour']]
                
        for x in tiers:
            Energy_Rate = 'Energy_Tier' + str(x)
            output_rate.loc[i,Energy_Rate] = 'energyratestructure/period' + str(output_rate.loc[i,Energy_Rate]) + '/tier' + str(x) + 'rate' 
            output_rate.loc[i,Energy_Rate] = rate_info[output_rate.loc[i,Energy_Rate]]
        
        try:
            for x in tiers:
                Energy_Max = 'Energy_Max' + str(x)
                Energy_Period = 'Energy_Period' + str(x)
                output_rate.loc[i,Energy_Max] = 'energyratestructure/period' + str(output_rate.loc[i,Energy_Period]) + '/tier' + str(x) + 'max'
                output_rate.loc[i,Energy_Max] = rate_info[output_rate.loc[i,Energy_Max]]
        except KeyError:
            output_rate.loc[i,Energy_Max] = ''
            pass
        
        try:
            for x in tiers:
                Energy_Adj = 'Energy_Adj' + str(x)
                Energy_Period = 'Energy_Period' + str(x)
                output_rate.loc[i,Energy_Adj] = 'energyratestructure/period' + str(output_rate.loc[i,Energy_Period]) + '/tier' + str(x) + 'adj'
                output_rate.loc[i,Energy_Adj] = rate_info[output_rate.loc[i,Energy_Adj]]
        except KeyError:
            output_rate.loc[i,Energy_Adj] = ''
            pass
        
        if day_demand == True:
            output_rate.loc[i,'Demand_Daily'] = 'demandratestructure/period' + str(output_rate.loc[i,'Demand_Daily']) + '/tier0rate' 
            output_rate.loc[i,'Demand_Daily'] = rate_info[output_rate.loc[i,'Demand_Daily']]
        
        if month_demand == True:
            output_rate.loc[i,'Demand_Monthly'] = int(demand_charge_mo[output_rate.loc[i,'Month']-1])
            output_rate.loc[i,'Demand_Monthly'] = 'flatdemandstructure/period' + str(output_rate.loc[i,'Demand_Monthly']) + '/tier0rate' 
            output_rate.loc[i,'Demand_Monthly'] = rate_info[output_rate.loc[i,'Demand_Monthly']]
            try:
                output_rate.loc[i,'Demand_Monthly_Adj'] = int(demand_charge_mo[output_rate.loc[i,'Month']-1])
                output_rate.loc[i,'Demand_Monthly_Adj'] = 'flatdemandstructure/period' + str(output_rate.loc[i,'Demand_Monthly_Adj']) + '/tier0adj' 
                output_rate.loc[i,'Demand_Monthly_Adj'] = rate_info[output_rate.loc[i,'Demand_Monthly_Adj']]
            except KeyError:
                pass
    return output_rate



# inputs for test case
input_year = 2016
input_rateid = 32532

### RUN YOUR TEST CASE ###
# check if it's already been pickled/saved, if not, go find it
case_id = '.pickled_rate_id_' + str(input_rateid)
try:
    case_path = join(cwd, 'pickled_ratereshape')
    os.chdir(case_path)
    output_rate_test = pd.read_pickle(case_id)
except FileNotFoundError:
    os.chdir(base_path)
    # load the rates csv
    rates = pd.read_csv(rates_path)
    output_rate_test = rate_reshape(input_year, input_rateid, rates)
    
    case_path = join(cwd, 'pickled_ratereshape')
    os.chdir(case_path)
    output_rate_test.to_pickle(case_id)

# now output to the test csv
os.chdir(base_path)
output_rate_test.to_csv('test_ratereshape.csv')

### RETURN TIME ###
end_time = time.time() - start_time
print ("time elapsed during run is " + str(end_time) + " seconds")