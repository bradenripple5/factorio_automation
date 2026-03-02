#convertPathfor os script in python
from recipe_extraction import convertPathForOs
mypath = convertPathForOs("C:\\Users\\brade.DESKTOP-E538E75\\OneDrive\\Documents\\factorio_software_automation")
from os import listdir
from os.path import isfile, join
onlypythonfiles = [f for f in listdir(mypath) if isfile(join(mypath, f)) and f[-3:] == ".py"]
onlydirectories = [f for f in listdir(mypath) if not isfile(join(mypath, f))]
print(onlypythonfiles)
def converT