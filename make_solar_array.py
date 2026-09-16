"""Generate rectangular, fully powered Factorio solar-panel blueprints."""

import argparse
import json
import math

import pyperclip

from convert_json_to_blueprint_string import convertoToBlueprint


BLUEPRINT_VERSION = 562949955780608
PANEL_SIZE = 3
SUBSTATION_SIZE = 2
SUBSTATION_SUPPLY_DIAMETER = 18
SUBSTATION_WIRE_REACH = 18
ROBOPORT_SIZE = 4
ROBOPORT_GRID_SPACING = 42
BIG_ELECTRIC_POLE_SIZE = 2
BIG_ELECTRIC_POLE_WIRE_REACH = 30
SOLAR_PANEL_OUTPUT_KW = 60


def _axis_substation_positions(length):
    """Return centered pole coordinates covering an axis of ``length`` tiles."""
    count = max(1, math.ceil(length / SUBSTATION_SUPPLY_DIAMETER))
    if count == 1:
        # Even-sized entities must use integer coordinates in Factorio.
        return [math.floor(length / 2 + 0.5)]

    # Distribute the poles evenly.  The first and last supply squares touch the
    # field edges, and adjacent poles remain within copper-wire reach.
    first = SUBSTATION_SUPPLY_DIAMETER / 2
    last = length - SUBSTATION_SUPPLY_DIAMETER / 2
    return [
        round(first + index * (last - first) / (count - 1))
        for index in range(count)
    ]


def _boxes_overlap(a_center, a_size, b_center, b_size):
    return all(
        abs(a_center[axis] - b_center[axis]) < (a_size + b_size) / 2
        for axis in (0, 1)
    )


def _validate_dimensions(columns, rows):
    if not isinstance(columns, int) or not isinstance(rows, int):
        raise TypeError("columns and rows must be integers")
    if columns < 1 or rows < 1:
        raise ValueError("columns and rows must both be at least 1")


def _axis_roboport_positions(length):
    """Return cell-centered positions for a connected roboport network."""
    count = max(1, math.ceil(length / ROBOPORT_GRID_SPACING))
    return [round((index + 0.5) * length / count) for index in range(count)]


