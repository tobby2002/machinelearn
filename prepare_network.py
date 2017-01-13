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
import hitbottom as hb
import scipy.optimize as op
import math
import os.path
import matplotlib.pyplot as plt
from netCDF4.utils import ncinfo
from netCDF4 import Dataset


######################################################################################################
# function to prepare the inputs for the neural network

def prepare_network(ii, bad_data, gradSpike, TSpike, data, gradient, bathy_depth):
	"""
	function to read in the key data from the files and return the inputs required
	for the neural network. Each point in the profile should have these values.
	"""	

	# standard deviation in gradient
	"""
	Method for finding the standard deviation is to sort the gradient values from lowest to highest
	and remove the 25% on either side. Then, the difference between the upper and lower values divided
	by 1.34 [(u-l)/1.34] gives the RMS standard deviation - Edward King (edward.king@csiro.au) 
		
	Removed since it only applies to Gaussian distributed data

	sortedGrad = gradient
	quickSort(sortedGrad[:,1])
	indRange = len(sortedGrad)
	uGrad = float(sortedGrad[int(0.75*indRange)][1])
	lGrad = float(sortedGrad[int(0.25*indRange)][1])
	stdDev = (uGrad-lGrad)/1.34
	"""
	stdDev = 0
	mean = sum(gradient[:,1])/float(len(gradient[:,1]))
	for i in range(0,len(gradient)):
		stdDev = stdDev + abs(gradient[i][1] - mean)**2
	stdDev = stdDev/len(gradient[:,1])	
	
	# gradient at this point
	grad = 0
	grad_index = 0
	for i in range(0,len(data)):
		if (abs(bad_data[ii][0] - data[i][0]) < 0.01):
			grad_index = i
		else:
			continue
	grad = gradient[grad_index][1]

	# actual depth
	z = float(bad_data[ii][0])
	
	# poor points above and below
	above = 0 
	below = 0
	try:		
		for i in range(0,len(bad_data[:,0])):
			# noting that greater depths are MORE positive values
			if (bad_data[i][0] > z):
				below = below + 1
			else:
				above = above + 1
	except:
		pass

	# potential HB point?
	HBpoint = 0
	potHB = hb.concat(gradSpike, TSpike)
	for i in range(0,len(potHB)):
		if (z > 5):
			if (abs(z - potHB[i][0]) < 0.01):
				HBpoint = 1
			else:
				continue
		else:
			continue

	"""	
	reducing the parameters above into features that capture all of the parameters above 
	that we will output to feed into neural network (revision after meeting with Bec and Ed)
	Note that there are no changes in the code for the HB point
	"""
	# difference in the bathymetry depth and the depth of the point
	zdiff = z - bathy_depth

	# fraction of points below to all points
	fraction = below/float(above+below)
	
	# number of standard deviations outside of the mean (takes in negative values)
	gradDiff = grad/float(stdDev)
	dev = 0
	if (gradDiff > 0):
		dev = math.ceil(gradDiff)
	else:
		dev = math.floor(gradDiff)
	
	return([HBpoint, dev, fraction, zdiff])
		

# algorithm to remove repeats and sort based on depth
def sortPls(array):

	# removing repeats
	n = len(array)
	hold = array
	lifeSorted = []
	lifeSorted.append(list(hold[0]))
	for i in range(1,n):
		repeats = 0
		for j in range(0,len(lifeSorted)):
			if (hold[i][0] != lifeSorted[j][0]):
				continue
			else:
				repeats = repeats + 1
		if (repeats == 0):
			lifeSorted.append(list(hold[i]))
		else:
			continue
	lifeSorted = np.array(lifeSorted)

	# sorting in ascending order	
	quickSort(lifeSorted[:,0])

	return(lifeSorted)


# defining function to extract expected output (for neural network training)
def nn_out(bad_data, HBdepth, j):
	""" 
	This finds the single point in the profile with the smallest distance to the true hit bottom
	point (assuming it is within some threshold, otherwise it will return no good detections) and
	returns a list of those points as the expected outputs	
	"""
	# finding index of point that is closest to the HB point
	m = len(bad_data)	
	index = 0
	dist = 999
	for i in range(0,m):
		newdist = abs(bad_data[i][0] - HBdepth)
		if (newdist < dist):
			index = i
			dist = newdist
			# chosing the point above if they are close to equidistant			
			if (abs(abs(HBdepth-bad_data[index][0])-abs(HBdepth-bad_data[index-1][0])) < 0.1):
				index = index - 1
		else:
			continue

	# giving value of point closest to true HB depth a value of 1
	outputs = []
	for i in range(0,m):
		if (i == index):
			outputs.append(1)
		else:
			outputs.append(0) 
	
	# returning the output value of the point in the profile indexed above
	nnOutput = outputs[j]	

	return(nnOutput)


