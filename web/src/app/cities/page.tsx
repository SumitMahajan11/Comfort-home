"use client";

import React, { useState, useEffect, Suspense } from "react";
import { useSearchParams } from "next/navigation";
import { CITIES_DATA } from "@/lib/constants";
import { getApplicabilityData, getReferencesForCity, getSurrogateMetricsForCity, getS3ResultForCity } from "@/lib/data";
import { CityKey } from "@/types";
import {
  MapPin,
  ShieldCheck,
  AlertTriangle,
  Thermometer,
  Wind,
  Droplets,
  Layers,
  FileText,
  BarChart2,
  CheckCircle2
} from "lucide-react";

function CityExplorerContent() {
  const searchParams = useSearchParams();
  const initialCity = (searchParams?.get("city") as CityKey) || "Jodhpur";
  const [selectedCity, setSelectedCity] = useState<CityKey>(initialCity);

  useEffect(() => {
    const c = searchParams?.get("city") as CityKey;
    if (c && CITIES_DATA[c]) {
      setSelectedCity(c);
    }
  }, [searchParams]);

  const cityInfo = CITIES_DATA[selectedCity];
  const allApplicability = getApplicabilityData();
  const currentApp = allApplicability.find((a) => a.city === selectedCity);
  const { r1, r2 } = getReferencesForCity(selectedCity);
  const surrogates = getSurrogateMetricsForCity(selectedCity);
  const s3Result = getS3ResultForCity(selectedCity);

  const citiesList = Object.keys(CITIES_DATA) as CityKey[];

  return (
    <div className="space-y-8 pb-16">
      {/* Page Header */}
      <div>
        <h1 className="text-3xl font-bold text-white tracking-tight flex items-center space-x-3">
          <MapPin className="w-7 h-7 text-teal-400" />
          <span>Indian Climate Zone Explorer</span>
        </h1>
        <p className="text-sm text-slate-300 mt-1 max-w-3xl">
          Detailed meteorological station metadata, empirical training applicability envelopes, and dual-judge rank agreement across India&apos;s 5 primary climate zones.
        </p>
      </div>

      {/* City Switcher Tabs */}
      <div className="flex flex-wrap items-center gap-2 p-1.5 rounded-2xl glass-panel border border-slate-700/60">
        {citiesList.map((c) => {
          const info = CITIES_DATA[c];
          const isActive = selectedCity === c;
          const isMedium = info.confidence === "Medium";

          return (
            <button
              key={c}
              onClick={() => setSelectedCity(c)}
              className={`flex items-center space-x-2 px-4 py-2.5 rounded-xl font-medium text-xs transition ${
                isActive
                  ? "bg-teal-600 text-white shadow-md font-semibold"
                  : "text-slate-300 hover:text-white hover:bg-slate-800/60"
              }`}
            >
              <span
                className={`w-2 h-2 rounded-full ${
                  isMedium ? "bg-emerald-400" : "bg-amber-400"
                }`}
              />
              <span>{info.name}</span>
              <span className="text-[10px] opacity-75 font-mono">({info.climateCode})</span>
            </button>
          );
        })}
      </div>

      {/* Main City Card Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left Column: Station Identity & Climate Overview */}
        <div className="lg:col-span-1 space-y-6">
          <div className="rounded-2xl glass-card p-6 space-y-4">
            <div className="flex items-center justify-between">
              <span className="text-xs uppercase font-mono tracking-wider text-teal-400">
                Climate Zone
              </span>
              <span
                className={`inline-flex items-center space-x-1.5 px-3 py-1 rounded-full text-xs font-semibold glass-pill ${
                  cityInfo.confidence === "Medium"
                    ? "text-emerald-300 border-emerald-400/40 shadow-[0_0_12px_rgba(16,185,129,0.2)]"
                    : "text-amber-300 border-amber-400/40 shadow-[0_0_12px_rgba(245,158,11,0.2)]"
                }`}
              >
                {cityInfo.confidence === "Medium" ? (
                  <ShieldCheck className="w-3.5 h-3.5 text-emerald-400" />
                ) : (
                  <AlertTriangle className="w-3.5 h-3.5 text-amber-400" />
                )}
                <span>{cityInfo.confidence} Confidence</span>
              </span>
            </div>

            <div>
              <h2 className="text-3xl font-extrabold text-white">
                {cityInfo.name}
              </h2>
              <p className="text-sm font-semibold text-teal-300 mt-0.5">
                {cityInfo.zone}
              </p>
            </div>

            <p className="text-xs text-slate-300 leading-relaxed">
              {cityInfo.description}
            </p>

            {/* Warning Alert if present */}
            {cityInfo.envelopeAlert && (
              <div className="p-3.5 rounded-xl glass-panel text-amber-200 text-xs flex items-start space-x-2.5 border-amber-500/30">
                <AlertTriangle className="w-4 h-4 text-amber-400 shrink-0 mt-0.5" />
                <span className="leading-snug">{cityInfo.envelopeAlert}</span>
              </div>
            )}

            {/* Station Specs */}
            <div className="pt-4 border-t border-white/10 space-y-2 text-xs font-mono">
              <div className="flex justify-between">
                <span className="text-slate-400">Weather File:</span>
                <span className="text-slate-100 font-semibold truncate max-w-[180px]" title={cityInfo.epw}>
                  {cityInfo.epw}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-400">Elevation:</span>
                <span className="text-slate-100 font-semibold">{cityInfo.elevation}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-400">Coordinates:</span>
                <span className="text-slate-100 font-semibold">
                  {cityInfo.coordinates[0]}° N, {cityInfo.coordinates[1]}° E
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-400">Dual-Judge Spearman:</span>
                <span className="text-teal-300 font-bold">{cityInfo.spearman.toFixed(3)}</span>
              </div>
            </div>
          </div>

          {/* S3 Physical Verification Card */}
          <div className="rounded-2xl glass-card p-6 space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-xs font-mono uppercase tracking-wider text-slate-400">
                Criterion S3 Status
              </span>
              <span className="px-3 py-1 rounded-full text-xs font-bold glass-pill text-emerald-300 border-emerald-400/40 shadow-[0_0_12px_rgba(16,185,129,0.25)]">
                PASS ({s3Result?.n_designs_beating_both}/10 Verified)
              </span>
            </div>

            <p className="text-xs text-slate-300 leading-relaxed">
              Direct physical simulation in EnergyPlus confirmed that verified Pareto designs beat <strong>both</strong> R1 and R2 reference shelters on all 3 objectives simultaneously in {cityInfo.name}.
            </p>

            <div className="pt-2 border-t border-slate-800 grid grid-cols-2 gap-2 text-xs font-mono">
              <div className="p-2 rounded-lg bg-slate-900/60 border border-slate-800">
                <span className="text-slate-400 block text-[10px]">Discomfort Cut</span>
                <span className="text-emerald-400 font-bold">
                  -{s3Result?.margin_O1_ml_pct.toFixed(2)}%
                </span>
              </div>
              <div className="p-2 rounded-lg bg-slate-900/60 border border-slate-800">
                <span className="text-slate-400 block text-[10px]">Energy Saved</span>
                <span className="text-emerald-400 font-bold">
                  -{s3Result?.margin_O2_kwh_per_m2.toFixed(1)} kWh/m²
                </span>
              </div>
            </div>
          </div>
        </div>

        {/* Right Columns: Applicability Gauge & Feature Envelopes */}
        <div className="lg:col-span-2 space-y-6">
          {/* Applicability Breakdown */}
          <div className="rounded-2xl glass-card p-6 space-y-6">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-white/10 pb-4">
              <div>
                <h3 className="text-lg font-bold text-white flex items-center space-x-2">
                  <Thermometer className="w-5 h-5 text-teal-400" />
                  <span>Empirical Training Envelope & Applicability (D-015)</span>
                </h3>
                <p className="text-xs text-slate-400 mt-0.5">
                  Share of 8,760 annual simulated indoor hours within the 1st to 99th percentile of ASHRAE DB II field data.
                </p>
              </div>

              <div className="text-right">
                <span className="text-xs font-mono text-slate-400 block">Overall In-Envelope</span>
                <span className="text-2xl font-black font-mono text-teal-400">
                  {currentApp?.all_features_in_envelope_pct.toFixed(1)}%
                </span>
              </div>
            </div>

            {/* Feature Envelope Progress Bars */}
            <div className="space-y-4">
              <div>
                <div className="flex justify-between text-xs font-mono mb-1">
                  <span className="text-slate-300">Air Temperature (Ta)</span>
                  <span className="text-teal-400 font-bold">{currentApp?.ta_in_envelope_pct.toFixed(2)}%</span>
                </div>
                <div className="w-full h-2 rounded-full bg-slate-800 overflow-hidden">
                  <div
                    className="h-full bg-teal-500 rounded-full transition-all duration-500"
                    style={{ width: `${currentApp?.ta_in_envelope_pct ?? 0}%` }}
                  />
                </div>
              </div>

              <div>
                <div className="flex justify-between text-xs font-mono mb-1">
                  <span className="text-slate-300">Mean Radiant Temperature (Tr)</span>
                  <span className="text-teal-400 font-bold">{currentApp?.tr_in_envelope_pct.toFixed(2)}%</span>
                </div>
                <div className="w-full h-2 rounded-full bg-slate-800 overflow-hidden">
                  <div
                    className="h-full bg-teal-500 rounded-full transition-all duration-500"
                    style={{ width: `${currentApp?.tr_in_envelope_pct ?? 0}%` }}
                  />
                </div>
              </div>

              <div>
                <div className="flex justify-between text-xs font-mono mb-1">
                  <span className="text-slate-300">Relative Humidity (RH)</span>
                  <span className={`font-bold ${
                    (currentApp?.rh_in_envelope_pct ?? 0) < 50 ? "text-amber-400" : "text-teal-400"
                  }`}>
                    {currentApp?.rh_in_envelope_pct.toFixed(2)}%
                  </span>
                </div>
                <div className="w-full h-2 rounded-full bg-slate-800 overflow-hidden">
                  <div
                    className={`h-full rounded-full transition-all duration-500 ${
                      (currentApp?.rh_in_envelope_pct ?? 0) < 50 ? "bg-amber-500" : "bg-teal-500"
                    }`}
                    style={{ width: `${currentApp?.rh_in_envelope_pct ?? 0}%` }}
                  />
                </div>
                {(currentApp?.rh_in_envelope_pct ?? 0) < 50 && (
                  <span className="text-[10px] text-amber-300/80 block mt-1">
                    * Severe monsoon humidity exceeds 99th percentile of field survey dataset.
                  </span>
                )}
              </div>

              <div>
                <div className="flex justify-between text-xs font-mono mb-1">
                  <span className="text-slate-300">Adaptive 90% Valid Hours Share</span>
                  <span className={`font-bold ${
                    (currentApp?.adaptive_90_valid_pct ?? 0) < 80 ? "text-rose-400" : "text-emerald-400"
                  }`}>
                    {currentApp?.adaptive_90_valid_pct.toFixed(2)}%
                  </span>
                </div>
                <div className="w-full h-2 rounded-full bg-slate-800 overflow-hidden">
                  <div
                    className={`h-full rounded-full transition-all duration-500 ${
                      (currentApp?.adaptive_90_valid_pct ?? 0) < 80 ? "bg-rose-500" : "bg-emerald-500"
                    }`}
                    style={{ width: `${currentApp?.adaptive_90_valid_pct ?? 0}%` }}
                  />
                </div>
                {(currentApp?.adaptive_90_valid_pct ?? 0) < 80 && (
                  <span className="text-[10px] text-rose-300/80 block mt-1">
                    * Winter running mean outdoor temperatures fall below the ASHRAE 55 Adaptive 10°C lower boundary.
                  </span>
                )}
              </div>
            </div>
          </div>

          {/* Reference Shelters Comparison (R1 vs R2) */}
          <div className="rounded-2xl glass-card p-6 space-y-4">
            <h3 className="text-lg font-bold text-white flex items-center space-x-2">
              <Layers className="w-5 h-5 text-teal-400" />
              <span>Reference Shelters in {cityInfo.name}</span>
            </h3>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {/* R1 Lightweight */}
              <div className="p-4 rounded-xl glass-panel space-y-2">
                <div className="flex justify-between items-center">
                  <span className="font-bold text-sm text-white">R1 Lightweight</span>
                  <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-slate-800 text-slate-400">
                    Uninsulated • Light Mass
                  </span>
                </div>
                <p className="text-xs text-slate-400">
                  Reflects emergency tents / tin sheets (absorptance 0.85, 0 mm insulation).
                </p>
                <div className="pt-2 border-t border-slate-800/80 grid grid-cols-2 gap-2 text-xs font-mono">
                  <div>
                    <span className="text-slate-400 block text-[10px]">O1 Discomfort</span>
                    <span className="text-rose-400 font-bold">{r1?.O1_ml.toFixed(1)}%</span>
                  </div>
                  <div>
                    <span className="text-slate-400 block text-[10px]">O2 Energy</span>
                    <span className="text-amber-400 font-bold">{r1?.O2.toFixed(1)} kWh/m²</span>
                  </div>
                </div>
              </div>

              {/* R2 Conventional */}
              <div className="p-4 rounded-xl glass-panel space-y-2">
                <div className="flex justify-between items-center">
                  <span className="font-bold text-sm text-white">R2 Conventional</span>
                  <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-slate-800 text-slate-400">
                    Medium Brick • Absorptance 0.60
                  </span>
                </div>
                <p className="text-xs text-slate-400">
                  Standard masonry construction with clay brick wall and uninsulated slab.
                </p>
                <div className="pt-2 border-t border-slate-800/80 grid grid-cols-2 gap-2 text-xs font-mono">
                  <div>
                    <span className="text-slate-400 block text-[10px]">O1 Discomfort</span>
                    <span className="text-rose-400 font-bold">{r2?.O1_ml.toFixed(1)}%</span>
                  </div>
                  <div>
                    <span className="text-slate-400 block text-[10px]">O2 Energy</span>
                    <span className="text-amber-400 font-bold">{r2?.O2.toFixed(1)} kWh/m²</span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default function CityExplorerPage() {
  return (
    <Suspense fallback={<div className="py-20 text-center text-slate-400 font-mono text-sm">Loading Climate Station Data...</div>}>
      <CityExplorerContent />
    </Suspense>
  );
}

