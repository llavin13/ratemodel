# -*- coding: utf-8 -*-
"""
Created on Mon Jul  2 09:53:32 2018

@author: llavi
"""
from __future__ import division
import os
from os.path import join
import pandas as pd
import numpy as np
import math
import time
from pyomo.environ import *

start_time = time.time()
cwd = os.getcwd()

### LOAD DATA ###
### Note: will want to change this to call other scripts for input, probs
data_path = join(cwd, 'test_full.csv')
input_data = pd.read_csv(data_path)
#print (input_data.columns.values)
def storage_optimizer(data,name):
    ### CHOOSE CASE ###
    months_of_year = [1,2,3,4,5,6,7,8,9,10,11,12]
    monthly_data = []
    for m in months_of_year:
        Month = m #should be from 1-12
        
        ### DATA INPUTS TO CONCRETE MODEL ###
        year_load = list(data[name])
        hour_load = list(data[name][(data['Month'] == Month)])
        hours = len(hour_load)
        month_list = [Month]*len(hour_load)
        hour_energycost = list(data['Energy_Tier0'][(data['Month'] == Month)])
        hour_demandperiod = list(data['Demand_Daily_Period'][(data['Month'] == Month)])
        time_input = []
        nativeload_input = {}
        energycost_input = {}
        demandperiod_input = {}
        for i in range(hours):
            time_input.append(i)
            nativeload_input[i] = hour_load[i]
            energycost_input[i] = hour_energycost[i]
            demandperiod_input[i] = hour_demandperiod[i]
        if isinstance(data['Demand_Monthly'][0],str):
            demandcost_monthly_input = 0
        else:
            demandcost_monthly_input = data['Demand_Monthly'].mean()
        if math.isnan(data['Demand_Daily'][(data['Demand_Daily_Period'] == 0)].mean()):
            demandcost0_input = 0
        else:
            demandcost0_input = data['Demand_Daily'][(data['Demand_Daily_Period'] == 0)].mean()
        if math.isnan(data['Demand_Daily'][(data['Demand_Daily_Period'] == 1)].mean()):
            demandcost1_input = 0
        else:
            demandcost1_input = data['Demand_Daily'][(data['Demand_Daily_Period'] == 1)].mean()
        if math.isnan(data['Demand_Daily'][(data['Demand_Daily_Period'] == 2)].mean()):
            demandcost2_input = 0
        else:
            demandcost2_input = data['Demand_Daily'][(data['Demand_Daily_Period'] == 2)].mean()
        if math.isnan(data['Demand_Daily'][(data['Demand_Daily_Period'] == 3)].mean()):
            demandcost3_input = 0
        else:
            demandcost3_input = data['Demand_Daily'][(data['Demand_Daily_Period'] == 3)].mean()
        power_input = max(year_load)*0.2 #size to 20% of annual peak native load
        SOCmax_input = power_input*4 #4 hour battery
        chargeEff_input = 1 
        dischargeEff_input = 1
        RTEff_input = 0.81
        initOMax_input = 0 #just always 0
        depthDischarge_input = 0.2 #can't go below 20% SOC
        initSOC_input = SOCmax_input*depthDischarge_input #start at min SOC in first time period
        
        
        ### MODEL ###
        model = ConcreteModel()
        
        ## Define sets ##
        #  Sets
        model.T = Set(initialize=time_input) #this is for time (i.e. hours of day)
        #model.TOpt = Set() #tOpt is a subset of t that excludes the first hour from the optimization, not used
        
        ## Define parameters ##
        #load
        model.nativeload = Param(model.T, initialize=nativeload_input) #load is indexed by hour
        #periods
        model.demandperiod = Param(model.T, initialize=demandperiod_input)
        #rates/costs
        model.energycost = Param(model.T, initialize=energycost_input) #energy cost is indexed by hour
        model.demandcostmonthly = Param(initialize=demandcost_monthly_input)
        model.demandcost0 = Param(initialize=demandcost0_input) 
        model.demandcost1 = Param(initialize=demandcost1_input)
        model.demandcost2 = Param(initialize=demandcost2_input)
        model.demandcost3 = Param(initialize=demandcost3_input)
        #storage
        model.power = Param(initialize=power_input) #scalar Battery power rating
        model.SOCmax = Param(initialize=SOCmax_input) #scalar storage energy
        model.chargeEff = Param(initialize=chargeEff_input) #scalar Storage charge efficiency
        model.dischargeEff = Param(initialize=dischargeEff_input) # scalar discharge efficiency
        model.RTEff = Param(initialize=RTEff_input) # scalar discharge efficiency
        model.initSOC = Param(within = NonNegativeReals, initialize=initSOC_input) # scalar Storage initial state
        model.initOMax = Param(initialize=initOMax_input) #initial Overall Max Load
        model.depthDischarge = Param(initialize=depthDischarge_input) #min SOC %
        
        ## Define variables ##
        #  System Variables
        model.NetLoad = Var(model.T, within = NonNegativeReals, initialize=nativeload_input)
        model.OverallMaxLoad = Var(initialize = model.initOMax, within = NonNegativeReals)
        model.Period1MaxLoad = Var(initialize = model.initOMax, within = NonNegativeReals)
        model.Period2MaxLoad = Var(initialize = model.initOMax, within = NonNegativeReals)
        model.Period3MaxLoad = Var(initialize = model.initOMax, within = NonNegativeReals)
        # Storage Variables
        model.charge = Var(model.T, within = NonNegativeReals, bounds=(0,model.power*model.chargeEff))
        model.discharge = Var(model.T, within = NonNegativeReals, bounds=(0,model.power*model.dischargeEff))
        model.SOC = Var(model.T, initialize = model.initSOC, bounds=(model.depthDischarge*model.SOCmax, model.SOCmax))
        
        ## Define constraints ##
        def NetLoadRule(model, t):
            return (model.NetLoad[t] == model.nativeload[t] + model.charge[t] - model.discharge[t])
        model.NetLoadConst = Constraint(model.T, rule=NetLoadRule)
        
        def SOCRule(model, t):
            if t==0:
                return (model.SOC[t] == model.initSOC + model.charge[t]*(model.RTEff**.5) - model.discharge[t]/(model.RTEff**.5))
            else:
                return (model.SOC[t] == model.SOC[t-1] + model.charge[t]*(model.RTEff**.5) - model.discharge[t]/(model.RTEff**.5))
        model.SOCConst = Constraint(model.T, rule=SOCRule)
        
        def MaxLoadRule(model, t):
            return (model.OverallMaxLoad >= model.NetLoad[t])
        model.MaxLoadConst = Constraint(model.T, rule=MaxLoadRule)
        
        def Period1MaxLoadRule(model, t):
            if isinstance(model.demandperiod[t], int):
                if model.demandperiod[t] == 1:
                    return (model.Period1MaxLoad >= model.NetLoad[t])
                else:
                    return (Constraint.Skip)
            else:
                return (Constraint.Skip)
        model.Period1MaxLoadConst = Constraint(model.T, rule=Period1MaxLoadRule) 
        
        def Period2MaxLoadRule(model, t):
            if isinstance(model.demandperiod[t], int):
                if model.demandperiod[t] == 2:
                    return (model.Period1MaxLoad >= model.NetLoad[t])
                else:
                    return (Constraint.Skip)
            else:
                return (Constraint.Skip)
        model.Period2MaxLoadConst = Constraint(model.T, rule=Period2MaxLoadRule) 
        
        def Period3MaxLoadRule(model, t):
            if isinstance(model.demandperiod[t], int):
                if model.demandperiod[t] == 3:
                    return (model.Period1MaxLoad >= model.NetLoad[t])
                else:
                    return (Constraint.Skip)
            else:
                return (Constraint.Skip)
        model.Period3MaxLoadConst = Constraint(model.T, rule=Period3MaxLoadRule)
        
        ## Define Objective ##
        def objective_rule(model):
          return (model.Period3MaxLoad*model.demandcost3 +
                  model.Period2MaxLoad*model.demandcost2 + 
                  model.Period1MaxLoad*model.demandcost1 + 
                  model.OverallMaxLoad*model.demandcost0 +
                  model.OverallMaxLoad*model.demandcostmonthly +
                  sum(model.NetLoad[t]*model.energycost[t] for t in model.T)) #this is the TotalCost
        model.objective = Objective(rule=objective_rule, sense=minimize) #says we should minimize objective fxn
        
        ####Solve w/ glpk
        
        opt = SolverFactory('glpk')
        results = opt.solve(model)
        #print(results)
        
        #for p in model.component_objects(Param):
        #    print("FOUND PARAM:" + p.name)
        #    p.pprint()
        #for v in model.component_objects(Var):
        #    print("FOUND VAR:" + v.name)
        #    v.pprint()
        
        #### WRITE RESULTS TO CSV ####
        results_df = pd.DataFrame()
        results_df['Month'] = pd.Series(month_list)
        results_df['Load'] = pd.Series(hour_load)
        results_df['Energy_Cost'] = pd.Series(hour_energycost)
        results_df['Demand_Period'] = pd.Series(hour_demandperiod) 
        results_NetLoad = []
        results_Charge = []
        results_Discharge = []
        results_NetStorage = []
        results_SOC = []
        for i in range(len(hour_load)):
            results_NetLoad.append(model.NetLoad[i].value)
            results_Charge.append(model.charge[i].value)
            results_Discharge.append(model.discharge[i].value)
            results_NetStorage.append(model.charge[i].value - model.discharge[i].value)
            results_SOC.append(model.SOC[i].value)
        results_df['NetLoad'] = pd.Series(results_NetLoad)
        results_df['Charge'] = pd.Series(results_Charge)
        results_df['Discharge'] = pd.Series(results_Discharge)
        results_df['Net_Storage'] = pd.Series(results_NetStorage)
        results_df['SOC'] = pd.Series(results_SOC)
        monthly_data.append(results_df)
    
    annual_results_df = pd.concat(monthly_data)
    return (annual_results_df)
#annual_results_df.to_csv('storage_dispatch.csv') #write to csv in working directory
#print (storage_optimizer(input_data))
end_time = time.time() - start_time
print ("time elapsed during run is " + str(end_time) + " seconds")