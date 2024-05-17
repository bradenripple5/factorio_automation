import sys, time, pyautogui

def get_multiple_mouse_coords(num_times = 2):
	mouse_coords = []
	for i in range(num_times):
		input("move mouse position to next position to be recorded and press enter")
		mouse_coords.append([i for i in pyautogui.position()])
	return mouse_coords

a,b = [[189, 110], [1346, 480]]

def delete_objects(num_times, delay):
	# [i.maximize() for i in pyautogui.getWindowsWithTitle("Factorio")]
	# pyautogui.getWindowsWithTitle("Factorio")[1].maximize()
	pyautogui.moveTo(a)
	pyautogui.click()
	pyautogui.keyDown("Alt")
	pyautogui.press("d")
	pyautogui.keyUp("Alt")

	for i in range(num_times):

		time.sleep(delay/1000)
		pyautogui.moveTo(a)
		pyautogui.mouseDown()
		pyautogui.moveTo(b)
		pyautogui.mouseUp()
delete_objects(int(sys.argv[1]), int(sys.argv[2]))
	
