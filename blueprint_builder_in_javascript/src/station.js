export class Station {
  constructor(product, id, trainsPerStation = 1) {
    if (!String(product).trim()) throw new Error("Station product is required");
    if (!String(id).trim()) throw new Error("Station ID is required");
    if (!Number.isInteger(trainsPerStation) || trainsPerStation < 1) {
      throw new Error("Trains per station must be a positive integer");
    }
    this.product = String(product).trim().replaceAll(" ", "-");
    this.id = String(id).trim();
    this.trainsPerStation = trainsPerStation;
    this.parentIds = new Set();
    this.childIds = new Set();
  }

  connectTo(consumer) {
    if (!(consumer instanceof Station)) throw new TypeError("Consumer must be a Station");
    if (consumer.id === this.id) return;
    this.childIds.add(consumer.id);
    consumer.parentIds.add(this.id);
  }
}

export function buildStationTree(products, ingredientMap = {}, trainsPerStation = 1) {
  const stations = products.map((product, index) =>
    new Station(product, `${String(product).trim().replaceAll(" ", "-")}-${String(index + 1).padStart(3, "0")}`, trainsPerStation),
  );
  const producers = new Map();
  for (const station of stations) {
    if (!producers.has(station.product)) producers.set(station.product, []);
    producers.get(station.product).push(station);
  }
  const cursors = new Map();
  for (const consumer of stations) {
    for (const ingredient of new Set(ingredientMap[consumer.product] ?? [])) {
      const candidates = producers.get(ingredient) ?? [];
      if (!candidates.length) continue;
      const cursor = cursors.get(ingredient) ?? 0;
      candidates[cursor % candidates.length].connectTo(consumer);
      cursors.set(ingredient, cursor + 1);
    }
  }
  return stations;
}
