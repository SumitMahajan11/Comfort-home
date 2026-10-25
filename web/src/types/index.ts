export type CityKey = "Jodhpur" | "Mumbai" | "New_Delhi" | "Bengaluru" | "Shimla";

export type ConfidenceTier = "Medium" | "Low";

export interface CityInfo {
  key: CityKey;
  name: string;
  zone: string;
  climateCode: string;
  epw: string;
  confidence: ConfidenceTier;
  spearman: number;
  coordinates: [number, number]; // [lat, lng]
  description: string;
  elevation: string;
  envelopeAlert?: string;
}

export interface ApplicabilityData {
  city: CityKey;
  display_name: string;
  zone: string;
  confidence: ConfidenceTier;
  spearman: number;
  coordinates: [number, number];
  n_hourly_samples: number;
  ta_in_envelope_pct: number;
  tr_in_envelope_pct: number;
  rh_in_envelope_pct: number;
  vel_in_envelope_pct: number;
  clo_in_envelope_pct: number;
  met_in_envelope_pct: number;
  t_mot_isd_in_envelope_pct: number;
  all_features_in_envelope_pct: number;
  adaptive_90_valid_pct: number;
  ml_flagged_under_80pct: boolean;
  adaptive_flagged_under_80pct: boolean;
}

export interface SurrogateMetric {
  city: CityKey;
  target: "O1_ml" | "warm_ml" | "cool_ml" | "O1_adapt" | "O2";
  r2: number;
  mae: number;
  nmae_pct: number;
  top10_overlap_pct: number;
  n_samples: number;
  passes_spec: boolean;
}

export interface ReferenceShelter {
  city: CityKey;
  reference_name: "R1_Lightweight" | "R2_Conventional";
  roof_insulation_thickness: number;
  wall_insulation_thickness: number;
  wall_mass_class: "light" | "medium" | "heavy";
  roof_solar_absorptance: number;
  wwr: number;
  orientation: number;
  shading_depth: number;
  ventilation_ach: number;
  mean_ta: number;
  max_ta: number;
  min_ta: number;
  mean_tr: number;
  O1_ml: number;
  warm_ml: number;
  cool_ml: number;
  O1_adapt: number;
  hot_adapt: number;
  cold_adapt: number;
  invalid_share_adapt: number;
  O2: number;
}

export interface ParetoDesign {
  pareto_id: string;
  city: CityKey;
  roof_insulation_thickness: number;
  wall_insulation_thickness: number;
  wall_mass_class: "light" | "medium" | "heavy";
  roof_solar_absorptance: number;
  wwr: number;
  orientation: number;
  shading_depth: number;
  ventilation_ach: number;
  O1_ml: number;
  warm_ml?: number;
  cool_ml?: number;
  O1_adapt: number;
  hot_adapt?: number;
  cold_adapt?: number;
  O2: number;
  is_verified?: boolean;
  verified_O1_ml?: number;
  verified_O1_adapt?: number;
  verified_O2?: number;
  rel_error_O1_ml?: number;
  rel_error_O1_adapt?: number;
  rel_error_O2?: number;
  composite_score?: number;
  preset_tag?: "Lowest Energy" | "Lowest Discomfort" | "Balanced (Knee Point)";
}

export interface S3Result {
  city: CityKey;
  s3_status: "PASS" | "FAIL";
  n_designs_beating_both: number;
  best_pareto_id: string;
  ref_min_O1_ml: number;
  ref_min_O1_adapt: number;
  ref_min_O2: number;
  margin_O1_ml_pct: number;
  margin_O1_adapt_pct: number;
  margin_O2_kwh_per_m2: number;
}

export interface DesignVariables {
  roof_insulation_thickness: number; // 0 - 150 mm
  wall_insulation_thickness: number; // 0 - 150 mm
  wall_mass_class: "light" | "medium" | "heavy";
  roof_solar_absorptance: number;   // 0.3 - 0.9
  wwr: number;                      // 5 - 40 %
  orientation: number;              // 0 - 359 deg
  shading_depth: number;            // 0.0 - 1.0 m
  ventilation_ach: number;          // 1.0 - 15.0 ACH
}

export interface PredictionResult {
  O1_ml: number;
  warm_ml: number;
  cool_ml: number;
  O1_adapt: number;
  O2: number;
  confidence: ConfidenceTier;
  confidenceNote: string;
  r2_O1_ml: number;
  r2_O2: number;
  r2_O1_adapt: number;
}

