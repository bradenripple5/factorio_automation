import json, os, sys, math, pathlib, math, numpy
from slpp import slpp as lua
from collections import defaultdict
from fraction import Fraction
def convertPathForOs(path):
	if sys.platform != "windows":
		return str(pathlib.PurePosixPath(path))
	else:
		return str(pathlib.PureWindowsPath(path))
# import json

def _strip_lua_comments(s):
	out = []
	i = 0
	in_string = None
	in_long_comment = False
	while i < len(s):
		ch = s[i]
		nxt = s[i+1] if i + 1 < len(s) else ""

		if in_long_comment:
			if ch == "]" and nxt == "]":
				in_long_comment = False
				i += 2
				continue
			i += 1
			continue

		if in_string:
			out.append(ch)
			if ch == "\\":
				if i + 1 < len(s):
					out.append(s[i+1])
					i += 2
					continue
			elif ch == in_string:
				in_string = None
			i += 1
			continue

		if ch in ["'", '"']:
			in_string = ch
			out.append(ch)
			i += 1
			continue

		if ch == "-" and nxt == "-":
			third = s[i+2] if i + 2 < len(s) else ""
			fourth = s[i+3] if i + 3 < len(s) else ""
			if third == "[" and fourth == "[":
				in_long_comment = True
				i += 4
				continue
			while i < len(s) and s[i] != "\n":
				i += 1
			continue

		out.append(ch)
		i += 1
	return "".join(out)

def _extract_data_extend_tables(s):
	clean = _strip_lua_comments(s)
	tables = []
	search = 0
	while True:
		idx = clean.find("data:extend", search)
		if idx == -1:
			break
		start = clean.find("(", idx)
		if start == -1:
			break
		i = start + 1
		depth = 1
		in_string = None
		while i < len(clean) and depth > 0:
			ch = clean[i]
			if in_string:
				if ch == "\\":
					i += 2
					continue
				if ch == in_string:
					in_string = None
				i += 1
				continue
			if ch in ["'", '"']:
				in_string = ch
				i += 1
				continue
			if ch == "(":
				depth += 1
			elif ch == ")":
				depth -= 1
			i += 1
		end = i - 1
		if depth == 0:
			tables.append(clean[start + 1:end].strip())
		search = i
	return tables

def _decode_data_extend_list(s):
	results = []
	for table_str in _extract_data_extend_tables(s):
		try:
			decoded = lua.decode(table_str)
		except Exception:
			continue
		if isinstance(decoded, list):
			results.extend(decoded)
		else:
			results.append(decoded)
	return results

FAC_HOME = os.getenv("FACTORIO_HOME")
if not FAC_HOME:
	raise RuntimeError("FACTORIO_HOME is not set; please point it to the Factorio install directory.")

def resolve_recipe_sources(fac_home):
	proto_home = pathlib.Path(fac_home) / "data" / "base" / "prototypes"
	recipe_dir_candidates = [proto_home / "recipe", proto_home / "recipes"]
	recipe_paths = []
	recipe_home = None

	for d in recipe_dir_candidates:
		if d.is_dir():
			recipe_home = d
			recipe_paths.extend([d / f for f in os.listdir(d)])

	if not recipe_paths and proto_home.is_dir():
		# Newer versions may keep recipe files directly under prototypes.
		recipe_home = proto_home
		recipe_paths.extend(sorted(proto_home.glob("*recipe*.lua")))

	# Ensure these are included if present.
	recipe_paths.extend([
		proto_home / "recipe.lua",
		proto_home / "recipe" / "recipe.lua",
	])

	seen = set()
	unique_paths = []
	for p in recipe_paths:
		p = pathlib.Path(p)
		if not p.is_file():
			continue
		if p in seen:
			continue
		seen.add(p)
		unique_paths.append(p)

	return recipe_home, unique_paths, proto_home

RECIPE_HOME, recipe_paths, PROTOTYPE_HOME = resolve_recipe_sources(FAC_HOME)
print(convertPathForOs(str(RECIPE_HOME)), " = recipe home")

