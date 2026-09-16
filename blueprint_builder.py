"""Reusable blueprint-generation workflow shared by scripts and UIs."""

import copy
import math
from collections import Counter
from pathlib import Path

from add_modules import add_max_modules
from convert_json_to_blueprint_string import convertoToJson
from make_single_assembler import make_single_assembler
from make_solar_array import make_solar_array, solar_array_stats
from Station import Station, build_station_tree
from recipe_extraction import (
    get_non_raw_materials_for_recipe,
    get_recipe_machine,
    recipes_dict,
)
from make_station import (
    ROBOPORT_STATION_TEMPLATE,
    SOLID_INGREDIENT_STATION_TEMPLATE,
    _load_blueprint_file,
    _normalize_factorio_2_entity_names,
    add_midpoints_to_train_schedule,
    fill_locomotives_with_coal,
    make_solid_ingredient_station_array,
    set_trains_per_stop,
)


SOLID_ORE_RESOURCES = ("iron-ore", "copper-ore", "coal", "stone", "uranium-ore")
STATION_LAYOUT_ORDERS = {
    "advanced-circuit": [
        # 5
        "plastic-bar", "copper-plate", "copper-cable", "copper-cable",
        "advanced-circuit",
        # 5
        "plastic-bar", "electronic-circuit", "copper-plate",
        "copper-cable", "copper-cable",
        # 4
        "electronic-circuit", "copper-plate", "copper-cable", "copper-cable",
        # 4
        "iron-plate", "copper-plate", "copper-cable", "copper-cable",
        # 4
        "iron-plate", "copper-plate", "copper-cable", "copper-cable",
    ],
}
ORE_PICKUP_TEMPLATE = Path(__file__).parent / "blueprints" / "iron_ore_pickup"
MINING_DRILL_TEMPLATE = Path(__file__).parent / "mining_drills_optimal"
TRAIN_DEPOT_TEMPLATE = Path(__file__).parent / "blueprints" / "train_depot.json"
NINETY_RAIL_TEMPLATE = Path(__file__).parent / "blueprints" / "ninety_rail.json"
TRACK_INTERSECTION_TEMPLATE = Path(__file__).parent / "blueprints" / "intersection.json"
ROLLING_STOCK_NAMES = {"locomotive", "cargo-wagon", "fluid-wagon", "artillery-wagon"}
INSERTER_NAMES = {"inserter", "long-handed-inserter", "fast-inserter", "filter-inserter", "stack-inserter", "stack-filter-inserter", "bulk-inserter"}


def outfit_roboports_with_inserters(blueprint_string):
    """Point roboport-adjacent inserters outward and give them steel chests."""
    if not str(blueprint_string).strip():
        raise ValueError("Paste a Factorio blueprint string first")
    result = copy.deepcopy(convertoToJson(blueprint_string))
    if "blueprint" not in result:
        raise ValueError("The pasted string must contain one blueprint")
    entities = result["blueprint"].get("entities", [])
    roboports = [entity for entity in entities if entity.get("name") == "roboport"]
    if not roboports:
        raise ValueError("The pasted blueprint contains no roboports")

    def position(entity):
        point = entity.get("position", {})
        return point.get("x"), point.get("y")

    occupied = {position(entity): entity for entity in entities}
    next_number = max((entity.get("entity_number", 0) for entity in entities), default=0) + 1
    sides = (
        (0, 0, -1, ((-0.5, -2.5), (0.5, -2.5), (-1.5, -2.5), (1.5, -2.5))),
        (4, 1, 0, ((2.5, -0.5), (2.5, 0.5), (2.5, -1.5), (2.5, 1.5))),
        (8, 0, 1, ((-0.5, 2.5), (0.5, 2.5), (-1.5, 2.5), (1.5, 2.5))),
        (12, -1, 0, ((-2.5, -0.5), (-2.5, 0.5), (-2.5, -1.5), (-2.5, 1.5))),
    )
    for roboport in roboports:
        center_x, center_y = position(roboport)
        has_pair = False
        adjacent = []
        for direction, dx, dy, candidates in sides:
            for offset_x, offset_y in candidates:
                entity = occupied.get((center_x + offset_x, center_y + offset_y))
                if entity and entity.get("name") in INSERTER_NAMES:
                    adjacent.append((entity, direction, dx, dy))
        for inserter, direction, dx, dy in adjacent:
            inserter["direction"] = direction
            inserter_x, inserter_y = position(inserter)
            chest_position = (inserter_x + dx, inserter_y + dy)
            drop_entity = occupied.get(chest_position)
            if drop_entity is None:
                chest = {"entity_number": next_number, "name": "steel-chest", "position": {"x": chest_position[0], "y": chest_position[1]}}
                next_number += 1
                entities.append(chest)
                occupied[chest_position] = chest
                has_pair = True
            elif drop_entity.get("name") == "steel-chest":
                has_pair = True
        if has_pair:
            continue
        for direction, dx, dy, candidates in sides:
            for offset_x, offset_y in candidates:
                inserter_position = (center_x + offset_x, center_y + offset_y)
                chest_position = (inserter_position[0] + dx, inserter_position[1] + dy)
                if inserter_position in occupied or chest_position in occupied:
                    continue
                inserter = {"entity_number": next_number, "name": "inserter", "position": {"x": inserter_position[0], "y": inserter_position[1]}, "direction": direction}
                chest = {"entity_number": next_number + 1, "name": "steel-chest", "position": {"x": chest_position[0], "y": chest_position[1]}}
                next_number += 2
                entities.extend((inserter, chest))
                occupied[inserter_position] = inserter
                occupied[chest_position] = chest
                has_pair = True
                break
            if has_pair:
                break
        if not has_pair:
            raise ValueError(f"No clear inserter and steel-chest space around roboport at ({center_x}, {center_y})")
    result["blueprint"]["entities"] = entities
    return result


def build_dropoff_circuit_test(inserter_type="bulk-inserter"):
    """Build one working stop-to-unloader circuit for in-game inspection."""
    rails = [
        {
            "entity_number": index,
            "name": "straight-rail",
            "position": {"x": 0, "y": y},
        }
        for index, y in enumerate((0, 2, 4, 6, 8, 10), 1)
    ]
    stop_number = 7
    inserter_number = 8
    entities = rails + [
        {
            "entity_number": stop_number,
            "name": "train-stop",
            "position": {"x": 2, "y": 0},
            "control_behavior": {"read_stopped_train": True},
            "station": "Circuit Test Dropoff",
            "manual_trains_limit": 1,
        },
        {
            "entity_number": inserter_number,
            "name": inserter_type,
            "position": {"x": 1.5, "y": 7.5},
            "direction": 12,
            "control_behavior": {
                "circuit_enable_disable": True,
                "circuit_condition": {
                    "first_signal": {"type": "virtual", "name": "signal-T"},
                    "constant": 0,
                    "comparator": ">",
                },
            },
        },
        {
            "entity_number": 9,
            "name": "active-provider-chest",
            "position": {"x": 2.5, "y": 7.5},
        },
    ]
    return {
        "blueprint": {
            "icons": [
                {
                    "signal": {"type": "item", "name": "train-stop"},
                    "index": 1,
                }
            ],
            "entities": entities,
            "wires": [[stop_number, 1, inserter_number, 1]],
            "item": "blueprint",
            "label": "Stopped-train unloading circuit test",
            "version": 281474976710656,
        }
    }


def ingredients_for_product(
    final_product, include_final_product=True, station_order=None
):
    """Expand a product into the repeated station recipe list used by run_program."""
    final_product = final_product.strip()
    if not final_product:
        raise ValueError("Final product is required")
    if final_product not in recipes_dict:
        raise ValueError(f"Unknown recipe: {final_product}")

    ingredients = [
        ingredient
        for ingredient, quantity in get_non_raw_materials_for_recipe(final_product).items()
        for _ in range(int(quantity))
    ]
    if include_final_product:
        ingredients.insert(0, final_product)
    if station_order:
        requested_order = [
            str(product).strip().replace(" ", "-") for product in station_order
            if include_final_product or product != final_product
        ]
        if Counter(requested_order) != Counter(ingredients):
            raise ValueError(
                f"Manual station order for {final_product} does not match "
                "the calculated recipe quantities"
            )
        ingredients = requested_order
    if not ingredients:
        raise ValueError(f"No production stations were found for {final_product}")
    return ingredients


def plan_product_stations(
    final_product,
    include_final_product=True,
    trains_per_station=1,
    inserter_type="bulk-inserter",
    station_order=None,
):
    """Return the validated station tree for a production array."""
    products = ingredients_for_product(
        final_product, include_final_product, station_order
    )
    return build_station_tree(
        products,
        trains_per_station=trains_per_station,
        inserter_type=inserter_type,
    )


