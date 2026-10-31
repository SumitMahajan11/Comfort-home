/**
 * web/src/lib/api.ts
 * 
 * ClimateAdapt-Comfort v2 API Client.
 * Connects to the local FastAPI backend (http://localhost:8000),
 * with robust, deterministic client-side fallback using precomputed repository artifacts.
 * 
 * ZERO LIVE ENERGYPLUS RUNS.
 * STRICT HONESTY & EVIDENCE TRACEABILITY.
 */

import {
  CityKey,
  BuildingType,
  UserFeel,
  CoolingType,
  ClothingType,
  UserPriority,
  LocationMatchResponse,
  EvaluationPackagesResponse,
  PassivePackage,
  CostRangeEstimate
} from "@/types";
import { CITIES_DATA } from "./constants";
import { getCityApplicability, getCityBaselines } from "./metrics";

// Static reference baselines from data/processed/reference_results.csv
import paretoJodhpur from "@/data/pareto_Jodhpur.json";
import paretoMumbai from "@/data/pareto_Mumbai.json";
import paretoDelhi from "@/data/pareto_New_Delhi.json";
import paretoBengaluru from "@/data/pareto_Bengaluru.json";
import paretoShimla from "@/data/pareto_Shimla.json";
import geometryData from "@/data/geometry.json";
import cityComfortNorms from "@/data/city_comfort_norms.json";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "";

const PARETO_BY_CITY: Record<CityKey, any[]> = {
  Jodhpur: paretoJodhpur,
  Mumbai: paretoMumbai,
  New_Delhi: paretoDelhi,
  Bengaluru: paretoBengaluru,
  Shimla: paretoShimla
};

const MONTH_NAMES = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];

const MONTHLY_OUTDOOR_TA: Record<CityKey, number[]> = {
  Jodhpur: [16.8, 20.4, 26.1, 31.8, 35.4, 34.6, 31.5, 29.8, 30.2, 28.1, 22.9, 17.9],
  Mumbai: [24.2, 24.8, 26.9, 28.8, 30.4, 29.2, 27.9, 27.5, 27.8, 28.4, 27.3, 25.4],
  New_Delhi: [14.1, 17.6, 23.4, 30.1, 34.2, 33.8, 30.6, 29.8, 29.1, 25.8, 20.2, 15.2],
  Bengaluru: [20.9, 23.2, 26.1, 27.6, 27.1, 24.5, 23.6, 23.5, 23.7, 23.6, 22.2, 20.8],
  Shimla: [5.6, 7.2, 11.4, 16.1, 19.5, 20.2, 18.9, 18.4, 17.1, 14.2, 10.8, 7.6]
};

function getCityComfortPref(city: CityKey): string {
  const norms = (cityComfortNorms as any)[city]?.occupant_preferences_db2;
  if (!norms || !norms.has_labelled_votes || !norms.tsv_distribution_pct) {
    return "not available (no labelled votes)";
  }
  const t = norms.tsv_distribution_pct;
  return `Neutral ${t.neutral}%, Cool ${t.cool}%, Warm ${t.warm}% (N=${norms.n_rows})`;
}

const AREA_AVERAGES: Record<CityKey, {
  usually_feel: string;
  hours_occupied: string;
  cooling_available: string;
  clothing_summer: string;
}> = {
  Jodhpur: {
    usually_feel: getCityComfortPref("Jodhpur"),
    hours_occupied: "24 h/day continuous (A-001)",
    cooling_available: "Passive cross-ventilation / fan",
    clothing_summer: "Light cotton (0.5 clo)"
  },
  Mumbai: {
    usually_feel: getCityComfortPref("Mumbai"),
    hours_occupied: "24 h/day continuous (A-001)",
    cooling_available: "Passive cross-ventilation / fan",
    clothing_summer: "Light breathable (0.5 clo)"
  },
  New_Delhi: {
    usually_feel: getCityComfortPref("New_Delhi"),
    hours_occupied: "24 h/day continuous (A-001)",
    cooling_available: "Passive cross-ventilation / fan",
    clothing_summer: "Seasonal: 0.5 clo summer / 1.0 clo winter"
  },
  Bengaluru: {
    usually_feel: getCityComfortPref("Bengaluru"),
    hours_occupied: "24 h/day continuous (A-001)",
    cooling_available: "Passive cross-ventilation / fan",
    clothing_summer: "Moderate casual (0.6 clo)"
  },
  Shimla: {
    usually_feel: getCityComfortPref("Shimla"),
    hours_occupied: "24 h/day continuous (A-001)",
    cooling_available: "Passive solar heating / natural ventilation",
    clothing_summer: "Layered woolens (1.0 clo winter / 0.8 clo summer)"
  }
};

