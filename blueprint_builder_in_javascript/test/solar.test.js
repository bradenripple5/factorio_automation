import test from "node:test";
import assert from "node:assert/strict";
import { makeSolarArray, solarStats } from "../src/solar.js";

test("20x10 solar array matches the Python generator", () => {
  assert.deepEqual(solarStats(20, 10), {
    solarPanels: 176,
    substations: 8,
    peakOutputMw: 10.56,
  });
  const blueprint = makeSolarArray(20, 10);
  assert.equal(blueprint.blueprint.entities.length, 184);
  assert.equal(new Set(blueprint.blueprint.entities.map((entity) => entity.entity_number)).size, 184);
});
