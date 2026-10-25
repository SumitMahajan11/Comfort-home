"""
tools/validate_costs.py

Validates CPWD DSR cost rates in data/costs/dsr_rates.json.
Fails loudly (exit code 1) if any cost item required by any design has a null rate.

Enforces project honesty rule: NEVER fabricate or substitute default cost numbers.
The API must refuse to display monetary cost estimates while rates are unfilled,
returning "Cost range unavailable: rates not yet loaded".
"""

import os
import sys
import json

REQUIRED_BOM_ITEM_IDS = [
    "wall_medium_brick",
    "wall_heavy_rcc",
    "wall_light_drywall",
    "wall_insulation_eps",
    "roof_slab_rcc",
    "roof_insulation_eps",
    "roof_cool_coating",
    "roof_standard_finish",
    "window_glazing_standard",
    "shading_overhang_cantilever"
]

def load_dsr_rates(json_path="data/costs/dsr_rates.json"):
    if not os.path.exists(json_path):
        raise FileNotFoundError(f"DSR rates file not found at: {json_path}")
    with open(json_path, "r", encoding="utf-8") as f:
        return json.load(f)

def validate_cost_rates(json_path="data/costs/dsr_rates.json", required_items=None):
    """
    Validates that all specified or loaded cost items have non-null rate_inr_low and rate_inr_high.
    Returns:
        is_valid (bool): True if all required items have valid numeric rates.
        unfilled_items (list): List of dicts describing items with null/missing rates.
    """
    items = load_dsr_rates(json_path)
    items_by_id = {item["item_id"]: item for item in items}
    
    check_ids = required_items if required_items is not None else list(items_by_id.keys())
    unfilled = []

    for item_id in check_ids:
        if item_id not in items_by_id:
            unfilled.append({
                "item_id": item_id,
                "reason": "ITEM_MISSING_FROM_DSR_RATES",
                "description": "Item referenced by design but not found in rate schedule"
            })
            continue

        item = items_by_id[item_id]
        rate_low = item.get("rate_inr_low")
        rate_high = item.get("rate_inr_high")

        if rate_low is None or rate_high is None:
            unfilled.append({
                "item_id": item_id,
                "reason": "RATE_IS_NULL",
                "description": item.get("description", "No description"),
                "status": item.get("status", "TO BE FILLED"),
                "rate_inr_low": rate_low,
                "rate_inr_high": rate_high
            })

    is_valid = len(unfilled) == 0
    return is_valid, unfilled

def main():
    print("=" * 80)
    print("CPWD DSR RATE VALIDATION AUDITOR (tools/validate_costs.py)")
    print("=" * 80)

    rates_file = "data/costs/dsr_rates.json"
    is_valid, unfilled = validate_cost_rates(rates_file, REQUIRED_BOM_ITEM_IDS)

    if not is_valid:
        print("\n[VALIDATION FAILED - RATES NOT LOADED]")
        print(f"The following {len(unfilled)} required envelope cost items have null rates:")
        print("-" * 80)
        for u in unfilled:
            print(f"  - {u['item_id']:30s} | Status: {u.get('status', 'TO BE FILLED'):15s} | Reason: {u['reason']}")
            print(f"    Desc: {u['description']}")
        print("-" * 80)
        print("ACTION REQUIRED:")
        print("Fill the official CPWD DSR rate figures in data/costs/dsr_rates_template.csv")
        print("and re-run tools/csv_to_dsr_json.py.")
        print("\nAPI ENFORCEMENT:")
        print("In accordance with project rules, the web API must display:")
        print('  "Cost range unavailable: rates not yet loaded"')
        print("and refuse to fabricate arbitrary monetary figures.")
        print("=" * 80)
        sys.exit(1)
    else:
        print(f"\n[VALIDATION PASSED] All {len(REQUIRED_BOM_ITEM_IDS)} envelope cost items are populated with verified numeric rates.")
        print("=" * 80)
        sys.exit(0)

if __name__ == "__main__":
    main()