def optimize_station_order(
    stations, *, spacing_x=62, spacing_y=66, include_roboports=True
):
    """Place producer/consumer neighbours into nearby balanced-grid slots."""
    stations = list(stations)
    if len(stations) < 3:
        return stations
    columns = math.ceil(math.sqrt(len(stations)))
    rows = math.ceil(len(stations) / columns)
    base_length, longer_rows = divmod(len(stations), rows)
    row_lengths = [base_length + (row < longer_rows) for row in range(rows)]
    slots = [
        (row, columns - row_length + column)
        for row, row_length in enumerate(row_lengths)
        for column in range(row_length)
    ]
    y_stride = spacing_y * (2 if include_roboports else 1)

    def distance(first, second):
        return abs(first[1] - second[1]) * spacing_x + abs(first[0] - second[0]) * y_stride

    by_id = {station.id: station for station in stations}
    neighbours = {
        station.id: (set(station.parent_ids) | set(station.child_ids)) & by_id.keys()
        for station in stations
    }
    center_slot = min(
        slots,
        key=lambda slot: (
            abs(slot[0] - (rows - 1) / 2) + abs(slot[1] - (columns - 1) / 2),
            slot,
        ),
    )
    first = max(stations, key=lambda station: (len(neighbours[station.id]), station.id))
    assigned = {first.id: center_slot}
    free_slots = set(slots) - {center_slot}
    unplaced = set(by_id) - {first.id}
    while unplaced:
        station_id = max(
            unplaced,
            key=lambda candidate: (
                len(neighbours[candidate] & assigned.keys()),
                len(neighbours[candidate]),
                candidate,
            ),
        )
        connected_slots = [
            assigned[other] for other in neighbours[station_id] if other in assigned
        ]
        reference_slots = connected_slots or list(assigned.values())
        chosen_slot = min(
            free_slots,
            key=lambda slot: (
                sum(distance(slot, other) for other in reference_slots),
                slot,
            ),
        )
        assigned[station_id] = chosen_slot
        free_slots.remove(chosen_slot)
        unplaced.remove(station_id)
    station_by_slot = {assigned[station.id]: station for station in stations}
    return [station_by_slot[slot] for slot in slots]


def build_single_product_station(
    product,
    *,
    include_trains=True,
    trains_per_stop=1,
    inserter_type="bulk-inserter",
):
    """Build one Station object without production-array infrastructure."""
    product = str(product).strip()
    if not product:
        raise ValueError("Product is required")
    station = Station(
        product=product,
        id=f'{product.replace(" ", "-")}-001',
        trains_per_station=trains_per_stop,
        inserter_type=inserter_type,
    )
    blueprint = station.get_blueprint()
    if not include_trains:
        root = blueprint["blueprint"]
        root["entities"] = [
            entity for entity in root.get("entities", [])
            if entity.get("name") not in ROLLING_STOCK_NAMES
        ]
        root.pop("schedules", None)
        root.pop("stock_connections", None)
    _normalize_factorio_2_entity_names(
        blueprint.get("blueprint", {}).get("entities", []), inserter_type
    )
    return blueprint


def build_product_station_array(
    final_product,
    *,
    include_final_product=True,
    include_roboports=True,
    place_roboports_in_squares=True,
    place_roboports_between_stations=True,
    roboport_columns=4,
    roboport_rows=6,
    roboport_array_x_offset=0,
    roboport_array_y_offset=0,
    radial_layout=True,
    roboports_between_only=False,
    include_intersections=True,
    intersections_between_rows=False,
    intersection_x_offset=0,
    intersection_y_offset=0,
    intersection_signal_x_offset=0,
    intersection_signal_y_offset=0,
    empty_requester_chests=True,
    include_trains=True,
    trains_per_stop=1,
    horizontal_spacing=6,
    vertical_spacing=7,
    station_center_spacing_x=None,
    station_center_spacing_y=None,
    separate_train_depot=False,
    depot_only=False,
    include_solar=False,
    solar_columns=20,
    solar_rows=10,
    inserter_type="bulk-inserter",
    station_order=None,
):
    """Build the complete station array currently configured in run_program."""
    station_plan = plan_product_stations(
        final_product,
        include_final_product,
        trains_per_stop,
        inserter_type,
        station_order,
    )
    ingredients = [station.product for station in station_plan]
    if roboports_between_only:
        spacing_x = station_center_spacing_x or 62
        spacing_y = station_center_spacing_y or 66
        return (
            build_station_roboport_power_array(
                len(station_plan),
                station_center_spacing_x=spacing_x,
                station_center_spacing_y=spacing_y,
                below_station_y_offset=spacing_y / 2,
            ),
            ingredients,
        )
    if depot_only and include_trains:
        blueprint = _build_product_train_depot_from_ingredients(
            final_product, ingredients, trains_per_stop
        )
    else:
        station_layout = {}
        blueprint = make_solid_ingredient_station_array(
            station_plan,
            horizontal_spacing=horizontal_spacing,
            vertical_spacing=vertical_spacing,
            station_center_spacing_x=station_center_spacing_x,
            station_center_spacing_y=station_center_spacing_y,
            include_roboports=(
                include_roboports and not roboports_between_only
            ),
            place_roboports_in_squares=place_roboports_in_squares,
            place_roboports_between_stations=place_roboports_between_stations,
            roboport_columns=roboport_columns,
            roboport_rows=roboport_rows,
            roboport_array_x_offset=roboport_array_x_offset,
            roboport_array_y_offset=roboport_array_y_offset,
            radial_layout=radial_layout,
            # Let the station grid place its one correctly aligned intersection
            # set. The legacy shared-scaffold fallback below is suppressed when
            # real station layout metadata is available.
            include_intersections=include_intersections,
            intersections_between_rows=intersections_between_rows,
            intersection_x_offset=intersection_x_offset,
            intersection_y_offset=intersection_y_offset,
            intersection_signal_x_offset=intersection_signal_x_offset,
            intersection_signal_y_offset=intersection_signal_y_offset,
            empty_requester_chests=empty_requester_chests,
            trains_per_stop=trains_per_stop,
            inserter=inserter_type,
            layout_metadata=station_layout,
        )

        if (
            include_roboports
            and roboports_between_only
            and place_roboports_between_stations
        ):
            station_count = len(station_plan)
            station_columns = math.ceil(math.sqrt(station_count))
            station_rows = math.ceil(station_count / station_columns)
            base_length, longer_rows = divmod(station_count, station_rows)
            row_lengths = [
                base_length + (row < longer_rows)
                for row in range(station_rows)
            ]
            occupied = {
                (row, station_columns - row_length + local_column)
                for row, row_length in enumerate(row_lengths)
                for local_column in range(row_length)
            }
            positions = set()
            spacing_x = station_center_spacing_x or 62
            spacing_y = station_center_spacing_y or 66
            for row, column in occupied:
                if (row + 1, column) in occupied:
                    positions.add((
                        column * spacing_x,
                        (row + 0.5) * spacing_y,
                    ))
            entities = blueprint["blueprint"]["entities"]
            next_number = max(
                (entity["entity_number"] for entity in entities), default=0
            ) + 1
            for x, y in sorted(positions, key=lambda position: (position[1], position[0])):
                entities.append({
                    "entity_number": next_number,
                    "name": "roboport",
                    "position": {"x": x, "y": y},
                })
                next_number += 1
                entities.append({
                    "entity_number": next_number,
                    "name": "big-electric-pole",
                    "position": {"x": x + 3, "y": y},
                })
                next_number += 1
        # Every generated station cell already contains its saved intersection
        # and signal geometry. Only use the legacy shared-scaffold fallback for
        # callers that do not provide real station layout metadata; merging it
        # into normal production arrays duplicates and shifts intersections.
        if include_intersections and not station_layout.get(
            "production_positions"
        ):
            station_count = len(station_plan)
            station_columns = math.ceil(math.sqrt(station_count))
            station_rows = math.ceil(station_count / station_columns)
            base_station_spacing_y = (
                station_center_spacing_y
                if station_center_spacing_y is not None else 66
            )
            effective_station_spacing_x = station_layout.get(
                "station_center_spacing_x",
                station_center_spacing_x or 62,
            )
            track_station_spacing_y = base_station_spacing_y * (
                2 if include_roboports else 1
            )
            track_layer_y_offset = (
                (base_station_spacing_y if include_roboports else 0) - 2
            )
            # The station templates anchor their primary vertical through-rail
            # at X=1. The center-track scaffold's matching first lane is X=-27,
            # so translate the complete rail/intersection layer as one unit.
            track_layer_x_offset = 28
            base_row_length, longer_rows = divmod(station_count, station_rows)
            row_lengths = [
                base_row_length + (row < longer_rows)
                for row in range(station_rows)
            ]
            occupied_station_positions = station_layout.get(
                "production_positions"
            )
            station_access_crossings = [
                (
                    column * effective_station_spacing_x + 32,
                    row * track_station_spacing_y,
                )
                for row, column in (
                    occupied_station_positions
                    if occupied_station_positions is not None else
                    [
                        (row, station_columns - row_length + column)
                        for row, row_length in enumerate(row_lengths)
                        for column in range(row_length)
                    ]
                )
            ] if include_roboports else []
            track_layer = build_center_track_array(
                station_columns,
                station_rows,
                station_center_spacing_x=effective_station_spacing_x,
                station_center_spacing_y=track_station_spacing_y,
                include_intersection_signals=True,
                additional_crossings=station_access_crossings,
            )
            destination = blueprint["blueprint"]["entities"]
            existing = {
                (
                    entity.get("name"),
                    entity["position"]["x"],
                    entity["position"]["y"],
                    entity.get("direction", 0),
                )
                for entity in destination
            }
            next_number = max(
                (entity["entity_number"] for entity in destination), default=0
            ) + 1
            for source in track_layer["blueprint"]["entities"]:
                source_x = source["position"]["x"] + track_layer_x_offset
                source_y = source["position"]["y"] + track_layer_y_offset
                key = (
                    source.get("name"),
                    source_x,
                    source_y,
                    source.get("direction", 0),
                )
                if key in existing:
                    continue
                entity = copy.deepcopy(source)
                entity["position"]["x"] = source_x
                entity["position"]["y"] = source_y
                entity["entity_number"] = next_number
                next_number += 1
                destination.append(entity)
                existing.add(key)
            blueprint["blueprint"]["label"] += ", with center-track scaffold"
        if not include_trains:
            root = blueprint["blueprint"]
            root["entities"] = [
                entity for entity in root.get("entities", [])
                if entity.get("name") not in ROLLING_STOCK_NAMES
            ]
            root.pop("schedules", None)
            root.pop("stock_connections", None)
        else:
            blueprint = build_pickup_train_fleet(blueprint)
            if separate_train_depot:
                blueprint = move_scheduled_trains_to_depots(
                    blueprint,
                    trains_per_schedule=trains_per_stop,
                    depot_only=False,
                )

    if include_solar:
        blueprint = add_solar_array_to_blueprint(
            blueprint, solar_columns, solar_rows
        )
    _normalize_factorio_2_entity_names(
        blueprint.get("blueprint", {}).get("entities", []), inserter_type
    )
    return blueprint, ingredients


