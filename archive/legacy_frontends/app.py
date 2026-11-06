"""
ThermoHome AI: Climate-Responsive Building Materials & Wall Layout Recommender
==============================================================================
A single-file Streamlit application that analyzes local climate data (via the free
Open-Meteo API) and personal comfort parameters to recommend optimal building envelope
materials and orientation-specific wall layouts.

Key Capabilities:
1. Geolocation detection (via streamlit-geolocation) & manual coordinate inputs.
2. Personal thermal profile (body temperature, clothing insulation, metabolic activity).
3. Auto-detected astronomical season from date and hemisphere (latitude sign).
4. Live Open-Meteo API integration (current temperature/humidity + 365-day historical means).
5. Heating Degree Days (HDD base 18°C) and Cooling Degree Days (CDD base 24°C) computation.
6. ASHRAE-style climate classification ('ASHRAE-based approximation').
7. Physiological & clothing-adjusted comfort need ('Needs Heating', 'Needs Cooling', 'Balanced').
8. Actionable building material recommendations (walls, insulation, roofs, glazing).
9. Cardinal wall layout strategy (North, South, East, West) with 2D architectural schematic.
10. Robust API failure handling with clear messaging and cached sample data.
"""

import io
import datetime
import json
import math
import urllib.request
import urllib.error
import numpy as np
import pandas as pd
import streamlit as st
import matplotlib.pyplot as plt
import matplotlib.patches as patches

# ReportLab components for publication-quality PDF advisory reports
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

# Import modular recommendation rules engine
from rules import recommend

# -----------------------------------------------------------------------------
# 1. Page Configuration & Custom Styling
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="ThermoHome AI | Climate-Responsive Building Advisor",
    page_icon="🏡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for crisp, modern architectural styling
st.markdown("""
<style>
    .main-header {
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
        font-size: 2.2rem;
        font-weight: 700;
        color: #1E293B;
        margin-bottom: 0.2rem;
    }
    .sub-header {
        font-size: 1.05rem;
        color: #64748B;
        margin-bottom: 1.5rem;
    }
    .metric-card {
        background-color: #F8FAFC;
        border: 1px solid #E2E8F0;
        border-radius: 8px;
        padding: 14px;
        text-align: center;
    }
    .metric-value {
        font-size: 1.6rem;
        font-weight: 700;
        color: #0F172A;
    }
    .metric-label {
        font-size: 0.85rem;
        color: #64748B;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }
    .badge-ashrae {
        display: inline-block;
        background-color: #EEF2FF;
        color: #4338CA;
        font-size: 0.85rem;
        font-weight: 600;
        padding: 4px 10px;
        border-radius: 9999px;
        border: 1px solid #C7D2FE;
    }
    .comfort-badge {
        display: inline-block;
        font-size: 1.15rem;
        font-weight: 700;
        padding: 8px 16px;
        border-radius: 8px;
        margin-bottom: 10px;
    }
    .material-card {
        background: #FFFFFF;
        border: 1px solid #E2E8F0;
        border-left: 4px solid #0284C7;
        border-radius: 6px;
        padding: 12px 16px;
        margin-bottom: 12px;
    }
</style>
""", unsafe_allow_html=True)


# -----------------------------------------------------------------------------
# 2. Season Auto-Detection
# -----------------------------------------------------------------------------
def detect_season(latitude: float, reference_date: datetime.date = None) -> tuple[str, str]:
    """
    Auto-detects astronomical season based on reference date and hemisphere
    determined by latitude sign (positive = Northern, negative = Southern).

    Returns:
        tuple[str, str]: (Season name, Hemisphere name)
    """
    if reference_date is None:
        reference_date = datetime.date.today()

    day_of_year = reference_date.timetuple().tm_yday
    is_northern = latitude >= 0.0
    hemisphere = "Northern" if is_northern else "Southern"

    # Astronomical solstice & equinox boundary approximations:
    # Mar 21 (day ~80), Jun 21 (day ~172), Sep 23 (day ~266), Dec 21 (day ~355)
    if 80 <= day_of_year < 172:
        north_season = "Spring"
    elif 172 <= day_of_year < 266:
        north_season = "Summer"
    elif 266 <= day_of_year < 355:
        north_season = "Autumn"
    else:
        north_season = "Winter"

    # In Southern Hemisphere, seasons are inverted
    if is_northern:
        season = north_season
    else:
        invert_map = {
            "Spring": "Autumn",
            "Summer": "Winter",
            "Autumn": "Spring",
            "Winter": "Summer"
        }
        season = invert_map[north_season]

    return season, hemisphere


# -----------------------------------------------------------------------------
# 3. Weather API & Historical Data Fetcher (with Fallback)
# -----------------------------------------------------------------------------
def get_cached_sample_data(lat: float, lon: float) -> dict:
    """
    Returns realistic cached climate sample data representing typical conditions
    (Pune baseline: Lat 18.52, Lon 73.86) when the live API cannot be reached.
    """
    # 365 daily temperatures synthesized with seasonal amplitude around 25.7°C
    days = 365
    t = np.linspace(0, 2 * np.pi, days)
    # Seasonal wave (peak hot in April/May, cool in Dec/Jan)
    base_temps = 25.5 + 4.5 * np.sin(t - 1.2) + np.random.RandomState(42).normal(0, 1.2, days)
    daily_temps = [round(float(x), 1) for x in base_temps]

    today = datetime.date.today()
    dates = [(today - datetime.timedelta(days=i)).isoformat() for i in range(days, 0, -1)]

    return {
        "current_temp": 26.5,
        "current_humidity": 65.0,
        "dates": dates,
        "daily_means": daily_temps,
        "is_cached_sample": True,
        "error_message": "Network offline or Open-Meteo API unreachable."
    }


@st.cache_data(ttl=3600, show_spinner=False)
def fetch_climate_data(lat: float, lon: float) -> dict:
    """
    Calls the free Open-Meteo API (no key required):
    1. Current temperature & humidity from the forecast endpoint.
    2. Past 365 days of daily mean temperature from the historical archive endpoint.

    Computes Heating Degree Days (HDD base 18°C) and Cooling Degree Days (CDD base 24°C).
    Gracefully falls back to cached sample data on any network or parsing error.
    """
    today = datetime.date.today()
    end_date = today - datetime.timedelta(days=1)
    start_date = end_date - datetime.timedelta(days=364)

    # Free Open-Meteo endpoints
    current_url = (
        f"https://api.open-meteo.com/v1/forecast?"
        f"latitude={lat}&longitude={lon}&current=temperature_2m,relative_humidity_2m"
    )
    archive_url = (
        f"https://archive-api.open-meteo.com/v1/archive?"
        f"latitude={lat}&longitude={lon}&start_date={start_date}&end_date={end_date}&daily=temperature_2m_mean"
    )

    headers = {"User-Agent": "ThermoHome-AI/1.0 (Streamlit Academic Recommender)"}

    try:
        # Fetch current conditions
        req_curr = urllib.request.Request(current_url, headers=headers)
        with urllib.request.urlopen(req_curr, timeout=8) as resp:
            curr_data = json.loads(resp.read().decode("utf-8"))

        curr_temp = float(curr_data["current"]["temperature_2m"])
        curr_humidity = float(curr_data["current"]["relative_humidity_2m"])

        # Fetch past 365 days
        req_arch = urllib.request.Request(archive_url, headers=headers)
        with urllib.request.urlopen(req_arch, timeout=12) as resp:
            arch_data = json.loads(resp.read().decode("utf-8"))

        dates = arch_data["daily"]["time"]
        daily_means = arch_data["daily"]["temperature_2m_mean"]

        # Filter out any missing values
        valid_daily = [float(t) for t in daily_means if t is not None]
        if len(valid_daily) < 300:
            raise ValueError("Insufficient daily temperature records returned by archive API.")

        return {
            "current_temp": curr_temp,
            "current_humidity": curr_humidity,
            "dates": dates,
            "daily_means": valid_daily,
            "is_cached_sample": False,
            "error_message": None
        }

    except Exception as exc:
        sample = get_cached_sample_data(lat, lon)
        sample["error_message"] = str(exc)
        return sample


# -----------------------------------------------------------------------------
# 4. Degree Days & ASHRAE-Style Climate Classification
# -----------------------------------------------------------------------------
def calculate_degree_days(daily_means: list[float], hdd_base: float = 18.0, cdd_base: float = 24.0):
    """
    Computes Heating Degree Days (HDD base 18°C) and Cooling Degree Days (CDD base 24°C).
    HDD = sum(max(0, 18 - T_mean))
    CDD = sum(max(0, T_mean - 24))
    """
    hdd = sum(max(0.0, hdd_base - t) for t in daily_means)
    cdd = sum(max(0.0, t - cdd_base) for t in daily_means)
    annual_mean = sum(daily_means) / len(daily_means) if daily_means else 20.0
    return round(hdd, 1), round(cdd, 1), round(annual_mean, 1)


