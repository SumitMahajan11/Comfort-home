/**
 * web/tests/pareto_format.test.ts
 *
 * Unit tests verifying:
 * 1. Design selection by design_id (pareto_id), strictly invariant to array index/order.
 * 2. Central formatter functions in web/lib/format.ts (units, compass azimuth, signed errors).
 * 3. 100 Pareto designs per city with exactly 10 verified designs per city (50 total).
 */

import { test } from "node:test";
import assert from "node:assert/strict";
import { CityKey } from "../src/types";
import { getParetoDesigns } from "../src/lib/data";
import {
  formatInsulationMm,
  formatGlazingPct,
  formatAzimuthWithCompass,
  formatOverhangM,
  formatVentilationAch,
  formatSolarAbsorptance,
  formatWallMassClass,
  formatO1Error,
  formatO2Error
} from "../src/lib/format";

const CITIES: CityKey[] = ["Jodhpur", "Mumbai", "New_Delhi", "Bengaluru", "Shimla"];

test("Pareto selection: matches design strictly by pareto_id, never by array index", () => {
  const jodhpurDesigns = getParetoDesigns("Jodhpur");
  assert.equal(jodhpurDesigns.length, 100, "Should have 100 designs for Jodhpur");

  // Pick a specific verified design ID
  const targetId = "P_Jodhpur_001";
  const targetDesign = jodhpurDesigns.find(d => d.pareto_id === targetId);
  assert.ok(targetDesign, "Target design P_Jodhpur_001 must exist");

  // Reorder / reverse the designs array (simulating different filters or sorts)
  const reversed = [...jodhpurDesigns].reverse();
  const sortedByEnergy = [...jodhpurDesigns].sort((a, b) => a.O2 - b.O2);

  // Assert lookup by pareto_id retrieves the identical design object regardless of index
  const matchOriginal = jodhpurDesigns.find(d => d.pareto_id === targetId);
  const matchReversed = reversed.find(d => d.pareto_id === targetId);
  const matchSorted = sortedByEnergy.find(d => d.pareto_id === targetId);

  assert.equal(matchOriginal?.pareto_id, targetId);
  assert.equal(matchReversed?.pareto_id, targetId);
  assert.equal(matchSorted?.pareto_id, targetId);

  // Verify properties match
  assert.equal(matchReversed?.O1_ml, targetDesign?.O1_ml);
  assert.equal(matchSorted?.O2, targetDesign?.O2);
  assert.equal(matchReversed?.roof_insulation_thickness, targetDesign?.roof_insulation_thickness);
});

test("Formatters: roof and wall insulation thickness in mm = round(metres * 1000)", () => {
  assert.equal(formatInsulationMm(0.143261), "143 mm");
  assert.equal(formatInsulationMm(0.088551), "89 mm");
  assert.equal(formatInsulationMm(0.0741), "74 mm");
  assert.equal(formatInsulationMm(0), "0 mm");
  assert.equal(formatInsulationMm(null), "Not available");
  assert.equal(formatInsulationMm(undefined), "Not available");
});

test("Formatters: glazing (WWR) as percentage with 0 decimals", () => {
  assert.equal(formatGlazingPct(0.1351), "14%");
  assert.equal(formatGlazingPct(0.20), "20%");
  assert.equal(formatGlazingPct(15), "15%");
  assert.equal(formatGlazingPct(0.115), "12%");
  assert.equal(formatGlazingPct(null), "Not available");
});

test("Formatters: azimuth orientation with 0 decimals and 16-point compass label", () => {
  assert.equal(formatAzimuthWithCompass(27), "27° · NNE");
  assert.equal(formatAzimuthWithCompass(0), "0° · N");
  assert.equal(formatAzimuthWithCompass(45), "45° · NE");
  assert.equal(formatAzimuthWithCompass(90), "90° · E");
  assert.equal(formatAzimuthWithCompass(135), "135° · SE");
  assert.equal(formatAzimuthWithCompass(180), "180° · S");
  assert.equal(formatAzimuthWithCompass(218.23), "218° · SW");
  assert.equal(formatAzimuthWithCompass(270), "270° · W");
  assert.equal(formatAzimuthWithCompass(315), "315° · NW");
  assert.equal(formatAzimuthWithCompass(360), "0° · N");
  assert.equal(formatAzimuthWithCompass(null), "Not available");
});

test("Formatters: overhang to 2 decimals and ventilation to 1.0 ACH", () => {
  assert.equal(formatOverhangM(0.75), "0.75 m");
  assert.equal(formatOverhangM(0.089), "0.09 m");
  assert.equal(formatOverhangM(null), "Not available");

  assert.equal(formatVentilationAch(1.0), "1.0 ACH");
  assert.equal(formatVentilationAch(1.6435), "1.6 ACH");
  assert.equal(formatVentilationAch(null), "Not available");

  assert.equal(formatSolarAbsorptance(0.6048), "0.60");
  assert.equal(formatWallMassClass("heavy"), "Heavy");
  assert.equal(formatWallMassClass("medium"), "Medium");
});

test("Formatters: O1 and O2 verification error computation (verified - predicted)", () => {
  // O1 error: signed percentage points (pp)
  const o1Error = formatO1Error(36.6438, 37.7343);
  assert.equal(o1Error, "−1.1 pp");

  const o1PositiveError = formatO1Error(40.5, 40.0);
  assert.equal(o1PositiveError, "+0.5 pp");

  assert.equal(formatO1Error(null, 37.0), "Not verified");
  assert.equal(formatO1Error(undefined, 37.0), "Not verified");

  // O2 error: signed kWh/m²/yr and relative percentage
  const o2Error = formatO2Error(41.403, 45.331);
  assert.equal(o2Error, "−3.9 kWh/m²/yr (−9%)");

  const o2PositiveError = formatO2Error(35.0, 30.0);
  assert.equal(o2PositiveError, "+5.0 kWh/m²/yr (+17%)");

  assert.equal(formatO2Error(null, 45.0), "Not verified");
  assert.equal(formatO2Error(undefined, 45.0), "Not verified");
});

test("Pareto verification dataset: exactly 100 designs and 10 verified per city across all 5 cities", () => {
  let totalVerified = 0;

  for (const city of CITIES) {
    const designs = getParetoDesigns(city);
    assert.equal(designs.length, 100, `${city} should have 100 Pareto designs`);

    const verified = designs.filter(d => d.is_verified);
    assert.equal(verified.length, 10, `${city} should have exactly 10 verified designs`);

    // Verify all 10 verified designs have non-null simulation actuals
    for (const v of verified) {
      assert.ok(v.verified_O1_ml != null, `${v.pareto_id} missing verified_O1_ml`);
      assert.ok(v.verified_O2 != null, `${v.pareto_id} missing verified_O2`);
      assert.ok(v.verified_O1_adapt != null, `${v.pareto_id} missing verified_O1_adapt`);
    }

    totalVerified += verified.length;
  }

  assert.equal(totalVerified, 50, "Total verified designs across all 5 cities must equal 50");
});