def resolve_item_sources(proto_home):
	item_dir_candidates = [proto_home / "item", proto_home / "items"]
	for d in item_dir_candidates:
		if d.is_dir():
			return d, [d / f for f in os.listdir(d)]

	item_lua = proto_home / "item.lua"
	if item_lua.is_file():
		return proto_home, [item_lua]

	# Last resort: include any file that looks like it defines items.
	globbed = sorted(proto_home.glob("item*.lua"))
	if globbed:
		return proto_home, globbed

	raise RuntimeError(f"Could not find items directory or item.lua under {proto_home}")

ITEMS_HOME, item_paths = resolve_item_sources(PROTOTYPE_HOME)
fluids = []
recipes_dict = {}
recipes_list = []
smelted_list = set()
#a station needs to be created for each scenario
chemical_plant_products_from_two_fluids = ["sulfur","light-oil","petroleum-gas"]
chemical_plant_fluids_from_two_fluids = ["light-oil","petroleum-gas"]
chemical_plant_solids_from_two_fluids = ["sulfur"]
chemical_plant_products_from_one_fluid = ["sulfuric-acid","solid-fuel","plastic-bar","lubricant","battery","explosives"]
chemical_plant_fluids_from_one_fluid = ["sulfuric-acid","lubricant"]
chemical_plant_solids_from_one_fluid = ["solid-fuel","plastic-bar","lubricant","battery","explosives","processing-unit"]
raw_materials = ["wood","petroleum-gas","raw-fish","water","crude-oil","coal","stone","copper-ore","iron-ore","water","light-oil","heavy-oil","petroleum-gas"]


demo_furnace_path = pathlib.Path(RECIPE_HOME) / "demo-furnace-recipe.lua"
if not demo_furnace_path.is_file():
	alt_demo = PROTOTYPE_HOME / "recipe" / "demo-furnace-recipe.lua"
	if alt_demo.is_file():
		demo_furnace_path = alt_demo

# In Factorio 2.0, demo-furnace-recipe.lua may not exist. If missing, skip smelted_list bootstrap.
if demo_furnace_path.is_file():
	with open(demo_furnace_path) as f:
		s = f.read()
		list_of_recipes = _decode_data_extend_list(s)
		# print(json.dumps(list_of_recipes,indent=2))
		for index,item in enumerate(list_of_recipes[:]):
			if isinstance(item,dict):
				if "name" in item:
					smelted_list.add(item["name"])

RECIPE_LUA_FILE_HOME = pathlib.Path(FAC_HOME) / "data" / "base" / "prototypes" / "recipe" / "recipe.lua"
OTHER_RECIPE_LUA_FILE_HOME = pathlib.Path(FAC_HOME) / "data" / "base" / "prototypes" / "recipe.lua"

for file in recipe_paths:
	with open(file) as f:
		s = f.read()
		# print(s)

	if "data:extend" not in s:
		continue

	list_of_recipes = _decode_data_extend_list(s)
	for index,recipe in enumerate(list_of_recipes[:]):

		recipes_list.append(recipe)
		if isinstance(recipe,dict):
			if "name" in recipe:
				if pathlib.Path(file).name == "demo-recipe.lua":
					recipe["energy_required"] = 0.5
				recipes_dict[recipe["name"]] = recipe




list_of_recipes = _decode_data_extend_list(s)
# if OTHER_RECIPE_LUA_FILE_HOME == file:
# 	print(list_of_recipes, " = stripped_string")
for index,recipe in enumerate(list_of_recipes[:]):
	recipes_list.append(recipe)
	if isinstance(recipe,dict):
		if "name" in recipe:
			recipes_dict[recipe["name"]] = recipe