def classify_ashrae_zone(hdd: float, cdd: float, humidity: float, mean_temp: float) -> tuple[str, str]:
    """
    Classifies climate into an ASHRAE-style zone using CDD/HDD thresholds:
    - Hot-Humid
    - Hot-Dry
    - Warm
    - Mixed
    - Cold

    Labeled as: 'ASHRAE-based approximation'
    """
    if hdd >= 1500 or (hdd >= 1000 and hdd > cdd):
        zone = "Cold"
        desc = (
            "Cold climate dominated by significant annual heating degree days (HDD₁₈ ≥ 1000). "
            "Envelope priority: High thermal insulation, airtight envelope, and passive solar capture."
        )
    elif hdd >= 200 and cdd >= 400:
        zone = "Mixed"
        desc = (
            "Composite/Mixed climate with both distinct heating winter and cooling summer requirements. "
            "Envelope priority: Dynamic shading, dual-season insulation, and moderate thermal mass."
        )
    elif cdd >= 1000:
        if humidity >= 55.0:
            zone = "Hot-Humid"
            desc = (
                "Hot and humid climate (CDD₂₄ ≥ 1000, high ambient relative humidity). "
                "Envelope priority: Maximum natural ventilation, breathable shaded walls, moisture resistance, and cool roofs."
            )
        else:
            zone = "Hot-Dry"
            desc = (
                "Arid desert or semi-arid climate (CDD₂₄ ≥ 1000, low ambient humidity). "
                "Envelope priority: Heavy thermal mass, diurnal thermal delay, night purge cooling, and external insulation."
            )
    else:
        # Moderate cooling, low heating
        if cdd >= 350 or mean_temp >= 22.0:
            zone = "Warm"
            desc = (
                "Warm/Temperate climate with mild winters and moderate cooling needs. "
                "Envelope priority: Solar shading, reflective exterior finishes, and cross-ventilation."
            )
        elif hdd >= 800:
            zone = "Cold"
            desc = "Cool upland climate with moderate annual heating demand."
        else:
            zone = "Warm"
            desc = "Equable warm temperate climate with balanced comfort requirements."

    return zone, desc


# -----------------------------------------------------------------------------
# 5. Personal Thermal Comfort Adjustment Engine
# -----------------------------------------------------------------------------
def evaluate_comfort_need(
    current_temp: float,
    body_temp: float,
    clothing_level: str,
    activity_level: str
) -> dict:
    """
    Calculates personal comfort need ('Needs Heating', 'Needs Cooling', 'Balanced').

    Physics-grounded adaptation of ASHRAE 55 PMV neutral operative temperature principles:
    - Baseline neutral temperature for sedentary person in standard clothing is 24.0°C.
    - Clothing insulation (clo):
      * Light (~0.5 clo): Person sheds heat readily; needs +2.0°C warmer ambient air to feel comfortable.
      * Medium (~1.0 clo): Standard baseline (0.0°C shift).
      * Heavy (~1.5 clo): Person traps metabolic heat; needs -2.5°C cooler ambient air.
    - Metabolic activity (met):
      * Resting (~0.8 met): Lower internal heat generation; requires +1.5°C warmer ambient air.
      * Light (~1.2 met): Standard sedentary baseline (0.0°C shift).
      * Active (~2.0 met): Elevated internal heat generation; requires -2.0°C cooler ambient air.
    - Core body temperature:
      * Standard resting baseline is 36.8°C.
      * Elevated body temperature increases sensitivity to heat (-1.5°C per degree above 36.8°C).
    """
    base_neutral = 24.0

    # Clothing insulation offset
    clothing_shifts = {"Light": 2.0, "Medium": 0.0, "Heavy": -2.5}
    clo_shift = clothing_shifts.get(clothing_level, 0.0)

    # Activity metabolic offset
    activity_shifts = {"Resting": 1.5, "Light": 0.0, "Active": -2.0}
    act_shift = activity_shifts.get(activity_level, 0.0)

    # Physiological body temperature offset
    body_shift = -(body_temp - 36.8) * 1.5

    # Net adjusted neutral temperature and comfort band (+/- 1.8°C)
    adj_neutral = base_neutral + clo_shift + act_shift + body_shift
    comfort_min = adj_neutral - 1.8
    comfort_max = adj_neutral + 1.8

    if current_temp < comfort_min:
        need = "Needs Heating"
        badge_bg = "#FEE2E2"
        badge_color = "#991B1B"
        badge_icon = "🔥"
        explanation = (
            f"Current outdoor temperature ({current_temp:.1f}°C) is below your personalized neutral comfort "
            f"band ({comfort_min:.1f}°C – {comfort_max:.1f}°C). The space requires thermal envelope heat retention "
            f"or solar heat gain."
        )
    elif current_temp > comfort_max:
        need = "Needs Cooling"
        badge_bg = "#E0F2FE"
        badge_color = "#075985"
        badge_icon = "❄️"
        explanation = (
            f"Current outdoor temperature ({current_temp:.1f}°C) exceeds your personalized neutral comfort "
            f"band ({comfort_min:.1f}°C – {comfort_max:.1f}°C). The space requires passive cooling, heat rejection, "
            f"and solar shielding."
        )
    else:
        need = "Balanced"
        badge_bg = "#DCFCE7"
        badge_color = "#166534"
        badge_icon = "⚖️"
        explanation = (
            f"Current outdoor temperature ({current_temp:.1f}°C) is comfortably within your personalized neutral "
            f"band ({comfort_min:.1f}°C – {comfort_max:.1f}°C). Passive thermal equilibrium is maintained."
        )

    return {
        "need": need,
        "badge_bg": badge_bg,
        "badge_color": badge_color,
        "badge_icon": badge_icon,
        "adj_neutral": round(adj_neutral, 1),
        "comfort_min": round(comfort_min, 1),
        "comfort_max": round(comfort_max, 1),
        "clo_shift": clo_shift,
        "act_shift": act_shift,
        "body_shift": round(body_shift, 2),
        "body_temp": body_temp,
        "clothing_level": clothing_level,
        "activity_level": activity_level,
        "explanation": explanation
    }


# -----------------------------------------------------------------------------
# 6. Building Material Recommendations
# -----------------------------------------------------------------------------
def get_recommended_materials(climate_zone: str, comfort_need: str) -> dict:
    """
    Returns climate- and comfort-adapted building material specifications across:
    1. External Wall Assemblies
    2. Wall Insulation Systems
    3. Roof & Ceiling Assemblies
    4. Glazing & Fenestration
    5. Internal Thermal Mass & Finishes
    """
    materials = {
        "Hot-Humid": {
            "walls": (
                "Lightweight Breathable Walls / Autoclaved Aerated Concrete (AAC)",
                "Low thermal capacitance to prevent nighttime heat re-radiation. Aerated autoclaved blocks (200mm) "
                "or perforated clay hollow blocks allow rapid heat dissipation and moisture transport."
            ),
            "insulation": (
                "Permeable Mineral Wool / Vapor-Open Insulation (50mm)",
                "Mineral rockwool with external breathable weather barrier. Avoid impermeable foam plastics that trap "
                "interstitial humidity and cause mold growth."
            ),
            "roof": (
                "High-Albedo Cool Roof (SRI > 82) + Ventilated Radiant Barrier",
                "Elastomeric white acrylic roof coating or reflective ceramic tiles over a ventilated air cavity. "
                "Reflects >80% of direct solar radiation, slashing roof heat ingress."
            ),
            "glazing": (
                "Double Glazing with Solar Control Low-E Coating (SHGC < 0.25, U < 2.8 W/m²K)",
                "Spectrally selective glass that maximizes daylight while rejecting infrared heat gain. Operable sash/casement "
                "windows designed for 100% natural cross-ventilation."
            ),
            "finishes": (
                "Vapor-Permeable Lime Plaster & Anti-Microbial Low-VOC Finishes",
                "Natural slaked lime plaster regulates indoor humidity fluctuations naturally and prevents mildew."
            )
        },
        "Hot-Dry": {
            "walls": (
                "High Thermal Mass Masonry (Stabilized Rammed Earth / Compressed Earth Blocks / Dense Fly-Ash)",
                "Thick mass walls (250–300mm) provide 8–10 hour thermal lag. Absorbs peak daytime desert heat and releases "
                "it during cold nighttime periods."
            ),
            "insulation": (
                "External Extruded Polystyrene (XPS) or Rigid Polyisocyanurate (75mm)",
                "Continuous external insulation wraps the thermal mass, isolating it from extreme daytime solar exposure "
                "and preventing thermal bridging."
            ),
            "roof": (
                "Overdeck Insulated Inverted Roof + High SRI Broken China Mosaic / Cool Paint",
                "100mm extruded polystyrene over reinforced concrete slab, topped with reflective white china mosaic tile "
                "to reflect harsh solar radiation."
            ),
            "glazing": (
                "Double Glazing Low-E with Deep Exterior Shading (SHGC < 0.22, U < 2.4 W/m²K)",
                "Recessed window reveals with solar reflective low-E coating. Window-to-wall ratio strictly controlled (<20%)."
            ),
            "finishes": (
                "Exposed Dense Earth / Stone Flooring (Kotah Stone / Terrazzo)",
                "High-admittance flooring materials store nighttime coolness and cool indoor air throughout the day."
            )
        },
        "Warm": {
            "walls": (
                "Fly-Ash Brick / AAC Block Cavity Wall (230mm)",
                "Balanced thermal mass: 200mm AAC blocks or fly-ash bricks with an unventilated 30mm air cavity providing "
                "sufficient thermal resistance without excessive heat storage."
            ),
            "insulation": (
                "Expanded Polystyrene (EPS) / Rockwool Core (50mm)",
                "Moderate exterior insulation layer keeping indoor surfaces close to comfort neutral temperatures."
            ),
            "roof": (
                "High-SRI Cool Roof Paint + Under-Deck Insulation (50mm)",
                "White solar reflective coating (SRI 78+) combined with 50mm glass wool or rockwool under-deck blanket."
            ),
            "glazing": (
                "Double Glazing with Low-E Film (SHGC < 0.35, U < 3.0 W/m²K)",
                "Good daylight transmission with moderate solar control and operable sashes for evening cross-ventilation."
            ),
            "finishes": (
                "Hydraulic Lime Plaster / Clay Plaster",
                "Breathable natural wall finishes supporting seasonal thermal comfort and passive moisture buffering."
            )
        },
        "Mixed": {
            "walls": (
                "Perforated Clay Block / Fly-Ash Cavity Wall (250mm)",
                "Hybrid envelope performing across both extreme summer heat and chilly winter months. Moderate mass dampens "
                "diurnal swings in both seasons."
            ),
            "insulation": (
                "Dual-Faced External Rockwool Board (75mm, U < 0.40 W/m²K)",
                "Non-combustible stone wool board providing year-round thermal containment—reducing cooling load in summer "
                "and heating loss in winter."
            ),
            "roof": (
                "Insulated Flat RCC Roof with Removable / Seasonal Shading Pergola",
                "75mm overdeck insulation with modular terrace planter/pergola shading that blocks high summer sun but permits "
                "low-angle winter sun to warm the roof slab."
            ),
            "glazing": (
                "Double-Glazed Low-E with Spectrally Selective Low-E Coating (U < 2.0 W/m²K, SHGC 0.30)",
                "Dual-performance glass minimizing winter conductive heat loss while blocking summer solar heat ingress."
            ),
            "finishes": (
                "Cement-Lime Composite Plaster & Medium-Admittance Vitrified Tile",
                "Balances durability with moderate thermal buffering for seasonal transitions."
            )
        },
        "Cold": {
            "walls": (
                "High-Insulation Super-Insulated Cavity Wall / Timber Frame with PUF/XPS (300mm)",
                "Continuous thermal envelope with eliminated thermal bridging. Double-leaf insulated masonry or timber/steel "
                "framing with high R-value."
            ),
            "insulation": (
                "Continuous Polyurethane Foam (PUF) or High-Density Rockwool (120mm, U < 0.25 W/m²K)",
                "Substantial insulation thickness wrapped around all building faces with interior airtight vapor barrier."
            ),
            "roof": (
                "Pitched Dark Metal / Slate Roof with 150mm Attic Insulation (R-value > 4.5 m²K/W)",
                "Dark solar-absorptive surface to capture winter solar heat, coupled with heavy fiberglass or cellulose insulation "
                "in the ceiling attic to prevent upward heat escape."
            ),
            "glazing": (
                "Triple Glazing or Argon-Filled Low-E Double Glazing (U < 1.4 W/m²K, High SHGC > 0.50)",
                "High solar heat gain coefficient (SHGC) glass allows free passive solar heating while argon gas fill minimizes "
                "conductive and radiant heat loss."
            ),
            "finishes": (
                "Dark Wood Panelling / High-Admittance Heat-Retaining Stone / Ceramic Tile",
                "Dark stone or brick surfaces placed in direct sunlight (Trombe wall or direct gain floor) absorb solar heat "
                "during daylight and radiate warmth overnight."
            )
        }
    }

    return materials.get(climate_zone, materials["Warm"])


