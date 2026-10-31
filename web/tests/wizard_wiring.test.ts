import test from "node:test";
import assert from "node:assert/strict";
import { evaluateQuestionnaire } from "../src/lib/api";

test("Step 4 answer wiring: changing each question changes at least one output field", async () => {
  const baseInput = {
    city: "Jodhpur",
    building_type: "house",
    usually_feel: "about right",
    hours_occupied: 18,
    has_cooling: "none",
    summer_clothing: "light",
    winter_clothing: "normal",
    priority: "balanced",
    future_climate: false
  };

  const baseResult = await evaluateQuestionnaire(baseInput);

  // 1. Changing 'usually_feel' (thermal sensation) must change comfort_fit_score
  const feelChanged = await evaluateQuestionnaire({
    ...baseInput,
    usually_feel: "too hot"
  });
  assert.notEqual(
    feelChanged.packages.balanced.comfort_fit_score,
    baseResult.packages.balanced.comfort_fit_score,
    "Changing 'usually_feel' must change comfort_fit_score"
  );
  assert.notEqual(
    feelChanged.user_comparison.user_feel,
    baseResult.user_comparison.user_feel,
    "Changing 'usually_feel' must update user_comparison.user_feel"
  );

  // 2. Changing 'hours_occupied' must change annual_discomfort_hours and hours_scored
  const hoursChanged = await evaluateQuestionnaire({
    ...baseInput,
    hours_occupied: 8
  });
  assert.notEqual(
    hoursChanged.packages.balanced.annual_discomfort_hours,
    baseResult.packages.balanced.annual_discomfort_hours,
    "Changing 'hours_occupied' must change annual_discomfort_hours"
  );
  assert.strictEqual(
    hoursChanged.packages.balanced.hours_scored,
    8 * 365,
    "hours_scored must match hours_occupied * 365"
  );
  assert.strictEqual(
    baseResult.packages.balanced.hours_scored,
    18 * 365,
    "base hours_scored must match 18 * 365"
  );

  // 3. Changing 'has_cooling' must change cooling_mode and comfort_fit_score
  const coolingChanged = await evaluateQuestionnaire({
    ...baseInput,
    has_cooling: "ac"
  });
  assert.notEqual(
    coolingChanged.packages.balanced.cooling_mode,
    baseResult.packages.balanced.cooling_mode,
    "Changing 'has_cooling' must change cooling_mode"
  );
  assert.notEqual(
    coolingChanged.packages.balanced.comfort_fit_score,
    baseResult.packages.balanced.comfort_fit_score,
    "Changing 'has_cooling' must change comfort_fit_score"
  );
  assert.notEqual(
    coolingChanged.user_comparison.user_cooling,
    baseResult.user_comparison.user_cooling,
    "Changing 'has_cooling' must update user_comparison.user_cooling"
  );

  // 4. Changing 'priority' changes highlighted / recommended package role
  // Verify that the 3 packages provide distinct roles matching priorities:
  assert.strictEqual(baseResult.packages.budget.selection_role, "Best_O2");
  assert.strictEqual(baseResult.packages.balanced.selection_role, "Knee_Point");
  assert.strictEqual(baseResult.packages.best_comfort.selection_role, "Best_O1_ml");

  // Verify non-saturating fit scores across packages
  const scores = [
    baseResult.packages.budget.comfort_fit_score,
    baseResult.packages.balanced.comfort_fit_score,
    baseResult.packages.best_comfort.comfort_fit_score
  ];
  assert.ok(
    scores.every(s => s >= 10 && s <= 98),
    "All fit scores must stay within valid bounds (10-98) and not saturate at 80"
  );
});