def add_solar_array_to_blueprint(blueprint, columns, rows, gap=12):
    """Place a powered solar field immediately to the right of a blueprint."""
    result = copy.deepcopy(blueprint)
    root = result["blueprint"]
    existing = root.get("entities", [])
    solar = make_solar_array(columns, rows)
    solar_entities = solar["blueprint"]["entities"]
    if existing:
        max_x = max(entity["position"]["x"] for entity in existing)
        min_y = min(entity["position"]["y"] for entity in existing)
        solar_min_x = min(entity["position"]["x"] for entity in solar_entities)
        solar_min_y = min(entity["position"]["y"] for entity in solar_entities)
        offset_x = math.ceil(max_x + gap - solar_min_x)
        offset_y = math.floor(min_y - solar_min_y)
    else:
        offset_x = offset_y = 0
    _append_entities(result, solar_entities, offset_x, offset_y)
    stats = solar_array_stats(solar)
    root["label"] = (
        f'{root.get("label", "Production array")} + '
        f'{stats["peak_output_mw"]:g} MW solar'
    )
    return result


def build_pickup_train_fleet(blueprint):
    """Give every physical pickup/dropoff stop its own ID-bound train route."""
    result = copy.deepcopy(blueprint)
    root = result["blueprint"]
    schedules = root.get("schedules", [])
    entities_by_number = {
        entity["entity_number"]: entity for entity in root.get("entities", [])
    }
    stop_names = sorted({
        entity["station"].removesuffix(" midpoint")
        for entity in root.get("entities", [])
        if entity.get("name") == "train-stop" and "station" in entity
    })
    midpoint_endpoints = {
        entity["station"].removesuffix(" midpoint")
        for entity in root.get("entities", [])
        if entity.get("name") == "train-stop"
        and entity.get("station", "").endswith(" midpoint")
    }

    def token_item(token):
        item, separator, identifier = token.rpartition("-")
        return item if separator and identifier.isdigit() else token

    pickups_by_item = {}
    dropoffs_by_item = {}
    for name in stop_names:
        if name.endswith(" pickup"):
            token = name.removesuffix(" pickup")
            pickups_by_item.setdefault(token_item(token), []).append(name)
        elif " dropoff " in name:
            item = name.rsplit(" dropoff ", 1)[1]
            dropoffs_by_item.setdefault(item, []).append(name)

    graph = {}
    for connection in root.get("stock_connections", []):
        stock = connection["stock"]
        graph.setdefault(stock, set())
        for end in ("front", "back"):
            if end in connection:
                graph[stock].add(connection[end])
                graph.setdefault(connection[end], set()).add(stock)

    def consist_numbers(schedule):
        seen = set(schedule.get("locomotives", []))
        pending = list(seen)
        while pending:
            stock = pending.pop()
            for neighbour in graph.get(stock, ()):
                if neighbour not in seen:
                    seen.add(neighbour)
                    pending.append(neighbour)
        return seen

    kept_stock = set()
    all_scheduled_stock = set()
    kept_schedules = []
    for schedule in schedules:
        stock = consist_numbers(schedule)
        all_scheduled_stock.update(stock)
        token = schedule.pop("_station_token", None)
        recipe = schedule.pop("_station_recipe", None)
        schedule.pop("_station_index", None)
        if not token or not recipe:
            continue
        value = schedule.get("schedule", {})
        old_records = value.get("records", []) if isinstance(value, dict) else value
        local_endpoints = [
            record.get("station", "").removesuffix(" midpoint")
            for record in old_records
            if record.get("station", "").removesuffix(" midpoint").startswith(
                f"{token} "
            )
        ]
        if not local_endpoints:
            continue
        local = local_endpoints[0]

        if local == f"{token} pickup":
            destinations = dropoffs_by_item.get(recipe, [])
            # Every physical station owns one product train. Repeated producer
            # stations intentionally share product-based stop names, and the
            # final product uses a generic external dropoff when the hierarchy
            # has no downstream consumer.
            destination = destinations[0] if destinations else f"{recipe} dropoff"
            records = [
                {"station": local, "wait_conditions": [{"type": "full", "compare_type": "and"}]},
                {"station": destination, "wait_conditions": [{"type": "empty", "compare_type": "and"}]},
            ]
            normalized = add_midpoints_to_train_schedule(records)
        elif " dropoff " in local:
            ingredient = local.rsplit(" dropoff ", 1)[1]
            producers = pickups_by_item.get(ingredient, [])
            if producers:
                # The producer pickup schedule already owns this internal
                # producer-to-consumer route. Keeping the template train at the
                # consumer dropoff created a second train on the same route.
                continue
            else:
                pickup = f"{ingredient} pickup"
                records = [
                    {"station": local, "wait_conditions": [{"type": "empty", "compare_type": "and"}]},
                    {"station": pickup, "wait_conditions": [{"type": "full", "compare_type": "and"}]},
                ]
                normalized = add_midpoints_to_train_schedule(
                    records, skip_midpoint_stations={pickup}
                )
        else:
            continue
        schedule["schedule"] = {"records": normalized}
        kept_schedules.append(schedule)
        kept_stock.update(stock)

    removed_stock = all_scheduled_stock - kept_stock
    root["entities"] = [
        entity for entity in root.get("entities", [])
        if entity["entity_number"] not in removed_stock
    ]
    root["stock_connections"] = [
        connection for connection in root.get("stock_connections", [])
        if connection["stock"] not in removed_stock
        and connection.get("front") not in removed_stock
        and connection.get("back") not in removed_stock
    ]
    root["schedules"] = kept_schedules
    return result


def build_train_depot():
    """Return the standalone 14-bay square train depot blueprint."""
    depot = _load_factorio_2_train_depot()
    root = depot["blueprint"]
    root["label"] = "Square train depot"
    root.pop("schedules", None)
    rolling_by_y = {}
    for entity in root.get("entities", []):
        if entity.get("name") in ROLLING_STOCK_NAMES:
            rolling_by_y.setdefault(entity["position"]["y"], []).append(entity)
    for bay in rolling_by_y.values():
        bay.sort(key=lambda entity: entity["position"]["x"])
        if len(bay) != 4:
            raise ValueError("Train depot contains a bay with an unexpected train length")
        for index, entity in enumerate(bay):
            if index in (0, 3):
                entity["name"] = "locomotive"
                entity["orientation"] = 0.75 if index == 0 else 0.25
                entity["items"] = {"coal": 25}
                entity.pop("inventory", None)
            else:
                entity["name"] = "cargo-wagon"
                entity["orientation"] = 0.75
                entity.pop("items", None)
    # The template is legacy, but the returned blueprint uses Factorio 2's
    # rolling-stock inventory schema and prototype names.
    fill_locomotives_with_coal(depot)
    return depot


def _load_factorio_2_train_depot():
    """Load the Factorio 1 depot and upgrade names/directions for Factorio 2."""
    depot = copy.deepcopy(_load_blueprint_file(TRAIN_DEPOT_TEMPLATE))
    root = depot["blueprint"]
    _normalize_factorio_2_entity_names(root.get("entities", []), "bulk-inserter")
    for entity in root.get("entities", []):
        if "direction" in entity:
            # Factorio 1 used 8 directions; Factorio 2 blueprint entities use 16.
            entity["direction"] = (entity["direction"] * 2) % 16
    root["version"] = _load_blueprint_file(
        SOLID_INGREDIENT_STATION_TEMPLATE
    )["blueprint"]["version"]
    return depot