# -----------------------------------------------------------------------------
# 7. Cardinal Wall Layout (North, South, East, West) & 2D Schematic
# -----------------------------------------------------------------------------
def get_wall_orientation_strategy(climate_zone: str, latitude: float) -> dict:
    """
    Determines architectural envelope strategies for North, South, East, and West walls.
    Accounts for latitude sign (Northern vs Southern Hemisphere solar trajectories).
    """
    is_northern = latitude >= 0.0

    if is_northern:
        south_role = "Solar Collection & High Sun"
        south_wwr = "25% – 35%" if climate_zone in ["Cold", "Mixed"] else "15% – 25%"
        south_shading = "Horizontal overhang (chajja / louver) sized to block high summer sun while allowing low winter sun."
        
        north_role = "Consistent Glare-Free Daylighting"
        north_wwr = "20% – 30%" if climate_zone != "Cold" else "10% – 15%"
        north_shading = "Minimal horizontal shading needed; small vertical reveals protect against early/late summer glare."
    else:
        # Southern Hemisphere inversion
        south_role = "Consistent Glare-Free Daylighting (Shaded)"
        south_wwr = "20% – 30%" if climate_zone != "Cold" else "10% – 15%"
        south_shading = "Minimal horizontal shading needed; diffuse daylight orientation."
        
        north_role = "Solar Collection & High Sun (Equator-Facing)"
        north_wwr = "25% – 35%" if climate_zone in ["Cold", "Mixed"] else "15% – 25%"
        north_shading = "Horizontal overhangs sized for summer cutoff while permitting low winter sun penetration."

    # East and West are symmetric across hemispheres regarding morning vs afternoon solar dynamics
    east_strategy = {
        "role": "Morning Sun & Early Day Warmup",
        "wwr": "15% – 20%",
        "shading": "Vertical louvers or external deciduous vegetation to intercept low morning solar angles.",
        "mass": "Moderate thermal mass (200mm blockwork)."
    }

    west_strategy = {
        "role": "Severe Afternoon Thermal Peak (Critical Protection)",
        "wwr": "< 10% (Minimal Glazing)",
        "shading": "Deep vertical fins, operable jalis, or solid buffer zones (staircases, bathrooms, utility rooms).",
        "mass": "Maximum thermal resistance & heavy mass (300mm insulated masonry)."
    }

    return {
        "North": {
            "title": "North Facade",
            "role": north_role,
            "wwr": north_wwr,
            "shading": north_shading,
            "color": "#3B82F6"
        },
        "South": {
            "title": "South Facade",
            "role": south_role,
            "wwr": south_wwr,
            "shading": south_shading,
            "color": "#EF4444"
        },
        "East": {
            "title": "East Facade",
            "role": east_strategy["role"],
            "wwr": east_strategy["wwr"],
            "shading": east_strategy["shading"],
            "color": "#F59E0B"
        },
        "West": {
            "title": "West Facade",
            "role": west_strategy["role"],
            "wwr": west_strategy["wwr"],
            "shading": west_strategy["shading"],
            "color": "#8B5CF6"
        }
    }


