import json, os, sys, math, pathlib
from slpp import slpp as lua
from collections import defaultdict
from fraction import Fraction
def convertPathForOs(path):
	if sys.platform != "windows":
		return str(pathlib.PurePosixPath(path))
	else:
		return str(pathlib.PureWindowsPath(path))
# import json

FAC_HOME = os.getenv("FACTORIO_HOME")
relative_recipe_string = "/data/base/prototypes/recipe"
relative_items_string = "/data/base/prototypes/item"
relative_items_string,relative_recipe_string = convertPathForOs(relative_items_string),convertPathForOs(relative_recipe_string)
RECIPE_HOME =  f"{FAC_HOME}{relative_recipe_string}"
ITEMS_HOME = FAC_HOME + relative_items_string
RECIPE_HOME, ITEMS_HOME = convertPathForOs(RECIPE_HOME),convertPathForOs(ITEMS_HOME)
recipe_files = os.listdir(RECIPE_HOME)
items_files = os.listdir(ITEMS_HOME)
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
chemical_plant_solids_from_one_fluid = ["solid-fuel","plastic-bar","lubricant","battery","explosives"]

with open(RECIPE_HOME+convertPathForOs("//demo-furnace-recipe.lua")) as f:
	s = f.read()
	stripped_string = s.strip().removeprefix("data:extend(").removesuffix(")")
	list_of_recipes =  lua.decode(stripped_string) # actually a list
	# print(json.dumps(list_of_recipes,indent=2))
	for index,item in enumerate(list_of_recipes[:]):
		if isinstance(item,dict):
			if "name" in item:
				smelted_list.add(item["name"])
RECIPE_LUA_FILE_HOME = FAC_HOME +   convertPathForOs(f"//data//base//prototypes//recipe//recipe.lua")
for file in recipe_files+[RECIPE_LUA_FILE_HOME]:
	if file == RECIPE_LUA_FILE_HOME:
		with open(file) as f:
			s = f.read()
	else:
		with open (RECIPE_HOME+"//"+file) as f:
			s = f.read()
	stripped_string = s.strip().removeprefix("data:extend(").removesuffix(")")
	list_of_recipes =  lua.decode(stripped_string) # actually a list
	# print(json.dumps(list_of_recipes,indent=2))
	for index,recipe in enumerate(list_of_recipes[:]):
		recipes_list.append(recipe)
		if isinstance(recipe,dict):
			if "name" in recipe:
				if file == "demo-recipe.lua":
					recipe["energy_required"] = 0.5
				recipes_dict[recipe["name"]] = recipe

items_dict = {}
for file in items_files:
	with open (ITEMS_HOME+convertPathForOs("/")+file) as f:
		s = f.read()
	lines = s.split("\n")
	if file != "demo-crash-site-item.lua":
		lines = s.split("\n")
		if "require" in lines[0]:
			s = "\n".join(lines[1:])
		stripped_string = s.strip().removeprefix("data:extend(").removesuffix(")")
		list_of_recipes =  lua.decode(stripped_string) # actually a list
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
def get_recipe(product):
	if product not in recipes_dict:
		return None
	fullinfo = recipes_dict[product]
	# print(fullinfo,"fullinfo")
	if "normal" in fullinfo:
		ingredients = fullinfo["normal"]["ingredients"]
	else:
		ingredients = fullinfo["ingredients"]
	return [i[0] if isinstance(i,list) else i["name"] for i in ingredients]
def make_request_filters(product):
	ingredients = get_recipe(product)
	stack_sizes = {}
	request_filters =[]
	for index, ingredient in enumerate(ingredients):
		if ingredient in fluids:
			request_filters.append({ "index":index+1,"name":ingredient+"-barrel", "count": int(get_stack_size(ingredient)*(48/len(ingredients)))})
		else:	
			request_filters.append({ "index":index+1,"name":ingredient+"-barrel"*(ingredient in fluids), "count": int(get_stack_size(ingredient)*(48/len(ingredients)))})
	return request_filters
#i.e. the amount of items that can fit into one square of a chest.
def get_fluids():
	fluids = set()
	with open(RECIPE_HOME+convertPathForOs("/")+"fluid-recipe.lua") as f:
		s = f.read()
	stripped_string = s.strip().removeprefix("data:extend(").removesuffix(")")
	list_of_recipes =  lua.decode(stripped_string) # actually a list
	# print(json.dumps(list_of_recipes,indent=2))
	for index,recipe in enumerate(list_of_recipes[:]):
		if isinstance(recipe,dict):
			for key in ["results","ingredients"]:
				if key in recipe:
					for i in recipe[key]:
						if i["type"] == "fluid":
							fluids.add(i["name"])
	return fluids
