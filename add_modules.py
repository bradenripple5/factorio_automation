"""Add modules to every compatible machine in a Factorio blueprint."""

from copy import deepcopy

from convert_json_to_blueprint_string import convertoToJson


# Module slot counts for module-capable Factorio 2.0 base-game/Space Age entities.
MODULE_SLOTS = {
    "assembling-machine-2": 2,
    "assembling-machine-3": 4,
    "electric-furnace": 2,
    "chemical-plant": 3,
    "oil-refinery": 3,
    "centrifuge": 2,
    "electric-mining-drill": 3,
    "big-mining-drill": 4,
    "pumpjack": 2,
    "lab": 2,
    "biolab": 4,
    "rocket-silo": 4,
    "beacon": 2,
    "foundry": 4,
    "electromagnetic-plant": 5,
    "biochamber": 4,
    "cryogenic-plant": 8,
    "recycler": 4,
}


def add_max_modules(blueprint, module, only_compatible=False):
    """Return a copy with each module-capable entity filled with ``module``.

    Existing modules in compatible entities are replaced. Beacons are skipped
    for productivity and quality modules because they cannot transmit those
    effects. If ``only_compatible`` is true, incompatible entities and wires
    connected to them are omitted from the returned blueprint.
    """
    if not isinstance(module, str) or not module:
        raise ValueError("module must be a non-empty Factorio item name")

    if isinstance(blueprint, str):
        blueprint = convertoToJson(blueprint)
    if not isinstance(blueprint, dict):
        raise TypeError("blueprint must be a decoded blueprint dictionary or Factorio blueprint string")

    new_blueprint = deepcopy(blueprint)
    blueprint_data = new_blueprint.get("blueprint", {})
    entities = blueprint_data.get("entities", [])
    version = blueprint_data.get("version", 0)
    major_version = version >> 48 if isinstance(version, int) else 0

    compatible_entities = []
    for entity in entities:
        entity_name = entity.get("name")
        slot_count = MODULE_SLOTS.get(entity_name, 0)
        if not slot_count:
            continue
        if entity_name == "beacon" and module.startswith(
            ("productivity-module", "quality-module")
        ):
            continue
        compatible_entities.append(entity)
        if major_version >= 2:
            entity["items"] = [{
                "id": {"name": module},
                "items": {
                    "in_inventory": [
                        {"inventory": 4, "stack": slot}
                        for slot in range(slot_count)
                    ],
                },
            }]
        else:
            entity["items"] = {module: slot_count}

    if only_compatible:
        blueprint_data["entities"] = compatible_entities
        retained_numbers = {
            entity["entity_number"]
            for entity in compatible_entities
            if "entity_number" in entity
        }
        if "wires" in blueprint_data:
            blueprint_data["wires"] = [
                wire
                for wire in blueprint_data["wires"]
                if len(wire) >= 3
                and wire[0] in retained_numbers
                and wire[2] in retained_numbers
            ]

    return new_blueprint


def add_max_speed_3_modules(blueprint):
    """Return a copy with every compatible entity filled with speed 3 modules."""
    return add_max_modules(blueprint, "speed-module-3")