def _solar_layout(columns, rows):
    """Return infrastructure positions and panel cells occupied by it."""
    _validate_dimensions(columns, rows)
    width = columns * PANEL_SIZE
    height = rows * PANEL_SIZE
    pole_positions = [
        (x, y)
        for y in _axis_substation_positions(height)
        for x in _axis_substation_positions(width)
    ]
    desired_roboports = [
        (x, y)
        for y in _axis_roboport_positions(height)
        for x in _axis_roboport_positions(width)
    ]
    offsets = sorted(
        ((x, y) for x in range(-4, 5) for y in range(-4, 5)),
        key=lambda offset: (abs(offset[0]) + abs(offset[1]), offset),
    )
    roboport_positions = []
    for desired in desired_roboports:
        for offset_x, offset_y in offsets:
            candidate = (desired[0] + offset_x, desired[1] + offset_y)
            if any(
                _boxes_overlap(candidate, ROBOPORT_SIZE, pole, SUBSTATION_SIZE)
                for pole in pole_positions
            ):
                continue
            if any(
                _boxes_overlap(candidate, ROBOPORT_SIZE, other, ROBOPORT_SIZE)
                for other in roboport_positions
            ):
                continue
            roboport_positions.append(candidate)
            break
        else:
            raise ValueError("Could not place a roboport without a collision")

    big_pole_positions = []
    power_offsets = sorted(
        (
            (x, y)
            for x in range(-4, 5)
            for y in range(-4, 5)
            if not _boxes_overlap((0, 0), ROBOPORT_SIZE, (x, y), BIG_ELECTRIC_POLE_SIZE)
        ),
        key=lambda offset: (abs(offset[0]) + abs(offset[1]), offset),
    )
    for roboport in roboport_positions:
        for offset_x, offset_y in power_offsets:
            candidate = (roboport[0] + offset_x, roboport[1] + offset_y)
            if any(_boxes_overlap(candidate, BIG_ELECTRIC_POLE_SIZE, pole, SUBSTATION_SIZE) for pole in pole_positions):
                continue
            if any(_boxes_overlap(candidate, BIG_ELECTRIC_POLE_SIZE, other, ROBOPORT_SIZE) for other in roboport_positions):
                continue
            if any(_boxes_overlap(candidate, BIG_ELECTRIC_POLE_SIZE, other, BIG_ELECTRIC_POLE_SIZE) for other in big_pole_positions):
                continue
            big_pole_positions.append(candidate)
            break
        else:
            raise ValueError("Could not place a big electric pole beside a roboport")

    blocked_panels = set()
    infrastructure = [
        *[(position, SUBSTATION_SIZE) for position in pole_positions],
        *[(position, ROBOPORT_SIZE) for position in roboport_positions],
        *[(position, BIG_ELECTRIC_POLE_SIZE) for position in big_pole_positions],
    ]
    for position, size in infrastructure:
        approximate_column = int(position[0] // PANEL_SIZE)
        approximate_row = int(position[1] // PANEL_SIZE)
        for row in range(max(0, approximate_row - 2), min(rows, approximate_row + 3)):
            for column in range(
                max(0, approximate_column - 2), min(columns, approximate_column + 3)
            ):
                panel = (column * PANEL_SIZE + 1.5, row * PANEL_SIZE + 1.5)
                if _boxes_overlap(panel, PANEL_SIZE, position, size):
                    blocked_panels.add((column, row))
    return pole_positions, roboport_positions, big_pole_positions, blocked_panels


def solar_array_dimension_stats(columns, rows):
    """Calculate exact totals without constructing every blueprint entity."""
    pole_positions, roboport_positions, big_pole_positions, blocked_panels = _solar_layout(columns, rows)
    panel_count = columns * rows - len(blocked_panels)
    return {
        "solar_panels": panel_count,
        "substations": len(pole_positions),
        "roboports": len(roboport_positions),
        "big_electric_poles": len(big_pole_positions),
        "peak_output_mw": panel_count * SOLAR_PANEL_OUTPUT_KW / 1000,
    }


def make_solar_array(columns, rows):
    """Build a blueprint containing ``columns`` by ``rows`` solar panels.

    Substations and roboports are placed throughout the resulting 3*columns by
    3*rows tile field. Panels that would collide with infrastructure are omitted.
    Every panel is powered, and the roboports form one connected logistics network
    whose construction area covers the complete field.
    """
    width = columns * PANEL_SIZE
    height = rows * PANEL_SIZE
    pole_positions, roboport_positions, big_pole_positions, blocked_panels = _solar_layout(columns, rows)

    panel_positions = []
    for row in range(rows):
        for column in range(columns):
            if (column, row) not in blocked_panels:
                panel_positions.append(
                    (column * PANEL_SIZE + 1.5, row * PANEL_SIZE + 1.5)
                )

    entities = []
    for position in panel_positions:
        entities.append(
            {
                "entity_number": len(entities) + 1,
                "name": "solar-panel",
                "position": {"x": position[0], "y": position[1]},
            }
        )

    pole_numbers = []
    for position in pole_positions:
        pole_numbers.append(len(entities) + 1)
        entities.append(
            {
                "entity_number": len(entities) + 1,
                "name": "substation",
                "position": {"x": position[0], "y": position[1]},
            }
        )

    for position in roboport_positions:
        entities.append(
            {
                "entity_number": len(entities) + 1,
                "name": "roboport",
                "position": {"x": position[0], "y": position[1]},
            }
        )

    big_pole_numbers = []
    for position in big_pole_positions:
        big_pole_numbers.append(len(entities) + 1)
        entities.append(
            {
                "entity_number": len(entities) + 1,
                "name": "big-electric-pole",
                "position": {"x": position[0], "y": position[1]},
            }
        )

    # Explicit neighbour links make the grid deterministic while retaining all
    # horizontal and vertical connections that are within wire reach.
    pole_by_position = dict(zip(pole_positions, pole_numbers))
    xs = _axis_substation_positions(width)
    ys = _axis_substation_positions(height)
    entity_by_number = {entity["entity_number"]: entity for entity in entities}
    for row, y in enumerate(ys):
        for column, x in enumerate(xs):
            number = pole_by_position[(x, y)]
            neighbours = []
            if column > 0 and x - xs[column - 1] <= SUBSTATION_WIRE_REACH:
                neighbours.append(pole_by_position[(xs[column - 1], y)])
            if column + 1 < len(xs) and xs[column + 1] - x <= SUBSTATION_WIRE_REACH:
                neighbours.append(pole_by_position[(xs[column + 1], y)])
            if row > 0 and y - ys[row - 1] <= SUBSTATION_WIRE_REACH:
                neighbours.append(pole_by_position[(x, ys[row - 1])])
            if row + 1 < len(ys) and ys[row + 1] - y <= SUBSTATION_WIRE_REACH:
                neighbours.append(pole_by_position[(x, ys[row + 1])])
            if neighbours:
                entity_by_number[number]["neighbours"] = neighbours

    # Tie every roboport's adjacent big pole into the powered substation grid.
    for position, number in zip(big_pole_positions, big_pole_numbers):
        nearest_position = min(
            pole_positions,
            key=lambda pole: (pole[0] - position[0]) ** 2 + (pole[1] - position[1]) ** 2,
        )
        if math.dist(position, nearest_position) > BIG_ELECTRIC_POLE_WIRE_REACH:
            raise ValueError("A roboport power pole cannot reach the substation grid")
        substation_number = pole_by_position[nearest_position]
        entity_by_number[number]["neighbours"] = [substation_number]
        entity_by_number[substation_number].setdefault("neighbours", []).append(number)

    output_mw = len(panel_positions) * SOLAR_PANEL_OUTPUT_KW / 1000
    return {
        "blueprint": {
            "item": "blueprint",
            "label": f"Solar array {columns}x{rows} - {output_mw:g} MW",
            "version": BLUEPRINT_VERSION,
            "icons": [
                {"signal": {"type": "item", "name": "solar-panel"}, "index": 1},
                {"signal": {"type": "item", "name": "substation"}, "index": 2},
                {"signal": {"type": "item", "name": "roboport"}, "index": 3},
            ],
            "entities": entities,
        }
    }


def solar_array_stats(blueprint):
    """Return panel, substation, and peak-output totals for a generated array."""
    entities = blueprint["blueprint"]["entities"]
    panel_count = sum(entity["name"] == "solar-panel" for entity in entities)
    substation_count = sum(entity["name"] == "substation" for entity in entities)
    roboport_count = sum(entity["name"] == "roboport" for entity in entities)
    big_pole_count = sum(entity["name"] == "big-electric-pole" for entity in entities)
    return {
        "solar_panels": panel_count,
        "substations": substation_count,
        "roboports": roboport_count,
        "big_electric_poles": big_pole_count,
        "peak_output_mw": panel_count * SOLAR_PANEL_OUTPUT_KW / 1000,
    }


def main():
    parser = argparse.ArgumentParser(
        description="Create a fully powered rectangular solar-panel blueprint."
    )
    parser.add_argument("columns", type=int, help="number of solar-panel columns")
    parser.add_argument("rows", type=int, help="number of solar-panel rows")
    parser.add_argument(
        "--json", action="store_true", help="print blueprint JSON instead of a blueprint string"
    )
    parser.add_argument(
        "--no-clipboard", action="store_true", help="do not copy the blueprint string"
    )
    args = parser.parse_args()

    blueprint = make_solar_array(args.columns, args.rows)
    stats = solar_array_stats(blueprint)
    summary = (
        f'{stats["solar_panels"]} solar panels, '
        f'{stats["substations"]} substations, '
        f'{stats["peak_output_mw"]:g} MW peak output'
    )
    if args.json:
        print(summary)
        print(json.dumps(blueprint, indent=2))
        return

    blueprint_string = convertoToBlueprint(blueprint)
    if not args.no_clipboard:
        pyperclip.copy(blueprint_string)
        print("Blueprint copied to the clipboard.")
    print(summary)
    print(blueprint_string)


if __name__ == "__main__":
    main()
