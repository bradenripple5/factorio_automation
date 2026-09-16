"""Logical production-station model used before blueprint placement."""

import copy
import math
from dataclasses import dataclass, field


@dataclass(frozen=True)
class StationEndpoint:
    """A physical stop paired with the reversing midpoint that serves it."""

    id: str
    station_name: str
    midpoint_name: str
    role: str
    item: str
    reverse_turn_direction: str = "right"
    reverse_turn_degrees: int = 90

    def __post_init__(self):
        if self.role not in {"pickup", "dropoff"}:
            raise ValueError("Station endpoint role must be pickup or dropoff")
        if self.midpoint_name != f"{self.station_name} midpoint":
            raise ValueError("A midpoint name must be its station name plus ' midpoint'")
        if self.reverse_turn_direction != "right" or self.reverse_turn_degrees != 90:
            raise ValueError("Station endpoints must reverse through a 90-degree right turn")


@dataclass
class Station:
    """One physical production station and its routing relationships."""

    product: str
    id: str
    trains_per_station: int = 1
    inserter_type: str = "bulk-inserter"
    parent_ids: set[str] = field(default_factory=set)
    child_ids: set[str] = field(default_factory=set)
    endpoints: dict[str, StationEndpoint] = field(default_factory=dict)
    controlled_inserters: dict[str, tuple[int, ...]] = field(
        default_factory=dict, init=False
    )
    _blueprint: dict | None = field(default=None, init=False, repr=False, compare=False)

    def __post_init__(self):
        if not isinstance(self.product, str) or not self.product.strip():
            raise ValueError("Station product must be a non-empty string")
        if not isinstance(self.id, str) or not self.id.strip():
            raise ValueError("Station id must be a non-empty string")
        if (
            not isinstance(self.trains_per_station, int)
            or isinstance(self.trains_per_station, bool)
            or self.trains_per_station < 1
        ):
            raise ValueError("trains_per_station must be a positive integer")
        if not isinstance(self.inserter_type, str) or not self.inserter_type.endswith(
            "inserter"
        ):
            raise ValueError("inserter_type must be a Factorio inserter entity name")
        self.product = self.product.strip().replace(" ", "-")
        self.id = self.id.strip()
        self.ensure_pickup_endpoint()

    def ensure_pickup_endpoint(self):
        station_name = f"{self.id} pickup"
        return self._ensure_endpoint("pickup", self.product, station_name)

    def ensure_dropoff_endpoint(self, ingredient):
        ingredient = ingredient.strip().replace(" ", "-")
        station_name = f"{self.id} dropoff {ingredient}"
        return self._ensure_endpoint("dropoff", ingredient, station_name)

    def _ensure_endpoint(self, role, item, station_name):
        endpoint_id = f"{self.id}:{role}:{item}"
        endpoint = self.endpoints.get(endpoint_id)
        if endpoint is None:
            endpoint = StationEndpoint(
                id=endpoint_id,
                station_name=station_name,
                midpoint_name=f"{station_name} midpoint",
                role=role,
                item=item,
            )
            self.endpoints[endpoint_id] = endpoint
        return endpoint

    def connect_to(self, consumer):
        """Establish this producer as a parent of ``consumer``."""
        if not isinstance(consumer, Station):
            raise TypeError("consumer must be a Station")
        if consumer.id == self.id:
            return
        self.child_ids.add(consumer.id)
        consumer.parent_ids.add(self.id)
        consumer.ensure_dropoff_endpoint(self.product)

    def get_product(self):
        """Compatibility accessor for older callers."""
        return self.product

    @property
    def blueprint(self):
        """Build and cache this station's ID-bound Factorio blueprint."""
        if self._blueprint is None:
            self._blueprint = self._build_blueprint()
        return self._blueprint

    def get_blueprint(self, *, copy_blueprint=True):
        """Return this station blueprint, optionally as its cached object."""
        return copy.deepcopy(self.blueprint) if copy_blueprint else self.blueprint

    def _build_blueprint(self):
        # Imported lazily to avoid a Station.py <-> make_station.py import cycle.
        from make_station import (
            _make_plastic_bar_station_with_trains,
            make_solid_ingredient_station,
        )

        if self.product == "plastic-bar":
            blueprint = _make_plastic_bar_station_with_trains(
                inserter=self.inserter_type,
                empty_requester_chests=True,
                trains_per_stop=self.trains_per_station,
            )
        else:
            blueprint = make_solid_ingredient_station(
                self.product,
                inserter=self.inserter_type,
                empty_requester_chests=True,
                trains_per_stop=self.trains_per_station,
            )

        def identify_endpoint(station_name):
            if not station_name:
                return station_name
            is_midpoint = station_name.endswith(" midpoint")
            base_name = station_name.removesuffix(" midpoint")
            if base_name == f"{self.product} pickup":
                endpoint = self.ensure_pickup_endpoint()
            elif base_name.startswith(f"{self.product} dropoff "):
                ingredient = base_name.removeprefix(f"{self.product} dropoff ")
                endpoint = self.ensure_dropoff_endpoint(ingredient)
            else:
                return station_name
            return endpoint.midpoint_name if is_midpoint else endpoint.station_name

        root = blueprint["blueprint"]
        for entity in root.get("entities", []):
            if entity.get("name", "").endswith("inserter"):
                entity["name"] = self.inserter_type
            if entity.get("name") == "train-stop":
                entity["station"] = identify_endpoint(entity.get("station"))
        for schedule in root.get("schedules", []):
            schedule_value = schedule.get("schedule", {})
            records = (
                schedule_value.get("records", [])
                if isinstance(schedule_value, dict)
                else schedule_value
            )
            for record in records:
                record["station"] = identify_endpoint(record.get("station"))
        self._deduplicate_train_routes(root)
        self._add_dropoff_inserter_controls(root)
        self._add_midpoint_train_controls(root)
        root["label"] = f"{self.id} station"
        return blueprint

    def _add_midpoint_train_controls(self, root):
        """Set a midpoint limit to zero while its train is stopped there."""
        entities = root.get("entities", [])
        midpoints = [
            entity
            for entity in entities
            if entity.get("name") == "train-stop"
            and entity.get("station", "").endswith(" midpoint")
        ]
        rails = [
            entity
            for entity in entities
            if "rail" in entity.get("name", "")
            and entity.get("name") not in {"rail-signal", "rail-chain-signal"}
        ]
        wires = root.setdefault("wires", [])
        next_entity_number = max(entity["entity_number"] for entity in entities) + 1

        def distance(first, second):
            first_position = first["position"]
            second_position = second["position"]
            return math.hypot(
                float(first_position["x"]) - float(second_position["x"]),
                float(first_position["y"]) - float(second_position["y"]),
            )

        for midpoint in midpoints:
            behavior = midpoint.setdefault("control_behavior", {})
            behavior["read_stopped_train"] = True
            behavior.pop("train_stopped_signal", None)
            behavior.pop("circuit_enable_disable", None)
            behavior.pop("circuit_condition", None)
            behavior["set_trains_limit"] = True
            behavior["trains_limit_signal"] = {
                "type": "virtual",
                "name": "signal-L",
            }

            nearest_rail = min(rails, key=lambda rail: distance(midpoint, rail))
            stop_position = midpoint["position"]
            rail_position = nearest_rail["position"]
            # Midpoint templates reserve a combinator-sized space on the far
            # side of the track. Continue from the stop through the nearest
            # rail, then 1.5 tiles beyond it (for example: stop x=-77,
            # rail x=-79, combinator x=-80.5).
            dx = float(rail_position["x"]) - float(stop_position["x"])
            dy = float(rail_position["y"]) - float(stop_position["y"])
            length = math.hypot(dx, dy) or 1
            combinator = {
                "entity_number": next_entity_number,
                "name": "decider-combinator",
                "position": {
                    "x": float(rail_position["x"]) + 1.5 * dx / length,
                    "y": float(rail_position["y"]) + 1.5 * dy / length,
                },
                "control_behavior": {
                    "decider_conditions": {
                        "conditions": [
                            {
                                "first_signal": {
                                    "type": "virtual",
                                    "name": "signal-T",
                                },
                                "constant": 0,
                                "comparator": "=",
                            }
                        ],
                        "outputs": [
                            {
                                "signal": {
                                    "type": "virtual",
                                    "name": "signal-L",
                                },
                                "copy_count_from_input": False,
                            }
                        ],
                    }
                },
            }
            entities.append(combinator)
            # Input reads T from the stop; output returns L=1 only when T=0.
            wires.append(
                [midpoint["entity_number"], 1, next_entity_number, 1]
            )
            wires.append(
                [next_entity_number, 3, midpoint["entity_number"], 1]
            )
            next_entity_number += 1

    def _deduplicate_train_routes(self, root):
        """Keep at most the configured number of trains on an endpoint pair."""
        graph = {}
        for connection in root.get("stock_connections", []):
            stock = connection["stock"]
            graph.setdefault(stock, set())
            for end in ("front", "back"):
                if end in connection:
                    neighbour = connection[end]
                    graph[stock].add(neighbour)
                    graph.setdefault(neighbour, set()).add(stock)

        def consist(schedule):
            members = set(schedule.get("locomotives", []))
            pending = list(members)
            while pending:
                current = pending.pop()
                for neighbour in graph.get(current, ()):
                    if neighbour not in members:
                        members.add(neighbour)
                        pending.append(neighbour)
            return members

        route_counts = {}
        kept_schedules = []
        removed_stock = set()
        for schedule in root.get("schedules", []):
            schedule_value = schedule.get("schedule", {})
            records = (
                schedule_value.get("records", [])
                if isinstance(schedule_value, dict)
                else schedule_value
            )
            endpoints = frozenset(
                record.get("station", "").removesuffix(" midpoint")
                for record in records
                if record.get("station")
                and not record["station"].endswith(" midpoint")
            )
            if len(endpoints) != 2:
                raise ValueError("Every train schedule must connect two endpoints")
            count = route_counts.get(endpoints, 0)
            if count >= self.trains_per_station:
                removed_stock.update(consist(schedule))
                continue
            route_counts[endpoints] = count + 1
            kept_schedules.append(schedule)

        if removed_stock:
            root["entities"] = [
                entity
                for entity in root.get("entities", [])
                if entity["entity_number"] not in removed_stock
            ]
            root["stock_connections"] = [
                connection
                for connection in root.get("stock_connections", [])
                if connection["stock"] not in removed_stock
                and connection.get("front") not in removed_stock
                and connection.get("back") not in removed_stock
            ]
        root["schedules"] = kept_schedules

    def _add_dropoff_inserter_controls(self, root):
        """Enable rail-side unloaders only while their dropoff train is stopped."""
        entities = root.get("entities", [])
        stops = [
            entity
            for entity in entities
            if entity.get("name") == "train-stop"
            and not entity.get("station", "").endswith(" midpoint")
        ]
        dropoffs = {
            stop["entity_number"]: stop
            for stop in stops
            if " dropoff " in stop.get("station", "")
        }
        rails = [
            entity
            for entity in entities
            if "rail" in entity.get("name", "")
            and entity.get("name") not in {"rail-signal", "rail-chain-signal"}
        ]
        chests = [
            entity
            for entity in entities
            if entity.get("name") == "active-provider-chest"
        ]
        underground_belts = [
            entity
            for entity in entities
            if "underground-belt" in entity.get("name", "")
        ]
        def position(entity):
            value = entity["position"]
            return float(value["x"]), float(value["y"])

        def distance(first, second):
            ax, ay = position(first)
            bx, by = position(second)
            return math.hypot(ax - bx, ay - by)

        groups = {number: [] for number in dropoffs}
        # Factorio inserter direction expressed as the tile containing its
        # drop target. Only rail -> active-provider-chest inserters unload.
        drop_vectors = {
            0: (0, 1),
            4: (-1, 0),
            8: (0, -1),
            12: (1, 0),
        }
        for inserter in entities:
            if not inserter.get("name", "").endswith("inserter"):
                continue
            drop_vector = drop_vectors.get(inserter.get("direction", 0))
            if drop_vector is None:
                continue

            ix, iy = position(inserter)
            chest = next(
                (
                    candidate
                    for candidate in chests
                    if position(candidate)
                    == (ix + drop_vector[0], iy + drop_vector[1])
                ),
                None,
            )
            if chest is None:
                continue
            cx, cy = position(chest)
            chest_vector = (cx - ix, cy - iy)
            rail_candidates = []
            for rail in rails:
                rx, ry = position(rail)
                dx, dy = rx - ix, ry - iy
                projection = -(dx * chest_vector[0] + dy * chest_vector[1])
                perpendicular = abs(dx * chest_vector[1] - dy * chest_vector[0])
                if 0.25 <= projection <= 3.5 and perpendicular <= 1.5:
                    rail_candidates.append((projection, rail))
            if not rail_candidates:
                continue
            rail_projection, _ = min(rail_candidates, key=lambda value: value[0])

            obstructed = False
            for belt in underground_belts:
                bx, by = position(belt)
                dx, dy = bx - ix, by - iy
                projection = -(dx * chest_vector[0] + dy * chest_vector[1])
                perpendicular = abs(dx * chest_vector[1] - dy * chest_vector[0])
                if -0.1 <= projection < rail_projection and perpendicular <= 0.75:
                    obstructed = True
                    break
            if obstructed:
                continue

            nearest_stop = min(
                stops, key=lambda stop: distance(inserter, stop)
            )
            stop_number = nearest_stop["entity_number"]
            if stop_number in dropoffs:
                groups[stop_number].append(inserter)

        wires = root.setdefault("wires", [])
        existing_wires = {tuple(wire) for wire in wires}

        # Apply the stopped-train sensor to every physical dropoff, including a
        # spare bay that happens to have no eligible unloading inserters.
        for stop in dropoffs.values():
            behavior = stop.setdefault("control_behavior", {})
            behavior["read_stopped_train"] = True
            behavior.pop("train_stopped_signal", None)

        def add_red_wire(first, second):
            wire = (first, 1, second, 1)
            reverse = (second, 1, first, 1)
            if wire not in existing_wires and reverse not in existing_wires:
                wires.append(list(wire))
                existing_wires.add(wire)

        self.controlled_inserters = {}
        for stop_number, inserters in groups.items():
            if not inserters:
                continue
            stop = dropoffs[stop_number]
            for inserter in inserters:
                inserter_behavior = inserter.setdefault("control_behavior", {})
                inserter_behavior["circuit_enable_disable"] = True
                inserter_behavior["circuit_condition"] = {
                    "first_signal": {"type": "virtual", "name": "signal-T"},
                    "constant": 0,
                    "comparator": ">",
                }

            # A circuit wire reaches only nine tiles. Build a short-edge spanning
            # tree so the stopped-train signal propagates across the whole bank.
            connected = [stop]
            remaining = list(inserters)
            available_relays = list(chests) + [
                entity
                for entity in entities
                if entity.get("name") in {
                    "small-electric-pole",
                    "medium-electric-pole",
                    "big-electric-pole",
                    "substation",
                }
            ]
            while remaining:
                edge_distance, source, target = min(
                    [
                        (distance(source, target), source, target)
                        for source in connected
                        for target in remaining
                    ],
                    key=lambda edge: edge[0],
                )
                if edge_distance > 9:
                    relay_edges = [
                        (distance(source, relay), source, relay)
                        for source in connected
                        for relay in available_relays
                        if distance(source, relay) <= 9
                    ]
                    if not relay_edges:
                        # Preserve every in-range connection already made, but
                        # never reject blueprint generation solely because the
                        # template has no relay capable of spanning this gap.
                        break
                    _, relay_source, relay = min(
                        relay_edges,
                        key=lambda edge: min(
                            distance(edge[2], destination)
                            for destination in remaining
                        ),
                    )
                    add_red_wire(
                        relay_source["entity_number"], relay["entity_number"]
                    )
                    connected.append(relay)
                    available_relays.remove(relay)
                    continue
                add_red_wire(source["entity_number"], target["entity_number"])
                connected.append(target)
                remaining.remove(target)
            self.controlled_inserters[stop["station"]] = tuple(
                inserter["entity_number"] for inserter in inserters
            )


