# convert iron ore station blueprint to copper ore station blueprint.

# actually better yet, figure out what the receiving item blueprint is and then change 
# it accordingly 
import time
from convert_json_to_blueprint_string import *
from recipe_extraction import *
import json,copy,pyperclip, numpy
def filter_blueprint_for_item(blueprint,item):
	blueprint_copy = copy.deepcopy(blueprint)
	blueprint_copy["blueprint"]["entities"] = []
	i = 1
	for entity in (blueprint["blueprint"]["entities"]):
		if entity["name"] == item:
			entity["entity_number"] = i
			blueprint_copy["blueprint"]["entities"].append(entity)
			i+=1
	return blueprint

def get_proximity_dictionary_alt_medium(blueprint,number_of_neighbors):
	with open("javascript_blueprint.json","w+") as f:
		f.write(json.dumps((blueprint)))
	os.system(f"node make_proximity_dictionary_medium.js {number_of_neighbors}")
	with open("proximity_dictionary.json") as f:
		return json.loads(f.read())


def neighbourify_medium_electric_poles(blueprint,number_of_neighbors = 3):
	proximity_dictionary = {int(k):v for k,v in get_proximity_dictionary_alt_medium(blueprint,number_of_neighbors).items()}

	for i,v in enumerate(blueprint["blueprint"]["entities"]):
		if v["name"] == "medium-electric-pole":
			v["neighbours"] = proximity_dictionary[i+1]
	return blueprint

def get_station_type(blueprint):
	for i,v in enumerate(blueprint["blueprint"]["entities"]):
		if "train-stop" == v["name"]:
			if "shipping" in v["station"]:
				return v["station"].replace(" shipping","")

