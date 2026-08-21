import math
import copy
from make_assembling_machine import (
    make_assembling_machine,
    _connect_pole_pair,
    _get_footprint,
)
import pyperclip
from convert_json_to_blueprint_string import convertoToBlueprint


def make_square_substation_array(
    products,
    assembling_machine="assembling-machine-2",
    module="speed-module",
):

    # Create individual blueprints
    blueprints = [
        make_assembling_machine(
            product,
            assembling_machine=assembling_machine,
            module=module,
        )
        for product in products
    ]

    footprint_width, footprint_height = _get_footprint(blueprints[0])
    spacing_x = footprint_width + 1
    spacing_y = footprint_height + 2

    n = len(blueprints)

    cols = math.ceil(math.sqrt(n))
    rows = math.ceil(n / cols)

    final_blueprint = {
        "blueprint": {
            "item": "blueprint",
            "version": blueprints[0]["blueprint"]["version"],
            "entities": []
        }
    }

    entity_counter = 1
    module_poles = {}

    for index, bp in enumerate(blueprints):

        row = index // cols
        col = index % cols

        offset_x = col * spacing_x
        offset_y = row * spacing_y

        bp_copy = copy.deepcopy(bp)
        old_to_new = {}

        # Allocate all IDs first so internal neighbour references can be remapped.
        for entity in bp_copy["blueprint"]["entities"]:
            old_to_new[entity["entity_number"]] = entity_counter
            entity_counter += 1

        module_poles[index] = []

        for entity in bp_copy["blueprint"]["entities"]:

            # Offset position
            entity["position"]["x"] += offset_x
            entity["position"]["y"] += offset_y

            old_number = entity["entity_number"]
            entity["entity_number"] = old_to_new[old_number]
            if "neighbours" in entity:
                entity["neighbours"] = [
                    old_to_new[neighbour]
                    for neighbour in entity["neighbours"]
                    if neighbour in old_to_new
                ]
            if "pole" in entity["name"]:
                module_poles[index].append(entity["entity_number"])

            final_blueprint["blueprint"]["entities"].append(entity)

    # Connect each module's pole to its horizontal and vertical neighbours.
    entity_by_number = {
        entity["entity_number"]: entity
        for entity in final_blueprint["blueprint"]["entities"]
    }

    for index in range(n):
        row = index // cols
        col = index % cols
        right = index + 1
        down = index + cols
        if col + 1 < cols and right < n and module_poles[index] and module_poles[right]:
            _connect_pole_pair(entity_by_number, module_poles[index][0], module_poles[right][0])
        if down < n and module_poles[index] and module_poles[down]:
            _connect_pole_pair(entity_by_number, module_poles[index][0], module_poles[down][0])

    return final_blueprint
if __name__ == "__main__":
    products = [
        "advanced-circuit",
        "processing-unit",
        "engine-unit",
        "electric-engine-unit",
        "low-density-structure",
        "battery",
        "rocket-control-unit"
    ]

    bp = make_square_substation_array(products)
    pyperclip.copy(convertoToBlueprint(bp))
