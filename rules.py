"""
rules.py: Climate-Adaptive Building Material & Wall Layout Rules Engine
========================================================================
Implements the rule-based expert recommendation engine for ThermoHome AI.

Function:
    recommend(zone: str, season: str, lat: float, comfort_need: str) -> dict

Rules Implemented:
- Cold:
    * Insulated walls (rock wool/EPS + brick)
    * Highest insulation on windward/north wall (flipped to south wall for Southern Hemisphere)
    * Large double-glazed windows on the sun-facing side for passive solar gain
    * Thermal mass (concrete/stone) inside for daytime solar heat retention
- Hot-Dry:
    * Thick AAC blocks or rammed earth on west and east walls (high diurnal thermal lag)
    * Light-colored reflective exterior finish (high albedo SRI > 75)
    * Small shaded windows on west and east walls
    * Cross-ventilation openings on north and south walls
    * High-SRI cool roof
- Hot-Humid:
    * Lightweight, ventilated walls (low thermal capacitance to prevent heat trapping)
    * Large shaded openings on windward sides for continuous breeze capture
    * Reflective cool roof with radiant barrier
    * Avoid heavy thermal mass
- Warm / Mixed:
    * Balanced insulation across envelope
    * Fixed or operable overhangs (chajjas) on the sun-facing side
"""

def _create_material(name: str, reason: str, u_value: str, r_value: str, cost: str) -> dict:
    """
    Helper to construct a typed material specification dictionary.
    Cost must be one of 'Low', 'Med', 'High'.
    """
    assert cost in ("Low", "Med", "High"), f"Invalid cost tier: {cost}"
    return {
        "name": name,
        "reason": reason,
        "u_value": u_value,
        "r_value": r_value,
        "cost": cost
    }


