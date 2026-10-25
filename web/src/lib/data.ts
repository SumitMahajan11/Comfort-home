import applicabilityJson from "../data/applicability.json";
import surrogateMetricsJson from "../data/surrogate_metrics.json";
import referenceResultsJson from "../data/reference_results.json";
import s3EvaluationJson from "../data/s3_evaluation.json";
import paretoBengaluruJson from "../data/pareto_Bengaluru.json";
import paretoJodhpurJson from "../data/pareto_Jodhpur.json";
import paretoMumbaiJson from "../data/pareto_Mumbai.json";
import paretoNewDelhiJson from "../data/pareto_New_Delhi.json";
import paretoShimlaJson from "../data/pareto_Shimla.json";
import shapSummaryJson from "../data/shap_summary.json";
import modelsLeaderboardJson from "../data/models_leaderboard.json";
import projectMetaJson from "../data/project_meta.json";

import {
  ApplicabilityData,
  CityKey,
  ParetoDesign,
  ProjectMetadata,
  ReferenceShelter,
  S3Result,
  SurrogateMetric
} from "../types";

export function getProjectMetadata(): ProjectMetadata {
  return projectMetaJson as unknown as ProjectMetadata;
}

export function getApplicabilityData(): ApplicabilityData[] {
  return applicabilityJson as unknown as ApplicabilityData[];
}

export function getApplicabilityForCity(city: CityKey): ApplicabilityData | undefined {
  const all = getApplicabilityData();
  return all.find((item) => item.city === city);
}

export function getSurrogateMetrics(): SurrogateMetric[] {
  return surrogateMetricsJson as unknown as SurrogateMetric[];
}

export function getSurrogateMetricsForCity(city: CityKey): SurrogateMetric[] {
  const all = getSurrogateMetrics();
  return all.filter((item) => item.city === city);
}

export function getReferenceResults(): ReferenceShelter[] {
  return referenceResultsJson as unknown as ReferenceShelter[];
}

export function getReferencesForCity(city: CityKey): {
  r1: ReferenceShelter | undefined;
  r2: ReferenceShelter | undefined;
} {
  const all = getReferenceResults();
  const cityRefs = all.filter((item) => item.city === city);
  return {
    r1: cityRefs.find((r) => r.reference_name === "R1_Lightweight"),
    r2: cityRefs.find((r) => r.reference_name === "R2_Conventional")
  };
}

export function getS3EvaluationResults(): S3Result[] {
  return s3EvaluationJson as unknown as S3Result[];
}

export function getS3ResultForCity(city: CityKey): S3Result | undefined {
  const all = getS3EvaluationResults();
  return all.find((r) => r.city === city);
}

const PARETO_MAP: Record<CityKey, any[]> = {
  Bengaluru: paretoBengaluruJson,
  Jodhpur: paretoJodhpurJson,
  Mumbai: paretoMumbaiJson,
  New_Delhi: paretoNewDelhiJson,
  Shimla: paretoShimlaJson
};

export function getParetoDesigns(city: CityKey): ParetoDesign[] {
  const rawList = PARETO_MAP[city] || [];
  // Ensure composite ranking & presets are tagged
  return rawList.map((item, idx) => {
    let preset_tag: ParetoDesign["preset_tag"] = undefined;
    if (idx === 0) preset_tag = "Lowest Discomfort";
    else if (idx === rawList.length - 1) preset_tag = "Lowest Energy";
    else if (idx === Math.floor(rawList.length / 2)) preset_tag = "Balanced (Knee Point)";

    return {
      ...item,
      preset_tag
    } as ParetoDesign;
  });
}

export function getShapSummary() {
  return shapSummaryJson;
}

export function getModelsLeaderboard() {
  return modelsLeaderboardJson;
}
