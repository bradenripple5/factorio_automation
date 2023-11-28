import json, zlib, base64, pyperclip

def convertoToBlueprint(data,header=""):
	return "0"+"".join([ i for i in str(base64.b64encode(zlib.compress(bytes(json.dumps(data),"utf-8"))))[2:-1]])
def convertoToJson(s):
	return json.loads(zlib.decompress(base64.b64decode(s[1:])).decode("utf-8")) 

s="0eNqV0U0KgzAQBeC7vHUKmqptc5VSij9DO6BRkigV8e6NEUqhduFyknlfwsyEou6pM6wd1AQuW22hrhMsP3ReL2du7AgK7KiBgM6bpTI515gFWFf0gornmwBpx45pzYdivOu+Kcj4hk/SOp99PN0hEAJda32q1ctTXpICI9Qhm2fxg8idSLKFHHcicgtJ9iHRlpF+jLI3A1V/hDgIqZ91xYbK9SZd5h02or4WKDCQsaEhO5+kPMeX6OT//waORqDI"
s="0eNqN0NsKgzAMBuB3yXUHs7rp+ipjDA/BBTRKW2UifffVCjI2B7sqaZMv5Z+haAbsNbEFNQOVHRtQ1xkM1Zw3y52degQFZLEFAZy3S6VzasAJIK7wCSpyNwHIlizhOh+K6c5DW6D2DdtkOegRq0MABPSd8TMdL4u8c4gFTP6IPF2RxnJ9OznxJcr/xGgXTHbAeAON9Vb9sD/IJJDy84s+gZCReotUwIjahIZzlkqZRZdjKp17ARfxe7E="
s="0eNqV192OgjAQBeB3mWtM6FDawqtsNht/GreJVgNolhjefUGMWdcaz1wZFD6L0zk4F1rtTv7YhNhRfaGwPsSW6o8LtWEbl7vpva4/eqopdH5PGcXlfjpqlmFHQ0YhbvwP1Wr4zMjHLnTBz9dfD/qveNqvfDOecL9yfWrOfrO4AhkdD+14zSFOXzQ6i/G8fnpRo70JjV/PH5oheyL5TrbdqG2/uxeovpn8aHLCLFDT4KZGTYebJWqqHEcNjDKOWhgVlMnBqKBOFbZF+cUWLRLk9OtD297Opn2/SqWk9+4eUZVC4V5St01qABRupgWn1eT9a1w1uFriqsZVg6uMqxZXc1yFe2qhBNWqcBWvFue4ileLFa7i1WKWxUoxpBAtQsrHZZUpsQTFIiUmH8fwZr/tyn+5ZFOmxVY5tW8/ZSNQDyeMOvc+5rmSJh30XySXJh2kKmnSQSpLkw5SC2nSQaqWJh2kltKkg1QjTTpItdKkg1TBE0RQLby38GJpvLXwWmm8s/BSaUFj4SjcV3idNNxVgnWWshEPMo1sxINMKxvxINMJR7xndBzJr0N7/WfGz+jsm3Z+iDvL7FSVWx6GX6mJQfk="
s='0eNqV0W0LgjAQB/Dvcq8n6Mq0fZWI8OGwA52yzUhk371NIYoG6atx2/1/O7gZynbEQZE0IGagqpcaxGUGTY0sWn9npgFBABnsgIEsOl+pglqwDEjW+ASR2CsDlIYM4Zpfiukmx65E5RreSW1ctrmbaCEYDL12qV76r5wUcQaTPxxek8JqfUst+zH5TjP+JpMAedhKxiExNORxn8j/z5huFXlITP2mll2Kj9UzeKDSS8MpzzjPk3OccWtfKwe0Dw=='
s='0eNqV0W0LgjAQB/Dvcq8n6Mq0fZWI8OGwA52yzUhk371NIYoG6atx2/1/O7gZynbEQZE0IGagqpcaxGUGTY0sWn9npgFBABnsgIEsOl+pglqwDEjW+ASR2CsDlIYM4Zpfiukmx65E5RreSW1ctrmbaCEYDL12qV76r5wUcQaTPxxek8JqfUst+zH5TjP+JpMAedhKxiExNORxn8j/z5huFXlITP2mll2Kj9UzeKDSS8MpzzjPk3OccWtfKwe0Dw=='
s="0eNqN0NsKgzAMBuB3yXUHs7rp+ipjDA/BBTRKW2UifffVCjI2B7sqaZMv5Z+haAbsNbEFNQOVHRtQ1xkM1Zw3y52degQFZLEFAZy3S6VzasAJIK7wCSpyNwHIlizhOh+K6c5DW6D2DdtkOegRq0MABPSd8TMdL4u8c4gFTP6IPF2RxnJ9OznxJcr/xGgXTHbAeAON9Vb9sD/IJJDy84s+gZCReotUwIjahIZzlkqZRZdjKp17ARfxe7E="
s= "0eNqV0WELgjAQBuD/8n6eoCvT9lciwvSwA52yrUhk/72pEEVC9fG2e5/duBHn5kq9Ye2gRnDZaQt1GGG51kUznbmhJyiwoxYCuminyhTcwAuwrugOlfijAGnHjmnJz8Vw0tf2TCY0PJPWhWx9cdFMCPSdDalOT08FKZICA1Qc7IoNlctV4sUHKf8kI/lupivm5lczXptyTdz+J8rv/05/FeWamE6bmnepXlYvcCNj54ZdnkmZJ/s4k94/ADX8tA8="
s="0eNqN0W0LgyAQB/Dvcq8Nlj3OrzLG6OFoB2WhFovwu88MYmMNeiWn9/8p5wJlO+KgSBoQC1DVSw3itoCmRhbtumfmAUEAGeyAgSy6tVIFtWAZkKzxBSK0dwYoDRnCLe+L+SHHrkTlGvZkNaoJ68ADDIZeu0wv14ucE0QMZreEjq5JYbWdJZb9iPycGB6C8QEY7aA2zmqe5t8jU2/ybzI6IOOzZHwkJutQ/djFxy8xmFBp35DmGed5eL1k3No3EleXOQ=="

