/**
 * web/tests/consistency.test.ts
 *
 * Automated regression test asserting UI metric traceability and cross-screen consistency.
 * Required by UI Consistency Protocol:
 * - A design ID must show the same O1 (ML discomfort) and O2 (HVAC energy) on every screen for all 5 cities.
 * - Baselines R1 and R2 must never be mixed.
 * - Applicability metrics must match empirical applicability values, not hardcoded strings.
 */

import { test } from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import { CityKey } from "../src/types";
import { getParetoDesigns } from "../src/lib/data";
import { evaluateQuestionnaire } from "../src/lib/api";
import { getCityBaselines, getCityApplicability, getDesignMetrics } from "../src/lib/metrics";
import { CITIES_DATA, PIPELINE_CONSTANTS } from "../src/lib/constants";

const CITIES: CityKey[] = ["Jodhpur", "Mumbai", "New_Delhi", "Bengaluru", "Shimla"];

test("Cross-screen objective consistency: identical O1 and O2 for package designs across all 5 cities", async () => {
  for (const city of CITIES) {
    const paretoDesigns = getParetoDesigns(city);
    const paretoMap = new Map(paretoDesigns.map(d => [d.pareto_id, d]));

    const response = await evaluateQuestionnaire({
      city,
      building_type: "house",
      usually_feel: "about right",
      hours_occupied: 18,
      has_cooling: "ac",
      clothing_type: "light",
      priority: "balanced",
      future_climate: false
    });

    const pkgs = [
      response.packages.budget,
      response.packages.balanced,
      response.packages.best_comfort
    ];

    for (const pkg of pkgs) {
      const paretoRow = paretoMap.get(pkg.pareto_id);
      assert.ok(paretoRow, `Design ${pkg.pareto_id} must exist in Pareto front for ${city}`);

      const expectedO1 = Math.round(Number(paretoRow.O1_ml) * 10) / 10;
      const expectedO2 = Math.round(Number(paretoRow.O2) * 10) / 10;

      assert.strictEqual(
        pkg.discomfort_pct,
        expectedO1,
        `Design ${pkg.pareto_id} in ${city} must have O1 discomfort matching Pareto Explorer exactly (${pkg.discomfort_pct}% vs ${expectedO1}%)`
      );

      assert.strictEqual(
        pkg.annual_energy_kwh_per_m2,
        expectedO2,
        `Design ${pkg.pareto_id} in ${city} must have O2 energy matching Pareto Explorer exactly (${pkg.annual_energy_kwh_per_m2} vs ${expectedO2} kWh/m²/yr)`
      );
    }
  }
});

test("Baselines R1 and R2 separation and integrity across all 5 cities", () => {
  for (const city of CITIES) {
    const baselines = getCityBaselines(city);

    assert.ok(baselines.r1, `R1 baseline must exist for ${city}`);
    assert.ok(baselines.r2, `R2 baseline must exist for ${city}`);

    assert.ok(baselines.r1.discomfort_ml_pct > 0, `R1 discomfort must be positive for ${city}`);
    assert.ok(baselines.r2.discomfort_ml_pct > 0, `R2 discomfort must be positive for ${city}`);
    assert.ok(baselines.r1.energy_kwh_per_m2_yr > 0, `R1 energy must be positive for ${city}`);
    assert.ok(baselines.r2.energy_kwh_per_m2_yr > 0, `R2 energy must be positive for ${city}`);

    // Verify Jodhpur values match specification
    if (city === "Jodhpur") {
      assert.strictEqual(Math.round(baselines.r1.discomfort_ml_pct * 10) / 10, 75.7);
      assert.strictEqual(Math.round(baselines.r2.discomfort_ml_pct * 10) / 10, 76.4);
      assert.strictEqual(Math.round(baselines.r1.energy_kwh_per_m2_yr * 10) / 10, 295.1);
      assert.strictEqual(Math.round(baselines.r2.energy_kwh_per_m2_yr * 10) / 10, 281.9);
    }
  }
});

test("City applicability metrics are empirical and not hard-coded", () => {
  const jodhpurApp = getCityApplicability("Jodhpur");
  assert.strictEqual(
    Math.round(jodhpurApp.adaptive_validity_pct * 100) / 100,
    86.85,
    "Jodhpur adaptive validity must be 86.85% (from applicability.json), not 100.0%"
  );
  assert.strictEqual(
    Math.round(jodhpurApp.envelope_validity_pct * 100) / 100,
    53.91,
    "Jodhpur envelope validity must be 53.91% (from applicability.json), not 68.4%"
  );

  const shimlaApp = getCityApplicability("Shimla");
  assert.strictEqual(
    Math.round(shimlaApp.adaptive_validity_pct * 100) / 100,
    73.97,
    "Shimla adaptive validity must be 73.97%"
  );
});

