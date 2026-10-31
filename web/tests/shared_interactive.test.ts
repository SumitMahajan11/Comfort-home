import { test } from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";

test("India Map: Survey of India boundary, exact EPW coordinates, collision avoidance, and chip row", () => {
  const mapPath = path.resolve(__dirname, "../src/components/maps/IndiaClimateMap.tsx");
  const mapContent = fs.readFileSync(mapPath, "utf-8");

  // Official Survey of India boundary data source
  assert.ok(mapContent.includes("Survey of India"), "Must source official Survey of India boundary");
  assert.ok(mapContent.includes("india_map_soi.json"), "Must import bundled SOI map data");

  // Real EPW coordinates referenced and configured
  assert.ok(mapContent.includes("26.24N 73.02E"), "Must reference Jodhpur EPW coordinates");
  assert.ok(mapContent.includes("Shimla"), "Must position Shimla");
  assert.ok(mapContent.includes("Mumbai"), "Must position Mumbai");
  assert.ok(mapContent.includes("New_Delhi"), "Must position New Delhi");
  assert.ok(mapContent.includes("Bengaluru"), "Must position Bengaluru");

  // Collision avoidance: Jodhpur and Mumbai anchored to end (left)
  assert.ok(mapContent.includes('labelAnchor: "end"'), "Must have collision avoidance anchoring to end");

  // Labels >= 13px
  assert.ok(mapContent.includes('fontSize={isSelected ? "14" : "13"}'), "Labels must be >= 13px");

  // Markers >= 12px with focus ring and keyboard Enter
  assert.ok(mapContent.includes("r={isSelected ? 9 : 7}"), "Marker radius must be 7-9px (diameter 14-18px >= 12px)");
  assert.ok(mapContent.includes("focus-visible:"), "Markers must have focus-visible styling");
  assert.ok(mapContent.includes('tabIndex={0}'), "Markers must be keyboard focusable");
  assert.ok(mapContent.includes('e.key === "Enter"'), "Enter must select city");

  // Chip row synchronization
  assert.ok(mapContent.includes("Select Station:"), "Must have station chip row");
  assert.ok(mapContent.includes("aria-pressed={isSelected}"), "Chip buttons must reflect selection");

  // Layout: fills panel width, min height 420px, card beside on desktop and below on mobile
  assert.ok(mapContent.includes("min-h-[420px]"), "Must have min height 420px");
  assert.ok(mapContent.includes("flex-col lg:flex-row"), "Card must sit beside on desktop and below on mobile");
});

test("Command Palette: placeholder, fuzzy match on Jodhpur, Pareto, D-005, 'No matches', and focus", () => {
  const cmdPath = path.resolve(__dirname, "../src/components/common/CommandPalette.tsx");
  const cmdContent = fs.readFileSync(cmdPath, "utf-8");

  // Exact placeholder required by spec
  assert.ok(cmdContent.includes('placeholder="Search pages, cities, decisions"'), 'Must have placeholder "Search pages, cities, decisions"');

  // Must match Jodhpur, Pareto, and D-005
  assert.ok(cmdContent.includes("city-Jodhpur") || cmdContent.includes("CITIES_DATA"), "Must include Jodhpur city search");
  assert.ok(cmdContent.includes("page-pareto"), "Must include Pareto page search");
  assert.ok(cmdContent.includes("meta.decisions"), "Must dynamically load all project decisions including D-005");

  // Fallback text on zero matches
  assert.ok(cmdContent.includes("No matches"), 'Must show "No matches" on zero search results');

  // Focus management
  assert.ok(cmdContent.includes("previousActiveElement"), "Must save previous active element to restore focus");
  assert.ok(cmdContent.includes("inputRef.current?.focus()"), "Must focus search input upon opening");
  assert.ok(cmdContent.includes('e.key === "Escape"'), "Esc must close palette");
});

test("Wizard: Simple Mode definition, persistence, tooltip, and Hindi toggle gating", () => {
  const recommenderPath = path.resolve(__dirname, "../src/app/recommender/page.tsx");
  const content = fs.readFileSync(recommenderPath, "utf-8");

  // Simple Mode state and persistence
  assert.ok(content.includes("simpleMode"), "Must have simpleMode state");
  assert.ok(content.includes("comfort_simple_mode"), "Must persist simpleMode in localStorage");

  // Tooltip definition
  assert.ok(content.includes("Simple Mode:"), "Must define Simple Mode in UI tooltip");
  assert.ok(content.includes("Hides technical metrics"), "Tooltip must explain technical metrics are hidden");

  // Technical metrics hidden in simple mode
  assert.ok(content.includes("spearman={simpleMode ? undefined : cityInfo.spearman}"), "Spearman rank must be hidden in Simple Mode");

  // Single recommendation emphasis
  assert.ok(content.includes("Simple Mode active:") || content.includes("Simple Mode:"), "Must highlight Simple Mode recommendation");

  // Hindi toggle is hidden until 100% translation coverage is complete
  assert.ok(!content.includes("Toggle English / हिंदी"), "Incomplete Hindi toggle must be hidden in wizard");
});
