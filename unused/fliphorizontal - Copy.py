import json
filename = "4trackcurve.json"

with open(filename) as f:
	recipe = json.load(f)

	print(json.dumps(recipe,indent=2))
	mininum_x = min([i["position"]["x"] for i in recipe["blueprint"]["entities"]])
	maximum_x = max([i["position"]["x"] for i in recipe["blueprint"]["entities"]])
	middle = (maximum_x + mininum_x)//2

	for index,entity in enumerate(recipe["blueprint"]["entities"]):
		x = entity["position"]["x"]
		delta_x = middle - x
		recipe["blueprint"]["entities"][index]["position"]["x"] -=delta_x
	with open("reversed"+filename,"w+") as s:
		s.write(json.dumps(recipe))