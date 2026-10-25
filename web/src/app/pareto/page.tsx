"use client";

import React, { useState, useMemo, Suspense } from "react";
import { useSearchParams } from "next/navigation";
import { CITIES_DATA } from "@/lib/constants";
import { getParetoDesigns, getReferencesForCity, getS3ResultForCity } from "@/lib/data";
import { CityKey, ParetoDesign } from "@/types";
import {
  Layers,
  Sparkles,
  Download,
  Filter,
  CheckCircle2,
  Star,
  Award,
  ArrowRight,
  TrendingDown,
  Info,
  Table as TableIcon,
  Sliders
} from "lucide-react";
import {
  ResponsiveContainer,
  ScatterChart,
  Scatter,
  XAxis,
  YAxis,
  ZAxis,
  Tooltip,
  Legend,
  CartesianGrid,
  ReferenceDot
} from "recharts";

function ParetoExplorerContent() {
  const searchParams = useSearchParams();
  const initialCity = (searchParams?.get("city") as CityKey) || "Jodhpur";
  const [selectedCity, setSelectedCity] = useState<CityKey>(initialCity);
  const [selectedDesignId, setSelectedDesignId] = useState<string | null>(null);
  const [filterVerifiedOnly, setFilterVerifiedOnly] = useState<boolean>(false);
  const [showTable, setShowTable] = useState<boolean>(false);

  const cityInfo = CITIES_DATA[selectedCity];
  const { r1, r2 } = getReferencesForCity(selectedCity);
  const s3Result = getS3ResultForCity(selectedCity);
  const allDesigns = useMemo(() => getParetoDesigns(selectedCity), [selectedCity]);

  // Filtered designs
  const displayDesigns = useMemo(() => {
    if (filterVerifiedOnly) {
      return allDesigns.filter((d) => d.is_verified);
    }
    return allDesigns;
  }, [allDesigns, filterVerifiedOnly]);

  // Selected design object (default to knee point or first design)
  const selectedDesign = useMemo(() => {
    if (selectedDesignId) {
      const found = allDesigns.find((d) => d.pareto_id === selectedDesignId);
      if (found) return found;
    }
    // Default to knee point (middle of Pareto front)
    return allDesigns[Math.floor(allDesigns.length / 2)] || allDesigns[0];
  }, [allDesigns, selectedDesignId]);

  // Presets
  const applyPreset = (preset: "lowest_discomfort" | "lowest_energy" | "knee") => {
    if (preset === "lowest_discomfort") {
      const best = [...allDesigns].sort((a, b) => a.O1_ml - b.O1_ml)[0];
      if (best) setSelectedDesignId(best.pareto_id);
    } else if (preset === "lowest_energy") {
      const best = [...allDesigns].sort((a, b) => a.O2 - b.O2)[0];
      if (best) setSelectedDesignId(best.pareto_id);
    } else {
      const knee = allDesigns[Math.floor(allDesigns.length / 2)];
      if (knee) setSelectedDesignId(knee.pareto_id);
    }
  };

  const exportSelectedDesignJson = () => {
    if (!selectedDesign) return;
    const blob = new Blob([JSON.stringify(selectedDesign, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `ClimateAdapt_Shelter_${selectedCity}_${selectedDesign.pareto_id}.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="space-y-8 pb-16">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-800 pb-4">
        <div>
          <div className="flex items-center space-x-2">
            <h1 className="text-3xl font-bold text-white tracking-tight flex items-center space-x-3">
              <Layers className="w-7 h-7 text-teal-400" />
              <span>Multi-Objective Pareto Explorer</span>
            </h1>
            <span className="px-2.5 py-0.5 rounded-full text-xs font-bold bg-teal-950 text-teal-400 border border-teal-700">
              Flagship
            </span>
          </div>
          <p className="text-sm text-slate-300 mt-1 max-w-2xl">
            Non-dominated shelter designs derived by NSGA-II optimization (Pop=100, Gen=200, seed 42) minimizing occupant discomfort hours and annual HVAC energy.
          </p>
        </div>

        {/* City Picker */}
        <div className="flex items-center space-x-3 bg-slate-900 border border-slate-700/60 p-2 rounded-xl">
          <span className="text-xs font-mono text-slate-400">Target Station:</span>
          <select
            value={selectedCity}
            onChange={(e) => {
              setSelectedCity(e.target.value as CityKey);
              setSelectedDesignId(null);
            }}
            className="bg-slate-800 text-white font-semibold text-xs py-1.5 px-3 rounded-lg border border-slate-700 focus:outline-none"
          >
            {(Object.keys(CITIES_DATA) as CityKey[]).map((c) => (
              <option key={c} value={c}>
                {CITIES_DATA[c].name} ({CITIES_DATA[c].zone})
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* Recommend For Me Presets */}
      <div className="flex flex-wrap items-center justify-between gap-3 p-4 rounded-2xl glass-panel border border-slate-700/60">
        <div className="flex items-center space-x-2">
          <Sparkles className="w-4 h-4 text-teal-400" />
          <span className="text-xs font-bold text-white uppercase tracking-wider font-mono">
            Recommend For Me:
          </span>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <button
            onClick={() => applyPreset("lowest_discomfort")}
            className="px-3.5 py-1.5 rounded-lg text-xs font-semibold bg-rose-950/60 hover:bg-rose-900/80 text-rose-300 border border-rose-700/50 transition flex items-center space-x-1.5"
          >
            <TrendingDown className="w-3.5 h-3.5" />
            <span>Lowest Discomfort Hours</span>
          </button>
          <button
            onClick={() => applyPreset("lowest_energy")}
            className="px-3.5 py-1.5 rounded-lg text-xs font-semibold bg-amber-950/60 hover:bg-amber-900/80 text-amber-300 border border-amber-700/50 transition flex items-center space-x-1.5"
          >
            <TrendingDown className="w-3.5 h-3.5" />
            <span>Lowest HVAC Energy</span>
          </button>
          <button
            onClick={() => applyPreset("knee")}
            className="px-3.5 py-1.5 rounded-lg text-xs font-semibold bg-teal-950/80 hover:bg-teal-900 text-teal-300 border border-teal-600 transition flex items-center space-x-1.5 shadow"
          >
            <Award className="w-3.5 h-3.5" />
            <span>Balanced (Knee Point Design)</span>
          </button>
        </div>

        {/* View toggles */}
        <div className="flex items-center space-x-2 text-xs">
          <label className="flex items-center space-x-1.5 cursor-pointer text-slate-300">
            <input
              type="checkbox"
              checked={filterVerifiedOnly}
              onChange={(e) => setFilterVerifiedOnly(e.target.checked)}
              className="accent-teal-500 rounded"
            />
            <span>EnergyPlus Verified Only</span>
          </label>
          <button
            onClick={() => setShowTable(!showTable)}
            className="p-1.5 rounded-lg bg-slate-800 text-slate-300 hover:text-white transition ml-2"
            title="Toggle data table"
          >
            <TableIcon className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Main Section: Scatter Chart + Selected Design Inspector */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
        {/* Pareto Scatter Chart */}
        <div className="lg:col-span-8 rounded-2xl glass-card p-6 space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="text-base font-bold text-white flex items-center space-x-2">
                <span>Pareto Trade-Off Frontier: Discomfort vs Energy</span>
              </h3>
              <p className="text-xs text-slate-400 mt-0.5">
                Click any point to inspect full envelope variables and verification error.
              </p>
            </div>
            <div className="flex items-center space-x-3 text-xs font-mono">
              <span className="flex items-center space-x-1 text-teal-400">
                <span className="w-2.5 h-2.5 rounded-full bg-teal-400 inline-block" />
                <span>Pareto ({displayDesigns.length})</span>
              </span>
              <span className="flex items-center space-x-1 text-amber-400">
                <Star className="w-3.5 h-3.5 text-amber-400" />
                <span>Verified ({s3Result?.n_designs_beating_both})</span>
              </span>
            </div>
          </div>

          <div className="w-full h-80 sm:h-96">
            <ResponsiveContainer width="100%" height="100%">
              <ScatterChart margin={{ top: 20, right: 20, bottom: 20, left: 10 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#1E293B" />
                <XAxis
                  type="number"
                  dataKey="O1_ml"
                  name="O1 ML Discomfort"
                  unit="%"
                  stroke="#94A3B8"
                  fontSize={11}
                  domain={["auto", "auto"]}
                  label={{ value: "Occupant Discomfort Hours O1_ml (%)", position: "bottom", fill: "#94A3B8", fontSize: 11 }}
                />
                <YAxis
                  type="number"
                  dataKey="O2"
                  name="O2 HVAC Energy"
                  unit=" kWh"
                  stroke="#94A3B8"
                  fontSize={11}
                  domain={["auto", "auto"]}
                  label={{ value: "Annual HVAC Energy O2 (kWh/m²/yr)", angle: -90, position: "left", fill: "#94A3B8", fontSize: 11 }}
                />
                <ZAxis range={[50, 180]} />
                <Tooltip
                  cursor={{ strokeDasharray: "3 3" }}
                  content={({ active, payload }) => {
                    if (active && payload && payload.length) {
                      const data = payload[0].payload as ParetoDesign;
                      return (
                        <div className="p-3 rounded-xl bg-slate-900/95 border border-slate-700 shadow-xl text-xs space-y-1 font-mono">
                          <div className="font-bold text-white flex items-center justify-between">
                            <span>{data.pareto_id}</span>
                            {data.is_verified && <span className="text-amber-400">★ Verified</span>}
                          </div>
                          <div className="text-rose-400">O1 ML Discomfort: {data.O1_ml.toFixed(1)}%</div>
                          <div className="text-amber-400">O2 HVAC Energy: {data.O2.toFixed(1)} kWh/m²</div>
                          <div className="text-slate-400">Adaptive 90%: {data.O1_adapt.toFixed(1)}%</div>
                          <div className="text-[10px] text-teal-400 pt-1">Click point to view envelope</div>
                        </div>
                      );
                    }
                    return null;
                  }}
                />

                {/* Pareto scatter dots */}
                <Scatter
                  name="Pareto Designs"
                  data={displayDesigns}
                  fill="#2A7F8E"
                  onClick={(node: any) => setSelectedDesignId(node.pareto_id)}
                  className="cursor-pointer"
                />

                {/* Reference Shelter R1 Lightweight Dot */}
                {r1 && (
                  <ReferenceDot
                    x={r1.O1_ml}
                    y={r1.O2}
                    r={7}
                    fill="#EF4444"
                    stroke="#FFFFFF"
                    strokeWidth={2}
                    label={{ value: "R1 Lightweight", position: "top", fill: "#EF4444", fontSize: 10 }}
                  />
                )}

                {/* Reference Shelter R2 Conventional Dot */}
                {r2 && (
                  <ReferenceDot
                    x={r2.O1_ml}
                    y={r2.O2}
                    r={7}
                    fill="#F59E0B"
                    stroke="#FFFFFF"
                    strokeWidth={2}
                    label={{ value: "R2 Conventional", position: "top", fill: "#F59E0B", fontSize: 10 }}
                  />
                )}
              </ScatterChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Selected Design Card & Verification Inspector */}
        <div className="lg:col-span-4 space-y-4">
          <div className="rounded-2xl glass-card p-6 space-y-4">
            <div className="flex items-center justify-between border-b border-white/10 pb-3">
              <div>
                <span className="text-[10px] font-mono uppercase tracking-wider text-teal-400 block">
                  Design Inspector
                </span>
                <h3 className="text-lg font-bold text-white flex items-center space-x-2">
                  <span>{selectedDesign?.pareto_id || "Design"}</span>
                  {selectedDesign?.is_verified && (
                    <span className="px-2.5 py-0.5 rounded-full text-[10px] font-bold glass-pill text-amber-300 border-amber-400/40 shadow-[0_0_10px_rgba(245,158,11,0.25)]">
                      ★ EnergyPlus Verified
                    </span>
                  )}
                </h3>
              </div>

              <button
                onClick={exportSelectedDesignJson}
                className="p-2 rounded-xl glass-button text-teal-300 transition"
                title="Export Design JSON"
              >
                <Download className="w-4 h-4" />
              </button>
            </div>

            {/* Objective Metrics */}
            <div className="grid grid-cols-2 gap-2 text-xs font-mono">
              <div className="p-3 rounded-xl glass-panel">
                <span className="text-slate-400 block text-[10px]">O1 Discomfort</span>
                <span className="text-xl font-black text-rose-400">
                  {selectedDesign?.O1_ml.toFixed(1)}%
                </span>
                <span className="text-[10px] text-slate-400 block">hours non-neutral</span>
              </div>

              <div className="p-3 rounded-xl glass-panel">
                <span className="text-slate-400 block text-[10px]">O2 HVAC Energy</span>
                <span className="text-xl font-black text-amber-400">
                  {selectedDesign?.O2.toFixed(1)}
                </span>
                <span className="text-[10px] text-slate-400 block">kWh/m²/yr</span>
              </div>
            </div>

            {/* Direct Simulation Verification Error if Verified */}
            {selectedDesign?.is_verified && (
              <div className="p-3 rounded-xl glass-panel space-y-1.5 text-xs font-mono border-teal-500/30">
                <div className="flex items-center justify-between text-teal-300 font-bold">
                  <span>EnergyPlus Physical Ground Truth</span>
                  <span>Direct Simulation</span>
                </div>
                <div className="grid grid-cols-2 gap-1 text-[11px] text-slate-300">
                  <div>Actual O1_ml: <strong>{selectedDesign.verified_O1_ml?.toFixed(1)}%</strong></div>
                  <div>Actual O2: <strong>{selectedDesign.verified_O2?.toFixed(1)} kWh</strong></div>
                  <div className="text-teal-400">O1 Error: {selectedDesign.rel_error_O1_ml?.toFixed(1)}%</div>
                  <div className="text-teal-400">O2 Error: {selectedDesign.rel_error_O2?.toFixed(1)}%</div>
                </div>
              </div>
            )}

            {/* Envelope Variables Listing */}
            <div className="space-y-2 pt-2 border-t border-slate-800 text-xs font-mono">
              <div className="flex justify-between">
                <span className="text-slate-400">Roof Insulation:</span>
                <span className="text-white font-bold">{selectedDesign?.roof_insulation_thickness} mm</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-400">Wall Insulation:</span>
                <span className="text-white font-bold">{selectedDesign?.wall_insulation_thickness} mm</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-400">Wall Mass Class:</span>
                <span className="text-teal-300 font-bold capitalize">{selectedDesign?.wall_mass_class}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-400">Roof Absorptance:</span>
                <span className="text-white font-bold">{selectedDesign?.roof_solar_absorptance.toFixed(2)}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-400">Glazing WWR:</span>
                <span className="text-white font-bold">{selectedDesign?.wwr}%</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-400">Azimuth Orientation:</span>
                <span className="text-white font-bold">{selectedDesign?.orientation}°</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-400">Overhang Shading:</span>
                <span className="text-white font-bold">{selectedDesign?.shading_depth.toFixed(2)} m</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-400">Natural Ventilation:</span>
                <span className="text-white font-bold">{selectedDesign?.ventilation_ach.toFixed(1)} ACH</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Data Table Toggle View */}
      {showTable && (
        <div className="rounded-2xl glass-panel p-6 border border-slate-700/60 space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-base font-bold text-white">
              Pareto Designs Table ({selectedCity})
            </h3>
            <span className="text-xs text-slate-400">Showing {displayDesigns.length} designs</span>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-xs font-mono text-left divide-y divide-slate-800">
              <thead className="bg-slate-900/60 text-slate-400">
                <tr>
                  <th className="py-2.5 px-3">Design ID</th>
                  <th className="py-2.5 px-3">Status</th>
                  <th className="py-2.5 px-3">O1 ML (%)</th>
                  <th className="py-2.5 px-3">O1 Adapt (%)</th>
                  <th className="py-2.5 px-3">O2 (kWh/m²)</th>
                  <th className="py-2.5 px-3">Roof Ins (mm)</th>
                  <th className="py-2.5 px-3">Wall Ins (mm)</th>
                  <th className="py-2.5 px-3">Mass</th>
                  <th className="py-2.5 px-3">Absorptance</th>
                  <th className="py-2.5 px-3">WWR</th>
                  <th className="py-2.5 px-3">Vent (ACH)</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60 text-slate-200">
                {displayDesigns.map((d) => (
                  <tr
                    key={d.pareto_id}
                    onClick={() => setSelectedDesignId(d.pareto_id)}
                    className={`cursor-pointer transition hover:bg-slate-800/60 ${
                      selectedDesign?.pareto_id === d.pareto_id ? "bg-teal-950/40 text-teal-300 font-bold" : ""
                    }`}
                  >
                    <td className="py-2 px-3">{d.pareto_id}</td>
                    <td className="py-2 px-3">
                      {d.is_verified ? (
                        <span className="text-amber-400 font-bold">★ Verified</span>
                      ) : (
                        <span className="text-slate-500">Pareto</span>
                      )}
                    </td>
                    <td className="py-2 px-3 text-rose-400">{d.O1_ml.toFixed(1)}%</td>
                    <td className="py-2 px-3">{d.O1_adapt.toFixed(1)}%</td>
                    <td className="py-2 px-3 text-amber-400">{d.O2.toFixed(1)}</td>
                    <td className="py-2 px-3">{d.roof_insulation_thickness}</td>
                    <td className="py-2 px-3">{d.wall_insulation_thickness}</td>
                    <td className="py-2 px-3 capitalize">{d.wall_mass_class}</td>
                    <td className="py-2 px-3">{d.roof_solar_absorptance.toFixed(2)}</td>
                    <td className="py-2 px-3">{d.wwr}%</td>
                    <td className="py-2 px-3">{d.ventilation_ach.toFixed(1)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}

export default function ParetoExplorerPage() {
  return (
    <Suspense fallback={<div className="py-20 text-center text-slate-400 font-mono text-sm">Loading Multi-Objective Pareto Explorer...</div>}>
      <ParetoExplorerContent />
    </Suspense>
  );
}