export function haversineDistanceKm(lat1: number, lon1: number, lat2: number, lon2: number): number {
  const rEarth = 6371.0;
  const dLat = ((lat2 - lat1) * Math.PI) / 180.0;
  const dLon = ((lon2 - lon1) * Math.PI) / 180.0;
  const a =
    Math.sin(dLat / 2) * Math.sin(dLat / 2) +
    Math.cos((lat1 * Math.PI) / 180.0) *
      Math.cos((lat2 * Math.PI) / 180.0) *
      Math.sin(dLon / 2) *
      Math.sin(dLon / 2);
  const c = 2.0 * Math.atan2(Math.sqrt(a), Math.sqrt(1.0 - a));
  return Math.round(rEarth * c * 10) / 10;
}

// Client-side CPWD DSR 2021 Cost Engine
export function estimateEnvelopeCost(design: {
  roof_insulation_thickness: number;
  wall_insulation_thickness: number;
  roof_solar_absorptance: number;
  shading_depth: number;
  wwr: number;
}): CostRangeEstimate {
  const roofArea = geometryData.shelter_v1.roof_area_m2; // 20.0 m2 (5m x 4m)
  const grossWallArea = geometryData.shelter_v1.gross_wall_area_m2; // 54.0 m2 (18m perimeter x 3m height)
  const carpetArea = geometryData.shelter_v1.carpet_area_m2; // 20.0 m2
  const wwrFraction = design.wwr > 1.0 ? design.wwr / 100.0 : design.wwr;
  const windowArea = grossWallArea * wwrFraction;
  const netWallArea = grossWallArea - windowArea;

  // CPWD DSR 2021 item codes & rates:
  // Item 12.41.1 EPS insulation 50mm: ₹385.40/m2
  const roofInsM = design.roof_insulation_thickness;
  const roofInsCost = roofInsM > 0.005 ? (roofInsM / 0.05) * 385.40 * roofArea : 0.0;

  // Item 12.48.1 Mineral wool insulation 50mm: ₹420.00/m2
  const wallInsM = design.wall_insulation_thickness;
  const wallInsCost = wallInsM > 0.005 ? (wallInsM / 0.05) * 420.00 * netWallArea : 0.0;

  // Item 11.50.1 High SRI reflective cool roof coating: ₹145.00/m2
  const coolRoofCost = design.roof_solar_absorptance < 0.60 ? 145.00 * roofArea : 0.0;

  // Item 9.120.1 Exterior powder-coated aluminium louvers: ₹1850.00/m2
  const louverArea = windowArea * Math.min(1.0, design.shading_depth * 1.5);
  const shadingCost = design.shading_depth > 0.1 ? louverArea * 1850.00 : 0.0;

  // Item 9.117.1 Double-glazed hermetically sealed window units: ₹2200.00/m2
  const glazingCost = windowArea * 2200.00;

  const totalCentral = roofInsCost + wallInsCost + coolRoofCost + shadingCost + glazingCost;
  const totalMin = Math.round(totalCentral * 0.85);
  const totalMax = Math.round(totalCentral * 1.15);
  const centralRounded = Math.round(totalCentral);

  return {
    total_envelope_cost_inr: {
      min: totalMin,
      max: totalMax,
      central: centralRounded
    },
    cost_per_m2_carpet: {
      min: Math.round(totalMin / carpetArea),
      max: Math.round(totalMax / carpetArea),
      central: Math.round(centralRounded / carpetArea)
    },
    breakdown: {
      roof_insulation_inr: Math.round(roofInsCost),
      wall_insulation_inr: Math.round(wallInsCost),
      cool_roof_coating_inr: Math.round(coolRoofCost),
      shading_louvers_inr: Math.round(shadingCost),
      window_glazing_inr: Math.round(glazingCost)
    },
    schedule_source: "CPWD Delhi Schedule of Rates (DSR 2021)",
    notes: "Rates incorporate 1% water charges and 15% contractor profit & overheads. ±15% range accounts for regional transport and local labour variance."
  };
}

