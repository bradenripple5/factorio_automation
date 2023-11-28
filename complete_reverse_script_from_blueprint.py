import json, zlib, base64, copy

filename = "4trackcurve"

from convert_json_to_blueprint_string import convertoToJson, convertoToBlueprint

with open(filename) as f:
	recipe = convertoToJson(f.read())

mininum_x = min([i["position"]["x"] for i in recipe["blueprint"]["entities"]])
maximum_x = max([i["position"]["x"] for i in recipe["blueprint"]["entities"]])
middle = (maximum_x + mininum_x)//2
newrecipe = copy.deepcopy(recipe)
for index,entity in enumerate(recipe["blueprint"]["entities"]):
	x = entity["position"]["x"]
	if "direction" in entity:
		direction = entity["direction"]
		if direction%2 == 0:
			recipe["blueprint"]["entities"][index]["direction"] = direction + 3 #4 #(direction +4)%7
	recipe["blueprint"]["entities"][index]["position"]["x"] = middle -x
with open("reversed"+filename,"w+") as s:
	print("0"+convertoToBlueprint(recipe))
	s.write(convertoToBlueprint(recipe))

# inverse = json.dumps(string)
# print(inverse)