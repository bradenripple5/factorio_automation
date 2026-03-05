import json
import copy
from recipe_extraction import *
import pyperclip 
from convert_json_to_blueprint_string import *

#ok, so what I have to do here is to 
# with open ("blueprints\\receiving_station_with_assemblers.json") as f:
# with open ("blueprints\\electric_engine_unit.json") as f:

# 	print("blueprint equals = ",json.dumps(blueprint,indent=2))
# with open ("ingredients.json") as f:
# 	ingredients = json.load(f)


# print(json.dumps(blueprint,indent =2))
# print(json.dumps(ingredients[-1],indent=2))



def make_assembling_machine(what_you_want_make):
	with open ("blueprints\\assembling_machines\\mining_drill") as f:
		blueprint = convertoToJson(f.read())

	recipe_name = resolve_recipe_name(what_you_want_make)
	recipe = get_recipe(what_you_want_make)
	if recipe is None:
		raise ValueError(f"unknown recipe: {what_you_want_make}")
	machine_name = "assembling-machine-2"
	if is_smelted(recipe_name) or "plate" in recipe_name or recipe_name in ["stone", "brick"]:
		machine_name = "electric-furnace"
	requestable_ingredients = [ingredient for ingredient in recipe if not is_fluid(ingredient)]
	#this changes every requester chest to what you want
	for index, entity in enumerate(blueprint["blueprint"]["entities"]):
		if entity["name"] == "requester-chest":
			blueprint["blueprint"]["entities"][index]["request_filters"]["sections"] =[{"index":1,"filters": [{"index":i+1,"name":v,"count":100,  "quality": "normal", "comparator": "="} for i,v in enumerate(requestable_ingredients)]}]
		elif "assembling-machine" in entity["name"]:
			blueprint["blueprint"]["entities"][index]["name"] = machine_name
			blueprint["blueprint"]["entities"][index]["recipe"] = recipe_name
	return blueprint

	return blueprint


def _get_footprint(blueprint):
	entities = blueprint["blueprint"]["entities"]
	min_x = min(e["position"]["x"] for e in entities)
	max_x = max(e["position"]["x"] for e in entities)
	min_y = min(e["position"]["y"] for e in entities)
	max_y = max(e["position"]["y"] for e in entities)
	return max_x - min_x, max_y - min_y


def _pole_distance(entity_by_number, a, b):
	ax, ay = entity_by_number[a]["position"]["x"], entity_by_number[a]["position"]["y"]
	bx, by = entity_by_number[b]["position"]["x"], entity_by_number[b]["position"]["y"]
	dx, dy = ax - bx, ay - by
	return (dx * dx + dy * dy) ** 0.5


def _connect_pole_pair(entity_by_number, a, b, wire_reach=9.0, max_connections=5):
	if a == b:
		return
	if _pole_distance(entity_by_number, a, b) > wire_reach:
		return
	entity_a = entity_by_number[a]
	entity_b = entity_by_number[b]
	neighbours_a = entity_a.setdefault("neighbours", [])
	neighbours_b = entity_b.setdefault("neighbours", [])
	if b in neighbours_a or a in neighbours_b:
		return
	if len(neighbours_a) >= max_connections or len(neighbours_b) >= max_connections:
		return
	neighbours_a.append(b)
	neighbours_b.append(a)


def make_assembling_machine_array(recipes, columns=None, spacing_x=None, spacing_y=None, connect_poles=True):
	"""
	Create an array of assembling machine modules where each module gets:
	- its own assembler recipe
	- its own requester chest filters
	"""
	if not recipes:
		raise ValueError("recipes must contain at least one recipe name")

	template = make_assembling_machine(recipes[0])
	width, height = _get_footprint(template)
	if spacing_x is None:
		spacing_x = width + 2
	if spacing_y is None:
		spacing_y = height + 2
	if columns is None:
		columns = len(recipes)
	columns = max(1, int(columns))

	result = copy.deepcopy(template)
	result["blueprint"]["entities"] = []
	module_poles = {}

	entity_number = 1
	for recipe_index, recipe in enumerate(recipes):
		module = make_assembling_machine(recipe)
		row = recipe_index // columns
		col = recipe_index % columns
		dx = col * spacing_x
		dy = row * spacing_y
		module_poles[recipe_index] = []
		for entity in module["blueprint"]["entities"]:
			entity_copy = copy.deepcopy(entity)
			entity_copy["position"]["x"] += dx
			entity_copy["position"]["y"] += dy
			entity_copy["entity_number"] = entity_number
			if "pole" in entity_copy["name"]:
				entity_copy.pop("neighbours", None)
				module_poles[recipe_index].append(entity_number)
			entity_number += 1
			result["blueprint"]["entities"].append(entity_copy)

	if connect_poles:
		entity_by_number = {e["entity_number"]: e for e in result["blueprint"]["entities"]}
		n = len(recipes)
		for idx in range(n):
			row = idx // columns
			col = idx % columns
			right = idx + 1
			down = idx + columns
			if col + 1 < columns and right < n and module_poles[idx] and module_poles[right]:
				_connect_pole_pair(entity_by_number, module_poles[idx][0], module_poles[right][0])
			if down < n and module_poles[idx] and module_poles[down]:
				_connect_pole_pair(entity_by_number, module_poles[idx][0], module_poles[down][0])
	return result
