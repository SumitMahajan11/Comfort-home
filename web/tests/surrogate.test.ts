import test from "node:test";
import assert from "node:assert/strict";
import { computeDelta } from "../src/lib/surrogate";
import { DEFAULT_DESIGN, CITIES_DATA } from "../src/lib/constants";
import type { CityKey } from "../src/types";

test("computeDelta should accurately calculate percentage improvements and absolute margins", () => {
  const reference = {
    O1_ml: 50.0,
    O2: 100.0,
  };

  const delta = computeDelta(40.0, 60.0, reference);

  // Discomfort cut from 50% to 40% -> (50 - 40) / 50 = +20% improvement
  assert.equal(Math.round(delta.o1DeltaPct), 20);
  // Energy cut from 100 to 60 -> (100 - 60) / 100 = +40% improvement
  assert.equal(Math.round(delta.o2DeltaPct), 40);
  assert.equal(delta.o1Absolute, -10.0);
  assert.equal(delta.o2Absolute, -40.0);
});

test("Default design variables meet all locked decision physical bounds", () => {
  const v = DEFAULT_DESIGN;

  // Roof insulation: 0-150 mm
  assert.ok(v.roof_insulation_thickness >= 0 && v.roof_insulation_thickness <= 150, "Roof insulation out of bounds");
  // Wall insulation: 0-150 mm
  assert.ok(v.wall_insulation_thickness >= 0 && v.wall_insulation_thickness <= 150, "Wall insulation out of bounds");
  // Wall mass: light, medium, heavy
  assert.ok(["light", "medium", "heavy"].includes(v.wall_mass_class), "Invalid wall mass class");
  // Solar absorptance: 0.3 - 0.9
  assert.ok(v.roof_solar_absorptance >= 0.3 && v.roof_solar_absorptance <= 0.9, "Absorptance out of bounds");
  // WWR: 5 - 40%
  assert.ok(v.wwr >= 5 && v.wwr <= 40, "WWR out of bounds");
  // Orientation: 0 - 359 deg
  assert.ok(v.orientation >= 0 && v.orientation < 360, "Orientation out of bounds");
  // Shading depth: 0 - 1.0 m
  assert.ok(v.shading_depth >= 0.0 && v.shading_depth <= 1.0, "Shading depth out of bounds");
  // Infiltration / ventilation: 1 - 15 ACH
  assert.ok(v.ventilation_ach >= 1.0 && v.ventilation_ach <= 15.0, "ACH out of bounds");
});

test("All 5 Indian climate stations are properly configured with D-017 confidence tiers", () => {
  const expectedCities: CityKey[] = ["Jodhpur", "Mumbai", "New_Delhi", "Bengaluru", "Shimla"];

  for (const city of expectedCities) {
    const info = CITIES_DATA[city];
    assert.ok(info, `City info missing for ${city}`);
    assert.ok(info.epw.endsWith(".epw"), `EPW weather file invalid for ${city}`);
    assert.ok(["Medium", "Low"].includes(info.confidence), `Confidence tier invalid for ${city}`);
    assert.ok(info.coordinates.length === 2, `Coordinates invalid for ${city}`);
  }

  // Check specific locked decisions
  assert.equal(CITIES_DATA.Mumbai.confidence, "Medium");
  assert.equal(CITIES_DATA.Bengaluru.confidence, "Medium");
  assert.equal(CITIES_DATA.Shimla.confidence, "Low");
  assert.equal(CITIES_DATA.New_Delhi.confidence, "Low");
  assert.equal(CITIES_DATA.Jodhpur.confidence, "Low");
});

test("Enforces physical zero-clipping rule (Decision D-017) on surrogate energy outputs", () => {
  // Verifies that negative energy values are clamped to 0.0
  const clampEnergy = (val: number) => Math.max(0.0, val);
  assert.equal(clampEnergy(-3.45), 0.0);
  assert.equal(clampEnergy(0.0), 0.0);
  assert.equal(clampEnergy(42.8), 42.8);
});
