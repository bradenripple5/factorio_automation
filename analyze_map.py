import os,sys,random

print("Python version")
print(sys.version)
print("Version info.")
print(sys.version_info)
import pygetwindow as gw
import numpy as np

print(gw.getAllTitles())
handle = gw.getWindowsWithTitle('Factorio 1.1.107')[0]
handle.activate()
handle.maximize()
from PIL import ImageGrab
from PIL import Image as im 

snapshot = ImageGrab.grab() 
img_np = np.array(snapshot)
print(img_np.shape)
img_np = img_np[:730]
print(img_np[250,250])
for i, row in enumerate(img_np):
	for j, pixel in enumerate(row):
		if not(pixel[2] > 220 and pixel[1] < 220 and pixel[0] < 220):
			img_np[i,j] = [0,0,0]
		else:
			img_np[i,j] = [255]*3

def get_cell_width(img_data):
	img_data_reduced = [[i[0] for i in j] for j in img_data][:len(img_data)//3]
	cell_distances = []

	for row in img_data_reduced[:3]:
		row = img_data_reduced[random.randint(0,len(img_data_reduced)-1)]
		if row != [0]*len(row):
			print(row, " = row")
			dist = 0
			nonzero_reached = False
			for cell in row:
				if cell != 0 :
					nonzero_reached = True
				elif nonzero_reached:
					cell_distances.append(dist)
					nonzero_reached = False
					dist = 0
				else:
					dist +=1
	while 0 in cell_distances:
		cell_distances.remove(0)
	return max(set(cell_distances), key = cell_distances.count)

def make_grid(initial_array, grids_wide = 5, grids_high = 5):
	cell_width = get_cell_width(initial_array)
	for row_index in range(len(initial_array)):
		for col_index in range(len(initial_array[0])):
			if row_index%cell_width == 0 or col_index%cell_width == 0:
				initial_array[row_index,col_index] = [255]*3
	return initial_array
img_data = make_grid(img_np)
data = im.fromarray(img_data) 

data.show()