items_dict = {}
for file in item_paths:
	with open(file) as f:
		s = f.read()
	lines = s.split("\n")
	if pathlib.Path(file).name != "demo-crash-site-item.lua":
		lines = s.split("\n")
		if "require" in lines[0]:
			s = "\n".join(lines[1:])
		list_of_recipes = _decode_data_extend_list(s)
		# print(json.dumps(list_of_recipes,indent=2))
		for index,item in enumerate(list_of_recipes[:]):

			if isinstance(item,dict):
				if "name" in item and item["type"] not in ["item-subgroup","item-group"]:
					items_dict[item["name"]] = item

def get_energy(item):
	try:
		return recipes_dict[item]["expensive"]["energy_required"]
	except:
		try:
			return recipes_dict[item]["energy_required"]
		except:
			return 1
def is_smelted(item):
	return item in smelted_list


#i.e. the amount of items that can fit into one square of a chest.
def get_fluids():
	fluids = set()
	fluid_recipe_path = pathlib.Path(RECIPE_HOME) / "fluid-recipe.lua"
	if not fluid_recipe_path.is_file():
		alt_fluid_recipe = PROTOTYPE_HOME / "fluid-recipe.lua"
		fluid_recipe_path = alt_fluid_recipe if alt_fluid_recipe.is_file() else fluid_recipe_path
	if fluid_recipe_path.is_file():
		with open(fluid_recipe_path) as f:
			s = f.read()
		list_of_recipes = _decode_data_extend_list(s)
		# print(json.dumps(list_of_recipes,indent=2))
		for index,recipe in enumerate(list_of_recipes[:]):
			if isinstance(recipe,dict):
				for key in ["results","ingredients"]:
					if key in recipe:
						for i in recipe[key]:
							if i["type"] == "fluid":
								fluids.add(i["name"])

	# Factorio 2.0 has fluid definitions in fluid.lua
	fluid_defs_path = PROTOTYPE_HOME / "fluid.lua"
	if fluid_defs_path.is_file():
		with open(fluid_defs_path) as f:
			s = f.read()
		list_of_fluids = _decode_data_extend_list(s)
		for index,fluid in enumerate(list_of_fluids[:]):
			if isinstance(fluid,dict) and "name" in fluid:
				fluids.add(fluid["name"])
	return fluids
fluids = get_fluids()
for fluid in fluids:
	recipes_dict["fill-"+fluid+"-barrel"] = {"ingredients": [["empty-barrel",1]]}
	recipes_dict["empty-"+fluid+"-barrel"] ={"ingredients": [[fluid+"-barrel",1]]}


def is_fluid(product):
	return product in fluids
def get_stack_size(item):
	if "module" in item:
		return 50
	if "barrel" in item:
		item = "empty-barrel"
	if item in fluids:
		return 10
	if item not in items_dict:
		return None
	fullinfo = items_dict[item]
	return fullinfo["stack_size"]
	# if "normal" in fullinfo:
	# 	ingredients = fullinfo["normal"]["ingredients"]
	# else:
	# 	ingredients = fullinfo["ingredients"]
	# return [i[0] if isinstance(i,list) else i["name"] for i in ingredients]print(get_recipe("plastic-bar"))

def getMaterialHeirarchy(item):
	non_addables = []
	material_dict = defaultdict(int)
	def get_ingredients(prod, amount = 1):
		ingredients = recipes_dict[prod]["expensive"]["ingredients"] if "expensive" in recipes_dict[prod] else recipes_dict[prod]["ingredients"]
		for ingredient in ingredients:
			if isinstance(ingredient, dict):
				material_dict[ingredient["name"]] += ingredient["amount"]
			else:
				material_dict[ingredient[0]] += ingredient[1]*amount
		for ingredient in ingredients:

			if isinstance(ingredient,dict):
				name,amount = ingredient["name"],ingredient["amount"]
			else:
				name,amount = ingredient[:2]

			if "ore" not in name and name not in ["wood","petroleum-gas","raw-fish","water","crude-oil","coal","stone"]:
					try:
						get_ingredients(name,amount)
					except:
						non_addables.append(name)

		
	get_ingredients(item)
	if non_addables:
		print(non_addables, ' = non_addables')
	return dict(material_dict)
