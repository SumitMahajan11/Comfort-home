/**
 * web/src/lib/glossary.ts
 *
 * Plain-language definitions for scientific and engineering concepts.
 * Technical terms are preserved in tooltips and the About page.
 */

export interface GlossaryEntry {
  term: string;          // Plain-language user-facing term
  technicalName: string; // Engineering / scientific term
  definition: string;    // Clear explanation for non-experts
}

export const GLOSSARY: Record<string, GlossaryEntry> = {
  pareto: {
    term: "best trade-off designs",
    technicalName: "Pareto frontier",
    definition:
      "A set of optimal designs where you cannot reduce discomfort hours any further without increasing cooling energy, and vice versa."
  },
  surrogate: {
    term: "fast estimator trained on simulations",
    technicalName: "XGBoost surrogate model",
    definition:
      "A machine-learning estimator trained on 10,000 EnergyPlus simulation runs that predicts annual comfort and energy demand in milliseconds."
  },
  o1: {
    term: "hours uncomfortable",
    technicalName: "Objective 1 (O1 discomfort)",
    definition:
      "The percentage of annual hours when indoor shelter conditions fall outside acceptable thermal comfort bounds."
  },
  o2: {
    term: "heating & cooling energy",
    technicalName: "Objective 2 (O2 energy)",
    definition:
      "The annual HVAC heating and cooling energy demand in kilowatt-hours per square meter per year (kWh/m²/yr)."
  },
  dualJudge: {
    term: "do our two comfort checks agree?",
    technicalName: "Dual-judge agreement (Adaptive 90% vs ML Champion)",
    definition:
      "Compares whether the standard physical adaptive comfort rule (ASHRAE 55) and the trained machine learning model agree on indoor comfort."
  },
  lowConfidence: {
    term: "treat as a rough guide",
    technicalName: "Low confidence tier (Decision D-017)",
    definition:
      "Indicates sparse local field data or lower agreement between comfort standards. Use recommendations as directional guidance rather than exact predictions."
  }
};