def move_scheduled_trains_to_depots(
    blueprint, trains_per_schedule=1, *, depot_only=False
):
    """Move every scheduled consist from station cells into square depot copies."""
    if not isinstance(trains_per_schedule, int) or trains_per_schedule < 1:
        raise ValueError("trains_per_schedule must be a positive integer")
    result = copy.deepcopy(blueprint)
    root = result["blueprint"]
    source_schedules = root.get("schedules", [])
    if not source_schedules:
        return result

    entities = root.get("entities", [])
    by_number = {entity["entity_number"]: entity for entity in entities}
    graph = {}
    for connection in root.get("stock_connections", []):
        stock = connection["stock"]
        graph.setdefault(stock, set())
        for end in ("front", "back"):
            if end in connection:
                graph[stock].add(connection[end])
                graph.setdefault(connection[end], set()).add(stock)

    def consist_for(schedule):
        locomotives = schedule.get("locomotives", [])
        if not locomotives:
            raise ValueError("A generated train schedule has no locomotive")
        seen, pending = set(locomotives), list(locomotives)
        while pending:
            stock = pending.pop()
            for neighbour in graph.get(stock, ()):
                if neighbour not in seen:
                    seen.add(neighbour)
                    pending.append(neighbour)
        return seen

    source_consists = [consist_for(schedule) for schedule in source_schedules]
    schedules = []
    consists = []
    for schedule, consist in zip(source_schedules, source_consists):
        for _ in range(trains_per_schedule):
            schedules.append(copy.deepcopy(schedule))
            consists.append(consist)
    root["schedules"] = schedules
    rolling_numbers = set().union(*consists)
    root["entities"] = ([] if depot_only else [
        entity for entity in entities if entity["entity_number"] not in rolling_numbers
    ])
    original_connections = root.get("stock_connections", [])
    root["stock_connections"] = []
    if depot_only:
        root["wires"] = []
        root.pop("tiles", None)

    depot_root = _load_factorio_2_train_depot()["blueprint"]
    depot_entities = depot_root["entities"]
    depot_rolling = [e for e in depot_entities if e["name"] in ROLLING_STOCK_NAMES]
    bays_by_y = {}
    for entity in depot_rolling:
        bays_by_y.setdefault(entity["position"]["y"], []).append(entity)
    bays = [
        sorted(bay, key=lambda entity: entity["position"]["x"])
        for _, bay in sorted(bays_by_y.items())
    ]
    if not bays or any(len(bay) != len(consist) for bay in bays for consist in consists[:1]):
        raise ValueError("Train depot bays do not match the generated train length")

    infrastructure = [e for e in depot_entities if e["name"] not in ROLLING_STOCK_NAMES]
    depot_min_x = min(e["position"]["x"] for e in depot_entities)
    depot_max_x = max(e["position"]["x"] for e in depot_entities)
    depot_min_y = min(e["position"]["y"] for e in depot_entities)
    depot_max_y = max(e["position"]["y"] for e in depot_entities)
    copy_count = math.ceil(len(schedules) / len(bays))
    copy_columns = math.ceil(math.sqrt(copy_count))
    step_x = math.ceil((depot_max_x - depot_min_x + 10) / 2) * 2
    step_y = math.ceil((depot_max_y - depot_min_y + 10) / 2) * 2
    if depot_only:
        base_x, base_y = -depot_min_x, -depot_min_y
    else:
        array_max_x = max(e["position"]["x"] for e in root["entities"])
        array_min_y = min(e["position"]["y"] for e in root["entities"])
        base_x = math.ceil((array_max_x + 20) / 2) * 2 - depot_min_x
        base_y = math.floor(array_min_y / 2) * 2 - depot_min_y
    next_number = max(
        (e["entity_number"] for e in root["entities"]), default=0
    ) + 1

    def remap_refs(value, number_map):
        if isinstance(value, dict):
            for key, nested in value.items():
                if key == "entity_id" and nested in number_map:
                    value[key] = number_map[nested]
                else:
                    remap_refs(nested, number_map)
        elif isinstance(value, list):
            for nested in value:
                remap_refs(nested, number_map)

    for depot_index in range(copy_count):
        row, column = divmod(depot_index, copy_columns)
        dx, dy = base_x + column * step_x, base_y + row * step_y
        number_map = {
            entity["entity_number"]: next_number + index
            for index, entity in enumerate(infrastructure)
        }
        for entity in infrastructure:
            copied = copy.deepcopy(entity)
            copied["entity_number"] = number_map[entity["entity_number"]]
            copied["position"]["x"] += dx
            copied["position"]["y"] += dy
            if "neighbours" in copied:
                copied["neighbours"] = [number_map[n] for n in copied["neighbours"] if n in number_map]
            remap_refs(copied.get("connections"), number_map)
            root["entities"].append(copied)
        for wire in depot_root.get("wires", []):
            if wire[0] in number_map and wire[2] in number_map:
                copied = copy.deepcopy(wire)
                copied[0], copied[2] = number_map[copied[0]], number_map[copied[2]]
                root.setdefault("wires", []).append(copied)
        next_number += len(infrastructure)

        for bay_index, bay in enumerate(bays):
            schedule_index = depot_index * len(bays) + bay_index
            if schedule_index >= len(schedules):
                break
            consist = consists[schedule_index]
            source_stock = sorted(
                (by_number[number] for number in consist),
                key=lambda entity: (entity["position"]["x"], entity["position"]["y"]),
            )
            if len(source_stock) != len(bay):
                raise ValueError("Train depot bays do not match the generated train length")
            stock_map = {}
            for source, target in zip(source_stock, bay):
                copied = copy.deepcopy(source)
                copied["entity_number"] = next_number
                copied["position"] = {
                    "x": target["position"]["x"] + dx,
                    "y": target["position"]["y"] + dy,
                }
                copied["orientation"] = target.get("orientation", copied.get("orientation"))
                stock_map[source["entity_number"]] = next_number
                root["entities"].append(copied)
                next_number += 1
            schedules[schedule_index]["locomotives"] = [
                stock_map[number] for number in schedules[schedule_index]["locomotives"]
            ]
            for connection in original_connections:
                if connection["stock"] not in consist:
                    continue
                copied = copy.deepcopy(connection)
                for key in ("stock", "front", "back"):
                    if key in copied:
                        copied[key] = stock_map[copied[key]]
                root["stock_connections"].append(copied)
    root["label"] = (
        "Scheduled train depot"
        if depot_only else f'{root.get("label", "Production array")} with train depot'
    )
    return result


def _rotate_blueprint_clockwise(blueprint):
    """Rotate a complete blueprint 90 degrees clockwise around the origin."""
    result = copy.deepcopy(blueprint)
    root = result["blueprint"]
    direction_names = {
        "straight-rail",
        "legacy-straight-rail",
        "curved-rail-a",
        "curved-rail-b",
        "legacy-curved-rail",
        "half-diagonal-rail",
        "rail-signal",
        "rail-chain-signal",
        "train-stop",
    }
    for collection in ("entities", "tiles"):
        for entry in root.get(collection, []):
            x, y = entry["position"]["x"], entry["position"]["y"]
            entry["position"] = {"x": -y, "y": x}
            has_direction = (
                "direction" in entry
                or entry.get("name") in direction_names
                or entry.get("name", "").endswith("inserter")
            )
            if has_direction:
                # An omitted Factorio direction means zero and must still rotate.
                entry["direction"] = (entry.get("direction", 0) + 4) % 16
            if "orientation" in entry:
                entry["orientation"] = (entry["orientation"] + 0.25) % 1
    return result


