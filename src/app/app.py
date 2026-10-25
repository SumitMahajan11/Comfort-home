"""
ClimateAdapt-Comfort: Modern Architectural Decision-Support Web Application
Passive Shelter Design Optimization, Thermal Comfort Evaluation, and Multi-Objective Trade-Off Analysis.

Research Decision-Support Tool for Indian Climate Zones.
Simulation-based pipeline using ASHRAE DB II, EnergyPlus 26.2.0, XGBoost Surrogates, NSGA-II, and SHAP.
"""

import os
import sys
import json
import math
import joblib
import urllib.request
import urllib.parse
import numpy as np
import pandas as pd
import streamlit as st
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker

# -----------------------------------------------------------------------------
# 1. Environment & Path Setup
# -----------------------------------------------------------------------------
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from src.models.explain import get_top_drivers, FEATURE_NAME_MAP
from src.app.answer_mapping import map_answers_to_weights

# -----------------------------------------------------------------------------
# 2. Page Configuration
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="ClimateAdapt-Comfort | Shelter Decision Support",
    page_icon="🏛️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# -----------------------------------------------------------------------------
# 3. Architectural Design System & CSS
# -----------------------------------------------------------------------------
ARCH_CSS = """
<style>
/* Architectural Climate Color Palette & Design Tokens */
:root {
    --bg-sand: #F8F7F4;
    --bg-card: #FFFFFF;
    --bg-subtle: #F4F1EA;
    --border-card: #E4DED5;
    --border-subtle: #EDE8E1;
    --navy-main: #0F1B2B;
    --navy-muted: #3B4B5F;
    --navy-faint: #64748B;
    --teal-accent: #0D9488;
    --teal-dark: #0F766E;
    --teal-subtle: #F0FDFA;
    --teal-border: #99F6E4;
    --green-accent: #15803D;
    --green-subtle: #F0FDF4;
    --green-border: #BBF7D0;
    --terracotta: #C85A32;
    --terracotta-subtle: #FFF7ED;
    --terracotta-border: #FFEDD5;
    --sand-accent: #C2A684;
}

/* Global Typography & Canvas */
html, body, [class*="st-"] {
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
    color: var(--navy-main);
}

.stApp {
    background-color: var(--bg-sand);
}

/* Sidebar Styling */
section[data-testid="stSidebar"] {
    background-color: #EFECE6 !important;
    border-right: 1px solid var(--border-card);
}

section[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] h1,
section[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] h2,
section[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] h3 {
    color: var(--navy-main);
    font-weight: 700;
}

/* Header & Titles */
h1 {
    color: var(--navy-main) !important;
    font-size: 1.85rem !important;
    font-weight: 750 !important;
    letter-spacing: -0.02em !important;
    margin-bottom: 0.35rem !important;
}

h2 {
    color: var(--navy-main) !important;
    font-size: 1.4rem !important;
    font-weight: 700 !important;
    letter-spacing: -0.015em !important;
    margin-top: 1.2rem !important;
    margin-bottom: 0.5rem !important;
}

h3 {
    color: var(--navy-muted) !important;
    font-size: 1.12rem !important;
    font-weight: 650 !important;
    margin-top: 1.0rem !important;
    margin-bottom: 0.35rem !important;
}

/* Institutional Banner Header */
.arch-header {
    background: linear-gradient(180deg, #FFFFFF 0%, #FAF8F5 100%);
    border: 1px solid var(--border-card);
    border-radius: 8px;
    padding: 18px 24px;
    margin-bottom: 20px;
    box-shadow: 0 1px 3px rgba(15, 27, 43, 0.04);
}
.arch-header-title {
    font-size: 1.6rem;
    font-weight: 800;
    color: var(--navy-main);
    letter-spacing: -0.02em;
    margin: 0;
    display: flex;
    align-items: center;
    gap: 10px;
}
.arch-header-subtitle {
    font-size: 0.92rem;
    color: var(--navy-muted);
    margin-top: 4px;
    line-height: 1.45;
}

/* Architectural Card */
.arch-card {
    background: var(--bg-card);
    border: 1px solid var(--border-card);
    border-radius: 8px;
    padding: 16px 20px;
    margin-bottom: 16px;
    box-shadow: 0 1px 3px rgba(15, 27, 43, 0.03);
}

/* Metric Display Cards */
.arch-metric-card {
    background: #FFFFFF;
    border: 1px solid var(--border-card);
    border-radius: 8px;
    padding: 14px 18px;
    height: 100%;
    box-shadow: 0 1px 2px rgba(15, 27, 43, 0.03);
    transition: transform 0.15s ease, box-shadow 0.15s ease;
}
.arch-metric-card:hover {
    border-color: var(--teal-accent);
    box-shadow: 0 2px 6px rgba(13, 148, 136, 0.10);
}
.arch-metric-label {
    font-size: 0.78rem;
    font-weight: 650;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    color: var(--navy-muted);
    margin-bottom: 4px;
}
.arch-metric-value {
    font-size: 1.55rem;
    font-weight: 750;
    color: var(--navy-main);
    letter-spacing: -0.02em;
    line-height: 1.2;
}
.arch-metric-subtext {
    font-size: 0.82rem;
    color: var(--navy-faint);
    margin-top: 4px;
}

/* Callouts and Banners */
.arch-banner {
    border-radius: 6px;
    padding: 14px 18px;
    margin: 14px 0;
    font-size: 0.90rem;
    line-height: 1.5;
}
.arch-banner-info {
    background-color: var(--teal-subtle);
    border: 1px solid var(--teal-border);
    border-left: 4px solid var(--teal-accent);
    color: #134E4A;
}
.arch-banner-warning {
    background-color: var(--terracotta-subtle);
    border: 1px solid var(--terracotta-border);
    border-left: 4px solid var(--terracotta);
    color: #9A3412;
}
.arch-banner-success {
    background-color: var(--green-subtle);
    border: 1px solid var(--green-border);
    border-left: 4px solid var(--green-accent);
    color: #14532D;
}

/* Confidence Badges */
.badge-tier {
    display: inline-block;
    padding: 3px 10px;
    border-radius: 9999px;
    font-size: 0.78rem;
    font-weight: 700;
    letter-spacing: 0.03em;
    text-transform: uppercase;
}
.badge-tier-medium {
    background-color: var(--green-subtle);
    color: var(--green-accent);
    border: 1px solid var(--green-border);
}
.badge-tier-low {
    background-color: var(--terracotta-subtle);
    color: var(--terracotta);
    border: 1px solid var(--terracotta-border);
}

/* Streamlit Native Element Overrides */
div[data-testid="stMetric"] {
    background: #FFFFFF;
    border: 1px solid var(--border-card);
    border-radius: 8px;
    padding: 12px 16px;
    box-shadow: 0 1px 2px rgba(15, 27, 43, 0.03);
}

div[data-testid="stMetric"] label {
    font-size: 0.80rem !important;
    font-weight: 650 !important;
    color: var(--navy-muted) !important;
}

div[data-testid="stMetric"] div[data-testid="stMetricValue"] {
    color: var(--navy-main) !important;
    font-weight: 750 !important;
}

/* Tables */
div[data-testid="stDataFrame"] {
    border: 1px solid var(--border-card);
    border-radius: 8px;
    background: #FFFFFF;
    overflow: hidden;
}

/* Forms and Inputs */
div[data-testid="stForm"] {
    background: #FFFFFF;
    border: 1px solid var(--border-card);
    border-radius: 8px;
    padding: 20px 24px;
}

.stButton > button {
    background-color: var(--navy-main);
    color: #FFFFFF;
    border: 1px solid var(--navy-main);
    border-radius: 6px;
    font-weight: 600;
    padding: 0.45rem 1.1rem;
    transition: all 0.15s ease;
}
.stButton > button:hover {
    background-color: var(--teal-accent);
    border-color: var(--teal-accent);
    color: #FFFFFF;
}

/* Mobile & Narrow Screen Responsiveness */
@media (max-width: 768px) {
    .arch-header {
        padding: 14px 16px;
    }
    .arch-header-title {
        font-size: 1.35rem;
    }
    .arch-card {
        padding: 12px 14px;
    }
    div[data-testid="stMetric"] {
        padding: 8px 12px;
    }
}
</style>
"""
st.markdown(ARCH_CSS, unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# 4. Master Station Metadata & Coordinates (5 Indian Climate Zones)
# -----------------------------------------------------------------------------
SIMULATED_CITIES_COORDS = {
    "Jodhpur": {
        "lat": 26.2389,
        "lon": 73.0243,
        "label": "Jodhpur (Hot-Dry, Rajasthan)",
        "zone": "Hot-Dry",
        "koppen": "BWh (Arid Desert)",
        "epw": "IND_RJ_Jodhpur.423390_TMYx.epw",
        "confidence_tier": "Low",
        "confidence_reason": "High seasonal temperature extremes; dual-judge divergence during hot summer months (Spearman rs = 0.109).",
        "adaptive_validity": "86.85% valid hours",
        "envelope_coverage": "53.91% inside DB II 1st-99th percentile"
    },
    "Mumbai": {
        "lat": 19.0760,
        "lon": 72.8777,
        "label": "Mumbai (Warm-Humid, Maharashtra)",
        "zone": "Warm-Humid",
        "koppen": "Aw (Tropical Savanna)",
        "epw": "IND_MH_Mumbai-Shivaji.Intl.AP.430030_TMYx.epw",
        "confidence_tier": "Medium",
        "confidence_reason": "High directional agreement between comfort judges (Spearman rs = 0.945) and 100% adaptive envelope validity.",
        "adaptive_validity": "100.0% valid hours",
        "envelope_coverage": "27.91% inside DB II 1st-99th percentile (monsoon humidity)"
    },
    "New_Delhi": {
        "lat": 28.6139,
        "lon": 77.2090,
        "label": "New Delhi (Composite, NCR)",
        "zone": "Composite",
        "koppen": "Cwa (Monsoon Subtropical)",
        "epw": "IND_DL_New.Delhi-Gandhi.Intl.AP.421810_TMYx.epw",
        "confidence_tier": "Low",
        "confidence_reason": "Sharp seasonal contrast between cold dry winters and humid hot monsoons causes model divergence (Spearman rs = 0.195).",
        "adaptive_validity": "89.86% valid hours",
        "envelope_coverage": "53.12% inside DB II 1st-99th percentile"
    },
    "Bengaluru": {
        "lat": 12.9716,
        "lon": 77.5946,
        "label": "Bengaluru (Temperate, Karnataka)",
        "zone": "Temperate",
        "koppen": "Aw / Cwa (Tropical Moderate Upland)",
        "epw": "IND_KA_Bengaluru-Hindustan.AP.432960_TMYx.epw",
        "confidence_tier": "Medium",
        "confidence_reason": "Moderate plateau conditions with strong dual-judge concordance (Spearman rs = 0.943) and 100% adaptive validity.",
        "adaptive_validity": "100.0% valid hours",
        "envelope_coverage": "43.39% inside DB II 1st-99th percentile"
    },
    "Shimla": {
        "lat": 31.1048,
        "lon": 77.1734,
        "label": "Shimla (Cold, Himachal Pradesh)",
        "zone": "Cold",
        "koppen": "Cwb (Subtropical Highland / Alpine)",
        "epw": "IND_HP_Shimla.420830_TMYx.epw",
        "confidence_tier": "Low",
        "confidence_reason": "Severe winter cold (26.03% hours outdoor temperature < 10°C) operates outside calibrated adaptive boundaries (D-011).",
        "adaptive_validity": "73.97% valid hours (Severe winter extrapolation)",
        "envelope_coverage": "77.26% inside DB II 1st-99th percentile"
    }
}

# Plain-language parameter map
APP_FEATURE_NAME_MAP = {
    'roof_insulation_thickness': 'Roof Insulation (mm)',
    'wall_insulation_thickness': 'Wall Insulation (mm)',
    'roof_solar_absorptance': 'Roof Solar Absorptance',
    'wwr': 'Window-to-Wall Ratio (WWR %)',
    'orientation': 'Orientation (° from North)',
    'shading_depth': 'Shading Overhang Depth (m)',
    'ventilation_ach': 'Ventilation Rate (ACH)',
    'wall_mass_heavy': 'Wall Mass: Heavy (Concrete)',
    'wall_mass_light': 'Wall Mass: Light (Sheet)',
    'wall_mass_medium': 'Wall Mass: Medium (Clay Brick)',
    'ta': 'Indoor Air Temp Ta (°C)',
    'tr': 'Mean Radiant Temp Tr (°C)',
    'rh': 'Relative Humidity RH (%)',
    'vel': 'Air Velocity (m/s)',
    'clo': 'Clothing Insulation (clo)',
    'met': 'Metabolic Rate (met)',
    't_outdoor': 'Running Mean Outdoor Temp (°C)'
}

# -----------------------------------------------------------------------------
# 5. Geocoding & Helper Utilities
# -----------------------------------------------------------------------------
def haversine_distance_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r_earth = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (math.sin(dlat / 2.0) ** 2 +
         math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) *
         math.sin(dlon / 2.0) ** 2)
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return r_earth * c

