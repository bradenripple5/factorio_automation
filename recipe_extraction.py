import json
import os
import pathlib
import subprocess
import tempfile

import numpy
from collections import defaultdict


def convertPathForOs(path):
	return os.path.normpath(path)

FAC_HOME = os.getenv("FACTORIO_HOME")
if not FAC_HOME and os.name == "nt":
	FAC_HOME = r"C:\Program Files\Factorio"
if not FAC_HOME:
	raise RuntimeError("Set FACTORIO_HOME to the Factorio installation directory.")

FACTORIO_HOME = pathlib.Path(FAC_HOME).expanduser().resolve()
RECIPE_HOME = FACTORIO_HOME / "data" / "base" / "prototypes" / "recipe.lua"
FACTORIO_EXE = FACTORIO_HOME / "bin" / "x64" / "factorio.exe"


def _load_factorio_prototypes():
	"""Load Factorio's evaluated data.raw instead of trying to parse executable Lua."""
	if not RECIPE_HOME.is_file():
		raise FileNotFoundError(f"Factorio 2.0 recipe file was not found: {RECIPE_HOME}")
	if not FACTORIO_EXE.is_file():
		raise FileNotFoundError(f"Factorio executable was not found: {FACTORIO_EXE}")

	cache_root = pathlib.Path(tempfile.gettempdir()) / "factorio-software-automation"
	write_data = cache_root / "factorio-data"
	dump_file = write_data / "script-output" / "data-raw-dump.json"
	config_file = cache_root / "config.ini"
	cache_root.mkdir(parents=True, exist_ok=True)

	# Refresh after Factorio or its base recipe definitions are updated.
	source_mtime = max(FACTORIO_EXE.stat().st_mtime, RECIPE_HOME.stat().st_mtime)
	if not dump_file.is_file() or dump_file.stat().st_mtime < source_mtime:
		config_file.write_text(
			"[path]\n"
			f"read-data={FACTORIO_HOME.joinpath('data').as_posix()}\n"
			f"write-data={write_data.as_posix()}\n\n"
			"[general]\nlocale=en\n",
			encoding="utf-8",
		)
		result = subprocess.run(
			[str(FACTORIO_EXE), "--config", str(config_file), "--dump-data"],
			capture_output=True,
			text=True,
		)
		if result.returncode != 0 or not dump_file.is_file():
			details = (result.stderr or result.stdout).strip()
			raise RuntimeError(f"Factorio could not dump prototype data: {details}")

	with dump_file.open(encoding="utf-8") as f:
		return json.load(f)


prototype_data = _load_factorio_prototypes()
recipes_dict = {
	name: recipe
	for name, recipe in prototype_data.get("recipe", {}).items()
	# Parameter and unknown prototypes are editor internals, not craftable recipes.
	if isinstance(recipe.get("ingredients"), list)
}
recipes_list = list(recipes_dict.values())
fluids = set(prototype_data.get("fluid", {}))
smelted_list = {
	name for name, recipe in recipes_dict.items()
	if recipe.get("category") == "smelting"
}

# Stackable prototypes are spread across item, ammo, module, armor, and other
# prototype groups in Factorio 2.0, so collect them by capability.
items_dict = {}
for prototype_group in prototype_data.values():
	if not isinstance(prototype_group, dict):
		continue
	for name, prototype in prototype_group.items():
		if isinstance(prototype, dict) and "stack_size" in prototype:
			items_dict[name] = prototype

print(f"Loaded {len(recipes_dict)} Factorio recipes from {RECIPE_HOME}")

#a station needs to be created for each scenario
chemical_plant_products_from_two_fluids = ["sulfur","light-oil","petroleum-gas"]
chemical_plant_fluids_from_two_fluids = ["light-oil","petroleum-gas"]
chemical_plant_solids_from_two_fluids = ["sulfur"]
chemical_plant_products_from_one_fluid = ["sulfuric-acid","solid-fuel","plastic-bar","lubricant","battery","explosives"]
chemical_plant_fluids_from_one_fluid = ["sulfuric-acid","lubricant"]
chemical_plant_solids_from_one_fluid = ["solid-fuel","plastic-bar","lubricant","battery","explosives","processing-unit"]
raw_materials = ["wood","petroleum-gas","raw-fish","water","crude-oil","coal","stone","copper-ore","iron-ore","water","light-oil","heavy-oil","petroleum-gas"]

ASSEMBLER_RECIPE_CATEGORIES = {"crafting", "advanced-crafting", "crafting-with-fluid"}
CHEMICAL_PLANT_RECIPE_CATEGORIES = {"chemistry"}
FURNACE_RECIPE_CATEGORIES = {"smelting"}