def _make_depot_tracks_parallel_and_complete(blueprint):
    """Keep complete vertical train-bay rails and remove the legacy perimeter."""
    result = copy.deepcopy(blueprint)
    root = result["blueprint"]
    excluded_support_names = {
        "requester-chest",
        "logistic-chest-requester",
        "medium-electric-pole",
        "big-electric-pole",
        "small-electric-pole",
        "substation",
    }
    # After clockwise rotation every depot stop sits two tiles left of its bay
    # rail. Those lanes are already continuous at two-tile rail spacing in the
    # source template; the other rails form the obsolete square perimeter.
    bay_rail_positions = set()
    bend_end_positions = set()
    terminal_rail_positions = set()
    for stop in root.get("entities", []):
        if stop.get("name") != "train-stop":
            continue
        stop_y = stop["position"]["y"]
        stop_direction = stop.get("direction", 0)
        lane_x = (
            stop["position"]["x"] - 2
            if stop_direction == 0 else stop["position"]["x"] + 2
        )
        start_y = stop_y if stop_direction == 0 else stop_y - 38
        end_y = start_y + 38
        bay_rail_positions.update(
            (lane_x, y)
            for y in range(int(start_y), int(end_y) + 1, 2)
        )
        terminal_rail_positions.add((lane_x, end_y + 2))
        bend_end_positions.add((lane_x, end_y + 4))

    # A partially occupied final depot can make a stop-derived lane ambiguous
    # between two closely spaced rails. Rolling stock is authoritative: ensure
    # every actual consist has a complete lane centered at its exact X value.
    rolling_by_x = {}
    source_rails_by_x = {}
    for entity in root.get("entities", []):
        if entity.get("name") in ROLLING_STOCK_NAMES:
            rolling_by_x.setdefault(entity["position"]["x"], []).append(
                entity["position"]["y"]
            )
        elif (
            entity.get("name") == "straight-rail"
            and entity.get("direction", 0) in (0, 8)
        ):
            source_rails_by_x.setdefault(entity["position"]["x"], []).append(
                entity["position"]["y"]
            )
    for x, stock_ys in rolling_by_x.items():
        stock_ys = sorted(stock_ys)
        component_start = 0
        for index in range(1, len(stock_ys) + 1):
            if index < len(stock_ys) and stock_ys[index] - stock_ys[index - 1] <= 8:
                continue
            component = stock_ys[component_start:index]
            selected_ys = sorted(
                y for rail_x, y in bay_rail_positions if rail_x == x
            )
            already_covered = (
                selected_ys
                and min(selected_ys) <= min(component)
                and max(selected_ys) >= max(component)
            )
            if not already_covered:
                source_ys = sorted(source_rails_by_x.get(x, []))
                rail_start = 0
                for rail_index in range(1, len(source_ys) + 1):
                    if (
                        rail_index < len(source_ys)
                        and source_ys[rail_index] - source_ys[rail_index - 1] <= 2
                    ):
                        continue
                    rail_component = source_ys[rail_start:rail_index]
                    if (
                        rail_component
                        and rail_component[0] <= min(component)
                        and rail_component[-1] >= max(component)
                    ):
                        bay_rail_positions.update((x, y) for y in rail_component)
                        terminal_rail_positions.add((x, rail_component[-1] + 2))
                        bend_end_positions.add((x, rail_component[-1] + 4))
                        break
                    rail_start = rail_index
            component_start = index
    root["entities"] = [
        entity for entity in root.get("entities", [])
        if entity.get("name") not in excluded_support_names
        and not entity.get("name", "").endswith("inserter")
        and (
            "rail" not in entity.get("name", "")
            or (
                entity.get("name") == "straight-rail"
                and (
                    entity["position"]["x"], entity["position"]["y"]
                ) in bay_rail_positions
                and entity.get("direction", 0) in (0, 8)
            )
        )
    ]
    retained_numbers = {
        entity["entity_number"] for entity in root["entities"]
    }
    root["wires"] = [
        wire for wire in root.get("wires", [])
        if wire[0] in retained_numbers and wire[2] in retained_numbers
    ]
    for entity in root["entities"]:
        if entity.get("name") == "straight-rail":
            entity["direction"] = 0

    next_number = max(
        (entity["entity_number"] for entity in root["entities"]), default=0
    ) + 1
    for x, y in sorted(terminal_rail_positions):
        root["entities"].append({
            "entity_number": next_number,
            "name": "straight-rail",
            "position": {"x": x, "y": y},
            "direction": 0,
        })
        next_number += 1
    bend_end_positions = sorted(bend_end_positions)
    bend_entities = [
        entity
        for entity in _load_blueprint_file(NINETY_RAIL_TEMPLATE)["blueprint"][
            "entities"
        ]
        if entity.get("name") not in {"rail-signal", "rail-chain-signal"}
    ]
    bend_anchor = min(
        (
            entity for entity in bend_entities
            if entity.get("name") == "curved-rail-a"
        ),
        key=lambda entity: entity["entity_number"],
    )
    anchor_x = bend_anchor["position"]["x"]
    anchor_y = bend_anchor["position"]["y"]
    template_rails = [
        entity for entity in bend_entities
        if entity.get("name") in {
            "straight-rail", "curved-rail-a", "curved-rail-b",
            "half-diagonal-rail", "legacy-curved-rail",
        }
    ]
    signal_anchors = {}
    for entity in bend_entities:
        if entity.get("name") not in {"rail-signal", "rail-chain-signal"}:
            continue
        adjacent_rail = min(
            template_rails,
            key=lambda rail: (
                (rail["position"]["x"] - entity["position"]["x"]) ** 2
                + (rail["position"]["y"] - entity["position"]["y"]) ** 2,
                rail["entity_number"],
            ),
        )
        signal_anchors[entity["entity_number"]] = (
            adjacent_rail,
            entity["position"]["x"] - adjacent_rail["position"]["x"],
            entity["position"]["y"] - adjacent_rail["position"]["y"],
        )
    for end_x, end_y in bend_end_positions:
        transformed_positions = {
            entity["entity_number"]: {
                "x": end_x + entity["position"]["x"] - anchor_x,
                "y": end_y + entity["position"]["y"] - anchor_y,
            }
            for entity in bend_entities
        }
        for template_entity in bend_entities:
            copied = copy.deepcopy(template_entity)
            copied["entity_number"] = next_number
            if template_entity["entity_number"] in signal_anchors:
                adjacent_rail, offset_x, offset_y = signal_anchors[
                    template_entity["entity_number"]
                ]
                copied_rail_position = transformed_positions[
                    adjacent_rail["entity_number"]
                ]
                copied["position"] = {
                    "x": copied_rail_position["x"] + offset_x,
                    "y": copied_rail_position["y"] + offset_y,
                }
            else:
                copied["position"] = transformed_positions[
                    template_entity["entity_number"]
                ]
            root["entities"].append(copied)
            next_number += 1

    # Factorio places the rolling-stock ghosts one tile left of these migrated
    # depot rails. Keep the rail geometry fixed and correct the entire consist.
    for entity in root["entities"]:
        if entity.get("name") in ROLLING_STOCK_NAMES:
            entity["position"]["x"] += 1

    # Add one continuous perpendicular trunk below the completed depot. Track
    # running extrema across every entity, including copied bends and signals.
    min_x = math.inf
    max_x = -math.inf
    max_y = -math.inf
    for entity in root["entities"]:
        position = entity.get("position")
        if position is None:
            continue
        min_x = min(min_x, position["x"])
        max_x = max(max_x, position["x"])
        max_y = max(max_y, position["y"])
    trunk_start_x = math.floor(min_x / 2) * 2
    trunk_end_x = math.ceil(max_x / 2) * 2
    trunk_y = math.ceil(max_y / 2) * 2 + 2
    for x in range(int(trunk_start_x), int(trunk_end_x) + 1, 2):
        root["entities"].append({
            "entity_number": next_number,
            "name": "straight-rail",
            "position": {"x": x, "y": trunk_y},
            "direction": 4,
        })
        next_number += 1

    entities_by_number = {
        entity["entity_number"]: entity for entity in root["entities"]
    }
    for schedule in root.get("schedules", []):
        locomotives = [
            entities_by_number[number]
            for number in schedule.get("locomotives", [])
            if number in entities_by_number
        ]
        if len(locomotives) != 2:
            raise ValueError("Depot train must have exactly two locomotives")
        upward, downward = sorted(
            locomotives, key=lambda entity: entity["position"]["y"]
        )
        upward["orientation"] = 0.0
        downward["orientation"] = 0.5
    return result


def build_product_train_depot(final_product, **array_options):
    """Build only the directly planned product fleet depot."""
    include_final = array_options.get("include_final_product", True)
    trains_per_stop = array_options.get("trains_per_stop", 1)
    ingredients = ingredients_for_product(final_product, include_final)
    depot = _build_product_train_depot_from_ingredients(
        final_product, ingredients, trains_per_stop
    )
    return depot, ingredients


def _planned_product_train_records(ingredients, final_product=None):
    """Plan one ID-bound train for every product or ingredient station role."""
    instances = [
        {"recipe": recipe.replace(" ", "-"), "token": f"{recipe.replace(' ', '-')}-{index:03d}"}
        for index, recipe in enumerate(ingredients, 1)
    ]
    producers = {}
    consumers = {}
    for instance in instances:
        producers.setdefault(instance["recipe"], []).append(instance["token"])
        for ingredient in recipes_dict[instance["recipe"]].get("ingredients", []):
            item = ingredient["name"].replace(" ", "-")
            consumers.setdefault(item, []).append(
                f'{instance["token"]} dropoff {item}'
            )

    def endpoint(station, wait_type):
        return {
            "station": station,
            "wait_conditions": [{"type": wait_type, "compare_type": "and"}],
        }

    planned = []
    next_producer = {}
    next_consumer = {}
    for instance in instances:
        recipe = instance["recipe"]
        token = instance["token"]

        destinations = consumers.get(recipe, [])
        if destinations:
            index = next_consumer.get(recipe, 0)
            destination = destinations[index % len(destinations)]
            next_consumer[recipe] = index + 1
            planned.append(add_midpoints_to_train_schedule([
                endpoint(f"{token} pickup", "full"),
                endpoint(destination, "empty"),
            ]))

        input_items = sorted({
            ingredient["name"].replace(" ", "-")
            for ingredient in recipes_dict[recipe].get("ingredients", [])
        })
        for item in input_items:
            destination = f"{token} dropoff {item}"
            item_producers = producers.get(item, [])
            if item_producers:
                index = next_producer.get(item, 0)
                producer = item_producers[index % len(item_producers)]
                next_producer[item] = index + 1
                planned.append(add_midpoints_to_train_schedule([
                    endpoint(f"{producer} pickup", "full"),
                    endpoint(destination, "empty"),
                ]))
            else:
                raw_pickup = f"{item} pickup"
                planned.append(add_midpoints_to_train_schedule([
                    endpoint(destination, "empty"),
                    endpoint(raw_pickup, "full"),
                ], skip_midpoint_stations={raw_pickup}))
    return planned