export function computeComfortFitScore(
  discomfortPct: number,
  energyKwh: number,
  userFeel: UserFeel,
  cooling: CoolingType = "none"
): number {
  const comfortShare = Math.max(0, Math.min(100, 100 - discomfortPct));
  const feelWeight = userFeel === "too hot" ? 1.15 : userFeel === "too cold" ? 0.90 : 1.0;
  // Fans are free-running: zero active HVAC energy penalty
  const isFreeRunning = cooling === "none" || cooling === "fan";
  const energyPenalty = isFreeRunning ? 0 : Math.min(25, (energyKwh / 200) * 20);
  const score = Math.round(comfortShare * 0.85 * (2 - feelWeight) - energyPenalty + 15);
  return Math.max(10, Math.min(98, score));
}

// Fallback Package Builder using local JSON Pareto Fronts
function buildLocalPackages(
  city: CityKey,
  bldgType: BuildingType,
  userFeel: UserFeel,
  priority: UserPriority,
  futureClimate: boolean,
  hoursOccupied: number = 24,
  cooling: CoolingType = "none"
): EvaluationPackagesResponse {
  const paretoRows = PARETO_BY_CITY[city] || PARETO_BY_CITY["Jodhpur"];
  const cityInfo = CITIES_DATA[city];
  const areaAvg = AREA_AVERAGES[city];
  const outdoorTa = MONTHLY_OUTDOOR_TA[city];

  const futureTempDelta = futureClimate ? 1.5 : 0.0;

  // Filter verified points from Pareto front
  const verifiedRows = paretoRows.filter(r => r.is_verified);
  const pool = verifiedRows.length > 0 ? verifiedRows : paretoRows;

  // 1. Lowest energy: min O2 (selection_role === "Best_O2" or lowest O2)
  const lowestEnergyRow =
    pool.find(r => r.selection_role === "Best_O2") ||
    [...pool].sort((a, b) => Number(a.verified_O2 ?? a.O2) - Number(b.verified_O2 ?? b.O2))[0];

  // 2. Balanced: Knee point
  const balancedRow =
    pool.find(r => r.selection_role === "Knee_Point") ||
    pool[Math.floor(pool.length / 2)];

  // 3. Lowest discomfort: min O1 (selection_role === "Best_O1_ml" or lowest O1_ml)
  const lowestDiscomfortRow =
    pool.find(r => r.selection_role === "Best_O1_ml") ||
    [...pool].sort((a, b) => Number(a.verified_O1_ml ?? a.O1_ml) - Number(b.verified_O1_ml ?? b.O1_ml))[0];

  function formatPackage(
    row: any,
    id: "pkg_budget" | "pkg_balanced" | "pkg_best_comfort",
    name: string,
    desc: string
  ): PassivePackage {
    const design = {
      roof_insulation_thickness: Number(row.roof_insulation_thickness || 0.05),
      wall_insulation_thickness: Number(row.wall_insulation_thickness || 0.03),
      roof_solar_absorptance: Number(row.roof_solar_absorptance || 0.4),
      wwr: Number(row.wwr || 0.15),
      orientation: Number(row.orientation || 0),
      shading_depth: Number(row.shading_depth || 0.5),
      ventilation_ach: Number(row.ventilation_ach || 6.0),
      wall_mass_class: (row.wall_mass_class || "medium") as "light" | "medium" | "heavy"
    };

    const costInfo = estimateEnvelopeCost(design);
    const discomfort = Math.round(Number(row.verified_O1_ml ?? row.O1_ml ?? 40.0) * 10) / 10;
    const mlDiscomfort = discomfort;
    const rawO2 = Number(row.verified_O2 ?? row.O2 ?? 50.0);
    const energy = Math.round(rawO2 * 10) / 10;
    const fitScore = computeComfortFitScore(discomfort, energy, userFeel, cooling);

    const roofMm = Math.round(design.roof_insulation_thickness * 1000);
    const wallMm = Math.round(design.wall_insulation_thickness * 1000);
    const wwrPct = Math.round(design.wwr > 1 ? design.wwr : design.wwr * 100);
    const carpetArea = geometryData.shelter_v1.carpet_area_m2; // 20.0 m2 (5m x 4m)
    const grossWallArea = geometryData.shelter_v1.gross_wall_area_m2; // 54.0 m2
    const windowArea = Math.round((grossWallArea * (wwrPct / 100)) * 10) / 10;
    const netWallArea = Math.round((grossWallArea - windowArea) * 10) / 10;

    const quantities = {
      roof_insulation_mm: roofMm,
      wall_insulation_mm: wallMm,
      roof_area_m2: carpetArea,
      wall_area_m2: netWallArea,
      wwr_pct: wwrPct,
      overhang_m: Math.round(design.shading_depth * 100) / 100,
      ventilation_ach: Math.round(design.ventilation_ach * 10) / 10,
      wall_mass: design.wall_mass_class
    };

    const materials = [
      `Roof: ${roofMm} mm Expanded Polystyrene (EPS) over ${carpetArea} m² roof slab`,
      `Roof Finish: Reflective high-SRI coating (absorptance: ${design.roof_solar_absorptance.toFixed(2)})`,
      `Exterior Walls: ${wallMm} mm mineral wool over ${netWallArea} m² net exterior wall area`,
      `Wall Construction: 200 mm ${design.wall_mass_class} mass masonry`,
      `Fenestration: ${wwrPct}% WWR (${windowArea} m² glazing) with ${design.shading_depth.toFixed(2)} m exterior overhang projection`,
      `Ventilation: Operable louvers providing ${design.ventilation_ach.toFixed(1)} ACH natural cross-ventilation`
    ];

    const hoursScored = Math.round(hoursOccupied * 365);
    const annualDiscomfortHours = Math.round(hoursScored * (discomfort / 100));

    // Monthly Indoor Before vs After
    const monthlyBefore: number[] = [];
    const monthlyAfter: number[] = [];

    outdoorTa.forEach((outT, idx) => {
      const effectiveOut = outT + futureTempDelta;
      if (city === "Shimla") {
        const tBefore = effectiveOut + 1.2;
        const warmingDelta = 1.8 + (roofMm / 150) * 2.5 + (wallMm / 150) * 2.0;
        monthlyBefore.push(Math.round(tBefore * 10) / 10);
        monthlyAfter.push(Math.round((tBefore + warmingDelta) * 10) / 10);
      } else {
        const tBefore = effectiveOut + 2.8 - (idx === 6 || idx === 7 ? 0.5 : 0.0);
        const coolingDelta = 2.4 + (roofMm / 150) * 2.2 + design.shading_depth * 1.2;
        monthlyBefore.push(Math.round(tBefore * 10) / 10);
        monthlyAfter.push(Math.round((tBefore - coolingDelta) * 10) / 10);
      }
    });

    const isVerifiedDirect = Boolean(row.is_verified || row.value_source === "energyplus");
    const valueSource: "energyplus" | "surrogate" = isVerifiedDirect ? "energyplus" : "surrogate";
    const badge = isVerifiedDirect ? "EnergyPlus verified" : "Estimated (Surrogate)";
    const isFreeRunning = cooling === "none" || cooling === "fan";

    return {
      id,
      name,
      description: desc,
      pareto_id: row.pareto_id || "P_VERIFIED",
      selection_role: row.selection_role || (id === "pkg_budget" ? "Best_O2" : id === "pkg_balanced" ? "Knee_Point" : "Best_O1_ml"),
      comfort_fit_score: fitScore,
      comfort_gain_vs_baseline_pts: Math.max(0, Math.round((getCityBaselines(city).r2.discomfort_ml_pct - discomfort) * 10) / 10),
      energy_reduction_pct: Math.max(
        0,
        Math.round(
          ((getCityBaselines(city).r2.energy_kwh_per_m2_yr - energy) /
            getCityBaselines(city).r2.energy_kwh_per_m2_yr) *
            1000
        ) / 10
      ),
      discomfort_pct: discomfort,
      ml_discomfort_pct: mlDiscomfort,
      annual_energy_kwh_per_m2: isFreeRunning ? 0.0 : energy,
      annual_discomfort_hours: annualDiscomfortHours,
      hours_scored: hoursScored,
      cooling_mode: (cooling === "AC" || cooling === "ac")
        ? "Active cooling (Ideal-loads HVAC)"
        : cooling === "fan"
        ? "Free-running (fan effect not yet modelled)"
        : "Free-running (0 HVAC energy)",
      is_verified: isVerifiedDirect,
      value_source: valueSource,
      badge: badge,
      o2_raw_pred: row.o2_raw_pred ?? row.pred_O2 ?? rawO2,
      o2_was_clipped: Boolean(row.o2_was_clipped ?? ((row.o2_raw_pred ?? row.pred_O2 ?? 0) < 0)),
      design_variables: design,
      quantities,
      materials_list: materials,
      cost_range: costInfo,
      monthly_performance: {
        months: MONTH_NAMES,
        outdoor_ta: outdoorTa.map(t => Math.round((t + futureTempDelta) * 10) / 10),
        indoor_ta_baseline_r2: monthlyBefore,
        indoor_ta_recommended: monthlyAfter
      }
    };
  }

  const pkgBudget = formatPackage(
    lowestEnergyRow,
    "pkg_budget",
    "Lowest energy",
    "Minimizes active heating and cooling demand (min O2) on the verified Pareto front through envelope thermal protection."
  );

  const pkgBalanced = formatPackage(
    balancedRow,
    "pkg_balanced",
    "Balanced",
    "Pareto knee-point design offering the best balance between uncomfortable hours and active energy demand."
  );

  const pkgBestComfort = formatPackage(
    lowestDiscomfortRow,
    "pkg_best_comfort",
    "Lowest discomfort",
    "Minimizes annual uncomfortable hours (min O1) on the verified Pareto front with maximized thermal stability."
  );

  return {
    city,
    building_type: bldgType,
    climate_zone: cityInfo.zone,
    confidence_tier: cityInfo.confidence,
    confidence_reason: cityInfo.envelopeAlert || "Precomputed EnergyPlus surrogate prediction.",
    adaptive_validity: `${getCityApplicability(city).adaptive_validity_pct.toFixed(1)}%`,
    future_climate_applied: futureClimate,
    packages: {
      budget: pkgBudget,
      balanced: pkgBalanced,
      best_comfort: pkgBestComfort
    },
    area_average: areaAvg,
    user_comparison: {
      user_feel: userFeel,
      area_feel: areaAvg.usually_feel,
      user_occupied_hours: hoursOccupied,
      area_occupied_hours: areaAvg.hours_occupied,
      user_cooling: cooling,
      area_cooling: areaAvg.cooling_available
    },
    disclaimer: "Simulation-based estimate, not a measured result or a construction quote.",
    cost_disclaimer: "Rough indicative ranges from CPWD Delhi Schedule of Rates (DSR 2021) with ±15% regional variance. For academic planning only; never present as an official contractor quote or tender."
  };
}