def recommend(zone: str, season: str, lat: float, comfort_need: str) -> dict:
    """
    Recommends building envelope materials and fenestration per cardinal wall (North, South, East, West).

    Parameters:
        zone (str): Climate zone ('Cold', 'Hot-Dry', 'Hot-Humid', 'Warm', 'Mixed').
        season (str): Current astronomical season ('Winter', 'Spring', 'Summer', 'Autumn').
        lat (float): Latitude in degrees (sign determines hemisphere: >= 0 Northern, < 0 Southern).
        comfort_need (str): Comfort assessment ('Needs Heating', 'Needs Cooling', 'Balanced').

    Returns:
        dict: Recommendations structured per cardinal wall ('North', 'South', 'East', 'West'),
              plus 'roof', 'interior', and 'walls' mapping.
    """
    is_northern = lat >= 0.0
    hemisphere = "Northern" if is_northern else "Southern"

    # Identify solar orientation geometry
    # In Northern Hemisphere, equator/sun is South; coldest polar winds typically North.
    # In Southern Hemisphere, equator/sun is North; coldest polar winds typically South.
    sun_facing_wall = "South" if is_northern else "North"
    polar_windward_wall = "North" if is_northern else "South"

    zone_norm = zone.strip().title()
    if "Humid" in zone_norm:
        category = "Hot-Humid"
    elif "Dry" in zone_norm:
        category = "Hot-Dry"
    elif "Cold" in zone_norm:
        category = "Cold"
    else:
        category = "Warm/Mixed"

    # -------------------------------------------------------------------------
    # RULE SET 1: COLD CLIMATE
    # -------------------------------------------------------------------------
    if category == "Cold":
        # Windward/Polar wall gets the highest insulation
        polar_wall_mat = _create_material(
            name="Super-Insulated Brick Wall (120mm Rock Wool + 230mm Dense Brick)",
            reason=f"Maximum continuous thermal insulation on {polar_windward_wall} facade to block biting polar winds and prevent conductive heat loss.",
            u_value="U ≈ 0.24 W/m²K",
            r_value="R ≈ 4.17 m²K/W",
            cost="High"
        )
        polar_window_mat = _create_material(
            name="Triple-Glazed Argon-Filled Window (Small WWR < 12%)",
            reason=f"Minimal glazing on {polar_windward_wall} wall to minimize cold-bridge transmission loss.",
            u_value="U ≈ 1.1 W/m²K",
            r_value="R ≈ 0.91 m²K/W",
            cost="High"
        )

        # Sun-facing wall gets large double-glazed windows for passive solar gain
        sun_wall_mat = _create_material(
            name="Insulated Brick Cavity Wall (80mm EPS + 230mm Brick)",
            reason=f"Insulated cavity wall on sun-facing {sun_facing_wall} facade supporting direct passive solar capture.",
            u_value="U ≈ 0.35 W/m²K",
            r_value="R ≈ 2.86 m²K/W",
            cost="Med"
        )
        sun_window_mat = _create_material(
            name="Large High-Gain Double-Glazed Low-E Windows (WWR 25–35%, SHGC > 0.55)",
            reason=f"Generous equator-facing glazing on {sun_facing_wall} facade designed for passive solar heat gain during daytime hours.",
            u_value="U ≈ 1.6 W/m²K",
            r_value="R ≈ 0.63 m²K/W",
            cost="Med"
        )

        # East and West walls: Standard insulated masonry
        flank_wall_mat = _create_material(
            name="Insulated Brick Wall (80mm Rock Wool / EPS + 230mm Clay Brick)",
            reason="Standard thermal resistance envelope providing continuous winter heat retention.",
            u_value="U ≈ 0.38 W/m²K",
            r_value="R ≈ 2.63 m²K/W",
            cost="Med"
        )
        flank_window_mat = _create_material(
            name="Double-Glazed Low-E Windows (WWR 15%)",
            reason="Airtight double glazing with insulated frame to restrict conductive heat escape.",
            u_value="U ≈ 1.8 W/m²K",
            r_value="R ≈ 0.56 m²K/W",
            cost="Med"
        )

        # Interior thermal mass & roof
        interior_mat = _create_material(
            name="Interior Concrete / Stone Thermal Mass Partition & Dark Stone Floor",
            reason="High thermal capacitance mass placed inside direct sunlight path absorbs daytime passive solar warmth and slowly radiates heat overnight.",
            u_value="U ≈ 2.2 W/m²K",
            r_value="R ≈ 0.45 m²K/W (High Heat Capacity > 200 kJ/m²K)",
            cost="Med"
        )
        roof_mat = _create_material(
            name="Pitched Dark Slate/Metal Roof + 150mm Attic Mineral Wool Blanket",
            reason="Dark solar-absorptive exterior surface capturing winter solar gains, backed by heavy attic insulation to stop rising warm air from escaping.",
            u_value="U ≈ 0.20 W/m²K",
            r_value="R ≈ 5.00 m²K/W",
            cost="High"
        )

        # Assemble per-wall records
        walls = {}
        for cardinal in ["North", "South", "East", "West"]:
            if cardinal == polar_windward_wall:
                walls[cardinal] = {
                    "orientation": cardinal,
                    "description": f"Polar / Windward Facade ({cardinal}) - Highest Insulation",
                    "wall": polar_wall_mat,
                    "glazing": polar_window_mat,
                    "finish": _create_material(
                        name="Airtight Vapor Barrier + Cement Stucco Finish",
                        reason="Prevents cold infiltration and exterior moisture damage.",
                        u_value="N/A",
                        r_value="N/A",
                        cost="Low"
                    ),
                    "materials": [polar_wall_mat, polar_window_mat]
                }
            elif cardinal == sun_facing_wall:
                walls[cardinal] = {
                    "orientation": cardinal,
                    "description": f"Sun-Facing Facade ({cardinal}) - Solar Gain & Large Glazing",
                    "wall": sun_wall_mat,
                    "glazing": sun_window_mat,
                    "finish": _create_material(
                        name="Protective Weather-Resistant Brick Finish",
                        reason="Durable weather barrier accommodating solar exposure.",
                        u_value="N/A",
                        r_value="N/A",
                        cost="Low"
                    ),
                    "materials": [sun_wall_mat, sun_window_mat]
                }
            else:
                walls[cardinal] = {
                    "orientation": cardinal,
                    "description": f"Flank Facade ({cardinal}) - Balanced Insulation",
                    "wall": flank_wall_mat,
                    "glazing": flank_window_mat,
                    "finish": _create_material(
                        name="Weather-Resistant Render",
                        reason="Standard external envelope seal.",
                        u_value="N/A",
                        r_value="N/A",
                        cost="Low"
                    ),
                    "materials": [flank_wall_mat, flank_window_mat]
                }

    # -------------------------------------------------------------------------
    # RULE SET 2: HOT-DRY CLIMATE
    # -------------------------------------------------------------------------
    elif category == "Hot-Dry":
        # East and West walls: Thick AAC blocks or rammed earth, light reflective finish, small shaded windows
        west_east_wall_mat = _create_material(
            name="Thick AAC Blocks (250–300mm) or Stabilized Rammed Earth",
            reason="High thermal mass with 8–10 hour thermal lag dampens intense morning and afternoon desert solar radiation.",
            u_value="U ≈ 0.44 W/m²K",
            r_value="R ≈ 2.27 m²K/W",
            cost="Med"
        )
        reflective_finish = _create_material(
            name="Light-Colored Solar Reflective White Finish (SRI > 75)",
            reason="Reflects harsh direct daytime solar irradiance on vulnerable East and West exposures.",
            u_value="SRI > 75 (Albedo ≈ 0.72)",
            r_value="N/A",
            cost="Low"
        )
        small_shaded_window = _create_material(
            name="Small Deeply Recessed Double Glazing with Overhang (WWR < 10%)",
            reason="Strictly controlled window openings with deep reveals and vertical fins to block low-angle east/west sun.",
            u_value="U ≈ 2.4 W/m²K",
            r_value="R ≈ 0.42 m²K/W",
            cost="Med"
        )

        # North and South walls: Cross-ventilation openings
        ns_wall_mat = _create_material(
            name="Autoclaved Aerated Concrete (AAC) Block Masonry (200mm)",
            reason="Solid envelope providing thermal stability with provisions for cross-ventilation.",
            u_value="U ≈ 0.55 W/m²K",
            r_value="R ≈ 1.82 m²K/W",
            cost="Low"
        )
        cross_vent_opening = _create_material(
            name="Operable Cross-Ventilation Windows with Horizontal Shading (WWR 15–20%)",
            reason="Positioned on North and South facades to capture diurnal and nighttime cooling cross-breezes without solar penalty.",
            u_value="U ≈ 2.6 W/m²K",
            r_value="R ≈ 0.38 m²K/W",
            cost="Med"
        )

        roof_mat = _create_material(
            name="High-Albedo Cool Roof (SRI > 82) + 75mm Overdeck XPS Insulation",
            reason="White broken-china mosaic or reflective cool elastomeric coating over exterior insulation, rejecting >80% of extreme rooftop desert heat.",
            u_value="U ≈ 0.30 W/m²K",
            r_value="R ≈ 3.33 m²K/W",
            cost="Med"
        )
        interior_mat = _create_material(
            name="Polished Stone Floor (Kotah Stone / Terrazzo) + Dense Lime Plaster",
            reason="High thermal admittance surfaces act as a cool thermal sink during daytime hot hours.",
            u_value="U ≈ 2.8 W/m²K",
            r_value="R ≈ 0.36 m²K/W",
            cost="Low"
        )

        walls = {}
        for cardinal in ["North", "South", "East", "West"]:
            if cardinal in ["East", "West"]:
                walls[cardinal] = {
                    "orientation": cardinal,
                    "description": f"{cardinal} Facade - Thick Mass & Small Shaded Openings",
                    "wall": west_east_wall_mat,
                    "glazing": small_shaded_window,
                    "finish": reflective_finish,
                    "materials": [west_east_wall_mat, reflective_finish, small_shaded_window]
                }
            else:
                walls[cardinal] = {
                    "orientation": cardinal,
                    "description": f"{cardinal} Facade - Cross-Ventilation Openings",
                    "wall": ns_wall_mat,
                    "glazing": cross_vent_opening,
                    "finish": reflective_finish,
                    "materials": [ns_wall_mat, cross_vent_opening, reflective_finish]
                }

    # -------------------------------------------------------------------------
    # RULE SET 3: HOT-HUMID CLIMATE
    # -------------------------------------------------------------------------
    elif category == "Hot-Humid":
        # Lightweight ventilated walls, large shaded openings on windward, reflective roof, avoid heavy mass
        lightweight_wall = _create_material(
            name="Lightweight Ventilated Cavity Wall (Perforated AAC / Fiber-Cement Board + Air Gap)",
            reason="Low thermal capacitance prevents nighttime heat entrapment; ventilated air cavity continuously exhausts heat.",
            u_value="U ≈ 0.60 W/m²K",
            r_value="R ≈ 1.67 m²K/W",
            cost="Low"
        )
        windward_large_openings = _create_material(
            name="Large Shaded Louvered Windows (WWR 30–40% with Deep Overhangs & Mesh)",
            reason="Maximizes continuous natural cross-ventilation across windward facades while preventing direct solar gain and rain ingress.",
            u_value="U ≈ 3.2 W/m²K",
            r_value="R ≈ 0.31 m²K/W",
            cost="Med"
        )
        sheltered_openings = _create_material(
            name="Operable Casement Windows with Exterior Shading (WWR 20–25%)",
            reason="Facilitates passive airflow draft while protecting against humid summer solar angles.",
            u_value="U ≈ 3.2 W/m²K",
            r_value="R ≈ 0.31 m²K/W",
            cost="Med"
        )
        reflective_finish = _create_material(
            name="Breathable White Anti-Fungal Silicate Coating (SRI > 78)",
            reason="Reflects diffuse tropical radiation and allows wall cavity moisture to escape without mold formation.",
            u_value="SRI > 78",
            r_value="N/A",
            cost="Low"
        )

        roof_mat = _create_material(
            name="Reflective Ventilated Cool Roof (SRI > 82) + Radiant Barrier Foil",
            reason="High-reflectance white roof with underside ventilated attic and radiant barrier to stop heat transfer into living zones.",
            u_value="U ≈ 0.35 W/m²K",
            r_value="R ≈ 2.86 m²K/W",
            cost="Low"
        )
        interior_mat = _create_material(
            name="Low-Mass Breathable Drywall / Natural Bamboo-Wood Slat Finishes (Avoid Heavy Thermal Mass)",
            reason="Heavy thermal mass must be strictly avoided in hot-humid climates because it traps daytime heat and re-radiates it uncomfortably during warm nights.",
            u_value="U ≈ 1.8 W/m²K",
            r_value="Low Heat Capacity (< 80 kJ/m²K)",
            cost="Low"
        )

        # Windward side for hot-humid monsoon winds (typically South and West in India/Tropics)
        windward_facades = ["South", "West"] if is_northern else ["North", "West"]

        walls = {}
        for cardinal in ["North", "South", "East", "West"]:
            is_windward = cardinal in windward_facades
            glazing_choice = windward_large_openings if is_windward else sheltered_openings
            desc_tag = "Windward Side - Large Shaded Openings" if is_windward else "Leeward Side - Ventilated Envelope"

            walls[cardinal] = {
                "orientation": cardinal,
                "description": f"{cardinal} Facade ({desc_tag})",
                "wall": lightweight_wall,
                "glazing": glazing_choice,
                "finish": reflective_finish,
                "materials": [lightweight_wall, glazing_choice, reflective_finish]
            }

    # -------------------------------------------------------------------------
    # RULE SET 4: WARM / MIXED CLIMATE
    # -------------------------------------------------------------------------
    else:
        # Balanced insulation, overhangs on sun-facing side
        balanced_wall = _create_material(
            name="Balanced Cavity Wall (50mm Rockwool/EPS + 200mm AAC / Fly-Ash Brick)",
            reason="Balanced thermal resistance and moderate thermal capacitance suitable for both warm summers and mild winters.",
            u_value="U ≈ 0.42 W/m²K",
            r_value="R ≈ 2.38 m²K/W",
            cost="Med"
        )
        sun_wall_overhang = _create_material(
            name="Double-Glazed Low-E Windows with Architectural Overhangs (Chajjas, WWR 20–25%)",
            reason=f"Generous overhang projection on sun-facing {sun_facing_wall} wall engineered to block high summer sun while allowing low winter warmth.",
            u_value="U ≈ 2.2 W/m²K",
            r_value="R ≈ 0.45 m²K/W",
            cost="Med"
        )
        standard_window = _create_material(
            name="Double-Glazed Low-E Windows with Moderate Shading (WWR 15–20%)",
            reason="Balanced fenestration optimizing glare-free daylight and thermal resistance.",
            u_value="U ≈ 2.4 W/m²K",
            r_value="R ≈ 0.42 m²K/W",
            cost="Med"
        )
        standard_finish = _create_material(
            name="High-Albedo Reflective Exterior Render (SRI > 70)",
            reason="Light exterior finish buffering seasonal solar heat ingress.",
            u_value="SRI > 70",
            r_value="N/A",
            cost="Low"
        )

        roof_mat = _create_material(
            name="High-SRI Cool Roof Coating + 50mm Overdeck Rigid Insulation",
            reason="Solar reflective treatment (SRI > 78) over moderate insulation, moderating peak indoor ceiling temperatures.",
            u_value="U ≈ 0.38 W/m²K",
            r_value="R ≈ 2.63 m²K/W",
            cost="Med"
        )
        interior_mat = _create_material(
            name="Moderate Mass Lime Plastered Masonry & Ceramic Flooring",
            reason="Stabilizes daily indoor temperature swings across seasonal transitions.",
            u_value="U ≈ 2.0 W/m²K",
            r_value="R ≈ 0.50 m²K/W",
            cost="Low"
        )

        walls = {}
        for cardinal in ["North", "South", "East", "West"]:
            is_sun = (cardinal == sun_facing_wall)
            glazing_choice = sun_wall_overhang if is_sun else standard_window
            desc_tag = f"Sun-Facing Side ({cardinal}) - Fixed Overhangs" if is_sun else f"Diffuse Side ({cardinal}) - Balanced Insulation"

            walls[cardinal] = {
                "orientation": cardinal,
                "description": desc_tag,
                "wall": balanced_wall,
                "glazing": glazing_choice,
                "finish": standard_finish,
                "materials": [balanced_wall, glazing_choice, standard_finish]
            }

    # Consolidated flat list of all unique materials
    all_materials = []
    seen_names = set()
    for w in walls.values():
        for m in w["materials"]:
            if m["name"] not in seen_names:
                all_materials.append(m)
                seen_names.add(m["name"])
    if roof_mat["name"] not in seen_names:
        all_materials.append(roof_mat)
        seen_names.add(roof_mat["name"])
    if interior_mat["name"] not in seen_names:
        all_materials.append(interior_mat)
        seen_names.add(interior_mat["name"])

    return {
        "zone": zone,
        "category": category,
        "season": season,
        "lat": lat,
        "hemisphere": hemisphere,
        "comfort_need": comfort_need,
        "sun_facing_wall": sun_facing_wall,
        "polar_windward_wall": polar_windward_wall,
        "walls": walls,
        "North": walls["North"],
        "South": walls["South"],
        "East": walls["East"],
        "West": walls["West"],
        "roof": roof_mat,
        "Roof": roof_mat,
        "interior": interior_mat,
        "Interior": interior_mat,
        "all_materials": all_materials
    }
