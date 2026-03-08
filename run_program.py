from make_assembling_machine import make_assembling_machine_array
from convert_json_to_blueprint_string import *
from recipe_extraction import get_recipe, recipes_dict, raw_materials, resolve_recipe_name, is_smelted
import math
import pyperclip
import sys
import json


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

def _get_recipe_block(recipe_name):
  info = recipes_dict.get(recipe_name)
  if info is None:
    return None
  if "normal" in info:
    return info["normal"]
  return info

def _extract_ingredients(recipe_name):
  recipe = _get_recipe_block(recipe_name)
  if recipe is None:
    return []
  ingredients = recipe.get("ingredients", [])
  out = []
  for ingredient in ingredients:
    if isinstance(ingredient, list):
      if len(ingredient) >= 2:
        out.append((ingredient[0], ingredient[1]))
    elif isinstance(ingredient, dict):
      name = ingredient.get("name")
      amount = ingredient.get("amount", 1)
      if name is not None:
        out.append((name, amount))
  return out

def _extract_result_count(recipe_name):
  info = recipes_dict.get(recipe_name, {})
  recipe = _get_recipe_block(recipe_name)
  if recipe is None:
    return 1
  if "result" in recipe:
    return recipe.get("result_count", 1)
  results = recipe.get("results")
  if results:
    main_product = recipe.get("main_product") or info.get("main_product")
    pick_name = main_product or recipe_name
    for result in results:
      if isinstance(result, list):
        name = result[0] if len(result) > 0 else None
        amount = result[1] if len(result) > 1 else 1
      else:
        name = result.get("name")
        amount = result.get("amount", result.get("amount_min", 1))
      if name == pick_name:
        return amount
    # fallback to first result
    first = results[0]
    if isinstance(first, list):
      return first[1] if len(first) > 1 else 1
    return first.get("amount", first.get("amount_min", 1))
  return 1

def _extract_energy_required(recipe_name):
  info = recipes_dict.get(recipe_name, {})
  recipe = _get_recipe_block(recipe_name)
  if recipe is None:
    return 0.5
  return recipe.get("energy_required", info.get("energy_required", 0.5)) or 0.5

def _machine_speed_for(recipe_name):
  recipe_info = recipes_dict.get(recipe_name, {})
  recipe_category = recipe_info.get("category")
  if recipe_category == "chemistry":
    return 1.0  # chemical-plant crafting speed
  if recipe_category == "oil-processing":
    return 1.0  # oil-refinery crafting speed (used for completeness)
  if (
      recipe_category == "smelting"
      or is_smelted(recipe_name)
      or "plate" in recipe_name
      or recipe_name in ["stone", "brick", "stone-brick"]
  ):
    return 2.0  # electric-furnace crafting speed
  return 0.75  # assembling-machine-2 crafting speed

def _per_machine_rates(recipe_name):
  energy = _extract_energy_required(recipe_name)
  speed = _machine_speed_for(recipe_name)
  cycle_time = energy / speed
  if cycle_time <= 0:
    cycle_time = 0.5 / speed
  output_count = _extract_result_count(recipe_name)
  output_rate = output_count / cycle_time
  ingredient_rates = []
  for name, amount in _extract_ingredients(recipe_name):
    ingredient_rates.append((name, amount / cycle_time))
  return output_rate, ingredient_rates

def _normalize_recipe_name(name):
  return resolve_recipe_name(name) or name

def _build_dependency_graph(targets):
  graph = {}
  visited = set()

  def dfs(node):
    node = _normalize_recipe_name(node)
    if node in visited:
      return
    visited.add(node)
    if node not in recipes_dict:
      graph[node] = []
      return
    ingredients = []
    for ing, _ in _extract_ingredients(node):
      ing_name = _normalize_recipe_name(ing)
      if ing_name in raw_materials:
        continue
      if ing_name in recipes_dict:
        ingredients.append(ing_name)
        dfs(ing_name)
    graph[node] = ingredients

  for t in targets:
    dfs(t)
  return graph

def _topo_sort(graph):
  order = []
  temp = set()
  perm = set()
  cycle = False

  def visit(n):
    nonlocal cycle
    if n in perm:
      return
    if n in temp:
      cycle = True
      return
    temp.add(n)
    for m in graph.get(n, []):
      visit(m)
    temp.remove(n)
    perm.add(n)
    order.append(n)

  for node in graph:
    visit(node)
  if cycle:
    return None
  return order