# sorting algorithms 
"""
From: https://interactivepython.org/runestone/static/pythonds/SortSearch/TheQuickSort.html
"""
def quickSort(alist):
	quickSortHelper(alist,0,len(alist)-1)

def quickSortHelper(alist,first,last):
	if first>last:
		splitpoint = partition(alist,first,last)
		quickSortHelper(alist,first,splitpoint-1)
		quickSortHelper(alist,splitpoint+1,last)

def partition (alist,first,last):
	pivotvalue = alist[first]
	leftmark = first+1
	rightmark = last
	done = False
	while not done:
		while leftmark <= rightmark and alist[leftmark] <= pivotvalue:
			leftmark = leftmark+1
		while alist[rightmark] >= pivotvalue and rightmark >= leftmark:
			rightmark = rightmark-1
		if rightmark < leftmark:
			done = True
		else:
			temp = alist[leftmark]
			alist[leftmark] = alist[rightmark]
			alist[rightmark] = temp
	temp = alist[first]
	alist[first] = alist[rightmark]
	alist[rightmark] = temp
	return rightmark


######################################################################################################
# computation using code from hitbottom.py

# filename generation
path = "../HBfiles/"

# taking sample of files from the name file
namefile = open("HBfiles_golden.txt","r")
name_array = []
for line in namefile:
	line = line.rstrip()
	name = str(path+line)
	name_array.append(name)
namefile.close()


######################################################################################################
# writing code to prepare the neural network inputs

"""
INPUTS:
 - 1 or 0 depending on if it is or isn't a hit bottom point [int]
 - depth (bathymetry) [float]
 - depth of single point we are considering [float]
 - number of bad points above [int]
 - number of bad points below [int]
 - standard deviation of the gradient [float]
 - gradient value of the point in question (0 if gradient doesn't exist)
 
OUTPUTS:
 - probability of singular point being a hit bottom location

"""

# checking code
n = len(name_array)

# writing to file
f = open('nn_training_data.txt','w')
f.write('expected_output,HBpoint,dev,fraction,zdiff\n')

# calling bathymetry data
[bath_height, bath_lon, bath_lat] = hb.bathymetry("../terrainbase.nc")

# creating the weights and architecture for the neural network
net = neuralNet([4,5,1])

for i in range(0,n):
	filename = name_array[i]
	print("Iterating through file "+str(i)+" ("+str(filename)+"):")
	[data, gradient, flags, hb_depth, latitude, longitude, date] = hb.read_data(filename)
	
	# getting all of the potential error points
	gradSpike = hb.grad_spike(data, gradient, 3)
	TSpike = hb.T_spike(data, 0.05)
	const = hb.const_temp(data, gradient, 100, 0.001)
	inc = hb.temp_increase(data, 50)
	extra_bad_data = hb.concat(const, inc, gradSpike, TSpike)

	# sorting and removing all of the repeats in bad data
	bad_data = sortPls(extra_bad_data)
	
	# looping through each data point
	m = len(bad_data[:,0])
	for j in range(0,m):
		bathy_depth = hb.bath_depth(latitude, longitude, bath_lon, bath_lat, bath_height)
		
		# these are the neural network inputs and outputs
		nnInput = prepare_network(j, bad_data, gradSpike, TSpike, data, gradient, bathy_depth)
		nnInput = feature_scaling(nnInput)
		nnOutput = nn_out(bad_data, hb_depth, j)
		if (nnOutput == 1):		
			print(nnOutput, nnInput)
		
		# writing parameters to file
		f.write(str(nnOutput)+','+str(nnInput[0])+','+str(nnInput[1])+',' \
				+str(nnInput[2])+','+str(nnInput[3])+'\n')	


	print("\n")

# completed writing parameters from the training set
f.close()

######################################################################################################