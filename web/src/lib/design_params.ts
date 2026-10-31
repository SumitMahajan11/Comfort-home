/**
 * web/src/lib/design_params.ts
 *
 * Grounded parameter bounds and query parsing logic for shelter design variables.
 * Bounds match src/sim/sampler.py (Latin Hypercube Sampling for EnergyPlus simulations).
 */

import { CityKey, DesignVariables, ParetoDesign } from "@/types";
import { DEFAULT_DESIGN } from "./constants";
import { getParetoDesigns } from "./data";

/**
 * Exact sampling bounds from src/sim/sampler.py:
 * - roof_insulation_thickness: (0.0, 0.150) m -> (0, 150) mm
 * - wall_insulation_thickness: (0.0, 0.150) m -> (0, 150) mm
 * - wall_mass_class: ['light', 'medium', 'heavy']
 * - roof_solar_absorptance: (0.30, 0.90)
 * - wwr: (0.05, 0.40) -> (5%, 40%)
 * - orientation: (0.0, 359.0) -> (0°, 360°)
 * - shading_depth: (0.0, 1.0) m
 * - ventilation_ach: (1.0, 15.0) ACH
 */
export const SAMPLER_BOUNDS = {
  roof_insulation_thickness: { min: 0, max: 150, step: 5, unit: "mm" },
  wall_insulation_thickness: { min: 0, max: 150, step: 5, unit: "mm" },
  wall_mass_class: ["light", "medium", "heavy"] as const,
  roof_solar_absorptance: { min: 0.30, max: 0.90, step: 0.05, unit: "" },
  wwr: { min: 5, max: 40, step: 1, unit: "%" },
  orientation: { min: 0, max: 360, step: 5, unit: "°" },
  shading_depth: { min: 0.0, max: 1.0, step: 0.05, unit: "m" },
  ventilation_ach: { min: 1.0, max: 15.0, step: 0.5, unit: "ACH" }
} as const;

export type WallMass = (typeof SAMPLER_BOUNDS.wall_mass_class)[number];

function clamp(value: number, min: number, max: number): number {
  if (Number.isNaN(value)) return min;
  return Math.max(min, Math.min(max, value));
}

/**
 * Parses and clamps design variables from query params or partial objects
 * strictly within sampling bounds. Out-of-bound values are clamped to edges.
 */
export function clampDesignVariables(raw: Partial<Record<string, unknown>>): DesignVariables {
  // Roof insulation
  const rawRoof = raw.roof_insulation_thickness ?? raw.roof_ins;
  const roof = rawRoof != null ? clamp(Number(rawRoof), SAMPLER_BOUNDS.roof_insulation_thickness.min, SAMPLER_BOUNDS.roof_insulation_thickness.max) : DEFAULT_DESIGN.roof_insulation_thickness;

  // Wall insulation
  const rawWall = raw.wall_insulation_thickness ?? raw.wall_ins;
  const wall = rawWall != null ? clamp(Number(rawWall), SAMPLER_BOUNDS.wall_insulation_thickness.min, SAMPLER_BOUNDS.wall_insulation_thickness.max) : DEFAULT_DESIGN.wall_insulation_thickness;

  // Wall mass class
  const rawMass = (raw.wall_mass_class ?? raw.mass ?? "").toString().toLowerCase();
  const mass: WallMass = (SAMPLER_BOUNDS.wall_mass_class as readonly string[]).includes(rawMass) ? (rawMass as WallMass) : DEFAULT_DESIGN.wall_mass_class;

  // Roof absorptance
  const rawAbsorp = raw.roof_solar_absorptance ?? raw.absorp;
  const absorp = rawAbsorp != null ? clamp(Number(rawAbsorp), SAMPLER_BOUNDS.roof_solar_absorptance.min, SAMPLER_BOUNDS.roof_solar_absorptance.max) : DEFAULT_DESIGN.roof_solar_absorptance;

  // WWR (handles both fraction e.g. 0.15 and percentage e.g. 15)
  const rawWwr = raw.wwr;
  let parsedWwr = rawWwr != null ? Number(rawWwr) : DEFAULT_DESIGN.wwr;
  if (parsedWwr > 0 && parsedWwr < 1.0) {
    parsedWwr = parsedWwr * 100;
  }
  const wwr = clamp(parsedWwr, SAMPLER_BOUNDS.wwr.min, SAMPLER_BOUNDS.wwr.max);

  // Orientation
  const rawOrient = raw.orientation ?? raw.orient;
  const orient = rawOrient != null ? clamp(Number(rawOrient), SAMPLER_BOUNDS.orientation.min, SAMPLER_BOUNDS.orientation.max) : DEFAULT_DESIGN.orientation;

  // Shading depth
  const rawShade = raw.shading_depth ?? raw.shading;
  const shade = rawShade != null ? clamp(Number(rawShade), SAMPLER_BOUNDS.shading_depth.min, SAMPLER_BOUNDS.shading_depth.max) : DEFAULT_DESIGN.shading_depth;

  // Ventilation ACH
  const rawVent = raw.ventilation_ach ?? raw.vent;
  const vent = rawVent != null ? clamp(Number(rawVent), SAMPLER_BOUNDS.ventilation_ach.min, SAMPLER_BOUNDS.ventilation_ach.max) : DEFAULT_DESIGN.ventilation_ach;

  return {
    roof_insulation_thickness: Math.round(roof),
    wall_insulation_thickness: Math.round(wall),
    wall_mass_class: mass,
    roof_solar_absorptance: Number(absorp.toFixed(2)),
    wwr: Math.round(wwr),
    orientation: Math.round(orient),
    shading_depth: Number(shade.toFixed(2)),
    ventilation_ach: Number(vent.toFixed(1))
  };
}