def compute_balanced_dependency_counts(target_counts):
  targets = [_normalize_recipe_name(k) for k in target_counts.keys()]
  graph = _build_dependency_graph(targets)
  order = _topo_sort(graph)
  if order is None:
    # Fallback: process in insertion order without guaranteeing optimal balance.
    order = list(graph.keys())
  process_order = list(reversed(order))

  demand_rate = {}
  machine_counts = {}

  for product in process_order:
    if product in target_counts:
      machine_count = target_counts[product]
      machine_counts[product] = machine_count
    else:
      required = demand_rate.get(product, 0.0)
      if required <= 0 or product not in recipes_dict:
        continue
      output_rate, _ = _per_machine_rates(product)
      if output_rate <= 0:
        continue
      machine_count = math.ceil(required / output_rate)
      if machine_count <= 0:
        continue
      machine_counts[product] = machine_count

    if product not in recipes_dict:
      continue
    _, ingredient_rates = _per_machine_rates(product)
    for ing, rate in ingredient_rates:
      ing_name = _normalize_recipe_name(ing)
      if ing_name in raw_materials:
        continue
      if ing_name not in recipes_dict:
        continue
      demand_rate[ing_name] = demand_rate.get(ing_name, 0.0) + machine_count * rate

  return process_order, machine_counts

MODULE_SLOTS = {
  "assembling-machine-1": 2,
  "assembling-machine-2": 2,
  "assembling-machine-3": 4,
  "electric-furnace": 3,
  "chemical-plant": 3,
  "oil-refinery": 3,
  "centrifuge": 2,
  "lab": 2,
  "rocket-silo": 4,
  "mining-drill": 3,
  "electric-mining-drill": 3,
}

MODULE_INVENTORY = {
  "assembling-machine-1": 4,
  "assembling-machine-2": 4,
  "assembling-machine-3": 4,
  "electric-furnace": 4,
  "chemical-plant": 4,
  "oil-refinery": 4,
  "centrifuge": 4,
  "lab": 4,
  "rocket-silo": 4,
  "mining-drill": 2,
  "electric-mining-drill": 2,
}

def _normalize_module_name(name):
  if name.endswith("-1"):
    base = name[:-2]
    if base in ["speed-module", "productivity-module", "effectivity-module"]:
      return base
  return name

def _load_blueprint_file(path="blueprint"):
  with open(path) as f:
    content = f.read().strip()
  if not content:
    raise ValueError("Blueprint file is empty.")
  if content.lstrip().startswith("{"):
    return json.loads(content)
  return convertoToJson(content)

def _apply_modules_to_blueprint(blueprint, module_name, count):
  entities = blueprint.get("blueprint", {}).get("entities", [])
  for entity in entities:
    slots = MODULE_SLOTS.get(entity.get("name"))
    inventory = MODULE_INVENTORY.get(entity.get("name"), 4)
    if not slots:
      continue
    if count == "max":
      use_count = slots
    else:
      use_count = min(slots, count)
    if use_count <= 0:
      continue
    entity["items"] = [
        {
            "id": {"name": module_name},
            "items": {
                "in_inventory": [
                    {"inventory": inventory, "stack": i} for i in range(use_count)
                ]
            },
        }
    ]
  return blueprint

