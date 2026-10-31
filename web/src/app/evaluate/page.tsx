"use client";

import React, { useState, useMemo, useEffect, useRef, Suspense } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import Link from "next/link";
import { CITIES_DATA, DEFAULT_DESIGN } from "@/lib/constants";
import { predictDesignObjectives } from "@/lib/surrogate";
import { getReferencesForCity, getSurrogateMetricsForCity } from "@/lib/data";
import { formatPercentagePoints, formatEnergyDelta } from "@/lib/metrics";
import {
  SAMPLER_BOUNDS,
  clampDesignVariables,
  checkSampledRangeValidity,
  findNearestVerifiedParetoDesign
} from "@/lib/design_params";
import { CityKey, DesignVariables, ParetoDesign } from "@/types";
import { Shelter3DViewer } from "@/components/shelter/Shelter3DViewer";
import { Slider } from "@/components/ui/Slider";
import { Badge } from "@/components/ui/Badge";
import { Tooltip, InfoTip } from "@/components/ui/Tooltip";
import {
  Sliders,
  AlertTriangle,
  ShieldCheck,
  RotateCcw,
  Sparkles,
  Link as LinkIcon,
  Download,
  GitCompare,
  Check,
  Compass,
  X,
  ExternalLink,
  Layers
} from "lucide-react";