def _build_product_train_depot_from_ingredients(
    final_product, ingredients, trains_per_stop=1
):
    """Construct the planned trains first, then place only their depot."""
    records_by_train = _planned_product_train_records(ingredients, final_product)
    source = {"blueprint": {
        "item": "blueprint",
        "label": f"{final_product} planned train fleet",
        "version": 562949958467584,
        "entities": [],
        "stock_connections": [],
        "schedules": [],
    }}
    source_root = source["blueprint"]
    next_number = 1
    for index, records in enumerate(records_by_train):
        train = build_train(
            2,
            double_ended=True,
            schedule_text="temporary | time | 1",
        )["blueprint"]
        number_map = {
            entity["entity_number"]: next_number + offset
            for offset, entity in enumerate(train["entities"])
        }
        for entity in train["entities"]:
            copied = copy.deepcopy(entity)
            copied["entity_number"] = number_map[entity["entity_number"]]
            copied["position"]["y"] += index * 12
            source_root["entities"].append(copied)
        for connection in train.get("stock_connections", []):
            copied = copy.deepcopy(connection)
            for key in ("stock", "front", "back"):
                if key in copied:
                    copied[key] = number_map[copied[key]]
            source_root["stock_connections"].append(copied)
        source_root["schedules"].append({
            "locomotives": [
                number_map[number]
                for number in train["schedules"][0]["locomotives"]
            ],
            "schedule": {"records": copy.deepcopy(records)},
        })
        next_number += len(train["entities"])

    depot = move_scheduled_trains_to_depots(
        source,
        trains_per_schedule=trains_per_stop,
        depot_only=True,
    )
    depot = _rotate_blueprint_clockwise(depot)
    depot = _make_depot_tracks_parallel_and_complete(depot)
    depot["blueprint"]["label"] = f"{final_product} scheduled train depot - upward rails"
    return depot


def _append_entities(target, source_entities, offset_x=0, offset_y=0):
    """Copy entities into a blueprint while preserving entity-number references."""
    target_entities = target["blueprint"]["entities"]
    next_number = max((entity["entity_number"] for entity in target_entities), default=0) + 1
    number_map = {
        entity["entity_number"]: next_number + index
        for index, entity in enumerate(source_entities)
    }
    for entity in source_entities:
        copied = copy.deepcopy(entity)
        copied["entity_number"] = number_map[entity["entity_number"]]
        copied["position"]["x"] += offset_x
        copied["position"]["y"] += offset_y
        if "neighbours" in copied:
            copied["neighbours"] = [
                number_map.get(neighbour, neighbour) for neighbour in copied["neighbours"]
            ]
        target_entities.append(copied)


def build_ore_pickup(
    resource="iron-ore",
    *,
    trains_per_stop=1,
    rail_x_offset=-50,
    mining_copies=1,
    rail_y_offset=0,
):
    """Build a bot-fed solid-resource mine connected to its pickup station."""
    if resource not in SOLID_ORE_RESOURCES:
        raise ValueError(
            f"Unsupported solid resource: {resource}. "
            f"Choose one of: {', '.join(SOLID_ORE_RESOURCES)}"
        )
    if not isinstance(mining_copies, int) or isinstance(mining_copies, bool) or mining_copies < 1:
        raise ValueError("Mining drill copies must be a positive integer")
    if not isinstance(rail_x_offset, int) or isinstance(rail_x_offset, bool):
        raise ValueError("Rail X offset must be an integer")
    if not isinstance(rail_y_offset, (int, float)):
        raise ValueError("Rail Y offset must be a number")
    encoded_template = ORE_PICKUP_TEMPLATE.read_text(encoding="utf-8-sig").strip()
    blueprint = copy.deepcopy(convertoToJson(encoded_template))
    root = blueprint["blueprint"]
    root["label"] = f"{resource} pickup"

    for entity in root.get("entities", []):
        if entity.get("name") == "train-stop":
            entity["station"] = f"{resource} pickup"
        request_filters = entity.get("request_filters", {})
        filters = list(request_filters.get("filters", []))
        for section in request_filters.get("sections", []):
            if isinstance(section, dict):
                filters.extend(section.get("filters", []))
        for item_filter in filters:
            if isinstance(item_filter, dict) and item_filter.get("name") == "iron-ore":
                item_filter["name"] = resource

    # Place the newest mining module to the left of the stop. Additional copies
    # extend farther left, retaining overlap between their logistics networks.
    mining = convertoToJson(MINING_DRILL_TEMPLATE.read_text(encoding="utf-8-sig").strip())
    mining_entities = mining["blueprint"]["entities"]
    min_x = min(entity["position"]["x"] for entity in mining_entities)
    max_x = max(entity["position"]["x"] for entity in mining_entities)
    min_y = min(entity["position"]["y"] for entity in mining_entities)
    max_y = max(entity["position"]["y"] for entity in mining_entities)
    stop = next(entity for entity in root["entities"] if entity["name"] == "train-stop")
    module_width = max_x - min_x + 1
    module_height = max_y - min_y + 1
    module_center_y = (min_y + max_y) / 2
    nearest_right_edge = stop["position"]["x"] + rail_x_offset
    first_offset_x = nearest_right_edge - max_x
    columns = math.ceil(math.sqrt(mining_copies))
    rows = math.ceil(mining_copies / columns)
    array_center_y = stop["position"]["y"] - rail_y_offset
    first_center_y = array_center_y - (rows - 1) * module_height / 2
    first_offset_y = first_center_y - module_center_y
    for copy_index in range(mining_copies):
        row, column = divmod(copy_index, columns)
        _append_entities(
            blueprint,
            mining_entities,
            first_offset_x - column * module_width,
            first_offset_y + row * module_height,
        )

    # Join the station logistics area to the nearest module. Roboports are at
    # most 46 tiles apart; substations are at most 18 tiles apart for power.
    module_roboport = next(e for e in mining_entities if e["name"] == "roboport")
    destination_x = module_roboport["position"]["x"] + first_offset_x
    destination_y = module_roboport["position"]["y"] + first_offset_y
    start_x = stop["position"]["x"] - 4
    # Keep corridor infrastructure beside the rails while still covering the
    # requester chests; placing it directly on the stop would collide.
    start_y = stop["position"]["y"] + 9
    span_x = destination_x - start_x
    span_y = destination_y - start_y
    span = math.hypot(span_x, span_y)
    corridor = []
    roboport_steps = max(1, math.ceil(span / 46))
    for step in range(roboport_steps):
        ratio = step / roboport_steps
        corridor.append({
            "entity_number": len(corridor) + 1,
            "name": "roboport",
            "position": {
                "x": start_x + span_x * ratio,
                "y": start_y + span_y * ratio,
            },
        })
    substation_steps = max(1, math.ceil(span / 18))
    for step in range(substation_steps + 1):
        ratio = step / substation_steps
        corridor.append({
            "entity_number": len(corridor) + 1,
            "name": "substation",
            "position": {
                "x": start_x + span_x * ratio,
                "y": start_y + span_y * ratio + 3,
            },
        })
    _append_entities(blueprint, corridor)

    return fill_locomotives_with_coal(
        set_trains_per_stop(blueprint, trains_per_stop)
    )


def build_single_production_machine(recipe):
    """Build one assembler, chemical plant, or furnace for a recipe."""
    recipe = recipe.strip()
    machine = get_recipe_machine(recipe)
    if machine is None:
        raise ValueError(f"{recipe} cannot be made in a supported production machine")
    return make_single_assembler(recipe, assembling_machine=machine)


def build_station_roboport_power_array(
    station_count,
    *,
    station_center_spacing_x=62,
    station_center_spacing_y=66,
    below_station_y_offset=33,
):
    """Build one roboport and adjacent big pole below every station slot."""
    if (
        not isinstance(station_count, int)
        or isinstance(station_count, bool)
        or station_count < 1
    ):
        raise ValueError("Station count must be a positive integer")
    columns = math.ceil(math.sqrt(station_count))
    rows = math.ceil(station_count / columns)
    base_length, longer_rows = divmod(station_count, rows)
    row_lengths = [
        base_length + (row < longer_rows) for row in range(rows)
    ]
    entities = []
    for row, row_length in enumerate(row_lengths):
        column_offset = columns - row_length
        for local_column in range(row_length):
            column = column_offset + local_column
            x = column * station_center_spacing_x
            y = row * station_center_spacing_y + below_station_y_offset
            entities.extend([
                {
                    "entity_number": len(entities) + 1,
                    "name": "roboport",
                    "position": {"x": x, "y": y},
                },
                {
                    "entity_number": len(entities) + 2,
                    "name": "big-electric-pole",
                    "position": {"x": x + 3, "y": y},
                },
            ])
    return {"blueprint": {
        "item": "blueprint",
        "label": f"{station_count}-station below-roboport power array",
        "version": 562949958467584,
        "entities": entities,
    }}