def get_recipe_machine(product):
	"""Return the machine for a supported recipe, or None if this layout cannot produce it."""
	recipe_name = resolve_recipe_name(product)
	if recipe_name is None:
		return None
	category = recipes_dict[recipe_name].get("category", "crafting")
	if category in ASSEMBLER_RECIPE_CATEGORIES:
		return "assembling-machine-3"
	if category in CHEMICAL_PLANT_RECIPE_CATEGORIES:
		return "chemical-plant"
	if category in FURNACE_RECIPE_CATEGORIES:
		return "electric-furnace"
	return None


def can_produce_in_assembler_or_chemical_plant(product, include_furnaces=True):
	# Kept for compatibility; supported production now includes electric furnaces.
	machine = get_recipe_machine(product)
	if machine == "electric-furnace" and not include_furnaces:
		return False
	return machine is not None

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


def is_fluid(product):
	return product in fluids
def get_stack_size(item):
	# Factorio 2.0 renamed the empty-barrel item to simply "barrel".
	if item == "empty-barrel":
		item = "barrel"
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

def _expected_amount(component):
	"""Return the expected amount represented by a Factorio ingredient/result."""
	if isinstance(component, (list, tuple)):
		return component[1]
	if "amount" in component:
		amount = component["amount"]
	else:
		amount = (component.get("amount_min", 0) + component.get("amount_max", 0)) / 2
	return amount * component.get("probability", 1)


def _recipe_output_amount(recipe, product):
	"""Return how many units of product one execution of recipe produces."""
	results = recipe.get("results")
	if results:
		for result in results:
			name = result[0] if isinstance(result, (list, tuple)) else result.get("name")
			if name == product:
				return _expected_amount(result)
		return 0
	if recipe.get("result") == product:
		return recipe.get("result_count", 1)
	# Most recipes share their name with their sole product.
	return 1 if recipe.get("name", product) == product else 0


def getMaterialHeirarchy(item, amount=1):
	"""
	Return the total ingredients needed to produce ``amount`` of ``item``.

	The result includes both intermediate and raw ingredients. Quantities account
	for parent quantities, recipe yields, probabilistic results, and repeated
	materials reached through different recipe branches.
	"""
	if amount < 0:
		raise ValueError("amount must be non-negative")

	material_totals = defaultdict(float)

	def add_ingredients(product, required_amount, active_path):
		recipe_name = resolve_recipe_name(product)
		if recipe_name is None:
			return
		if recipe_name in active_path:
			cycle = " -> ".join((*active_path, recipe_name))
			raise ValueError(f"recipe cycle detected: {cycle}")

		recipe = recipes_dict[recipe_name]
		output_amount = _recipe_output_amount(recipe, product)
		if output_amount <= 0:
			raise ValueError(f"recipe {recipe_name!r} does not produce {product!r}")

		executions = required_amount / output_amount
		for ingredient in recipe.get("ingredients", []):
			name = ingredient[0] if isinstance(ingredient, (list, tuple)) else ingredient["name"]
			ingredient_amount = _expected_amount(ingredient) * executions
			material_totals[name] += ingredient_amount
			add_ingredients(name, ingredient_amount, (*active_path, recipe_name))

	add_ingredients(item, amount, ())
	return {
		name: int(quantity) if quantity.is_integer() else quantity
		for name, quantity in sorted(material_totals.items())
	}


def get_non_raw_materials_for_recipe(item, amount=1):
	"""Return required intermediate products, excluding all raw materials."""
	material_hierarchy = getMaterialHeirarchy(item, amount)
	raw_material_names = set(raw_materials)
	return {
		name: quantity
		for name, quantity in material_hierarchy.items()
		if name not in raw_material_names
	}

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
	"empty-barrel": "barrel",
}

def resolve_recipe_name(product):
	"""
	Return a canonical Factorio 2.0 recipe key from user-facing or 1.1 names.
	"""
	if product in recipes_dict:
		return product
	alias = RECIPE_ALIASES.get(product)
	if alias in recipes_dict:
		return alias

	# Factorio 1.1 called these "fill-<fluid>-barrel". Factorio 2.0 uses
	# "<fluid>-barrel" for filling and keeps "empty-<fluid>-barrel".
	if product.startswith("fill-") and product.endswith("-barrel"):
		factorio_2_name = product.removeprefix("fill-")
		if factorio_2_name in recipes_dict:
			return factorio_2_name
	return None

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

