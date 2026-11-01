"use client";

import React, { useState, useMemo } from "react";
import { getShapSummary } from "@/lib/data";
import { getSurrogateShapFeatures } from "@/lib/metrics";
import { CITIES_DATA } from "@/lib/constants";
import { CityKey } from "@/types";
import {
  Sparkles,
  Layers,
  Thermometer,
  Table as TableIcon,
  BarChart3,
  MapPin,
  Target,
  FileCode,
  Info
} from "lucide-react";

interface HorizontalBarItem {
  key: string;
  name: string;
  value: number;
  displayValue: string;
  detail: string;
  extra?: string;
}

export default function ExplainPage() {
  const shapData = getShapSummary();
  const [selectedCity, setSelectedCity] = useState<CityKey>("Jodhpur");
  const [selectedTarget, setSelectedTarget] = useState<"O1_ml" | "O1_adapt" | "O2">("O1_ml");

  const [showDb2Table, setShowDb2Table] = useState(false);
  const [showEnvelopeTable, setShowEnvelopeTable] = useState(false);
  const [showCityTable, setShowCityTable] = useState(false);

  // 1. ML Champion Comfort Model Feature Importance (ASHRAE DB II Complete Cases)
  // Sourced directly from data/processed/shap_champion_db2.csv / shap_summary.json
  const db2Items: HorizontalBarItem[] = useMemo(() => {
    return [
      {
        key: "ta",
        name: "Indoor air temperature (Ta)",
        value: 0.301,
        displayValue: "0.301",
        detail: "Direct convective heat transfer and sensation trigger across occupant survey records.",
        extra: "Cool: 0.406 | Warm: 0.398 | Neutral: 0.098"
      },
      {
        key: "t_outdoor",
        name: "Running mean outdoor temperature",
        value: 0.214,
        displayValue: "0.214",
        detail: "Governs seasonal physiological and behavioral adaptation history over previous 7 days.",
        extra: "Cool: 0.285 | Warm: 0.259 | Neutral: 0.099"
      },
      {
        key: "tr",
        name: "Mean radiant temperature (Tr)",
        value: 0.201,
        displayValue: "0.201",
        detail: "Primary driver of radiative discomfort boundaries, particularly in cold regimes.",
        extra: "Cool: 0.334 | Warm: 0.224 | Neutral: 0.044"
      },
      {
        key: "met",
        name: "Metabolic rate",
        value: 0.098,
        displayValue: "0.098",
        detail: "Internal human heat production baseline during seated and sedentary shelter activities.",
        extra: "Cool: 0.090 | Warm: 0.110 | Neutral: 0.095"
      },
      {
        key: "vel",
        name: "Air velocity",
        value: 0.092,
        displayValue: "0.092",
        detail: "Convective heat loss and sweat evaporation enhancement at elevated indoor air speeds.",
        extra: "Cool: 0.105 | Warm: 0.123 | Neutral: 0.048"
      },
      {
        key: "rh",
        name: "Relative humidity",
        value: 0.080,
        displayValue: "0.080",
        detail: "Inhibits evaporative skin cooling under warm-humid conditions when vapor pressure is high.",
        extra: "Cool: 0.068 | Warm: 0.097 | Neutral: 0.076"
      },
      {
        key: "clo",
        name: "Clothing insulation",
        value: 0.061,
        displayValue: "0.061",
        detail: "Thermal resistance barrier between occupant skin surface and ambient indoor environment.",
        extra: "Cool: 0.061 | Warm: 0.066 | Neutral: 0.054"
      }
    ].sort((a, b) => b.value - a.value);
  }, []);

  // 2. Surrogate Envelope Variable Importance Ranking (Relative Importance across 25 models)
  const envelopeItems: HorizontalBarItem[] = useMemo(() => {
    return [
      {
        key: "roof_absorptance",
        name: "Roof solar absorptance",
        value: 0.36,
        displayValue: "36%",
        detail: "Determines solar radiation absorbed by horizontal roof slab; low absorptance functions as cool roof."
      },
      {
        key: "roof_insulation",
        name: "Roof insulation thickness",
        value: 0.24,
        displayValue: "24%",
        detail: "Reduces conductive heat flux through roof slab; essential for extreme summer heat and winter cold."
      },
      {
        key: "wwr",
        name: "Window-to-wall ratio (WWR)",
        value: 0.16,
        displayValue: "16%",
        detail: "Governs solar heat gain coefficient apertures and conductive envelope thermal transfer."
      },
      {
        key: "shading_depth",
        name: "Overhang shading depth",
        value: 0.11,
        displayValue: "11%",
        detail: "Intercepts high-elevation solar radiation during hot summer hours while allowing diffuse daylight."
      },
      {
        key: "ventilation",
        name: "Natural ventilation rate",
        value: 0.07,
        displayValue: "7%",
        detail: "Flushes nocturnal indoor heat when ambient outdoor temperatures fall below indoor air."
      },
      {
        key: "wall_mass",
        name: "Wall thermal mass",
        value: 0.04,
        displayValue: "4%",
        detail: "Thermal inertia dampens diurnal temperature swings and delays peak heat hours."
      },
      {
        key: "wall_insulation",
        name: "Wall insulation thickness",
        value: 0.02,
        displayValue: "2%",
        detail: "Provides secondary conductive thermal resistance along vertical exterior facades."
      }
    ].sort((a, b) => b.value - a.value);
  }, []);

  // 3. City-specific empirical surrogate feature drivers from shap_summary.json
  const cityFeaturesRaw = useMemo(() => {
    return getSurrogateShapFeatures(selectedCity, selectedTarget);
  }, [selectedCity, selectedTarget]);

  const readableFeatureName = (rawName: string): string => {
    const map: Record<string, string> = {
      "wwr": "Window-to-wall ratio (WWR)",
      "wall_insulation_thickness": "Wall insulation thickness",
      "roof_insulation_thickness": "Roof insulation thickness",
      "shading_depth": "Overhang shading depth",
      "roof_solar_absorptance": "Roof solar absorptance",
      "ventilation_ach": "Natural ventilation rate",
      "wall_mass_light": "Wall mass: Light (sheet)",
      "orientation": "Orientation (azimuth)",
      "wall_mass_heavy": "Wall mass: Heavy (concrete)",
      "wall_mass_medium": "Wall mass: Medium (clay brick)"
    };
    return map[rawName] || rawName;
  };

  const cityItems: HorizontalBarItem[] = useMemo(() => {
    return cityFeaturesRaw.map(f => ({
      key: f.feature,
      name: readableFeatureName(f.feature),
      value: f.mean_abs_shap,
      displayValue: f.mean_abs_shap.toFixed(2),
      detail: `Empirical sensitivity driver for ${selectedCity} under ${selectedTarget} surrogate evaluation.`
    })).sort((a, b) => b.value - a.value);
  }, [cityFeaturesRaw, selectedCity, selectedTarget]);

  const targetLabel = selectedTarget === "O1_ml"
    ? "Discomfort (ML Judge)"
    : selectedTarget === "O1_adapt"
    ? "Discomfort (Adaptive 90%)"
    : "HVAC Energy";

  const targetUnit = selectedTarget === "O2" ? "kWh/m²/yr" : "% discomfort";

  return (
    <div className="space-y-8 pb-16">
      {/* Header */}
      <div className="border-b border-[var(--line)] pb-4">
        <h1 className="text-3xl font-semibold text-[var(--ink)] tracking-tight flex items-center space-x-3">
          <Sparkles className="w-7 h-7 text-[var(--primary)]" />
          <span>Explainability & SHAP Feature Attribution</span>
        </h1>
        <p className="text-sm text-[var(--ink-2)] mt-1.5 max-w-3xl leading-relaxed">
          TreeExplainer SHAP values quantify feature contributions for the champion comfort model and surrogate estimators.
          Attributions indicate the relative impact of physiological variables and envelope parameters on discomfort hours and HVAC energy.
        </p>
      </div>

      {/* Grid: Global Model SHAP & Surrogate Sensitivity */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        {/* Card 1: Comfort Model Physiological SHAP */}
        <div className="rounded-[8px] border border-[var(--line)] bg-[var(--surface)] p-6 space-y-4 flex flex-col justify-between">
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold text-[var(--primary)] tracking-wide uppercase">
                Phase 6 global attribution
              </span>
              <button
                onClick={() => setShowDb2Table(!showDb2Table)}
                className="text-xs font-medium text-[var(--link)] hover:underline flex items-center space-x-1"
                aria-expanded={showDb2Table}
              >
                {showDb2Table ? <BarChart3 className="w-3.5 h-3.5" /> : <TableIcon className="w-3.5 h-3.5" />}
                <span>{showDb2Table ? "Show as chart" : "Show as table"}</span>
              </button>
            </div>
            <h2 className="text-lg font-semibold text-[var(--ink)]">
              ML champion comfort model feature importance
            </h2>
            <p className="text-xs text-[var(--ink-2)]">
              Mean absolute SHAP impact computed across ASHRAE DB II complete-case evaluation records.
            </p>
            <div className="text-[13px] text-[var(--ink-2)] bg-[var(--surface-2)] p-2.5 rounded-[6px] border border-[var(--line)]">
              <span className="font-semibold text-[var(--ink)]">How to read this: </span>
              Bars represent the average magnitude of change (|SHAP|) that each physiological variable causes in predicted thermal comfort.
            </div>
          </div>

          {/* Chart or Table */}
          {showDb2Table ? (
            <div className="overflow-x-auto rounded-[var(--radius)] border border-[var(--line)]">
              <table className="w-full text-left text-[13px] border-collapse">
                <thead>
                  <tr className="bg-[var(--surface-2)] border-b border-[var(--line)] text-[var(--ink)] font-semibold">
                    <th className="py-2.5 px-3">Physiological variable</th>
                    <th className="py-2.5 px-3 text-right">Mean |SHAP|</th>
                    <th className="py-2.5 px-3">Role</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-[var(--line)]">
                  {db2Items.map((item) => (
                    <tr key={item.key} className="hover:bg-[var(--surface-2)] transition-colors">
                      <td className="py-2 px-3 font-medium text-[var(--ink)]">{item.name}</td>
                      <td className="py-2 px-3 text-right font-mono font-semibold text-[var(--ink)] tabular-nums">
                        {item.displayValue}
                      </td>
                      <td className="py-2 px-3 text-xs text-[var(--ink-2)]">{item.detail}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <div className="space-y-2.5 py-2">
              {db2Items.map((item) => {
                const maxVal = 0.35;
                const widthPct = Math.min(100, Math.max(3, (item.value / maxVal) * 100));
                return (
                  <div key={item.key} className="flex items-center space-x-3 text-[13px]">
                    <div
                      className="w-[210px] min-w-[210px] shrink-0 text-right font-medium text-[var(--ink)] line-clamp-2 leading-snug"
                      title={item.name}
                    >
                      {item.name}
                    </div>
                    <div className="flex-1 flex items-center space-x-2">
                      <div className="flex-1 bg-[var(--surface-2)] h-7 rounded-[4px] overflow-hidden flex items-center p-0.5">
                        <div
                          style={{ width: `${widthPct}%` }}
                          className="h-full bg-[var(--link)] rounded-[3px] transition-all duration-300"
                        />
                      </div>
                      <span className="w-12 shrink-0 text-left font-mono font-semibold text-[13px] text-[var(--ink)] tabular-nums">
                        {item.displayValue}
                      </span>
                    </div>
                  </div>
                );
              })}

              {/* X-Axis Scale & Title */}
              <div className="pt-2 pl-[222px] pr-12">
                <div className="flex justify-between text-[11px] font-mono text-[var(--ink-2)] border-t border-[var(--line)] pt-1">
                  <span>0.00</span>
                  <span>0.10</span>
                  <span>0.20</span>
                  <span>0.30</span>
                  <span>0.35</span>
                </div>
                <div className="text-left text-[13px] font-semibold text-[var(--ink-2)] mt-1.5">
                  Mean |SHAP| (impact on prediction)
                </div>
              </div>
            </div>
          )}

          {/* Neutral Scientific Insight */}
          <div className="p-3 rounded-[8px] bg-[var(--surface-2)] border border-[var(--line)] text-xs text-[var(--ink)] space-y-1">
            <div className="font-semibold text-[var(--ink)] flex items-center space-x-1.5">
              <Thermometer className="w-3.5 h-3.5 text-[var(--primary)]" />
              <span>Key physiological finding (Decision D-005):</span>
            </div>
            <p className="text-[12px] leading-relaxed text-[var(--ink-2)]">
              Mean radiant temperature (Tr) exhibits a mean |SHAP| impact of 0.201 overall and 0.334 under cool sensation conditions, comparable to indoor air temperature (Ta = 0.301 overall).
              This suggests that assuming Tr equals Ta would obscure the primary radiative heat transfer mechanism evaluated by comfort models.
            </p>
          </div>
        </div>

        {/* Card 2: Envelope Design Variable Sensitivity */}
        <div className="rounded-[8px] border border-[var(--line)] bg-[var(--surface)] p-6 space-y-4 flex flex-col justify-between">
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold text-[var(--primary)] tracking-wide uppercase">
                Surrogate model sensitivity
              </span>
              <button
                onClick={() => setShowEnvelopeTable(!showEnvelopeTable)}
                className="text-xs font-medium text-[var(--link)] hover:underline flex items-center space-x-1"
                aria-expanded={showEnvelopeTable}
              >
                {showEnvelopeTable ? <BarChart3 className="w-3.5 h-3.5" /> : <TableIcon className="w-3.5 h-3.5" />}
                <span>{showEnvelopeTable ? "Show as chart" : "Show as table"}</span>
              </button>
            </div>
            <h2 className="text-lg font-semibold text-[var(--ink)]">
              Envelope design variables importance ranking
            </h2>
            <p className="text-xs text-[var(--ink-2)]">
              Relative gain attribution across 25 XGBoost surrogate models predicting O1 and O2.
            </p>
            <div className="text-[13px] text-[var(--ink-2)] bg-[var(--surface-2)] p-2.5 rounded-[6px] border border-[var(--line)]">
              <span className="font-semibold text-[var(--ink)]">How to read this: </span>
              Bars indicate the relative share of model split gain attributed to each architectural envelope variable across surrogate estimators.
            </div>
          </div>

          {/* Chart or Table */}
          {showEnvelopeTable ? (
            <div className="overflow-x-auto rounded-[var(--radius)] border border-[var(--line)]">
              <table className="w-full text-left text-[13px] border-collapse">
                <thead>
                  <tr className="bg-[var(--surface-2)] border-b border-[var(--line)] text-[var(--ink)] font-semibold">
                    <th className="py-2.5 px-3">Envelope variable</th>
                    <th className="py-2.5 px-3 text-right">Relative share</th>
                    <th className="py-2.5 px-3">Physical mechanism</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-[var(--line)]">
                  {envelopeItems.map((item) => (
                    <tr key={item.key} className="hover:bg-[var(--surface-2)] transition-colors">
                      <td className="py-2 px-3 font-medium text-[var(--ink)]">{item.name}</td>
                      <td className="py-2 px-3 text-right font-mono font-semibold text-[var(--ink)] tabular-nums">
                        {item.displayValue}
                      </td>
                      <td className="py-2 px-3 text-xs text-[var(--ink-2)]">{item.detail}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <div className="space-y-2.5 py-2">
              {envelopeItems.map((item) => {
                const maxVal = 0.40;
                const widthPct = Math.min(100, Math.max(3, (item.value / maxVal) * 100));
                return (
                  <div key={item.key} className="flex items-center space-x-3 text-[13px]">
                    <div
                      className="w-[210px] min-w-[210px] shrink-0 text-right font-medium text-[var(--ink)] line-clamp-2 leading-snug"
                      title={item.name}
                    >
                      {item.name}
                    </div>
                    <div className="flex-1 flex items-center space-x-2">
                      <div className="flex-1 bg-[var(--surface-2)] h-7 rounded-[4px] overflow-hidden flex items-center p-0.5">
                        <div
                          style={{ width: `${widthPct}%` }}
                          className="h-full bg-[var(--primary)] rounded-[3px] transition-all duration-300"
                        />
                      </div>
                      <span className="w-12 shrink-0 text-left font-mono font-semibold text-[13px] text-[var(--ink)] tabular-nums">
                        {item.displayValue}
                      </span>
                    </div>
                  </div>
                );
              })}

              {/* X-Axis Scale & Title */}
              <div className="pt-2 pl-[222px] pr-12">
                <div className="flex justify-between text-[11px] font-mono text-[var(--ink-2)] border-t border-[var(--line)] pt-1">
                  <span>0%</span>
                  <span>10%</span>
                  <span>20%</span>
                  <span>30%</span>
                  <span>40%</span>
                </div>
                <div className="text-left text-[13px] font-semibold text-[var(--ink-2)] mt-1.5">
                  Relative importance
                </div>
              </div>
            </div>
          )}

          {/* Neutral Scientific Insight */}
          <div className="p-3 rounded-[8px] bg-[var(--surface-2)] border border-[var(--line)] text-xs text-[var(--ink)] space-y-1">
            <div className="font-semibold text-[var(--ink)] flex items-center space-x-1.5">
              <Layers className="w-3.5 h-3.5 text-[var(--primary)]" />
              <span>Architectural insight:</span>
            </div>
            <p className="text-[12px] leading-relaxed text-[var(--ink-2)]">
              Roof solar absorptance and roof insulation thickness account for 60% of total surrogate model gain across single-zone shelters.
              This suggests that horizontal roof envelope interventions dominate annual discomfort and HVAC energy reduction.
            </p>
          </div>
        </div>
      </div>

      {/* Section 3: City-Specific Empirical Surrogate Sensitivities */}
      <div className="rounded-[8px] border border-[var(--line)] bg-[var(--surface)] p-6 space-y-6">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-[var(--line)] pb-4">
          <div>
            <span className="text-xs font-semibold text-[var(--primary)] tracking-wide uppercase">
              City-specific sensitivity
            </span>
            <h2 className="text-lg font-semibold text-[var(--ink)] mt-0.5">
              Empirical surrogate feature drivers in {CITIES_DATA[selectedCity]?.name || selectedCity}
            </h2>
            <p className="text-xs text-[var(--ink-2)] mt-0.5">
              Target: <span className="font-semibold text-[var(--ink)]">{targetLabel}</span> ({targetUnit}).
            </p>
          </div>

          {/* City Selector Buttons */}
          <div className="flex flex-wrap items-center gap-1.5 bg-[var(--surface-2)] p-1 rounded-[6px] border border-[var(--line)]">
            {(Object.keys(CITIES_DATA) as CityKey[]).map((cityKey) => {
              const active = selectedCity === cityKey;
              return (
                <button
                  key={cityKey}
                  onClick={() => setSelectedCity(cityKey)}
                  className={`px-3 py-1.5 text-xs font-medium rounded-[4px] transition-all flex items-center space-x-1 ${
                    active
                      ? "bg-[var(--surface)] text-[var(--primary)] font-semibold shadow-sm border border-[var(--line)]"
                      : "text-[var(--ink-2)] hover:text-[var(--ink)]"
                  }`}
                >
                  <MapPin className="w-3 h-3" />
                  <span>{CITIES_DATA[cityKey].name}</span>
                </button>
              );
            })}
          </div>
        </div>

        {/* Target Switcher & Table Toggle */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div className="flex items-center space-x-2">
            <span className="text-xs font-semibold text-[var(--ink)] flex items-center space-x-1">
              <Target className="w-3.5 h-3.5 text-[var(--primary)]" />
              <span>Objective:</span>
            </span>
            <div className="inline-flex rounded-[6px] border border-[var(--line)] bg-[var(--surface-2)] p-0.5 text-xs">
              <button
                onClick={() => setSelectedTarget("O1_ml")}
                className={`px-2.5 py-1 rounded-[4px] font-medium transition-colors ${
                  selectedTarget === "O1_ml"
                    ? "bg-[var(--surface)] text-[var(--ink)] font-semibold shadow-sm"
                    : "text-[var(--ink-2)] hover:text-[var(--ink)]"
                }`}
              >
                Discomfort (ML)
              </button>
              <button
                onClick={() => setSelectedTarget("O1_adapt")}
                className={`px-2.5 py-1 rounded-[4px] font-medium transition-colors ${
                  selectedTarget === "O1_adapt"
                    ? "bg-[var(--surface)] text-[var(--ink)] font-semibold shadow-sm"
                    : "text-[var(--ink-2)] hover:text-[var(--ink)]"
                }`}
              >
                Discomfort (Adaptive)
              </button>
              <button
                onClick={() => setSelectedTarget("O2")}
                className={`px-2.5 py-1 rounded-[4px] font-medium transition-colors ${
                  selectedTarget === "O2"
                    ? "bg-[var(--surface)] text-[var(--ink)] font-semibold shadow-sm"
                    : "text-[var(--ink-2)] hover:text-[var(--ink)]"
                }`}
              >
                HVAC Energy (O2)
              </button>
            </div>
          </div>

          <button
            onClick={() => setShowCityTable(!showCityTable)}
            className="text-xs font-medium text-[var(--link)] hover:underline flex items-center space-x-1 self-start sm:self-auto"
            aria-expanded={showCityTable}
          >
            {showCityTable ? <BarChart3 className="w-3.5 h-3.5" /> : <TableIcon className="w-3.5 h-3.5" />}
            <span>{showCityTable ? "Show as chart" : "Show as table"}</span>
          </button>
        </div>

        <div className="text-[13px] text-[var(--ink-2)] bg-[var(--surface-2)] p-2.5 rounded-[6px] border border-[var(--line)]">
          <span className="font-semibold text-[var(--ink)]">How to read this: </span>
          Bars quantify the empirical mean absolute SHAP impact of each design variable on {targetLabel.toLowerCase()} in {CITIES_DATA[selectedCity]?.name}.
        </div>

        {/* City Chart or Table */}
        {showCityTable ? (
          <div className="overflow-x-auto rounded-[var(--radius)] border border-[var(--line)]">
            <table className="w-full text-left text-[13px] border-collapse">
              <thead>
                <tr className="bg-[var(--surface-2)] border-b border-[var(--line)] text-[var(--ink)] font-semibold">
                  <th className="py-2.5 px-3">Design parameter</th>
                  <th className="py-2.5 px-3 text-right">Mean |SHAP|</th>
                  <th className="py-2.5 px-3">Context</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[var(--line)]">
                {cityItems.map((item, idx) => (
                  <tr key={item.key} className="hover:bg-[var(--surface-2)] transition-colors">
                    <td className="py-2 px-3 font-medium text-[var(--ink)]">
                      <span className="text-xs text-[var(--ink-2)] font-mono mr-2">#{idx + 1}</span>
                      {item.name}
                    </td>
                    <td className="py-2 px-3 text-right font-mono font-semibold text-[var(--ink)] tabular-nums">
                      {item.displayValue}
                    </td>
                    <td className="py-2 px-3 text-xs text-[var(--ink-2)]">{item.detail}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="space-y-2.5 py-2">
            {cityItems.map((item) => {
              const maxVal = Math.max(...cityItems.map(c => c.value), 1.0);
              const widthPct = Math.min(100, Math.max(3, (item.value / maxVal) * 100));
              return (
                <div key={item.key} className="flex items-center space-x-3 text-[13px]">
                  <div
                    className="w-[210px] min-w-[210px] shrink-0 text-right font-medium text-[var(--ink)] line-clamp-2 leading-snug"
                    title={item.name}
                  >
                    {item.name}
                  </div>
                  <div className="flex-1 flex items-center space-x-2">
                    <div className="flex-1 bg-[var(--surface-2)] h-7 rounded-[4px] overflow-hidden flex items-center p-0.5">
                      <div
                        style={{ width: `${widthPct}%` }}
                        className="h-full bg-[var(--good)] rounded-[3px] transition-all duration-300"
                      />
                    </div>
                    <span className="w-16 shrink-0 text-left font-mono font-semibold text-[13px] text-[var(--ink)] tabular-nums">
                      {item.displayValue}
                    </span>
                  </div>
                </div>
              );
            })}

            {/* Scale Label */}
            <div className="pt-2 pl-[222px] pr-16 text-left text-[13px] font-semibold text-[var(--ink-2)] border-t border-[var(--line)]">
              Mean |SHAP| (impact on prediction)
            </div>
          </div>
        )}

        {/* City Insight */}
        {cityItems.length > 0 && (
          <div className="p-3 rounded-[8px] bg-[var(--surface-2)] border border-[var(--line)] text-xs text-[var(--ink)] space-y-1">
            <span className="font-semibold text-[var(--ink)]">Regional sensitivity summary:</span>
            <p className="text-[12px] leading-relaxed text-[var(--ink-2)]">
              In {CITIES_DATA[selectedCity]?.name}, {cityItems[0]?.name.toLowerCase()} is the leading sensitivity driver with a mean |SHAP| of {cityItems[0]?.displayValue} on {targetLabel.toLowerCase()}.
              This suggests that passive interventions in this climate zone should prioritize {cityItems[0]?.name.toLowerCase()} to modulate thermal performance.
            </p>
          </div>
        )}

        {/* Section 4: Transparent Disclosure on Local Waterfall Attribution */}
        <div className="rounded-[8px] border border-[var(--line)] bg-[var(--surface-2)] p-5 space-y-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-2">
              <FileCode className="w-4 h-4 text-[var(--warn)]" />
              <h3 className="text-sm font-semibold text-[var(--ink)]">
                Local Instance Attribution (Micro-Waterfall Decomposition)
              </h3>
            </div>
            <span className="text-[11px] font-semibold px-2 py-0.5 rounded bg-[var(--surface)] border border-[var(--line)] text-[var(--ink-2)]">
              Status: Not available in static export
            </span>
          </div>

          <p className="text-xs text-[var(--ink-2)] leading-relaxed">
            Single-building additive micro-waterfalls require evaluating candidate design vectors against Reference R2 baselines using live TreeExplainer tree-path traversal.
            The client-side bundle serves offline static JSON artifacts from <code className="text-[11px]">shap_summary.json</code> to adhere to Decision S4 offline operation rules.
          </p>

          <div className="text-xs text-[var(--ink)] bg-[var(--surface)] p-3 rounded-[6px] border border-[var(--line)] space-y-2">
            <div className="font-semibold text-[var(--ink)] flex items-center space-x-1.5">
              <Info className="w-3.5 h-3.5 text-[var(--primary)]" />
              <span>Pipeline specification for export_web_data.py:</span>
            </div>
            <ol className="list-decimal pl-5 space-y-1 text-[12px] text-[var(--ink-2)]">
              <li>
                <strong>Model persistence:</strong> Serialize and load all 25 XGBoost surrogate models (<code className="text-[11px]">models/surrogate_[city]_[target].joblib</code>).
              </li>
              <li>
                <strong>Baseline vector evaluation:</strong> Compute TreeExplainer attributions on Reference R2 Conventional shelter vector <code className="text-[11px]">x_base</code>.
              </li>
              <li>
                <strong>Design vector evaluation:</strong> Compute TreeExplainer attributions on verified candidate design vector <code className="text-[11px]">x_design</code>.
              </li>
              <li>
                <strong>Exact additivity verification:</strong> Assert that delta contributions sum to headline delta within machine tolerance (<code className="text-[11px]">|sum(delta_shap) - delta_pred| &lt; 1e-4</code>).
              </li>
              <li>
                <strong>Static export:</strong> Emit verified attribution arrays to <code className="text-[11px]">web/public/data/waterfall_[city].json</code>.
              </li>
            </ol>
          </div>
        </div>
      </div>
    </div>
  );
}
