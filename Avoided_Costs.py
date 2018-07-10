# -*- coding: utf-8 -*-
"""
Created on Tue Jun 19 14:53:08 2018

@author: llavi
"""

import os
from os.path import join
import pandas as pd
import numpy as np
import time

start_time = time.time()
cwd = os.getcwd()


'''
xls = pd.ExcelFile('path_to_file.xls')
df1 = pd.read_excel(xls, 'Sheet1')
df2 = pd.read_excel(xls, 'Sheet2')
'''
# look at EE or FERC form 1 filings for other utilities?