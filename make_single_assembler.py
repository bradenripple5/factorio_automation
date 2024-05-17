# convert iron ore station blueprint to copper ore station blueprint.

# actually better yet, figure out what the receiving item blueprint is and then change 
# it accordingly 
from convert_json_to_blueprint_string import *
from recipe_extraction import *
import json,copy,pyperclip
filename = "blueprints\\single_assembler_big_electric_pole"
# with open(filename) as f:
# 	with open(filename+".json","w+") as q:
# 		q.write(json.dumps(convertoToJson(f.read()),indent=2))
with open(filename) as f:
	filestring = f.read()
blueprint = convertoToJson(filestring)
def make_single_assembler(recipe):
	blueprint_copy = copy.deepcopy(blueprint)
	for i,v in enumerate(blueprint["blueprint"]["entities"]):
		v_copy = v
		if v["name"] == "logistic-chest-requester":
			v_copy["request_filters"] = make_request_filters(recipe)
		elif v["name"] == "assembling-machine-3":
			v_copy["recipe"] = recipe
			v_copy["items"] = {"speed-module-3": 4}
			if is_smelted(v["recipe"]):
				v["name"] = "electric-furnace"
		blueprint_copy["blueprint"]["entities"][i] = v_copy
	return blueprint_copy

pyperclip.copy(convertoToBlueprint(make_single_assembler("empty-barrel")))
# print(get_output_product(blueprint))#["blueprint"]["entities"][123]))
# print(m("electronic-circuit"))