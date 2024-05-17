import os,json

recipes = {}

with open('ingredients.json') as f:
	ingredients = json.loads(f.read())

ingredients = {i["id"]:i for i in ingredients}
for i in ingredients:
	recipes[i] = {k["id"]:k["amount"] for k in ingredients[i]["recipe"]["ingredients"]}

print(json.dumps(recipes,indent=2))


def getTotalMaterials(product):
	totalMaterials = {}
	def getMaterialAmounts(current_product,amount =1):
		direct_amounts = recipes[current_product]
		for mat in direct_amounts:
			if mat in totalMaterials:
				totalMaterials[mat] += direct_amounts[mat]*amount
			else:
				totalMaterials[mat] = direct_amounts[mat]*amount
			getMaterialAmounts(mat,direct_amounts[mat])
	getMaterialAmounts(product)
	return totalMaterials
print(json.dumps(getTotalMaterials("logistic-robot"),indent=2))
print(recipes["iron-plate"])