test("DesignMetrics computes explicit non-mixed deltas vs R1 and R2", () => {
  const jodhpurDesigns = getParetoDesigns("Jodhpur");
  const p001 = jodhpurDesigns.find(d => d.pareto_id === "P_Jodhpur_001");
  assert.ok(p001, "P_Jodhpur_001 must exist");

  const metrics = getDesignMetrics(p001, "Jodhpur");
  assert.strictEqual(metrics.design_id, "P_Jodhpur_001");

  // Verify verified physical values
  assert.ok(metrics.is_verified, "P_Jodhpur_001 must be verified");
  assert.strictEqual(Math.round((metrics.o1_ml_verified_pct || 0) * 100) / 100, 36.64);
  assert.strictEqual(Math.round((metrics.o2_verified_kwh || 0) * 100) / 100, 41.40);

  // Verify explicit deltas vs R1 (75.72% / 295.06 kWh)
  const expectedDeltaR1Discomfort = 36.6438356 - 75.719178;
  assert.ok(
    Math.abs((metrics.delta_o1_ml_verified_vs_r1_pp || 0) - expectedDeltaR1Discomfort) < 0.01,
    "Delta vs R1 discomfort must be approximately -39.08 pp"
  );

  // Verify explicit deltas vs R2 (76.43% / 281.88 kWh)
  const expectedDeltaR2Energy = 41.403205 - 281.875828;
  assert.ok(
    Math.abs((metrics.delta_o2_verified_vs_r2_kwh || 0) - expectedDeltaR2Energy) < 0.01,
    "Delta vs R2 energy must be approximately -240.47 kWh/m²/yr"
  );
});

test("Overview low-confidence panel renders cities from CITIES_DATA with confidence === 'Low'", () => {
  const lowFromConstants = Object.values(CITIES_DATA)
    .filter((c) => c.confidence === "Low")
    .map((c) => c.name);

  // Assert expected cities
  assert.deepStrictEqual(
    [...lowFromConstants].sort(),
    ["Jodhpur", "New Delhi", "Shimla"].sort(),
    "Low confidence cities must be Jodhpur, New Delhi, and Shimla"
  );
  assert.ok(!lowFromConstants.includes("Bengaluru"), "Bengaluru must NOT be in low confidence list");

  // Read page.tsx and verify dynamic derivation from CITIES_DATA
  const pagePath = path.resolve(__dirname, "../src/app/page.tsx");
  const pageSrc = fs.readFileSync(pagePath, "utf-8");
  assert.ok(
    pageSrc.includes('c.confidence === "Low"'),
    "Overview page must dynamically filter CITIES_DATA for confidence === 'Low'"
  );
  assert.ok(
    pageSrc.includes("lowConfidenceText"),
    "Overview page must render computed lowConfidenceText"
  );
});

test("PDF specification states EnergyPlus 26.2.0 from PIPELINE_CONSTANTS", () => {
  assert.strictEqual(
    PIPELINE_CONSTANTS.ENERGYPLUS_VERSION,
    "26.2.0",
    "Single source of truth EnergyPlus version must be 26.2.0"
  );
  assert.strictEqual(
    PIPELINE_CONSTANTS.SEED,
    42,
    "Single source of truth seed must be 42"
  );

  // Verify recommender page references PIPELINE_CONSTANTS.ENERGYPLUS_VERSION and does not have hardcoded 23.2.0
  const recommenderPath = path.resolve(__dirname, "../src/app/recommender/page.tsx");
  const recommenderSrc = fs.readFileSync(recommenderPath, "utf-8");
  assert.ok(
    !recommenderSrc.includes("23.2.0"),
    "Recommender page must not contain stale EnergyPlus 23.2.0"
  );
  assert.ok(
    recommenderSrc.includes("PIPELINE_CONSTANTS.ENERGYPLUS_VERSION"),
    "Recommender page PDF specification must reference PIPELINE_CONSTANTS.ENERGYPLUS_VERSION"
  );
});

test("Step 4 cooling 'none' case renders '0 kWh/m²/yr (free-running: no HVAC)' on Step 5", () => {
  const recommenderPath = path.resolve(__dirname, "../src/app/recommender/page.tsx");
  const recommenderSrc = fs.readFileSync(recommenderPath, "utf-8");
  assert.ok(
    recommenderSrc.includes('0 kWh/m²/yr (free-running: no HVAC)'),
    "Recommender page must explicitly render '0 kWh/m²/yr (free-running: no HVAC)' when cooling is none"
  );
  assert.ok(
    recommenderSrc.includes('data-testid="energy-line"'),
    "Recommender page must provide data-testid='energy-line' for testability"
  );
});

test("Jodhpur 'Balanced' package design ID is P_Jodhpur_052 across wizard, PDF specification, and Pareto knee point", async () => {
  const paretoDesigns = getParetoDesigns("Jodhpur");
  const kneePoint = paretoDesigns.find((d) => d.selection_role === "Knee_Point");
  assert.ok(kneePoint, "Jodhpur Pareto set must have a Knee_Point design");
  assert.strictEqual(
    kneePoint.pareto_id,
    "P_Jodhpur_052",
    "Jodhpur knee point Pareto ID must be P_Jodhpur_052"
  );

  const evaluation = await evaluateQuestionnaire({
    city: "Jodhpur",
    building_type: "house",
    usually_feel: "about right",
    hours_occupied: 24,
    has_cooling: "ac",
    clothing_type: "light",
    priority: "balanced",
    future_climate: false,
  });

  assert.strictEqual(
    evaluation.packages.balanced.pareto_id,
    "P_Jodhpur_052",
    "Wizard balanced package pareto_id must equal P_Jodhpur_052"
  );
  assert.strictEqual(
    evaluation.packages.balanced.selection_role,
    "Knee_Point",
    "Wizard balanced package must be assigned the Knee_Point role"
  );

  // Recommender deep link href must resolve to /pareto?city=Jodhpur&design=P_Jodhpur_052
  const recommenderPath = path.resolve(__dirname, "../src/app/recommender/page.tsx");
  const recommenderSrc = fs.readFileSync(recommenderPath, "utf-8");
  assert.ok(
    recommenderSrc.includes("href={`/pareto?city=${selectedCity}&design=${activePackage.pareto_id}`}"),
    "Recommender page must contain deep link using activePackage.pareto_id"
  );
});



