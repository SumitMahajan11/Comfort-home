import { CityInfo, CityKey, DesignVariables } from "../types";

export const CITIES_DATA: Record<CityKey, CityInfo> = {
  Jodhpur: {
    key: "Jodhpur",
    name: "Jodhpur",
    zone: "Hot-Dry (BWh)",
    climateCode: "BWh",
    epw: "IND_RJ_Jodhpur.423390_TMYx.epw",
    confidence: "Low",
    spearman: 0.109,
    coordinates: [26.2389, 73.0243],
    description: "Thar desert edge with extreme daytime solar radiation, high summer peak temperatures exceeding 42°C, and significant diurnal temperature swings.",
    elevation: "224 m",
    envelopeAlert: "Low dual-judge rank agreement (Spearman rs = 0.109). High extreme heat periods push conditions toward boundary of training data."
  },
  Mumbai: {
    key: "Mumbai",
    name: "Mumbai",
    zone: "Warm-Humid (Aw)",
    climateCode: "Aw",
    epw: "IND_MH_Mumbai-Shivaji.Intl.AP.430030_TMYx.epw",
    confidence: "Medium",
    spearman: 0.945,
    coordinates: [19.0760, 72.8777],
    description: "Coastal tropical savanna with high persistent humidity (>70% RH), moderate diurnal range, and heavy southwest monsoon seasons.",
    elevation: "14 m",
    envelopeAlert: "Monsoon relative humidity exceeds 99th percentile DB II training distribution during peak rain months (27.9% overall envelope)."
  },
  New_Delhi: {
    key: "New_Delhi",
    name: "New Delhi",
    zone: "Composite (Cwa)",
    climateCode: "Cwa",
    epw: "IND_DL_New.Delhi-Gandhi.Intl.AP.421810_TMYx.epw",
    confidence: "Low",
    spearman: 0.195,
    coordinates: [28.6139, 77.2090],
    description: "Northern plains continental composite climate characterized by scorching dry pre-monsoon heat, humid monsoons, and chilly winter nights (<8°C).",
    elevation: "216 m",
    envelopeAlert: "Dual-judge rank divergence (Spearman rs = 0.195) due to severe seasonal swing between winter heating and summer cooling regimes."
  },
  Bengaluru: {
    key: "Bengaluru",
    name: "Bengaluru",
    zone: "Temperate (Aw/Cwb)",
    climateCode: "Cwb/Aw",
    epw: "IND_KA_Bengaluru-Hindustan.AP.432960_TMYx.epw",
    confidence: "Medium",
    spearman: 0.943,
    coordinates: [12.9716, 77.5946],
    description: "Deccan plateau elevation tempering equatorial climate with mild pleasant temperatures year-round and moderate diurnal cooling.",
    elevation: "920 m",
    envelopeAlert: "Strongest dual-judge agreement (Spearman rs = 0.943) with 100% Adaptive 90% validity share."
  },
  Shimla: {
    key: "Shimla",
    name: "Shimla",
    zone: "Cold (Cwb)",
    climateCode: "Cwb",
    epw: "IND_HP_Shimla.420830_TMYx.epw",
    confidence: "Low",
    spearman: 0.868,
    coordinates: [31.1048, 77.1734],
    description: "Himalayan montane altitude with freezing sub-zero winter temperatures, snowfall, and heating-dominated annual discomfort hours.",
    elevation: "2,205 m",
    envelopeAlert: "EXTRAPOLATION REGIME: 460 DB II records in Shimla lacked TSV sensation votes; only 73.97% of hours are valid for Adaptive 90% (winter outdoor temperatures drop below 10°C boundary)."
  }
};

export const DEFAULT_DESIGN: DesignVariables = {
  roof_insulation_thickness: 75,
  wall_insulation_thickness: 50,
  wall_mass_class: "medium",
  roof_solar_absorptance: 0.40,
  wwr: 15,
  orientation: 0,
  shading_depth: 0.5,
  ventilation_ach: 6.0
};

export const COLOR_PALETTE = {
  bg: "var(--bg)",
  surface: "var(--surface)",
  surface2: "var(--surface-2)",
  line: "var(--line)",
  ink: "var(--ink)",
  ink2: "var(--ink-2)",
  primary: "var(--primary)",
  link: "var(--link)",
  good: "var(--good)",
  warn: "var(--warn)",
  bad: "var(--bad)",
  cool: "var(--cool)",
  hot: "var(--hot)"
};

export const PIPELINE_CONSTANTS = {
  ENERGYPLUS_VERSION: "26.2.0",
  SEED: 42,
  TOTAL_SIMULATIONS: 10000,
  TOTAL_SURVEY_VOTES: 109033,
  COMPLETE_CASES: 58512
};