/**
 * Checks whether all design variables fall strictly within the Latin Hypercube sampled bounds.
 */
export function checkSampledRangeValidity(design: DesignVariables): {
  isWithinBounds: boolean;
  outOfBoundsFields: string[];
} {
  const outOfBoundsFields: string[] = [];

  if (
    design.roof_insulation_thickness < SAMPLER_BOUNDS.roof_insulation_thickness.min ||
    design.roof_insulation_thickness > SAMPLER_BOUNDS.roof_insulation_thickness.max
  ) {
    outOfBoundsFields.push("Roof insulation");
  }

  if (
    design.wall_insulation_thickness < SAMPLER_BOUNDS.wall_insulation_thickness.min ||
    design.wall_insulation_thickness > SAMPLER_BOUNDS.wall_insulation_thickness.max
  ) {
    outOfBoundsFields.push("Wall insulation");
  }

  if (
    design.roof_solar_absorptance < SAMPLER_BOUNDS.roof_solar_absorptance.min ||
    design.roof_solar_absorptance > SAMPLER_BOUNDS.roof_solar_absorptance.max
  ) {
    outOfBoundsFields.push("Roof solar absorptance");
  }

  if (design.wwr < SAMPLER_BOUNDS.wwr.min || design.wwr > SAMPLER_BOUNDS.wwr.max) {
    outOfBoundsFields.push("Window-to-wall ratio");
  }

  if (
    design.orientation < SAMPLER_BOUNDS.orientation.min ||
    design.orientation > SAMPLER_BOUNDS.orientation.max
  ) {
    outOfBoundsFields.push("Orientation");
  }

  if (
    design.shading_depth < SAMPLER_BOUNDS.shading_depth.min ||
    design.shading_depth > SAMPLER_BOUNDS.shading_depth.max
  ) {
    outOfBoundsFields.push("Overhang shading");
  }

  if (
    design.ventilation_ach < SAMPLER_BOUNDS.ventilation_ach.min ||
    design.ventilation_ach > SAMPLER_BOUNDS.ventilation_ach.max
  ) {
    outOfBoundsFields.push("Ventilation rate");
  }

  return {
    isWithinBounds: outOfBoundsFields.length === 0,
    outOfBoundsFields
  };
}

/**
 * Finds the nearest EnergyPlus-verified Pareto design for the given city
 * using normalized Euclidean distance across envelope variables.
 */
export function findNearestVerifiedParetoDesign(
  city: CityKey,
  design: DesignVariables
): { nearestDesign: ParetoDesign; distance: number } {
  const allPareto = getParetoDesigns(city);
  const verifiedDesigns = allPareto.filter((p) => p.is_verified);
  const candidates = verifiedDesigns.length > 0 ? verifiedDesigns : allPareto;

  let minDistance = Infinity;
  let nearest = candidates[0];

  for (const candidate of candidates) {
    // Normalization to [0, 1] ranges
    const candRoofMm =
      candidate.roof_insulation_thickness <= 0.2
        ? candidate.roof_insulation_thickness * 1000
        : candidate.roof_insulation_thickness;
    const candWallMm =
      candidate.wall_insulation_thickness <= 0.2
        ? candidate.wall_insulation_thickness * 1000
        : candidate.wall_insulation_thickness;
    const candWwr =
      candidate.wwr <= 1.0 ? candidate.wwr * 100 : candidate.wwr;

    const dRoof = Math.abs((candRoofMm - design.roof_insulation_thickness) / 150);
    const dWall = Math.abs((candWallMm - design.wall_insulation_thickness) / 150);
    const dAbsorp = Math.abs((candidate.roof_solar_absorptance - design.roof_solar_absorptance) / 0.6);
    const dWwr = Math.abs((candWwr - design.wwr) / 35);
    const dShade = Math.abs((candidate.shading_depth - design.shading_depth) / 1.0);
    const dVent = Math.abs((candidate.ventilation_ach - design.ventilation_ach) / 14);
    const dMass = candidate.wall_mass_class === design.wall_mass_class ? 0 : 0.3;

    // Roof absorptance and ventilation are high-weight physical drivers
    const dist = Math.sqrt(
      dRoof ** 2 +
      dWall ** 2 +
      (dAbsorp * 1.5) ** 2 +
      dWwr ** 2 +
      dShade ** 2 +
      (dVent * 1.2) ** 2 +
      dMass ** 2
    );

    if (dist < minDistance) {
      minDistance = dist;
      nearest = candidate;
    }
  }

  return { nearestDesign: nearest, distance: Number(minDistance.toFixed(3)) };
}