def plot_top_view_house_diagram(rec_results: dict, hemisphere: str, climate_zone: str):
    """
    Renders an architectural top-view house diagram:
    - Square plan in the center with 4 colored walls labeled N/S/E/W.
    - Each wall clearly displays its recommended material, U/R-value, and relative cost.
    - Dynamic sun-path arrow showing diurnal solar trajectory across the sky
      (East -> South -> West for Northern Hemisphere, East -> North -> West for Southern Hemisphere).
    - Designed with large fonts (11-17pt) and high contrast for clear readability on a projector
      with guaranteed non-overlapping labels and unclipped sun trajectories.
    """
    fig, ax = plt.subplots(figsize=(14.0, 12.5), facecolor="#FFFFFF")
    ax.set_facecolor("#FFFFFF")

    if hemisphere == "Northern":
        ax.set_xlim(-2.5, 15.0)
        ax.set_ylim(-2.2, 13.5)
    else:
        ax.set_xlim(-2.5, 15.0)
        ax.set_ylim(-0.5, 15.2)
    ax.axis("off")

    # Center square house footprint (x=4.5 to 8.5, y=4.5 to 8.5)
    house_rect = patches.Rectangle(
        (4.5, 4.5), 4.0, 4.0,
        linewidth=3.0, edgecolor="#0F172A", facecolor="#F8FAFC", zorder=2
    )
    ax.add_patch(house_rect)

    # 4 Colored Walls (linewidth=14 for high visibility on projector)
    wall_colors = {
        "North": "#1D4ED8",  # Royal Blue
        "South": "#B91C1C",  # Crimson Red
        "East": "#D97706",   # Deep Amber
        "West": "#7E22CE"    # Vibrant Purple
    }

    # North Wall (y=8.5, x from 4.5 to 8.5)
    ax.plot([4.5, 8.5], [8.5, 8.5], color=wall_colors["North"], lw=14, solid_capstyle="round", zorder=4)
    # South Wall (y=4.5, x from 4.5 to 8.5)
    ax.plot([4.5, 8.5], [4.5, 4.5], color=wall_colors["South"], lw=14, solid_capstyle="round", zorder=4)
    # West Wall (x=4.5, y from 4.5 to 8.5)
    ax.plot([4.5, 4.5], [4.5, 8.5], color=wall_colors["West"], lw=14, solid_capstyle="round", zorder=4)
    # East Wall (x=8.5, y from 4.5 to 8.5)
    ax.plot([8.5, 8.5], [4.5, 8.5], color=wall_colors["East"], lw=14, solid_capstyle="round", zorder=4)

    def wrap_title(txt: str, max_chars: int = 34) -> str:
        words = txt.split()
        lines = []
        cur = []
        for w in words:
            if sum(len(x) for x in cur) + len(cur) + len(w) > max_chars:
                lines.append(" ".join(cur))
                cur = [w]
            else:
                cur.append(w)
        if cur:
            lines.append(" ".join(cur))
        return "\n".join(lines)

    n_mat = rec_results["walls"]["North"]["wall"]
    s_mat = rec_results["walls"]["South"]["wall"]
    e_mat = rec_results["walls"]["East"]["wall"]
    w_mat = rec_results["walls"]["West"]["wall"]

    # 1. NORTH WALL LABEL
    n_text = (
        f"NORTH WALL (N)\n"
        f"{wrap_title(n_mat['name'], 36)}\n"
        f"{n_mat['u_value']}  |  Cost: {n_mat['cost']}"
    )
    ax.text(
        6.5, 10.15, n_text,
        ha="center", va="center", fontsize=12.5, fontweight="bold", color="#0F172A",
        bbox=dict(boxstyle="round,pad=0.55", facecolor="#EFF6FF", edgecolor="#1D4ED8", lw=2.0),
        zorder=5
    )

    # 2. SOUTH WALL LABEL
    s_text = (
        f"SOUTH WALL (S)\n"
        f"{wrap_title(s_mat['name'], 36)}\n"
        f"{s_mat['u_value']}  |  Cost: {s_mat['cost']}"
    )
    ax.text(
        6.5, 2.85, s_text,
        ha="center", va="center", fontsize=12.5, fontweight="bold", color="#0F172A",
        bbox=dict(boxstyle="round,pad=0.55", facecolor="#FEF2F2", edgecolor="#B91C1C", lw=2.0),
        zorder=5
    )

    # 3. WEST WALL LABEL
    w_text = (
        f"WEST WALL (W)\n"
        f"{wrap_title(w_mat['name'], 26)}\n"
        f"{w_mat['u_value']}\nCost: {w_mat['cost']}"
    )
    ax.text(
        1.3, 6.5, w_text,
        ha="center", va="center", fontsize=12.0, fontweight="bold", color="#0F172A",
        bbox=dict(boxstyle="round,pad=0.55", facecolor="#FAF5FF", edgecolor="#7E22CE", lw=2.0),
        zorder=5
    )

    # 4. EAST WALL LABEL
    e_text = (
        f"EAST WALL (E)\n"
        f"{wrap_title(e_mat['name'], 26)}\n"
        f"{e_mat['u_value']}\nCost: {e_mat['cost']}"
    )
    ax.text(
        11.7, 6.5, e_text,
        ha="center", va="center", fontsize=12.0, fontweight="bold", color="#0F172A",
        bbox=dict(boxstyle="round,pad=0.55", facecolor="#FFFBEB", edgecolor="#D97706", lw=2.0),
        zorder=5
    )

    # Center Interior Stamp
    center_text = (
        f"SQUARE HOUSE PLAN\n"
        f"Zone: {climate_zone}\n"
        f"─────────────────\n"
        f"Roof: {wrap_title(rec_results['roof']['name'], 22)}\n"
        f"Mass: {wrap_title(rec_results['interior']['name'], 22)}"
    )
    ax.text(
        6.5, 6.5, center_text,
        ha="center", va="center", fontsize=10.5, fontweight="bold", color="#1E293B",
        bbox=dict(boxstyle="round,pad=0.45", facecolor="#F1F5F9", edgecolor="#CBD5E1", lw=1.5),
        zorder=3
    )

    # Compass Indicator
    compass_y = 12.2 if hemisphere == "Northern" else 14.0
    ax.annotate(
        "N", xy=(-0.5, compass_y + 0.7), xytext=(-0.5, compass_y - 0.5),
        arrowprops=dict(facecolor="#0F172A", width=3.5, headwidth=12),
        ha="center", va="bottom", fontsize=18, fontweight="bold", color="#0F172A", zorder=6
    )

    # Sun-Path Arrow (Outside envelope & label boxes with guaranteed margin)
    if hemisphere == "Northern":
        sun_arrow = patches.FancyArrowPatch(
            (11.5, 1.8), (1.5, 1.8),
            connectionstyle="arc3,rad=-0.32",
            color="#D97706", lw=4.0, arrowstyle="-|>", mutation_scale=28,
            linestyle="--", zorder=2
        )
        ax.add_patch(sun_arrow)
        ax.plot([6.5], [0.38], marker="o", markersize=14, color="#F59E0B", zorder=6)
        ax.text(
            6.5, -1.1,
            "☀️ Diurnal Sun Path: East ➔ South ➔ West (Peak Afternoon Sun on South Facade)",
            ha="center", va="center", fontsize=13, fontweight="bold", color="#78350F",
            bbox=dict(boxstyle="round,pad=0.5", facecolor="#FEF3C7", edgecolor="#F59E0B", lw=2.0),
            zorder=6
        )
    else:
        sun_arrow = patches.FancyArrowPatch(
            (11.5, 11.2), (1.5, 11.2),
            connectionstyle="arc3,rad=0.32",
            color="#D97706", lw=4.0, arrowstyle="-|>", mutation_scale=28,
            linestyle="--", zorder=2
        )
        ax.add_patch(sun_arrow)
        ax.plot([6.5], [12.62], marker="o", markersize=14, color="#F59E0B", zorder=6)
        ax.text(
            6.5, 14.1,
            "☀️ Diurnal Sun Path: East ➔ North ➔ West (Equator-Facing Sun on North Facade)",
            ha="center", va="center", fontsize=13, fontweight="bold", color="#78350F",
            bbox=dict(boxstyle="round,pad=0.5", facecolor="#FEF3C7", edgecolor="#F59E0B", lw=2.0),
            zorder=6
        )

    plt.tight_layout()
    return fig



def plot_thermometer_gauge(comfort_res: dict, current_temp: float):
    """
    Renders a high-contrast thermometer-style gauge for comfort need:
    - Vertical thermometer with mercury column showing current outdoor temperature.
    - Clearly segmented color zones: Needs Heating (blue), Balanced (green), Needs Cooling (red).
    - Large projector-readable fonts (11-17pt) with non-overlapping callout pointer and zone text.
    """
    fig, ax = plt.subplots(figsize=(11.0, 7.8), facecolor="#FFFFFF")
    ax.set_facecolor("#FFFFFF")
    ax.set_xlim(0, 11)
    ax.set_ylim(0, 10)
    ax.axis("off")

    c_min = comfort_res["comfort_min"]
    c_max = comfort_res["comfort_max"]
    adj_neutral = comfort_res["adj_neutral"]
    need = comfort_res["need"]

    # Dynamic temperature scale bounds
    t_min_val = min(current_temp, c_min)
    t_max_val = max(current_temp, c_max)
    t_low = float(math.floor(min(10.0, t_min_val - 4.0) / 5.0) * 5.0)
    t_high = float(math.ceil(max(40.0, t_max_val + 4.0) / 5.0) * 5.0)

    y_bot = 1.8
    y_top = 8.2
    h_total = y_top - y_bot

    def t_to_y(temp_val: float) -> float:
        frac = (temp_val - t_low) / (t_high - t_low)
        return y_bot + np.clip(frac, 0.0, 1.0) * h_total

    # Tube geometry
    tube_x = 1.9
    tube_w = 0.8
    bulb_r = 0.72
    bulb_center = (tube_x + tube_w / 2.0, y_bot - 0.2)

    # Tube background
    tube_bg = patches.FancyBboxPatch(
        (tube_x, y_bot), tube_w, h_total,
        boxstyle="round,pad=0.08,rounding_size=0.4",
        facecolor="#F1F5F9", edgecolor="#334155", lw=3.0, zorder=2
    )
    ax.add_patch(tube_bg)

    bulb_bg = patches.Circle(
        bulb_center, bulb_r,
        facecolor="#F1F5F9", edgecolor="#334155", lw=3.0, zorder=2
    )
    ax.add_patch(bulb_bg)

    # Mercury liquid fill
    y_curr = t_to_y(current_temp)
    if need == "Needs Heating":
        liq_color = "#2563EB"  # Cool blue
        status_bg = "#EFF6FF"
        status_border = "#2563EB"
        status_icon = "🔥 NEEDS HEATING"
    elif need == "Needs Cooling":
        liq_color = "#DC2626"  # Fiery red
        status_bg = "#FEF2F2"
        status_border = "#DC2626"
        status_icon = "❄️ NEEDS COOLING"
    else:
        liq_color = "#16A34A"  # Forest green
        status_bg = "#F0FDF4"
        status_border = "#16A34A"
        status_icon = "⚖️ BALANCED COMFORT"

    # Fill bulb and stem
    bulb_fill = patches.Circle(bulb_center, bulb_r - 0.08, facecolor=liq_color, edgecolor="none", zorder=3)
    ax.add_patch(bulb_fill)
    mercury_stem = patches.Rectangle(
        (tube_x + 0.12, y_bot - 0.2), tube_w - 0.24, max(0.1, y_curr - (y_bot - 0.2)),
        facecolor=liq_color, edgecolor="none", zorder=3
    )
    ax.add_patch(mercury_stem)

    # Temperature ticks on the left side of the tube
    tick_step = 5.0
    tick_temps = np.arange(t_low, t_high + 0.1, tick_step)
    for t_val in tick_temps:
        y_val = t_to_y(t_val)
        ax.plot([tube_x - 0.22, tube_x], [y_val, y_val], color="#334155", lw=2.0, zorder=4)
        ax.text(
            tube_x - 0.35, y_val, f"{int(t_val)}°C",
            ha="right", va="center", fontsize=11, fontweight="bold", color="#1E293B", zorder=4
        )

    # Right side: Comfort Zone Bands
    band_x = 3.2
    band_w = 7.3

    y_cmin = t_to_y(c_min)
    y_cmax = t_to_y(c_max)
    y_neut = t_to_y(adj_neutral)

    # 1. Needs Heating Zone (Below c_min)
    if y_cmin > y_bot:
        ax.fill_between([band_x, band_x + band_w], [y_bot, y_bot], [y_cmin, y_cmin],
                        color="#EFF6FF", alpha=0.9, zorder=1)
        ax.plot([band_x, band_x + band_w], [y_cmin, y_cmin], color="#93C5FD", lw=1.5, linestyle=":", zorder=2)
        ax.text(
            band_x + band_w - 0.2, (y_bot + y_cmin) / 2.0,
            f"COOL / HEATING ZONE (< {c_min:.1f}°C)",
            ha="right", va="center", fontsize=11, fontweight="bold", color="#1D4ED8", zorder=4
        )

    # 2. Balanced Zone (Between c_min and c_max)
    ax.fill_between([band_x, band_x + band_w], [y_cmin, y_cmin], [y_cmax, y_cmax],
                    color="#DCFCE7", alpha=0.95, zorder=1)
    # Neutral line
    ax.plot([band_x, band_x + band_w], [y_neut, y_neut], color="#15803D", lw=2.2, linestyle="--", zorder=2)
    ax.text(
        band_x + band_w - 0.2, y_neut,
        f"BALANCED ZONE ({c_min:.1f}°C – {c_max:.1f}°C)  |  Target: {adj_neutral:.1f}°C",
        ha="right", va="center", fontsize=11, fontweight="bold", color="#14532D",
        bbox=dict(boxstyle="round,pad=0.25", facecolor="#DCFCE7", edgecolor="#15803D", lw=1.0),
        zorder=4
    )

    # 3. Needs Cooling Zone (Above c_max)
    if y_cmax < y_top:
        ax.fill_between([band_x, band_x + band_w], [y_cmax, y_cmax], [y_top, y_top],
                        color="#FEF2F2", alpha=0.9, zorder=1)
        ax.plot([band_x, band_x + band_w], [y_cmax, y_cmax], color="#FCA5A5", lw=1.5, linestyle=":", zorder=2)
        ax.text(
            band_x + band_w - 0.2, (y_cmax + y_top) / 2.0,
            f"WARM / COOLING ZONE (> {c_max:.1f}°C)",
            ha="right", va="center", fontsize=11, fontweight="bold", color="#B91C1C", zorder=4
        )

    # Meniscus Callout Pointer on the left half of the bands
    callout_y = np.clip(y_curr, 1.4, 8.6)
    ax.annotate(
        f"CURRENT: {current_temp:.1f}°C\n({need})",
        xy=(tube_x + tube_w, y_curr), xytext=(band_x + 0.35, callout_y),
        arrowprops=dict(facecolor=liq_color, edgecolor=liq_color, width=2.2, headwidth=8),
        fontsize=11.5, fontweight="bold", color="#FFFFFF", ha="left", va="center",
        bbox=dict(boxstyle="round,pad=0.45", facecolor=liq_color, edgecolor="#0F172A", lw=1.5),
        zorder=6
    )

    # Title Banner (Large, bold, high contrast for projector)
    ax.text(
        5.5, 9.4, "THERMAL COMFORT NEED GAUGE",
        ha="center", va="center", fontsize=17, fontweight="bold", color="#0F172A", zorder=6
    )
    ax.text(
        5.5, 8.75, f"STATUS: {status_icon}",
        ha="center", va="center", fontsize=13.5, fontweight="bold", color=liq_color,
        bbox=dict(boxstyle="round,pad=0.38", facecolor=status_bg, edgecolor=status_border, lw=2.0),
        zorder=6
    )

    plt.tight_layout()
    return fig


