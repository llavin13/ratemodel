# -*- coding: utf-8 -*-
"""
Created on Tue Jun 19 17:17:38 2018

@author: llavi
"""
import numpy as np
import pandas as pd

#ENERGY BILL
def energy_bill_calc(data, col):
    energy_bill = []
    months = list(range(1, 13))
    
    for m in months:
        energy_charge = data['Energy_Tier0'][(data['Month']==m)]
        load = data[col][(data['Month']==m)]
        month_bill = energy_charge.dot(load)
        energy_bill.append(month_bill)
    return energy_bill
#test_full.to_csv('test_full.csv')

#CUSTOMER BILL
def customer_bill_calc(data, col):
    customer_bill = []
    months = list(range(1, 13))
    
    for m in months:
        customer_charge = data['Customer'].mean()
        customer_bill.append(customer_charge)
    return customer_bill

#DEMAND BILL DAILY (TIME PERIOD BASED)
def demand_bill_calc(data, col):
    demand_bill = []
    months = list(range(1, 13))
    dmnd_daily = data['Demand_Daily_Period']
    dmnd_period_count = dmnd_daily.nunique(dropna=True)

    for m in months:
        for d in range(dmnd_period_count):
            demand_rate = data['Demand_Daily'][(data['Demand_Daily_Period']==d)].mean()
            if d == 0:
                max_demand = data[col][(data['Month']==m)].max()
            else:
                max_demand = data[col][(data['Month']==m) & (data['Demand_Daily_Period']==d)].max()
            max_demand = np.asarray(max_demand)
            max_demand[np.isnan(max_demand)] = 0
            max_demand = max_demand.tolist()

            demand_cost = max_demand * demand_rate
            if np.isnan(demand_cost):
                demand_cost = 0
            demand_bill.append(demand_cost)
    return demand_bill

#DEMAND BILL MONTHLY
def demand_bill_month_calc(data, col):
    demand_bill = []
    months = list(range(1, 13))
    
    for m in months:
        if isinstance(data['Demand_Monthly'][0],str):
            demand_rate = 0
        else:
            demand_rate = data['Demand_Monthly'].mean()
        max_demand = data[col][(data['Month']==m)].max()
        max_demand = np.asarray(max_demand)
        max_demand[np.isnan(max_demand)] = 0
        max_demand = max_demand.tolist()
        demand_cost = max_demand * demand_rate
        if np.isnan(demand_cost):
            demand_cost = 0
        demand_bill.append(demand_cost)
    return demand_bill