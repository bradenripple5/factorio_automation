import unittest
from collections import Counter
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import blueprint_builder
import make_station


class StationLayoutTests(unittest.TestCase):
    @staticmethod
    def tiny_station(recipe, **kwargs):
        return {"blueprint": {"item": "blueprint", "entities": [{
            "entity_number": 1,
            "name": "constant-combinator",
            "position": {"x": 0, "y": 0},
        }]}}

    def test_automatic_grid_distributes_partial_rows(self):
        with patch.object(
            make_station,
            "make_solid_ingredient_station",
            side_effect=self.tiny_station,
        ):
            blueprint = make_station.make_solid_ingredient_station_array(
                [f"recipe-{index}" for index in range(22)],
                include_intersections=False,
            )
        markers = [
            entity for entity in blueprint["blueprint"]["entities"]
            if entity["name"] == "constant-combinator"
        ]
        row_counts = Counter(entity["position"]["y"] for entity in markers)
        self.assertEqual(
            [count for _, count in sorted(row_counts.items())],
            [5, 5, 4, 4, 4],
        )

    def test_roboport_rows_contain_no_empty_station_rails(self):
        blueprint = make_station._load_roboport_station_with_center_pole(True)
        names = {entity["name"] for entity in blueprint["blueprint"]["entities"]}
        self.assertEqual(
            names,
            {"roboport", "substation", "big-electric-pole", "radar"},
        )

    def test_roboport_array_defaults_to_four_by_six(self):
        blueprint = make_station._load_roboport_station_with_center_pole(True)
        roboports = [
            entity for entity in blueprint["blueprint"]["entities"]
            if entity["name"] == "roboport"
        ]
        self.assertEqual(len(roboports), 24)
        self.assertEqual(len({entity["position"]["x"] for entity in roboports}), 4)
        self.assertEqual(len({entity["position"]["y"] for entity in roboports}), 6)

        expected_pole_position = {
            "x": sum(entity["position"]["x"] for entity in roboports) / len(roboports),
            "y": max(entity["position"]["y"] for entity in roboports) + 4,
        }
        self.assertTrue(any(
            entity["name"] == "big-electric-pole"
            and entity["position"] == expected_pole_position
            for entity in blueprint["blueprint"]["entities"]
        ))
        upper_pole = next(
            entity for entity in blueprint["blueprint"]["entities"]
            if entity["name"] == "big-electric-pole"
            and entity["position"] == expected_pole_position
        )
        lower_pole = next(
            entity for entity in blueprint["blueprint"]["entities"]
            if entity["name"] == "big-electric-pole"
            and entity["position"] == {
                "x": expected_pole_position["x"],
                "y": expected_pole_position["y"] + 28,
            }
        )
        self.assertIn(lower_pole["entity_number"], upper_pole["neighbours"])
        self.assertIn(upper_pole["entity_number"], lower_pole["neighbours"])
        self.assertTrue(any(
            entity["name"] == "radar"
            and entity["position"] == {
                "x": expected_pole_position["x"],
                "y": expected_pole_position["y"] + 25,
            }
            for entity in blueprint["blueprint"]["entities"]
        ))

        between_blueprint = make_station._load_roboport_station_with_center_pole(
            True, 4, 6, True
        )
        between_entities = between_blueprint["blueprint"]["entities"]
        between_y = expected_pole_position["y"] + 21
        self.assertTrue(any(
            entity["name"] == "roboport"
            and entity["position"] == {
                "x": expected_pole_position["x"], "y": between_y
            }
            for entity in between_entities
        ))
        self.assertTrue(any(
            entity["name"] == "substation"
            and entity["position"] == {
                "x": expected_pole_position["x"] + 3, "y": between_y
            }
            for entity in between_entities
        ))

        substations = [
            entity for entity in blueprint["blueprint"]["entities"]
            if entity["name"] == "substation"
        ]
        self.assertGreaterEqual(len(substations), 4)
        for roboport in roboports:
            self.assertTrue(any(
                abs(roboport["position"]["x"] - substation["position"]["x"]) <= 9
                and abs(roboport["position"]["y"] - substation["position"]["y"]) <= 9
                for substation in substations
            ))

    def test_center_spacing_is_consumed_by_array(self):
        with patch.object(
            make_station,
            "make_solid_ingredient_station",
            side_effect=self.tiny_station,
        ):
            blueprint = make_station.make_solid_ingredient_station_array(
                ["one", "two", "three", "four"],
                station_center_spacing_x=124,
                station_center_spacing_y=66,
                include_intersections=False,
            )
        positions = {
            (entity["position"]["x"], entity["position"]["y"])
            for entity in blueprint["blueprint"]["entities"]
            if entity["name"] == "constant-combinator"
        }
        self.assertEqual(positions, {(4, 0), (128, 0), (4, 66), (128, 66)})

    def test_zero_horizontal_gap_uses_station_footprint(self):
        def station_with_width(recipe, **kwargs):
            return {"blueprint": {"item": "blueprint", "entities": [
                {"entity_number": 1, "name": "constant-combinator",
                 "position": {"x": 0, "y": 0}},
                {"entity_number": 2, "name": "constant-combinator",
                 "position": {"x": 56, "y": 0}},
            ]}}

        layout = {}
        with patch.object(
            make_station,
            "make_solid_ingredient_station",
            side_effect=station_with_width,
        ):
            make_station.make_solid_ingredient_station_array(
                ["one", "two"],
                rows=1,
                cols=2,
                horizontal_spacing=0,
                include_intersections=False,
                layout_metadata=layout,
            )
        self.assertEqual(layout["station_center_spacing_x"], 56)

    def test_roboport_rows_keep_internal_intersection_cells_aligned(self):
        with patch.object(
            make_station,
            "make_solid_ingredient_station",
            side_effect=self.tiny_station,
        ), patch.object(
            make_station,
            "_load_roboport_station_with_center_pole",
            side_effect=lambda enabled, columns, rows, between=False: self.tiny_station("roboport"),
        ):
            blueprint = make_station.make_solid_ingredient_station_array(
                ["one", "two", "three", "four"],
                station_center_spacing_x=124,
                station_center_spacing_y=66,
                include_roboports=True,
                include_intersections=False,
            )
        y_positions = sorted({
            entity["position"]["y"]
            for entity in blueprint["blueprint"]["entities"]
            if entity["name"] == "constant-combinator"
        })
        self.assertEqual(y_positions, [0, 66, 132, 198])

    def test_merged_track_layer_uses_production_row_origin(self):
        station_plan = [
            SimpleNamespace(
                id=f"p{index}", product=f"p{index}",
                parent_ids=set(), child_ids=set(),
            )
            for index in range(4)
        ]
        station_blueprint = {"blueprint": {
            "item": "blueprint",
            "label": "stations",
            "entities": [],
        }}
        track_blueprint = {"blueprint": {"entities": [{
            "entity_number": 1,
            "name": "straight-rail",
            "position": {"x": 10, "y": 10},
        }]}}
        with patch.object(
            blueprint_builder, "plan_product_stations", return_value=station_plan,
        ), patch.object(
            blueprint_builder,
            "make_solid_ingredient_station_array",
            return_value=station_blueprint,
        ), patch.object(
            blueprint_builder, "build_center_track_array", return_value=track_blueprint,
        ) as build_tracks:
            result, _ = blueprint_builder.build_product_station_array(
                "test-product",
                include_roboports=True,
                include_intersections=True,
                include_trains=False,
                station_center_spacing_x=124,
                station_center_spacing_y=66,
            )
        self.assertEqual(
            build_tracks.call_args.kwargs["station_center_spacing_y"], 132
        )
        self.assertEqual(
            build_tracks.call_args.kwargs["additional_crossings"],
            [(32, 0), (156, 0), (32, 132), (156, 132)],
        )
        rail = result["blueprint"]["entities"][0]
        self.assertEqual(rail["position"]["x"], 38)
        self.assertEqual(rail["position"]["y"], 74)

    def test_real_station_layout_does_not_add_duplicate_shared_scaffold(self):
        station_plan = [
            SimpleNamespace(
                id=f"p{index}", product=f"p{index}",
                parent_ids=set(), child_ids=set(),
            )
            for index in range(4)
        ]
        station_blueprint = {"blueprint": {
            "item": "blueprint", "label": "stations", "entities": [],
        }}

        def build_station_array(*args, **kwargs):
            kwargs["layout_metadata"].update({
                "station_center_spacing_x": 56,
                "station_center_spacing_y": 66,
                "production_positions": [(0, 0), (0, 1), (1, 0), (1, 1)],
            })
            return station_blueprint

        with patch.object(
            blueprint_builder, "plan_product_stations", return_value=station_plan,
        ), patch.object(
            blueprint_builder,
            "make_solid_ingredient_station_array",
            side_effect=build_station_array,
        ), patch.object(
            blueprint_builder, "build_center_track_array",
        ) as build_tracks:
            result, _ = blueprint_builder.build_product_station_array(
                "test-product",
                include_roboports=True,
                include_intersections=True,
                include_trains=False,
            )
        build_tracks.assert_not_called()
        self.assertIs(result, station_blueprint)

    def test_real_station_array_builds_its_own_intersections(self):
        station_plan = [
            SimpleNamespace(
                id=f"p{index}", product=f"p{index}",
                parent_ids=set(), child_ids=set(),
            )
            for index in range(4)
        ]
        station_blueprint = {"blueprint": {
            "item": "blueprint", "label": "stations", "entities": [],
        }}

        def build_station_array(*args, **kwargs):
            kwargs["layout_metadata"].update({
                "station_center_spacing_x": 56,
                "station_center_spacing_y": 66,
                "production_positions": [(0, 0), (0, 1), (1, 0), (1, 1)],
            })
            return station_blueprint

        with patch.object(
            blueprint_builder, "plan_product_stations", return_value=station_plan,
        ), patch.object(
            blueprint_builder,
            "make_solid_ingredient_station_array",
            side_effect=build_station_array,
        ) as build_array:
            blueprint_builder.build_product_station_array(
                "test-product",
                include_intersections=True,
                include_trains=False,
            )
        self.assertTrue(build_array.call_args.kwargs["include_intersections"])

    def test_dependency_ordering_reduces_train_travel(self):
        stations = [
            SimpleNamespace(
                id=f"s{index}", product=f"p{index}",
                parent_ids={f"s{index - 1}"} if index else set(),
                child_ids={f"s{index + 1}"} if index < 8 else set(),
            )
            for index in range(9)
        ]
        scrambled = [stations[index] for index in (0, 8, 1, 7, 2, 6, 3, 5, 4)]

        def route_cost(order):
            positions = {station.id: divmod(index, 3) for index, station in enumerate(order)}
            return sum(
                abs(positions[f"s{i}"][0] - positions[f"s{i + 1}"][0])
                + abs(positions[f"s{i}"][1] - positions[f"s{i + 1}"][1])
                for i in range(8)
            )

        optimized = blueprint_builder.optimize_station_order(
            scrambled, include_roboports=False
        )
        self.assertLess(route_cost(optimized), route_cost(scrambled))

    def test_product_array_preserves_original_station_order(self):
        station_plan = [
            SimpleNamespace(
                id=f"s{index}", product=product,
                parent_ids=set(), child_ids=set(),
            )
            for index, product in enumerate(("first", "second", "third"))
        ]
        station_blueprint = {"blueprint": {
            "item": "blueprint", "entities": [],
        }}
        with patch.object(
            blueprint_builder, "plan_product_stations", return_value=station_plan,
        ), patch.object(
            blueprint_builder,
            "make_solid_ingredient_station_array",
            return_value=station_blueprint,
        ) as build_array:
            _, ingredients = blueprint_builder.build_product_station_array(
                "test-product",
                include_roboports=False,
                include_intersections=False,
                radial_layout=False,
            )
        self.assertEqual(ingredients, ["first", "second", "third"])
        self.assertIs(build_array.call_args.args[0], station_plan)

    def test_radial_layout_centers_product_and_pushes_dependencies_outward(self):
        models = [
            SimpleNamespace(id="final", product="final", parent_ids={"direct"}, child_ids=set(), trains_per_station=1, inserter_type="bulk-inserter"),
            SimpleNamespace(id="direct", product="direct", parent_ids={"raw"}, child_ids={"final"}, trains_per_station=1, inserter_type="bulk-inserter"),
            SimpleNamespace(id="raw", product="raw", parent_ids=set(), child_ids={"direct"}, trains_per_station=1, inserter_type="bulk-inserter"),
        ]
        layout = {}
        with patch.object(
            make_station,
            "make_solid_ingredient_station",
            side_effect=self.tiny_station,
        ):
            make_station.make_solid_ingredient_station_array(
                models,
                rows=3,
                cols=3,
                include_intersections=False,
                radial_layout=True,
                layout_metadata=layout,
                empty_requester_chests=False,
            )
        positions = layout["production_positions"]
        center = (1, 1)
        distance = lambda position: abs(position[0] - 1) + abs(position[1] - 1)
        self.assertEqual(positions[0], center)
        self.assertLessEqual(distance(positions[1]), distance(positions[2]))


