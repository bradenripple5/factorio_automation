import math
import copy
from make_assembling_machine import make_assembling_machine
import pyperclip
from conversion_script import *
SUBSTATION_SPACING = 18


def make_square_substation_array(products):

    # Create individual blueprints
    blueprints = [
        make_assembling_machine(product)
        for product in products
    ]

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

    for index, bp in enumerate(blueprints):

        row = index // cols
        col = index % cols

        offset_x = col * SUBSTATION_SPACING
        offset_y = row * SUBSTATION_SPACING

        bp_copy = copy.deepcopy(bp)

        for entity in bp_copy["blueprint"]["entities"]:

            # Offset position
            entity["position"]["x"] += offset_x
            entity["position"]["y"] += offset_y

            # Re-number entity
            entity["entity_number"] = entity_counter
            entity_counter += 1

            final_blueprint["blueprint"]["entities"].append(entity)

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
    pyperclip.copy(convertToBlueprint(bp))