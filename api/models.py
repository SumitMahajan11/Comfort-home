"""
api/models.py

Pydantic v2 data models for request validation and typed API responses.
Includes explicit schema examples, cross-cutting metadata, and strict null gating.
"""

from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field, ConfigDict

# -----------------------------------------------------------------------------
# Cross-Cutting Base Metadata
# -----------------------------------------------------------------------------
class BaseResponse(BaseModel):
    confidence_tier: str = Field(..., description="Decision confidence tier: High, Medium, or Low")
    applicability: Dict[str, Any] = Field(..., description="DB II training envelope and adaptive validity metrics")
    verification_status: str = Field(..., description="Verification level: verified, light verification, or estimated")
    limitations: List[str] = Field(..., description="List of methodological and simulation limitations")
    data_version: str = Field(..., description="Cryptographic SHA256 checksum of data/export/manifest.json")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "confidence_tier": "Medium",
                "applicability": {
                    "db2_envelope_pct": 66.8,
                    "adaptive_validity": 100.0
                },
                "verification_status": "verified",
                "limitations": [
                    "Simulation-based estimate using EnergyPlus 26.2.0; not a construction quote."
                ],
                "data_version": "0cae9daf6788abf6f685785ba935580d7faf1b105ee4d0def6f504c098f27b35"
            }
        }
    )

# -----------------------------------------------------------------------------
# City & Match Models
# -----------------------------------------------------------------------------
class CitySummary(BaseModel):
    city: str = Field(..., example="Jodhpur")
    display_name: str = Field(..., example="Jodhpur")
    zone: str = Field(..., example="Hot-dry")
    koppen: str = Field(..., example="BWh")
    epw: str = Field(..., example="IND_RJ_Jodhpur.423390_TMYx.epw")
    coordinates: List[float] = Field(..., example=[26.2389, 73.0243])
    confidence_tier: str = Field(..., example="Low")
    confidence_reason: str = Field(..., example="Dual-judge disagreement 18.6 pts, high DB II envelope deviation")
    adaptive_validity: float = Field(..., example=98.4)
    db2_envelope_pct: float = Field(..., example=68.4)

class CitiesResponse(BaseResponse):
    cities: List[CitySummary]
    allowed_cities: List[str]

class MatchResponse(BaseResponse):
    query: str = Field(..., example="Jaipur")
    matched_city: str = Field(..., example="Jodhpur")
    distance_km: float = Field(..., example=280.4)
    is_nearest_match: bool = Field(True, example=True)
    exceeds_threshold: bool = Field(False, example=False)
    strong_warning: Optional[str] = Field(None, example=None)
    city_info: CitySummary

# -----------------------------------------------------------------------------
# Climate Models
# -----------------------------------------------------------------------------
class MonthlyClimateItem(BaseModel):
    month_index: int = Field(..., example=1)
    month_name: str = Field(..., example="Jan")
    dry_bulb_mean: float = Field(..., example=16.7)
    dry_bulb_min: float = Field(..., example=7.3)
    dry_bulb_max: float = Field(..., example=27.4)
    relative_humidity_mean: float = Field(..., example=44.9)
    adaptive_90_valid_pct: float = Field(..., example=100.0)
    outdoor_comfortable_pct: float = Field(..., example=27.0)
    outdoor_too_warm_pct: float = Field(..., example=3.4)
    outdoor_too_cool_pct: float = Field(..., example=69.6)

class CityClimateResponse(BaseResponse):
    city: str = Field(..., example="Jodhpur")
    current: List[MonthlyClimateItem]
    plus1p5: List[MonthlyClimateItem]
    plus3p0: List[MonthlyClimateItem]

class CityComfortNormsResponse(BaseResponse):
    city: str = Field(..., example="Jodhpur")
    building_type: str = Field(..., example="house")
    monthly_climate_summary: List[Dict[str, Any]]
    reference_building_performance: Dict[str, Any]
    occupant_preferences_db2: Dict[str, Any]
    has_labelled_votes: bool = Field(..., example=True)

# -----------------------------------------------------------------------------
# Questionnaire & Profile Models
# -----------------------------------------------------------------------------
class QuestionnaireSchemaResponse(BaseResponse):
    language: str = Field(..., example="en")
    title: str = Field(..., example="Occupant Thermal Comfort Profile")
    description: str = Field(..., example="Tailors candidate designs to your sensitivity and daily occupancy.")
    questions: List[Dict[str, Any]]

class ProfileEvaluationRequest(BaseModel):
    building_type: str = Field("house", example="house")
    city: str = Field("Jodhpur", example="Jodhpur")
    scenario: str = Field("current", example="current")
    answers: Dict[str, Any] = Field(
        default_factory=lambda: {
            "usually_feel_summer": "warm",
            "sensitivity": "heat_sensitive",
            "priority": {"comfort": 60, "energy": 25, "cost": 15}
        },
        example={
            "usually_feel_summer": "warm",
            "usually_feel_winter": "neutral",
            "sensitivity": "heat_sensitive",
            "priority": {"comfort": 60, "energy": 25, "cost": 15}
        }
    )

