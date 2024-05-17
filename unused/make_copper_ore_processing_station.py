import json,copy,pyperclip
filename = "blueprints\\iron_ore_station"
from convert_json_to_blueprint_string import *
# with open(filename) as f:
# 	with open(filename+".json","w+") as q:
# 		q.write(json.dumps(convertoToJson(f.read()),indent=2))
with open(filename) as f:
	filestring = f.read()
blueprint = convertoToJson(filestring)
blueprint_copy = copy.deepcopy(blueprint)

for i,v in enumerate(blueprint["blueprint"]["entities"]):
	if v["name"] == "logistic-chest-requester":
		if "iron-ore" == v["request_filters"][0]["name"]:
			v["request_filters"][0]["name"] = "copper-ore"
		elif "iron-plate" == v["request_filters"][0]["name"]:
			v["request_filters"][0]["name"] = "copper-plate"

		blueprint_copy["blueprint"]["entities"][i] = v
with open("blueprints\\copper_ore_station","w+") as f:
	f.write(convertoToBlueprint(blueprint_copy))
# pyperclip.copy(convertoToBlueprint(blueprint_copy))
