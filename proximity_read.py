import json


def get_max_neighbor_dist():
	with open("proximity_dictionary.json") as f:
		max, min = 0,0
		data = json.loads(f.read())
		for key in data:
			for node in data[key]:
				dif = node - int(key)
				if dif < min:
					min = dif
				if dif > max:
					max = dif
		return min,max
print(get_max_neighbor_dist())