class OneFluidChemicalTemplateTests(unittest.TestCase):
    def test_lubricant_uses_requested_template(self):
        station = make_station.make_solid_ingredient_station("lubricant")
        entities = station["blueprint"]["entities"]
        self.assertTrue(any(
            entity["name"] == "chemical-plant"
            and entity.get("recipe") == "lubricant"
            for entity in entities
        ))

    def test_sulfuric_acid_reskins_requested_template(self):
        station = make_station.make_solid_ingredient_station("sulfuric-acid")
        serialized = str(station["blueprint"])
        self.assertIn("sulfuric-acid", serialized)
        self.assertIn("water", serialized)
        self.assertNotIn("lubricant", serialized)
        self.assertNotIn("heavy-oil", serialized)
        self.assertEqual(
            make_station.ONE_SOLID_ONE_FLUID_CHEMICAL_STATION_TEMPLATE,
            Path(
                "blueprints/stations/chemical_plant_fluid_from_one_solid_and_one_fluid/"
                "sulfuric_acid_station.json"
            ),
        )


class TwoFluidSolidChemicalTemplateTests(unittest.TestCase):
    def test_sulfur_uses_two_fluid_solid_template(self):
        station = make_station.make_solid_ingredient_station("sulfur")
        root = station["blueprint"]
        self.assertTrue(any(
            entity["name"] == "chemical-plant"
            and entity.get("recipe") == "sulfur"
            for entity in root["entities"]
        ))
        serialized = str(root)
        self.assertIn("sulfur dropoff water", serialized)
        self.assertIn("sulfur dropoff petroleum-gas", serialized)


class AssemblerAndFurnaceTemplateTests(unittest.TestCase):
    def test_assembler_recipe_uses_copper_cable_template(self):
        station = make_station.make_solid_ingredient_station("electronic-circuit")
        self.assertTrue(any(
            entity["name"] == "assembling-machine-3"
            and entity.get("recipe") == "electronic-circuit"
            for entity in station["blueprint"]["entities"]
        ))

    def test_furnace_recipe_uses_copper_cable_template(self):
        station = make_station.make_solid_ingredient_station("iron-plate")
        self.assertTrue(any(
            entity["name"] == "electric-furnace"
            and entity.get("recipe") == "iron-plate"
            for entity in station["blueprint"]["entities"]
        ))

    def test_advanced_circuit_can_build_its_plastic_bar_station(self):
        station = make_station._make_plastic_bar_station_with_trains()
        entities = station["blueprint"]["entities"]
        self.assertTrue(any(
            entity["name"] == "chemical-plant"
            and entity.get("recipe") == "plastic-bar"
            for entity in entities
        ))
        self.assertTrue(any(
            entity["name"] == "train-stop"
            and "plastic-bar" in entity.get("station", "")
            for entity in entities
        ))


if __name__ == "__main__":
    unittest.main()
