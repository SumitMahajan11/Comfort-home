"""
src/costs/estimate.py

Cost Range Estimation Engine using CPWD DSR Rates and City Cost Indices.
Outputs an indicative cost range for early-stage decision support, never a construction quote.

Key Rules:
1. Strict Null Gating: Refuses to calculate arbitrary numbers if rates are unfilled.
   Returns status="UNAVAILABLE" and "Cost range unavailable: rates not yet loaded".
2. Documented Contingency: Configurable default +/- 15% band (Assumption A-012).
3. Reference Comparison & Payback: Computes incremental cost vs reference and payback
   period in years based on O2 energy savings and SERC retail electricity tariffs.
"""

import os
import json
from typing import Dict, Any, List, Optional, Tuple

DEFAULT_CONTINGENCY_PCT = 15.0 # Assumption A-012: +/- 15% contingency band

def load_dsr_rates(json_path: str = "data/costs/dsr_rates.json") -> Dict[str, Dict[str, Any]]:
    if not os.path.exists(json_path):
        return {}
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)
        return {item["item_id"]: item for item in data}

def load_tariffs(json_path: str = "data/costs/tariffs.json") -> Dict[str, Any]:
    if not os.path.exists(json_path):
        return {}
    with open(json_path, "r", encoding="utf-8") as f:
        return json.load(f)

def estimate_cost_range(
    bom: List[Dict[str, Any]],
    city: str,
    dsr_rates: Optional[Dict[str, Dict[str, Any]]] = None,
    contingency_pct: float = DEFAULT_CONTINGENCY_PCT
) -> Dict[str, Any]:
    """
    Computes indicative cost range (low, mid, high) from BOM and DSR rate schedule.

    Args:
        bom: List of BOM item dicts from build_bom()
        city: reference city name ('Jodhpur', 'Mumbai', 'New_Delhi', 'Bengaluru', 'Shimla')
        dsr_rates: optional preloaded rates dict; loads from data/costs/dsr_rates.json if None
        contingency_pct: percentage contingency band (default +/- 15%)

    Returns:
        Dictionary containing cost range, breakdown, and validity status.
    """
    if dsr_rates is None:
        dsr_rates = load_dsr_rates()

    # Check if any required rate is null or missing
    unfilled_items = []
    for item in bom:
        i_id = item["item_id"]
        rate_entry = dsr_rates.get(i_id)
        if not rate_entry or rate_entry.get("rate_inr_low") is None or rate_entry.get("rate_inr_high") is None:
            unfilled_items.append(i_id)

    if unfilled_items:
        return {
            "status": "UNAVAILABLE",
            "message": "Cost range unavailable: rates not yet loaded",
            "cost_inr_low": None,
            "cost_inr_mid": None,
            "cost_inr_high": None,
            "unfilled_items_count": len(unfilled_items),
            "unfilled_items": unfilled_items,
            "contingency_pct": contingency_pct,
            "breakdown": []
        }

    # All rates are valid numbers: compute cost range
    total_low = 0.0
    total_high = 0.0
    breakdown = []

    for item in bom:
        i_id = item["item_id"]
        qty = float(item["quantity"])
        rate_entry = dsr_rates[i_id]
        rate_low = float(rate_entry["rate_inr_low"])
        rate_high = float(rate_entry["rate_inr_high"])

        # City cost index multiplier
        cci_dict = rate_entry.get("city_cost_index", {})
        cci = float(cci_dict.get(city, 1.0)) if cci_dict.get(city) is not None else 1.0

        item_cost_low = round(qty * rate_low * cci, 2)
        item_cost_high = round(qty * rate_high * cci, 2)
        item_cost_mid = round((item_cost_low + item_cost_high) / 2.0, 2)

        total_low += item_cost_low
        total_high += item_cost_high

        breakdown.append({
            "item_id": i_id,
            "description": item["description"],
            "category": item.get("category", "envelope"),
            "quantity": qty,
            "unit": item["unit"],
            "rate_low": rate_low,
            "rate_high": rate_high,
            "city_cost_index": cci,
            "cost_low": item_cost_low,
            "cost_mid": item_cost_mid,
            "cost_high": item_cost_high
        })

    # Apply contingency band
    c_mult_low = 1.0 - (contingency_pct / 100.0)
    c_mult_high = 1.0 + (contingency_pct / 100.0)

    final_low = round(total_low * c_mult_low, 2)
    final_high = round(total_high * c_mult_high, 2)
    final_mid = round((final_low + final_high) / 2.0, 2)

    return {
        "status": "AVAILABLE",
        "message": "Preliminary estimate based on CPWD DSR rate items",
        "cost_inr_low": final_low,
        "cost_inr_mid": final_mid,
        "cost_inr_high": final_high,
        "base_subtotal_low": round(total_low, 2),
        "base_subtotal_high": round(total_high, 2),
        "contingency_pct": contingency_pct,
        "city": city,
        "breakdown": breakdown
    }

def compare_design_to_reference(
    design_cost: Dict[str, Any],
    reference_cost: Dict[str, Any],
    o2_design: float,
    o2_reference: float,
    floor_area_m2: float,
    city: str,
    tariffs: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Compares design against reference building on incremental cost and simple payback.

    Args:
        design_cost: cost range dict of the candidate design
        reference_cost: cost range dict of the reference building (e.g. R2)
        o2_design: annual energy use intensity (kWh/m2/yr) of design
        o2_reference: annual energy use intensity (kWh/m2/yr) of reference
        floor_area_m2: building floor area in m2
        city: reference city
        tariffs: optional tariffs dict

    Returns:
        Dict containing extra cost range, annual energy savings, and payback period.
    """
    if tariffs is None:
        tariffs = load_tariffs()

    tariff_val = tariffs.get("tariffs_inr_per_kwh", {}).get(city)

    # Check if costs are available
    if design_cost.get("status") != "AVAILABLE" or reference_cost.get("status") != "AVAILABLE":
        return {
            "status": "UNAVAILABLE",
            "message": "Cost comparison and payback unavailable: rates not yet loaded",
            "extra_cost_low": None,
            "extra_cost_mid": None,
            "extra_cost_high": None,
            "annual_energy_saved_kwh": round(max(0.0, (o2_reference - o2_design) * floor_area_m2), 1),
            "tariff_inr_per_kwh": tariff_val,
            "payback_years": None
        }

    extra_low = round(design_cost["cost_inr_low"] - reference_cost["cost_inr_low"], 2)
    extra_mid = round(design_cost["cost_inr_mid"] - reference_cost["cost_inr_mid"], 2)
    extra_high = round(design_cost["cost_inr_high"] - reference_cost["cost_inr_high"], 2)

    annual_kwh_saved = max(0.0, (o2_reference - o2_design) * floor_area_m2)

    payback_years = None
    if tariff_val is not None and tariff_val > 0 and annual_kwh_saved > 0:
        annual_bill_saving_inr = annual_kwh_saved * tariff_val
        if annual_bill_saving_inr > 0:
            payback_years = round(extra_mid / annual_bill_saving_inr, 2)
            if payback_years < 0:
                payback_years = 0.0 # design is cheaper than reference and saves energy

    return {
        "status": "AVAILABLE",
        "message": "Incremental cost and payback estimate",
        "extra_cost_low": extra_low,
        "extra_cost_mid": extra_mid,
        "extra_cost_high": extra_high,
        "annual_energy_saved_kwh": round(annual_kwh_saved, 1),
        "tariff_inr_per_kwh": tariff_val,
        "payback_years": payback_years
    }
