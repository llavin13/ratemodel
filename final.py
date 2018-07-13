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
from Bill_Calculator import demand_bill_month_calc

## RAW DATA & FILE STRUCTURE ##
cwd = os.getcwd()
base_path = cwd 
data_path = join(cwd, 'data')
rates_path = join(data_path, 'Raw_OpenEI_Rate_Data.csv')
rates = pd.read_csv(rates_path)

## READ IN CASE INPUTS FOR RUNNING SCRIPT ##
case_path = join(data_path, 'case_input.csv')
cases = pd.read_csv(case_path)
#print (cases)

## CREATE LOOP ##
#use for running multiple cases, be careful
full_list = []
for caseno in range(len(cases)):
#PG&E ids include: 8978, 12896, 28446, 35604, 35673, 39055, 39056, 39058, 39059, 39075, 39954
#39975, 41327, 41385, 42036
#SCE includes: 38161, 38168, 38171, 38172, 38175, 38178, 38180, 38182, 38184, 38185, 38186, 38187, 38188, 38192
#38194, 38196, 38197, 38200, 38202, 38204, 38219, 38230, 38231, 38232, 38235, 38241, 38243, 38245
# looks like Mike used 38232 for his work
#BG&E 1810, 12989, 15002, 15975, 23872, 35882, 43110
#Duke 29363, 38393 sm, 38394 lg
#Austin
#PECO 38915, 38917, 38926, 38930
#Georgia Power
#OG&E
#ConEd 6325, 21926, 35730, 35735, 35747, 39088, 39089, 39091, 39092, 39093, 39094, 39096
#39110, 39111, 39113, 39114, 39116, 39117, 39118, 39120, 39265, 42021
#DQL 13525, 34129, 35878
    ## Tell user what you're running ##
    print ("running case for rateid " + str(cases['rateid'][caseno]))

    ## LOAD ##
    #load = Load_Script.losangeles_com #native load, wrong for now
    load = eval("Load_Script." + str(cases['loadlocation'][caseno]))
    load_name = cases['loadname'][caseno] #select the column name of your chosen load shape
    #convert to 8760
    loads_2013 = load[load['Year'] == cases['loadyear'][caseno]]
    Lg_Office_2013 = loads_2013[[load_name]]
    Lg_Office_2013_8760 = Lg_Office_2013.groupby(np.arange(len(Lg_Office_2013))//2).mean()
    
    ## CASE INPUTS ##
    input_year = cases['rateyear'][caseno]
    input_peak_kW = Lg_Office_2013_8760.max()
    input_utility = "Pacific Gas & Electric Co" # not used unless you check rate options
    input_sector = "Commercial" # not used unless you check rate options
    input_voltage = "Transmission"
    input_rateid = cases['rateid'][caseno]
    CZ_sheet = cases['CZ_Sheet'][caseno]
    input_CZ = cases['input_CZ'][caseno] #3A is SF, 6 and 8 are LA
    CZ_year = float(cases['CZ_year'][caseno]) #this is a problem but leave for now
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
    xls_path = join(data_path, CZ_sheet)
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
    native_demand_2 = demand_bill_month_calc(full_df, load_name)
    
    net_energy = energy_bill_calc(full_df, "NetLoad")
    net_customer = customer_bill_calc(full_df, "NetLoad")
    net_demand = demand_bill_calc(full_df, "NetLoad")
    net_demand_2 = demand_bill_month_calc(full_df, "NetLoad")
    
    ## GRAPHS/OUTPUTS ##
    
    # create and format monthly data for plotting
    months_str = ['January','February','March','April','May','June','July','August','September','October','November','December']
    months_str_short = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec']
    energy_delta = -np.array(net_energy) + np.array(native_energy)
    energy_delta = list(energy_delta)
    
    # convert daily demand period charges into single monthly values
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
        
    # for full delta add in the flat monthly demand charges
    demand_delta = -np.array(net_demand_monthly) + np.array(native_demand_monthly) - np.array(net_demand_2) + np.array(native_demand_2)
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
    
    #full_df.to_csv('case_results.csv')
    full_list.append(full_df)
    #writer = pd.ExcelWriter('Storage_case.xlsx')
    #full_df.to_excel(writer,'data_output')
    #writer.save()
all_case_results_df = pd.concat(full_list)
all_case_results_df.to_csv('all_case_results.csv')
end_time = time.time() - start_time
print ("time elapsed during run is " + str(end_time) + " seconds")