// -----------------------------------------------------------------------------
// Exported API Client Functions
// -----------------------------------------------------------------------------

export async function matchLocation(query: string, lat?: number, lon?: number): Promise<LocationMatchResponse> {
  try {
    const res = await fetch(`${API_BASE}/match-location`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ query, latitude: lat, longitude: lon })
    });
    if (res.ok) {
      return await res.json();
    }
  } catch (err) {
    // Backend offline; continue to deterministic client fallback
  }

  // Client-side fallback matching
  let targetLat = lat;
  let targetLon = lon;
  const qLower = query.toLowerCase().trim();

  if (targetLat === undefined || targetLon === undefined) {
    if (qLower.includes("pune")) {
      targetLat = 18.5204; targetLon = 73.8567; // ~120 km from Mumbai
    } else if (qLower.includes("goa")) {
      targetLat = 15.2993; targetLon = 74.1240;
    } else if (qLower.includes("mumbai")) {
      targetLat = 19.0760; targetLon = 72.8777;
    } else if (qLower.includes("jaipur")) {
      targetLat = 26.9124; targetLon = 75.7873;
    } else if (qLower.includes("noida") || qLower.includes("gurgaon") || qLower.includes("gurugram")) {
      targetLat = 28.4595; targetLon = 77.0266;
    } else if (qLower.includes("delhi")) {
      targetLat = 28.6139; targetLon = 77.2090;
    } else if (qLower.includes("chennai")) {
      targetLat = 13.0827; targetLon = 80.2707;
    } else if (qLower.includes("hyderabad")) {
      targetLat = 17.3850; targetLon = 78.4867;
    } else if (qLower.includes("mysore")) {
      targetLat = 12.2958; targetLon = 76.6394;
    } else if (qLower.includes("bengaluru") || qLower.includes("bangalore")) {
      targetLat = 12.9716; targetLon = 77.5946;
    } else if (qLower.includes("manali")) {
      targetLat = 32.2432; targetLon = 77.1892;
    } else if (qLower.includes("dharamshala")) {
      targetLat = 32.2190; targetLon = 76.3234;
    } else if (qLower.includes("dehradun")) {
      targetLat = 30.3165; targetLon = 78.0322;
    } else if (qLower.includes("shimla")) {
      targetLat = 31.1048; targetLon = 77.1734;
    } else {
      targetLat = 26.2389; targetLon = 73.0243; // Default Jodhpur
    }
  }

  let minDistance = Infinity;
  let nearestCity: CityKey = "Jodhpur";

  (Object.keys(CITIES_DATA) as CityKey[]).forEach(cKey => {
    const [cLat, cLon] = CITIES_DATA[cKey].coordinates;
    const dist = haversineDistanceKm(targetLat!, targetLon!, cLat, cLon);
    if (dist < minDistance) {
      minDistance = dist;
      nearestCity = cKey;
    }
  });

  const isDirect = minDistance < 20.0;
  const notice = !isDirect
    ? `Nearest simulated climate station is ${CITIES_DATA[nearestCity].name} (${minDistance} km away). Local elevation and microclimate may cause differences.`
    : null;

  return {
    searched_query: query,
    matched_city_key: nearestCity,
    matched_city_name: CITIES_DATA[nearestCity].name,
    climate_zone: CITIES_DATA[nearestCity].zone,
    confidence_tier: CITIES_DATA[nearestCity].confidence,
    distance_km: minDistance,
    is_direct_station: isDirect,
    nearest_match_notice: notice,
    disclaimer: "Simulation-based estimate, not a measured result or a construction quote."
  };
}