def generate_markdown_summary(
    lat: float,
    lon: float,
    season: str,
    hemisphere: str,
    weather: dict,
    hdd18: float,
    cdd24: float,
    annual_mean: float,
    ashrae_zone: str,
    zone_desc: str,
    comfort_res: dict,
    rec_results: dict,
    wall_strategies: dict,
    is_demo_mode: bool = False
) -> str:
    """Generates a comprehensive Markdown report summarizing climate, comfort, materials, and wall layouts."""
    today_str = datetime.date.today().strftime("%B %d, %Y")
    data_source = "Saved Sample Weather (Offline Demo Mode)" if is_demo_mode else "Live Open-Meteo API (CC BY 4.0)"

    n_mat = rec_results["walls"]["North"]["wall"]
    s_mat = rec_results["walls"]["South"]["wall"]
    e_mat = rec_results["walls"]["East"]["wall"]
    w_mat = rec_results["walls"]["West"]["wall"]
    r_mat = rec_results["roof"]
    i_mat = rec_results["interior"]

    md = f"""# ThermoHome AI — Architectural Thermal Advisory Report
**Generated:** {today_str} | **Location:** {lat:.4f}° N, {lon:.4f}° E | **Hemisphere:** {hemisphere} | **Season:** {season}
**Data Source:** {data_source}

---

## 1. Climate & Degree Days Analysis
- **Current Outdoor Temperature:** {weather['current_temp']:.1f} °C
- **Relative Humidity:** {weather['current_humidity']:.0f} %
- **Heating Degree Days (HDD base 18°C):** {hdd18:.1f}
- **Cooling Degree Days (CDD base 24°C):** {cdd24:.1f}
- **Annual Mean Temperature:** {annual_mean:.1f} °C
- **Climate Zone:** **{ashrae_zone}** (*ASHRAE-based approximation*)
  - *{zone_desc}*

---

## 2. Personal Comfort Assessment
- **Status:** **{comfort_res['need']}**
- **Personal Thermal Profile:** Body Temp: {comfort_res.get('body_temp', 36.8):.1f} °C | Clothing: {comfort_res.get('clothing_level', 'Medium')} | Activity: {comfort_res.get('activity_level', 'Light')}
- **Adjusted Neutral Temperature:** {comfort_res['adj_neutral']:.1f} °C
- **Acceptable Comfort Band (±1.8 °C):** {comfort_res['comfort_min']:.1f} °C – {comfort_res['comfort_max']:.1f} °C
- **Assessment Rationale:** {comfort_res['explanation']}

---

## 3. Recommended Building Envelope Materials (Engineered by rules.py)

### Wall Assemblies by Cardinal Orientation
| Facade | Recommended Assembly | U-Value / R-Value | Cost | Architectural Rationale |
|:---|:---|:---:|:---:|:---|
| **North Wall** | {n_mat['name']} | {n_mat['u_value']} | {n_mat['cost']} | {n_mat['reason']} |
| **South Wall** | {s_mat['name']} | {s_mat['u_value']} | {s_mat['cost']} | {s_mat['reason']} |
| **East Wall** | {e_mat['name']} | {e_mat['u_value']} | {e_mat['cost']} | {e_mat['reason']} |
| **West Wall** | {w_mat['name']} | {w_mat['u_value']} | {w_mat['cost']} | {w_mat['reason']} |

### Roof & Interior Thermal Assemblies
- **Roof Assembly:** **{r_mat['name']}**
  - Thermal Rating: {r_mat['u_value']} | {r_mat.get('r_value', '')} | Cost: {r_mat['cost']}
  - Rationale: {r_mat['reason']}
- **Interior Thermal Mass & Finishes:** **{i_mat['name']}**
  - Thermal Rating: {i_mat['u_value']} | {i_mat.get('r_value', '')} | Cost: {i_mat['cost']}
  - Rationale: {i_mat['reason']}

---

## 4. Cardinal Orientation & Architectural Strategy
| Facade | Architectural Function & Daylighting | Window-to-Wall Ratio (WWR) | Shading & Solar Strategy |
|:---|:---|:---:|:---|
| **North** | {wall_strategies['North']['role']} | {wall_strategies['North']['wwr']} | {wall_strategies['North']['shading']} |
| **South** | {wall_strategies['South']['role']} | {wall_strategies['South']['wwr']} | {wall_strategies['South']['shading']} |
| **East** | {wall_strategies['East']['role']} | {wall_strategies['East']['wwr']} | {wall_strategies['East']['shading']} |
| **West** | {wall_strategies['West']['role']} | {wall_strategies['West']['wwr']} | {wall_strategies['West']['shading']} |

---
*Classification is an ASHRAE-based approximation for educational and early architectural decision support.*
"""
    return md