recipe = (convertoToJson((s)))                                                                                                                                                                                                                                                                                                                                                                   
# recipe["blueprint"]["entities"] =[recipe["blueprint"]["entities"][0]] 
# recipe["blueprint"]["entities"][0]["direction"] =1
print(json.dumps(recipe,indent=2))
mininum_x = min([i["position"]["x"] for i in recipe["blueprint"]["entities"]])
maximum_x = max([i["position"]["x"] for i in recipe["blueprint"]["entities"]])
middle = (maximum_x + mininum_x)//2 	

with open("reflection.json","w+") as f:
	f.write(json.dumps(recipe))
def generate_entity(entity_number = 1,name="straight-rail",x= 0,y=0,direction=0,rotation=0):
		entity = {
			"entity_number": entity_number,
			"name": name,
			"position": {
				"x": x,
				"y": y
			},
			"direction": direction,
			"rotation": rotation
		}
		return entity
def generate_blueprint(number_of_entities):
	blueprint_dict = {"blueprint": { "icons": [{ "signal": {"type": "item", "name": "rail"},"index": 1}]}}
	entities = []
	for i in range(number_of_entities):
		entities.append(generate_entity(entity_number = i+1,y=5*i,x=i,direction= (3+(4*i))%8))#rotation=i+1))
	# for i in range(number_of_entities,number_of_entities*2):
	# 	entities.append(generate_entity(entity_number = i,y=1,x=(2*i)%(2*number_of_entities),direction= i%8))
	blueprint_dict["blueprint"]["entities"] = entities
	blueprint_dict["blueprint"]["item"] = "blueprint"
	blueprint_dict["blueprint"]["version"] = 68722819072
	return blueprint_dict
# recipe = generate_blueprint(8)
with open("newrail.json","w+") as f:
	f.write(json.dumps(recipe))
	# x = entity["position"]["x"]
	# delta_x = middle - x
	# if index >0:
	# 	recipe["blueprint"]["entities"][index]["position"]["x"] = x-delta_x 
	# 	direction = recipe["blueprint"]["entities"][index]["direction"]
	# 	# if direction == 5:
	# 	# 	if recipe["blueprint"]["entities"][index-1]["direction"]["x"]
	# 	# 	recipe["blueprint"]["entities"][index]["position"]["x"] -=2
	# 	recipe["blueprint"]["entities"][index]["direction"] = (direction+4) % 8

pyperclip.copy(convertoToBlueprint(recipe))