function EvaluateContent() {
  const router = useRouter();
  const searchParams = useSearchParams();

  // Initialize city from query or fallback to Jodhpur
  const initialCity = (searchParams?.get("city") as CityKey) || "Jodhpur";
  const [selectedCity, setSelectedCity] = useState<CityKey>(initialCity);

  // Parse and clamp initial design from URL search params
  const initialDesign = useMemo(() => {
    if (!searchParams) return DEFAULT_DESIGN;
    const rawParams: Record<string, string> = {};
    searchParams.forEach((val, key) => {
      rawParams[key] = val;
    });
    return clampDesignVariables(rawParams);
  }, [searchParams]);

  // Immediate design state for smooth 60fps slider dragging
  const [design, setDesign] = useState<DesignVariables>(initialDesign);

  // Debounced design state (60ms) for surrogate model inference & layout stability
  const [debouncedDesign, setDebouncedDesign] = useState<DesignVariables>(initialDesign);
  const debounceTimerRef = useRef<NodeJS.Timeout | null>(null);

  // Actions feedback state
  const [copiedLink, setCopiedLink] = useState<boolean>(false);
  const [showCompareModal, setShowCompareModal] = useState<boolean>(false);

  // Sync debounced design whenever design changes
  useEffect(() => {
    if (debounceTimerRef.current) {
      clearTimeout(debounceTimerRef.current);
    }
    debounceTimerRef.current = setTimeout(() => {
      setDebouncedDesign(design);
    }, 60);

    return () => {
      if (debounceTimerRef.current) clearTimeout(debounceTimerRef.current);
    };
  }, [design]);

  const cityInfo = CITIES_DATA[selectedCity];
  const { r1, r2 } = getReferencesForCity(selectedCity);
  const surrMetrics = useMemo(() => getSurrogateMetricsForCity(selectedCity), [selectedCity]);

  // Surrogate R2 metrics for reliability strip
  const r2Metrics = useMemo(() => {
    const mO1 = surrMetrics.find((m) => m.target === "O1_ml")?.r2 ?? 0.96;
    const mO2 = surrMetrics.find((m) => m.target === "O2")?.r2 ?? 0.99;
    const mAdapt = surrMetrics.find((m) => m.target === "O1_adapt")?.r2 ?? 0.97;
    return {
      r2_O1_ml: mO1.toFixed(2),
      r2_O2: mO2.toFixed(2),
      r2_O1_adapt: mAdapt.toFixed(2)
    };
  }, [surrMetrics]);

  // Sampled range validity check
  const rangeValidity = useMemo(() => checkSampledRangeValidity(design), [design]);

  // Live predicted objectives using debounced design
  const prediction = useMemo(() => {
    return predictDesignObjectives(selectedCity, debouncedDesign);
  }, [selectedCity, debouncedDesign]);

  // Nearest verified Pareto design for side-by-side comparison
  const nearestPareto = useMemo(() => {
    return findNearestVerifiedParetoDesign(selectedCity, design);
  }, [selectedCity, design]);

  // Slider change handler
  const handleVariableChange = <K extends keyof DesignVariables>(
    key: K,
    val: DesignVariables[K]
  ) => {
    setDesign((prev) => ({ ...prev, [key]: val }));
  };

  // Action 1: Reset to default design
  const resetToDefault = () => {
    setDesign(DEFAULT_DESIGN);
    router.replace(`/evaluate?city=${selectedCity}`);
  };

  // Action 2: Copy shareable link with query parameters
  const copyShareableLink = () => {
    if (typeof window === "undefined") return;
    const params = new URLSearchParams({
      city: selectedCity,
      roof_ins: design.roof_insulation_thickness.toString(),
      wall_ins: design.wall_insulation_thickness.toString(),
      mass: design.wall_mass_class,
      absorp: design.roof_solar_absorptance.toString(),
      wwr: design.wwr.toString(),
      orient: design.orientation.toString(),
      shading: design.shading_depth.toString(),
      vent: design.ventilation_ach.toString()
    });

    const shareUrl = `${window.location.origin}${window.location.pathname}?${params.toString()}`;
    navigator.clipboard.writeText(shareUrl).then(() => {
      setCopiedLink(true);
      window.history.replaceState(null, "", `?${params.toString()}`);
      setTimeout(() => setCopiedLink(false), 2000);
    });
  };

  // Action 3: Download custom design JSON
  const downloadDesignJson = () => {
    const payload = {
      app: "ClimateAdapt-Comfort",
      version: "2.0.0",
      city: selectedCity,
      climate_zone: cityInfo.zone,
      timestamp: new Date().toISOString(),
      envelope_variables: {
        roof_insulation_thickness_mm: design.roof_insulation_thickness,
        wall_insulation_thickness_mm: design.wall_insulation_thickness,
        wall_mass_class: design.wall_mass_class,
        roof_solar_absorptance: design.roof_solar_absorptance,
        window_to_wall_ratio_pct: design.wwr,
        azimuth_orientation_deg: design.orientation,
        overhang_shading_depth_m: design.shading_depth,
        natural_ventilation_ach: design.ventilation_ach
      },
      surrogate_predictions: {
        hours_uncomfortable_ml_pct: prediction.O1_ml,
        warm_discomfort_ml_pct: prediction.warm_ml,
        cool_discomfort_ml_pct: prediction.cool_ml,
        adaptive_90_discomfort_pct: prediction.O1_adapt,
        annual_hvac_energy_kwh_m2_yr: prediction.O2
      },
      reference_comparisons: {
        r1_lightweight: r1
          ? {
              delta_o1_ml_pp: Number((prediction.O1_ml - r1.O1_ml).toFixed(1)),
              delta_o2_kwh: Number((prediction.O2 - r1.O2).toFixed(1))
            }
          : null,
        r2_conventional: r2
          ? {
              delta_o1_ml_pp: Number((prediction.O1_ml - r2.O1_ml).toFixed(1)),
              delta_o2_kwh: Number((prediction.O2 - r2.O2).toFixed(1))
            }
          : null
      },
      reliability: {
        confidence_tier: cityInfo.confidence,
        within_lhs_bounds: rangeValidity.isWithinBounds,
        surrogate_r2: r2Metrics
      }
    };

    const blob = new Blob([JSON.stringify(payload, null, 2)], {
      type: "application/json"
    });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `ClimateAdapt_Custom_Design_${selectedCity}.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  // Action 4: Apply nearest verified design to sliders
  const applyVerifiedDesign = (pareto: ParetoDesign) => {
    const candRoofMm =
      pareto.roof_insulation_thickness <= 0.2
        ? Math.round(pareto.roof_insulation_thickness * 1000)
        : Math.round(pareto.roof_insulation_thickness);
    const candWallMm =
      pareto.wall_insulation_thickness <= 0.2
        ? Math.round(pareto.wall_insulation_thickness * 1000)
        : Math.round(pareto.wall_insulation_thickness);
    const candWwr =
      pareto.wwr <= 1.0 ? Math.round(pareto.wwr * 100) : Math.round(pareto.wwr);

    setDesign({
      roof_insulation_thickness: candRoofMm,
      wall_insulation_thickness: candWallMm,
      wall_mass_class: pareto.wall_mass_class,
      roof_solar_absorptance: Number(pareto.roof_solar_absorptance.toFixed(2)),
      wwr: candWwr,
      orientation: Math.round(pareto.orientation),
      shading_depth: Number(pareto.shading_depth.toFixed(2)),
      ventilation_ach: Number(pareto.ventilation_ach.toFixed(1))
    });
    setShowCompareModal(false);
  };

  return (
    <div className="space-y-8 pb-16">
      {/* Header & City Switcher */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-[var(--line)] pb-4">
        <div>
          <h1 className="text-3xl font-semibold text-[var(--ink)] tracking-tight flex items-center space-x-3">
            <Sliders className="w-7 h-7 text-[var(--primary)]" />
            <span>Custom Shelter Design Evaluator</span>
          </h1>
          <p className="text-sm text-[var(--ink-2)] mt-1 max-w-2xl">
            Simulate envelope configurations with instantaneous surrogate predictions calibrated across 10,000 EnergyPlus runs.
          </p>
        </div>

        {/* City Switcher Select */}
        <div className="flex items-center space-x-3 bg-[var(--surface-2)] border border-[var(--line)] p-2 rounded-[8px]">
          <span className="text-xs text-[var(--ink-2)]">Target station:</span>
          <select
            value={selectedCity}
            onChange={(e) => {
              const newCity = e.target.value as CityKey;
              setSelectedCity(newCity);
            }}
            className="bg-[var(--surface)] text-[var(--ink)] border border-[var(--line)] font-medium text-xs py-1.5 px-3 rounded-[6px] focus:outline-none focus:ring-2 focus:ring-[var(--primary)]"
          >
            {(Object.keys(CITIES_DATA) as CityKey[]).map((c) => (
              <option key={c} value={c}>
                {CITIES_DATA[c].name} ({CITIES_DATA[c].zone})
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* Action Toolbar */}
      <div className="flex flex-wrap items-center justify-between gap-3 p-3 rounded-[8px] bg-[var(--surface-2)] border border-[var(--line)] text-xs">
        <div className="flex items-center space-x-2">
          <button
            onClick={resetToDefault}
            className="px-3 py-1.5 rounded-[6px] bg-[var(--surface)] hover:bg-[var(--surface-2)] text-[var(--ink)] border border-[var(--line)] transition flex items-center space-x-1.5 shadow-sm"
            title="Reset sliders to standard baseline shelter"
          >
            <RotateCcw className="w-3.5 h-3.5 text-[var(--ink-2)]" />
            <span>Reset</span>
          </button>
          <button
            onClick={copyShareableLink}
            className="px-3 py-1.5 rounded-[6px] bg-[var(--surface)] hover:bg-[var(--surface-2)] text-[var(--ink)] border border-[var(--line)] transition flex items-center space-x-1.5 shadow-sm"
            title="Copy shareable link with current slider parameters"
          >
            {copiedLink ? (
              <>
                <Check className="w-3.5 h-3.5 text-[var(--good)]" />
                <span className="text-[var(--good)] font-medium">Copied link ✓</span>
              </>
            ) : (
              <>
                <LinkIcon className="w-3.5 h-3.5 text-[var(--ink-2)]" />
                <span>Copy link to this design</span>
              </>
            )}
          </button>
        </div>

        <div className="flex items-center space-x-2">
          <button
            onClick={downloadDesignJson}
            className="px-3 py-1.5 rounded-[6px] bg-[var(--surface)] hover:bg-[var(--surface-2)] text-[var(--ink)] border border-[var(--line)] transition flex items-center space-x-1.5 shadow-sm"
            title="Download design variables and predictions as JSON"
          >
            <Download className="w-3.5 h-3.5 text-[var(--ink-2)]" />
            <span>Download as JSON</span>
          </button>
          <button
            onClick={() => setShowCompareModal(true)}
            className="px-3 py-1.5 rounded-[6px] bg-[var(--surface)] hover:bg-[var(--surface-2)] text-[var(--primary)] border border-[var(--primary)]/40 font-medium transition flex items-center space-x-1.5 shadow-sm"
            title="Compare with nearest EnergyPlus-verified Pareto design"
          >
            <GitCompare className="w-3.5 h-3.5" />
            <span>Compare with nearest Pareto design</span>
          </button>
        </div>
      </div>

      {/* Reliability Strip (Surrogate R², LHS Bounds Check, Single Confidence Banner) */}
      <div className="rounded-[8px] border border-[var(--line)] bg-[var(--surface)] p-4 space-y-3">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 text-xs">
          <div className="flex flex-wrap items-center gap-3">
            <span className="font-semibold text-[var(--ink)] flex items-center space-x-1.5">
              <Sparkles className="w-4 h-4 text-[var(--primary)]" />
              <span>Reliability & Calibration:</span>
            </span>

            {/* Surrogate R² Readouts */}
            <div className="flex items-center space-x-2 tabular-nums">
              <span className="px-2 py-0.5 rounded bg-[var(--surface-2)] border border-[var(--line)] text-[var(--ink)]">
                Surrogate R²(O1 ML) = <strong>{r2Metrics.r2_O1_ml}</strong>
              </span>
              <span className="px-2 py-0.5 rounded bg-[var(--surface-2)] border border-[var(--line)] text-[var(--ink)]">
                R²(O2) = <strong>{r2Metrics.r2_O2}</strong>
              </span>
            </div>

            {/* LHS Sampling Range Validity */}
            {rangeValidity.isWithinBounds ? (
              <span className="px-2 py-0.5 rounded bg-[var(--good)]/10 text-[var(--good)] border border-[var(--good)]/30 font-medium flex items-center space-x-1">
                <Check className="w-3 h-3" />
                <span>Within sampled LHS bounds</span>
              </span>
            ) : (
              <span className="px-2 py-0.5 rounded bg-[var(--warn)]/10 text-[var(--warn)] border border-[var(--warn)]/30 font-medium flex items-center space-x-1">
                <AlertTriangle className="w-3 h-3" />
                <span>Extrapolation: {rangeValidity.outOfBoundsFields.join(", ")} out of range</span>
              </span>
            )}
          </div>

          {/* Confidence Tier Tag */}
          <div className="flex items-center space-x-2">
            <span className="text-[var(--ink-2)]">Climate confidence:</span>
            <Badge variant={cityInfo.confidence === "Medium" ? "primary" : "warn"}>
              {cityInfo.confidence === "Medium" ? "Standard (Medium)" : "Low confidence"}
            </Badge>
          </div>
        </div>

        {/* Single Non-Duplicated Confidence Explanation */}
        <div className="pt-2 border-t border-[var(--line)] text-xs text-[var(--ink-2)] flex items-start space-x-2">
          {cityInfo.confidence === "Medium" ? (
            <ShieldCheck className="w-4 h-4 text-[var(--good)] shrink-0 mt-0.5" />
          ) : (
            <AlertTriangle className="w-4 h-4 text-[var(--warn)] shrink-0 mt-0.5" />
          )}
          <span className="text-[12px] leading-relaxed">
            {cityInfo.confidence === "Medium" ? (
              <>
                <strong>High validation consensus:</strong> Dual comfort judges exhibit Spearman rank correlation $r_s \ge 0.80$ and adaptive comfort criteria apply to $\ge 80\%$ of annual weather hours.
              </>
            ) : (
              <>
                <strong>Low confidence guidance:</strong> {cityInfo.envelopeAlert} Use predictions as preliminary directional guidance; verify critical shelter envelopes with local bioclimatic engineering.
              </>
            )}
          </span>
        </div>
      </div>

      {/* Main Grid: Controls on Left, 3D + Results on Right */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
        {/* Left Column: 8 Design Variable Sliders strictly bounded to src/sim/sampler.py */}
        <div className="lg:col-span-6 space-y-6">
          <div className="rounded-[8px] border border-[var(--line)] bg-[var(--surface)] p-6 space-y-5">
            <div className="flex items-center justify-between border-b border-[var(--line)] pb-3">
              <h3 className="text-base font-semibold text-[var(--ink)] flex items-center space-x-2">
                <Sliders className="w-4 h-4 text-[var(--primary)]" />
                <span>Envelope design variables</span>
              </h3>
              <span className="text-xs text-[var(--ink-2)]">
                LHS sampling bounds (seed 42)
              </span>
            </div>

            {/* 1. Roof Insulation (0 - 150 mm) */}
            <Slider
              label="Roof insulation thickness"
              value={design.roof_insulation_thickness}
              min={SAMPLER_BOUNDS.roof_insulation_thickness.min}
              max={SAMPLER_BOUNDS.roof_insulation_thickness.max}
              step={SAMPLER_BOUNDS.roof_insulation_thickness.step}
              unit="mm"
              displayValue={`${design.roof_insulation_thickness} mm`}
              description="0 mm (uninsulated emergency shelter) to 150 mm (superinsulated passive roof)"
              onChange={(v) => handleVariableChange("roof_insulation_thickness", Math.round(v))}
            />

            {/* 2. Wall Insulation (0 - 150 mm) */}
            <Slider
              label="Wall insulation thickness"
              value={design.wall_insulation_thickness}
              min={SAMPLER_BOUNDS.wall_insulation_thickness.min}
              max={SAMPLER_BOUNDS.wall_insulation_thickness.max}
              step={SAMPLER_BOUNDS.wall_insulation_thickness.step}
              unit="mm"
              displayValue={`${design.wall_insulation_thickness} mm`}
              description="0 mm (single leaf/uninsulated) to 150 mm (insulated cavity)"
              onChange={(v) => handleVariableChange("wall_insulation_thickness", Math.round(v))}
            />

            {/* 3. Wall Mass Class (light, medium, heavy) */}
            <div className="space-y-1.5">
              <div className="flex items-center justify-between">
                <span className="font-medium text-xs text-[var(--ink)] block">Thermal wall mass class</span>
                <span className="text-xs text-[var(--ink-2)] capitalize font-semibold">{design.wall_mass_class}</span>
              </div>
              <div className="grid grid-cols-3 gap-2">
                {SAMPLER_BOUNDS.wall_mass_class.map((mass) => (
                  <button
                    key={mass}
                    type="button"
                    onClick={() => handleVariableChange("wall_mass_class", mass)}
                    className={`py-2 px-3 rounded-[6px] text-xs font-medium capitalize border transition ${
                      design.wall_mass_class === mass
                        ? "bg-[var(--surface-2)] border-[var(--primary)] text-[var(--ink)] font-semibold shadow-sm ring-1 ring-[var(--primary)]"
                        : "bg-[var(--surface)] border-[var(--line)] text-[var(--ink-2)] hover:text-[var(--ink)] hover:bg-[var(--surface-2)]/50"
                    }`}
                  >
                    {mass} {mass === "medium" ? "(Brick)" : mass === "heavy" ? "(Concrete)" : "(Timber)"}
                  </button>
                ))}
              </div>
            </div>

            {/* 4. Roof Solar Absorptance (0.30 - 0.90) */}
            <Slider
              label="Roof solar absorptance"
              value={design.roof_solar_absorptance}
              min={SAMPLER_BOUNDS.roof_solar_absorptance.min}
              max={SAMPLER_BOUNDS.roof_solar_absorptance.max}
              step={SAMPLER_BOUNDS.roof_solar_absorptance.step}
              displayValue={design.roof_solar_absorptance.toFixed(2)}
              description={
                design.roof_solar_absorptance <= 0.4
                  ? "Cool reflective white coating (α ≤ 0.40 cuts solar gain)"
                  : "Standard dark/bitumen finish (α > 0.40 absorbs solar heat)"
              }
              onChange={(v) => handleVariableChange("roof_solar_absorptance", Number(v.toFixed(2)))}
            />

            {/* 5. Window-to-Wall Ratio (WWR) (5% - 40%) */}
            <Slider
              label="Window-to-wall ratio (WWR)"
              value={design.wwr}
              min={SAMPLER_BOUNDS.wwr.min}
              max={SAMPLER_BOUNDS.wwr.max}
              step={SAMPLER_BOUNDS.wwr.step}
              unit="%"
              displayValue={`${design.wwr}%`}
              description="5% (minimum daylight aperture) to 40% (maximum natural glazing)"
              onChange={(v) => handleVariableChange("wwr", Math.round(v))}
            />

            {/* 6. Orientation (0 - 360°) with exact cardinal ticks and interactive compass */}
            <div className="space-y-1.5">
              <div className="flex items-center justify-between">
                <span className="text-xs font-medium text-[var(--ink)] flex items-center space-x-1.5">
                  <Compass className="w-3.5 h-3.5 text-[var(--primary)]" />
                  <span>Azimuth orientation (0–360°)</span>
                </span>
              </div>

              <Slider
                label=""
                value={design.orientation}
                min={SAMPLER_BOUNDS.orientation.min}
                max={SAMPLER_BOUNDS.orientation.max}
                step={SAMPLER_BOUNDS.orientation.step}
                unit="°"
                displayValue={`${design.orientation}°`}
                ticks={[
                  { value: 0, label: "0° (N)" },
                  { value: 90, label: "90° (E)" },
                  { value: 180, label: "180° (S)" },
                  { value: 270, label: "270° (W)" },
                  { value: 360, label: "360° (N)" }
                ]}
                onChange={(v) => handleVariableChange("orientation", Math.round(v))}
              />

              {/* Cardinal quick-select buttons */}
              <div className="flex items-center justify-end space-x-1 pt-1 text-[11px]">
                <span className="text-[var(--ink-2)] mr-1">Snap to:</span>
                {[
                  { deg: 0, label: "North" },
                  { deg: 90, label: "East" },
                  { deg: 180, label: "South" },
                  { deg: 270, label: "West" }
                ].map((card) => (
                  <button
                    key={card.deg}
                    type="button"
                    onClick={() => handleVariableChange("orientation", card.deg)}
                    className="px-2 py-0.5 rounded bg-[var(--surface-2)] border border-[var(--line)] hover:bg-[var(--surface)] text-[var(--ink)] transition"
                  >
                    {card.label}
                  </button>
                ))}
              </div>
            </div>

            {/* 7. Overhang Shading Depth (0.0 - 1.0 m) */}
            <Slider
              label="Overhang shading depth"
              value={design.shading_depth}
              min={SAMPLER_BOUNDS.shading_depth.min}
              max={SAMPLER_BOUNDS.shading_depth.max}
              step={SAMPLER_BOUNDS.shading_depth.step}
              unit="m"
              displayValue={`${design.shading_depth.toFixed(2)} m`}
              description="0.0 m (flush facade) to 1.0 m (full-depth solar shading projection)"
              onChange={(v) => handleVariableChange("shading_depth", Number(v.toFixed(2)))}
            />

            {/* 8. Natural Ventilation Rate (1.0 - 15.0 ACH) */}
            <Slider
              label="Natural ventilation air exchange"
              value={design.ventilation_ach}
              min={SAMPLER_BOUNDS.ventilation_ach.min}
              max={SAMPLER_BOUNDS.ventilation_ach.max}
              step={SAMPLER_BOUNDS.ventilation_ach.step}
              unit="ACH"
              displayValue={`${design.ventilation_ach.toFixed(1)} ACH`}
              description="1.0 ACH (closed windows / still air) to 15.0 ACH (cross ventilation)"
              onChange={(v) => handleVariableChange("ventilation_ach", Number(v.toFixed(1)))}
            />
          </div>
        </div>

        {/* Right Column: Illustrative 3D Model + Side-by-Side Dual Judge Results Panel */}
        <div className="lg:col-span-6 space-y-6">
          {/* Responsive 3D Canvas responding to every slider */}
          <Shelter3DViewer design={design} />

          {/* Results Panel */}
          <div className="rounded-[8px] border border-[var(--line)] bg-[var(--surface)] p-6 space-y-5">
            <div className="border-b border-[var(--line)] pb-3">
              <h3 className="text-base font-semibold text-[var(--ink)] flex items-center space-x-2">
                <span>Simulation results & reference deltas</span>
              </h3>
              <span className="text-xs text-[var(--ink-2)]">
                Instantaneous surrogate estimation calibrated to EnergyPlus ground truth
              </span>
            </div>

            {/* 1. Hours Uncomfortable: Side-by-Side Comfort Checks */}
            <div className="space-y-2">
              <div className="flex items-center space-x-1.5">
                <span className="text-xs font-semibold uppercase tracking-wider text-[var(--ink-2)]">
                  Hours uncomfortable
                </span>
                <InfoTip
                  label="Hours uncomfortable"
                  content="Objective O1: Percentage of annual hours (out of 8,760 hours/yr) where indoor temperatures fall outside comfort boundaries."
                />
              </div>

              {/* Side-by-Side Two Comfort Checks */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                {/* Column A: ML Comfort Model (Primary Judge) */}
                <div className="p-4 rounded-[8px] border border-[var(--line)] bg-[var(--surface-2)] space-y-2">
                  <div className="flex justify-between items-start">
                    <div>
                      <span className="font-semibold text-xs text-[var(--ink)] block">
                        ML comfort check
                      </span>
                      <span className="text-[11px] text-[var(--ink-2)] block">
                        Ablation A3 XGBoost
                      </span>
                    </div>
                    <Badge variant="primary">Primary</Badge>
                  </div>

                  <div className="flex items-baseline space-x-1">
                    <span className="text-2xl font-bold text-[var(--hot)] tabular-nums">
                      {prediction.O1_ml}%
                    </span>
                    <span className="text-xs text-[var(--ink-2)]">hours</span>
                  </div>

                  <div className="text-[11px] text-[var(--ink-2)] tabular-nums border-t border-[var(--line)] pt-1.5 flex justify-between">
                    <span>Warm: <strong>{prediction.warm_ml}%</strong></span>
                    <span>Cool: <strong>{prediction.cool_ml}%</strong></span>
                  </div>

                  {/* Deltas vs R2 and R1 in percentage points (pp) */}
                  <div className="pt-2 border-t border-[var(--line)] space-y-1 text-xs tabular-nums">
                    <div className="text-[11px] font-medium text-[var(--ink-2)]">Reference deltas:</div>
                    {r2 && (
                      <div className="flex justify-between text-[11px]">
                        <span className="text-[var(--ink-2)]">vs R2 Conventional:</span>
                        <strong className="text-[var(--good)]">
                          {formatPercentagePoints(prediction.O1_ml - r2.O1_ml)}
                        </strong>
                      </div>
                    )}
                    {r1 && (
                      <div className="flex justify-between text-[11px]">
                        <span className="text-[var(--ink-2)]">vs R1 Lightweight:</span>
                        <strong className="text-[var(--good)]">
                          {formatPercentagePoints(prediction.O1_ml - r1.O1_ml)}
                        </strong>
                      </div>
                    )}
                  </div>
                </div>

                {/* Column B: ASHRAE Adaptive 90% (Secondary Judge) */}
                <div className="p-4 rounded-[8px] border border-[var(--line)] bg-[var(--surface-2)] space-y-2">
                  <div className="flex justify-between items-start">
                    <div>
                      <span className="font-semibold text-xs text-[var(--ink)] block">
                        Adaptive 90% check
                      </span>
                      <span className="text-[11px] text-[var(--ink-2)] block">
                        ASHRAE 55 / IMAC
                      </span>
                    </div>
                    <Badge variant="neutral">Adaptive</Badge>
                  </div>

                  <div className="flex items-baseline space-x-1">
                    <span className="text-2xl font-bold text-[var(--ink)] tabular-nums">
                      {prediction.O1_adapt}%
                    </span>
                    <span className="text-xs text-[var(--ink-2)]">hours</span>
                  </div>

                  <div className="text-[11px] text-[var(--ink-2)] tabular-nums border-t border-[var(--line)] pt-1.5">
                    <span>7-day running mean outdoor temperature comfort band</span>
                  </div>

                  {/* Deltas vs R2 and R1 in percentage points (pp) */}
                  <div className="pt-2 border-t border-[var(--line)] space-y-1 text-xs tabular-nums">
                    <div className="text-[11px] font-medium text-[var(--ink-2)]">Reference deltas:</div>
                    {r2 && (
                      <div className="flex justify-between text-[11px]">
                        <span className="text-[var(--ink-2)]">vs R2 Conventional:</span>
                        <strong className="text-[var(--good)]">
                          {formatPercentagePoints(prediction.O1_adapt - r2.O1_adapt)}
                        </strong>
                      </div>
                    )}
                    {r1 && (
                      <div className="flex justify-between text-[11px]">
                        <span className="text-[var(--ink-2)]">vs R1 Lightweight:</span>
                        <strong className="text-[var(--good)]">
                          {formatPercentagePoints(prediction.O1_adapt - r1.O1_adapt)}
                        </strong>
                      </div>
                    )}
                  </div>
                </div>
              </div>
            </div>

            {/* 2. Heating & Cooling Energy Card */}
            <div className="space-y-2 pt-2">
              <div className="flex items-center space-x-1.5">
                <span className="text-xs font-semibold uppercase tracking-wider text-[var(--ink-2)]">
                  Heating & cooling energy
                </span>
                <InfoTip
                  label="Heating & cooling energy"
                  content="Objective O2: Annual ideal-loads HVAC energy in kWh/m²/yr needed to maintain indoor operative temperatures between 20°C (heating) and 26°C (cooling)."
                />
              </div>

              <div className="p-4 rounded-[8px] border border-[var(--line)] bg-[var(--surface-2)] space-y-3">
                <div className="flex flex-col sm:flex-row sm:items-baseline justify-between gap-1">
                  <div className="flex items-baseline space-x-2">
                    <span className="text-3xl font-bold text-[var(--ink)] tabular-nums">
                      {prediction.O2.toFixed(1)}
                    </span>
                    <span className="text-xs text-[var(--ink-2)]">kWh/m²/yr</span>
                  </div>
                  <span className="text-[11px] text-[var(--ink-2)]">
                    Ideal-loads HVAC (26°C cool / 20°C heat)
                  </span>
                </div>

                {/* Deltas vs R2 and R1 in kWh/m²/yr */}
                <div className="pt-2 border-t border-[var(--line)] space-y-1.5 text-xs tabular-nums">
                  {r2 && (
                    <div className="flex justify-between items-center text-[12px]">
                      <span className="text-[var(--ink-2)]">vs R2 Conventional ({r2.O2.toFixed(1)} kWh/m²/yr):</span>
                      <strong className="text-[var(--good)]">
                        {formatEnergyDelta(prediction.O2 - r2.O2)}
                      </strong>
                    </div>
                  )}
                  {r1 && (
                    <div className="flex justify-between items-center text-[12px]">
                      <span className="text-[var(--ink-2)]">vs R1 Lightweight ({r1.O2.toFixed(1)} kWh/m²/yr):</span>
                      <strong className="text-[var(--good)]">
                        {formatEnergyDelta(prediction.O2 - r1.O2)}
                      </strong>
                    </div>
                  )}
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Side-by-Side Comparison Modal with Nearest Verified Pareto Design */}
      {showCompareModal && nearestPareto && (
        <div
          role="dialog"
          aria-modal="true"
          className="fixed inset-0 z-50 bg-black/50 backdrop-blur-xs flex items-center justify-center p-4 overflow-y-auto"
        >
          <div className="bg-[var(--surface)] border border-[var(--line)] rounded-[8px] max-w-2xl w-full p-6 space-y-5 shadow-xl">
            <div className="flex items-center justify-between border-b border-[var(--line)] pb-3">
              <div>
                <span className="text-xs font-semibold text-[var(--primary)] uppercase tracking-wider block">
                  Ground Truth Verification Benchmark
                </span>
                <h3 className="text-lg font-semibold text-[var(--ink)] flex items-center space-x-2">
                  <span>Comparison with Nearest Pareto Design</span>
                  <code>{nearestPareto.nearestDesign.pareto_id}</code>
                  <Badge variant="warn">★ Verified</Badge>
                </h3>
              </div>
              <button
                onClick={() => setShowCompareModal(false)}
                className="p-1 rounded-[6px] hover:bg-[var(--surface-2)] text-[var(--ink-2)] hover:text-[var(--ink)] transition"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <p className="text-xs text-[var(--ink-2)] leading-relaxed">
              Below is the closest non-dominated shelter design for <strong>{cityInfo.name}</strong> directly simulated and verified in EnergyPlus 26.2.0 (distance metric = {nearestPareto.distance}).
            </p>

            {/* Comparison Table */}
            <div className="overflow-x-auto rounded-[var(--radius)] border border-[var(--line)]">
              <table className="w-full text-xs text-left tabular-nums divide-y divide-[var(--line)]">
                <thead className="bg-[var(--surface-2)] text-[var(--ink-2)]">
                  <tr>
                    <th className="py-2 px-3 text-left">Variable / Objective</th>
                    <th className="py-2 px-3 font-semibold text-[var(--ink)] text-right">Your Custom Design</th>
                    <th className="py-2 px-3 font-semibold text-[var(--primary)] text-right">Nearest Verified ({nearestPareto.nearestDesign.pareto_id})</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-[var(--line)] text-[var(--ink)]">
                  <tr>
                    <td className="py-2 px-3 font-medium text-[var(--ink-2)] text-left">Roof Insulation</td>
                    <td className="py-2 px-3 text-right">{design.roof_insulation_thickness} mm</td>
                    <td className="py-2 px-3 font-semibold text-right">
                      {Math.round(nearestPareto.nearestDesign.roof_insulation_thickness * 1000)} mm
                    </td>
                  </tr>
                  <tr>
                    <td className="py-2 px-3 font-medium text-[var(--ink-2)] text-left">Wall Insulation</td>
                    <td className="py-2 px-3 text-right">{design.wall_insulation_thickness} mm</td>
                    <td className="py-2 px-3 font-semibold text-right">
                      {Math.round(nearestPareto.nearestDesign.wall_insulation_thickness * 1000)} mm
                    </td>
                  </tr>
                  <tr>
                    <td className="py-2 px-3 font-medium text-[var(--ink-2)] text-left">Thermal Wall Mass</td>
                    <td className="py-2 px-3 capitalize text-right">{design.wall_mass_class}</td>
                    <td className="py-2 px-3 font-semibold capitalize text-right">{nearestPareto.nearestDesign.wall_mass_class}</td>
                  </tr>
                  <tr>
                    <td className="py-2 px-3 font-medium text-[var(--ink-2)] text-left">Roof Solar Absorptance</td>
                    <td className="py-2 px-3 text-right">{design.roof_solar_absorptance.toFixed(2)}</td>
                    <td className="py-2 px-3 font-semibold text-right">{nearestPareto.nearestDesign.roof_solar_absorptance.toFixed(2)}</td>
                  </tr>
                  <tr>
                    <td className="py-2 px-3 font-medium text-[var(--ink-2)] text-left">Window-to-Wall Ratio (WWR)</td>
                    <td className="py-2 px-3 text-right">{design.wwr}%</td>
                    <td className="py-2 px-3 font-semibold text-right">
                      {Math.round(nearestPareto.nearestDesign.wwr <= 1 ? nearestPareto.nearestDesign.wwr * 100 : nearestPareto.nearestDesign.wwr)}%
                    </td>
                  </tr>
                  <tr>
                    <td className="py-2 px-3 font-medium text-[var(--ink-2)] text-left">Azimuth Orientation</td>
                    <td className="py-2 px-3 text-right">{design.orientation}°</td>
                    <td className="py-2 px-3 font-semibold text-right">{Math.round(nearestPareto.nearestDesign.orientation)}°</td>
                  </tr>
                  <tr>
                    <td className="py-2 px-3 font-medium text-[var(--ink-2)] text-left">Overhang Shading Depth</td>
                    <td className="py-2 px-3 text-right">{design.shading_depth.toFixed(2)} m</td>
                    <td className="py-2 px-3 font-semibold text-right">{nearestPareto.nearestDesign.shading_depth.toFixed(2)} m</td>
                  </tr>
                  <tr>
                    <td className="py-2 px-3 font-medium text-[var(--ink-2)] text-left">Natural Ventilation</td>
                    <td className="py-2 px-3 text-right">{design.ventilation_ach.toFixed(1)} ACH</td>
                    <td className="py-2 px-3 font-semibold text-right">{nearestPareto.nearestDesign.ventilation_ach.toFixed(1)} ACH</td>
                  </tr>
                  <tr className="bg-[var(--surface-2)]/60">
                    <td className="py-2 px-3 font-medium text-[var(--ink)] text-left">O1 Discomfort (ML model)</td>
                    <td className="py-2 px-3 text-[var(--hot)] font-semibold text-right">{prediction.O1_ml}%</td>
                    <td className="py-2 px-3 font-bold text-[var(--hot)] text-right">
                      {nearestPareto.nearestDesign.verified_O1_ml != null
                        ? `${nearestPareto.nearestDesign.verified_O1_ml.toFixed(1)}% (verified)`
                        : `${nearestPareto.nearestDesign.O1_ml.toFixed(1)}%`}
                    </td>
                  </tr>
                  <tr className="bg-[var(--surface-2)]/60">
                    <td className="py-2 px-3 font-medium text-[var(--ink)] text-left">O2 Annual HVAC Energy</td>
                    <td className="py-2 px-3 font-semibold text-right">{prediction.O2.toFixed(1)} kWh/m²</td>
                    <td className="py-2 px-3 font-bold text-[var(--ink)] text-right">
                      {nearestPareto.nearestDesign.verified_O2 != null
                        ? `${nearestPareto.nearestDesign.verified_O2.toFixed(1)} kWh/m² (verified)`
                        : `${nearestPareto.nearestDesign.O2.toFixed(1)} kWh/m²`}
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>

            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pt-2">
              <Link
                href={`/pareto?city=${selectedCity}&design=${nearestPareto.nearestDesign.pareto_id}`}
                className="text-xs text-[var(--primary)] hover:underline flex items-center space-x-1"
              >
                <span>View {nearestPareto.nearestDesign.pareto_id} in Pareto Explorer</span>
                <ExternalLink className="w-3.5 h-3.5" />
              </Link>

              <div className="flex items-center space-x-2">
                <button
                  onClick={() => setShowCompareModal(false)}
                  className="px-3 py-1.5 rounded-[6px] bg-[var(--surface-2)] hover:bg-[var(--surface)] border border-[var(--line)] text-xs text-[var(--ink)] transition"
                >
                  Close
                </button>
                <button
                  onClick={() => applyVerifiedDesign(nearestPareto.nearestDesign)}
                  className="px-3.5 py-1.5 rounded-[6px] bg-[var(--primary)] hover:bg-[var(--primary)]/90 text-white text-xs font-medium transition flex items-center space-x-1.5 shadow-sm"
                >
                  <Layers className="w-3.5 h-3.5" />
                  <span>Apply this verified design to sliders</span>
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default function EvaluatePage() {
  return (
    <Suspense fallback={<div className="py-20 text-center text-[var(--ink-2)] text-sm">Loading custom design evaluator...</div>}>
      <EvaluateContent />
    </Suspense>
  );
}