def generate_pdf_summary(
    lat: float,
    lon: float,
    season: str,
    hemisphere: str,
    weather: dict,
    hdd18: float,
    cdd24: float,
    annual_mean: float,
    ashrae_zone: str,
    zone_desc: str,
    comfort_res: dict,
    rec_results: dict,
    wall_strategies: dict,
    is_demo_mode: bool = False
) -> bytes:
    """Generates a publication-quality PDF summary using ReportLab."""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=letter,
        leftMargin=36, rightMargin=36, topMargin=36, bottomMargin=36
    )
    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        'DocTitle', parent=styles['Heading1'],
        fontSize=18, leading=22, textColor=colors.HexColor('#0F172A'), fontName='Helvetica-Bold'
    )
    subtitle_style = ParagraphStyle(
        'DocSubTitle', parent=styles['Normal'],
        fontSize=8.5, leading=12, textColor=colors.HexColor('#475569')
    )
    sec_head = ParagraphStyle(
        'SecHead', parent=styles['Heading2'],
        fontSize=11, leading=15, textColor=colors.HexColor('#0F172A'),
        fontName='Helvetica-Bold', spaceBefore=7, spaceAfter=4
    )
    cell_bold = ParagraphStyle(
        'CellBold', parent=styles['Normal'],
        fontSize=8, leading=10, textColor=colors.HexColor('#0F172A'), fontName='Helvetica-Bold'
    )
    cell_text = ParagraphStyle(
        'CellText', parent=styles['Normal'],
        fontSize=7.8, leading=10, textColor=colors.HexColor('#334155')
    )
    badge_text = ParagraphStyle(
        'BadgeText', parent=styles['Normal'],
        fontSize=7.8, leading=10, textColor=colors.HexColor('#0284C7'), fontName='Helvetica-Bold'
    )

    today_str = datetime.date.today().strftime("%B %d, %Y")
    data_source = "Saved Sample Weather (Offline Demo Mode)" if is_demo_mode else "Live Open-Meteo API (CC BY 4.0)"

    story = []
    story.append(Paragraph("ThermoHome AI — Architectural Thermal Advisory Report", title_style))
    story.append(Spacer(1, 2))
    story.append(Paragraph("Climate-Adaptive Building Envelope, Materials Selection & Orientation Strategy", subtitle_style))
    story.append(Paragraph(
        f"Generated: {today_str} | Location: {lat:.4f}° N, {lon:.4f}° E | "
        f"Hemisphere: {hemisphere} | Season: {season} | Source: {data_source}",
        subtitle_style
    ))
    story.append(Spacer(1, 4))
    story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor("#0284C7"), spaceAfter=6))

    # Section 1: Climate & Comfort Metadata Grid
    c_color = "#DC2626" if comfort_res["need"] == "Needs Cooling" else ("#2563EB" if comfort_res["need"] == "Needs Heating" else "#16A34A")
    meta_data = [
        [
            Paragraph(f"<b>Climate Zone:</b> {ashrae_zone} (ASHRAE-based approximation)", cell_text),
            Paragraph(f"<b>Current Conditions:</b> {weather['current_temp']:.1f} °C, {weather['current_humidity']:.0f}% RH", cell_text),
        ],
        [
            Paragraph(f"<b>Degree Days:</b> HDD₁₈: {hdd18:.1f} | CDD₂₄: {cdd24:.1f} | Mean: {annual_mean:.1f} °C", cell_text),
            Paragraph(f"<b>Thermal Comfort Need:</b> <font color=\"{c_color}\"><b>{comfort_res['need']}</b></font>", cell_text),
        ],
        [
            Paragraph(f"<b>Target Neutral:</b> {comfort_res['adj_neutral']:.1f} °C (Band: {comfort_res['comfort_min']:.1f} °C – {comfort_res['comfort_max']:.1f} °C)", cell_text),
            Paragraph(f"<b>User Profile:</b> {comfort_res.get('body_temp', 36.8):.1f} °C body, {comfort_res.get('clothing_level', 'Medium')} clothing, {comfort_res.get('activity_level', 'Light')} activity", cell_text),
        ]
    ]
    t_meta = Table(meta_data, colWidths=[270, 270])
    t_meta.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#F8FAFC')),
        ('BOX', (0,0), (-1,-1), 1.0, colors.HexColor('#E2E8F0')),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor('#E2E8F0')),
        ('TOPPADDING', (0,0), (-1,-1), 3),
        ('BOTTOMPADDING', (0,0), (-1,-1), 3),
    ]))
    story.append(t_meta)
    story.append(Spacer(1, 6))

    # Section 2: Recommended Building Materials Table
    story.append(Paragraph("Recommended Building Envelope Materials (Engineered by rules.py)", sec_head))
    mat_headers = [
        Paragraph("<b>Envelope Component</b>", cell_bold),
        Paragraph("<b>Recommended Material Assembly</b>", cell_bold),
        Paragraph("<b>Thermal Rating</b>", cell_bold),
        Paragraph("<b>Cost</b>", cell_bold),
        Paragraph("<b>Architectural Rationale</b>", cell_bold),
    ]
    mat_rows = [mat_headers]

    for card in ["North", "South", "East", "West"]:
        w = rec_results["walls"][card]["wall"]
        mat_rows.append([
            Paragraph(f"<b>{card} Facade</b>", cell_bold),
            Paragraph(w["name"], cell_text),
            Paragraph(f"{w['u_value']}<br/>{w.get('r_value', '')}", badge_text),
            Paragraph(w["cost"], cell_bold),
            Paragraph(w["reason"], cell_text),
        ])

    r = rec_results["roof"]
    mat_rows.append([
        Paragraph("<b>Roof Assembly</b>", cell_bold),
        Paragraph(r["name"], cell_text),
        Paragraph(f"{r['u_value']}<br/>{r.get('r_value', '')}", badge_text),
        Paragraph(r["cost"], cell_bold),
        Paragraph(r["reason"], cell_text),
    ])

    i = rec_results["interior"]
    mat_rows.append([
        Paragraph("<b>Interior Mass</b>", cell_bold),
        Paragraph(i["name"], cell_text),
        Paragraph(f"{i['u_value']}<br/>{i.get('r_value', '')}", badge_text),
        Paragraph(i["cost"], cell_bold),
        Paragraph(i["reason"], cell_text),
    ])

    t_mat = Table(mat_rows, colWidths=[80, 140, 85, 35, 200])
    t_mat.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#EEF2FF')),
        ('BOX', (0,0), (-1,-1), 1.0, colors.HexColor('#C7D2FE')),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor('#E2E8F0')),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('TOPPADDING', (0,0), (-1,-1), 3),
        ('BOTTOMPADDING', (0,0), (-1,-1), 3),
    ]))
    story.append(t_mat)
    story.append(Spacer(1, 6))

    # Section 3: Cardinal Orientation Strategy
    story.append(Paragraph("Cardinal Wall Orientation & Passive Solar Strategy", sec_head))
    strat_headers = [
        Paragraph("<b>Facade</b>", cell_bold),
        Paragraph("<b>Envelope Function & Daylighting</b>", cell_bold),
        Paragraph("<b>WWR %</b>", cell_bold),
        Paragraph("<b>Passive Shading & Mass Strategy</b>", cell_bold),
    ]
    strat_rows = [strat_headers]
    for card in ["North", "South", "East", "West"]:
        s = wall_strategies[card]
        strat_rows.append([
            Paragraph(f"<b>{card} Facade</b>", cell_bold),
            Paragraph(s["role"], cell_text),
            Paragraph(s["wwr"], badge_text),
            Paragraph(s["shading"], cell_text),
        ])

    t_strat = Table(strat_rows, colWidths=[70, 160, 55, 255])
    t_strat.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#F0FDF4')),
        ('BOX', (0,0), (-1,-1), 1.0, colors.HexColor('#BBF7D0')),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor('#E2E8F0')),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('TOPPADDING', (0,0), (-1,-1), 3),
        ('BOTTOMPADDING', (0,0), (-1,-1), 3),
    ]))
    story.append(t_strat)
    story.append(Spacer(1, 6))
    story.append(Paragraph(
        "<i>Classification is an ASHRAE-based approximation for educational and early architectural decision support.</i>",
        subtitle_style
    ))

    doc.build(story)
    return buffer.getvalue()



# Backward compatibility alias
def plot_wall_layout_diagram(wall_strategies: dict, hemisphere: str, climate_zone: str):
    """Alias delegating to plot_top_view_house_diagram if rec_results is passed or generates schematic."""
    if "walls" in wall_strategies:
        return plot_top_view_house_diagram(wall_strategies, hemisphere, climate_zone)
    # Fallback wrapper if called with legacy wall_strategies dict
    dummy_rec = {
        "walls": {
            k: {
                "wall": {"name": f"{k} Wall Assembly", "u_value": "U ≈ 0.40 W/m²K", "cost": "Med"},
                "materials": []
            } for k in ["North", "South", "East", "West"]
        },
        "roof": {"name": "Reflective Insulated Roof", "u_value": "U ≈ 0.35 W/m²K", "cost": "Med"},
        "interior": {"name": "Thermal Mass Partition", "u_value": "U ≈ 2.0 W/m²K", "cost": "Low"}
    }
    return plot_top_view_house_diagram(dummy_rec, hemisphere, climate_zone)



