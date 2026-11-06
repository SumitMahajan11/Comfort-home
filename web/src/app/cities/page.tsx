"use client";

import React, { useState, useEffect, useMemo, Suspense } from "react";
import { useSearchParams } from "next/navigation";
import { CITIES_DATA } from "@/lib/constants";
import {
  getApplicabilityData,
  getReferencesForCity,
  getSurrogateMetricsForCity,
  getS3ResultForCity,
  get30CitiesData
} from "@/lib/data";
import { getCityS3Metrics, formatPercentagePoints, formatEnergyDelta } from "@/lib/metrics";
import { CityKey, City30Record } from "@/types";
import {
  MapPin,
  ShieldCheck,
  AlertTriangle,
  Thermometer,
  Layers,
  CheckCircle2,
  Search,
  Copy,
  Check,
  Building,
  TrendingDown,
  Compass,
  FileSpreadsheet
} from "lucide-react";
import { Badge } from "@/components/ui/Badge";

function CityExplorerContent() {
  const searchParams = useSearchParams();
  const initialCity = (searchParams?.get("city") as CityKey) || "Jodhpur";
  const [selectedCity, setSelectedCity] = useState<CityKey>(initialCity);
  const [viewMode, setViewMode] = useState<"flagship" | "all30">("flagship");
  const [copiedSha, setCopiedSha] = useState<string | null>(null);

  // 30-city table state
  const [zoneFilter, setZoneFilter] = useState<string>("All");
  const [searchTerm, setSearchTerm] = useState<string>("");
  const all30Cities = useMemo(() => get30CitiesData(), []);

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

  const handleCopySha = (sha: string) => {
    navigator.clipboard.writeText(sha);
    setCopiedSha(sha);
    setTimeout(() => setCopiedSha(null), 2500);
  };

  const filtered30 = useMemo(() => {
    return all30Cities.filter((item) => {
      const matchZone = zoneFilter === "All" || item.zone.toLowerCase() === zoneFilter.toLowerCase();
      const matchSearch =
        !searchTerm.trim() ||
        item.city.toLowerCase().includes(searchTerm.toLowerCase()) ||
        item.zone.toLowerCase().includes(searchTerm.toLowerCase()) ||
        (item.station_name && item.station_name.toLowerCase().includes(searchTerm.toLowerCase())) ||
        (item.wmo && String(item.wmo).includes(searchTerm));
      return matchZone && matchSearch;
    });
  }, [all30Cities, zoneFilter, searchTerm]);

  return (
    <div className="space-y-8 pb-16">
      {/* Page Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-[var(--line)] pb-4">
        <div>
          <h1 className="text-3xl font-semibold text-[var(--ink)] tracking-tight flex items-center space-x-3">
            <MapPin className="w-7 h-7 text-[var(--primary)]" />
            <span>Indian Climate Zone Explorer</span>
          </h1>
          <p className="text-sm text-[var(--ink-2)] mt-1 max-w-3xl">
            Meteorological station provenance, multi-objective Pareto front sizes, and envelope optimization results across India&apos;s 5 primary climate zones and all 30 audited cities.
          </p>
        </div>

        {/* View Mode Toggle */}
        <div className="flex p-1 rounded-xl bg-[var(--surface-2)] border border-[var(--line)] gap-1 shrink-0">
          <button
            type="button"
            onClick={() => setViewMode("flagship")}
            className={`px-4 py-2 rounded-lg text-xs font-semibold transition ${
              viewMode === "flagship"
                ? "bg-[var(--surface)] text-[var(--ink)] shadow-sm font-bold border border-[var(--line)]"
                : "text-[var(--ink-2)] hover:text-[var(--ink)]"
            }`}
          >
            5 Flagship Zones Deep-Dive
          </button>
          <button
            type="button"
            onClick={() => setViewMode("all30")}
            className={`px-4 py-2 rounded-lg text-xs font-semibold transition flex items-center space-x-1.5 ${
              viewMode === "all30"
                ? "bg-[var(--surface)] text-[var(--ink)] shadow-sm font-bold border border-[var(--line)]"
                : "text-[var(--ink-2)] hover:text-[var(--ink)]"
            }`}
          >
            <FileSpreadsheet className="w-3.5 h-3.5 text-[var(--primary)]" />
            <span>All 30 Indian Cities (Table 1 & 5)</span>
          </button>
        </div>
      </div>

      {viewMode === "flagship" ? (
        <>
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

                {/* Metadata Items */}
                <div className="pt-2 border-t border-[var(--line)] space-y-2 text-xs">
                  <div className="flex justify-between py-1 border-b border-[var(--line)]/50">
                    <span className="text-[var(--ink-2)]">Coordinates:</span>
                    <span className="font-mono text-[var(--ink)]">
                      {cityInfo.coordinates[0].toFixed(4)}°N, {cityInfo.coordinates[1].toFixed(4)}°E
                    </span>
                  </div>
                  <div className="flex justify-between py-1 border-b border-[var(--line)]/50">
                    <span className="text-[var(--ink-2)]">Elevation:</span>
                    <span className="font-mono text-[var(--ink)]">{cityInfo.elevation}</span>
                  </div>
                  <div className="flex justify-between py-1 border-b border-[var(--line)]/50">
                    <span className="text-[var(--ink-2)]">EPW Source:</span>
                    <span className="font-mono text-[var(--ink)] text-[11px] truncate max-w-[180px]" title={cityInfo.epw}>
                      {cityInfo.epw}
                    </span>
                  </div>
                  <div className="flex justify-between py-1">
                    <span className="text-[var(--ink-2)]">Dual-Judge Agreement:</span>
                    <span className="font-mono font-semibold text-[var(--ink)]">
                      rs = {cityInfo.spearman.toFixed(3)}
                    </span>
                  </div>
                </div>
              </div>

              {/* S3 Success Criterion Card */}
              <div className="rounded-[8px] border border-[var(--line)] bg-[var(--surface)] p-6 space-y-3">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-semibold text-[var(--primary)] uppercase tracking-wider">
                    Success Criterion S3
                  </span>
                  <Badge variant="good" icon={<CheckCircle2 className="w-3.5 h-3.5" />}>
                    Verified PASS
                  </Badge>
                </div>
                <p className="text-xs text-[var(--ink-2)]">
                  Physical EnergyPlus runs confirmed that Pareto designs beat BOTH R1 (Lightweight) and R2 (Conventional) reference shelters across all three objectives.
                </p>
                <div className="p-3 rounded-[6px] bg-[var(--surface-2)] border border-[var(--line)] text-xs">
                  <span className="text-[var(--ink-2)] block text-[11px]">Verified Designs Beating Both:</span>
                  <span className="text-lg font-bold text-[var(--good)]">
                    {s3Result?.n_designs_beating_both || 0} / 10 designs
                  </span>
                  <span className="text-[11px] text-[var(--ink-2)] block mt-0.5">
                    Best Design: <code className="font-mono text-[var(--ink)] font-semibold">{s3Result?.best_pareto_id}</code>
                  </span>
                </div>
              </div>
            </div>

            {/* Right 2 Columns: Empirical Envelopes & Reference Baselines */}
            <div className="lg:col-span-2 space-y-6">
              {/* Training Envelope Coverage Card */}
              <div className="rounded-[8px] border border-[var(--line)] bg-[var(--surface)] p-6 space-y-4">
                <div className="flex items-center justify-between">
                  <h3 className="text-base font-semibold text-[var(--ink)] flex items-center space-x-2">
                    <Layers className="w-5 h-5 text-[var(--primary)]" />
                    <span>Empirical Training Data Applicability (Decision D-015)</span>
                  </h3>
                  <span className="text-xs text-[var(--ink-2)]">
                    {currentApp?.n_hourly_samples.toLocaleString()} hours analyzed
                  </span>
                </div>

                <p className="text-xs text-[var(--ink-2)]">
                  Percentage of annual simulated hours falling within the 1st–99th percentile feature envelope of the ASHRAE Global Thermal Comfort Database II training set.
                </p>

                <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 pt-2">
                  <div className="p-3 rounded-[6px] bg-[var(--surface-2)] border border-[var(--line)]">
                    <span className="text-[11px] text-[var(--ink-2)] block">Dry-Bulb (Ta)</span>
                    <span className="text-base font-bold text-[var(--ink)]">
                      {currentApp?.ta_in_envelope_pct.toFixed(1)}%
                    </span>
                  </div>
                  <div className="p-3 rounded-[6px] bg-[var(--surface-2)] border border-[var(--line)]">
                    <span className="text-[11px] text-[var(--ink-2)] block">Relative Humidity</span>
                    <span className={`text-base font-bold ${
                      (currentApp?.rh_in_envelope_pct || 100) < 50 ? "text-[var(--warn)]" : "text-[var(--ink)]"
                    }`}>
                      {currentApp?.rh_in_envelope_pct.toFixed(1)}%
                    </span>
                  </div>
                  <div className="p-3 rounded-[6px] bg-[var(--surface-2)] border border-[var(--line)]">
                    <span className="text-[11px] text-[var(--ink-2)] block">All Features</span>
                    <span className="text-base font-bold text-[var(--primary)]">
                      {currentApp?.all_features_in_envelope_pct.toFixed(1)}%
                    </span>
                  </div>
                  <div className="p-3 rounded-[6px] bg-[var(--surface-2)] border border-[var(--line)]">
                    <span className="text-[11px] text-[var(--ink-2)] block">Adaptive 90% Valid</span>
                    <span className={`text-base font-bold ${
                      (currentApp?.adaptive_90_valid_pct || 100) < 80 ? "text-[var(--warn)]" : "text-[var(--good)]"
                    }`}>
                      {currentApp?.adaptive_90_valid_pct.toFixed(1)}%
                    </span>
                  </div>
                </div>
              </div>

              {/* Reference Baselines Card */}
              <div className="rounded-[8px] border border-[var(--line)] bg-[var(--surface)] p-6 space-y-4">
                <h3 className="text-base font-semibold text-[var(--ink)] flex items-center space-x-2">
                  <Building className="w-5 h-5 text-[var(--primary)]" />
                  <span>Reference Shelter Baselines (Assumptions A-006 & A-007)</span>
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
        </>
      ) : (
        /* ========================================================================= */
        /* ALL 30 INDIAN CITIES DATASET VIEW (TABLE 1 & TABLE 5) */
        /* ========================================================================= */
        <div className="space-y-6">
          {/* Summary KPIs */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
            <div className="p-4 rounded-xl border border-[var(--line)] bg-[var(--surface)]">
              <span className="text-xs text-[var(--ink-2)] block">Audited Indian Cities</span>
              <span className="text-2xl font-bold text-[var(--ink)]">30 Cities</span>
              <span className="text-[11px] text-[var(--primary)] block mt-0.5">5 Flagship + 25 Batch</span>
            </div>
            <div className="p-4 rounded-xl border border-[var(--line)] bg-[var(--surface)]">
              <span className="text-xs text-[var(--ink-2)] block">Climate Zones Covered</span>
              <span className="text-2xl font-bold text-[var(--ink)]">5 ECBC Zones</span>
              <span className="text-[11px] text-[var(--good)] block mt-0.5">Hot-Dry, Humid, Comp, Temp, Cold</span>
            </div>
            <div className="p-4 rounded-xl border border-[var(--line)] bg-[var(--surface)]">
              <span className="text-xs text-[var(--ink-2)] block">Weather File Epoch</span>
              <span className="text-2xl font-bold text-[var(--ink)]">2011–2025</span>
              <span className="text-[11px] text-[var(--ink-2)] block mt-0.5">100% Cryptographic SHA-256</span>
            </div>
            <div className="p-4 rounded-xl border border-[var(--line)] bg-[var(--surface)]">
              <span className="text-xs text-[var(--ink-2)] block">Pareto Deduplication</span>
              <span className="text-2xl font-bold text-[var(--good)]">100% Unique</span>
              <span className="text-[11px] text-[var(--ink-2)] block mt-0.5">Zero Duplicate Parameter Vectors</span>
            </div>
          </div>

          {/* Search & Zone Filter Bar */}
          <div className="flex flex-col md:flex-row md:items-center justify-between gap-3 p-3 rounded-xl bg-[var(--surface)] border border-[var(--line)]">
            <div className="flex flex-wrap items-center gap-1.5">
              <span className="text-xs font-semibold text-[var(--ink-2)] mr-1">Zone:</span>
              {["All", "Hot-dry", "Warm-humid", "Composite", "Temperate", "Cold"].map((z) => {
                const isActive = zoneFilter.toLowerCase() === z.toLowerCase();
                return (
                  <button
                    key={z}
                    type="button"
                    onClick={() => setZoneFilter(z)}
                    className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition ${
                      isActive
                        ? "bg-[var(--ink)] text-[var(--surface)]"
                        : "bg-[var(--surface-2)] text-[var(--ink-2)] hover:text-[var(--ink)] border border-[var(--line)]"
                    }`}
                  >
                    {z === "All" ? "All Zones (30)" : z}
                  </button>
                );
              })}
            </div>

            <div className="relative max-w-xs w-full">
              <Search className="w-4 h-4 text-[var(--ink-2)] absolute left-3 top-2.5" />
              <input
                type="text"
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                placeholder="Search city, station, or WMO ID..."
                className="w-full bg-[var(--surface-2)] border border-[var(--line)] text-[var(--ink)] text-xs pl-9 pr-3 py-2 rounded-lg focus:outline-none focus:ring-1 focus:ring-[var(--primary)]"
              />
            </div>
          </div>

          {/* Results Table */}
          <div className="rounded-xl border border-[var(--line)] bg-[var(--surface)] overflow-hidden shadow-sm">
            <div className="overflow-x-auto max-h-[640px] overflow-y-auto">
              <table className="w-full text-left border-collapse text-xs">
                <thead className="bg-[var(--surface-2)] sticky top-0 z-10 border-b border-[var(--line)] text-[var(--ink)] font-bold">
                  <tr>
                    <th className="py-3 px-3">City</th>
                    <th className="py-3 px-3">ECBC Zone</th>
                    <th className="py-3 px-3">WMO / Coordinates</th>
                    <th className="py-3 px-3 text-right">Elevation</th>
                    <th className="py-3 px-3 text-right">Front (N)</th>
                    <th className="py-3 px-3 text-right">Best O1 (ML)</th>
                    <th className="py-3 px-3 text-right">Best O2 (kWh/m²)</th>
                    <th className="py-3 px-3 text-right">Δ vs R2 Conv</th>
                    <th className="py-3 px-3 text-center">EPW SHA-256</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-[var(--line)] text-[var(--ink)]">
                  {filtered30.map((c: City30Record) => {
                    const isFlagship = c.group === "flagship";
                    return (
                      <tr
                        key={c.city}
                        className="hover:bg-[var(--surface-2)]/60 transition"
                      >
                        <td className="py-2.5 px-3">
                          <div className="flex items-center space-x-2">
                            <span className="font-bold text-[var(--ink)]">{c.city}</span>
                            {isFlagship ? (
                              <span className="px-1.5 py-0.5 rounded text-[10px] bg-teal-500/20 text-teal-300 border border-teal-500/30 font-semibold">
                                Flagship
                              </span>
                            ) : (
                              <span className="px-1.5 py-0.5 rounded text-[10px] bg-white/[0.05] text-[var(--ink-2)] border border-white/10">
                                Batch
                              </span>
                            )}
                          </div>
                          {c.station_name && (
                            <span className="text-[11px] text-[var(--ink-2)] block truncate max-w-[160px]" title={c.station_name}>
                              {c.station_name}
                            </span>
                          )}
                        </td>
                        <td className="py-2.5 px-3">
                          <span className="font-semibold text-[var(--primary)]">{c.zone}</span>
                          <span className="text-[10px] text-[var(--ink-2)] block">
                            {c.zone_source === "ASSUMED" ? "Assumed (ECBC)" : "Standard"}
                          </span>
                        </td>
                        <td className="py-2.5 px-3 font-mono text-[11px] tabular-nums">
                          <div>WMO: {c.wmo || "—"}</div>
                          {c.latitude !== undefined && c.longitude !== undefined && (
                            <div className="text-[var(--ink-2)]">
                              {c.latitude.toFixed(2)}°N, {c.longitude.toFixed(2)}°E
                            </div>
                          )}
                        </td>
                        <td className="py-2.5 px-3 text-right font-mono tabular-nums">
                          {c.elevation_m !== undefined ? `${Math.round(c.elevation_m)} m` : "—"}
                        </td>
                        <td className="py-2.5 px-3 text-right font-bold tabular-nums">
                          {c.front_size}
                        </td>
                        <td className="py-2.5 px-3 text-right font-mono tabular-nums font-semibold text-[var(--good)]">
                          {c.best_O1_ml.toFixed(1)}%
                        </td>
                        <td className="py-2.5 px-3 text-right font-mono tabular-nums font-semibold">
                          {c.best_O2.toFixed(1)}
                        </td>
                        <td className="py-2.5 px-3 text-right font-mono tabular-nums font-semibold text-[var(--good)]">
                          -{c.pct_better_R3_O2 ? c.pct_better_R3_O2.toFixed(1) : "0.0"}%
                        </td>
                        <td className="py-2.5 px-3 text-center">
                          <button
                            type="button"
                            onClick={() => handleCopySha(c.epw_sha256)}
                            title={`Click to copy SHA-256:\n${c.epw_sha256}`}
                            className="inline-flex items-center space-x-1 px-2 py-1 rounded bg-[var(--surface-2)] hover:bg-[var(--surface)] border border-[var(--line)] text-[11px] font-mono text-[var(--ink-2)] hover:text-[var(--ink)]"
                          >
                            {copiedSha === c.epw_sha256 ? (
                              <Check className="w-3 h-3 text-[var(--good)]" />
                            ) : (
                              <Copy className="w-3 h-3" />
                            )}
                            <span>{c.epw_sha256 ? c.epw_sha256.substring(0, 8) : "hash"}…</span>
                          </button>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>

            <div className="p-3 bg-[var(--surface-2)] border-t border-[var(--line)] text-xs text-[var(--ink-2)] flex flex-col sm:flex-row justify-between items-center gap-2">
              <span>
                Showing <strong>{filtered30.length}</strong> of <strong>30</strong> Indian cities from audited Table 1 & Table 5.
              </span>
              <span>
                Canonical TMYx Weather Epoch: <strong>2011–2025</strong> • Engine: <strong>EnergyPlus 26.2.0</strong>
              </span>
            </div>
          </div>
        </div>
      )}
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
