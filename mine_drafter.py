from draftsman.blueprintable import Blueprint, BlueprintBook
from draftsman.entity import StraightRail
from draftsman.constants import Direction
from draftsman.classes.vector import Vec2
import base64

# ---- Config ----

station_blueprint_string = "0eNq..."  # Replace with your mining outpost blueprint
ore_patches = [
    {'x': 200, 'y': 280, 'type': 'iron-ore'},
    {'x': 300, 'y': 270, 'type': 'copper-ore'},
    {'x': 400, 'y': 240, 'type': 'coal'},
]
main_rail_y = 50

# ---- Load station blueprint ----

station_bp = Blueprint.decode(station_blueprint_string)

# ---- Create blueprint book ----

book = BlueprintBook()

for i, patch in enumerate(ore_patches):
    bp = Blueprint()

    # Copy station
    shifted_station = station_bp.copy()
    shift_vector = Vec2(patch["x"], patch["y"])
    shifted_station.shift(shift_vector)
    for entity in shifted_station.entities:
        bp.entities.append(entity)

    # Build straight rail from patch to main line
    rail_x = patch['x']
    y1, y2 = sorted([patch['y'], main_rail_y])
    for y in range(int(y1), int(y2)):
        rail = StraightRail(position=(rail_x, y + 0.5), direction=Direction.NORTH)
        bp.entities.append(rail)

    bp.label = f"{patch['type'].capitalize()} Outpost {i+1}"
    book.append(bp)

# ---- Output the blueprint book string ----

book_string = book.to_string()
print("Blueprint book string:\n")
print(book_string)