def geocode_location(query: str):
    if not query or not query.strip():
        return None
    try:
        encoded_query = urllib.parse.quote(query.strip())
        url = f"https://geocoding-api.open-meteo.com/v1/search?name={encoded_query}&count=1&language=en&format=json"
        req = urllib.request.Request(url, headers={"User-Agent": "ClimateAdaptComfort/1.2"})
        with urllib.request.urlopen(req, timeout=3.0) as response:
            if response.status == 200:
                data = json.loads(response.read().decode("utf-8"))
                if "results" in data and len(data["results"]) > 0:
                    res = data["results"][0]
                    name_parts = [res.get("name", query)]
                    if "admin1" in res and res["admin1"]:
                        name_parts.append(res["admin1"])
                    if "country" in res and res["country"]:
                        name_parts.append(res["country"])
                    return float(res["latitude"]), float(res["longitude"]), ", ".join(name_parts)
    except Exception:
        pass
    return None

@st.cache_data(ttl=600)
def fetch_current_weather(lat: float, lon: float):
    """
    Fetches current 2-meter outdoor temperature from Open-Meteo API.
    Free, local-first compatible, no API key required.
    Cached for 10 minutes; returns None if offline or timed out.
    """
    try:
        url = (
            f"https://api.open-meteo.com/v1/forecast?"
            f"latitude={lat:.4f}&longitude={lon:.4f}&"
            f"current=temperature_2m,relative_humidity_2m,apparent_temperature&"
            f"timezone=auto"
        )
        req = urllib.request.Request(url, headers={"User-Agent": "ClimateAdaptComfort/1.2"})
        with urllib.request.urlopen(req, timeout=3.5) as response:
            if response.status == 200:
                data = json.loads(response.read().decode("utf-8"))
                if "current" in data:
                    cur = data["current"]
                    return {
                        "temperature_2m": cur.get("temperature_2m"),
                        "apparent_temperature": cur.get("apparent_temperature"),
                        "relative_humidity_2m": cur.get("relative_humidity_2m"),
                        "time": cur.get("time"),
                        "timezone": data.get("timezone", "Local Time"),
                        "source": "Open-Meteo Weather Model (ECMWF/GFS)"
                    }
    except Exception:
        pass
    return None

def render_live_weather_card(lat: float, lon: float, location_name: str, key_suffix: str = ""):
    """
    Renders the 'Current outdoor temperature' card for the searched location or climate station.
    Clearly marks it as a live weather-model estimate separate from EPW annual data.
    Provides manual refresh button, graceful offline fallback, and Open-Meteo attribution.
    """
    weather_data = fetch_current_weather(lat, lon)
    
    st.markdown("#### 🌡️ Current Outdoor Temperature")
    
    col_w_content, col_w_refresh = st.columns([4, 1])
    with col_w_refresh:
        if st.button("🔄 Refresh Weather", key=f"btn_refresh_weather_{key_suffix}", help="Bypass 10-minute cache and fetch latest live temperature from Open-Meteo"):
            fetch_current_weather.clear()
            st.rerun()

    with col_w_content:
        if weather_data is not None and weather_data.get("temperature_2m") is not None:
            temp_c = weather_data["temperature_2m"]
            feels_like = weather_data.get("apparent_temperature")
            rh_pct = weather_data.get("relative_humidity_2m")
            raw_time = weather_data.get("time", "Recent")
            formatted_time = raw_time.replace("T", " ") if isinstance(raw_time, str) else str(raw_time)
            tz = weather_data.get("timezone", "Local Time")
            source_name = weather_data.get("source", "Open-Meteo Weather API")
            
            feels_text = f"Feels like: <strong>{feels_like:.1f} °C</strong> &bull; " if feels_like is not None else ""
            rh_text = f"Relative Humidity: <strong>{rh_pct}%</strong>" if rh_pct is not None else ""
            
            st.markdown(
                f"<div class='arch-card' style='border-left: 4px solid var(--teal-accent); background: #FFFFFF; margin-bottom: 12px;'>"
                f"<div style='display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:8px;'>"
                f"  <div>"
                f"    <span class='badge-tier badge-tier-medium' style='background:#F0FDFA; color:#0F766E; border-color:#99F6E4;'>Live Weather-Model Estimate</span>"
                f"    <div style='font-size:0.85rem; color:#475569; margin-top:4px;'>"
                f"      📍 <strong>Matched Location:</strong> {location_name} (<code>{lat:.3f}°N, {lon:.3f}°E</code>)"
                f"    </div>"
                f"  </div>"
                f"</div>"
                f"<div style='display:flex; align-items:baseline; gap:12px; margin: 10px 0 6px 0;'>"
                f"  <span style='font-size:2.35rem; font-weight:800; color:var(--navy-main); letter-spacing:-0.03em;'>{temp_c:.1f} °C</span>"
                f"  <span style='font-size:0.86rem; color:#64748B;'>{feels_text}{rh_text}</span>"
                f"</div>"
                f"<div style='font-size:0.78rem; color:#64748B; border-top:1px solid #EDE8E1; padding-top:8px; display:flex; justify-content:space-between; flex-wrap:wrap; gap:8px;'>"
                f"  <div>🕒 <strong>Last Updated:</strong> {formatted_time} ({tz}) &bull; <strong>Source:</strong> {source_name}</div>"
                f"  <div>Weather data by <a href='https://open-meteo.com/' target='_blank' style='color:#0D9488; text-decoration:underline;'>Open-Meteo.com</a> (CC BY 4.0)</div>"
                f"</div>"
                f"<div style='margin-top:6px; font-size:0.75rem; color:#94A3B8; font-style:italic;'>"
                f"  ⚠️ Live weather-model estimate for real-time situational awareness. "
                f"Strictly independent from EPW annual simulation weather data; does not alter surrogate comfort predictions, energy demand, or optimization."
                f"</div>"
                f"</div>",
                unsafe_allow_html=True
            )
        else:
            st.markdown(
                f"<div class='arch-banner arch-banner-info'>"
                f"☁️ <strong>Live weather unavailable:</strong> Unable to retrieve current 2-meter temperature for <strong>{location_name}</strong> "
                f"(network offline or request timed out). Saved simulation artifacts, comfort baselines, and Pareto recommendations remain fully active.<br>"
                f"<small style='color:#64748B;'>Weather data service attribution: <a href='https://open-meteo.com/' target='_blank' style='color:#0D9488;'>Open-Meteo.com</a> (CC BY 4.0)</small>"
                f"</div>",
                unsafe_allow_html=True
            )

