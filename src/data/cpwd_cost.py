"""
src/data/cpwd_cost.py

Cost estimation utility for ClimateAdapt-Comfort v2.
Computes rough indicative construction cost ranges for envelope interventions
based strictly on official CPWD Delhi Schedule of Rates (DSR).

HONESTY RULES:
- Never invent prices, rates, or results.
- Unverified items are strictly flagged 'TO BE FILLED'.
- Costs are rough research ranges, never presented as contractor quotes or tenders.
"""

import os
import pandas as pd
from typing import Dict, Any, Tuple

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
CSV_PATH = os.path.join(REPO_ROOT, "data/processed/cpwd_dsr_rates.csv")

# Standard reference single-zone shelter footprint parameters (fixed spec footprint)
# Floor area: 30 m2 (e.g. 5m x 6m), wall height 3m.
# Total roof area: 30 m2.
# Total perimeter wall facade area: (5 + 6) * 2 * 3 = 66 m2.
DEFAULT_DIMENSIONS = {
    "floor_area_m2": 30.0,
    "roof_area_m2": 30.0,
    "wall_facade_area_m2": 66.0,
    "window_height_m": 1.2
}

def load_dsr_schedule() -> pd.DataFrame:
    """Loads the verified CPWD DSR rate schedule."""
    if not os.path.exists(CSV_PATH):
        raise FileNotFoundError(f"CPWD DSR rate schedule not found at {CSV_PATH}")
    return pd.read_csv(CSV_PATH)

def validate_dsr_rates() -> Tuple[bool, list]:
    """
    Validation step: blocks release if any item has status 'TO BE FILLED' or missing rate.
    Returns (is_valid, list_of_issues).
    """
    df = load_dsr_schedule()
    issues = []
    
    for idx, row in df.iterrows():
        status = str(row.get('validation_status', '')).strip().upper()
        rate = row.get('rate_inr', None)
        
        if status == "TO BE FILLED" or "TO BE FILLED" in str(row.values):
            issues.append(f"Row {idx} ({row.get('dsr_item_code')}: {row.get('component')}): Marked 'TO BE FILLED'")
        elif pd.isna(rate) or rate <= 0:
            issues.append(f"Row {idx} ({row.get('dsr_item_code')}): Invalid rate {rate}")
            
    is_valid = len(issues) == 0
    return is_valid, issues

def estimate_envelope_cost(
    design: Dict[str, Any],
    dimensions: Dict[str, float] = None,
    uncertainty_band: float = 0.15
) -> Dict[str, Any]:
    """
    Estimates passive envelope intervention cost using CPWD DSR schedule.
    Returns indicative cost range (low, nominal, high) in INR and per m2.
    """
    dims = dimensions or DEFAULT_DIMENSIONS
    df = load_dsr_schedule().set_index('component')
    
    roof_area = dims["roof_area_m2"]
    wall_area = dims["wall_facade_area_m2"]
    
    # 1. Roof Insulation (mm -> rate per 50mm)
    roof_ins_mm = float(design.get('roof_insulation_thickness', 0.0))
    if roof_ins_mm < 1.0 and roof_ins_mm > 0: # handle meters if passed as 0.05
        roof_ins_mm *= 1000.0
    roof_units_50mm = roof_ins_mm / 50.0
    roof_ins_rate = float(df.loc['roof_insulation_thickness', 'rate_inr']) if 'roof_insulation_thickness' in df.index else 0.0
    cost_roof_ins = roof_area * roof_units_50mm * roof_ins_rate
    
    # 2. Wall Insulation (mm -> rate per 50mm)
    wall_ins_mm = float(design.get('wall_insulation_thickness', 0.0))
    if wall_ins_mm < 1.0 and wall_ins_mm > 0:
        wall_ins_mm *= 1000.0
    wall_units_50mm = wall_ins_mm / 50.0
    wall_ins_rate = float(df.loc['wall_insulation_thickness', 'rate_inr']) if 'wall_insulation_thickness' in df.index else 0.0
    cost_wall_ins = wall_area * wall_units_50mm * wall_ins_rate
    
    # 3. Wall Construction Mass
    wall_mass = str(design.get('wall_mass_class', 'medium')).lower()
    if 'heavy' in wall_mass:
        mass_key = 'wall_mass_heavy'
        # 200mm concrete wall = 0.20 m3 per m2 facade
        cost_wall_mass = wall_area * 0.20 * float(df.loc[mass_key, 'rate_inr'])
    elif 'light' in wall_mass:
        mass_key = 'wall_mass_light'
        cost_wall_mass = wall_area * float(df.loc[mass_key, 'rate_inr'])
    else:
        mass_key = 'wall_mass_medium'
        # 200mm brick wall in 1:6 cement mortar = 0.20 m3 per m2 facade
        cost_wall_mass = wall_area * 0.20 * float(df.loc[mass_key, 'rate_inr'])
        
    # 4. Roof Finish / Reflective Coating
    roof_abs = float(design.get('roof_solar_absorptance', 0.60))
    if roof_abs <= 0.40:
        cost_roof_finish = roof_area * float(df.loc['roof_solar_absorptance', 'rate_inr']) # cool roof coating
    else:
        cost_roof_finish = roof_area * float(df.loc['roof_solar_absorptance_standard', 'rate_inr']) # standard cement
        
    # 5. Glazing (WWR fraction)
    wwr = float(design.get('wwr', 0.15))
    if wwr > 1.0: # handle percentage
        wwr = wwr / 100.0
    window_area = wall_area * wwr
    cost_glazing = window_area * float(df.loc['wwr', 'rate_inr'])
    
    # 6. Overhang Shading
    shading_m = float(design.get('shading_depth', 0.0))
    # Approximate window width = window_area / window_height
    window_width = window_area / max(0.5, dims["window_height_m"])
    shading_projection_m2 = window_width * shading_m
    cost_shading = shading_projection_m2 * float(df.loc['shading_depth', 'rate_inr'])
    
    # Total nominal cost of envelope components
    total_nominal = (
        cost_roof_ins +
        cost_wall_ins +
        cost_wall_mass +
        cost_roof_finish +
        cost_glazing +
        cost_shading
    )
    
    # Apply standard regional construction variance (±15% CPWD index)
    cost_min = round(total_nominal * (1.0 - uncertainty_band), -2)
    cost_nominal = round(total_nominal, -2)
    cost_max = round(total_nominal * (1.0 + uncertainty_band), -2)
    
    cost_per_m2_nominal = round(total_nominal / dims["floor_area_m2"], 1)
    cost_per_m2_min = round(cost_min / dims["floor_area_m2"], 1)
    cost_per_m2_max = round(cost_max / dims["floor_area_m2"], 1)
    
    return {
        "cost_inr_nominal": cost_nominal,
        "cost_inr_min": cost_min,
        "cost_inr_max": cost_max,
        "cost_inr_range_str": f"₹{int(cost_min):,} – ₹{int(cost_max):,}",
        "cost_per_m2_range_str": f"₹{int(cost_per_m2_min):,} – ₹{int(cost_per_m2_max):,}/m²",
        "breakdown": {
            "roof_insulation": round(cost_roof_ins),
            "wall_insulation": round(cost_wall_ins),
            "wall_construction": round(cost_wall_mass),
            "roof_finish": round(cost_roof_finish),
            "glazing": round(cost_glazing),
            "shading_overhang": round(cost_shading)
        },
        "source": "CPWD Delhi Schedule of Rates (DSR) 2021",
        "disclaimer": "Rough indicative academic research range based on CPWD DSR schedule. Never present as an official contractor quote or tender."
    }