export interface SuccessCriterion {
  id: "S1" | "S2" | "S3" | "S4";
  name: string;
  threshold: string;
  status: "PASS" | "PARTIAL" | "FAIL";
  evidence: string;
  explanation: string;
  ml_score?: number;
  baseline_score?: number;
  margin?: number;
  passing_models?: number;
  total_models?: number;
  mean_o2_r2?: number;
  passing_cities?: number;
  total_cities?: number;
  verified_beating_both?: string;
}

export interface ProjectMetadata {
  kpis: {
    survey_records: number;
    clean_complete_case: number;
    total_simulations: number;
    valid_paired_designs: number;
    surrogate_models: number;
    pareto_designs: number;
    verified_in_energyplus: number;
  };
  success_criteria: SuccessCriterion[];
  assumptions: { id: string; name: string; value: string }[];
  decisions: { id: string; title: string; description: string }[];
  design_variables: {
    id: string;
    name: string;
    unit: string;
    min?: number;
    max?: number;
    step?: number;
    default: any;
    options?: string[];
    description: string;
  }[];
}

// ==========================================
// ClimateAdapt-Comfort v2 Types
// ==========================================

export type BuildingType = "house" | "apartment" | "commercial";
export type UserFeel = "too hot" | "about right" | "too cold";
export type CoolingType = "none" | "fan" | "AC";
export type ClothingType = "light" | "normal" | "heavy";
export type UserPriority = "comfort" | "balanced" | "low energy";
export type LanguageCode = "en" | "hi";

export interface CostRangeBreakdown {
  roof_insulation_inr: number;
  wall_insulation_inr: number;
  cool_roof_coating_inr: number;
  shading_louvers_inr: number;
  window_glazing_inr: number;
}

export interface CostRangeEstimate {
  total_envelope_cost_inr: {
    min: number;
    max: number;
    central: number;
  };
  cost_per_m2_carpet: {
    min: number;
    max: number;
    central: number;
  };
  breakdown: CostRangeBreakdown;
  schedule_source: string;
  notes: string;
}

export interface MonthlyPerformanceData {
  months: string[];
  outdoor_ta: number[];
  indoor_ta_baseline_r2: number[];
  indoor_ta_recommended: number[];
}

export interface PassivePackage {
  id: "pkg_budget" | "pkg_balanced" | "pkg_best_comfort";
  name: string;
  description: string;
  pareto_id: string;
  comfort_fit_score: number;
  comfort_gain_vs_baseline_pts: number;
  energy_reduction_pct: number;
  discomfort_pct: number;
  ml_discomfort_pct: number;
  annual_energy_kwh_per_m2: number;
  design_variables: {
    roof_insulation_thickness: number;
    wall_insulation_thickness: number;
    roof_solar_absorptance: number;
    wwr: number;
    orientation: number;
    shading_depth: number;
    ventilation_ach: number;
    wall_mass_class: "light" | "medium" | "heavy";
  };
  materials_list: string[];
  cost_range: CostRangeEstimate;
  monthly_performance: MonthlyPerformanceData;
}

export interface CityAreaAverages {
  usually_feel: string;
  hours_occupied: string;
  cooling_available: string;
  clothing_summer: string;
}

export interface LocationMatchResponse {
  searched_query: string;
  matched_city_key: CityKey;
  matched_city_name: string;
  climate_zone: string;
  confidence_tier: ConfidenceTier;
  distance_km: number;
  is_direct_station: boolean;
  nearest_match_notice: string | null;
  disclaimer: string;
}

export interface EvaluationPackagesResponse {
  city: CityKey;
  building_type: BuildingType;
  climate_zone: string;
  confidence_tier: ConfidenceTier;
  confidence_reason: string;
  adaptive_validity: string;
  future_climate_applied: boolean;
  packages: {
    budget: PassivePackage;
    balanced: PassivePackage;
    best_comfort: PassivePackage;
  };
  area_average: CityAreaAverages;
  user_comparison: {
    user_feel: string;
    area_feel: string;
    user_occupied_hours: number;
    area_occupied_hours: string;
    user_cooling: string;
    area_cooling: string;
  };
  disclaimer: string;
  cost_disclaimer: string;
}