def find_nearest_simulated_city(lat: float, lon: float):
    nearest_city = None
    min_dist = float("inf")
    for city_key, meta in SIMULATED_CITIES_COORDS.items():
        dist = haversine_distance_km(lat, lon, meta["lat"], meta["lon"])
        if dist < min_dist:
            min_dist = dist
            nearest_city = city_key
    return nearest_city, round(min_dist, 1)

def get_cardinal_direction(deg: float) -> str:
    directions = [
        "North (0°)", "North-East (45°)", "East (90°)", "South-East (135°)",
        "South (180°)", "South-West (225°)", "West (270°)", "North-West (315°)"
    ]
    idx = int((deg + 22.5) / 45.0) % 8
    return directions[idx]

def format_plain_shap_driver(driver_name: str, value: float, city: str) -> str:
    if "roof_insulation" in driver_name:
        mm = int(round(value * 1000 if value < 1.0 else value))
        return f"Roof insulation of {mm} mm provides essential thermal barrier against solar heat gain and winter loss."
    elif "wall_insulation" in driver_name:
        mm = int(round(value * 1000 if value < 1.0 else value))
        return f"Wall insulation of {mm} mm moderates envelope conductive flux during peak daytime hours."
    elif "wwr" in driver_name:
        pct = int(round(value * 100 if value < 1.0 else value))
        return f"Window area of {pct}% balances natural daylight against radiant solar heat ingress."
    elif "shading" in driver_name:
        return f"Exterior overhang depth of {value:.2f} m shields windows from steep high-altitude solar radiation."
    elif "ventilation" in driver_name:
        return f"Ventilation rate of {value:.1f} ACH removes heat accumulations when outdoor temperatures drop."
    elif "roof_solar_absorptance" in driver_name:
        return f"Roof solar absorptance of {value:.2f} reflects a large portion of incident direct solar radiation."
    elif "orientation" in driver_name:
        return f"Building azimuth ({value:.0f}°) optimizes passive shading and aligns openings with prevailing winds."
    elif "wall_mass" in driver_name:
        return "Wall thermal mass dampens diurnal temperature oscillations, shifting peak heat loads to cooler night hours."
    else:
        return f"{driver_name.replace('_', ' ').title()} is a primary sensitivity driver in this climate envelope."

def apply_architectural_plot_style(ax, fig=None):
    """Applies clean architectural aesthetic to matplotlib axes."""
    if fig is not None:
        fig.patch.set_facecolor('#FFFFFF')
    ax.set_facecolor('#FFFFFF')
    ax.grid(True, linestyle='--', color='#E5E0D8', alpha=0.7, zorder=0)
    for spine in ax.spines.values():
        spine.set_color('#D4C7B0')
        spine.set_linewidth(1.0)
    ax.tick_params(colors='#3B4B5F', labelsize=9)
    ax.xaxis.label.set_color('#0F1B2B')
    ax.yaxis.label.set_color('#0F1B2B')
    ax.title.set_color('#0F1B2B')
    ax.title.set_weight('bold')

# -----------------------------------------------------------------------------
# 6. Cached Data Loaders (Strictly Read-Only on Saved Artifacts)
# -----------------------------------------------------------------------------
@st.cache_data
def load_reference_results():
    path = os.path.join(REPO_ROOT, "data/processed/reference_results.csv")
    return pd.read_csv(path) if os.path.exists(path) else pd.DataFrame()

@st.cache_data
def load_applicability_data():
    path = os.path.join(REPO_ROOT, "data/processed/applicability.csv")
    return pd.read_csv(path) if os.path.exists(path) else pd.DataFrame()

@st.cache_data
def load_pareto_front(city_name):
    path = os.path.join(REPO_ROOT, f"data/processed/pareto_{city_name}.parquet")
    if os.path.exists(path):
        df = pd.read_parquet(path)
        if 'pred_O1_ml' in df.columns and 'O1_ml' not in df.columns:
            df['O1_ml'] = df['pred_O1_ml']
        if 'pred_O1_adapt' in df.columns and 'O1_adapt' not in df.columns:
            df['O1_adapt'] = df['pred_O1_adapt']
        if 'pred_O2' in df.columns and 'O2' not in df.columns:
            df['O2'] = df['pred_O2']
        return df
    return pd.DataFrame()

@st.cache_data
def load_verified_results():
    path = os.path.join(REPO_ROOT, "data/processed/pareto_verification_results.csv")
    return pd.read_csv(path) if os.path.exists(path) else pd.DataFrame()

@st.cache_data
def load_s3_results():
    path = os.path.join(REPO_ROOT, "data/processed/s3_evaluation_results.csv")
    return pd.read_csv(path) if os.path.exists(path) else pd.DataFrame()

@st.cache_data
def load_surrogate_metrics():
    path = os.path.join(REPO_ROOT, "data/processed/surrogate_metrics.csv")
    return pd.read_csv(path) if os.path.exists(path) else pd.DataFrame()

@st.cache_data
def load_surrogate_shap_summary():
    path = os.path.join(REPO_ROOT, "data/processed/shap_surrogates_summary.csv")
    return pd.read_csv(path) if os.path.exists(path) else pd.DataFrame()

@st.cache_resource
def load_surrogate_model(city_name, target):
    path = os.path.join(REPO_ROOT, f"models/surrogate_{city_name}_{target}.joblib")
    if os.path.exists(path):
        obj = joblib.load(path)
        return obj['model'] if isinstance(obj, dict) and 'model' in obj else obj
    return None

# -----------------------------------------------------------------------------
# 7. Sidebar Navigation (Preserving Test Contracts)
# -----------------------------------------------------------------------------
with st.sidebar:
    st.markdown("### 🏛️ ClimateAdapt-Comfort")
    st.caption("Passive Shelter Decision-Support System")
    
    main_nav = st.radio(
        "Navigation",
        ["🏠 Get My Shelter Design", "🔬 Research Details"],
        index=0
    )
    
    st.markdown("---")
    st.markdown(
        "<div style='font-size:0.75rem; color:#64748B;'>"
        "<strong>Research Scope:</strong> Decision-support for passive shelter envelopes in India. "
        "Strictly local & free tools. Fixed seed: <code>42</code>."
        "</div>",
        unsafe_allow_html=True
    )

