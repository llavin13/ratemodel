# -*- coding: utf-8 -*-
"""
Created on Mon Jul  2 13:42:16 2018

@author: llavi
"""

# GENERIC IMPORTS
from __future__ import division
import os
from os.path import join
import pandas as pd
import numpy as np
import time
from pyomo.environ import *

# PLOTTING IMPORTS
import seaborn as sns
from matplotlib import pyplot as plt
sns.set_style("white")

start_time = time.time()

# SCRIPT IMPORTS
import Load_Script
#from Rate_Script import rate_options
from Rate_Reshape import rate_reshape
from Storage_Optimizer import storage_optimizer
from Bill_Calculator import energy_bill_calc
from Bill_Calculator import customer_bill_calc
from Bill_Calculator import demand_bill_calc

## RAW DATA & FILE STRUCTURE ##
cwd = os.getcwd()
base_path = cwd 
data_path = join(cwd, 'data')
rates_path = join(data_path, 'Raw_OpenEI_Rate_Data.csv')
rates = pd.read_csv(rates_path)

## CREATE LOOP ##
#use for running multiple cases, be careful
for rateid in [41327, 41385]:
#PG&E ids include: 8978, 12896, 28446, 35604, 35673, 39055, 39056, 39058, 39059, 39075, 39954
#39975, 41327, 41385, 42036
    print ("running case for rateid " + str(rateid))

    ## LOAD ##
    load = Load_Script.sanfrancisco_com #native
    load_name = "PrimarySchoolNew2004" #select the column name of your chosen load shape
    #convert to 8760
    loads_2013 = load[load['Year'] == 2013]
    Lg_Office_2013 = loads_2013[[load_name]]
    Lg_Office_2013_8760 = Lg_Office_2013.groupby(np.arange(len(Lg_Office_2013))//2).mean()
    
    ## CASE INPUTS ##
    input_year = 2016
    input_peak_kW = Lg_Office_2013_8760.max()
    input_utility = "Pacific Gas & Electric Co"
    input_sector = "Commercial"
    input_voltage = "Transmission"
    input_rateid = rateid #must be kept consistent w prvs inputs 35673, 39059
    input_CZ = 'CZ3A'
    CZ_year = 2018.0
    order_magnitude = 1000
    months = list(range(1, 13))
    
    ## RATES ##
    
    #test_output = rate_options(rates, input_year, input_peak_kW, input_utility, input_sector, input_voltage)
    #print (test_output)
    
    case_id = '.pickled_rate_id_' + str(input_rateid)
    try:
        case_path = join(cwd, 'pickled_ratereshape')
        os.chdir(case_path)
        my_rate = pd.read_pickle(case_id)
    except FileNotFoundError:
        os.chdir(base_path)
        # load the rates csv
        rates = pd.read_csv(rates_path)
        my_rate = rate_reshape(input_year, input_rateid, rates)
        
        case_path = join(cwd, 'pickled_ratereshape')
        os.chdir(case_path)
        my_rate.to_pickle(case_id)
    os.chdir(base_path)
    
    ## STORAGE DISPATCH ##
    
    rate_load_df = pd.concat([my_rate, Lg_Office_2013_8760], axis=1) #gets rate/load combo
    #make empty values 0's, otherwise optimization won't run
    '''
    if (rate_load_df['Demand_Daily'].iloc[0]==""):
        print ("replacing blank demand cost and periods with zeros")
        zeros_list = 2190*[0,1,2,3]
        zeros_pdseries = pd.Series(zeros_list, dtype='int64')
        other = 8760*[0.0]
        other_pdseries = pd.Series(other, dtype='float64')
        rate_load_df['Demand_Daily'] = other_pdseries
        rate_load_df['Demand_Daily_Period'] = zeros_pdseries
    rate_load_df.to_csv('check.csv')
    '''
    # now dispatch the storage below
    storage_output = storage_optimizer(rate_load_df,load_name)
    storage_output = storage_output.reset_index(drop=True) #reindex 
    # then combine important parts of storage with the rates and load
    rate_load_storage_df = pd.concat([rate_load_df, storage_output.iloc[:,4:]], axis=1)
    
    ## AVOIDED COSTS ##
    
    #ok first the format is dumb so make the first column the headers
    xls_path = join(data_path, 'PG&E by CZ_All.xlsx')
    xls = pd.ExcelFile(xls_path)
    CZ_AvoidedCosts = pd.read_excel(xls, input_CZ)
    CZ_AvoidedCosts.columns = CZ_AvoidedCosts.iloc[0]
    # now pull a column and add those avoided costs ($/MWh) to the 8760
    year_string = str(int(CZ_year))
    avoided_costs = CZ_AvoidedCosts.loc[1:8760,CZ_year]
    avoided_costs = avoided_costs.reset_index(drop=True)
    avoided_cost_df = pd.concat([rate_load_storage_df, avoided_costs], axis=1)
    # finally, add a column that has hourly avoided costs (in $)
    hourly_avoided_costs = -np.array(avoided_costs) * np.array(avoided_cost_df["Net_Storage"]) / order_magnitude
    full_df = pd.concat([avoided_cost_df, pd.Series(hourly_avoided_costs)], axis=1)
    # now get list of monthly avoided costs
    monthly_avoided_costs = []
    for m in months:
        month_avoided_costs = full_df[0][(full_df['Month']==m)].sum() #want to rename the column better
        monthly_avoided_costs.append(month_avoided_costs)
    
    ## BILLS ##
    native_energy = energy_bill_calc(full_df, load_name)
    native_customer = customer_bill_calc(full_df, load_name)
    native_demand = demand_bill_calc(full_df, load_name)
    
    net_energy = energy_bill_calc(full_df, "NetLoad")
    net_customer = customer_bill_calc(full_df, "NetLoad")
    net_demand = demand_bill_calc(full_df, "NetLoad")
    
    ## GRAPHS/OUTPUTS ##
    
    # create and format monthly data for plotting
    months_str = ['January','February','March','April','May','June','July','August','September','October','November','December']
    months_str_short = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec']
    energy_delta = -np.array(net_energy) + np.array(native_energy)
    energy_delta = list(energy_delta)
    
    native_demand_monthly = []
    net_demand_monthly = []
    val = len(net_demand)/12
    for m in range(len(months_str)):
        native = 0
        net = 0
        for v in range(int(val)):
            native += native_demand[int(m*val+v)]
            net += net_demand[int(m*val+v)]
        native_demand_monthly.append(native)
        net_demand_monthly.append(net)
    demand_delta = -np.array(net_demand_monthly) + np.array(native_demand_monthly)
    demand_delta = list(demand_delta)
       
    total_delta = np.array(demand_delta) + np.array(energy_delta)
    total_delta = list(total_delta)
        
    # creation of dfs
    bill_results_df = pd.DataFrame(
        {'month': months_str,
         'month short': months_str_short,
         'delta energy bill': energy_delta,
         'native energy bill': native_energy,
         'net energy bill': net_energy,
         'delta demand bill': demand_delta,
         'native demand bill': native_demand_monthly,
         'net demand bill': net_demand_monthly,
         'native customer bill': native_customer,
         'net customer bill': net_customer,
         'avoided costs': monthly_avoided_costs,
         'total delta': total_delta
        })
    
    bill_results_df_small = pd.DataFrame(
        {'month short': months_str_short,
         'avoided costs': monthly_avoided_costs,
         'total delta': total_delta
        })
    
    df1 = pd.melt(bill_results_df_small, id_vars=['month short'])
    
    for i in range(len(months_str)):
        demand_delta.insert(0, 0)
    se = pd.Series(demand_delta)
    df1["delta demand bill"] = se.values
    
    # now finally do the acutal plotting
    palette_choice = "muted"
    #sns.color_palette(palette_choice).as_hex()[0]
    
    #Plot 1 - background - "total" (top) series
    sns.barplot(x = "month short", y = "value", data = df1, hue = 'variable', palette = palette_choice)
    
    #Plot 2 - overlay - "bottom" series
    bottom_plot = sns.barplot(x = "month short", y = "delta demand bill", data = df1, hue = 'variable', color = sns.color_palette(palette_choice).as_hex()[2])
    
    costbar = plt.Rectangle((0,0),1,1,fc=sns.color_palette(palette_choice).as_hex()[0], edgecolor = 'none') 
    topbar = plt.Rectangle((0,0),1,1,fc=sns.color_palette(palette_choice).as_hex()[1], edgecolor = 'none')
    bottombar = plt.Rectangle((0,0),1,1,fc=sns.color_palette(palette_choice).as_hex()[2],  edgecolor = 'none')
    l = plt.legend([costbar, bottombar, topbar], ['Avoided Costs','Demand Bill Savings', 'Energy Bill Savings'], loc=0, ncol = 1, prop={'size':12})
    l.draw_frame(False)
    
    sns.despine(left=True)
    bottom_plot.set_ylabel("Monthly Bill Savings ($)")
    bottom_plot.set_xlabel("Month of Year")
    chart_title = full_df['Rate Name'].iloc[0] + ' ' + input_CZ + ' ' + str(int(CZ_year)) + ' // ' + load_name + ' Load Shape'
    #full_df.iloc[0,'Rate Name'] + ' ' +
    bottom_plot.set_title(chart_title)
    plt.show()
    
    full_df.to_csv('case_results.csv')
    #writer = pd.ExcelWriter('Storage_case.xlsx')
    #full_df.to_excel(writer,'data_output')
    #writer.save()
end_time = time.time() - start_time
print ("time elapsed during run is " + str(end_time) + " seconds")