export async function evaluateQuestionnaire(params: {
  city: CityKey;
  building_type: BuildingType;
  usually_feel: UserFeel;
  hours_occupied: number;
  has_cooling: CoolingType;
  summer_clothing: ClothingType;
  winter_clothing: ClothingType;
  priority: UserPriority;
  future_climate: boolean;
}): Promise<EvaluationPackagesResponse> {
  if (API_BASE) {
    try {
      const res = await fetch(`${API_BASE}/evaluate-packages`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(params)
      });
      if (res.ok) {
        return await res.json();
      }
    } catch {
      // Backend offline; continue to deterministic client fallback
    }
  }

  return buildLocalPackages(
    params.city,
    params.building_type,
    params.usually_feel,
    params.priority,
    params.future_climate,
    params.hours_occupied,
    params.has_cooling
  );
}

export async function downloadBuilderPdf(
  packageData: any,
  profile?: any,
  language: string = "en"
): Promise<void> {
  const payload = {
    package_data: packageData,
    profile: profile || null,
    language: language,
    project_title: "Passive Climate Design Specification"
  };

  const endpoints = [
    `${API_BASE}/export/pdf`,
    `${API_BASE}/v1/export/pdf`,
    "http://localhost:8000/api/v1/export/pdf",
    "http://localhost:8000/export/pdf"
  ];

  let res: Response | null = null;
  for (const ep of endpoints) {
    try {
      const attempt = await fetch(ep, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      });
      if (attempt.ok) {
        res = attempt;
        break;
      }
    } catch {}
  }

  if (!res || !res.ok) {
    window.print();
    return;
  }

  const blob = await res.blob();
  const url = window.URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  const cityName = packageData.city || "Design";
  const pkgName = packageData.name || packageData.package_name || "Package";
  a.download = `Passive_Specification_${cityName}_${pkgName}.pdf`;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  window.URL.revokeObjectURL(url);
}

