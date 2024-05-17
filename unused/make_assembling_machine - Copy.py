import json
#ok, so what I have to do here is to 
with open ("receiving_station_with_assemblers.json") as f:
	blueprint = json.load(f)
with open ("ingredients.json") as f:
	ingredients = json.load(f)


# print(json.dumps(blueprint,indent =2))
# print(json.dumps(ingredients[-1],indent=2))

from convert_json_to_blueprint_string import convertoToBlueprint


def make_assembling_machine(what_you_want_make,multiplication_factor):
	recipe = [ i for i in ingredients if i["id"] == what_you_want_make][0]["recipe"]["ingredients"]
	#this changes every requester chest to what you want
	for index, entity in enumerate(blueprint["blueprint"]["entities"]):
		if entity["name"] == "logistic-chest-requester":
			blueprint["blueprint"]["entities"][index]["request_filters"] = []
			for index_, element in enumerate(recipe):
				blueprint["blueprint"]["entities"][index]["request_filters"] += [{ "index":index_+1,"name":element["id"], "count":int(element["amount"])*multiplication_factor}]
	#this changes every assembling machine to what you want
	for index, entity in enumerate(blueprint["blueprint"]["entities"]):
		if "assembling-machine" in entity["name"]:
			blueprint["blueprint"]["entities"][index]["recipe"] = what_you_want_make


	return blueprint
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

ingredient_dictionary = {i["id"]:i for i in ingredients}
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
# print(json.dumps(getMaterialHeirarchy("space-science-pack"),indent=2))
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

# print(json.dumps(data["blueprint"]["entities"][3]["request_filters"],indent=2))