#i.e. where the product is produced, in a smelter, assembling-machine, or a chemical-plant, or a centrifuge, refinery here not included
def get_production_time(product):

	try:
		return recipes_dict[product]["expensive"]["energy_required"]
	except:

		try:
			return recipes_dict[product]["energy_required"]
		except:
			return 1

def get_production_type(product):
	try:
		if product == "processing-unit":
			return "processing-unit"
		if product in chemical_plant_fluids_from_two_fluids:
			return "chemical_plant_fluids_from_two_fluids"
		if product in chemical_plant_solids_from_two_fluids:
			return "chemical_plant_solids_from_two_fluids"
		if product in chemical_plant_fluids_from_one_fluid:
			return "chemical_plant_fluids_from_one_fluid"
		elif product in chemical_plant_solids_from_one_fluid:
			return "chemical_plant_solids_from_one_fluid"
		# recipe = get_recipe(product)
		# for i in recipe:
		# 	if i in chemical_plant_products_from_one_fluid+chemical_plant_products_from_one_fluid:
		# 		return "assembling-machine-with-one-fluid"
		return "assembling-machine or smelter"
	except:
		return "must be crude-oil or some type of ore"


def makeMaterialHeirarchy(item,amount = 1):
	total = 0

	def makeMaterialHeirarchyRecursive(item,amount=1):
		nonlocal total
		if any([i in item for i in ["coal","gas","ore","water","oil","stone"]]):
				return None

		return_dict = {}
		ingredients =  recipes_dict[item]["expensive"]["ingredients"] if "expensive" in recipes_dict[item] else recipes_dict[item]["ingredients"]
		new_ingredients = []
		for i in ingredients:
			if isinstance(i,dict):
				if "name" in i and "amount" in i:
					new_ingredients.append([i["name"],i["amount"]])
			else:
				new_ingredients.append(i)		
		ingredients = new_ingredients
		for ingredient in ingredients:
			ingredient_name = ingredient[0]
			ingredient_amount = ingredient[1]
			time_ratio = get_production_time(ingredient_name)/get_production_time(item)
			amount_for_ingredient = amount*ingredient_amount*time_ratio
			total+=amount_for_ingredient
			return_dict[ingredient_name] = { "amount": amount_for_ingredient, "ingredients": makeMaterialHeirarchyRecursive(ingredient_name,amount_for_ingredient) }
		return return_dict
		if "gas" in item or "water" in item or "raw-fish" in item:
			return {item: {"amount": 1}}

	ingredients_dictionary = makeMaterialHeirarchyRecursive(item,amount)
	# print(item,total)
	return {item: {"amount": amount, "ingredients": ingredients_dictionary}}

def makeTrainSchedules(material_heirarchy):
	train_schedules = defaultdict(int)

	def rec(m,parent_station):
		nonlocal train_schedules
		if "ingredients" in m:
			if m["ingredients"] != None:

				for i in m["ingredients"]:
					
					if i in train_schedules:
						train_schedules[i]+=m["amount"]
					else:
						train_schedules[i]=m["amount"]
					rec(m["ingredients"][i],parent_station)
		else:
			rec(m[first_element],parent_station)

	rec(material_heirarchy)
	return train_schedules

def get_non_raw_materials_from_material_heirarchy(material_heirarchy):
	total_materials = defaultdict(int)
	def recurse(sub_heirarchy):
		nonlocal total_materials
		for item in sub_heirarchy:
			if item not in raw_materials:
				total_materials[item]+=sub_heirarchy[item]["amount"]
				if sub_heirarchy[item]["ingredients"] != None:
					recurse(sub_heirarchy[item]["ingredients"])
	recurse(material_heirarchy)
	return {i:numpy.round(v) for i,v in dict(sorted(total_materials.items(),key = lambda item:item[0])).items()}

RECIPE_ALIASES = {
	"wall": "stone-wall",
}

