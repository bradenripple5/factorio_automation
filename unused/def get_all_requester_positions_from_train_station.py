import json
def get_all_requester_x_positions_from_train_station_blueprint(blueprint):
	xpositions,ypositions = [],[]
	for entity in blueprint["blueprint"]["entities"]:
		if entity["name"] == "logistic-chest-requester":
			xpositions.append(entity["position"]["x"])
			ypositions.append(entity["position"]["y"])

	return sorted(xpositions),sorted(ypositions)

with open("receiving_trainstation.json") as f:
	print(get_all_requester_x_positions_from_train_station_blueprint(json.load(f)))