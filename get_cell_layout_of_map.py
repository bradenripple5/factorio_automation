# # we take an image of the map using image PIL library
# # then we choose a point on that image that we can use to distinguish filled cells from the non filled ones.
# # then we take small parts of that grid and determine if what we have is a new grid or if it's not.
# # filling up a matrix with ones and zeroes representing what parts of the map are new grids and which ones are not.

# from PIL import ImageGrab
# import copy
# # Capture the entire screen
# screenshot = ImageGrab.grab()

# # Save the screenshot to a file
# screenshot.save("screenshot.png")

# # Close the screenshot
# screenshot.close()
# import mss
# import mss.tools
# from matplotlib import pyplot as plt
# import numpy as np


# with mss.mss() as sct:
# 	# Get information of monitor 2
# 	monitor_number = 2
# 	mon = sct.monitors[monitor_number]

# 	# The screen part to capture
# 	monitor = {
# 		"top": mon["top"],
# 		"left": mon["left"],
# 		"width": mon["width"],
# 		"height": mon["height"],
# 		"mon": monitor_number,
# 	}
# 	output = "sct-mon{mon}_{top}x{left}_{width}x{height}.png".format(**monitor)

# 	# Grab the data
# 	sct_img = sct.grab(monitor)

# 	M = sct_img.pixels
# 	M = np.asarray(M)
# 	M = M#[400:450,400:450]

# 	N = copy.deepcopy(M)
# 	maximum = 0
# 	for i,v  in enumerate(M):
# 		for j,u in enumerate(v):
# 			# if not any([ u.tolist() == x for x in [[214,206,140]]]):
# 			# 	u = (0,0,0)
			
# 			N[i,j] =  u

# 	plt.imshow(np.array(N), interpolation='none')
# 	plt.show()
# 	# Save to the picture file
# 	mss.tools.to_png(sct_img.rgb, sct_img.size, output=output)
# 	print(output)
import os
from PIL import Image
import numpy

if "monitor-2.png" not in os.listdir():
	import mss
	sct = mss.mss()
	print(dir)
	for x in sct.save():
	    print(x)
im = Image.open("monitor-2.png")
data = numpy.asarray(im)
print(data)