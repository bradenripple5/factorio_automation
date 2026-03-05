from make_assembling_machine import make_assembling_machine_array
from convert_json_to_blueprint_string import *
from recipe_extraction import get_recipe, recipes_dict, raw_materials
import math
import pyperclip


def expand_to_non_raw_products(target_products):
  raw_set = set(raw_materials)
  required = set()

  def walk(product):
    if product in raw_set:
      return
    if product in required:
      return
    if product in recipes_dict:
      required.add(product)

    recipe = get_recipe(product)
    if not recipe:
      return
    for ingredient in recipe:
      walk(ingredient)

  for target in target_products:
    walk(target)
  return sorted(required)


if __name__ == "__main__":
  raw_set = set(raw_materials)
  all_non_raw_products = sorted(
      [product for product in recipes_dict.keys() if product not in raw_set]
  )

  bp = make_assembling_machine_array(
      # ["assembling-machine-1","assembling-machine-2","assembling-machine-3"]*3,
      # [    "advanced-circuit",    "automation-science-pack",    "centrifuge",    "chemical-science-pack",    "concrete",    "construction-robot",    "copper-cable",    "electric-engine-unit",    "electric-furnace",    "electric-mining-drill",    "electronic-circuit",    "engine-unit",    "firearm-magazine",    "flying-robot-frame",    "grenade",    "heat-exchanger",    "heat-pipe",    "inserter",    "iron-chest",    "iron-gear-wheel",    "iron-stick",    "logistic-chest-active-provider",    "logistic-chest-buffer",    "logistic-chest-passive-provider",    "logistic-chest-requester",    "logistic-chest-storage",    "logistic-robot",    "logistic-science-pack",    "low-density-structure",    "military-science-pack",    "nuclear-reactor",    "offshore-pump",    "piercing-rounds-magazine",    "pipe",    "processing-unit",    "production-science-pack",    "productivity-module",    "pump",    "rail",    "steam-turbine",    "steel-chest",    "stone-wall",    "transport-belt",    "uranium-fuel-cell",    "utility-science-pack",    "wooden-chest"  ],
      # columns= int(math.sqrt(len(      [    "advanced-circuit",    "automation-science-pack",    "centrifuge",    "chemical-science-pack",    "concrete",    "construction-robot",    "copper-cable",    "electric-engine-unit",    "electric-furnace",    "electric-mining-drill",    "electronic-circuit",    "engine-unit",    "firearm-magazine",    "flying-robot-frame",    "grenade",    "heat-exchanger",    "heat-pipe",    "inserter",    "iron-chest",    "iron-gear-wheel",    "iron-stick",    "logistic-chest-active-provider",    "logistic-chest-buffer",    "logistic-chest-passive-provider",    "logistic-chest-requester",    "logistic-chest-storage",    "logistic-robot",    "logistic-science-pack",    "low-density-structure",    "military-science-pack",    "nuclear-reactor",    "offshore-pump",    "piercing-rounds-magazine",    "pipe",    "processing-unit",    "production-science-pack",    "productivity-module",    "pump",    "rail",    "steam-turbine",    "steel-chest",    "stone-wall",    "transport-belt",    "uranium-fuel-cell",    "utility-science-pack",    "wooden-chest"  ])))
      # [    "burner-inserter",    "inserter",    "long-handed-inserter",    "fast-inserter",    "filter-inserter",    "stack-inserter",    "stack-filter-inserter",    "bulk-inserter"  ],
      # [
      #     "wooden-chest",
      #     "iron-chest",
      #     "steel-chest",
      #     "active-provider-chest",
      #     "passive-provider-chest",
      #     "storage-chest",
      #     "buffer-chest",
      #     "requester-chest",
      # ],
      # ["lab"]*3,
      # all_non_raw_products*10,
      # ["concrete"]
      # columns=12*5
      ["advanced-circuit","electronic-circuit"]*10, 5
      # ["efficiency-module","efficiency-module-2","efficiency-module-3","productivity-module","productivity-module-2","productivity-module-3","speed-module","speed-module-2","speed-module-3","belt-immunity-equipment","express-splitter","express-transport-belt","express-underground-belt","fast-splitter","fast-transport-belt","fast-underground-belt","splitter","transport-belt","underground-belt"]
  )
  pyperclip.copy(convertoToBlueprint(bp))
# {'blueprint': {'icons': [{'signal': {'name': 'assembling-machine-2'}, 'index': 1}], 'entities': [{'entity_number': 1, 'name': 'requester-chest', 'position': {'x': -2.5, 'y': 89.5}, 'request_filters': {'sections': [{'index': 1, 'filters': [{'index': 2, 'name': 'stone-brick', 'quality': 'normal', 'comparator': '=', 'count': 1000}]}]}}, {'entity_number': 2, 'name': 'active-provider-chest', 'position': {'x': -3.5, 'y': 89.5}}, {'entity_number': 3, 'name': 'fast-inserter', 'position': {'x': -3.5, 'y': 90.5}, 'direction': 8}, {'entity_number': 4, 'name': 'fast-inserter', 'position': {'x': -2.5, 'y': 90.5}}, {'entity_number': 5, 'name': 'assembling-machine-2', 'position': {'x': -2.5, 'y': 92.5}, 'recipe': 'stone-wall', 'recipe_quality': 'normal'}], 'item': 'blueprint', 'version': 562949955911682}}