fluids = get_fluids()
for fluid in fluids:
	recipes_dict["fill-"+fluid+"-barrel"] = {"ingredients": [["empty-barrel",1]]}
	recipes_dict["empty-"+fluid+"-barrel"] ={"ingredients": [[fluid+"-barrel",1]]}
def get_stack_size(item):
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
	material_dict = defaultdict(int)
	def get_ingredients(prod, amount = 1):
		ingredients = recipes_dict[prod]["expensive"]["ingredients"] if "expensive" in recipes_dict[prod] else recipes_dict[prod]["ingredients"]
		
		for ingredient in ingredients:
			material_dict[ingredient[0]] += ingredient[1]*amount
		for ingredient in ingredients:
			if "ore" not in ingredient[0] and "ore" not in ingredient[0] and ingredient[0] not in ["wood","petroleum-gas","raw-fish","water","crude-oil","coal","stone"]:
					try:
						get_ingredients(ingredient[0],ingredient[1])
					except:
						print("non_addable", ingredient[0])
		
	get_ingredients(item)
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
	#assembling or smelter, 
		#vs assembling with liquid
		#vs chemical-plant with one liquid
		#vs chemical-plant with two liquids
		#vs, possibly a refinery
	try:
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


def getMaterialNeededAccountingForTime(item,raw_material,amount =1):
	if item == raw_material	or "ore" in item or "oil" in item:
		return amount 



	ingredients =  recipes_dict[item]["expensive"]["ingredients"] if "expensive" in recipes_dict[item] else recipes_dict[item]["ingredients"]		
	for ingredient in ingredients:
		ingredient_name = ingredient[0]
		ingredient_amount = ingredient[1]
		time_ratio = get_production_time(ingredient_name)/get_production_time(item)

		print(time_ratio, " = time_ratio for ", ingredient_name, item)
		# print("new_amount = ", amount*ingredient_amount*get_production_time(ingredient_name))
		recursive = getMaterialNeededAccountingForTime(ingredient[0], raw_material, amount*ingredient_amount*time_ratio)
		if recursive:
			return  recursive

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
	ingredients_dictionary = makeMaterialHeirarchyRecursive(item,amount)
	print(item, total)
	return {item: {"amount": amount, "ingredients": ingredients_dictionary}}

def getNestedMaterialHeirarchy(item, amount = 1):
		return_dict = {}
		try:
			ingredients =  recipes_dict[item]["expensive"]["ingredients"] if "expensive" in recipes_dict[item] else recipes_dict[item]["ingredients"]		
			if len(ingredients) > 1:
				if type(ingredients[0]) != type(ingredients[-1]):
					ingredients = ingredients[:-1]
			# for ingredient in ingredients:
			# 	if ingredient
			new_amount = 1/ (min([getNestedMaterialHeirarchy(amount*ingredient[1]*get_production_time(ingredient[0])/get_production_time(item)) for ingredient in ingredients]))
			
			amount = new_amount
			# if item == "plastic-bar":
			print(item,amount, "item, amount")
			amount = math.ceil(amount)
			return_dict["ingredients"] = [getNestedMaterialHeirarchy(ingredient[0],amount*ingredient[1]*get_production_time(ingredient[0])/get_production_time(item)) for  ingredient in ingredients]


		except Exception as e:
			return {item:amount}
		# print(new_amount,item)
		# print(amount, [amount*ingredient[1]*get_production_time(ingredient[0])/get_production_time(item) for ingredient in ingredients])
		return_dict["amount"] = amount

		return {item: return_dict}




for key in recipes_dict:
	if "science" in key:
		print(key)
items = ["science-pack-3","military-science-pack","rocket-control-unit"]#"advanced-circuit"]#,"roboport","rocket-control-unit","low-density-structure","satellite"]
items = [i for i in recipes_dict if "science" in i]
for item in items:
	with open(convertPathForOs(f"recipes/{item}.json"), "w+") as f:
		f.write(json.dumps(makeMaterialHeirarchy(item,6),indent=2))

print(recipes_dict["electronic-circuit"])