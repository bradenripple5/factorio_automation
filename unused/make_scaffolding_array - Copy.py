import json,copy,pyperclip
from convert_json_to_blueprint_string import *
with open("blueprints\\map_scaffold.json") as f:
	scaffold_blueprint = json.loads(f.read())
# i want this, but also to overlap the edge entities, so perhaps subtract the width, and length of roboport,
# no that's a bad idea, it needs to somehow 
def get_x_and_y_distance(blueprint):
	roboport_x,roboport_y = 0,0
	mininum_x,maximum_x = [blueprint["blueprint"]["entities"][0]["position"]["x"]]*2
	mininum_y,maximum_y = [blueprint["blueprint"]["entities"][0]["position"]["y"]]*2
	for i,v in enumerate(blueprint["blueprint"]["entities"]):
		# if v["name"] == "roboport":

		x,y = v["position"].values()
		if x < mininum_x:
			mininum_x = x
		if x > maximum_x:
			maximum_x = x 
		if y < mininum_y:
			mininum_y = y
		if y > maximum_y:
			maximum_y = y
	return [maximum_x - mininum_x,maximum_y - mininum_y]
def make_blueprint_offset_copy(blueprint,offset_x,offset_y):
	blueprint_copy = copy.deepcopy(blueprint)
	for i,v in enumerate(blueprint["blueprint"]["entities"]):
		v_copy = copy.deepcopy(v)
		v_copy["position"] = {"x" : v["position"]["x"]+offset_x, "y": v["position"]["y"]+offset_y}
		blueprint_copy["blueprint"]["entities"][i] = v_copy
	return blueprint_copy
def add_entities_to_blueprint(blueprint_copy,blueprint):
	for i,v in enumerate(blueprint_copy["blueprint"]["entities"]):
		v_copy = copy.deepcopy(v)
		v_copy["entity_number"] = len(blueprint["blueprint"]["entities"])+i
		blueprint["blueprint"]["entities"].append(v_copy)
	return blueprint
def add_entities_to_blueprint_n_times(blueprint,number_of_times,offset_x,offset_y):
	blueprint_copy = copy.deepcopy(blueprint)

	for instance in range(1,number_of_times):
		offset_x,offset_y = get_x_and_y_distance(blueprint)
		offset_x = offset_x - 4
		offset_y = 0
		for i,v in enumerate(blueprint_copy["blueprint"]["entities"]):
			v_copy = copy.deepcopy(v)
			v_copy["entity_number"] = len(blueprint["blueprint"]["entities"])+i
			v_copy["position"]["x"] = v["position"]["x"] + offset_x +e1*(instance%2==0)
			blueprint["blueprint"]["entities"].append(v_copy)

	return blueprint

offset_x,offset_y = get_x_and_y_distance(scaffold_blueprint)
offset_x = 0
doubled_blueprint = add_entities_to_blueprint(make_blueprint_offset_copy(scaffold_blueprint,offset_x,offset_y-2),scaffold_blueprint)
blueprint_array = add_entities_to_blueprint_n_times(scaffold_blueprint,8,offset_x,0)
pyperclip.copy(convertoToBlueprint(blueprint_array))
