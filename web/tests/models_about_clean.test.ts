import { test } from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";

test("Model Lab: clean tabs, no Phase N, no duplicate S1-S4 cards", () => {
  const modelsPath = path.resolve(__dirname, "../src/app/models/page.tsx");
  const content = fs.readFileSync(modelsPath, "utf-8");

  // Tab labels must be exact
  assert.ok(content.includes("Comfort models"), 'Must have tab label "Comfort models"');
  assert.ok(content.includes("Fast estimators (25)"), 'Must have tab label "Fast estimators (25)"');
  assert.ok(content.includes("Evidence log"), 'Must have tab label "Evidence log"');

  // No duplicated S1-S4 cards or research scorecard banner
  assert.ok(!content.includes("View S1–S4 research scorecard"), "Duplicate S1-S4 link card must be removed");
  assert.ok(!content.includes("Success Criteria S1-S4 Research Results Link"), "Duplicate S1-S4 section must be removed");

  // Evidence log must not contain "Phase N" labels (e.g. "Phase 0", "Phase 1")
  const phaseNRegex = /Phase\s+[0-9]/i;
  assert.ok(!phaseNRegex.test(content), 'Evidence log must not contain "Phase N" strings');
});

test("Model Lab: leaderboard plain statement, 4-decimal formatting, CI en-dash, non-wrapping status", () => {
  const modelsPath = path.resolve(__dirname, "../src/app/models/page.tsx");
  const content = fs.readFileSync(modelsPath, "utf-8");

  // Plain statement above table
  const plainStatement = "The best ML model scored 0.0154 lower than the adaptive baseline, so it is not claimed to be better.";
  assert.ok(content.includes(plainStatement), `Must contain exact statement: "${plainStatement}"`);

  // Sticky header below 64px global header
  assert.ok(content.includes("sticky top-16"), "Must contain sticky header at top-16 (below 64px header)");

  // CI formatted with en-dash and no square brackets
  assert.ok(content.includes("0.4907–0.4971"), 'CI must be formatted as "0.4907–0.4971"');
  assert.ok(!content.includes("[0.4907, 0.4971]"), "CI must not have brackets");

  // Status column whitespace-nowrap and min-width
  assert.ok(content.includes("whitespace-nowrap"), "Status must have whitespace-nowrap preventing wrapping");
  assert.ok(content.includes("min-w-[140px]") || content.includes("min-w-[130px]"), "Status column must have min width");

  // Numbers right aligned with 4 decimals
  assert.ok(content.includes("text-right tabular-nums"), "Numbers must be right aligned with tabular nums");
  assert.ok(content.includes(".toFixed(4)"), "Numbers must be formatted to 4 decimals");
});

test("Model Lab: surrogate matrix threshold marked and failing cells highlighted with icon+text", () => {
  const modelsPath = path.resolve(__dirname, "../src/app/models/page.tsx");
  const content = fs.readFileSync(modelsPath, "utf-8");

  // Threshold 0.95 marked
  assert.ok(content.includes("0.95"), "0.95 threshold must be marked");

  // Mumbai O1_ml (0.9406) and Shimla warm_ml (0.9225) failing cells highlighted with icon+text
  assert.ok(content.includes("AlertTriangle"), "Failing cells must have an alert icon");
  assert.ok(content.includes("Fail"), "Failing cells must have failure text");
  assert.ok(content.includes("Mumbai O1_ml (R² = 0.9406)"), "Mumbai failing target documented");
  assert.ok(content.includes("Shimla warm_ml (R² = 0.9225)"), "Shimla failing target documented");
});

test("About: Mandatory Limitations is the first content section", () => {
  const aboutPath = path.resolve(__dirname, "../src/app/about/page.tsx");
  const content = fs.readFileSync(aboutPath, "utf-8");

  // Limitations must appear before architecture, assumptions, decisions, licences, and reproduction
  const limitationsIdx = content.indexOf('id="limitations"');
  const architectureIdx = content.indexOf('id="architecture"');
  const assumptionsIdx = content.indexOf('id="assumptions"');
  const decisionsIdx = content.indexOf('id="decisions"');
  const licencesIdx = content.indexOf('id="licences"');
  const reproductionIdx = content.indexOf('id="reproduction"');

  assert.ok(limitationsIdx !== -1, "Must contain limitations section");
  assert.ok(architectureIdx !== -1, "Must contain architecture section");
  assert.ok(assumptionsIdx !== -1, "Must contain assumptions section");
  assert.ok(decisionsIdx !== -1, "Must contain decisions section");
  assert.ok(licencesIdx !== -1, "Must contain licences section");
  assert.ok(reproductionIdx !== -1, "Must contain reproduction section");

  assert.ok(limitationsIdx < architectureIdx, "Limitations must come before architecture");
  assert.ok(limitationsIdx < assumptionsIdx, "Limitations must come before assumptions");
  assert.ok(limitationsIdx < decisionsIdx, "Limitations must come before decisions");
  assert.ok(limitationsIdx < licencesIdx, "Limitations must come before licences");
  assert.ok(limitationsIdx < reproductionIdx, "Limitations must come before reproduction");
});

test("About: Scenario Assumptions has A-001 · Title format with description below", () => {
  const aboutPath = path.resolve(__dirname, "../src/app/about/page.tsx");
  const content = fs.readFileSync(aboutPath, "utf-8");

  // Must have title format with dot separator
  assert.ok(content.includes("{a.id}"), "Must render assumption id");
  assert.ok(content.includes("·"), "Must render centered dot separator in assumption title");
  assert.ok(content.includes("{a.name}"), "Must render assumption name");
  assert.ok(content.includes("{a.value}"), "Must render assumption description below");
});

test("About: Decision search filter works and reproduction commands have no && and OS venv paths", () => {
  const aboutPath = path.resolve(__dirname, "../src/app/about/page.tsx");
  const content = fs.readFileSync(aboutPath, "utf-8");

  // Decision filter
  assert.ok(content.includes("decisionFilter"), "Must have decision filter state");
  assert.ok(content.includes("filteredDecisions"), "Must compute filtered decisions");

  // Two shell tabs: PowerShell and Bash
  assert.ok(content.includes("PowerShell (Windows)"), "Must have PowerShell tab");
  assert.ok(content.includes("Bash (macOS / Linux)"), "Must have Bash tab");

  // Copy button
  assert.ok(content.includes("handleCopy"), "Must have copy handler");
  assert.ok(content.includes("navigator.clipboard.writeText"), "Must write to clipboard");

  // Zero && in reproduction commands list
  const reproductionSection = content.substring(content.indexOf('id="reproduction"'));
  assert.ok(!reproductionSection.includes("&&"), 'Reproduction commands must not contain "&&"');

  // OS-specific venv paths
  assert.ok(content.includes("Scripts\\\\python.exe") || content.includes("Scripts\\python.exe"), "PowerShell commands must use Scripts\\python.exe");
  assert.ok(content.includes("./.venv/bin/python"), "Bash commands must use ./.venv/bin/python");
});

test("About: Two-column desktop layout with sticky TOC and single-column mobile", () => {
  const aboutPath = path.resolve(__dirname, "../src/app/about/page.tsx");
  const content = fs.readFileSync(aboutPath, "utf-8");

  // Desktop TOC
  assert.ok(content.includes("hidden lg:block"), "TOC must be hidden on mobile and visible on desktop");
  assert.ok(content.includes("sticky top-20"), "TOC must be sticky on desktop");
  assert.ok(content.includes("lg:flex lg:gap-8"), "Main container must use flex on desktop");
});
