import json,copy,pyperclip,math,time,random,os
from collections import defaultdict
from convert_json_to_blueprint_string import *
from make_station import *

filename = "new_map_scaffold"
# filename = "test_blueprint"
# writeJsonFile(filename)

with open(f"blueprints\\{filename}.json") as f:
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

def get_euclidean_distance(pt1,pt2):
	return math.sqrt(sum([(pt1[i]-pt2[i])**2 for i in range(2)]))

def get_proximity_dictionary_alt(blueprint,number_of_neighbors):
	t = time.time()
	with open("javascript_blueprint.json","w+") as f:
		f.write(json.dumps(blueprint))
	print(time.time()-t, " time to write javascript_blueprint.json")
	t = time.time()
	os.system(f"node make_proximity_dictionary.js {number_of_neighbors}")
	print(time.time()-t, " time to run make_proximity_dictionary.js")
	with open("proximity_dictionary.json") as f:
		return json.loads(f.read())
def get_proximity_dictionary(blueprint,number_of_neighbors):

	pole_location_dictionary = {}
	for i,v in enumerate(blueprint["blueprint"]["entities"]):
		if v["name"] == "big-electric-pole" :
			pole_location_dictionary[v["entity_number"]] = (v["position"]["x"],v["position"]["y"])
	#so now we have the locations of each pole keys being the entity number and values the location
	# now to do the computationally expensive part of getting the five minimal distances between each
	proximity_dictionary = {} 
	for entity_number in pole_location_dictionary:
		five_minimal_distances = []
		five_minimal_indices = []
		dictionary_of_distances = {}
		for other_entity_number in pole_location_dictionary:
			pt1,pt2 = pole_location_dictionary[entity_number], pole_location_dictionary[other_entity_number]
			dist = get_euclidean_distance(pt1,pt2)
			if dist <= 100:
				dictionary_of_distances[other_entity_number] = dist

			five_closest_points =  [j for j in  {int(k):v for k,v in sorted(dictionary_of_distances.items(),key=lambda item:item[1])}.keys()][1:number_of_neighbors+1]

		proximity_dictionary[(entity_number)] = five_closest_points
	
	return proximity_dictionary


def neighbourify(blueprint,number_of_neighbors = 3):
	t = time.time()
	proximity_dictionary = {int(k):v for k,v in get_proximity_dictionary_alt(blueprint,number_of_neighbors).items()}
	print(time.time()-t, " = just for proximity_dictionary")
	# with open("proximity_dictionary.json","w+") as f:
	# 	f.write(json.dumps(proximity_dictionary,indent=2))
	for i,v in enumerate(blueprint["blueprint"]["entities"]):
		if v["name"] == "big-electric-pole":
			v["neighbours"] = proximity_dictionary[v["entity_number"]]
	return blueprint
def add_entities_to_blueprint_n_times(blueprint,number_of_times,offset_x,offset_y):
	blueprint_copy = copy.deepcopy(blueprint)
	empty_blueprint = copy.deepcopy(blueprint)
	empty_blueprint["blueprint"]["entities"] = []
	initial_length = len(blueprint["blueprint"]["entities"])
	# in here we need to add ONE connection between the old and new blueprints.
	for instance in range(1,number_of_times):
		blueprint_length = len(blueprint["blueprint"]["entities"])
		print(blueprint_length, " = blueprint_length")
		new_blueprint = copy.deepcopy(empty_blueprint)
		for i,v in enumerate(blueprint_copy["blueprint"]["entities"]):

			v_copy = copy.deepcopy(v)
			v_copy["entity_number"] = blueprint_length+i+1
			v_copy["position"]["x"] = v["position"]["x"] + offset_x*instance # +i*(instance%2==0)
			v_copy["position"]["y"] = v["position"]["y"] + offset_y*instance # +i*(instance%2==0)
			if "neighbours" in v_copy:
				v_copy["neighbours"] = [k+blueprint_length for k in v["neighbours"]]
			new_blueprint["blueprint"]["entities"].append(v_copy)
		connect_segments(blueprint,new_blueprint,40)

	return blueprint

#m being the number of times in the x direction, n number of times in the y
def make_m_by_n_array_of_blueprint(blueprint,m,n,offset_x,offset_y):
	blueprint_copy = (add_entities_to_blueprint_n_times(blueprint,m,offset_x,0))

	return (add_entities_to_blueprint_n_times(blueprint_copy,n,0,offset_y))


def connect_segments(blueprint_one, blueprint_two, distance_threshold):

	def find_two_connecting_poles_from_two_segments():
		first_division = blueprint_one["blueprint"]["entities"]
		second_divsion = blueprint_two["blueprint"]["entities"]
		while True:
			first_entity = random.choice(first_division)
			second_entity = random.choice(second_divsion)
			if first_entity["name"] == "big-electric-pole" and second_entity["name"] == "big-electric-pole":
				pt1, pt2 = [i for i in first_entity["position"].values()] , [i for i in second_entity["position"].values()] 
				if get_euclidean_distance(pt2,pt1) <= distance_threshold:
					return first_entity, second_entity
	for i in range(1):
		entity_one, entity_two = find_two_connecting_poles_from_two_segments()
		for entity in blueprint_two["blueprint"]["entities"]:
			# if entity["entity_number"] == entity_one["entity_number"]:
			# 	blueprint_one["blueprint"]["entities"].append(entity_one)
			# elif entity["entity_number"] == entity_two["entity_number"]:
			# 	blueprint_one["blueprint"]["entities"].append(entity_two)
			# else:
				blueprint_one["blueprint"]["entities"].append(entity)
		blueprint_one["blueprint"]["entities"][entity_one["entity_number"]-1]["neighbours"].append(entity_two["entity_number"])
		blueprint_one["blueprint"]["entities"][entity_two["entity_number"]-1]["neighbours"].append(entity_one["entity_number"])


# 	for i,v in enumerate(blueprint_1["blueprint"]["entities"]):
for i,v in enumerate(scaffold_blueprint["blueprint"]["entities"]):
	scaffold_blueprint["blueprint"]["entities"][i]["auto-connect"] = "false"
	scaffold_blueprint["blueprint"]["entities"][i]["neighbours"] = []


offset_x,offset_y = get_x_and_y_distance(scaffold_blueprint)
# scaffold_blueprint = neighbourify(scaffold_blueprint,5)
# doubled_blueprint = add_entities_to_blueprint(make_blueprint_offset_copy(scaffold_blueprint,offset_x,offset_y-2),scaffold_blueprint)
# blueprint_array = add_entities_to_blueprint_n_times(scaffold_blueprint,8,offset_x,0)
# scaffold_blueprint = neighbourify(scaffold_blueprint,3)
blueprint_to_be_copied = make_station("advanced-circuit")
with open("blueprints\\advanced-circuit.json","w+") as f:
	f.write(json.dumps(blueprint_to_be_copied, indent=2))
array_length = 20
blueprint_array = make_m_by_n_array_of_blueprint(blueprint_to_be_copied,1,6,offset_x-1,offset_y-1)
T = time.time()
# blueprint_array = neighbourify(blueprint_array,3)
print(time.time()-T)
blueprint_array = neighbourify(blueprint_array,4)

# with open("blueprint_with_neighbourify.json","w+") as f:
# 	f.write(json.dumps(blueprint_array, indent =2 ))
pyperclip.copy(convertoToBlueprint(blueprint_array))

#ideally we'd locate TWO electric poles close enough to each other, one from the old blueprint one from the new
# and connect the two. this might not solve the problem when dealing with two poles 
