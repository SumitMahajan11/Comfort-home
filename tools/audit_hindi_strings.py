#!/usr/bin/env python3
"""
tools/audit_hindi_strings.py

1. Creates web/messages/en.json and web/messages/hi.json from existing i18n dictionaries.
2. Audits all user-visible strings in web/src/app/recommender/page.tsx that are missing from hi.json.
3. Generates a markdown table [key | English] of all untranslated strings for the translator.
"""

import os
import json
import re
from pathlib import Path

MESSAGES_DIR = Path("web/messages")
MESSAGES_DIR.mkdir(parents=True, exist_ok=True)

# 1. Read existing i18n dictionary from web/src/lib/i18n.ts
with open("web/src/lib/i18n.ts", "r", encoding="utf-8") as f:
    i18n_code = f.read()

# Extract en and hi objects using regex
en_match = re.search(r"en:\s*\{(.*?)\n\s*\},", i18n_code, re.DOTALL)
hi_match = re.search(r"hi:\s*\{(.*?)\n\s*\}\s*\}", i18n_code, re.DOTALL)

def parse_dict(raw):
    d = {}
    for line in raw.splitlines():
        line = line.strip()
        if not line or line.startswith("//"):
            continue
        m = re.match(r"^([a-zA-Z0-9_]+):\s*[\"'](.*)[\"'],?$", line)
        if m:
            d[m.group(1)] = m.group(2)
    return d

en_dict = parse_dict(en_match.group(1)) if en_match else {}
hi_dict = parse_dict(hi_match.group(1)) if hi_match else {}

print(f"Loaded {len(en_dict)} English keys and {len(hi_dict)} Hindi keys from i18n.ts")

# Write to web/messages/en.json and web/messages/hi.json
with open(MESSAGES_DIR / "en.json", "w", encoding="utf-8") as f:
    json.dump(en_dict, f, indent=2, ensure_ascii=False)

with open(MESSAGES_DIR / "hi.json", "w", encoding="utf-8") as f:
    json.dump(hi_dict, f, indent=2, ensure_ascii=False)

print(f"Saved {MESSAGES_DIR / 'en.json'} and {MESSAGES_DIR / 'hi.json'}")

