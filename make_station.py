# convert iron ore station blueprint to copper ore station blueprint.

# actually better yet, figure out what the receiving item blueprint is and then change 
# it accordingly 
from convert_json_to_blueprint_string import *
from recipe_extraction import *
import json,copy,pyperclip
def get_template_for_assembling_machines_or_smelters():
	filename = "blueprints\\iron_gear_wheel_station"
	# with open(filename) as f:
	# 	with open(filename+".json","w+") as q:
	# 		q.write(json.dumps(convertoToJson(f.read()),indent=2))
	with open(filename) as f:
		filestring = f.read()
	blueprint = convertoToJson(filestring)
	return blueprint


def get_requester_chest_ingredients(blueprint_entity):
	return [i["name"] for i in blueprint_entity["request_filters"]]

def get_output_product(blueprint_data):
	furnace_station = False
	for i,v in enumerate(blueprint_data["blueprint"]["entities"]):
		if "assembling" in v["name"] or v["name"] == "chemical-plant":
			return v["recipe"]

def convert_assembling_recipe(blueprint,recipe):
	blueprint_copy = copy.deepcopy(blueprint)
	for i,v in enumerate(blueprint["blueprint"]["entities"]):
		if v["name"] == "logistic-chest-requester":
			if len(v["request_filters"]) == 1 and v["request_filters"][0]["name"] == "iron-gear-wheel":

				v["request_filters"] = [{"index":1, "name": recipe, "count": 48*get_stack_size(recipe)}]
			else:
				v["request_filters"] = make_request_filters(recipe)

		elif  "assembling-machine" in v["name"]:
			v["name"] == "assembling-machine-3"
			v["recipe"] = recipe
			v["items"] = {"speed-module-3": 4}
			if is_smelted(v["recipe"]):
				v["name"] = "electric-furnace"
		# elif v["name"] == "train-stop"
		blueprint_copy["blueprint"]["entities"][i] = v
	return blueprint_copy
def get_chemical_plant_recipe(blueprint):
	for i,v in blueprint["blueprint"]["entities"]:
		if v["name"] == "chemical-plant":
			return v["recipe"]

# def convert_chemical_plant_recipe(recipe):


def convert_chemical_plant_for_chemical_plant_fluids_from_one_fluid(product):
	with open("blueprints\\stations\\chemical_plant_fluids_from_one_fluid\\lubricant.json") as f:
		blueprint = json.loads(f.read())
	if product == "lubricant":
		return blueprint

def make_repository(recipe):

	with open("blueprints\\empty_barrel_repository.json") as f:
		repository_blueprint = json.loads(f.read())
	repository_blueprint_copy = copy.deepcopy(repository_blueprint)
	current_recipe = "empty-barrel"
	for i,v in enumerate(repository_blueprint["blueprint"]["entities"]):
		v_copy = copy.deepcopy(v)
		if v["name"] == "logistic-chest-requester" or "logistic-chest-buffer":
			v_copy["request_filters"] = [{
			"index": 1,
			"name": recipe,
			"count": 48*get_stack_size(recipe)
		  }]
		elif v["name"] == "train-stop":
			if "dropoff" in v["name"]:
				v_copy["name"] = f"{recipe} dropoff"
			elif "pickup" in v["name"]:
				v_copy["name"] = f"{recipe} pickup"
		repository_blueprint_copy["blueprint"]["entities"][i] = v_copy
	return repository_blueprint_copy

def convert_assembling_recipe_for_fluid_consuming_assembling_machines(blueprint,recipe):
	blueprint_copy = copy.deepcopy(blueprint)
	for i,v in enumerate(blueprint["blueprint"]["entities"]):
		if v["name"] == "logistic-chest-requester":
			if len(v["request_filters"]) == 1 and v["request_filters"][0]["name"] == "iron-gear-wheel":

				v["request_filters"] = [{"index":1, "name": recipe, "count": 48*get_stack_size(recipe)}]
			else:
				v["request_filters"] = make_request_filters(recipe)

		elif  "assembling-machine" in v["name"]:
			v["name"] == "assembling-machine-3"
			v["recipe"] = recipe
			v["items"] = {"speed-module-3": 4}
			if is_smelted(v["recipe"]):
				v["name"] = "electric-furnace"
		blueprint_copy["blueprint"]["entities"][i] = v
	return blueprint_copy

def make_station(product):

	production_type = get_production_type(product)
	production_types = ["chemical_plant_fluids_from_two_fluids", "chemical_plant_solids_from_two_fluids", 
						"chemical_plant_fluids_from_one_fluid", "chemical_plant_solids_from_one_fluid", 
						"assembling-machine-with-one-fluid", "assembling-machine or smelter"]
	# if production_type == "chemical_plant_fluids_from_one_fluid":

	if production_type == "assembling-machine or smelter":
		blueprint = get_template_for_assembling_machines_or_smelters()
		return convert_assembling_recipe(blueprint,product)
	elif production_type == "assembling-machine-with-one-fluid":
		blueprint = json.loads("blueprints\\petroleum_gas_barrel_filling_assembling_machine.json")
	
	return blueprint
# pyperclip.copy(convertoToBlueprint(convert_assembling_recipe(get_template_for_assembling_machines_or_smelters(),"solar-panel")))
# pyperclip.copy(convertoToBlueprint(make_repository("petroleum-gas-barrel")))
# pyperclip.copy(convertoToBlueprint(make_station("advanced-circuit")))
# pyperclip.copy(convertoToBlueprint(make_repository("steel-plate")))#"petroleum-gas-barrel")))
pyperclip.copy(convertoToBlueprint(make_station("empty-barrel")))
# print(get_output_product(blueprint))#["blueprint"]["entities"][123]))
# print(m("electronic-circuit"))