def get_template_for_assembling_machines_or_smelters():
	filename =  convertPathForOs("blueprints\\iron_gear_wheel_station.json")
	# with open(filename) as f:
	# 	with open(filename+".json","w+") as q:
	# 		q.write(json.dumps(convertoToJson(f.read()),indent=2))
	with open(filename) as f:
		return json.loads(f.read())



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
	ingredients = get_recipe(recipe)
	blueprint_copy = copy.deepcopy(blueprint)

	if recipe in ["electric-engine-unit","processing-unit"]:
		print("recipe in electric or processing unit")
		solid_ingredients = [i for i in get_recipe(recipe) if not is_fluid(i)]
		for i,v in enumerate(blueprint["blueprint"]["entities"]):
			if recipe == "processing-unit":
				if v["name"] == "logistic-chest-requester":
					if v["request_filters"]:
						if len(v["request_filters"]) == 1:
							name = v["request_filters"][0]["name"]
							if name == "electric-engine-unit":
								v["request_filters"][0]["name"] = recipe
							elif name == "lubricant-barrel":
								v["request_filters"][0]["name"] = "sulfuric-acid-barrel"
					else:
						v["request_filters"] = [ {"index": i, "name": v, "count": (48//len(solid_ingredients))*get_stack_size(recipe)} for i in solid_ingredients]
				elif "assembling-machine" in v["name"]:
					v["recipe"] == (v["recipe"] == "electric-engine-unit")*"processing-unit"+(v["recipe"] == "empty-lubricant-barrel")*"empty-sulfuric-acid-barrel"
			blueprint_copy["blueprint"]["entities"][i] = v

	elif production_type != "": # i.e. chemical plant production
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
			if v["name"] == "logistic-chest-requester":
				if len(v["request_filters"]) == 1 and v["request_filters"][0]["name"] == "iron-gear-wheel":

					v["request_filters"] = [{"index":1, "name": recipe, "count": 48*get_stack_size(recipe)}]
				else:
					v["request_filters"] = make_request_filters(recipe)

			elif  "assembling-machine" in v["name"]:
				if "plate" in recipe:
					v["name"] = "electric-furnace"
				v["recipe"] = recipe


			# elif v["name"] == "train-stop"
			blueprint_copy["blueprint"]["entities"][i] = v

	#change the names of stations
	current_station_product = get_station_type(blueprint_copy)
	ingredient_count = 0
	for i,v in enumerate(blueprint["blueprint"]["entities"]):
		if v["name"] == "train-stop":
			if "shipping" in v["station"] or "coal" in v["station"]:
				v["station"] = v["station"].replace(current_station_product,recipe)
			elif "receiving" in v["station"]:
				current_ingredient = ingredients[ingredient_count]
				three_spots = "3 spots" in v["station"]
				if is_fluid(current_ingredient):
					v["station"] = f"{recipe} receiving {current_ingredient}-barrel"
				else:
					v["station"] = f"{recipe} receiving {current_ingredient}"
				if three_spots:
					v["station"]+=" 3 spots"
				ingredient_count += 1
				ingredient_count = ingredient_count%len(ingredients)
		elif v["name"] in ["assembling-machine-3","electric-furnace","chemical-plant","oil-refinery"]:
			item_number_dictionary = { "assembling-machine-3":4, "chemical-plant":3, "electric-furnace":2, "oil-refinery":3}
			items_number = item_number_dictionary[v["name"]]
			v["items"] = {"speed-module":items_number}

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

#actual input will be blueprint["bluperint"]["entities"]
def zero_out_x_y_coordinates(blueprint):
	min_x = min([int(v["position"]["x"]) for i,v in enumerate(blueprint["blueprint"]["entities"])])
	min_y = min([int(v["position"]["y"]) for i,v in enumerate(blueprint["blueprint"]["entities"])])
	# min_x,min_y = int(min_x), int(min_y)
	blueprint_copy = copy.deepcopy(blueprint)

	for i,v in enumerate(blueprint_copy["blueprint"]["entities"]):
		v["position"]["x"] -= min_x - ( v["name"] == "curved-rail")
		v["position"]["y"] -= min_y - ( v["name"] == "curved-rail")
		blueprint_copy[i] =v
	return blueprint_copy

def make_station(product):
	blueprint = get_template_for_assembling_machines_or_smelters()
	production_type = get_production_type(product)
	production_types = ["chemical_plant_fluids_from_two_fluids", "chemical_plant_solids_from_two_fluids", 
						"chemical_plant_fluids_from_one_fluid", "chemical_plant_solids_from_one_fluid", 
						"assembling-machine-with-one-fluid", "assembling-machine or smelter"]
	chemical_production_types = production_types[:4]

	# if production_type == "chemical_plant_fluids_from_one_fluid":
	if production_type in chemical_production_types:
		blueprint =  convert_assembling_recipe(blueprint,product,production_type)
	elif product == "processing-unit" or product == "electric-engine-unit":
		with open("blueprints\\electric_engine_unit.json") as f:
			blueprint = convert_assembling_recipe(json.loads(f.read()),product)

	elif production_type == "assembling-machine or smelter":
		blueprint =  convert_assembling_recipe(blueprint,product)
	blueprint = zero_out_x_y_coordinates(blueprint)

	return ( blueprint)
def get_train_stops(blueprint):
	train_stops = defaultdict(int)
	for i,v in enumerate(blueprint["blueprint"]["entities"]):
		if v["name"] == "train-stop":
			if "sulfur" in v["station"]:
				print(v["station"])
			train_stops[v["station"]] += 1
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

def find_extreme_intersections(blueprint):
	train_coordinates = {1:[], 2:[]}
	for i,v in enumerate(blueprint["blueprint"]["entities"]):
		if v["name"] == "straight-rail":
			train_coordinates[2*("direction" in v)+1*(not "direction" in v)].append([v["position"]["x"],v["position"]["y"]])
	#get intersections
	intersections = []
	for coordinate in train_coordinates[1]:
		if coordinate in train_coordinates[2]:
			intersections.append(coordinate)
	intersections.sort()
	return intersections[0],intersections[-1]


def add_extended_extreme_intersections(blueprint):
	pass
	# extreme_intersections = find_extreme_intersections(blueprint)
	# for intersection in extreme_intersections:

def get_all_station_names(blueprint):

	stations = defaultdict(int)
	for i,v in enumerate(blueprint["blueprint"]["entities"]):
		if v["name"] == "train-stop":
			stations[v["station"]] +=1
	return stations
def get_all_station_names_from_file():
	with open("blueprints\\all_stations.json") as f:
		return json.loads(f.read())
def makeArray(recipe):
	with open("blueprints\\station_of_only_roboports.json") as f:
		robo_station = json.loads(f.read())
	station_width,station_height = get_station_dimensions()
	station_height +=2
	# print(get_station_dimensions())
	station_offset = 5
	# station_width,station_height = station_width-station_offset,station_height-station_offset
	# station_height += 2
	total_blueprint= {}
	material_dictionary = get_non_raw_materials_from_material_heirarchy(makeMaterialHeirarchy(recipe))
	blueprints = []
	for key in material_dictionary:
		blueprints.extend([key]*int(material_dictionary[key]))

	total_number_of_stations = sum(material_dictionary.values())
	stations_high,stations_long = [int(math.sqrt(total_number_of_stations)),int(total_number_of_stations//int(math.sqrt(total_number_of_stations)))]
	rail_offset = 1
	print(*blueprints,sep="\n")
	for i in range(stations_high):
		for j in range(stations_long):
			current_station = zero_out_x_y_coordinates(robo_station)
			if current_station:
				if total_blueprint == {}:
					total_blueprint = current_station
				else:
					num_entities = len(total_blueprint["blueprint"]["entities"])
					for k,v in enumerate(current_station["blueprint"]["entities"]):
						v_copy = copy.deepcopy(v)

						v_copy["entity_number"] = v["entity_number"]+num_entities
						v_copy["position"]["x"] += j*station_width
						v_copy["position"]["y"] += i*station_height*2
						if v_copy["name"] == "curved-rail":
							v_copy["position"]["x"] += rail_offset
						if v_copy["name"] == "straight-rail":
							if "direction" in v_copy:
								v_copy["position"]["x"] += rail_offset*((v["direction"]%2 == 0)*-1 + (v["direction"]%2 == 0)*1)
						total_blueprint["blueprint"]["entities"].append(v_copy)

		for j in range(stations_long):
			next_station = False
			if blueprints[0] == "sulfur":
				next_station = True
			current_station = make_station(blueprints.pop(0))
			if next_station:
				print("next_station")
				with open("blueprints\\new_sulfur_station.json") as f:
					f.write(json.dumps(current_station,indent=2))
			if current_station:
				if total_blueprint == {}:
					total_blueprint = current_station
				else:
					num_entities = len(total_blueprint["blueprint"]["entities"])
					for k,v in enumerate(current_station["blueprint"]["entities"]):
						if next_station:
							print(v)
						v_copy = copy.deepcopy(v)
						if v_copy["name"] == "train-stop" and "sulfur" in v["station"]:
							print(v_copy,' = v copy')
						v_copy["entity_number"] = v["entity_number"]+num_entities
						v_copy["position"]["x"] += j*station_width
						v_copy["position"]["y"] += (2*i+1)*station_height
						if v_copy["name"] == "curved-rail":
							v_copy["position"]["x"] += rail_offset
						if v_copy["name"] == "straight-rail":
							if "direction" in v_copy:
								v_copy["position"]["x"] += rail_offset*((v["direction"]%2 == 0)*-1 + (v["direction"]%2 == 0)*1)
						total_blueprint["blueprint"]["entities"].append(v_copy)

	return (total_blueprint) 

def make_train_schedules(blueprint,heirarchy_dictionary):
	schedules = []
	char_index = ord('a')
	three_wagon_train = False
	three_spots = False
	for i,v in enumerate(blueprint["blueprint"]["entities"]):
		if v["name"] == "locomotive":
			
			schedules.append({"locomotives":[v["entity_number"]], "schedule":[{"station":chr(char_index)}]})
			char_index +=1
			three_spots = True*(three_spots == False)
	blueprint["blueprint"]["schedules"] = schedules
	return blueprint
def make_schedule(origin, destination, entity_number):
	return {"locomotives":[entity_number],"schedule":[{"station":origin,"wait_conditions":[{"compare_type":"or","type":"full"}]}, {"station":destination,"wait_conditions":[{"compare_type":"or","type":"empty"}]}]}

with open("blueprints\\newer_sulfur.json","w+") as f:
	f.write(json.dumps(make_station('sulfur'),indent=2))
with open("blueprints\\total_blueprint.json","w+") as f:
	f.write(json.dumps(makeArray('speed-module'),indent=2))
# with open("blueprints\\all_stations.json","w+") as f:
# 	f.write(json.dumps(get_train_stops(makeArray("speed-module")),indent=2))
# # def make_product_ingredient_amounts(final_product):
# 	product_ingredient_amount_dictionary = {}
# 	heirarchy = makeMaterialHeirarchy(final_product)
# 	def traverse_dictionary(current_chunk):
# 		parent_material = [i for i in current_chunk.keys()][0]
# 		parent_amount = current_chunk[parent_material]["amount"]
# 		nonlocal product_ingredient_amount_dictionary
# 		ephemeral_dictionary = {}
# 		for ingredient in current_chunk[parent_material]["ingredients"]:
# 			subdict_by_ingredient = current_chunk[parent_material]["ingredients"][ingredient]
# 			ephemeral_dictionary[parent_material]  = {ingredient:subdict_by_ingredient["amount"]*parent_amount}
# 			print(json.dumps(ephemeral_dictionary,indent=2))
# 			for key in ephemeral_dictionary:
# 				subdict = ephemeral_dictionary[key]
# 				for subkey in subdict:
# 					if subkey in product_ingredient_amount_dictionary
# 				if key in product_ingredient_amount_dictionary:
# 					product_ingredient_amount_dictionary[key].update(subdict)
# 				else:
# 					product_ingredient_amount_dictionary[key] = subdict
# 			if ingredient not in raw_materials:
# 				traverse_dictionary({ingredient: current_chunk[parent_material]["ingredients"][ingredient]})

# 	traverse_dictionary(heirarchy)
# 	return product_ingredient_amount_dictionary


		
# print(make_product_ingredient_amounts("speed-module"))
# def enough_train_stops_check(heirarchy):
# 	train_stops = get_all_station_names_from_file()
# 	def recursively_iterate_thru_heirarchy(current_chunk_of_heirarchical_dictionary):


#so the next question is do the number of stations, i.e. receiving and shipping
#correspond to the material_dictionary?

# with open("blueprints\\plastic_bar.json","w+") as f:
# 	f.write(json.dumps(make_station("plastic-bar"),indent=2))
# with open("blueprints\\new_sulfur_station.json","w+") as f:
# 	f.write(json.dumps(neighbourify_medium_electric_poles(make_station("sulfur"),4),indent=2))

# with open("blueprints\\station_of_only_roboports.json") as f:
# 	pyperclip.copy(convertoToBlueprint(json.loads(f.read())))
# pyperclip.copy(convertoToBlueprint(make_station("sulfuric-acid")))
# pyperclip.copy(convertoToBlueprint(makeArray("speed-module")))
# def get_all_inidividual_items_from_blueprint(blueprints):
# 	items = set()
# 	if not isinstance(blueprints, list):
# 		blueprints = [blueprints]

# 	for blueprint in blueprints:
# 		items = set()
# 		for i,v in enumerate(blueprint["blueprint"]["entities"]):
# 			items.add(v["name"])
# 	return items

# train_depot = "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"
# writeJsonFile("train_depot",train_depot)
# with open("blueprints\\train_depot.json") as f:
# 	new_bluperint = make_train_schedules(json.loads(f.read()))
# 	with open("blueprints\\train_depot_with_schedules.json","w+") as g:
# 		g.write(json.dumps(new_bluperint,indent =2))
# 	pyperclip.copy(convertoToBlueprint(new_bluperint))			

# with open("blueprints\\generated_iron_plate_station.json") as f:
# 	pyperclip.copy(convertoToBlueprint(neighbourify_medium_electric_poles(json.loads(f.read()))))

# print(json.dumps(make_station("electronic-circuit"),indent=2))
# print(get_station_type(convert_assembling_recipe(get_template_for_assembling_machines_or_smelters(),"speed-module-3")))
# pyperclip.copy(convertoToBlueprint(makeArray("assembling-machine-3")))
# pyperclip.copy(convertoToBlueprint(makeArray("advanced-circuit")))
# with open("blueprints\\speed_module_array.json") as f:
# 	stops =  "\n".join(get_all_station_names(json.loads(f.read())))
# 	with open("stops","w+") as g:
# 			g.writelines(stops)
# with open("blueprints\\test.json","w+") as f:
# 	f.write(json.dumps(get_template_for_assembling_machines_or_smelters(),indent=2))
# 	pyperclip.copy(convertoToBlueprint(make_station("iron-gear-wheel")))
# pyperclip.copy(convertoToBlueprint(get_template_for_assembling_machines_or_smelters()))
# with open("blueprints\\electric_engine_unit.json") as f:
# 	blueprint = json.loads(f.read())
# pyperclip.copy(convertoToBlueprint(make_station("iron-gear-wheel")))
# pyperclip.cops(convertoToBlueprint(make_repository("heavy-oil-barrel")))

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