def build_center_track_array(
    columns=2,
    rows=2,
    *,
    station_center_spacing_x=62,
    station_center_spacing_y=66,
    include_intersection_signals=True,
    additional_crossings=(),
):
    """Build two horizontal and two vertical straight rails per station section."""
    for name, value in (("columns", columns), ("rows", rows)):
        if not isinstance(value, int) or isinstance(value, bool) or value < 1:
            raise ValueError(f"Track {name} must be a positive integer")
    for name, value in (
        ("station center spacing X", station_center_spacing_x),
        ("station center spacing Y", station_center_spacing_y),
    ):
        if not isinstance(value, (int, float)) or value <= 0 or value % 2:
            raise ValueError(f"{name} must be a positive even number")
    if not isinstance(include_intersection_signals, bool):
        raise ValueError("Include intersection signals must be true or false")
    additional_crossings = tuple(additional_crossings)
    if not all(
        isinstance(point, (tuple, list))
        and len(point) == 2
        and all(isinstance(value, (int, float)) for value in point)
        for point in additional_crossings
    ):
        raise ValueError("Additional crossings must be numeric X/Y pairs")

    # Keep both pairs centered on the section axes. Horizontal rails have one
    # full track-width gap between them (eight tiles center-to-center); the
    # vertical reference pair remains six tiles apart.
    horizontal_lane_offsets = (-4, 4)
    vertical_lane_offsets = (-3, 3)
    min_x = -station_center_spacing_x // 2
    max_x = (columns - 1) * station_center_spacing_x + station_center_spacing_x // 2
    min_y = -station_center_spacing_y // 2
    max_y = (rows - 1) * station_center_spacing_y + station_center_spacing_y // 2
    entities = []
    occupied = set()

    def add_rail(x, y, direction):
        key = (x, y, direction)
        if key in occupied:
            return
        occupied.add(key)
        entities.append({
            "entity_number": len(entities) + 1,
            "name": "straight-rail",
            "position": {"x": x, "y": y},
            "direction": direction,
        })

    # just_tracks.json places two crossings across every boundary between
    # station columns, at +32 and +94 from the left station anchor. Vertically,
    # crossings sit halfway (+33) between adjacent 66-tile station rows.
    interior_crossing_xs = [
        boundary_column * station_center_spacing_x + offset
        for boundary_column in range(columns - 1)
        for offset in (32, 94)
    ]
    crossing_center_xs = [
        -30,
        *interior_crossing_xs,
        (columns - 1) * station_center_spacing_x + 32,
    ]
    interior_crossing_ys = [
        boundary_row * station_center_spacing_y + station_center_spacing_y / 2
        for boundary_row in range(rows - 1)
    ]
    crossing_center_ys = [
        -station_center_spacing_y / 2,
        *interior_crossing_ys,
        (rows - 1) * station_center_spacing_y + station_center_spacing_y / 2,
    ]

    for center_y in crossing_center_ys:
        for lane_y in (
            center_y + offset - 1 for offset in horizontal_lane_offsets
        ):
            for x in range(int(min_x), int(max_x) + 1, 2):
                add_rail(x, lane_y, 4)
    for _, center_y in additional_crossings:
        for lane_y in (
            center_y + offset - 1 for offset in horizontal_lane_offsets
        ):
            for x in range(int(min_x), int(max_x) + 1, 2):
                add_rail(x, lane_y, 4)
    for center_x in crossing_center_xs:
        for lane_x in (center_x + offset for offset in vertical_lane_offsets):
            for y in range(int(min_y), int(max_y) + 1, 2):
                add_rail(lane_x, y, 0)

    intersection_root = _load_blueprint_file(TRACK_INTERSECTION_TEMPLATE)["blueprint"]
    intersection_entities = intersection_root["entities"]
    # The template's paired straight rails establish its exact crossing anchor.
    vertical_xs = [
        entity["position"]["x"] for entity in intersection_entities
        if entity.get("name") == "straight-rail"
        and entity.get("direction", 0) == 0
    ]
    horizontal_ys = [
        entity["position"]["y"] for entity in intersection_entities
        if entity.get("name") == "straight-rail"
        and entity.get("direction", 0) == 4
    ]
    template_anchor_x = (min(vertical_xs) + max(vertical_xs)) / 2
    template_anchor_y = (min(horizontal_ys) + max(horizontal_ys)) / 2
    template_min_x = min(entity["position"]["x"] for entity in intersection_entities)
    template_max_x = max(entity["position"]["x"] for entity in intersection_entities)
    template_min_y = min(entity["position"]["y"] for entity in intersection_entities)
    template_max_y = max(entity["position"]["y"] for entity in intersection_entities)

    crossings = [
        (center_x, center_y)
        for center_y in crossing_center_ys
        for center_x in crossing_center_xs
    ]
    crossings.extend(
        point for point in additional_crossings if point not in crossings
    )
    # Remove the plain rails inside every intersection footprint before laying
    # down the template. Its own rail signals are therefore the only signals.
    def inside_any_intersection(entity):
        x = entity["position"]["x"]
        y = entity["position"]["y"]
        return any(
            center_x + template_min_x - template_anchor_x <= x
            <= center_x + template_max_x - template_anchor_x
            and center_y + template_min_y - template_anchor_y <= y
            <= center_y + template_max_y - template_anchor_y
            for center_x, center_y in crossings
        )

    entities = [
        entity for entity in entities if not inside_any_intersection(entity)
    ]
    for number, entity in enumerate(entities, 1):
        entity["entity_number"] = number
    for center_x, center_y in crossings:
        dx = center_x - template_anchor_x
        dy = center_y - template_anchor_y - 1
        for source_entity in intersection_entities:
            if (
                source_entity.get("name") == "rail-signal"
                and not include_intersection_signals
            ):
                continue
            entity = copy.deepcopy(source_entity)
            entity["entity_number"] = len(entities) + 1
            entity["position"]["x"] += dx
            entity["position"]["y"] += dy
            if entity.get("name") in ("rail-signal", "rail-chain-signal"):
                entity["position"]["y"] += 1
            entity.pop("neighbours", None)
            entities.append(entity)

    # intersection.json's right vertical through-lane begins eight tiles below
    # its left lane. Restore those four straight pieces so both vertical tracks
    # continue through the full top edge of every intersection.
    occupied_rails = {
        (
            entity["name"],
            entity["position"]["x"],
            entity["position"]["y"],
            entity.get("direction", 0),
        )
        for entity in entities
        if "rail" in entity.get("name", "")
    }
    for center_x, center_y in crossings:
        for relative_y in (-34, -32, -30, -28):
            key = (
                "straight-rail",
                center_x + 3,
                center_y + relative_y - 1,
                0,
            )
            if key in occupied_rails:
                continue
            entities.append({
                "entity_number": len(entities) + 1,
                "name": "straight-rail",
                "position": {"x": key[1], "y": key[2]},
                "direction": 0,
            })
            occupied_rails.add(key)

    return {"blueprint": {
        "item": "blueprint",
        "label": f"{columns}x{rows} center-two track array",
        "version": 562949958467584,
        "entities": entities,
    }}


TRAIN_WAIT_CONDITIONS = ("time", "inactivity", "full", "empty")
REPEAT_CELL_TYPES = ("product-station", "roboport-station")


def parse_train_schedule(text):
    """Parse ``stop | condition | seconds`` lines into schedule entries."""
    stops = []
    for line_number, raw_line in enumerate(text.splitlines(), 1):
        if not raw_line.strip():
            continue
        fields = [field.strip() for field in raw_line.split("|")]
        if len(fields) not in (2, 3) or not fields[0]:
            raise ValueError(
                f"Schedule line {line_number} must be: Stop name | condition | seconds"
            )
        station, condition = fields[:2]
        condition = condition.casefold().replace(" ", "-")
        aliases = {"full-cargo": "full", "empty-cargo": "empty"}
        condition = aliases.get(condition, condition)
        if condition not in TRAIN_WAIT_CONDITIONS:
            raise ValueError(
                f"Schedule line {line_number} has unsupported condition: {condition}"
            )
        seconds = 5
        if condition in ("time", "inactivity"):
            if len(fields) == 3 and fields[2]:
                try:
                    seconds = int(fields[2])
                except ValueError as error:
                    raise ValueError(
                        f"Schedule line {line_number} seconds must be an integer"
                    ) from error
            if seconds < 1:
                raise ValueError(f"Schedule line {line_number} seconds must be positive")
        stops.append((station, condition, seconds))
    if not stops:
        raise ValueError("The train schedule needs at least one stop")
    return stops