def build_station_tree(
    products,
    trains_per_station=1,
    inserter_type="bulk-inserter",
    ingredient_lookup=None,
):
    """Create uniquely identified stations and connect producers to consumers.

    When several stations produce the same ingredient, consumers are assigned
    round-robin. This creates one unambiguous producer relationship per required
    ingredient while still distributing routes across duplicate stations.
    """
    if ingredient_lookup is None:
        from recipe_extraction import get_recipe

        ingredient_lookup = get_recipe

    stations = [
        Station(
            product=product,
            id=f'{str(product).strip().replace(" ", "-")}-{index:03d}',
            trains_per_station=trains_per_station,
            inserter_type=inserter_type,
        )
        for index, product in enumerate(products, 1)
    ]
    producers = {}
    for station in stations:
        producers.setdefault(station.product, []).append(station)

    next_producer = {}
    for consumer in stations:
        for ingredient in dict.fromkeys(ingredient_lookup(consumer.product) or []):
            consumer.ensure_dropoff_endpoint(ingredient)
            candidates = producers.get(ingredient, [])
            if not candidates:
                continue
            index = next_producer.get(ingredient, 0)
            producer = candidates[index % len(candidates)]
            next_producer[ingredient] = index + 1
            producer.connect_to(consumer)
    return stations
