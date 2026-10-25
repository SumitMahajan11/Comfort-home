"""
src/costs/bom.py

Bill of Materials (BOM) Calculation Engine for ClimateAdapt-Comfort.
Translates design parameters and building typology geometry into physical,
verifiable material quantities matching the EnergyPlus IDF templates.

Strict Evidence & Geometric Integrity:
- Quantities are derived directly from the template dimensions (wall area minus window area,
  roof area, window area, shading projection, insulation volumes).
- Quantities scale predictably with floor area and geometry.
- Full mathematical equations documented in docs/COSTS.md.
"""

from typing import Dict, Any, List

# Standard default dimensions matching IDF templates
TYPOLOGY_GEOMETRY = {
    "shelter_v1": {
        "floor_area_m2": 20.25,
        "height_m": 3.0,
        "perimeter_m": 18.0,
        "gross_wall_area_m2": 54.0,
        "roof_area_m2": 20.25,
        "exposed_roof_default": True,
        "window_height_m": 1.2
    },
    "house": {
        "floor_area_m2": 59.0,
        "height_m": 3.0,
        "perimeter_m": 31.5,
        "gross_wall_area_m2": 94.5,
        "roof_area_m2": 59.0,
        "exposed_roof_default": True,
        "window_height_m": 1.2
    },
    "apartment": {
        "floor_area_m2": 55.0,
        "height_m": 2.8,
        "perimeter_m": 15.0, # 2 exterior walls (North & South, 7.5m each); East/West are adiabatic shared party walls
        "gross_wall_area_m2": 42.0, # 15.0 * 2.8
        "roof_area_m2": 0.0, # middle floor has adiabatic ceiling to upper unit
        "exposed_roof_default": False,
        "window_height_m": 1.2
    },
    "commercial": {
        "floor_area_m2": 80.0,
        "height_m": 3.5,
        "perimeter_m": 36.0, # 10m x 8m footprint
        "gross_wall_area_m2": 126.0, # 36.0 * 3.5
        "roof_area_m2": 80.0,
        "exposed_roof_default": True,
        "window_height_m": 1.5
    }
}