def find_receiving_train_stop_coords(blueprint):
	receiving_stop_coords = {}
	for index, entity in enumerate(blueprint["blueprint"]["entities"]):
		if entity["name"] == "train-stop" and "station" in entity:
			if any( [i in entity["station"].lower() for i in ["receiving","dropoff"]]):
				return entity["position"]

def change_requester_chests_near_requester_station(what_you_want_make):
	make_assembling_machine("electronic-circuit",100)
	y_above, y_below, x_range = -1.5, .5, [-3,4*-3]
	train_coords = find_receiving_train_stop_coords(blueprint)
	if train_coords:	
		for index, entity in enumerate(blueprint["blueprint"]["entities"]):
			if entity["name"] == "logistic-chest-requester":
				if abs(entity["position"]["x"] - train_coords["x"]) < 40:
					if abs(entity["position"]["y"] - train_coords["y"]) in [.5,4.5]:
						blueprint["blueprint"]["entities"][index]["request_filters"] = [{
								"index": 1,
								"name": what_you_want_make,
								"count": 20000
							}]

	return blueprint

# print(json.dumps(ingredient_dictionary,indent=2))
# print(json.dumps(ingredient_dictionary["raw-wood"],indent=2))
def getAllNecessaryItems(item):
	items = set()
	material_dict = ingredient_dictionary[item]
	if material_dict["recipe"]["time"] == None:
		return items
	for element in material_dict["recipe"]["ingredients"]:
		items.add(element["id"])
	for element in material_dict["recipe"]["ingredients"]:
		items = items.union(getAllNecessaryItems(element["id"]))
	return items
def getMaterialHeirarchy(item,amount =1):
	material_dict = ingredient_dictionary[item]
	if material_dict["recipe"]["time"] == None:
		return None
	subDict = {}
	for element in material_dict["recipe"]["ingredients"]:
		subDict[element["id"]+"-amount"] = element["amount"]*amount
		subDict[element["id"]] =  getMaterialHeirarchy(element["id"],element["amount"]*amount)
	return subDict

# print(json.dumps(getMaterialHeirarchy("nuclear-reactor"),indent=2))
if __name__ == "__main__":
	pyperclip.copy(
		convertoToBlueprint(
			make_assembling_machine_array(
				["iron-gear-wheel", "transport-belt", "inserter", "electronic-circuit"],
				columns=2,
			)
		)
	)

# product = "space-science-pack"
# print(json.dumps({product:getMaterialHeirarchy(product)},indent=2))
# packs = [i for i in ingredient_dictionary if "pack" in i]
# allitems = set()
# for pack in packs:
# 	allitems = allitems.union(getAllNecessaryItems(pack))
# print(allitems)
# print(len(allitems))
# print(len(ingredients))
# print([i["id"] for i in ingredients if "belt" in i["id"]])
# print([i for i in ingredient_dictionary if "pack" in i])
# print(json.dumps(ingredient_dictionary["copper-cable"]))
# print(make_assembling_machine("fusion-reactor",1))
# print(convertoToBlueprint(change_requester_chests_near_requester_station("electronic-circuit")))


# change_requester_chests_near_requester_station("electronic-circuit")
# # print(convertoToBlueprint(change_requester_chests_near_requester_station("production-science-pack")))
# print(convertoToBlueprint(blueprint))
# print(json.dumps(make_assembling_machine("production-science-pack"),indent=2))

# pyperclip.copy(json.dumps(data["blueprint"]["entities"][3]["request_filters"],indent=2))