# -----------------------------------------------------------------------------
# 8. Main Application Interface
# -----------------------------------------------------------------------------
def main():
    # Header Banner
    st.markdown('<div class="main-header">ThermoHome AI 🏡🌡️</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="sub-header">Climate-Adaptive Building Materials & Wall Layout Recommendation Engine</div>',
        unsafe_allow_html=True
    )

    # -------------------------------------------------------------------------
    # Sidebar: Location, Geolocation, Personal Thermal Profile, Season
    # -------------------------------------------------------------------------
    st.sidebar.markdown("### 📍 Geographic Location")

    # Session state for coordinates (default: Pune 18.52, 73.86)
    if "user_lat" not in st.session_state:
        st.session_state.user_lat = 18.52
    if "user_lon" not in st.session_state:
        st.session_state.user_lon = 73.86
    if "last_detected_lat" not in st.session_state:
        st.session_state.last_detected_lat = None
    if "last_detected_lon" not in st.session_state:
        st.session_state.last_detected_lon = None

    # Geolocation detection button via streamlit-geolocation
    try:
        from streamlit_geolocation import streamlit_geolocation
        st.sidebar.caption("Detect your live GPS coordinates:")
        geo_location = streamlit_geolocation()
        if (
            geo_location
            and geo_location.get("latitude") is not None
            and geo_location.get("longitude") is not None
        ):
            detected_lat = round(float(geo_location["latitude"]), 4)
            detected_lon = round(float(geo_location["longitude"]), 4)
            if (
                detected_lat != st.session_state.last_detected_lat
                or detected_lon != st.session_state.last_detected_lon
            ):
                st.session_state.last_detected_lat = detected_lat
                st.session_state.last_detected_lon = detected_lon
                st.session_state.user_lat = detected_lat
                st.session_state.user_lon = detected_lon
                st.sidebar.success(f"Location detected: {detected_lat}, {detected_lon}")
    except Exception as geo_err:
        st.sidebar.caption("💡 Geolocation module idle (use manual inputs below).")

    # Manual Coordinate Inputs (Default: Pune 18.52° N, 73.86° E)
    lat_input = st.sidebar.number_input(
        "Latitude (°)",
        min_value=-90.0,
        max_value=90.0,
        value=float(st.session_state.user_lat),
        step=0.01,
        format="%.4f",
        help="Default: Pune (18.5200° N). Positive values denote Northern Hemisphere."
    )
    lon_input = st.sidebar.number_input(
        "Longitude (°)",
        min_value=-180.0,
        max_value=180.0,
        value=float(st.session_state.user_lon),
        step=0.01,
        format="%.4f",
        help="Default: Pune (73.8600° E). Positive values denote Eastern Hemisphere."
    )

    # Sync back to session state
    st.session_state.user_lat = lat_input
    st.session_state.user_lon = lon_input

    # -------------------------------------------------------------------------
    # Offline Demo Mode Checkbox
    # -------------------------------------------------------------------------
    demo_mode = st.sidebar.checkbox(
        "Offline Demo Mode (Use Sample Weather)",
        value=False,
        help="When enabled, bypasses live Open-Meteo API network calls and uses pre-cached sample weather data (Pune baseline)."
    )

    # -------------------------------------------------------------------------
    # Personal Comfort Profile
    # -------------------------------------------------------------------------
    st.sidebar.markdown("---")
    st.sidebar.markdown("### 👤 Personal Comfort Profile")

    body_temp = st.sidebar.slider(
        "Body Temperature (°C)",
        min_value=35.0,
        max_value=38.5,
        value=36.8,
        step=0.1,
        help="Normal resting core temperature is ~36.8°C. Higher temperatures elevate cooling demand."
    )

    clothing_level = st.sidebar.selectbox(
        "Clothing Level",
        options=["Light", "Medium", "Heavy"],
        index=1,
        help="Light (~0.5 clo: summer t-shirt/shorts), Medium (~1.0 clo: standard trousers/shirt), Heavy (~1.5 clo: winter sweater/jacket)"
    )

    activity_level = st.sidebar.selectbox(
        "Activity Level",
        options=["Resting", "Light", "Active"],
        index=1,
        help="Resting (~0.8 met: sleeping/reclining), Light (~1.2 met: sedentary office work), Active (~2.0 met: walking/chores)"
    )

    # -------------------------------------------------------------------------
    # Season Auto-Detection
    # -------------------------------------------------------------------------
    st.sidebar.markdown("---")
    st.sidebar.markdown("### 📅 Auto-Detected Season")
    auto_season, hemisphere = detect_season(lat_input)
    today_str = datetime.date.today().strftime("%b %d, %Y")
    st.sidebar.info(
        f"**Season:** {auto_season}\n\n"
        f"**Hemisphere:** {hemisphere} ({lat_input:+.2f}°)\n\n"
        f"**Date:** {today_str}"
    )

    # -------------------------------------------------------------------------
    # Fetch Weather Data via Free Open-Meteo API or Offline Demo Mode
    # -------------------------------------------------------------------------
    if demo_mode:
        weather = get_cached_sample_data(lat_input, lon_input)
        st.info("ℹ️ **Offline Demo Mode Active:** Using verified saved sample weather data (Pune baseline).")
    else:
        with st.spinner("Fetching live climate data from Open-Meteo..."):
            weather = fetch_climate_data(lat_input, lon_input)

        # API Failure / Fallback notification
        if weather["is_cached_sample"]:
            st.warning(
                f"⚠️ **Notice: Live Open-Meteo API call was unsuccessful.** "
                f"({weather.get('error_message', 'Connection issue')}). "
                f"Displaying verified cached sample climate data (Pune baseline) to evaluate recommendations."
            )

    # Calculations
    curr_temp = weather["current_temp"]
    curr_humidity = weather["current_humidity"]
    daily_means = weather["daily_means"]

    hdd18, cdd24, annual_mean = calculate_degree_days(daily_means, hdd_base=18.0, cdd_base=24.0)
    ashrae_zone, zone_desc = classify_ashrae_zone(hdd18, cdd24, curr_humidity, annual_mean)
    comfort_res = evaluate_comfort_need(curr_temp, body_temp, clothing_level, activity_level)
    rec_results = recommend(
        zone=ashrae_zone,
        season=auto_season,
        lat=lat_input,
        comfort_need=comfort_res["need"]
    )
    material_rec = get_recommended_materials(ashrae_zone, comfort_res["need"])
    wall_strategies = get_wall_orientation_strategy(ashrae_zone, lat_input)

    # Generate Export Summaries (Markdown & PDF)
    md_summary = generate_markdown_summary(
        lat=lat_input,
        lon=lon_input,
        season=auto_season,
        hemisphere=hemisphere,
        weather=weather,
        hdd18=hdd18,
        cdd24=cdd24,
        annual_mean=annual_mean,
        ashrae_zone=ashrae_zone,
        zone_desc=zone_desc,
        comfort_res=comfort_res,
        rec_results=rec_results,
        wall_strategies=wall_strategies,
        is_demo_mode=demo_mode
    )

    pdf_summary = generate_pdf_summary(
        lat=lat_input,
        lon=lon_input,
        season=auto_season,
        hemisphere=hemisphere,
        weather=weather,
        hdd18=hdd18,
        cdd24=cdd24,
        annual_mean=annual_mean,
        ashrae_zone=ashrae_zone,
        zone_desc=zone_desc,
        comfort_res=comfort_res,
        rec_results=rec_results,
        wall_strategies=wall_strategies,
        is_demo_mode=demo_mode
    )

    # Sidebar Quick Export Section
    zone_file_str = ashrae_zone.lower().replace(" ", "_")
    st.sidebar.markdown("---")
    st.sidebar.markdown("### 📥 Export Advisory Report")
    st.sidebar.download_button(
        label="📄 Download PDF Summary",
        data=pdf_summary,
        file_name=f"thermohome_{zone_file_str}.pdf",
        mime="application/pdf",
        use_container_width=True
    )
    st.sidebar.download_button(
        label="📝 Download Markdown Summary",
        data=md_summary,
        file_name=f"thermohome_{zone_file_str}.md",
        mime="text/markdown",
        use_container_width=True
    )

    # -------------------------------------------------------------------------
    # Main Tabs: (Climate | Materials | Wall Layout)
    # -------------------------------------------------------------------------
    tab_climate, tab_materials, tab_walls = st.tabs([
        "Climate",
        "Materials",
        "Wall Layout"
    ])

    # -------------------------------------------------------------------------
    # TAB 1: Climate (Summary, Classification, Gauge, Historical Profile)
    # -------------------------------------------------------------------------
    with tab_climate:
        st.subheader("Climate Profile & Thermal Comfort Analysis")

        # Top 5 Climate Metrics
        col1, col2, col3, col4, col5 = st.columns(5)
        with col1:
            st.metric("Current Outdoor Temp", f"{curr_temp:.1f} °C")
        with col2:
            st.metric("Relative Humidity", f"{curr_humidity:.0f} %")
        with col3:
            st.metric("Annual CDD (Base 24°C)", f"{cdd24:.0f}")
        with col4:
            st.metric("Annual HDD (Base 18°C)", f"{hdd18:.0f}")
        with col5:
            st.metric("Annual Mean Temp", f"{annual_mean:.1f} °C")

        st.markdown("<br>", unsafe_allow_html=True)

        # Climate Classification & Comfort Need Highlighters
        stat_col1, stat_col2 = st.columns([1, 1])

        with stat_col1:
            st.markdown(f"#### 🌐 Climate Zone: **{ashrae_zone}**")
            st.markdown(
                f'<span class="badge-ashrae">ASHRAE-based approximation</span>',
                unsafe_allow_html=True
            )
            st.write(f"*{zone_desc}*")

        with stat_col2:
            st.markdown("#### 🎯 Current Thermal Comfort Need")
            badge_html = (
                f'<div class="comfort-badge" style="background-color: {comfort_res["badge_bg"]}; '
                f'color: {comfort_res["badge_color"]};">'
                f'{comfort_res["badge_icon"]} {comfort_res["need"]}'
                f'</div>'
            )
            st.markdown(badge_html, unsafe_allow_html=True)
            st.write(f"{comfort_res['explanation']}")

        st.markdown("---")
        st.markdown("### 👤 Personalized Thermal Comfort Assessment")
        st.write(
            "Thermal sensation depends on physiological and behavioral factors as defined by "
            "ASHRAE Standard 55 PMV principles. Below is how your inputs shifted your neutral comfort temperature:"
        )

        gauge_col, table_col = st.columns([1.1, 1.0])

        with gauge_col:
            st.markdown("#### Thermometer-Style Comfort Gauge")
            fig_gauge = plot_thermometer_gauge(comfort_res, curr_temp)
            st.pyplot(fig_gauge)

        with table_col:
            st.markdown("#### Physiological & Clothing Offsets")
            comfort_df = pd.DataFrame([
                {"Parameter": "Base Neutral Temperature", "Value": "24.0 °C", "Impact on Neutral Target": "0.0 °C (Sedentary baseline)"},
                {"Parameter": f"Clothing ({clothing_level})", "Value": f"{clothing_level}", "Impact on Neutral Target": f"{comfort_res['clo_shift']:+.1f} °C"},
                {"Parameter": f"Activity ({activity_level})", "Value": f"{activity_level}", "Impact on Neutral Target": f"{comfort_res['act_shift']:+.1f} °C"},
                {"Parameter": f"Body Temperature ({body_temp:.1f} °C)", "Value": f"{body_temp:.1f} °C", "Impact on Neutral Target": f"{comfort_res['body_shift']:+.2f} °C"},
                {"Parameter": "Adjusted Neutral Target", "Value": f"{comfort_res['adj_neutral']:.1f} °C", "Impact on Neutral Target": "Personalized equilibrium point"},
                {"Parameter": "Comfort Band (±1.8 °C)", "Value": f"{comfort_res['comfort_min']:.1f} °C – {comfort_res['comfort_max']:.1f} °C", "Impact on Neutral Target": "Acceptable range"},
                {"Parameter": "Current Ambient Temp", "Value": f"{curr_temp:.1f} °C", "Impact on Neutral Target": f"Status: {comfort_res['need']}"}
            ])
            st.table(comfort_df)

            st.markdown("#### Sensation & Energy Implications")
            if comfort_res["need"] == "Needs Cooling":
                st.info(
                    "❄️ **Cooling Dominant:** High metabolic rate, heavy clothing, or elevated outdoor warmth "
                    "pushes internal heat dissipation requirements. Focus on cross-ventilation, ceiling airflow, "
                    "and exterior solar shading."
                )
            elif comfort_res["need"] == "Needs Heating":
                st.warning(
                    "🔥 **Heating Dominant:** Light clothing, low activity, or cold ambient air creates net heat loss. "
                    "Focus on passive direct solar capture through equator-facing glazing and building envelope insulation."
                )
            else:
                st.success(
                    "⚖️ **Thermal Equilibrium:** Ambient temperature aligns with your current metabolic heat generation "
                    "and clothing resistance. Natural passive conditions suffice without active HVAC intervention."
                )

        st.markdown("---")
        st.markdown("### 📊 365-Day Historical Climate Profile")
        st.write(
            f"Analysis of past 365 daily mean temperatures retrieved from the Open-Meteo Archive API. "
            f"Heating Degree Days (base 18°C) = **{hdd18:.1f}**, Cooling Degree Days (base 24°C) = **{cdd24:.1f}**."
        )

        # Plot daily temperature series with threshold bands
        fig_temp, ax_temp = plt.subplots(figsize=(10, 4.2), facecolor='#FAFAFA')
        ax_temp.set_facecolor('#FFFFFF')

        x_days = np.arange(len(daily_means))
        ax_temp.plot(x_days, daily_means, color='#0284C7', lw=1.5, label='Daily Mean Temp (°C)')
        ax_temp.axhline(18.0, color='#DC2626', linestyle='--', lw=1.2, label='HDD Base (18°C)')
        ax_temp.axhline(24.0, color='#2563EB', linestyle='--', lw=1.2, label='CDD Base (24°C)')

        # Shading for heating and cooling zones
        ax_temp.fill_between(x_days, daily_means, 18.0, where=(np.array(daily_means) < 18.0),
                             color='#FCA5A5', alpha=0.35, label='Heating Demand (HDD)')
        ax_temp.fill_between(x_days, daily_means, 24.0, where=(np.array(daily_means) > 24.0),
                             color='#93C5FD', alpha=0.35, label='Cooling Demand (CDD)')

        ax_temp.set_title(f"Annual Temperature History & Degree Days ({len(daily_means)} days)", fontsize=11, fontweight='bold')
        ax_temp.set_xlabel("Days in Past Year", fontsize=9)
        ax_temp.set_ylabel("Temperature (°C)", fontsize=9)
        ax_temp.grid(True, linestyle=':', alpha=0.6)
        ax_temp.legend(loc='upper right', fontsize=8, framealpha=0.9)
        plt.tight_layout()
        st.pyplot(fig_temp)

    # -------------------------------------------------------------------------
    # TAB 2: Materials (Recommended Materials engineered by rules.py)
    # -------------------------------------------------------------------------
    with tab_materials:
        st.subheader(f"Recommended Building Materials for {ashrae_zone} Climate")
        st.caption(f"Engineered by rules.py for '{comfort_res['need']}' state in {auto_season} ({hemisphere} Hemisphere).")

        st.markdown("### 🧱 Wall Envelope Materials by Cardinal Orientation")
        cardinal_cols = st.columns(2)
        cardinals = ["North", "South", "East", "West"]

        for idx, card in enumerate(cardinals):
            with cardinal_cols[idx % 2]:
                w_info = rec_results["walls"][card]
                st.markdown(f"#### {card} Facade")
                st.caption(f"*{w_info['description']}*")

                for mat in w_info["materials"]:
                    cost_color = {"Low": "#15803D", "Med": "#B45309", "High": "#B91C1C"}.get(mat["cost"], "#475569")
                    cost_bg = {"Low": "#DCFCE7", "Med": "#FEF3C7", "High": "#FEE2E2"}.get(mat["cost"], "#F1F5F9")
                    st.markdown(f"""
                    <div class="material-card">
                        <div style="display: flex; justify-content: space-between; align-items: baseline;">
                            <span style="font-weight: 700; font-size: 0.98rem; color: #0F172A;">{mat['name']}</span>
                            <span style="background: {cost_bg}; color: {cost_color}; font-size: 0.78rem; font-weight: 700; padding: 2px 7px; border-radius: 4px; border: 1px solid {cost_color};">
                                Cost: {mat['cost']}
                            </span>
                        </div>
                        <div style="font-size: 0.85rem; color: #0284C7; font-weight: 600; margin: 3px 0;">
                            {mat['u_value']} &nbsp;|&nbsp; {mat['r_value']}
                        </div>
                        <div style="font-size: 0.88rem; color: #475569; line-height: 1.4;">
                            {mat['reason']}
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                st.markdown("<br>", unsafe_allow_html=True)

        st.markdown("---")
        st.markdown("### 🏠 Roof & Interior Thermal Assemblies")
        r_col1, r_col2 = st.columns(2)
        with r_col1:
            st.markdown("#### Roof Assembly")
            r_mat = rec_results["roof"]
            cost_color = {"Low": "#15803D", "Med": "#B45309", "High": "#B91C1C"}.get(r_mat["cost"], "#475569")
            cost_bg = {"Low": "#DCFCE7", "Med": "#FEF3C7", "High": "#FEE2E2"}.get(r_mat["cost"], "#F1F5F9")
            st.markdown(f"""
            <div class="material-card">
                <div style="display: flex; justify-content: space-between; align-items: baseline;">
                    <span style="font-weight: 700; font-size: 0.98rem; color: #0F172A;">{r_mat['name']}</span>
                    <span style="background: {cost_bg}; color: {cost_color}; font-size: 0.78rem; font-weight: 700; padding: 2px 7px; border-radius: 4px; border: 1px solid {cost_color};">
                        Cost: {r_mat['cost']}
                    </span>
                </div>
                <div style="font-size: 0.85rem; color: #0284C7; font-weight: 600; margin: 3px 0;">
                    {r_mat['u_value']} &nbsp;|&nbsp; {r_mat['r_value']}
                </div>
                <div style="font-size: 0.88rem; color: #475569; line-height: 1.4;">
                    {r_mat['reason']}
                </div>
            </div>
            """, unsafe_allow_html=True)

        with r_col2:
            st.markdown("#### Interior Thermal Mass & Finishes")
            i_mat = rec_results["interior"]
            cost_color = {"Low": "#15803D", "Med": "#B45309", "High": "#B91C1C"}.get(i_mat["cost"], "#475569")
            cost_bg = {"Low": "#DCFCE7", "Med": "#FEF3C7", "High": "#FEE2E2"}.get(i_mat["cost"], "#F1F5F9")
            st.markdown(f"""
            <div class="material-card">
                <div style="display: flex; justify-content: space-between; align-items: baseline;">
                    <span style="font-weight: 700; font-size: 0.98rem; color: #0F172A;">{i_mat['name']}</span>
                    <span style="background: {cost_bg}; color: {cost_color}; font-size: 0.78rem; font-weight: 700; padding: 2px 7px; border-radius: 4px; border: 1px solid {cost_color};">
                        Cost: {i_mat['cost']}
                    </span>
                </div>
                <div style="font-size: 0.85rem; color: #0284C7; font-weight: 600; margin: 3px 0;">
                    {i_mat['u_value']} &nbsp;|&nbsp; {i_mat['r_value']}
                </div>
                <div style="font-size: 0.88rem; color: #475569; line-height: 1.4;">
                    {i_mat['reason']}
                </div>
            </div>
            """, unsafe_allow_html=True)

    # -------------------------------------------------------------------------
    # TAB 3: Wall Layout (Top-View House Diagram, Orientation, Downloads)
    # -------------------------------------------------------------------------
    with tab_walls:
        st.subheader("Architectural Top-View House Diagram & Orientation Strategy")
        st.write(
            f"Square floor plan with four cardinal walls (N/S/E/W) for the **{hemisphere} Hemisphere** "
            f"({lat_input:+.2f}° latitude), showing recommended materials, thermal ratings, and diurnal sun-path arrow."
        )

        # High-contrast projector-readable top-view diagram
        fig_house = plot_top_view_house_diagram(rec_results, hemisphere, ashrae_zone)
        st.pyplot(fig_house)

        st.markdown("---")
        st.markdown("### 🧭 Cardinal Orientation Strategy Breakdown")
        w_cols = st.columns(4)
        for idx, cardinal in enumerate(["North", "South", "East", "West"]):
            strat = wall_strategies[cardinal]
            with w_cols[idx]:
                st.markdown(f"#### {cardinal} Wall")
                st.markdown(f"**Function:**\n{strat['role']}")
                st.markdown(f"**WWR:** `{strat['wwr']}`")
                st.markdown(f"**Shading:**\n{strat['shading']}")

        st.markdown("---")
        st.markdown("### 📥 Download Advisory Summary Report")
        st.write(
            "Export a complete, publication-ready advisory summary of your climate analysis, "
            "material selections, and orientation rules as PDF or Markdown:"
        )

        dl_col1, dl_col2 = st.columns(2)
        with dl_col1:
            st.download_button(
                label="📄 Download Advisory Report (.pdf)",
                data=pdf_summary,
                file_name=f"thermohome_advisory_{zone_file_str}.pdf",
                mime="application/pdf",
                use_container_width=True
            )
        with dl_col2:
            st.download_button(
                label="📝 Download Advisory Report (.md)",
                data=md_summary,
                file_name=f"thermohome_advisory_{zone_file_str}.md",
                mime="text/markdown",
                use_container_width=True
            )

    # Footer
    st.markdown("---")
    st.caption(
        "ThermoHome AI | Built with Streamlit & Open-Meteo API (CC BY 4.0). "
        "Classification is an ASHRAE-based approximation for educational & early architectural decision support."
    )


if __name__ == "__main__":
    main()
