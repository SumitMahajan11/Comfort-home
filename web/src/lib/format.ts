/**
 * web/src/lib/format.ts
 *
 * Central formatting utilities for envelope variables, simulation outputs,
 * and Pareto verification inspection.
 *
 * SOURCE UNIT DOCUMENTATION:
 * - roof_insulation_thickness and wall_insulation_thickness in raw and processed
 *   simulation files (and pareto_{city}.json) are stored in METRES (e.g. 0.143261 m = 143 mm).
 * - WWR is stored as a fraction [0.0, 1.0] (e.g. 0.135 = 14%) or percentage.
 * - Orientation is in degrees [0, 360).
 * - Shading depth is in metres.
 * - Natural ventilation is in air changes per hour (ACH).
 * - O1 discomfort is in percentage of hours (%).
 * - O2 HVAC energy is in kWh/m²/yr.
 */

const COMPASS_DIRECTIONS = [
  "N",
  "NNE",
  "NE",
  "ENE",
  "E",
  "ESE",
  "SE",
  "SSE",
  "S",
  "SSW",
  "SW",
  "WSW",
  "W",
  "WNW",
  "NW",
  "NNW"
] as const;

/**
 * Format roof or wall insulation thickness in millimetres.
 * Source unit: metres (converted via val * 1000).
 */
export function formatInsulationMm(valInMeters: number | null | undefined): string {
  if (valInMeters == null || Number.isNaN(valInMeters)) return "Not available";
  return `${Math.round(valInMeters * 1000)} mm`;
}

/**
 * Format Window-to-Wall Ratio (WWR) as percentage with 0 decimals.
 * Handles both fractional (0.15) and percentage (15) inputs.
 */
export function formatGlazingPct(val: number | null | undefined): string {
  if (val == null || Number.isNaN(val)) return "Not available";
  const pct = val <= 1 ? val * 100 : val;
  return `${Math.round(pct)}%`;
}

/**
 * Format building azimuth orientation with 0 decimals and 16-point compass label.
 * Example: 27° -> "27° · NNE", 218° -> "218° · SW".
 */
export function formatAzimuthWithCompass(deg: number | null | undefined): string {
  if (deg == null || Number.isNaN(deg)) return "Not available";
  const rounded = Math.round(deg);
  const normalized = ((rounded % 360) + 360) % 360;
  const index = Math.round(normalized / 22.5) % 16;
  const compass = COMPASS_DIRECTIONS[index];
  return `${normalized}° · ${compass}`;
}

/**
 * Format overhang shading depth in metres with 2 decimals.
 * Example: 0.75 -> "0.75 m".
 */
export function formatOverhangM(val: number | null | undefined): string {
  if (val == null || Number.isNaN(val)) return "Not available";
  return `${val.toFixed(2)} m`;
}

/**
 * Format natural ventilation rate in ACH with 1 decimal.
 * Example: 1.0 -> "1.0 ACH".
 */
export function formatVentilationAch(val: number | null | undefined): string {
  if (val == null || Number.isNaN(val)) return "Not available";
  return `${val.toFixed(1)} ACH`;
}

/**
 * Format solar absorptance coefficient with 2 decimals.
 * Example: 0.60 -> "0.60".
 */
export function formatSolarAbsorptance(val: number | null | undefined): string {
  if (val == null || Number.isNaN(val)) return "Not available";
  return val.toFixed(2);
}

/**
 * Format thermal mass class name with capitalization.
 * Example: "heavy" -> "Heavy".
 */
export function formatWallMassClass(val: string | null | undefined): string {
  if (!val) return "Not available";
  return val.charAt(0).toUpperCase() + val.slice(1).toLowerCase();
}

/**
 * Format discomfort percentage with 1 decimal.
 */
export function formatDiscomfortPct(val: number | null | undefined, decimals = 1): string {
  if (val == null || Number.isNaN(val)) return "Not available";
  return `${val.toFixed(decimals)}%`;
}

/**
 * Format annual HVAC energy with unit kWh/m²/yr.
 */
export function formatEnergyValue(val: number | null | undefined, decimals = 1): string {
  if (val == null || Number.isNaN(val)) return "Not available";
  return `${val.toFixed(decimals)} kWh/m²/yr`;
}

/**
 * Format O1 verification error: (verified - predicted).
 * Signed value with percentage points unit (pp).
 * Returns "Not verified" if verified value is missing or unverified.
 * Example: verified=36.6, predicted=37.7 -> "−1.1 pp".
 */
export function formatO1Error(
  verified: number | null | undefined,
  predicted: number | null | undefined
): string {
  if (
    verified == null ||
    predicted == null ||
    Number.isNaN(verified) ||
    Number.isNaN(predicted)
  ) {
    return "Not verified";
  }
  const delta = verified - predicted;
  const sign = delta < 0 ? "−" : delta > 0 ? "+" : "";
  return `${sign}${Math.abs(delta).toFixed(1)} pp`;
}

/**
 * Format O2 verification error: (verified - predicted).
 * Signed value with unit and relative percentage.
 * Returns "Not verified" if verified value is missing or unverified.
 * Example: verified=41.4, predicted=45.3 -> "−3.9 kWh/m²/yr (−9%)".
 */
export function formatO2Error(
  verified: number | null | undefined,
  predicted: number | null | undefined
): string {
  if (
    verified == null ||
    predicted == null ||
    Number.isNaN(verified) ||
    Number.isNaN(predicted)
  ) {
    return "Not verified";
  }
  const delta = verified - predicted;
  const pct = predicted !== 0 ? Math.round((delta / predicted) * 100) : 0;
  const sign = delta < 0 ? "−" : delta > 0 ? "+" : "";
  const pctSign = pct < 0 ? "−" : pct > 0 ? "+" : "";
  return `${sign}${Math.abs(delta).toFixed(1)} kWh/m²/yr (${pctSign}${Math.abs(pct)}%)`;
}