class FitScoreResult(BaseModel):
    overall_fit_score: float = Field(..., example=78.6)
    comfort_subscore: float = Field(..., example=75.3)
    energy_subscore: float = Field(..., example=91.7)
    cost_subscore: float = Field(..., example=70.0)
    comfort_gain_points: float = Field(..., example=32.9)
    discomfort_reduction_pct: float = Field(..., example=30.9)
    dual_judge: Dict[str, Any] = Field(..., example={"ml_champion_o1": 10.5, "adaptive_90_o1": 29.1, "disagreement_pts": 18.6})
    explanation_en: str
    explanation_hi: str

class ProfileEvaluationResponse(BaseResponse):
    city: str = Field(..., example="Jodhpur")
    building_type: str = Field(..., example="house")
    scenario: str = Field(..., example="current")
    user_profile_summary: Dict[str, Any]
    typical_local_building: FitScoreResult
    packages: Dict[str, FitScoreResult]

# -----------------------------------------------------------------------------
# Cost & Package Models
# -----------------------------------------------------------------------------
class CostRangeModel(BaseModel):
    low_inr: Optional[float] = Field(None, example=None)
    high_inr: Optional[float] = Field(None, example=None)
    status: str = Field("UNAVAILABLE", example="UNAVAILABLE")
    reason: Optional[str] = Field("Rates unpopulated in official DSR schedule", example="Rates unpopulated in official DSR schedule")
    dsr_edition: Optional[str] = Field("CPWD DSR 2021", example="CPWD DSR 2021")
    disclaimer: str = Field(
        "Estimate for early decisions, never a quote.",
        example="Estimate for early decisions, never a quote."
    )

class PackageModel(BaseModel):
    package_key: str = Field(..., example="balanced")
    package_name: str = Field(..., example="Balanced Comfort & Cost")
    design_id: str = Field(..., example="P_Jodhpur_house_063")
    verification_status: str = Field(..., example="verified")
    design_variables: Dict[str, Any]
    objectives: Dict[str, Any]
    cost_range: CostRangeModel
    carbon: Dict[str, Any]
    payback_years: Optional[float] = Field(None, example=None)
    bom: List[Dict[str, Any]]
    monthly_series: List[Dict[str, Any]]

class PackagesResponse(BaseResponse):
    city: str = Field(..., example="Jodhpur")
    building_type: str = Field(..., example="house")
    scenario: str = Field(..., example="current")
    packages: Dict[str, PackageModel]

# -----------------------------------------------------------------------------
# Pareto Models
# -----------------------------------------------------------------------------
class ParetoDesign(BaseModel):
    pareto_id: str = Field(..., example="P_Jodhpur_house_001")
    city: str = Field(..., example="Jodhpur")
    building_type: str = Field(..., example="house")
    roof_insulation_thickness: float = Field(..., example=0.10)
    wall_insulation_thickness: float = Field(..., example=0.05)
    roof_solar_absorptance: float = Field(..., example=0.35)
    wwr: float = Field(..., example=0.15)
    orientation: float = Field(..., example=180.0)
    shading_depth: float = Field(..., example=0.6)
    ventilation_ach: float = Field(..., example=10.0)
    wall_mass_class: str = Field(..., example="medium")
    floor_position: Optional[str] = Field(None, example=None)
    O1_ml: float = Field(..., example=18.4)
    O1_adapt: float = Field(..., example=22.1)
    O2: float = Field(..., example=42.5)
    warm_ml: float = Field(..., example=15.2)
    cool_ml: float = Field(..., example=3.2)
    verified: bool = Field(..., example=True)
    verification_mode: str = Field(..., example="fully verified")

class ParetoDesignsResponse(BaseResponse):
    city: str = Field(..., example="Jodhpur")
    building_type: str = Field(..., example="house")
    total_count: int = Field(..., example=100)
    page: int = Field(..., example=1)
    page_size: int = Field(..., example=20)
    designs: List[ParetoDesign]

# -----------------------------------------------------------------------------
# Explain & Model Lab Models
# -----------------------------------------------------------------------------
class DesignExplainResponse(BaseResponse):
    design_id: str = Field(..., example="P_Jodhpur_house_063")
    city: str = Field(..., example="Jodhpur")
    building_type: str = Field(..., example="house")
    top_drivers: List[Dict[str, Any]]
    sentences_en: List[str]
    sentences_hi: List[str]

class ModelLabResponse(BaseResponse):
    scorecard_s1_s4: Dict[str, Any]
    comfort_model_leaderboard: List[Dict[str, Any]]
    surrogate_matrices: Dict[str, Any]
    phase_timeline: List[Dict[str, Any]]

# -----------------------------------------------------------------------------
# PDF Export Model
# -----------------------------------------------------------------------------
class PDFExportRequest(BaseModel):
    package_data: Dict[str, Any] = Field(..., description="Package details from GET /packages")
    profile: Optional[Dict[str, Any]] = Field(None, description="User comfort profile answers")
    language: Optional[str] = Field("en", description="Language: 'en' or 'hi'")
    project_title: Optional[str] = Field("Passive Climate Design Specification", description="Title in PDF header")