def resolve_recipe_name(product):
	"""
	Return a canonical recipe key from user-facing shorthand.
	"""
	if product in recipes_dict:
		return product
	return RECIPE_ALIASES.get(product)

def get_recipe(product):
	product = resolve_recipe_name(product)
	if product is None:
		return None
	fullinfo = recipes_dict[product]
	# print(fullinfo,"fullinfo")
	if "normal" in fullinfo:
		ingredients = fullinfo["normal"]["ingredients"]
	else:
		ingredients = fullinfo["ingredients"]
	# print(f"fullinfo = {json.dumps(fullinfo,indent=2)}")
	return [i[0] if isinstance(i,list) else i["name"] for i in ingredients]

def make_request_filters(product,fluid_only = False):
	# print(product, "make_request_filters")
	# print(recipes_dict[product])
	ingredients = get_recipe(product)

	stack_sizes = {}
	request_filters =[]
	for index, ingredient in enumerate(ingredients):
		# print(ingredient)
		try:
			if ingredient in fluids:
				request_filters.append({ "index":index+1,"name":ingredient+"-barrel", "count": int(get_stack_size(ingredient)*(48/len(ingredients)))})
			else:	
				request_filters.append({ "index":index+1,"name":ingredient+"-barrel"*(ingredient in fluids), "count": int(get_stack_size(ingredient)*(48/len(ingredients)))})
		except:
			print(f"cannot add {ingredient} to logistics request chest")
	return request_filters

import numpy as np

def make_inserter_sequence(product, max_val=3):
	data = {k["name"]:k["count"] for k in make_request_filters(product) if "barrel" not in  k["name"] }

	# print(data)
	if data == {}:
		return None
	values = list(data.values())
	# print([type(i) for i in values])
	minval = min(values)

	for i in [j for j in range(max_val,0,-1)]+[j for j in range(max_val,25)]:
		candidate  = [int(p) for p in list(np.array([(k/minval)*i for k in values ]))]

		factor = minval//i
		factored_back_in = [int(b) for b in list(np.array(candidate)*factor)]
		# print(candidate,factor,list(np.array(candidate)*factor),values)
		# print([type(b) for b in factored_back_in])
		if all( [factored_back_in[r] == values[r] for r in range(len(factored_back_in))]):
			keys = [k for k in data.keys()]
			return { keys[k]:candidate[k] for k in range(len(keys))}
	



# print([i for i in recipes_dict if "belt" in i])
# print(make_request_filters("advanced-circuit"))
#the next step is to match physical trains with schedules

# print(is_smelted("copper-plate"))
# with open("speed-module-heirarchy.json", "w+") as f:
# 	f.write(json.dumps(makeMaterialHeirarchy("speed-module"),indent=2))
# print(makeTrainSchedules(makeMaterialHeirarchy("speed-module")))
# print(get_non_raw_materials_from_material_heirarchy(makeMaterialHeirarchy("speed-module")))
# print(make_request_filters("processing-unit"))
# print(get_recipe("processing-unit"))
# print([i for i in get_recipe("processing-unit") if is_fluid(i)])
# categories = set()
# recipes_dict["raw-fish"] = {"name":"raw-fish","energy_required":1, "ingredients":[]}
# for i in recipes_dict:
# 	if "category" in recipes_dict[i]:
# 		categories.add(recipes_dict[i]["category"])
# print(categories)
# print(recipes_dict["spidertron"])

# for key in recipes_dict:
# 	if "science" in key:
# 		print(key)
# items = ["military-science-pack","rocket-control-unit","spidertron"]#"advanced-circuit"]#,"roboport","rocket-control-unit","low-density-structure","satellite"]
# items = [i for i in recipes_dict if "science" in i] + items
# for item in items:
# 	with open(convertPathForOs(f"recipes/{item}.json"), "w+") as f:
# 		f.write(json.dumps(makeMaterialHeirarchy(item,1),indent=2))
