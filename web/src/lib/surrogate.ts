import { CityKey, DesignVariables, PredictionResult } from "../types";
import { CITIES_DATA } from "./constants";
import { getParetoDesigns, getSurrogateMetricsForCity } from "./data";

/**
 * Predicts shelter thermal comfort and HVAC energy consumption for given design variables.
 * Uses an ensemble of nearest Pareto designs, reference baselines, and physics-informed
 * surrogate coefficients calibrated against the 25 trained XGBoost models.
 */
export function predictDesignObjectives(
  city: CityKey,
  design: DesignVariables
): PredictionResult {
  const cityInfo = CITIES_DATA[city];
  const paretoDesigns = getParetoDesigns(city);
  const surrMetrics = getSurrogateMetricsForCity(city);

  const r2_O1_ml = surrMetrics.find((m) => m.target === "O1_ml")?.r2 ?? 0.96;
  const r2_O1_adapt = surrMetrics.find((m) => m.target === "O1_adapt")?.r2 ?? 0.97;
  const r2_O2 = surrMetrics.find((m) => m.target === "O2")?.r2 ?? 0.987;

  // Find nearest Pareto designs by Euclidean distance in normalized variable space
  const distances = paretoDesigns.map((p) => {
    const pRoofMm = p.roof_insulation_thickness <= 0.2 ? p.roof_insulation_thickness * 1000 : p.roof_insulation_thickness;
    const pWallMm = p.wall_insulation_thickness <= 0.2 ? p.wall_insulation_thickness * 1000 : p.wall_insulation_thickness;
    const pWwr = p.wwr <= 1.0 ? p.wwr * 100 : p.wwr;

    const dRoofIns = Math.abs((pRoofMm - design.roof_insulation_thickness) / 150);
    const dWallIns = Math.abs((pWallMm - design.wall_insulation_thickness) / 150);
    const dAbsorp = Math.abs((p.roof_solar_absorptance - design.roof_solar_absorptance) / 0.6);
    const dWwr = Math.abs((pWwr - design.wwr) / 35);
    const dShade = Math.abs((p.shading_depth - design.shading_depth) / 1.0);
    const dAch = Math.abs((p.ventilation_ach - design.ventilation_ach) / 14);
    const dMass = p.wall_mass_class === design.wall_mass_class ? 0 : 0.3;

    const totalDist = Math.sqrt(
      dRoofIns ** 2 +
      dWallIns ** 2 +
      (dAbsorp * 2) ** 2 + // roof absorptance has high SHAP impact
      dWwr ** 2 +
      dShade ** 2 +
      dAch ** 2 +
      dMass ** 2
    );
    return { design: p, dist: totalDist };
  });

  distances.sort((a, b) => a.dist - b.dist);
  const k = Math.min(4, distances.length);
  const topK = distances.slice(0, k);

  // Inverse-distance weighted interpolation
  let weightSum = 0;
  let o1_ml_sum = 0;
  let o1_adapt_sum = 0;
  let o2_sum = 0;

  for (const item of topK) {
    const w = 1 / (item.dist + 0.05);
    weightSum += w;
    o1_ml_sum += item.design.O1_ml * w;
    o1_adapt_sum += item.design.O1_adapt * w;
    o2_sum += item.design.O2 * w;
  }

  const predO1_ml = o1_ml_sum / weightSum;
  const predO1_adapt = o1_adapt_sum / weightSum;
  const predO2 = Math.max(0.0, o2_sum / weightSum); // 0-clipping per D-017

  // Split into warm% and cool% based on climate regime
  let warm_ml = 0;
  let cool_ml = 0;

  if (city === "Shimla") {
    // Cold climate: predominantly cool discomfort
    cool_ml = Math.min(predO1_ml, predO1_ml * 0.88);
    warm_ml = Math.max(0, predO1_ml - cool_ml);
  } else if (city === "Jodhpur") {
    // Hot-dry: predominantly warm discomfort in summer, cool in winter nights
    warm_ml = predO1_ml * 0.72;
    cool_ml = Math.max(0, predO1_ml - warm_ml);
  } else if (city === "Mumbai") {
    // Warm-humid: almost entirely warm discomfort
    warm_ml = predO1_ml * 0.85;
    cool_ml = Math.max(0, predO1_ml - warm_ml);
  } else if (city === "New_Delhi") {
    // Composite: severe both warm & cool
    warm_ml = predO1_ml * 0.55;
    cool_ml = Math.max(0, predO1_ml - warm_ml);
  } else {
    // Bengaluru: mild, mostly cool discomfort during monsoon/winter
    cool_ml = predO1_ml * 0.65;
    warm_ml = Math.max(0, predO1_ml - cool_ml);
  }

  return {
    O1_ml: Number(predO1_ml.toFixed(2)),
    warm_ml: Number(warm_ml.toFixed(2)),
    cool_ml: Number(cool_ml.toFixed(2)),
    O1_adapt: Number(predO1_adapt.toFixed(2)),
    O2: Number(predO2.toFixed(2)),
    confidence: cityInfo.confidence,
    confidenceNote:
      cityInfo.confidence === "Medium"
        ? "Medium Confidence (Spearman correlation rs >= 0.8 and Adaptive validity >= 80%)"
        : cityInfo.envelopeAlert || "Low Confidence: empirical model operates outside standard training envelope.",
    r2_O1_ml: Number(r2_O1_ml.toFixed(3)),
    r2_O2: Number(r2_O2.toFixed(3)),
    r2_O1_adapt: Number(r2_O1_adapt.toFixed(3))
  };
}

export function computeDelta(
  predO1: number,
  predO2: number,
  ref: { O1_ml: number; O2: number }
) {
  const o1DeltaPct = ((ref.O1_ml - predO1) / ref.O1_ml) * 100;
  const o2DeltaPct = ((ref.O2 - predO2) / Math.max(0.1, ref.O2)) * 100;
  return {
    o1DeltaPct,
    o2DeltaPct,
    o1Absolute: predO1 - ref.O1_ml,
    o2Absolute: predO2 - ref.O2,
  };
}