def build_bom(
    building_type: str,
    design_variables: Dict[str, Any],
    floor_area_m2: float = None,
    city: str = None,
    floor_position: str = "middle"
) -> List[Dict[str, Any]]:
    """
    Builds a Bill of Materials (BOM) with quantities from design variables.

    Args:
        building_type: 'shelter_v1', 'house', 'apartment', or 'commercial'
        design_variables: dictionary of design parameters:
            - roof_insulation_thickness (m)
            - wall_insulation_thickness (m)
            - wall_mass_class ('light', 'medium', 'heavy')
            - roof_solar_absorptance (float 0.3 - 0.9)
            - wwr (float 0.05 - 0.40)
            - orientation (deg)
            - shading_depth (m 0.0 - 1.0)
            - ventilation_ach (ACH 1.0 - 15.0)
        floor_area_m2: optional custom floor area (scales geometry proportionally)
        city: city name (metadata)
        floor_position: for apartment ('ground', 'middle', 'top')

    Returns:
        List of BOM item dictionaries:
        [
            {
                "item_id": str,
                "category": str,
                "description": str,
                "quantity": float,
                "unit": str,
                "formula": str
            }, ...
        ]
    """
    b_type = building_type.lower()
    if b_type not in TYPOLOGY_GEOMETRY:
        # Default fallback to shelter_v1
        geom = TYPOLOGY_GEOMETRY["shelter_v1"].copy()
    else:
        geom = TYPOLOGY_GEOMETRY[b_type].copy()

    # Scale geometry if custom floor area provided
    base_floor = geom["floor_area_m2"]
    scale_factor = 1.0
    if floor_area_m2 and floor_area_m2 > 0 and base_floor > 0:
        scale_factor = floor_area_m2 / base_floor

    linear_scale = scale_factor ** 0.5
    gross_wall_area = geom["gross_wall_area_m2"] * linear_scale
    
    # Roof exposure logic (apartment floor_position)
    if b_type == "apartment":
        if floor_position == "top":
            roof_area = geom["floor_area_m2"] * scale_factor
        else:
            roof_area = 0.0 # middle or ground: adiabatic ceiling
    else:
        roof_area = geom["roof_area_m2"] * scale_factor

    # Extract design variables
    roof_ins_thick = float(design_variables.get("roof_insulation_thickness", 0.0))
    wall_ins_thick = float(design_variables.get("wall_insulation_thickness", 0.0))
    wall_mass = str(design_variables.get("wall_mass_class", "medium")).lower()
    roof_absorptance = float(design_variables.get("roof_solar_absorptance", 0.60))
    wwr = float(design_variables.get("wwr", 0.20))
    shading_depth = float(design_variables.get("shading_depth", 0.0))
    vent_ach = float(design_variables.get("ventilation_ach", 5.0))

    # Geometrical calculations
    window_area = round(gross_wall_area * wwr, 3)
    net_wall_area = round(gross_wall_area - window_area, 3)
    wall_insulation_volume = round(net_wall_area * wall_ins_thick, 4)
    roof_insulation_volume = round(roof_area * roof_ins_thick, 4)

    # Shading projection calculation
    win_h = geom.get("window_height_m", 1.2)
    window_width_total = window_area / win_h if win_h > 0 else 0.0
    shading_area = round(window_width_total * shading_depth, 3)

    # Louver / ventilation hardware area (fraction of window area)
    # Scaled with ACH demand up to 50% operable window opening
    operable_fraction = min(0.60, max(0.10, vent_ach / 15.0 * 0.50))
    ventilation_hardware_area = round(window_area * operable_fraction, 3)

    bom_items = []

    # 1. Wall Masonry Item
    if wall_mass == "heavy":
        wall_item_id = "wall_heavy_rcc"
        wall_desc = "Reinforced cement concrete M25 work in walls (200 mm)"
    elif wall_mass == "light":
        wall_item_id = "wall_light_drywall"
        wall_desc = "Lightweight fiber cement panel dry wall system with light gauge metal frame"
    else:
        wall_item_id = "wall_medium_brick"
        wall_desc = "Common burnt clay brick masonry 1:6 in cement mortar for exterior walls (200 mm)"

    bom_items.append({
        "item_id": wall_item_id,
        "category": "wall_masonry",
        "description": wall_desc,
        "quantity": net_wall_area,
        "unit": "m2",
        "formula": f"gross_wall_area ({gross_wall_area:.2f}) - window_area ({window_area:.2f})"
    })

    # 2. Wall Insulation (if thickness > 0)
    if wall_ins_thick > 0.0001:
        bom_items.append({
            "item_id": "wall_insulation_eps",
            "category": "insulation",
            "description": f"Expanded polystyrene (EPS) / mineral wool wall board insulation ({int(wall_ins_thick*1000)} mm)",
            "quantity": wall_insulation_volume,
            "unit": "m3",
            "formula": f"net_wall_area ({net_wall_area:.2f}) * thickness ({wall_ins_thick:.4f} m)"
        })

    # 3. Roof Slab (if roof exposed)
    if roof_area > 0.01:
        bom_items.append({
            "item_id": "roof_slab_rcc",
            "category": "roof_structure",
            "description": "Reinforced cement concrete 150mm roof slab including shuttering and reinforcement",
            "quantity": round(roof_area, 3),
            "unit": "m2",
            "formula": f"roof_area ({roof_area:.2f} m2)"
        })

        # 4. Roof Insulation (if thickness > 0)
        if roof_ins_thick > 0.0001:
            bom_items.append({
                "item_id": "roof_insulation_eps",
                "category": "insulation",
                "description": f"Expanded polystyrene (EPS) board roof thermal insulation ({int(roof_ins_thick*1000)} mm)",
                "quantity": roof_insulation_volume,
                "unit": "m3",
                "formula": f"roof_area ({roof_area:.2f}) * thickness ({roof_ins_thick:.4f} m)"
            })

        # 5. Roof Finish / Reflective Coating
        if roof_absorptance <= 0.45:
            bom_items.append({
                "item_id": "roof_cool_coating",
                "category": "roof_finish",
                "description": "High solar reflectance index (SRI >= 104) reflective elastomeric cool roof coating",
                "quantity": round(roof_area, 3),
                "unit": "m2",
                "formula": f"roof_area ({roof_area:.2f} m2) [absorptance {roof_absorptance:.2f} <= 0.45]"
            })
        else:
            bom_items.append({
                "item_id": "roof_standard_finish",
                "category": "roof_finish",
                "description": "Standard cementitious water-proofing and wearing coat terrace finish",
                "quantity": round(roof_area, 3),
                "unit": "m2",
                "formula": f"roof_area ({roof_area:.2f} m2) [absorptance {roof_absorptance:.2f} > 0.45]"
            })

    # 6. Window Glazing
    bom_items.append({
        "item_id": "window_glazing_standard",
        "category": "glazing",
        "description": "Powder coated aluminium window frame with 6mm clear float glass glazing",
        "quantity": window_area,
        "unit": "m2",
        "formula": f"gross_wall_area ({gross_wall_area:.2f}) * WWR ({wwr:.3f})"
    })

    # 7. Shading Overhang (if depth > 0)
    if shading_depth > 0.001 and shading_area > 0.001:
        bom_items.append({
            "item_id": "shading_overhang_cantilever",
            "category": "shading",
            "description": f"Cantilever horizontal exterior window sunshade overhang ({shading_depth:.2f} m depth)",
            "quantity": shading_area,
            "unit": "m2",
            "formula": f"window_width ({window_width_total:.2f} m) * shading_depth ({shading_depth:.2f} m)"
        })

    # 8. Ventilation Operable Louvers / Hardware
    bom_items.append({
        "item_id": "ventilation_louvers",
        "category": "ventilation",
        "description": "Operable glazed ventilation louvers / wire-mesh ventilation shutters",
        "quantity": ventilation_hardware_area,
        "unit": "m2",
        "formula": f"window_area ({window_area:.2f}) * operable_fraction ({operable_fraction:.2f})"
    })

    return bom_items
