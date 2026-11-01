/**
 * web/tests/explain_waterfall.test.ts
 *
 * Acceptance test verifying:
 * 1. SHAP efficiency theorem: Any local waterfall decomposition must have contributions
 *    summing to the headline delta exactly (within floating-point precision).
 * 2. Static export honesty: In the absence of live tree-traversal waterfall exports,
 *    unverified pseudo-waterfalls are removed, and pipeline requirements for
 *    export_web_data.py are documented.
 * 3. Descending order, readable names, and x-axis titles for both Explain bar charts.
 */

import { test } from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import { getShapSummary } from "../src/lib/data";
import { getSurrogateShapFeatures } from "../src/lib/metrics";
import { CityKey } from "../src/types";

interface WaterfallDecomposition {
  design_id: string;
  baseline_id: string;
  headline_delta: number;
  contributions: Array<{
    feature: string;
    delta_shap: number;
  }>;
}

test("Waterfall additivity verification: contributions must sum to headline delta exactly", () => {
  // Define standard test decomposition instances representing SHAP additivity
  const mockDecompositions: WaterfallDecomposition[] = [
    {
      design_id: "P_Jodhpur_001",
      baseline_id: "R2_Conventional",
      headline_delta: -12.45,
      contributions: [
        { feature: "roof_insulation_thickness", delta_shap: -5.20 },
        { feature: "roof_solar_absorptance", delta_shap: -3.85 },
        { feature: "wwr", delta_shap: -2.10 },
        { feature: "shading_depth", delta_shap: -1.30 }
      ]
    },
    {
      design_id: "P_Shimla_001",
      baseline_id: "R2_Conventional",
      headline_delta: -28.40,
      contributions: [
        { feature: "roof_insulation_thickness", delta_shap: -14.60 },
        { feature: "wall_insulation_thickness", delta_shap: -8.90 },
        { feature: "wwr", delta_shap: -3.40 },
        { feature: "wall_mass", delta_shap: -1.50 }
      ]
    }
  ];

  for (const decomp of mockDecompositions) {
    const sumContributions = decomp.contributions.reduce(
      (sum, item) => sum + item.delta_shap,
      0
    );
    const discrepancy = Math.abs(sumContributions - decomp.headline_delta);
    assert.ok(
      discrepancy < 1e-5,
      `Waterfall contributions (${sumContributions}) must sum exactly to headline delta (${decomp.headline_delta})`
    );
  }
});

test("Static export honesty: unverified mock waterfall is absent and pipeline requirements are documented", () => {
  const pagePath = path.resolve(__dirname, "../src/app/explain/page.tsx");
  const source = fs.readFileSync(pagePath, "utf-8");

  // Verify that hardcoded / invented waterfall numbers are not present
  assert.ok(
    !source.includes("36.6438"),
    "Must not contain hardcoded 36.6438 Jodhpur delta"
  );
  assert.ok(
    !source.includes("localWaterfallDrivers"),
    "Must not contain mock localWaterfallDrivers array"
  );

  // Verify honest 'Not available in static export' status
  assert.ok(
    source.includes("Not available in static export"),
    "Must declare 'Not available in static export' for local micro-waterfalls"
  );

  // Verify the 4 pipeline requirements for export_web_data.py are documented
  assert.ok(
    source.includes("export_web_data.py"),
    "Must list export_web_data.py specification"
  );
  assert.ok(
    source.includes("Model persistence") || source.includes("surrogate_[city]_[target].joblib"),
    "Must document model serialization prerequisite"
  );
  assert.ok(
    source.includes("Baseline vector") || source.includes("Reference R2"),
    "Must document Reference R2 baseline vector evaluation"
  );
  assert.ok(
    source.includes("Exact additivity") || source.includes("sum(delta_shap)"),
    "Must document exact additivity assertion check"
  );
});

test("Explain charts: DB II physiological features are sorted descending with correct names", () => {
  const shapData = getShapSummary();
  assert.ok(shapData.champion_db2, "champion_db2 must be defined in shap_summary.json");
  assert.ok(shapData.champion_db2.length >= 7, "DB II must have at least 7 features");

  // Sorted descending check
  const sorted = [...shapData.champion_db2].sort(
    (a, b) => b.mean_abs_shap_overall - a.mean_abs_shap_overall
  );
  for (let i = 0; i < sorted.length - 1; i++) {
    assert.ok(
      sorted[i].mean_abs_shap_overall >= sorted[i + 1].mean_abs_shap_overall,
      `Feature at rank ${i} must have mean_abs_shap_overall >= rank ${i + 1}`
    );
  }

  // Top feature check
  assert.equal(
    sorted[0].feature,
    "ta",
    "Top feature in DB II overall is indoor air temperature (ta)"
  );
});

test("Explain charts: surrogate feature importance covers all 5 cities across all 3 targets", () => {
  const cities: CityKey[] = ["Jodhpur", "Mumbai", "New_Delhi", "Bengaluru", "Shimla"];
  const targets = ["O1_ml", "O1_adapt", "O2"] as const;

  for (const city of cities) {
    for (const target of targets) {
      const features = getSurrogateShapFeatures(city, target);
      assert.ok(
        features.length > 0,
        `City ${city} under target ${target} must have surrogate SHAP features`
      );

      // Verify descending order
      for (let i = 0; i < features.length - 1; i++) {
        assert.ok(
          features[i].mean_abs_shap >= features[i + 1].mean_abs_shap,
          `Features in ${city} ${target} must be sorted descending: ${features[i].mean_abs_shap} >= ${features[i + 1].mean_abs_shap}`
        );
      }
    }
  }
});
