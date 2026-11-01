/**
 * web/tests/evaluate_clamp.test.ts
 *
 * Unit tests verifying:
 * 1. Out-of-range query params are strictly clamped to sampling bounds in src/sim/sampler.py.
 * 2. Invalid inputs (NaN, negative, beyond max, invalid strings) are sanitized deterministically.
 * 3. Sampled range validity checks identify out-of-bounds variables.
 * 4. Nearest verified Pareto design finder returns valid EnergyPlus verified designs.
 */

import { test } from "node:test";
import assert from "node:assert/strict";
import {
  SAMPLER_BOUNDS,
  clampDesignVariables,
  checkSampledRangeValidity,
  findNearestVerifiedParetoDesign
} from "../src/lib/design_params";
import { DEFAULT_DESIGN } from "../src/lib/constants";
import { CityKey } from "../src/types";

test("Sampling bounds match src/sim/sampler.py exactly", () => {
  // Sampling bounds from Latin Hypercube sampler in src/sim/sampler.py:
  assert.equal(SAMPLER_BOUNDS.roof_insulation_thickness.min, 0);
  assert.equal(SAMPLER_BOUNDS.roof_insulation_thickness.max, 150);

  assert.equal(SAMPLER_BOUNDS.wall_insulation_thickness.min, 0);
  assert.equal(SAMPLER_BOUNDS.wall_insulation_thickness.max, 150);

  assert.deepEqual(SAMPLER_BOUNDS.wall_mass_class, ["light", "medium", "heavy"]);

  assert.equal(SAMPLER_BOUNDS.roof_solar_absorptance.min, 0.30);
  assert.equal(SAMPLER_BOUNDS.roof_solar_absorptance.max, 0.90);

  assert.equal(SAMPLER_BOUNDS.wwr.min, 5);
  assert.equal(SAMPLER_BOUNDS.wwr.max, 40);

  assert.equal(SAMPLER_BOUNDS.orientation.min, 0);
  assert.equal(SAMPLER_BOUNDS.orientation.max, 360);

  assert.equal(SAMPLER_BOUNDS.shading_depth.min, 0.0);
  assert.equal(SAMPLER_BOUNDS.shading_depth.max, 1.0);

  assert.equal(SAMPLER_BOUNDS.ventilation_ach.min, 1.0);
  assert.equal(SAMPLER_BOUNDS.ventilation_ach.max, 15.0);
});

test("Out-of-range query parameters are strictly clamped to lower bounds", () => {
  const extremeLowParams = {
    roof_ins: "-50",
    wall_ins: "-100",
    mass: "paper",
    absorp: "0.10",
    wwr: "1",
    orient: "-90",
    shading: "-2.5",
    vent: "0.1"
  };

  const clamped = clampDesignVariables(extremeLowParams);

  assert.equal(clamped.roof_insulation_thickness, 0, "Negative roof insulation must clamp to 0 mm");
  assert.equal(clamped.wall_insulation_thickness, 0, "Negative wall insulation must clamp to 0 mm");
  assert.equal(clamped.wall_mass_class, "medium", "Invalid mass class must default to medium");
  assert.equal(clamped.roof_solar_absorptance, 0.30, "Sub-0.30 absorptance must clamp to 0.30");
  assert.equal(clamped.wwr, 5, "Sub-5% WWR must clamp to 5%");
  assert.equal(clamped.orientation, 0, "Negative orientation must clamp to 0°");
  assert.equal(clamped.shading_depth, 0.0, "Negative shading depth must clamp to 0.0 m");
  assert.equal(clamped.ventilation_ach, 1.0, "Sub-1.0 ACH ventilation must clamp to 1.0 ACH");
});

test("Out-of-range query parameters are strictly clamped to upper bounds", () => {
  const extremeHighParams = {
    roof_ins: "999",
    wall_ins: "500",
    mass: "steel_reinforced_titanium",
    absorp: "1.85",
    wwr: "95",
    orient: "720",
    shading: "10.0",
    vent: "100.0"
  };

  const clamped = clampDesignVariables(extremeHighParams);

  assert.equal(clamped.roof_insulation_thickness, 150, "Excessive roof insulation must clamp to 150 mm");
  assert.equal(clamped.wall_insulation_thickness, 150, "Excessive wall insulation must clamp to 150 mm");
  assert.equal(clamped.wall_mass_class, "medium", "Invalid mass class must fallback to medium");
  assert.equal(clamped.roof_solar_absorptance, 0.90, "Excessive absorptance must clamp to 0.90");
  assert.equal(clamped.wwr, 40, "Excessive WWR must clamp to 40%");
  assert.equal(clamped.orientation, 360, "Excessive orientation must clamp to 360°");
  assert.equal(clamped.shading_depth, 1.0, "Excessive shading depth must clamp to 1.0 m");
  assert.equal(clamped.ventilation_ach, 15.0, "Excessive ventilation must clamp to 15.0 ACH");
});

test("Valid query parameters and fractional WWR are parsed accurately", () => {
  const validParams = {
    roof_ins: "100",
    wall_ins: "80",
    mass: "heavy",
    absorp: "0.55",
    wwr: "0.25", // fractional WWR (25%)
    orient: "180",
    shading: "0.75",
    vent: "8.5"
  };

  const clamped = clampDesignVariables(validParams);

  assert.equal(clamped.roof_insulation_thickness, 100);
  assert.equal(clamped.wall_insulation_thickness, 80);
  assert.equal(clamped.wall_mass_class, "heavy");
  assert.equal(clamped.roof_solar_absorptance, 0.55);
  assert.equal(clamped.wwr, 25);
  assert.equal(clamped.orientation, 180);
  assert.equal(clamped.shading_depth, 0.75);
  assert.equal(clamped.ventilation_ach, 8.5);
});

test("Empty parameters fallback safely to DEFAULT_DESIGN", () => {
  const clamped = clampDesignVariables({});
  assert.deepEqual(clamped, DEFAULT_DESIGN);
});

test("checkSampledRangeValidity correctly flags in-bounds and out-of-bounds states", () => {
  const validDesign = { ...DEFAULT_DESIGN };
  const validCheck = checkSampledRangeValidity(validDesign);
  assert.equal(validCheck.isWithinBounds, true);
  assert.equal(validCheck.outOfBoundsFields.length, 0);

  const invalidDesign = {
    ...DEFAULT_DESIGN,
    roof_insulation_thickness: 200,
    roof_solar_absorptance: 0.15
  };
  const invalidCheck = checkSampledRangeValidity(invalidDesign);
  assert.equal(invalidCheck.isWithinBounds, false);
  assert.ok(invalidCheck.outOfBoundsFields.includes("Roof insulation"));
  assert.ok(invalidCheck.outOfBoundsFields.includes("Roof solar absorptance"));
});

test("findNearestVerifiedParetoDesign returns verified design across all 5 cities", () => {
  const cities: CityKey[] = ["Jodhpur", "Mumbai", "New_Delhi", "Bengaluru", "Shimla"];

  for (const city of cities) {
    const { nearestDesign, distance } = findNearestVerifiedParetoDesign(city, DEFAULT_DESIGN);
    assert.ok(nearestDesign, `Nearest design not found for ${city}`);
    assert.equal(nearestDesign.is_verified, true, `Design ${nearestDesign.pareto_id} for ${city} should be verified`);
    assert.ok(distance >= 0, "Distance metric must be non-negative");
  }
});
