"use client";

import React, { useState, useMemo } from "react";
import { CITIES_DATA, DEFAULT_DESIGN } from "@/lib/constants";
import { predictDesignObjectives } from "@/lib/surrogate";
import { getReferencesForCity } from "@/lib/data";
import { CityKey, DesignVariables } from "@/types";
import { Shelter3DViewer } from "@/components/shelter/Shelter3DViewer";
import {
  Sliders,
  TrendingDown,
  TrendingUp,
  AlertTriangle,
  ShieldCheck,
  RotateCcw,
  Sparkles,
  Zap,
  Thermometer,
  Layers
} from "lucide-react";

export default function EvaluatePage() {
  const [selectedCity, setSelectedCity] = useState<CityKey>("Jodhpur");
  const [design, setDesign] = useState<DesignVariables>(DEFAULT_DESIGN);

  const cityInfo = CITIES_DATA[selectedCity];
  const { r1, r2 } = getReferencesForCity(selectedCity);

  // Live predicted objectives
  const prediction = useMemo(() => {
    return predictDesignObjectives(selectedCity, design);
  }, [selectedCity, design]);

  // Improvements relative to R2 Conventional baseline
  const r2DiscomfortDelta = r2 ? Number((prediction.O1_ml - r2.O1_ml).toFixed(1)) : 0;
  const r2EnergyDelta = r2 ? Number((prediction.O2 - r2.O2).toFixed(1)) : 0;

  const handleVariableChange = <K extends keyof DesignVariables>(
    key: K,
    val: DesignVariables[K]
  ) => {
    setDesign((prev) => ({ ...prev, [key]: val }));
  };

  const resetToDefault = () => {
    setDesign(DEFAULT_DESIGN);
  };

  return (
    <div className="space-y-8 pb-16">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold text-white tracking-tight flex items-center space-x-3">
            <Sliders className="w-7 h-7 text-teal-400" />
            <span>Custom Shelter Design Evaluator</span>
          </h1>
          <p className="text-sm text-slate-300 mt-1 max-w-2xl">
            Simulate envelope configurations with instantaneous surrogate predictions calibrated across 10,000 EnergyPlus runs.
          </p>
        </div>

        {/* City Switcher Select */}
        <div className="flex items-center space-x-3 glass-panel p-2 rounded-2xl">
          <span className="text-xs font-mono text-slate-400">Target Station:</span>
          <select
            value={selectedCity}
            onChange={(e) => setSelectedCity(e.target.value as CityKey)}
            className="glass-input text-white font-semibold text-xs py-1.5 px-3 rounded-xl focus:outline-none focus:ring-1 focus:ring-teal-400"
          >
            {(Object.keys(CITIES_DATA) as CityKey[]).map((c) => (
              <option key={c} value={c} className="bg-slate-900 text-white">
                {CITIES_DATA[c].name} ({CITIES_DATA[c].zone})
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* Main Grid: Controls on Left, 3D + Metrics on Right */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
        {/* Left Column: 8 Design Variable Sliders */}
        <div className="lg:col-span-6 space-y-6">
          <div className="rounded-2xl glass-card p-6 space-y-5">
            <div className="flex items-center justify-between border-b border-white/10 pb-3">
              <h3 className="text-base font-bold text-white flex items-center space-x-2">
                <Sliders className="w-4 h-4 text-teal-400" />
                <span>Envelope Design Variables</span>
              </h3>
              <button
                onClick={resetToDefault}
                className="text-xs text-slate-400 hover:text-white flex items-center space-x-1 transition"
                title="Reset to default baseline design"
              >
                <RotateCcw className="w-3.5 h-3.5" />
                <span>Reset</span>
              </button>
            </div>

            {/* 1. Roof Insulation */}
            <div className="space-y-1.5">
              <div className="flex justify-between text-xs">
                <span className="font-medium text-slate-300">Roof Insulation Thickness</span>
                <span className="font-mono font-bold text-teal-400">{design.roof_insulation_thickness} mm</span>
              </div>
              <input
                type="range"
                min="0"
                max="150"
                step="5"
                value={design.roof_insulation_thickness}
                onChange={(e) => handleVariableChange("roof_insulation_thickness", Number(e.target.value))}
                className="w-full accent-teal-500 bg-slate-800 h-2 rounded-lg cursor-pointer"
              />
              <div className="flex justify-between text-[10px] text-slate-500 font-mono">
                <span>0 mm (Uninsulated)</span>
                <span>150 mm (Max)</span>
              </div>
            </div>

            {/* 2. Wall Insulation */}
            <div className="space-y-1.5">
              <div className="flex justify-between text-xs">
                <span className="font-medium text-slate-300">Wall Insulation Thickness</span>
                <span className="font-mono font-bold text-teal-400">{design.wall_insulation_thickness} mm</span>
              </div>
              <input
                type="range"
                min="0"
                max="150"
                step="5"
                value={design.wall_insulation_thickness}
                onChange={(e) => handleVariableChange("wall_insulation_thickness", Number(e.target.value))}
                className="w-full accent-teal-500 bg-slate-800 h-2 rounded-lg cursor-pointer"
              />
              <div className="flex justify-between text-[10px] text-slate-500 font-mono">
                <span>0 mm</span>
                <span>150 mm</span>
              </div>
            </div>

            {/* 3. Wall Mass Class */}
            <div className="space-y-1.5">
              <span className="font-medium text-xs text-slate-300 block">Thermal Wall Mass Class</span>
              <div className="grid grid-cols-3 gap-2">
                {(["light", "medium", "heavy"] as const).map((mass) => (
                  <button
                    key={mass}
                    onClick={() => handleVariableChange("wall_mass_class", mass)}
                    className={`py-2 px-3 rounded-xl text-xs font-semibold capitalize border transition ${
                      design.wall_mass_class === mass
                        ? "bg-teal-600/30 border-teal-500 text-teal-300"
                        : "bg-slate-900 border-slate-700 text-slate-400 hover:text-white"
                    }`}
                  >
                    {mass} {mass === "medium" ? "(Brick)" : mass === "heavy" ? "(Concrete)" : "(Timber)"}
                  </button>
                ))}
              </div>
            </div>

            {/* 4. Roof Solar Absorptance */}
            <div className="space-y-1.5">
              <div className="flex justify-between text-xs">
                <span className="font-medium text-slate-300">Roof Solar Absorptance</span>
                <span className="font-mono font-bold text-teal-400">
                  {design.roof_solar_absorptance.toFixed(2)}{" "}
                  <span className="text-[10px] font-normal text-slate-400">
                    ({design.roof_solar_absorptance <= 0.4 ? "Cool White" : "Dark/Standard"})
                  </span>
                </span>
              </div>
              <input
                type="range"
                min="0.30"
                max="0.90"
                step="0.05"
                value={design.roof_solar_absorptance}
                onChange={(e) => handleVariableChange("roof_solar_absorptance", Number(e.target.value))}
                className="w-full accent-teal-500 bg-slate-800 h-2 rounded-lg cursor-pointer"
              />
              <div className="flex justify-between text-[10px] text-slate-500 font-mono">
                <span>0.30 (Reflective White)</span>
                <span>0.90 (Dark Bitumen)</span>
              </div>
            </div>

            {/* 5. Window-to-Wall Ratio (WWR) */}
            <div className="space-y-1.5">
              <div className="flex justify-between text-xs">
                <span className="font-medium text-slate-300">Window-to-Wall Ratio (WWR)</span>
                <span className="font-mono font-bold text-teal-400">{design.wwr}%</span>
              </div>
              <input
                type="range"
                min="5"
                max="40"
                step="1"
                value={design.wwr}
                onChange={(e) => handleVariableChange("wwr", Number(e.target.value))}
                className="w-full accent-teal-500 bg-slate-800 h-2 rounded-lg cursor-pointer"
              />
              <div className="flex justify-between text-[10px] text-slate-500 font-mono">
                <span>5% (Min Aperture)</span>
                <span>40% (Max Glazing)</span>
              </div>
            </div>

            {/* 6. Orientation */}
            <div className="space-y-1.5">
              <div className="flex justify-between text-xs">
                <span className="font-medium text-slate-300">Orientation (Azimuth)</span>
                <span className="font-mono font-bold text-teal-400">{design.orientation}°</span>
              </div>
              <input
                type="range"
                min="0"
                max="355"
                step="5"
                value={design.orientation}
                onChange={(e) => handleVariableChange("orientation", Number(e.target.value))}
                className="w-full accent-teal-500 bg-slate-800 h-2 rounded-lg cursor-pointer"
              />
              <div className="flex justify-between text-[10px] text-slate-500 font-mono">
                <span>0° (North)</span>
                <span>90° (East)</span>
                <span>180° (South)</span>
                <span>270° (West)</span>
              </div>
            </div>

            {/* 7. Overhang Shading Depth */}
            <div className="space-y-1.5">
              <div className="flex justify-between text-xs">
                <span className="font-medium text-slate-300">Overhang Shading Depth</span>
                <span className="font-mono font-bold text-teal-400">{design.shading_depth.toFixed(2)} m</span>
              </div>
              <input
                type="range"
                min="0.0"
                max="1.0"
                step="0.05"
                value={design.shading_depth}
                onChange={(e) => handleVariableChange("shading_depth", Number(e.target.value))}
                className="w-full accent-teal-500 bg-slate-800 h-2 rounded-lg cursor-pointer"
              />
              <div className="flex justify-between text-[10px] text-slate-500 font-mono">
                <span>0.0 m (Flush)</span>
                <span>1.0 m (Deep Overhang)</span>
              </div>
            </div>

            {/* 8. Natural Ventilation */}
            <div className="space-y-1.5">
              <div className="flex justify-between text-xs">
                <span className="font-medium text-slate-300">Natural Ventilation Air Exchange</span>
                <span className="font-mono font-bold text-teal-400">{design.ventilation_ach.toFixed(1)} ACH</span>
              </div>
              <input
                type="range"
                min="1.0"
                max="15.0"
                step="0.5"
                value={design.ventilation_ach}
                onChange={(e) => handleVariableChange("ventilation_ach", Number(e.target.value))}
                className="w-full accent-teal-500 bg-slate-800 h-2 rounded-lg cursor-pointer"
              />
              <div className="flex justify-between text-[10px] text-slate-500 font-mono">
                <span>1.0 ACH (Closed)</span>
                <span>15.0 ACH (Cross Ventilation)</span>
              </div>
            </div>
          </div>
        </div>

        {/* Right Column: 3D Visualization + Predicted Objectives */}
        <div className="lg:col-span-6 space-y-6">
          {/* Interactive 3D Model */}
          <Shelter3DViewer design={design} />

          {/* Predicted Objectives Scorecard */}
          <div className="rounded-2xl glass-card p-6 space-y-4">
            <div className="flex items-center justify-between border-b border-white/10 pb-3">
              <div>
                <h3 className="text-base font-bold text-white flex items-center space-x-2">
                  <Sparkles className="w-4 h-4 text-teal-400" />
                  <span>Surrogate Model Predictions</span>
                </h3>
                <span className="text-xs text-slate-400">
                  Evaluated at {cityInfo.name} ({cityInfo.zone})
                </span>
              </div>

              {/* Accuracy badge */}
              <span className="text-[10px] font-mono px-2.5 py-1 rounded-xl glass-pill text-teal-300">
                Surrogate R² = {prediction.r2_O2}
              </span>
            </div>

            {/* Key Objective Cards */}
            <div className="grid grid-cols-2 gap-3">
              {/* O1 ML Discomfort */}
              <div className="p-4 rounded-xl glass-panel space-y-1">
                <span className="text-xs font-mono text-slate-400 block">
                  O1 Discomfort (ML Judge)
                </span>
                <div className="flex items-baseline space-x-2">
                  <span className="text-3xl font-black text-rose-400 font-mono">
                    {prediction.O1_ml}%
                  </span>
                </div>
                <div className="flex items-center space-x-3 text-[10px] font-mono text-slate-400 pt-1">
                  <span className="text-amber-300">Warm: {prediction.warm_ml}%</span>
                  <span className="text-sky-300">Cool: {prediction.cool_ml}%</span>
                </div>
              </div>

              {/* O2 Annual HVAC Energy */}
              <div className="p-4 rounded-xl glass-panel space-y-1">
                <span className="text-xs font-mono text-slate-400 block">
                  O2 Ideal-Loads Energy
                </span>
                <div className="flex items-baseline space-x-2">
                  <span className="text-3xl font-black text-amber-400 font-mono">
                    {prediction.O2}
                  </span>
                  <span className="text-xs text-slate-400 font-mono">kWh/m²/yr</span>
                </div>
                <div className="text-[10px] font-mono text-slate-400 pt-1">
                  Setpoints: 26°C cool / 20°C heat
                </div>
              </div>

              {/* O1 Adaptive 90% */}
              <div className="p-4 rounded-xl glass-panel space-y-1 col-span-2">
                <div className="flex justify-between items-center">
                  <span className="text-xs font-mono text-slate-400 block">
                    O1 Discomfort (ASHRAE 55 Adaptive 90% Judge)
                  </span>
                  <span className="text-[10px] font-mono text-slate-400">
                    Dual Comfort Judge
                  </span>
                </div>
                <div className="flex items-baseline space-x-2">
                  <span className="text-2xl font-black text-white font-mono">
                    {prediction.O1_adapt}%
                  </span>
                  <span className="text-xs text-slate-400 font-mono">
                    uncomfortable hours
                  </span>
                </div>
              </div>
            </div>

            {/* Comparison against R2 Conventional Reference Shelter */}
            <div className="pt-3 border-t border-slate-800 space-y-2">
              <span className="text-xs font-semibold text-slate-300 block">
                Side-by-Side vs R2 Conventional Shelter (Clay Brick, Uninsulated)
              </span>

              <div className="grid grid-cols-2 gap-2 text-xs font-mono">
                <div className="p-2.5 rounded-lg bg-slate-900/50 border border-slate-800 flex items-center justify-between">
                  <span className="text-slate-400 text-[11px]">Discomfort Delta:</span>
                  <span className={`font-bold flex items-center space-x-1 ${
                    r2DiscomfortDelta <= 0 ? "text-emerald-400" : "text-rose-400"
                  }`}>
                    {r2DiscomfortDelta <= 0 ? (
                      <TrendingDown className="w-3.5 h-3.5" />
                    ) : (
                      <TrendingUp className="w-3.5 h-3.5" />
                    )}
                    <span>{r2DiscomfortDelta > 0 ? `+${r2DiscomfortDelta}` : r2DiscomfortDelta}%</span>
                  </span>
                </div>

                <div className="p-2.5 rounded-lg bg-slate-900/50 border border-slate-800 flex items-center justify-between">
                  <span className="text-slate-400 text-[11px]">Energy Delta:</span>
                  <span className={`font-bold flex items-center space-x-1 ${
                    r2EnergyDelta <= 0 ? "text-emerald-400" : "text-rose-400"
                  }`}>
                    {r2EnergyDelta <= 0 ? (
                      <TrendingDown className="w-3.5 h-3.5" />
                    ) : (
                      <TrendingUp className="w-3.5 h-3.5" />
                    )}
                    <span>{r2EnergyDelta > 0 ? `+${r2EnergyDelta}` : r2EnergyDelta} kWh</span>
                  </span>
                </div>
              </div>
            </div>

            {/* Confidence & Applicability Note */}
            <div className="p-3 rounded-xl bg-slate-900/90 border border-slate-800 text-xs text-slate-300 flex items-start space-x-2">
              {prediction.confidence === "Medium" ? (
                <ShieldCheck className="w-4 h-4 text-emerald-400 shrink-0 mt-0.5" />
              ) : (
                <AlertTriangle className="w-4 h-4 text-amber-400 shrink-0 mt-0.5" />
              )}
              <span className="text-[11px] leading-relaxed">{prediction.confidenceNote}</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
