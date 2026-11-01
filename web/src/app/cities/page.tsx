"use client";

import React, { useState, useEffect, Suspense } from "react";
import { useSearchParams } from "next/navigation";
import { CITIES_DATA } from "@/lib/constants";
import { getApplicabilityData, getReferencesForCity, getSurrogateMetricsForCity, getS3ResultForCity } from "@/lib/data";
import { getCityS3Metrics, formatPercentagePoints, formatEnergyDelta } from "@/lib/metrics";
import { CityKey } from "@/types";
import {
  MapPin,
  ShieldCheck,
  AlertTriangle,
  Thermometer,
  Layers,
  CheckCircle2
} from "lucide-react";
import { Badge } from "@/components/ui/Badge";

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
  const s3Metrics = getCityS3Metrics(selectedCity);

  const citiesList = Object.keys(CITIES_DATA) as CityKey[];

  return (
    <div className="space-y-8 pb-16">
      {/* Page Header */}
      <div>
        <h1 className="text-3xl font-semibold text-[var(--ink)] tracking-tight flex items-center space-x-3">
          <MapPin className="w-7 h-7 text-[var(--primary)]" />
          <span>Indian Climate Zone Explorer</span>
        </h1>
        <p className="text-sm text-[var(--ink-2)] mt-1 max-w-3xl">
          Detailed meteorological station metadata, empirical training applicability envelopes, and dual-judge rank agreement across India&apos;s 5 primary climate zones.
        </p>
      </div>

      {/* City Switcher Tabs */}
      <div className="flex flex-wrap items-center gap-2 p-1.5 rounded-[8px] bg-[var(--surface-2)] border border-[var(--line)]">
        {citiesList.map((c) => {
          const info = CITIES_DATA[c];
          const isActive = selectedCity === c;
          const isMedium = info.confidence === "Medium";

          return (
            <button
              key={c}
              onClick={() => setSelectedCity(c)}
              className={`flex items-center space-x-2 px-4 py-2 rounded-[6px] font-medium text-xs transition ${
                isActive
                  ? "bg-[var(--surface)] text-[var(--ink)] shadow-sm font-semibold border border-[var(--line)]"
                  : "text-[var(--ink-2)] hover:text-[var(--ink)] hover:bg-[var(--surface)]/50"
              }`}
            >
              <span
                className={`w-2 h-2 rounded-full ${
                  isMedium ? "bg-[var(--good)]" : "bg-[var(--warn)]"
                }`}
              />
              <span>{info.name}</span>
              <span className="text-[11px] text-[var(--ink-2)]">({info.climateCode})</span>
            </button>
          );
        })}
      </div>

      {/* Main City Card Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left Column: Station Identity & Climate Overview */}
        <div className="lg:col-span-1 space-y-6">
          <div className="rounded-[8px] border border-[var(--line)] bg-[var(--surface)] p-6 space-y-4">
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold text-[var(--primary)]">
                Climate zone
              </span>
              <Badge
                variant={cityInfo.confidence === "Medium" ? "good" : "warn"}
                icon={cityInfo.confidence === "Medium" ? <ShieldCheck className="w-3.5 h-3.5" /> : <AlertTriangle className="w-3.5 h-3.5" />}
              >
                {cityInfo.confidence} confidence
              </Badge>
            </div>

            <div>
              <h2 className="text-2xl font-semibold text-[var(--ink)]">
                {cityInfo.name}
              </h2>
              <p className="text-sm font-medium text-[var(--primary)] mt-0.5">
                {cityInfo.zone}
              </p>
            </div>

            <p className="text-xs text-[var(--ink-2)] leading-relaxed">
              {cityInfo.description}
            </p>

            {/* Warning Alert if present */}
            {cityInfo.envelopeAlert && (
              <div className="p-3.5 rounded-[8px] border border-[var(--line)] bg-[var(--surface-2)] text-[var(--ink)] text-xs flex items-start space-x-2.5">
                <AlertTriangle className="w-4 h-4 text-[var(--warn)] shrink-0 mt-0.5" />
                <span className="leading-snug">{cityInfo.envelopeAlert}</span>
              </div>
            )}

            {/* Station Specs */}
            <div className="pt-4 border-t border-[var(--line)] space-y-2 text-xs">
              <div className="flex justify-between">
                <span className="text-[var(--ink-2)]">Weather file:</span>
                <span className="text-[var(--ink)] font-semibold truncate max-w-[180px]" title={cityInfo.epw}>
                  {cityInfo.epw}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-[var(--ink-2)]">Elevation:</span>
                <span className="text-[var(--ink)] font-semibold tabular-nums">{cityInfo.elevation}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-[var(--ink-2)]">Coordinates:</span>
                <span className="text-[var(--ink)] font-semibold tabular-nums">
                  {cityInfo.coordinates[0]}° N, {cityInfo.coordinates[1]}° E
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-[var(--ink-2)]">Dual-judge Spearman:</span>
                <span className="text-[var(--primary)] font-semibold tabular-nums">{cityInfo.spearman.toFixed(3)}</span>
              </div>
            </div>
          </div>

          {/* S3 Physical Verification Card */}
          <div className="rounded-[8px] border border-[var(--line)] bg-[var(--surface)] p-6 space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold text-[var(--ink-2)]">
                Criterion S3 status
              </span>
              <Badge variant="good" icon={<CheckCircle2 className="w-3.5 h-3.5" />}>
                PASS ({s3Result?.n_designs_beating_both}/10 verified)
              </Badge>
            </div>

            <p className="text-xs text-[var(--ink-2)] leading-relaxed">
              Direct physical simulation in EnergyPlus confirmed that verified Pareto designs beat <strong>both</strong> R1 and R2 reference shelters on all 3 objectives simultaneously in {cityInfo.name}.
            </p>

            <div className="pt-2 border-t border-[var(--line)] space-y-2 text-xs tabular-nums">
              <div className="flex justify-between items-center p-2 rounded-[6px] bg-[var(--surface-2)] border border-[var(--line)]">
                <div>
                  <span className="text-[var(--ink-2)] block text-[11px]">Delta vs R1 lightweight</span>
                  <span className="text-[var(--good)] font-semibold">
                    {formatPercentagePoints(s3Metrics.best_delta_vs_r1_discomfort_pp)}
                  </span>
                </div>
                <div className="text-right">
                  <span className="text-[var(--ink-2)] block text-[11px]">Energy vs R1</span>
                  <span className="text-[var(--link)] font-semibold">
                    {formatEnergyDelta(s3Metrics.best_delta_vs_r1_energy_kwh)}
                  </span>
                </div>
              </div>
              <div className="flex justify-between items-center p-2 rounded-[6px] bg-[var(--surface-2)] border border-[var(--line)]">
                <div>
                  <span className="text-[var(--ink-2)] block text-[11px]">Delta vs R2 conventional</span>
                  <span className="text-[var(--good)] font-semibold">
                    {formatPercentagePoints(s3Metrics.best_delta_vs_r2_discomfort_pp)}
                  </span>
                </div>
                <div className="text-right">
                  <span className="text-[var(--ink-2)] block text-[11px]">Energy vs R2</span>
                  <span className="text-[var(--link)] font-semibold">
                    {formatEnergyDelta(s3Metrics.best_delta_vs_r2_energy_kwh)}
                  </span>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Right Columns: Applicability Gauge & Feature Envelopes */}
        <div className="lg:col-span-2 space-y-6">
          {/* Applicability Breakdown */}
          <div className="rounded-[8px] border border-[var(--line)] bg-[var(--surface)] p-6 space-y-6">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-[var(--line)] pb-4">
              <div>
                <h3 className="text-lg font-semibold text-[var(--ink)] flex items-center space-x-2">
                  <Thermometer className="w-5 h-5 text-[var(--primary)]" />
                  <span>Empirical training envelope & applicability (D-015)</span>
                </h3>
                <p className="text-xs text-[var(--ink-2)] mt-0.5">
                  Share of 8,760 annual simulated indoor hours within the 1st to 99th percentile of ASHRAE DB II field data.
                </p>
              </div>

              <div className="text-right">
                <span className="text-xs text-[var(--ink-2)] block">Overall in-envelope</span>
                <span className="text-2xl font-semibold tabular-nums text-[var(--ink)]">
                  {currentApp?.all_features_in_envelope_pct.toFixed(1)}%
                </span>
              </div>
            </div>

            {/* Feature Envelope Progress Bars */}
            <div className="space-y-4">
              <div>
                <div className="flex justify-between text-xs tabular-nums mb-1">
                  <span className="text-[var(--ink)]">Air temperature (Ta)</span>
                  <span className="text-[var(--ink)] font-semibold">{currentApp?.ta_in_envelope_pct.toFixed(2)}%</span>
                </div>
                <div className="w-full h-2 rounded-full bg-[var(--surface-2)] border border-[var(--line)] overflow-hidden">
                  <div
                    className="h-full bg-[var(--good)] rounded-full transition-all duration-500"
                    style={{ width: `${currentApp?.ta_in_envelope_pct ?? 0}%` }}
                  />
                </div>
              </div>

              <div>
                <div className="flex justify-between text-xs tabular-nums mb-1">
                  <span className="text-[var(--ink)]">Mean radiant temperature (Tr)</span>
                  <span className="text-[var(--ink)] font-semibold">{currentApp?.tr_in_envelope_pct.toFixed(2)}%</span>
                </div>
                <div className="w-full h-2 rounded-full bg-[var(--surface-2)] border border-[var(--line)] overflow-hidden">
                  <div
                    className="h-full bg-[var(--good)] rounded-full transition-all duration-500"
                    style={{ width: `${currentApp?.tr_in_envelope_pct ?? 0}%` }}
                  />
                </div>
              </div>

              <div>
                <div className="flex justify-between text-xs tabular-nums mb-1">
                  <span className="text-[var(--ink)]">Relative humidity (RH)</span>
                  <span className={`font-semibold ${
                    (currentApp?.rh_in_envelope_pct ?? 0) < 50 ? "text-[var(--warn)]" : "text-[var(--good)]"
                  }`}>
                    {currentApp?.rh_in_envelope_pct.toFixed(2)}%
                  </span>
                </div>
                <div className="w-full h-2 rounded-full bg-[var(--surface-2)] border border-[var(--line)] overflow-hidden">
                  <div
                    className={`h-full rounded-full transition-all duration-500 ${
                      (currentApp?.rh_in_envelope_pct ?? 0) < 50 ? "bg-[var(--warn)]" : "bg-[var(--good)]"
                    }`}
                    style={{ width: `${currentApp?.rh_in_envelope_pct ?? 0}%` }}
                  />
                </div>
                {(currentApp?.rh_in_envelope_pct ?? 0) < 50 && (
                  <span className="text-[12px] text-[var(--warn)] block mt-1">
                    * Severe monsoon humidity exceeds 99th percentile of field survey dataset.
                  </span>
                )}
              </div>

              <div>
                <div className="flex justify-between text-xs tabular-nums mb-1">
                  <span className="text-[var(--ink)]">Adaptive 90% valid hours share</span>
                  <span className={`font-semibold ${
                    (currentApp?.adaptive_90_valid_pct ?? 0) < 80 ? "text-[var(--bad)]" : "text-[var(--good)]"
                  }`}>
                    {currentApp?.adaptive_90_valid_pct.toFixed(2)}%
                  </span>
                </div>
                <div className="w-full h-2 rounded-full bg-[var(--surface-2)] border border-[var(--line)] overflow-hidden">
                  <div
                    className={`h-full rounded-full transition-all duration-500 ${
                      (currentApp?.adaptive_90_valid_pct ?? 0) < 80 ? "bg-[var(--bad)]" : "bg-[var(--good)]"
                    }`}
                    style={{ width: `${currentApp?.adaptive_90_valid_pct ?? 0}%` }}
                  />
                </div>
                {(currentApp?.adaptive_90_valid_pct ?? 0) < 80 && (
                  <span className="text-[12px] text-[var(--bad)] block mt-1">
                    * Winter running mean outdoor temperatures fall below the ASHRAE 55 Adaptive 10°C lower boundary.
                  </span>
                )}
              </div>
            </div>
          </div>

          {/* Reference Shelters Comparison (R1 vs R2) */}
          <div className="rounded-[8px] border border-[var(--line)] bg-[var(--surface)] p-6 space-y-4">
            <h3 className="text-lg font-semibold text-[var(--ink)] flex items-center space-x-2">
              <Layers className="w-5 h-5 text-[var(--primary)]" />
              <span>Reference shelters in {cityInfo.name}</span>
            </h3>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {/* R1 Lightweight */}
              <div className="p-4 rounded-[8px] border border-[var(--line)] bg-[var(--surface-2)] space-y-2">
                <div className="flex justify-between items-center">
                  <span className="font-semibold text-sm text-[var(--ink)]">R1 Lightweight</span>
                  <span className="text-[12px] px-2 py-0.5 rounded-[4px] bg-[var(--surface)] border border-[var(--line)] text-[var(--ink-2)]">
                    Uninsulated • Light Mass
                  </span>
                </div>
                <p className="text-xs text-[var(--ink-2)]">
                  Reflects emergency tents / tin sheets (absorptance 0.85, 0 mm insulation).
                </p>
                <div className="pt-2 border-t border-[var(--line)] grid grid-cols-2 gap-2 text-xs tabular-nums">
                  <div>
                    <span className="text-[var(--ink-2)] block text-[11px]">O1 Discomfort (ML)</span>
                    <span className="text-[var(--hot)] font-semibold">{r1?.O1_ml.toFixed(1)}%</span>
                    <span className="text-[var(--ink-2)] block text-[11px]">Adapt: {r1?.O1_adapt.toFixed(1)}%</span>
                  </div>
                  <div>
                    <span className="text-[var(--ink-2)] block text-[11px]">O2 HVAC Energy</span>
                    <span className="text-[var(--ink)] font-semibold">{r1?.O2.toFixed(1)} kWh/m²/yr</span>
                  </div>
                </div>
              </div>

              {/* R2 Conventional */}
              <div className="p-4 rounded-[8px] border border-[var(--line)] bg-[var(--surface-2)] space-y-2">
                <div className="flex justify-between items-center">
                  <span className="font-semibold text-sm text-[var(--ink)]">R2 Conventional</span>
                  <span className="text-[12px] px-2 py-0.5 rounded-[4px] bg-[var(--surface)] border border-[var(--line)] text-[var(--ink-2)]">
                    Medium Brick • Absorptance 0.60
                  </span>
                </div>
                <p className="text-xs text-[var(--ink-2)]">
                  Standard masonry construction with clay brick wall and uninsulated slab.
                </p>
                <div className="pt-2 border-t border-[var(--line)] grid grid-cols-2 gap-2 text-xs tabular-nums">
                  <div>
                    <span className="text-[var(--ink-2)] block text-[11px]">O1 Discomfort (ML)</span>
                    <span className="text-[var(--hot)] font-semibold">{r2?.O1_ml.toFixed(1)}%</span>
                    <span className="text-[var(--ink-2)] block text-[11px]">Adapt: {r2?.O1_adapt.toFixed(1)}%</span>
                  </div>
                  <div>
                    <span className="text-[var(--ink-2)] block text-[11px]">O2 HVAC Energy</span>
                    <span className="text-[var(--ink)] font-semibold">{r2?.O2.toFixed(1)} kWh/m²/yr</span>
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
    <Suspense fallback={<div className="py-20 text-center text-[var(--ink-2)] text-sm">Loading Climate Station Data...</div>}>
      <CityExplorerContent />
    </Suspense>
  );
}