def build_train(
    wagon_count=4, *, fluid_wagons=False, double_ended=False, schedule_text=""
):
    """Build a fueled train, optionally with locomotives at both ends."""
    if not isinstance(wagon_count, int) or isinstance(wagon_count, bool) or wagon_count < 1:
        raise ValueError("Wagon count must be a positive integer")
    if not isinstance(fluid_wagons, bool):
        raise ValueError("Fluid wagons must be true or false")
    if not isinstance(double_ended, bool):
        raise ValueError("Double-ended must be true or false")
    stops = parse_train_schedule(schedule_text)
    wagon_name = "fluid-wagon" if fluid_wagons else "cargo-wagon"
    entities = [{
        "entity_number": 1,
        "name": "locomotive",
        "position": {"x": 0, "y": 0},
        # The locomotive sits left of the wagons and faces outward, away from
        # the consist. In Factorio, 0.75 is west and 0.25 is east.
        "orientation": 0.75,
        "enable_logistics_while_moving": False,
    }]
    for index in range(wagon_count):
        wagon = {
            "entity_number": index + 2,
            "name": wagon_name,
            "position": {"x": (index + 1) * 7, "y": 0},
            "orientation": 0.25,
            "enable_logistics_while_moving": False,
        }
        if wagon_name == "cargo-wagon":
            wagon["inventory"] = None
        entities.append(wagon)
    if double_ended:
        entities.append({
            "entity_number": wagon_count + 2,
            "name": "locomotive",
            "position": {"x": (wagon_count + 1) * 7, "y": 0},
            "orientation": 0.25,
            "enable_logistics_while_moving": False,
        })

    connections = []
    for index, entity in enumerate(entities):
        connection = {"stock": entity["entity_number"]}
        if index == 0:
            connection["back"] = entities[1]["entity_number"]
        elif entity["name"] == "locomotive":
            # The optional rear locomotive faces away from the wagons, so its
            # back coupling points toward the consist just like the lead one.
            connection["back"] = entities[index - 1]["entity_number"]
        else:
            connection["back"] = entities[index - 1]["entity_number"]
            if index + 1 < len(entities):
                connection["front"] = entities[index + 1]["entity_number"]
        connections.append(connection)

    records = []
    for station, condition, seconds in stops:
        wait = {"type": condition, "compare_type": "and"}
        if condition in ("time", "inactivity"):
            wait["ticks"] = seconds * 60
        records.append({"station": station, "wait_conditions": [wait]})
    blueprint = {"blueprint": {
        "item": "blueprint",
        "label": (
            f"{'2' if double_ended else '1'}-{wagon_count} "
            f"{'fluid' if fluid_wagons else 'cargo'} train"
        ),
        "version": 562949958467584,
        "entities": entities,
        "stock_connections": connections,
        "schedules": [{
            "locomotives": [
                entity["entity_number"] for entity in entities
                if entity["name"] == "locomotive"
            ],
            "schedule": {"records": records},
        }],
    }}
    return fill_locomotives_with_coal(blueprint)


def build_repeated_blueprint(
    blueprint_string,
    copies=1,
    *,
    layout_blueprint_string="",
    horizontal_spacing=10,
    vertical_spacing=10,
    cell_type="product-station",
    include_roboports=True,
    module_upgrade=None,
):
    """Place pasted copies in the actual slots used by the final station array."""
    if not isinstance(copies, int) or isinstance(copies, bool) or copies < 1:
        raise ValueError("Blueprint copies must be a positive integer")
    for name, value in (
        ("horizontal spacing", horizontal_spacing),
        ("vertical spacing", vertical_spacing),
    ):
        if not isinstance(value, (int, float)) or value < 0:
            raise ValueError(f"{name.title()} must be a non-negative number")
    if not blueprint_string.strip():
        raise ValueError("Paste a Factorio blueprint string first")
    if cell_type not in REPEAT_CELL_TYPES:
        raise ValueError(f"Unknown repeat cell type: {cell_type}")
    if not isinstance(include_roboports, bool):
        raise ValueError("Include roboports must be true or false")
    if cell_type == "roboport-station" and not include_roboports:
        raise ValueError("Enable roboports to target extra-roboport station slots")
    source = convertoToJson(blueprint_string)
    if "blueprint" not in source:
        raise ValueError("The pasted string must contain one blueprint")
    if module_upgrade:
        source = add_max_modules(source, module_upgrade)
    source_root = source["blueprint"]
    source_entities = source_root.get("entities", [])
    source_tiles = source_root.get("tiles", [])
    positions = [item["position"] for item in (*source_entities, *source_tiles)]
    if not positions:
        raise ValueError("The pasted blueprint contains no entities or tiles")

    min_x = min(position["x"] for position in positions)
    max_x = max(position["x"] for position in positions)
    min_y = min(position["y"] for position in positions)
    max_y = max(position["y"] for position in positions)

    # When a completed production array is supplied, its train stops are the
    # authoritative placement slots. This preserves its exact count, spacing,
    # and any non-square arrangement instead of reconstructing the layout.
    target_positions = None
    if layout_blueprint_string.strip():
        layout = convertoToJson(layout_blueprint_string)
        if "blueprint" not in layout:
            raise ValueError("The final product array must contain one blueprint")
        target_positions = sorted(
            (
                entity["position"]["x"],
                entity["position"]["y"],
            )
            for entity in layout["blueprint"].get("entities", [])
            if entity.get("name") == "train-stop"
        )
        if not target_positions:
            raise ValueError("The final product array contains no train stops")
        copies = len(target_positions)
    templates = [SOLID_INGREDIENT_STATION_TEMPLATE]
    if include_roboports:
        templates.append(ROBOPORT_STATION_TEMPLATE)
    template_sizes = []
    for template in templates:
        entities = _load_blueprint_file(template)["blueprint"]["entities"]
        xs = [entity["position"]["x"] for entity in entities]
        ys = [entity["position"]["y"] for entity in entities]
        template_sizes.append((max(xs) - min(xs), max(ys) - min(ys)))
    cell_width = max(width for width, _ in template_sizes)
    cell_height = max(height for _, height in template_sizes)
    # This is the same even-grid step calculation used by the final station
    # array. Keep the pasted footprint as a minimum to prevent overlap.
    step_x = math.ceil((max(cell_width, max_x - min_x) + horizontal_spacing) / 2) * 2
    step_y = math.ceil((max(cell_height, max_y - min_y) + vertical_spacing) / 2) * 2
    columns = math.ceil(math.sqrt(copies))

    source_stops = [
        entity for entity in source_entities if entity.get("name") == "train-stop"
    ]
    if source_stops:
        source_anchor = min(
            source_stops,
            key=lambda entity: (entity["position"]["y"], entity["position"]["x"]),
        )["position"]
        anchor_x, anchor_y = source_anchor["x"], source_anchor["y"]
    else:
        anchor_x, anchor_y = min_x, min_y

    result = copy.deepcopy(source)
    result_root = result["blueprint"]
    for collection in ("entities", "tiles", "wires", "schedules", "stock_connections"):
        result_root[collection] = []
    result_root["label"] = f"{source_root.get('label', 'Pasted blueprint')} x{copies}"

    def remap_references(value, number_map):
        if isinstance(value, dict):
            for key, nested in value.items():
                if key == "entity_id" and nested in number_map:
                    value[key] = number_map[nested]
                else:
                    remap_references(nested, number_map)
        elif isinstance(value, list):
            for nested in value:
                remap_references(nested, number_map)

    next_number = 1
    for copy_index in range(copies):
        if target_positions is not None:
            target_x, target_y = target_positions[copy_index]
            dx = target_x - anchor_x
            dy = target_y - anchor_y
        else:
            logical_row, column = divmod(copy_index, columns)
            if include_roboports:
                # This mirrors make_solid_ingredient_station_array: each logical
                # production row has a roboport row directly above it.
                row = logical_row * 2 + (cell_type == "product-station")
            else:
                row = logical_row
            # Anchor the pasted unit at each canonical cell origin. Translations
            # remain even so pasted rails retain their Factorio grid parity.
            dx = column * step_x - min_x
            dy = row * step_y - min_y
        number_map = {
            entity["entity_number"]: next_number + index
            for index, entity in enumerate(source_entities)
        }
        for entity in source_entities:
            copied = copy.deepcopy(entity)
            copied["entity_number"] = number_map[entity["entity_number"]]
            copied["position"]["x"] += dx
            copied["position"]["y"] += dy
            if "neighbours" in copied:
                copied["neighbours"] = [
                    number_map[n] for n in copied["neighbours"] if n in number_map
                ]
            remap_references(copied.get("connections"), number_map)
            result_root["entities"].append(copied)
        for tile in source_tiles:
            copied = copy.deepcopy(tile)
            copied["position"]["x"] += dx
            copied["position"]["y"] += dy
            result_root["tiles"].append(copied)
        for wire in source_root.get("wires", []):
            copied = copy.deepcopy(wire)
            copied[0] = number_map[copied[0]]
            copied[2] = number_map[copied[2]]
            result_root["wires"].append(copied)
        for schedule in source_root.get("schedules", []):
            copied = copy.deepcopy(schedule)
            copied["locomotives"] = [
                number_map[n] for n in copied.get("locomotives", []) if n in number_map
            ]
            result_root["schedules"].append(copied)
        for connection in source_root.get("stock_connections", []):
            copied = copy.deepcopy(connection)
            for key in ("stock", "front", "back"):
                if key in copied:
                    copied[key] = number_map[copied[key]]
            result_root["stock_connections"].append(copied)
        next_number += len(source_entities)
    return result
