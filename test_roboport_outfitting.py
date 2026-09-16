import unittest

from blueprint_builder import outfit_roboports_with_inserters
from convert_json_to_blueprint_string import convertoToBlueprint


class RoboportOutfittingTests(unittest.TestCase):
    def transform(self, entities):
        source = {"blueprint": {"item": "blueprint", "entities": entities}}
        return outfit_roboports_with_inserters(convertoToBlueprint(source))["blueprint"]["entities"]

    def test_redirects_adjacent_inserter_and_adds_chest(self):
        entities = self.transform([
            {"entity_number": 1, "name": "roboport", "position": {"x": 0, "y": 0}},
            {"entity_number": 2, "name": "fast-inserter", "position": {"x": 2.5, "y": 0.5}, "direction": 12},
        ])
        inserter = next(entity for entity in entities if entity["name"] == "fast-inserter")
        chest = next(entity for entity in entities if entity["name"] == "steel-chest")
        self.assertEqual(inserter["direction"], 4)
        self.assertEqual(chest["position"], {"x": 3.5, "y": 0.5})

    def test_adds_pair_when_missing(self):
        entities = self.transform([
            {"entity_number": 7, "name": "roboport", "position": {"x": 10, "y": 20}},
        ])
        inserter = next(entity for entity in entities if entity["name"] == "inserter")
        chest = next(entity for entity in entities if entity["name"] == "steel-chest")
        self.assertEqual(inserter["position"], {"x": 9.5, "y": 17.5})
        self.assertEqual(inserter["direction"], 0)
        self.assertEqual(chest["position"], {"x": 9.5, "y": 16.5})

    def test_rejects_blueprint_without_roboports(self):
        with self.assertRaisesRegex(ValueError, "contains no roboports"):
            self.transform([])


if __name__ == "__main__":
    unittest.main()
