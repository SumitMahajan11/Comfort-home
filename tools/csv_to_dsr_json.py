"""
tools/csv_to_dsr_json.py

Converts data/costs/dsr_rates_template.csv to data/costs/dsr_rates.json.
Preserves null values for unfilled rates and parses city cost indices.
"""

import os
import sys
import csv
import json

def convert_csv_to_json(csv_path="data/costs/dsr_rates_template.csv", json_path="data/costs/dsr_rates.json"):
    if not os.path.exists(csv_path):
        raise FileNotFoundError(f"Source CSV not found: {csv_path}")

    items = []
    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            def parse_float_or_null(val):
                if val is None or str(val).strip() == "" or str(val).strip().upper() == "NULL":
                    return None
                try:
                    return float(val)
                except ValueError:
                    return None

            item = {
                "item_id": row["item_id"].strip(),
                "description": row["description"].strip(),
                "unit": row["unit"].strip(),
                "dsr_item_code": row["dsr_item_code"].strip() if row["dsr_item_code"].strip() else "TO BE FILLED",
                "rate_inr_low": parse_float_or_null(row["rate_inr_low"]),
                "rate_inr_high": parse_float_or_null(row["rate_inr_high"]),
                "dsr_edition": row["dsr_edition"].strip() if row["dsr_edition"].strip() else "TO BE FILLED",
                "city_cost_index": {
                    "Jodhpur": parse_float_or_null(row.get("cci_Jodhpur")),
                    "Mumbai": parse_float_or_null(row.get("cci_Mumbai")),
                    "New_Delhi": parse_float_or_null(row.get("cci_New_Delhi")),
                    "Bengaluru": parse_float_or_null(row.get("cci_Bengaluru")),
                    "Shimla": parse_float_or_null(row.get("cci_Shimla"))
                },
                "source_note": row.get("source_note", "CPWD DSR rate template - awaiting official manual input").strip(),
                "status": row.get("status", "TO BE FILLED").strip()
            }
            items.append(item)

    os.makedirs(os.path.dirname(json_path), exist_ok=True)
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(items, f, indent=2)

    print(f"Successfully converted {len(items)} rate items from {csv_path} to {json_path}.")
    unfilled_count = sum(1 for item in items if item["rate_inr_low"] is None or item["rate_inr_high"] is None)
    print(f"Items with unfilled rates: {unfilled_count}/{len(items)} (Status: TO BE FILLED)")

if __name__ == "__main__":
    csv_file = sys.argv[1] if len(sys.argv) > 1 else "data/costs/dsr_rates_template.csv"
    json_file = sys.argv[2] if len(sys.argv) > 2 else "data/costs/dsr_rates.json"
    convert_csv_to_json(csv_file, json_file)