if __name__ == "__main__":
  args = sys.argv[1:]
  items = None
  columns = None
  include_deps = False
  print_counts = False
  no_clipboard = False
  help_text = (
      "Usage:\n"
      "  python run_program.py [--with-deps|--deps|-d] <item> <count> [<item> <count> ...] <columns>\n"
      "  python run_program.py --modules <module>=<count|max>\n"
      "  python run_program.py --print-counts [--no-clipboard] [--with-deps|--deps|-d] <item> <count> ... <columns>\n"
      "\n"
      "Default behavior:\n"
      "  Makes an array of assembling machines for the provided items.\n"
      "\n"
      "Flags:\n"
      "  --with-deps, --deps, -d   Include balanced dependency machines.\n"
      "  --print-counts            Print computed machine counts.\n"
      "  --no-clipboard            Skip copying output to clipboard.\n"
      "  --modules, --module       Apply modules using clipboard blueprint by default.\n"
      "                           Optionally add file=<path> to read from a file.\n"
      "  -h, --help                Show this help.\n"
      "\n"
      "Examples:\n"
      "  python run_program.py iron-plate 5 electronic-circuit 5 3\n"
      "  python run_program.py --deps iron-plate 5 electronic-circuit 5 3\n"
      "  python run_program.py --print-counts --deps iron-plate 5 electronic-circuit 5 3\n"
      "  python run_program.py --no-clipboard iron-plate 5 3\n"
      "  python run_program.py --modules speed-module-1=max\n"
      "  python run_program.py --modules speed-module-1=max file=blueprint\n"
  )

  if args:
    if "-h" in args or "--help" in args:
      print(help_text)
      sys.exit(0)
    if "--print-counts" in args:
      print_counts = True
      args = [a for a in args if a != "--print-counts"]
    if "--no-clipboard" in args:
      no_clipboard = True
      args = [a for a in args if a != "--no-clipboard"]
    if "--modules" in args or "--module" in args:
      try:
        idx = args.index("--modules") if "--modules" in args else args.index("--module")
        spec = args[idx + 1]
      except (ValueError, IndexError):
        print("Usage: python run_program.py --modules <module>=<count|max> [file=<path>]")
        sys.exit(1)
      if "=" not in spec:
        print("Module spec must be in the form <module>=<count|max>.")
        sys.exit(1)
      module_name, raw_count = spec.split("=", 1)
      module_name = _normalize_module_name(module_name)
      if raw_count == "max":
        count = "max"
      else:
        try:
          count = int(raw_count)
        except ValueError:
          print("Module count must be an integer or 'max'.")
          sys.exit(1)
      source_path = None
      if idx + 2 < len(args) and args[idx + 2].startswith("file="):
        source_path = args[idx + 2].split("=", 1)[1]
        if not source_path:
          print("file=<path> must include a path.")
          sys.exit(1)
      if source_path:
        try:
          blueprint = _load_blueprint_file(source_path)
        except FileNotFoundError:
          print(f"Blueprint file '{source_path}' not found.")
          sys.exit(1)
        except ValueError as e:
          print(str(e))
          sys.exit(1)
      else:
        content = pyperclip.paste().strip()
        if not content:
          print("Clipboard is empty.")
          sys.exit(1)
        try:
          if content.lstrip().startswith("{"):
            blueprint = json.loads(content)
          else:
            blueprint = convertoToJson(content)
        except Exception:
          print("Clipboard does not contain valid blueprint data.")
          sys.exit(1)
      blueprint = _apply_modules_to_blueprint(blueprint, module_name, count)
      output = convertoToBlueprint(blueprint)
      print(output)
      pyperclip.copy(output)
      sys.exit(0)

    if args[0] in ("--with-deps", "--deps", "-d"):
      include_deps = True
      args = args[1:]

    if len(args) < 3 or len(args) % 2 == 0:
      print(help_text)
      sys.exit(1)
    try:
      columns = int(args[-1])
    except ValueError:
      print("Columns must be an integer.")
      sys.exit(1)

    items = []
    target_products = []
    target_counts = {}
    pair_args = args[:-1]
    for i in range(0, len(pair_args), 2):
      item = pair_args[i]
      item = _normalize_recipe_name(item)
      try:
        count = int(pair_args[i + 1])
      except ValueError:
        print(f"Count must be an integer for item '{item}'.")
        sys.exit(1)
      if count < 0:
        print(f"Count must be non-negative for item '{item}'.")
        sys.exit(1)
      target_products.append(item)
      target_counts[item] = target_counts.get(item, 0) + count
      items.extend([item] * count)

    if include_deps:
      order, machine_counts = compute_balanced_dependency_counts(target_counts)
      if print_counts:
        print("Machine counts (including dependencies):")
        for product in order:
          count = machine_counts.get(product, 0)
          if count:
            print(f"{product}: {count}")
      for product in order:
        if product in target_counts:
          continue
        count = machine_counts.get(product, 0)
        if count > 0:
          items.extend([product] * count)
    elif print_counts:
      print("Machine counts (targets only):")
      for product in target_products:
        count = target_counts.get(product, 0)
        if count:
          print(f"{product}: {count}")

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
      items if items is not None else ["iron-plate"] * 100,
      columns if columns is not None else 10,
      # ["efficiency-module","efficiency-module-2","efficiency-module-3","productivity-module","productivity-module-2","productivity-module-3","speed-module","speed-module-2","speed-module-3","belt-immunity-equipment","express-splitter","express-transport-belt","express-underground-belt","fast-splitter","fast-transport-belt","fast-underground-belt","splitter","transport-belt","underground-belt"]
  )
  print(convertoToBlueprint(bp))
  if not no_clipboard:
    pyperclip.copy(convertoToBlueprint(bp))
# {'blueprint': {'icons': [{'signal': {'name': 'assembling-machine-2'}, 'index': 1}], 'entities': [{'entity_number': 1, 'name': 'requester-chest', 'position': {'x': -2.5, 'y': 89.5}, 'request_filters': {'sections': [{'index': 1, 'filters': [{'index': 2, 'name': 'stone-brick', 'quality': 'normal', 'comparator': '=', 'count': 1000}]}]}}, {'entity_number': 2, 'name': 'active-provider-chest', 'position': {'x': -3.5, 'y': 89.5}}, {'entity_number': 3, 'name': 'fast-inserter', 'position': {'x': -3.5, 'y': 90.5}, 'direction': 8}, {'entity_number': 4, 'name': 'fast-inserter', 'position': {'x': -2.5, 'y': 90.5}}, {'entity_number': 5, 'name': 'assembling-machine-2', 'position': {'x': -2.5, 'y': 92.5}, 'recipe': 'stone-wall', 'recipe_quality': 'normal'}], 'item': 'blueprint', 'version': 562949955911682}}
