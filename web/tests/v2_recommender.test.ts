import test from "node:test";
import assert from "node:assert/strict";
import {
  haversineDistanceKm,
  estimateEnvelopeCost,
  computeComfortFitScore,
  matchLocation,
  evaluateQuestionnaire
} from "../src/lib/api";
import { TRANSLATIONS } from "../src/lib/i18n";
import { CITIES_DATA } from "../src/lib/constants";

test("haversineDistanceKm calculates accurate geographic distances between Indian cities", () => {
  // Mumbai (19.0760, 72.8777) to Pune (18.5204, 73.8567) is ~120-150 km
  const dist = haversineDistanceKm(19.0760, 72.8777, 18.5204, 73.8567);
  assert.ok(dist > 100 && dist < 160, `Distance unexpected: ${dist} km`);

  // Direct station distance should be 0.0 km
  const zeroDist = haversineDistanceKm(26.2389, 73.0243, 26.2389, 73.0243);
  assert.equal(zeroDist, 0.0);
});

test("CPWD DSR Cost Engine produces accurate itemized cost ranges with +/- 15% variance", () => {
  const design = {
    roof_insulation_thickness: 0.075, // 75 mm
    wall_insulation_thickness: 0.050, // 50 mm
    roof_solar_absorptance: 0.40,     // cool roof
    shading_depth: 0.50,              // overhangs
    wwr: 0.15                         // 15%
  };

  const cost = estimateEnvelopeCost(design);
  assert.ok(cost.total_envelope_cost_inr.central > 50000, "Central cost too low");
  assert.equal(cost.total_envelope_cost_inr.min, Math.round(cost.total_envelope_cost_inr.central * 0.85));
  assert.equal(cost.total_envelope_cost_inr.max, Math.round(cost.total_envelope_cost_inr.central * 1.15));
  assert.ok(cost.cost_per_m2_carpet.central > 1000, "Carpet rate too low");
  assert.equal(cost.schedule_source, "CPWD Delhi Schedule of Rates (DSR 2021)");
  assert.ok(cost.breakdown.roof_insulation_inr > 0);
  assert.ok(cost.breakdown.wall_insulation_inr > 0);
  assert.ok(cost.breakdown.cool_roof_coating_inr > 0);
});

test("computeComfortFitScore calculates deterministic score bounded between 10 and 98", () => {
  const score1 = computeComfortFitScore(20.0, 50.0, "about right", "Hot-Dry");
  assert.ok(score1 >= 10 && score1 <= 98, `Score out of bounds: ${score1}`);

  const scoreHighDiscomfort = computeComfortFitScore(85.0, 200.0, "too hot", "Hot-Dry");
  assert.ok(scoreHighDiscomfort < score1, "Higher discomfort should yield lower fit score");
});

test("matchLocation accurately falls back and attaches nearest station notice for external cities", async () => {
  const resPune = await matchLocation("Pune, Maharashtra");
  assert.equal(resPune.matched_city_key, "Mumbai");
  assert.ok(!resPune.is_direct_station, "Pune should not be direct station");
  assert.ok(resPune.nearest_match_notice?.includes("Mumbai"));
  assert.ok(resPune.distance_km > 50);

  const resJodhpur = await matchLocation("Jodhpur");
  assert.equal(resJodhpur.matched_city_key, "Jodhpur");
  assert.ok(resJodhpur.is_direct_station);
});

test("evaluateQuestionnaire generates 3 complete packages with 12-month performance and future-climate shift", async () => {
  const normalRes = await evaluateQuestionnaire({
    city: "Jodhpur",
    building_type: "house",
    usually_feel: "too hot",
    hours_occupied: 18,
    has_cooling: "fan",
    summer_clothing: "light",
    winter_clothing: "normal",
    priority: "balanced",
    future_climate: false
  });

  assert.ok(normalRes.packages.budget);
  assert.ok(normalRes.packages.balanced);
  assert.ok(normalRes.packages.best_comfort);
  assert.equal(normalRes.packages.budget.monthly_performance.months.length, 12);

  // Future climate (+1.5C) evaluation
  const futureRes = await evaluateQuestionnaire({
    city: "Jodhpur",
    building_type: "house",
    usually_feel: "too hot",
    hours_occupied: 18,
    has_cooling: "fan",
    summer_clothing: "light",
    winter_clothing: "normal",
    priority: "balanced",
    future_climate: true
  });

  assert.ok(futureRes.future_climate_applied);
  // Outdoor temperatures in futureRes should be +1.5C higher
  const diff = futureRes.packages.balanced.monthly_performance.outdoor_ta[0] -
               normalRes.packages.balanced.monthly_performance.outdoor_ta[0];
  assert.equal(Math.round(diff * 10) / 10, 1.5);
});

test("Bilingual dictionary covers all required v2 keys in both English and Hindi", () => {
  const en = TRANSLATIONS.en;
  const hi = TRANSLATIONS.hi;

  const requiredKeys = [
    "appName", "disclaimerSimulation", "disclaimerCost", "simpleMode",
    "expertMode", "futureClimateToggle", "step1Title", "step2Title",
    "step3Title", "step4Title", "step5Title", "comfortFitScore",
    "envelopeMaterials", "costBreakdown", "monthlyPerformanceChart"
  ] as const;

  for (const k of requiredKeys) {
    assert.ok(en[k], `Missing English key ${k}`);
    assert.ok(hi[k], `Missing Hindi key ${k}`);
  }
});
