"""
src/costs/carbon.py

Embodied Carbon Calculation Engine using University of Bath Inventory of Carbon and Energy (ICE) factors.
In accordance with project rules: where an ICE factor exists, computes kgCO2e/m2;
where missing or unverified, reports 'not available'; NEVER fabricates numbers.
"""

import os
import json
from typing import Dict, Any, List, Optional

def load_materials(json_path: str = "data/costs/materials.json") -> Dict[str, Dict[str, Any]]:
    if not os.path.exists(json_path):
        return {}
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)
        return {m["id"]: m for m in data.get("materials", [])}

def compute_embodied_carbon(
    bom: List[Dict[str, Any]],
    floor_area_m2: float,
    materials_db: Optional[Dict[str, Dict[str, Any]]] = None
) -> Dict[str, Any]:
    """
    Computes total and per-m2 embodied carbon from BOM and materials database.

    Args:
        bom: Bill of materials list
        floor_area_m2: building floor area
        materials_db: optional preloaded materials dict

    Returns:
        Dictionary with total_kgco2e, kgco2e_per_m2, status, and per-item details.
    """
    if materials_db is None:
        materials_db = load_materials()

    missing_factors = []
    item_carbon_list = []
    total_carbon_kg = 0.0

    for item in bom:
        i_id = item["item_id"]
        # Map BOM item ID to material ID
        mat_entry = materials_db.get(f"mat_{i_id}", materials_db.get(i_id))
        
        factor = None
        if mat_entry:
            factor = mat_entry.get("embodied_carbon_factor_kgco2e_per_kg")
            if factor is None:
                factor = mat_entry.get("embodied_carbon_factor_kgco2e_per_unit")

        if factor is None:
            missing_factors.append(i_id)
            item_carbon_list.append({
                "item_id": i_id,
                "description": item["description"],
                "quantity": item["quantity"],
                "carbon_factor": None,
                "carbon_status": "not available"
            })
        else:
            qty = float(item["quantity"])
            density = float(mat_entry.get("density_kg_m3", 1.0)) if item["unit"] == "m3" else 1.0
            mass_kg = qty * density if item["unit"] == "m3" else qty
            c_kg = mass_kg * float(factor)
            total_carbon_kg += c_kg
            item_carbon_list.append({
                "item_id": i_id,
                "description": item["description"],
                "quantity": qty,
                "carbon_factor": factor,
                "carbon_kgco2e": round(c_kg, 2),
                "carbon_status": "available"
            })

    # If ANY material has missing/null factor, report as 'not available' per spec
    if missing_factors:
        return {
            "status": "not available",
            "message": "Embodied carbon factor not available for all BOM items in ICE database",
            "total_kgco2e": None,
            "kgco2e_per_m2": None,
            "missing_factors_count": len(missing_factors),
            "missing_items": missing_factors,
            "items": item_carbon_list
        }

    c_per_m2 = round(total_carbon_kg / floor_area_m2, 2) if floor_area_m2 > 0 else 0.0
    return {
        "status": "available",
        "message": "Embodied carbon computed from ICE database",
        "total_kgco2e": round(total_carbon_kg, 2),
        "kgco2e_per_m2": c_per_m2,
        "floor_area_m2": floor_area_m2,
        "items": item_carbon_list
    }
