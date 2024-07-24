# convert iron ore station blueprint to copper ore station blueprint.

# actually better yet, figure out what the receiving item blueprint is and then change 
# it accordingly 
from convert_json_to_blueprint_string import *
from recipe_extraction import *
import json,copy,pyperclip, numpy

def get_template_for_assembling_machines_or_smelters():
	filename =  convertPathForOs("blueprints\\iron_gear_wheel_station")
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

def get_assembler_coordinate_data(blueprint):
	coordinate_dictionary_by_row = {}
	for i,v in enumerate(blueprint["blueprint"]["entities"]):
		if "assembling-machine" in v["name"]:
			if v["position"]["y"] in coordinate_dictionary_by_row:
				coordinate_dictionary_by_row[v["position"]["y"]] += [v["position"]["x"]]
			else:
				coordinate_dictionary_by_row[v["position"]["y"]] = [v["position"]["x"]]
	return coordinate_dictionary_by_row
def convert_assembling_recipe(blueprint,recipe,production_type =""):
	blueprint_copy = copy.deepcopy(blueprint)
	if recipe == "electric-engine-unit":
			solid_ingredients = [i for i in get_recipe(recipe) if not is_fluid(i)]
			for i,v in enumerate(blueprint["blueprint"]["entities"]):
				if v["name"] == "logistic-chest-requester":
					if len(v["request_filters"]) == 1:
						name = v["request_filters"][0]["name"]
						if name == "processing-unit":
							v["request_filters"][0]["name"] = recipe
						elif name == "sulfuric-acid-barrel":
							v["request_filters"][0]["name"] = "lubricant-barrel"
					else:
						v["request_filters"] = [ {"index": i, "name": v, "count": (48//len(solid_ingredients))*get_stack_size(recipe)} for i in solid_ingredients]

				elif  "assembling-machine" in v["name"]:
						v["items"] = {"speed-module-3": 4}
						if v["recipe"] == "processing-unit":
							v["recipe"] = "electric-engine-unit"
						if v["recipe"] == "empty-sulfuric-acid-barrel":
							v["recipe"] = "empty-lubricant-barrel"

				blueprint_copy["blueprint"]["entities"][i] = v
			return blueprint_copy

	elif production_type != "": # i.e. chemical plant production
		ingredients = get_recipe(recipe)
		total_fluids = ([i for i in ingredients if is_fluid(i)])
		other_fluid = ""
		try:
			other_fluid = [i for i in total_fluids if i!= "water"][0]
		except:
			other_fluid = ""
		with open(convertPathForOs("blueprints\\sulfur_station.json")) as f:
			blueprint = json.loads(f.read())
			blueprint_copy = copy.deepcopy(blueprint)

		for i,v in enumerate(blueprint["blueprint"]["entities"]):
			if v["name"] == "logistic-chest-requester":
				if "request_filters" in v:
					#these are for the logistic chest requester boxes that are to get the product
					if len(v["request_filters"]) == 1 and v["request_filters"][0]["name"] == "sulfur":
						v["request_filters"] = [{"index":1, "name": recipe, "count": 48*get_stack_size(recipe)}]
					elif sorted([v["name"] for v in v["request_filters"]]) == sorted(["petroleum-gas-barrel","water-barrel"]):
						v["request_filters"] = [{ "index": 1, "name": "water-barrel", "count" : 240},
						 {"index": 2, "name": other_fluid+"-barrel", "count" : 240
						 }]

			

					
				else:
					#this this would include the necessary solids for the chemical plant
					solid_ingredients = [i for i in ingredients if not is_fluid(i)]
					v["request_filters"] = [{"index":i+1,"name":v, "count":(48//(len(solid_ingredients)))*get_stack_size(v)} for i,v in enumerate(solid_ingredients) ]



			elif  "chemical-plant" == v["name"]:
				v["items"] = {"speed-module-3": 3}
				v["recipe"] = recipe
			elif "assembling-machine" in v["name"]:
				v["items"] = {"speed-module-3": 4}
				if "recipe" in v:
					if len(total_fluids) ==1:
						v["recipe"] = "empty-"+total_fluids[0]+"-barrel"
					elif len(total_fluids) >1:
						if v["recipe"] != "empty-water-barrel":
							v["recipe"] = "empty-"+other_fluid+"-barrel"
				else:
					v["recipe"] = "fill-"+recipe+"-barrel"

			blueprint_copy["blueprint"]["entities"][i] = v
	

	else:
		for i,v in enumerate(blueprint["blueprint"]["entities"]):
			v_copy = copy.deepcopy(v)
			if v["name"] == "logistic-chest-requester":
				if len(v["request_filters"]) == 1 and v["request_filters"][0]["name"] == "iron-gear-wheel":

					v_copy["request_filters"] = [{"index":1, "name": recipe, "count": 48*get_stack_size(recipe)}]
				else:
					v_copy["request_filters"] = make_request_filters(recipe)

			elif  "assembling-machine" in v["name"]:
				if is_smelted(recipe):
					v_copy["name"] = "electric-furnace"
					v_copy["items"] = {"speed-module-3": 2}
				else:
					v_copy["name"] == "assembling-machine-3"
					v_copy["items"] = {"speed-module-3": 4}


			# elif v["name"] == "train-stop"
			blueprint_copy["blueprint"]["entities"][i] = v_copy
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

	with open("blueprints\\stations\\repositories\\petroleum-gas-repository.json") as f:
		repository_blueprint = json.loads(f.read())
	repository_blueprint_copy = copy.deepcopy(repository_blueprint)
	current_recipe = "empty-barrel"
	for i,v in enumerate(repository_blueprint["blueprint"]["entities"]):
			v_copy = copy.deepcopy(v)
			if "request_filters" in v:
				if "coal" not in [i["name"] for i in v["request_filters"]]:
					v_copy["request_filters"] = [{
					"index": 1,
					"name": recipe,
					"count": 48*get_stack_size(recipe)
				  }]
			elif v["name"] == "train-stop":
				current_station = v["station"]
				new_station_name = current_station.replace("petroleum-gas-barrel",recipe)
				v_copy["station"] = new_station_name
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

def get_closest_locomotive(train_stop,blueprint):
	min_distance = 999999999
	closest_locomotive = ""
	for i,v in enumerate(blueprint["blueprint"]["entities"]):
		if v["name"] == "locomotive":
			dx = v["position"]["x"] - train_stop["position"]["x"]
			dy = v["position"]["y"] - train_stop["position"]["y"]

			distance = math.sqrt(dx*dx + dy*dy)
			if distance < min_distance:
				closest_locomotive = v
				distance = min_distance
	return closest_locomotive


def make_station(product):
	blueprint = get_template_for_assembling_machines_or_smelters()
	production_type = get_production_type(product)
	production_types = ["chemical_plant_fluids_from_two_fluids", "chemical_plant_solids_from_two_fluids", 
						"chemical_plant_fluids_from_one_fluid", "chemical_plant_solids_from_one_fluid", 
						"assembling-machine-with-one-fluid", "assembling-machine or smelter"]
	chemical_production_types = production_types[:4]

	# if production_type == "chemical_plant_fluids_from_one_fluid":
	if production_type in chemical_production_types:
		return convert_assembling_recipe(blueprint,product,production_type)
	if production_type == "processing-unit" or production_type == "electric-engine-unit":
		if product == "electric-engine-unit":
			blueprint = convert_assembling_recipe(blueprint,product)

	elif production_type == "assembling-machine or smelter":
		blueprint = get_template_for_assembling_machines_or_smelters()
		return convert_assembling_recipe(blueprint,product)

	
	return blueprint
def get_train_stops(blueprint):
	train_stops = {}
	for i,v in enumerate(blueprint["blueprint"]["entities"]):
		if v["name"] == "train-stop":
			if v["station"] in train_stops:
				train_stops[v["station"]] += v 
			else:
				
				train_stops[v["name"]] = v["station"]
	return train_stops

def get_station_dimensions():
	station = get_template_for_assembling_machines_or_smelters()

	min_x, min_y = station["blueprint"]["entities"][0]["position"].values()
	max_x, max_y = station["blueprint"]["entities"][0]["position"].values()

	for i,v in enumerate(station["blueprint"]["entities"][1:]):

		x,y = v["position"].values()
		if x < min_x:
			min_x = x
		if x > max_x:
			max_x =x
		if y < min_y:
			min_y = y
		if y > max_y:
			max_y = y
	return max_x - min_x+2, max_y- min_y


def makeArray(recipe):
	station_width,station_height = get_station_dimensions()
	total_blueprint= {}
	material_dictionary = get_non_raw_materials_from_material_heirarchy(makeMaterialHeirarchy(recipe,2))
	blueprints = []
	for key in material_dictionary:
		blueprints.extend([key]*int(material_dictionary[key]))
	total_number_of_stations = sum(material_dictionary.values())

	stations_high,stations_long = [int(math.sqrt(total_number_of_stations)),int(total_number_of_stations//int(math.sqrt(total_number_of_stations)))]
	for i in range(stations_high):
		for j in range(stations_long):
			current_station = make_station(blueprints.pop(0))
			if current_station:
				if total_blueprint == {}:
					total_blueprint = current_station
				else:
					num_entities = len(total_blueprint["blueprint"]["entities"])
					for k,v in enumerate(current_station["blueprint"]["entities"]):
						v_copy = copy.deepcopy(v)
						v_copy["entity_number"] = v["entity_number"]+num_entities
						v_copy["position"]["x"] += j*station_width
						v_copy["position"]["y"] += i*station_height

						total_blueprint["blueprint"]["entities"].append(v_copy)

	return total_blueprint 
pyperclip.copy(convertoToBlueprint(makeArray("steel-plate")))
# with open("blueprints\\electric_engine_unit.json") as f:
# 	blueprint = json.loads(f.read())
# pyperclip.copy(convertoToBlueprint(make_station("iron-gear-wheel")))
# pyperclip.copy(convertoToBlueprint(make_repository("heavy-oil-barrel")))

# pyperclip.copy(convertoToBlueprint(make_repository("water-barrel")))
# print(get_closest_locomotive(blueprint["blueprint"]["entities"][1406],blueprint))
# print((blueprint["blueprint"]["entities"][1406]))
# pyperclip.copy(convertoToBlueprint(make_station("processing-unit")))
# print(json.dumps(get_assembler_coordinate_data(get_template_for_assembling_machines_or_smelters()),indent=2))
# pyperclip.copy(convertoToBlueprint(convert_assembling_recipe(get_template_for_assembling_machines_or_smelters(),"solar-panel")))
# pyperclip.copy(convertoToBlueprint(make_repository("petroleum-gas-barrel")))
# pyperclip.copy(convertoToBlueprint(make_station("advanced-circuit")))
# pyperclip.copy(convertoToBlueprint(make_repository("steel-plate")))#"petroleum-gas-barrel")))
# pyperclip.copy(convertoToBlueprint(make_station("rocket-control-unit")))
# print(get_output_product(blueprint))#["blueprint"]["entities"][123]))
# print(m("electronic-circuit"))