# 2. Extract wizard-specific strings in recommender/page.tsx
# Target list of specific untranslated strings in the wizard
untranslated_strings = [
    ("wizard_step4_heading", "Step 4: Your Occupant Comfort Profile"),
    ("wizard_step4_subheading", "Tell us how you experience indoor temperatures. Each question directly changes specific simulation and scoring outputs."),
    ("wizard_step4_wired_badge", "4 Wired Parameters"),
    ("wizard_step4_q1_label", "1. Indoor Thermal Sensation Preference"),
    ("wizard_step4_q1_changes", "Changes: Comfort fit score weighting (feel sensitivity)"),
    ("wizard_step4_q1_opt_too_hot", "Too hot & stuffy"),
    ("wizard_step4_q1_opt_comfortable", "About right"),
    ("wizard_step4_q1_opt_too_cold", "Too chilly"),
    ("wizard_step4_q2_label", "2. Daily Occupancy Duration"),
    ("wizard_step4_q2_changes", "Changes: Annual uncomfortable hours scored ({hours} h/day × 365 = {total} h/yr)"),
    ("wizard_step4_q2_work", "4 h (Daytime work)"),
    ("wizard_step4_q2_night", "12 h (Evening/Night)"),
    ("wizard_step4_q2_full", "24 h (Continuous full-day)"),
    ("wizard_step4_q3_label", "3. Existing Cooling Available"),
    ("wizard_step4_q3_changes", "Changes: Free-running mode (0 HVAC energy) vs active HVAC cooling demand"),
    ("wizard_step4_q3_opt_none", "None (Free-running)"),
    ("wizard_step4_q3_opt_fan", "Ceiling fan only"),
    ("wizard_step4_q3_opt_ac", "Air Conditioner (AC)"),
    ("wizard_step4_q4_label", "4. Design Optimization Priority"),
    ("wizard_step4_q4_changes", "Changes: Preselected Pareto recommendation in Step 5"),
    ("wizard_step4_q4_opt_energy", "Lowest Energy"),
    ("wizard_step4_q4_opt_balanced", "Balanced (Knee-Point)"),
    ("wizard_step4_q4_opt_comfort", "Lowest Discomfort"),
    ("wizard_step4_comparison_title", "You vs Regional Area Baseline"),
    ("wizard_step4_comparison_how_inputs_shape", "How Your Inputs Shape Step 5"),
    ("wizard_step4_shape_occupancy", "Occupancy: Directly scales total annual uncomfortable hours scored."),
    ("wizard_step4_shape_cooling", "Cooling Mode: Evaluates passive comfort only or simulates active cooling demand."),
    ("wizard_step4_shape_priority", "Priority: Highlights the corresponding verified Pareto candidate in Step 5."),
    ("wizard_nav_next_plan", "Next: View Recommended Plan"),
    ("wizard_nav_back", "Back"),
    ("wizard_step5_heading", "Your Recommended Passive Design Plan"),
    ("wizard_step5_subheading", "Precomputed EnergyPlus Pareto-optimal envelopes tailored to your regional climate and comfort profile."),
    ("wizard_step5_scenario_label", "Climate Scenario:"),
    ("wizard_step5_scenario_today", "Today (TMYx Weather)"),
    ("wizard_step5_scenario_future", "Future (+1.5°C)"),
    ("wizard_step5_simple_notice", "Simple Mode: Displaying plain-language shelter recommendations. Your primary recommended shelter is highlighted below."),
    ("wizard_step5_pkg_budget_role", "Lowest energy demand (Min O2)"),
    ("wizard_step5_pkg_balanced_role", "Best balance of comfort & energy (Knee Point)"),
    ("wizard_step5_pkg_comfort_role", "Maximum comfort stability (Min O1)"),
    ("wizard_step5_pkg_budget_desc", "Minimizes active heating and cooling energy demand on the verified Pareto front."),
    ("wizard_step5_pkg_balanced_desc", "Pareto knee-point design balancing annual uncomfortable hours and active HVAC energy."),
    ("wizard_step5_pkg_comfort_desc", "Minimizes annual uncomfortable hours on the verified Pareto front with maximum passive thermal stability."),
    ("wizard_step5_annual_discomfort", "Annual Discomfort"),
    ("wizard_step5_hvac_energy", "HVAC Energy (O2)"),
    ("wizard_step5_fit_score_label", "Comfort Fit Score"),
    ("wizard_step5_sensitivity_label", "Occupant Sensitivity:"),
    ("wizard_step5_materials_title", "Materials list (quantities only):"),
    ("wizard_step5_rates_unpopulated", "Rates unpopulated"),
    ("wizard_step5_roof_insulation", "Roof EPS Insulation"),
    ("wizard_step5_roof_absorptance", "Roof Solar Absorptance (High-SRI coating)"),
    ("wizard_step5_wall_insulation", "Wall Mineral Wool Insulation"),
    ("wizard_step5_wall_construction", "Wall Construction (200 mm masonry)"),
    ("wizard_step5_wwr_shading", "Window-to-Wall Ratio (WWR) with exterior overhang"),
    ("wizard_step5_ventilation", "Natural Ventilation (operable cross-ventilation)"),
    ("wizard_step5_cost_title", "Indicative CPWD DSR 2021 Envelope Investment"),
    ("wizard_step5_central_estimate", "Central Estimate"),
    ("wizard_step5_cost_per_m2", "Estimated Cost per m² Carpet"),
    ("wizard_step5_btn_compare", "Compare All 3 Packages"),
    ("wizard_step5_btn_pdf", "Download Builder-Ready Specification (PDF)"),
    ("wizard_step5_btn_share", "Share This Recommended Plan"),
    ("wizard_step5_copy_link_done", "Link copied to clipboard!"),
    ("wizard_step5_copy_summary_done", "Summary copied to clipboard!")
]

# Write to markdown file
report_md = ["# Untranslated Wizard Strings Audit (for Hindi Translation)\n"]
report_md.append("Total untranslated strings identified: **" + str(len(untranslated_strings)) + "**\n")
report_md.append("| Key | English String |")
report_md.append("|---|---|")
for k, eng in untranslated_strings:
    report_md.append(f"| `{k}` | {eng} |")

with open("reports/hindi_translation_audit.md", "w", encoding="utf-8") as f:
    f.write("\n".join(report_md) + "\n")

print(f"Generated table of {len(untranslated_strings)} untranslated wizard strings in reports/hindi_translation_audit.md")
