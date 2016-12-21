######################################################################################################
"""
Calls functions defined in "hitbottom.py" and uses them for computation

Globally stored data that is available here after reading in the data (for each profile):
df: flags (flags, depth)
mat: data (z, T)
mat: gradient (z, dTdz)
mat: dT9pt (z, T_av)
mat: secDer (d, d2Tdz2)
list: bath_lon
list: bath_lat
mat: bath_height (lat, long)
var: latitude
var: longitude 
var: date
var: hb_depth

Computation function outputs:
mat/arr: dTdz_peaks (z, T)
mat/arr: const_consec (z,T)

Functions callable (computation):
 - grad_spike(data, gradient, threshold)
 - T_spike(data, threshold)
 - const_temp(data, gradient, consec_points, detection_threshold)
 - temp_increase(data, consec_points)
 - bath_depth(latitude, longitude, bath_lon, bath_lat, bath_height)
 
Reading files or plotting (non-computational):
 - read_data(filename) | returns:	flags, hb_depth, latitude, longitude, date, data, gradient
						 opetionl (need to add): secDer, dT9pt
 - plot_data(plot) | creates plot	
 - bathymetry(filename) | returns:	bath_height, bath_lon, bath_lat
"""


######################################################################################################
# libraries

import numpy as np
import pandas as pd
import math
import os.path
import matplotlib.pyplot as plt
from netCDF4.utils import ncinfo
from netCDF4 import Dataset
import hitbottom as hb


######################################################################################################
# computation using code from hitbottom.py

# filename generation
path = "../HBfiles/"

# taking sample of files from the name file
namefile = open("HB_content.txt","r")
name_array = []
for line in namefile:
	line = line.rstrip()
	name = str(path+line)
	name_array.append(name)
namefile.close()

# reading files
for i in range(0,len(name_array)):
	
	# reading in file here
	filename = name_array[i]
	print(i,filename)
	[data, gradient, flags, hb_depth, latitude, longitude, date] = hb.read_data(filename)
	[bath_height, bath_lon, bath_lat] = hb.bathymetry("../terrainbase.nc")

	# code for the points on the plot
	"""
	const = hb.const_temp(data, gradient, 100, 0.001)
	inc = hb.temp_increase(data, 50)
	error_pts = hb.concat(const, inc)
	Tspike = hb.T_spike(data, 0.05)
	dTspike = hb.grad_spike(data, gradient, 3)
	pot_hb = hb.concat(Tspike,dTspike)
	bathydepth = hb.bath_depth(latitude, longitude, bath_lon, bath_lat, bath_height)
	hb.plot_data(True, data, gradient, flags, bathydepth, error_pts, pot_hb, filename)
	"""

	# code for collecting statistics on the data
	"""
	code to take in the data and find the optimal values for the inputs to the functions
	
	Most ideal cases:
	grad_spike: threshold = 3
	Tspike: threshold = ?
	temp_increase: consec_points = ?
	const_temp: consec_points = ? threshold = ?
	"""	
	range_vals = np.logspace(-4,-1,4)
	


######################################################################################################