# =============================================================================
# DESTINATION 1: GUIDED QUESTIONNAIRE ("Get My Shelter Design")
# =============================================================================
if main_nav == "🏠 Get My Shelter Design":
    st.title("🏠 Get My Climate-Adapted Shelter Design")
    
    st.markdown(
        "<div class='arch-header'>"
        "<div class='arch-header-title'>Passive Shelter Recommendation System</div>"
        "<div class='arch-header-subtitle'>"
        "Tailor passive envelope strategies (insulation, window sizing, overhangs, natural ventilation) "
        "to Indian climate realities. Combines EnergyPlus physics simulations with validated surrogate models."
        "</div>"
        "</div>",
        unsafe_allow_html=True
    )

    st.subheader("1. Location & Climate Matching")
    col_loc, col_fb = st.columns([2, 1])
    with col_loc:
        location_input = st.text_input(
            "Shelter Location / Region",
            value="Jodhpur, Rajasthan",
            placeholder="e.g. Jodhpur, Mumbai, New Delhi, Bengaluru, Shimla, Jaipur, Pune...",
            help="Enter a town or city in India to automatically geocode and match to the nearest simulated climate station."
        )

    geo_res = geocode_location(location_input)
    if geo_res is not None:
        user_lat, user_lon, matched_place = geo_res
        matched_city, dist_km = find_nearest_simulated_city(user_lat, user_lon)
        st.markdown(
            f"<div class='arch-banner arch-banner-info'>"
            f"📍 <strong>Matched Geolocation:</strong> {matched_place} (<code>{user_lat:.3f}°N, {user_lon:.3f}°E</code>)<br>"
            f"Closest representative climate station: <strong>{matched_city.replace('_', ' ')}</strong> (<strong>{dist_km} km</strong> away)"
            f"</div>",
            unsafe_allow_html=True
        )
    else:
        with col_fb:
            fallback_city = st.selectbox(
                "Direct Climate Zone Selection",
                list(SIMULATED_CITIES_COORDS.keys()),
                index=0
            )
        matched_city = fallback_city
        dist_km = 0.0
        user_lat = SIMULATED_CITIES_COORDS[matched_city]["lat"]
        user_lon = SIMULATED_CITIES_COORDS[matched_city]["lon"]
        matched_place = SIMULATED_CITIES_COORDS[matched_city]["label"]
        st.markdown(
            f"<div class='arch-banner arch-banner-info'>"
            f"📍 Using direct station selection: <strong>{SIMULATED_CITIES_COORDS[matched_city]['label']}</strong>"
            f"</div>",
            unsafe_allow_html=True
        )

    city_info = SIMULATED_CITIES_COORDS[matched_city]
    conf_tier = city_info["confidence_tier"]

    if dist_km > 500.0:
        st.markdown(
            f"<div class='arch-banner arch-banner-warning'>"
            f"⚠️ <strong>Distance Caveat:</strong> This site is <strong>{dist_km:.0f} km</strong> from the nearest simulated EPW weather station ({matched_city}). "
            f"Local topography, microclimates, and elevation gradients may alter actual thermal performance."
            f"</div>",
            unsafe_allow_html=True
        )

    if conf_tier == "Medium":
        st.markdown(
            f"<div class='arch-banner arch-banner-success'>"
            f"✅ <strong>Confidence Tier: Medium</strong> &mdash; {city_info['confidence_reason']} "
            f"(Adaptive validity: {city_info['adaptive_validity']})."
            f"</div>",
            unsafe_allow_html=True
        )
    else:
        st.markdown(
            f"<div class='arch-banner arch-banner-warning'>"
            f"⚠️ <strong>Confidence Tier: Low</strong> &mdash; {city_info['confidence_reason']} "
            f"(Coverage: {city_info['envelope_coverage']})."
            f"</div>",
            unsafe_allow_html=True
        )

    # Render Live Outdoor Temperature Card
    render_live_weather_card(user_lat, user_lon, matched_place, key_suffix="get_shelter")

    st.markdown("---")
    st.subheader("2. Occupancy & Comfort Questionnaire")

    with st.form("shelter_questionnaire"):
        q_col1, q_col2 = st.columns(2)
        with q_col1:
            usually_feel = st.radio(
                "How do occupants typically feel inside existing local structures?",
                ["Too hot", "About right", "Too cold"],
                index=0,
                help="Shifts weight toward cooling or heating comfort models."
            )
            main_use = st.selectbox(
                "Primary shelter occupancy mode",
                ["Sleeping", "Working", "Cooking", "Mixed"],
                index=3
            )
            hours_occupied = st.slider(
                "Shelter occupied hours per day",
                min_value=1,
                max_value=24,
                value=24,
                step=1,
                help="Shelter typologies default to continuous 24h occupancy (Assumption A-001)."
            )
            has_fan_ac = st.radio(
                "Active cooling equipment available",
                ["None (100% Passive)", "Fan", "AC"],
                index=0
            )

        with q_col2:
            summer_clothing = st.selectbox(
                "Typical indoor summer clothing level",
                ["Light (shorts / light shirt)", "Normal (pants / t-shirt)", "Heavy (traditional layered)"],
                index=0
            )
            winter_clothing = st.selectbox(
                "Typical indoor winter clothing level",
                ["Light (light sweater)", "Normal (warm sweater / shawl)", "Heavy (thick jacket / quilt)"],
                index=1
            )
            priority = st.radio(
                "Top design priority",
                ["Comfort (maximize hours of comfort)", "Balanced (good comfort + lower energy)", "Low energy (minimize cooling/heating power)"],
                index=1
            )

        submitted = st.form_submit_button("🎯 Generate Recommended Shelter Design", use_container_width=True)

    # Process responses into weights
    priority_clean = "comfort" if "comfort" in priority.lower() else ("low energy" if "low" in priority.lower() else "balanced")
    feel_clean = "too hot" if "hot" in usually_feel.lower() else ("too cold" if "cold" in usually_feel.lower() else "about right")
    use_clean = main_use.lower()
    sum_clo_clean = "light" if "light" in summer_clothing.lower() else ("heavy" if "heavy" in summer_clothing.lower() else "normal")
    win_clo_clean = "light" if "light" in winter_clothing.lower() else ("heavy" if "heavy" in winter_clothing.lower() else "normal")
    cool_clean = "none" if "none" in has_fan_ac.lower() else ("fan" if "fan" in has_fan_ac.lower() else "AC")

    user_answers = {
        "priority": priority_clean,
        "usually_feel": feel_clean,
        "main_use": use_clean,
        "hours_occupied": hours_occupied,
        "summer_clothing": sum_clo_clean,
        "winter_clothing": win_clo_clean,
        "has_fan_ac": cool_clean
    }
    weights = map_answers_to_weights(user_answers)

    # Load Pareto Front & References
    df_pareto = load_pareto_front(matched_city)
    df_refs = load_reference_results()

    if not df_pareto.empty:
        min_ml, max_ml = df_pareto['O1_ml'].min(), df_pareto['O1_ml'].max()
        min_ad, max_ad = df_pareto['O1_adapt'].min(), df_pareto['O1_adapt'].max()
        min_o2, max_o2 = df_pareto['O2'].min(), df_pareto['O2'].max()

        ml_norm = (df_pareto['O1_ml'] - min_ml) / max(1e-5, max_ml - min_ml)
        ad_norm = (df_pareto['O1_adapt'] - min_ad) / max(1e-5, max_ad - min_ad)
        o2_norm = (df_pareto['O2'] - min_o2) / max(1e-5, max_o2 - min_o2)

        scores = (weights["O1_ml"] * ml_norm +
                  weights["O1_adapt"] * ad_norm +
                  weights["O2"] * o2_norm)
        best_row = df_pareto.loc[scores.idxmin()]

        r2_row = None
        if not df_refs.empty:
            r2_match = df_refs[(df_refs['city'] == matched_city) & (df_refs['reference_name'] == 'R2_Conventional')]
            if not r2_match.empty:
                r2_row = r2_match.iloc[0]

        st.markdown("---")
        st.subheader("3. Recommended Passive Shelter Specifications")

        roof_mm = int(round(best_row['roof_insulation_thickness'] * 1000))
        wall_mm = int(round(best_row['wall_insulation_thickness'] * 1000))
        wall_type = best_row['wall_mass_class'].capitalize()
        wwr_val = int(round(best_row['wwr'] * 100))
        orient_deg = int(round(best_row['orientation']))
        shading_val = round(best_row['shading_depth'], 2)
        vent_val = round(best_row['ventilation_ach'], 1)

        spec_c1, spec_c2 = st.columns(2)
        with spec_c1:
            st.markdown(
                f"<div class='arch-card'>"
                f"<h4 style='margin-top:0;'>Envelope & Thermal Mass</h4>"
                f"<p>🧱 <strong>Roof Insulation:</strong> <strong>{roof_mm} mm</strong></p>"
                f"<p>🧱 <strong>Wall Insulation:</strong> <strong>{wall_mm} mm</strong></p>"
                f"<p>🏗️ <strong>Wall Construction:</strong> <strong>{wall_type} mass</strong> "
                f"({'Clay Brick' if wall_type=='Medium' else ('Reinforced Concrete' if wall_type=='Heavy' else 'Lightweight Sheet')})</p>"
                f"<p>☀️ <strong>Roof Solar Absorptance:</strong> <strong>{best_row['roof_solar_absorptance']:.2f}</strong> (High reflectivity)</p>"
                f"</div>",
                unsafe_allow_html=True
            )
        with spec_c2:
            st.markdown(
                f"<div class='arch-card'>"
                f"<h4 style='margin-top:0;'>Openings & Shading</h4>"
                f"<p>🧭 <strong>Orientation:</strong> Facing <strong>{get_cardinal_direction(orient_deg)}</strong></p>"
                f"<p>🪟 <strong>Window Share (WWR):</strong> <strong>{wwr_val}%</strong> of wall area</p>"
                f"<p>☂️ <strong>Overhang Shading Depth:</strong> <strong>{shading_val} m</strong></p>"
                f"<p>💨 <strong>Natural Ventilation:</strong> <strong>{vent_val} ACH</strong></p>"
                f"</div>",
                unsafe_allow_html=True
            )

        st.markdown("#### Performance Compared to Standard Brick Shelter (R2 Baseline)")
        if r2_row is not None:
            pts_better = r2_row['O1_adapt'] - best_row['O1_adapt']
            pct_energy_saved = ((r2_row['O2'] - best_row['O2']) / max(1e-5, r2_row['O2'])) * 100.0

            c_m1, c_m2 = st.columns(2)
            with c_m1:
                st.metric(
                    "Comfort Improvement vs Standard Shelter",
                    f"{pts_better:+.1f} percentage points",
                    help="Percentage points reduction in uncomfortable indoor hours compared to an uninsulated brick shelter"
                )
            with c_m2:
                st.metric(
                    "Energy Savings vs Standard Shelter",
                    f"{pct_energy_saved:.1f}% less energy",
                    help="Percentage reduction in active heating and cooling energy demand"
                )

        st.markdown("---")
        st.subheader("💡 Why This Design Works (Top Sensitivity Drivers)")
        
        design_dict = {
            'roof_insulation_thickness': float(best_row['roof_insulation_thickness']),
            'wall_insulation_thickness': float(best_row['wall_insulation_thickness']),
            'roof_solar_absorptance': float(best_row['roof_solar_absorptance']),
            'wwr': float(best_row['wwr']),
            'orientation': float(best_row['orientation']),
            'shading_depth': float(best_row['shading_depth']),
            'ventilation_ach': float(best_row['ventilation_ach']),
            'wall_mass_class': str(best_row['wall_mass_class'])
        }

        try:
            drivers = get_top_drivers(matched_city, design_dict, target="O1_adapt", top_k=3)
            if drivers:
                for i, d in enumerate(drivers, 1):
                    feat = d['feature']
                    val = design_dict.get(feat, 0.0)
                    plain_reason = format_plain_shap_driver(feat, val if isinstance(val, (int, float)) else 0.0, matched_city)
                    st.markdown(f"**{i}. {plain_reason}**")
            else:
                st.markdown("- Insulation buffers the interior against seasonal outdoor temperature extremes.")
                st.markdown("- Shading and window sizing control solar radiation entering the living area.")
                st.markdown("- Natural ventilation flushes accumulated daytime heat during cooler evenings.")
        except Exception:
            st.markdown("- Overhead roof insulation blocks direct solar radiation through the ceiling.")
            st.markdown("- Exterior window overhangs prevent high summer sun from entering living areas.")
            st.markdown("- Natural ventilation rates purge heat at night to maintain comfort.")
    else:
        st.error(f"Pareto front data not found for {matched_city}.")

# =============================================================================
# DESTINATION 2: RESEARCH DETAILS (5 Core Research Sub-Pages)
# =============================================================================
else:
    st.sidebar.markdown("---")
    st.sidebar.subheader("Research Sections")
    
    res_subpage = st.sidebar.selectbox(
        "Select Research View",
        ["1. Overview", "2. Evaluate a Design", "3. Recommend", "4. Explain", "5. About"],
        index=0
    )
    
    city_selected = st.sidebar.selectbox(
        "Select Climate Station",
        list(SIMULATED_CITIES_COORDS.keys()),
        index=0
    )
    city_meta = SIMULATED_CITIES_COORDS[city_selected]
    
    st.sidebar.markdown(f"**Zone:** {city_meta['zone']}")
    st.sidebar.markdown(f"**Climate Class:** {city_meta['koppen']}")
    st.sidebar.caption(f"EPW Weather: `{city_meta['epw']}`")

    # -------------------------------------------------------------------------
    # RESEARCH SUBPAGE 1: OVERVIEW
    # -------------------------------------------------------------------------
    if res_subpage == "1. Overview":
        st.title("ClimateAdapt-Comfort: Research Overview")
        
        st.markdown(
            f"<div class='arch-header'>"
            f"<div class='arch-header-title'>Station: {city_selected} &mdash; {city_meta['zone']} Zone</div>"
            f"<div class='arch-header-subtitle'>"
            f"Köppen Climate Classification: <strong>{city_meta['koppen']}</strong> &bull; "
            f"EPW Source: <code>{city_meta['epw']}</code> &bull; "
            f"Confidence Tier: <span class='badge-tier {'badge-tier-medium' if city_meta['confidence_tier']=='Medium' else 'badge-tier-low'}'>{city_meta['confidence_tier']} Confidence</span>"
            f"</div>"
            f"</div>",
            unsafe_allow_html=True
        )

        # Prominent Applicability Domain Warning
        if "Shimla" in city_selected:
            st.markdown(
                f"<div class='arch-banner arch-banner-warning'>"
                f"⚠️ <strong>Applicability Domain Warning (Cold Zone - Shimla | D-011, D-015):</strong><br>"
                f"&bull; <strong>ML Comfort Model Extrapolation:</strong> DB II contains 0 labelled sensation votes for the Shimla building (460 rows, all TSV missing). Comfort predictions represent statistical extrapolation.<br>"
                f"&bull; <strong>Adaptive 90% Model Extrapolation:</strong> 26.03% of outdoor hourly running mean temperatures are below 10.0°C, operating outside ASHRAE 55 adaptive boundaries ({city_meta['adaptive_validity']})."
                f"</div>",
                unsafe_allow_html=True
            )
        elif "Jodhpur" in city_selected or "New_Delhi" in city_selected:
            st.markdown(
                f"<div class='arch-banner arch-banner-warning'>"
                f"⚠️ <strong>Applicability & Model Divergence Notice ({city_selected} | D-015, D-017):</strong><br>"
                f"&bull; <strong>Status:</strong> Low Confidence Tier. Extreme seasonal contrast between dry cold winters and scorching summers causes comfort judges to diverge.<br>"
                f"&bull; <strong>Adaptive Validity:</strong> {city_meta['adaptive_validity']} &bull; <strong>DB II Feature Coverage:</strong> {city_meta['envelope_coverage']}."
                f"</div>",
                unsafe_allow_html=True
            )
        else:
            st.markdown(
                f"<div class='arch-banner arch-banner-success'>"
                f"✅ <strong>Applicability Notice ({city_selected} | D-015, D-017):</strong><br>"
                f"&bull; <strong>Status:</strong> Medium Confidence Tier. Comfort models show strong directional agreement (Spearman <em>r</em><sub>s</sub> > 0.94) and 100% adaptive envelope validity.<br>"
                f"&bull; <strong>Coverage Note:</strong> {city_meta['envelope_coverage']}."
                f"</div>",
                unsafe_allow_html=True
            )

        st.markdown("---")
        
        # High-level summary metrics
        m_c1, m_c2, m_c3, m_c4 = st.columns(4)
        with m_c1:
            st.metric("Selected Station", city_selected, help="Simulated Indian station name")
        with m_c2:
            st.metric("Climate Classification", city_meta["zone"], help="Bureau of Indian Standards / NBC climate zone")
        with m_c3:
            st.metric("Adaptive 90% Validity", city_meta["adaptive_validity"].split()[0], help="Share of 8,760 annual hours with outdoor running mean between 10.0°C and 33.5°C")
        with m_c4:
            st.metric("Confidence Tier (D-017)", city_meta["confidence_tier"], help="Based on dual-judge rank agreement and adaptive validity share")

        # Live Weather Card for Climate Station
        render_live_weather_card(city_meta["lat"], city_meta["lon"], city_meta["label"], key_suffix="overview")

        st.subheader("1. Reference Shelter Baseline Benchmarks")
        st.markdown(
            "EnergyPlus baseline simulations for **R1 (Lightweight Shelter)** and **R2 (Conventional Clay Brick Shelter)**. "
            "Both reference models represent uninsulated shelters simulated under identical continuous occupancy and EPW conditions."
        )

        df_refs = load_reference_results()
        if not df_refs.empty:
            city_refs = df_refs[df_refs['city'] == city_selected].copy()
            display_cols = ['reference_name', 'wall_mass_class', 'roof_solar_absorptance', 'mean_ta', 'O1_ml', 'warm_ml', 'cool_ml', 'O1_adapt', 'O2']
            rename_dict = {
                'reference_name': 'Shelter Benchmark',
                'wall_mass_class': 'Wall Mass',
                'roof_solar_absorptance': 'Roof Absorptance',
                'mean_ta': 'Mean Ta (°C)',
                'O1_ml': 'O1 ML Discomfort (%)',
                'warm_ml': 'Warm ML (%)',
                'cool_ml': 'Cool ML (%)',
                'O1_adapt': 'O1 Adaptive 90% (%)',
                'O2': 'O2 Energy (kWh/m²/yr)'
            }
            styled_refs = city_refs[display_cols].rename(columns=rename_dict).set_index('Shelter Benchmark')
            st.dataframe(styled_refs.style.format({
                'Mean Ta (°C)': '{:.1f}',
                'O1 ML Discomfort (%)': '{:.1f}%',
                'Warm ML (%)': '{:.1f}%',
                'Cool ML (%)': '{:.1f}%',
                'O1 Adaptive 90% (%)': '{:.1f}%',
                'O2 Energy (kWh/m²/yr)': '{:.1f}'
            }), use_container_width=True)

        st.subheader("2. Applicability Domain & Decision Confidence Tiers (D-015, D-017)")
        st.markdown(
            "<div class='arch-banner arch-banner-info'>"
            "ℹ️ <strong>Empirical Feature Coverage Finding (D-015):</strong> Across all five climate zones, the ML Champion model operates below the 80% training envelope threshold (27.91% to 77.26% inside the DB II 1st–99th percentile feature envelope). "
            "Extrapolations are primarily triggered by intense monsoon relative humidity and arid desert saturation deficits."
            "</div>",
            unsafe_allow_html=True
        )

        conf_table = pd.DataFrame([
            {"City": "Mumbai", "Climate Zone": "Warm-Humid", "DB II Envelope Inside (%)": "27.91%", "Adaptive 90% Valid (%)": "100.00%", "Dual-Judge Spearman (rs)": "0.945", "Confidence Tier (D-017)": "Medium"},
            {"City": "Bengaluru", "Climate Zone": "Temperate", "DB II Envelope Inside (%)": "43.39%", "Adaptive 90% Valid (%)": "100.00%", "Dual-Judge Spearman (rs)": "0.943", "Confidence Tier (D-017)": "Medium"},
            {"City": "Shimla", "Climate Zone": "Cold", "DB II Envelope Inside (%)": "77.26%", "Adaptive 90% Valid (%)": "73.97%", "Dual-Judge Spearman (rs)": "0.868", "Confidence Tier (D-017)": "Low (Winter < 10°C)"},
            {"City": "New_Delhi", "Climate Zone": "Composite", "DB II Envelope Inside (%)": "53.12%", "Adaptive 90% Valid (%)": "89.86%", "Dual-Judge Spearman (rs)": "0.195", "Confidence Tier (D-017)": "Low (Judge Disagreement)"},
            {"City": "Jodhpur", "Climate Zone": "Hot-Dry", "DB II Envelope Inside (%)": "53.91%", "Adaptive 90% Valid (%)": "86.85%", "Dual-Judge Spearman (rs)": "0.109", "Confidence Tier (D-017)": "Low (Judge Disagreement)"}
        ])
        st.dataframe(conf_table.set_index("City"), use_container_width=True)

        df_app = load_applicability_data()
        if not df_app.empty:
            with st.expander("🔍 View Detailed Hourly Feature Envelope Breakdown (applicability.csv)"):
                st.dataframe(df_app.set_index("city"), use_container_width=True)

    # -------------------------------------------------------------------------
    # RESEARCH SUBPAGE 2: EVALUATE A DESIGN
    # -------------------------------------------------------------------------
    elif res_subpage == "2. Evaluate a Design":
        st.title("Evaluate a Custom Shelter Design")
        st.markdown(
            f"Explore interactive performance estimates for custom envelope and ventilation configurations in **{city_selected}** ({city_meta['zone']}). "
            "Evaluated instantly using 25 cross-validated XGBoost surrogate models trained on 7,483 valid EnergyPlus simulations."
        )

        st.subheader("1. Design Variables & Envelope Parameters")
        
        # Presets & Reset Control
        btn_c1, btn_c2, btn_c3 = st.columns([1, 1, 2])
        preset_choice = "custom"
        with btn_c1:
            if st.button("🔄 Reset to Default Spec"):
                st.session_state['eval_roof_ins'] = 100.0
                st.session_state['eval_wall_ins'] = 50.0
                st.session_state['eval_roof_abs'] = 0.60
                st.session_state['eval_wwr'] = 15.0
                st.session_state['eval_orient'] = 180.0
                st.session_state['eval_shading'] = 0.50
                st.session_state['eval_vent'] = 5.0
                st.session_state['eval_mass'] = "medium"
        with btn_c2:
            if st.button("🏛️ Reset to R2 Baseline"):
                st.session_state['eval_roof_ins'] = 0.0
                st.session_state['eval_wall_ins'] = 0.0
                st.session_state['eval_roof_abs'] = 0.60
                st.session_state['eval_wwr'] = 15.0
                st.session_state['eval_orient'] = 0.0
                st.session_state['eval_shading'] = 0.0
                st.session_state['eval_vent'] = 5.0
                st.session_state['eval_mass'] = "medium"

        # Initialize session state defaults if absent
        if 'eval_roof_ins' not in st.session_state:
            st.session_state['eval_roof_ins'] = 100.0
        if 'eval_wall_ins' not in st.session_state:
            st.session_state['eval_wall_ins'] = 50.0
        if 'eval_roof_abs' not in st.session_state:
            st.session_state['eval_roof_abs'] = 0.60
        if 'eval_wwr' not in st.session_state:
            st.session_state['eval_wwr'] = 15.0
        if 'eval_orient' not in st.session_state:
            st.session_state['eval_orient'] = 180.0
        if 'eval_shading' not in st.session_state:
            st.session_state['eval_shading'] = 0.50
        if 'eval_vent' not in st.session_state:
            st.session_state['eval_vent'] = 5.0
        if 'eval_mass' not in st.session_state:
            st.session_state['eval_mass'] = "medium"

        c1, c2, c3 = st.columns(3)
        with c1:
            st.markdown("#### Envelope & Insulation")
            roof_ins_mm = st.slider(
                "Roof Insulation Thickness (mm)",
                min_value=0.0, max_value=150.0,
                value=float(st.session_state['eval_roof_ins']),
                step=5.0,
                help="Thermal insulation (expanded polystyrene) applied to roof deck [0–150 mm]"
            )
            wall_ins_mm = st.slider(
                "Wall Insulation Thickness (mm)",
                min_value=0.0, max_value=150.0,
                value=float(st.session_state['eval_wall_ins']),
                step=5.0,
                help="Thermal insulation applied to exterior perimeter walls [0–150 mm]"
            )
            wall_mass_choice = st.selectbox(
                "Wall Construction Mass Class",
                ["medium", "light", "heavy"],
                index=["medium", "light", "heavy"].index(st.session_state['eval_mass']),
                help="Medium = 200 mm Clay Brick; Heavy = 200 mm Reinforced Concrete; Light = 50 mm Sheet/Board"
            )
            roof_abs = st.slider(
                "Roof Solar Absorptance",
                min_value=0.30, max_value=0.90,
                value=float(st.session_state['eval_roof_abs']),
                step=0.01,
                help="0.30 = white reflective cool roof; 0.90 = dark bitumen/metal roof"
            )

        with c2:
            st.markdown("#### Openings & Shading")
            wwr_pct = st.slider(
                "Window-to-Wall Ratio (WWR %)",
                min_value=5.0, max_value=40.0,
                value=float(st.session_state['eval_wwr']),
                step=1.0,
                help="Total window aperture area as a percentage of total exterior wall facade [5–40%]"
            )
            orientation_deg = st.slider(
                "Building Orientation (° from North)",
                min_value=0.0, max_value=359.0,
                value=float(st.session_state['eval_orient']),
                step=1.0,
                help="0° = North, 90° = East, 180° = South, 270° = West"
            )
            shading_m = st.slider(
                "Exterior Shading Overhang Depth (m)",
                min_value=0.0, max_value=1.0,
                value=float(st.session_state['eval_shading']),
                step=0.05,
                help="Horizontal projection depth of exterior window overhangs [0.0–1.0 m]"
            )

        with c3:
            st.markdown("#### Ventilation & Dynamics")
            vent_ach = st.slider(
                "Natural Ventilation Rate (ACH)",
                min_value=0.5, max_value=15.0,
                value=float(st.session_state['eval_vent']),
                step=0.5,
                help="Air changes per hour via operable windows and natural convection [0.5–15.0 ACH]"
            )
            st.markdown(
                "<div class='arch-card' style='margin-top:10px; font-size:0.82rem;'>"
                "<strong>Locked Assumptions (A-001–A-005):</strong><br>"
                "&bull; Occupancy: 24 h/day<br>"
                "&bull; Metabolic Rate: 1.1 met<br>"
                "&bull; Indoor Air Velocity: 0.15 m/s<br>"
                "&bull; Dynamic Clothing: 0.5/0.7/1.0 clo<br>"
                "&bull; Ideal Loads Setpoints: 26°C cooling, 20°C heating"
                "</div>",
                unsafe_allow_html=True
            )

        # Build feature vector for surrogate evaluation
        roof_ins_m = roof_ins_mm / 1000.0
        wall_ins_m = wall_ins_mm / 1000.0
        wwr_frac = wwr_pct / 100.0

        design_dict = {
            'roof_insulation_thickness': roof_ins_m,
            'wall_insulation_thickness': wall_ins_m,
            'roof_solar_absorptance': roof_abs,
            'wwr': wwr_frac,
            'orientation': orientation_deg,
            'shading_depth': shading_m,
            'ventilation_ach': vent_ach,
            'wall_mass_heavy': 1.0 if wall_mass_choice == 'heavy' else 0.0,
            'wall_mass_light': 1.0 if wall_mass_choice == 'light' else 0.0,
            'wall_mass_medium': 1.0 if wall_mass_choice == 'medium' else 0.0,
        }
        X_eval = pd.DataFrame([design_dict])

        # Load models and predict
        m_o1_ml = load_surrogate_model(city_selected, "O1_ml")
        m_warm_ml = load_surrogate_model(city_selected, "warm_ml")
        m_cool_ml = load_surrogate_model(city_selected, "cool_ml")
        m_o1_ad = load_surrogate_model(city_selected, "O1_adapt")
        m_o2 = load_surrogate_model(city_selected, "O2")

        pred_o1_ml = float(m_o1_ml.predict(X_eval)[0]) if m_o1_ml else np.nan
        pred_warm_ml = float(m_warm_ml.predict(X_eval)[0]) if m_warm_ml else np.nan
        pred_cool_ml = float(m_cool_ml.predict(X_eval)[0]) if m_cool_ml else np.nan
        pred_o1_ad = float(m_o1_ad.predict(X_eval)[0]) if m_o1_ad else np.nan
        pred_o2_raw = float(m_o2.predict(X_eval)[0]) if m_o2 else np.nan
        pred_o2 = max(0.0, pred_o2_raw) if not np.isnan(pred_o2_raw) else np.nan

        st.markdown("---")
        st.subheader("2. Predicted Multi-Objective Performance")

        # Load baseline for delta comparison
        df_refs = load_reference_results()
        r2_ref = None
        if not df_refs.empty:
            r2_match = df_refs[(df_refs['city'] == city_selected) & (df_refs['reference_name'] == 'R2_Conventional')]
            if not r2_match.empty:
                r2_ref = r2_match.iloc[0]

        delta_o1_ml = f"Δ {pred_o1_ml - r2_ref['O1_ml']:+.1f}% vs R2" if r2_ref is not None else None
        delta_o1_ad = f"Δ {pred_o1_ad - r2_ref['O1_adapt']:+.1f}% vs R2" if r2_ref is not None else None
        delta_o2 = f"Δ {pred_o2 - r2_ref['O2']:+.1f} vs R2" if r2_ref is not None else None

        col_m1, col_m2, col_m3 = st.columns(3)
        with col_m1:
            st.metric(
                "O1 ML Champion Discomfort",
                f"{pred_o1_ml:.1f}%",
                delta=delta_o1_ml,
                delta_color="inverse",
                help=f"Percentage of occupied hours non-neutral (Warm: {pred_warm_ml:.1f}%, Cool: {pred_cool_ml:.1f}%)"
            )
        with col_m2:
            st.metric(
                "O1 Adaptive 90% Discomfort",
                f"{pred_o1_ad:.1f}%",
                delta=delta_o1_ad,
                delta_color="inverse",
                help="Percentage of hours outside the ASHRAE 55 90% acceptability comfort band"
            )
        with col_m3:
            st.metric(
                "O2 Annual HVAC Energy",
                f"{pred_o2:.1f} kWh/m²/yr",
                delta=delta_o2,
                delta_color="inverse",
                help="Annual ideal-loads heating and cooling intensity (clipped at zero)"
            )

        if r2_ref is not None:
            comfort_gain = r2_ref['O1_adapt'] - pred_o1_ad
            energy_gain = ((r2_ref['O2'] - pred_o2) / max(1e-5, r2_ref['O2'])) * 100.0
            st.markdown(
                f"<div class='arch-banner arch-banner-info'>"
                f"📊 <strong>Comparison vs Standard Shelter (R2 Conventional):</strong> "
                f"This configuration achieves a <strong>{comfort_gain:+.1f} percentage point</strong> change in adaptive comfort "
                f"and <strong>{energy_gain:.1f}%</strong> change in active HVAC energy demand relative to an uninsulated clay brick shelter."
                f"</div>",
                unsafe_allow_html=True
            )

    # -------------------------------------------------------------------------
    # RESEARCH SUBPAGE 3: RECOMMEND (PARETO EXPLORER)
    # -------------------------------------------------------------------------
    elif res_subpage == "3. Recommend":
        st.title("Recommend: Multi-Objective Pareto Explorer")
        st.markdown(
            f"Explore the 100 non-dominated Pareto designs derived via NSGA-II optimization for **{city_selected}**. "
            "In multi-objective shelter design, no single configuration is universally optimal: "
            "designers must navigate trade-offs between natural ventilation, thermal mass, and active cooling requirements."
        )

        df_pareto = load_pareto_front(city_selected)
        df_verified = load_verified_results()
        df_refs = load_reference_results()

        if not df_pareto.empty:
            # Interactive Filter & Weighting Controls
            ctrl_c1, ctrl_c2 = st.columns([2, 1])
            with ctrl_c1:
                st.markdown("#### Objective Weighting Preferences")
                cw1, cw2, cw3 = st.columns(3)
                with cw1:
                    w1 = st.slider("Weight: O1 ML Discomfort", 0.0, 1.0, 0.33, 0.05)
                with cw2:
                    w2 = st.slider("Weight: O1 Adaptive Discomfort", 0.0, 1.0, 0.33, 0.05)
                with cw3:
                    w3 = st.slider("Weight: O2 HVAC Energy Demand", 0.0, 1.0, 0.34, 0.05)

            with ctrl_c2:
                st.markdown("#### Frontier Filters")
                mass_filter = st.selectbox(
                    "Filter by Wall Mass Class",
                    ["All Constructions", "Medium (Clay Brick)", "Heavy (Concrete)", "Light (Sheet)"],
                    index=0
                )

            w_sum = w1 + w2 + w3
            if w_sum > 0:
                w1, w2, w3 = w1 / w_sum, w2 / w_sum, w3 / w_sum

            # Filter data if requested
            filtered_pareto = df_pareto.copy()
            if mass_filter == "Medium (Clay Brick)":
                filtered_pareto = filtered_pareto[filtered_pareto['wall_mass_class'] == 'medium']
            elif mass_filter == "Heavy (Concrete)":
                filtered_pareto = filtered_pareto[filtered_pareto['wall_mass_class'] == 'heavy']
            elif mass_filter == "Light (Sheet)":
                filtered_pareto = filtered_pareto[filtered_pareto['wall_mass_class'] == 'light']

            if filtered_pareto.empty:
                filtered_pareto = df_pareto.copy()
                st.warning("No designs matched the filter; displaying full Pareto set.")

            # Compute normalized composite score
            o1_ml_norm = (filtered_pareto['O1_ml'] - df_pareto['O1_ml'].min()) / max(1e-5, df_pareto['O1_ml'].max() - df_pareto['O1_ml'].min())
            o1_ad_norm = (filtered_pareto['O1_adapt'] - df_pareto['O1_adapt'].min()) / max(1e-5, df_pareto['O1_adapt'].max() - df_pareto['O1_adapt'].min())
            o2_norm = (filtered_pareto['O2'] - df_pareto['O2'].min()) / max(1e-5, df_pareto['O2'].max() - df_pareto['O2'].min())

            filtered_pareto['composite_score'] = w1 * o1_ml_norm + w2 * o1_ad_norm + w3 * o2_norm
            best_design = filtered_pareto.loc[filtered_pareto['composite_score'].idxmin()]

            st.markdown(
                f"<div class='arch-banner arch-banner-success'>"
                f"🎯 <strong>Optimal Compromise Design ID:</strong> <code>{best_design['pareto_id']}</code> "
                f"&bull; Composite Score: <strong>{best_design['composite_score']:.3f}</strong> "
                f"&bull; Adaptive Discomfort: <strong>{best_design['O1_adapt']:.1f}%</strong> "
                f"&bull; ML Discomfort: <strong>{best_design['O1_ml']:.1f}%</strong> "
                f"&bull; Annual Energy: <strong>{best_design['O2']:.1f} kWh/m²</strong>"
                f"</div>",
                unsafe_allow_html=True
            )

            # Matplotlib Pareto Chart with Verified Designs & Baselines
            fig, ax = plt.subplots(figsize=(10, 5.2), dpi=120)
            apply_architectural_plot_style(ax, fig)

            sc = ax.scatter(
                df_pareto['O1_adapt'],
                df_pareto['O2'],
                c=df_pareto['O1_ml'],
                cmap='viridis',
                s=65,
                alpha=0.85,
                edgecolor='#0F1B2B',
                linewidth=0.5,
                label='Pareto Front (Surrogate Estimates)'
            )
            cbar = plt.colorbar(sc, ax=ax, pad=0.02)
            cbar.set_label('O1 ML Discomfort (%)', fontsize=9, color='#0F1B2B')
            cbar.ax.tick_params(labelsize=8, colors='#3B4B5F')

            # Overlay Reference Baselines (R1, R2)
            if not df_refs.empty:
                city_r = df_refs[df_refs['city'] == city_selected]
                for _, r in city_r.iterrows():
                    ax.scatter(
                        r['O1_adapt'], r['O2'],
                        s=170, marker='X', color='#C85A32', edgecolor='#0F1B2B', linewidth=1.2,
                        zorder=5, label=f"Baseline: {r['reference_name']}"
                    )

            # Overlay EnergyPlus Directly Verified Designs
            if not df_verified.empty:
                city_v = df_verified[df_verified['city'] == city_selected]
                if not city_v.empty:
                    ax.scatter(
                        city_v['actual_O1_adapt'], city_v['actual_O2'],
                        s=110, marker='D', facecolor='#FBBF24', edgecolor='#0F1B2B', linewidth=1.2,
                        zorder=6, label="Direct EnergyPlus Verified Points (10 runs)"
                    )

            # Highlight selected compromise point
            ax.scatter(
                best_design['O1_adapt'], best_design['O2'],
                s=240, marker='*', facecolor='#F59E0B', edgecolor='#0F1B2B', linewidth=1.5,
                zorder=7, label=f"Selected Compromise ({best_design['pareto_id']})"
            )

            ax.set_xlabel("O1 Adaptive 90% Discomfort (% of occupied hours)", fontsize=10, fontweight='bold')
            ax.set_ylabel("O2 Annual HVAC Energy Demand (kWh/m²/yr)", fontsize=10, fontweight='bold')
            ax.set_title(f"Pareto Trade-Off Frontier: Thermal Comfort vs Energy Intensity &mdash; {city_selected}", fontsize=11, pad=12)
            ax.legend(loc='upper right', fontsize=8, framealpha=0.92, facecolor='#FFFFFF', edgecolor='#D4C7B0')
            plt.tight_layout()
            st.pyplot(fig)

            st.caption(
                "Note: Colored circles represent 100 fast surrogate estimates evaluated across design space. "
                "Gold diamonds represent 10 representative designs re-simulated directly in EnergyPlus 26.2.0 to confirm physical accuracy (Success Criterion S3)."
            )

            # Detailed Specifications of Selected Design
            st.markdown("#### Selected Design Specifications")
            d_c1, d_c2, d_c3 = st.columns(3)
            with d_c1:
                st.markdown(
                    f"<div class='arch-card'>"
                    f"<strong>Envelope Insulation:</strong><br>"
                    f"&bull; Roof Insulation: <strong>{best_design['roof_insulation_thickness']*1000:.0f} mm</strong><br>"
                    f"&bull; Wall Insulation: <strong>{best_design['wall_insulation_thickness']*1000:.0f} mm</strong><br>"
                    f"&bull; Wall Mass: <strong>{best_design['wall_mass_class'].capitalize()}</strong>"
                    f"</div>",
                    unsafe_allow_html=True
                )
            with d_c2:
                st.markdown(
                    f"<div class='arch-card'>"
                    f"<strong>Solar & Fenestration:</strong><br>"
                    f"&bull; Roof Solar Absorptance: <strong>{best_design['roof_solar_absorptance']:.2f}</strong><br>"
                    f"&bull; Window-to-Wall Ratio: <strong>{best_design['wwr']*100:.0f}%</strong><br>"
                    f"&bull; Exterior Shading: <strong>{best_design['shading_depth']:.2f} m</strong>"
                    f"</div>",
                    unsafe_allow_html=True
                )
            with d_c3:
                st.markdown(
                    f"<div class='arch-card'>"
                    f"<strong>Dynamics & Siting:</strong><br>"
                    f"&bull; Orientation: <strong>{best_design['orientation']:.0f}°</strong> ({get_cardinal_direction(best_design['orientation'])})<br>"
                    f"&bull; Ventilation Rate: <strong>{best_design['ventilation_ach']:.1f} ACH</strong><br>"
                    f"&bull; Pareto ID: <code>{best_design['pareto_id']}</code>"
                    f"</div>",
                    unsafe_allow_html=True
                )

            st.subheader("Browse All 100 Pareto Frontier Solutions")
            st.dataframe(
                filtered_pareto.drop(columns=['composite_score'], errors='ignore'),
                use_container_width=True
            )

    # -------------------------------------------------------------------------
    # RESEARCH SUBPAGE 4: EXPLAIN (SHAP SENSITIVITY DRIVERS)
    # -------------------------------------------------------------------------
    elif res_subpage == "4. Explain":
        st.title("Explain: SHAP Attribution & Model Drivers")
        st.markdown(
            f"Inspect TreeExplainer feature attributions for surrogate and comfort models in **{city_selected}**. "
            "Attributions identify which building envelope parameters exert the greatest leverage on comfort and energy."
        )

        st.markdown(
            "<div class='arch-banner arch-banner-info'>"
            "🔍 <strong>Interpretability Notice:</strong> SHAP feature attributions describe statistical sensitivities within the trained surrogate model domain. "
            "They quantify relative input importance, but do not prove direct physical cause-and-effect or substitute for localized structural engineering."
            "</div>",
            unsafe_allow_html=True
        )

        st.subheader("1. Local Design Sensitivity Drivers")
        st.markdown("Examine the signed local feature impacts for a selected Pareto configuration:")

        df_pareto = load_pareto_front(city_selected)
        if not df_pareto.empty:
            sel_pareto_id = st.selectbox(
                "Choose Pareto Design ID to Explain",
                df_pareto['pareto_id'].tolist(),
                index=0
            )
            sel_row = df_pareto[df_pareto['pareto_id'] == sel_pareto_id].iloc[0]

            sample_design = {
                'roof_insulation_thickness': float(sel_row['roof_insulation_thickness']),
                'wall_insulation_thickness': float(sel_row['wall_insulation_thickness']),
                'roof_solar_absorptance': float(sel_row['roof_solar_absorptance']),
                'wwr': float(sel_row['wwr']),
                'orientation': float(sel_row['orientation']),
                'shading_depth': float(sel_row['shading_depth']),
                'ventilation_ach': float(sel_row['ventilation_ach']),
                'wall_mass_class': str(sel_row['wall_mass_class'])
            }

            target_to_explain = st.radio(
                "Target Objective to Attribute",
                ["O1_adapt", "O1_ml", "O2"],
                horizontal=True,
                help="O1_adapt = Adaptive Discomfort %; O1_ml = ML Sensation Discomfort %; O2 = HVAC Energy kWh/m²"
            )

            drivers = get_top_drivers(city_selected, sample_design, target=target_to_explain, top_k=6)

            driver_records = []
            for rank, d in enumerate(drivers, 1):
                feat = d['feature']
                clean_name = APP_FEATURE_NAME_MAP.get(feat, feat)
                val = sample_design.get(feat, 0.0)

                if "insulation" in feat:
                    val_str = f"{val * 1000:.1f} mm" if val < 1.0 else f"{val:.1f} mm"
                elif "wwr" in feat:
                    val_str = f"{val * 100:.1f}%"
                elif "orientation" in feat:
                    val_str = f"{val:.0f}°"
                elif isinstance(val, (int, float)):
                    val_str = f"{val:.2f}"
                else:
                    val_str = str(val)

                driver_records.append({
                    "Rank": rank,
                    "Design Variable": clean_name,
                    "Configured Value": val_str,
                    "SHAP Impact": f"{d['shap_value']:+.3f}",
                    "Mean |SHAP|": f"{d['abs_shap']:.4f}",
                    "Plain Architectural Explanation": format_plain_shap_driver(feat, val if isinstance(val, (int, float)) else 0.0, city_selected)
                })

            st.dataframe(pd.DataFrame(driver_records).set_index("Rank"), use_container_width=True)

        st.subheader("2. Global Surrogate Feature Importance")
        st.markdown(
            "Mean absolute SHAP attributions across the global surrogate test envelope, highlighting dominant physical drivers per target."
        )

        df_surr_summary = load_surrogate_shap_summary()
        if not df_surr_summary.empty:
            city_surr = df_surr_summary[df_surr_summary['city'] == city_selected]
            if not city_surr.empty:
                st.dataframe(
                    city_surr[['target', 'feature', 'mean_abs_shap', 'feature_name']].rename(columns={
                        'target': 'Target Objective',
                        'feature_name': 'Design Parameter',
                        'mean_abs_shap': 'Global Mean |SHAP|'
                    }),
                    use_container_width=True
                )

        # Technical Term Plain-Language Translation
        with st.expander("📖 Architectural Terms Glossary & Plain-Language Guide"):
            st.markdown("""
            - **Roof Solar Absorptance:** The fraction of solar radiation absorbed by the roof surface. Lower absorptance (e.g. 0.30) reflects incident sun, functioning as a 'cool roof'.
            - **Window-to-Wall Ratio (WWR):** Percentage of the facade covered by glazing. Lower WWR limits solar heat gain while preserving adequate daylight.
            - **Thermal Mass:** Heat storage capacity of the building walls. Heavy concrete or clay brick stores daytime heat and releases it slowly at night, dampening interior temperature swings.
            - **Ventilation (ACH):** Air changes per hour. Flushes warm indoor air during cooler evening and night hours.
            """)

    # -------------------------------------------------------------------------
    # RESEARCH SUBPAGE 5: ABOUT & AUDIT
    # -------------------------------------------------------------------------
    elif res_subpage == "5. About":
        st.title("About ClimateAdapt-Comfort & Research Audit")
        
        st.markdown(
            "<div class='arch-header'>"
            "<div class='arch-header-title'>Research Audit & Success Criteria Evaluation</div>"
            "<div class='arch-header-subtitle'>"
            "Complete empirical ledger, methodology notes, and verified criteria statuses for ClimateAdapt-Comfort v1.1."
            "</div>"
            "</div>",
            unsafe_allow_html=True
        )

        # Simulation Prototype Disclaimer
        st.markdown(
            "<div class='arch-banner arch-banner-warning'>"
            "⚠️ <strong>Important Research Disclosure & Prototype Status:</strong><br>"
            "All comfort ratings, energy demands, and design trade-offs presented in this system are derived from physics-based computer simulations (EnergyPlus 26.2.0) and empirical statistical models. "
            "<strong>No physical shelter prototypes have been constructed or monitored in the field for physical validation.</strong> "
            "This platform serves as a pre-construction decision-support exploratory tool, not a certified structural engineering approval authority."
            "</div>",
            unsafe_allow_html=True
        )

        st.subheader("1. Formal Success Criteria Ledger (S1 to S4)")
        st.markdown("All criteria evaluated against locked specifications and saved evidence files without modification:")

        s_table = pd.DataFrame([
            {
                "Criterion": "S1: ML Champion vs Adaptive Baseline",
                "Spec Target Threshold": "Macro-F1 lead >= +0.05 on identical rows under GroupKFold CV",
                "Empirical Result": "FAIL (Reported honestly as negative result)",
                "Literal Margin / Evidence": "ML Champion 0.4785 vs Adaptive 90% 0.4939 (Margin: -0.0154; E-012)",
                "Verified Status": "❌ S1 FAIL"
            },
            {
                "Criterion": "S2: Surrogate Model Accuracy",
                "Spec Target Threshold": "R² >= 0.95 on held-out test designs across all targets",
                "Empirical Result": "PARTIAL (23 of 25 models passed)",
                "Literal Margin / Evidence": "23/25 passed R² >= 0.95 (Failures: Mumbai O1_ml R²=0.9406, Shimla warm_ml R²=0.9225; Mean R² on O2 = 0.987; E-019)",
                "Verified Status": "⚠️ S2 PARTIAL"
            },
            {
                "Criterion": "S3: Direct EnergyPlus Optimization Verification",
                "Spec Target Threshold": "Verified Pareto design beats BOTH R1 & R2 on all 3 objectives via direct simulation",
                "Empirical Result": "PASS (Confirmed across all 5 climate zones)",
                "Literal Margin / Evidence": "Passed in all 5 cities (Jodhpur 7/10, Mumbai 7/10, New Delhi 6/10, Bengaluru 8/10, Shimla 8/10; 36/50 verified designs beat both; E-020)",
                "Verified Status": "✅ S3 PASS"
            },
            {
                "Criterion": "S4: Standalone Decision-Support Dashboard",
                "Spec Target Threshold": "Runs locally with 1 command, read-only on saved artifacts, zero external paid APIs",
                "Empirical Result": "PASS (Streamlit app with automated AppTest test suite)",
                "Literal Margin / Evidence": "Local-first architecture operating strictly read-only on processed parquet/csv files (E-021)",
                "Verified Status": "✅ S4 PASS"
            }
        ])
        st.dataframe(s_table.set_index("Criterion"), use_container_width=True)

        st.subheader("2. Dual Comfort Judges Side-by-Side Comparison")
        st.markdown(r"""
        | Comfort Judge | Formulation & Standard | Primary Strengths | Implementation Notes & Boundaries |
        |---|---|---|---|
        | **ML Champion (`Ablation_A3_OutdoorTemp`)** | Discrete argmax class $\hat{y}_t \in \{0=\text{cool}, 1=\text{neutral}, 2=\text{warm}\}$, evaluating $O_{1,\text{ml}} = \frac{100}{N}\sum \mathbf{1}(\hat{y}_t \ne 1)$ | Captures complex multi-variable interactions (radiant-air temperature deltas, humidity coupling) | Trained on global ASHRAE DB II; extrapolates in extreme monsoons and deserts. Uses discrete argmax prediction (`model.predict()`). |
        | **Physical Adaptive 90%** | $T_{\text{cmf}} = 17.8 + 0.31 T_{\text{rm}} \pm 2.5^\circ\text{C}$ on valid hours $10.0^\circ\text{C} \le T_{\text{rm}} \le 33.5^\circ\text{C}$ (ASHRAE Standard 55) | Grounded in empirical field adaptation physics; highly interpretable | Defined strictly for running mean $10.0^\circ\text{C} \le T_{\text{rm}} \le 33.5^\circ\text{C}$; invalid during cold mountain winters (Shimla). |
        """)

        st.subheader("3. Core Research Assumptions & Limitations")
        st.markdown("""
        - **DB II Representation:** ASHRAE DB II comprises primarily commercial offices and classrooms, with limited representation of emergency or rural informal shelters.
        - **Simulation-Based:** All energy and indoor conditions were modeled in EnergyPlus 26.2.0 under standardized TMYx weather files. Real-world air infiltration and thermal bridging will introduce variance.
        - **Cold-Zone Extrapolation:** Shimla indoor conditions frequently fall below the 10°C lower boundary of the ASHRAE adaptive model, requiring careful interpretation of winter discomfort.
        """)

# -----------------------------------------------------------------------------
# 8. Institutional Footer
# -----------------------------------------------------------------------------
st.markdown("---")
st.markdown(
    "<div style='text-align:center; font-size:0.80rem; color:#64748B; padding:10px 0;'>"
    "<strong>ClimateAdapt-Comfort</strong> &bull; Multi-Objective Passive Shelter Decision-Support System &bull; "
    "Fixed Seed: <code>42</code> &bull; Local-First Read-Only Architecture"
    "</div>",
    unsafe_allow_html=True
)
