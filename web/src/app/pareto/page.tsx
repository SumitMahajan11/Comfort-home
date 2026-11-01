"use client";

import React, { useState, useMemo, useRef, Suspense } from "react";
import { useSearchParams } from "next/navigation";
import { CITIES_DATA } from "@/lib/constants";
import { getParetoDesigns, getReferencesForCity, getS3ResultForCity } from "@/lib/data";
import { formatPercentagePoints, formatEnergyDelta } from "@/lib/metrics";
import {
  formatInsulationMm,
  formatGlazingPct,
  formatAzimuthWithCompass,
  formatOverhangM,
  formatVentilationAch,
  formatSolarAbsorptance,
  formatWallMassClass,
  formatDiscomfortPct,
  formatEnergyValue,
  formatO1Error,
  formatO2Error
} from "@/lib/format";
import { CityKey, ParetoDesign } from "@/types";
import { Badge } from "@/components/ui/Badge";
import { InfoTip } from "@/components/ui/Tooltip";
import {
  Layers,
  Sparkles,
  Download,
  Star,
  Award,
  TrendingDown,
  Table as TableIcon,
  FileSpreadsheet,
  Info
} from "lucide-react";
import {
  ResponsiveContainer,
  ScatterChart,
  Scatter,
  XAxis,
  YAxis,
  ZAxis,
  Tooltip,
  CartesianGrid,
  ReferenceDot
} from "recharts";

// SVG helper to generate a 5-point star path
function getStarPath(cx: number, cy: number, outerRadius: number, innerRadius: number): string {
  const points: string[] = [];
  for (let i = 0; i < 10; i++) {
    const angle = (i * Math.PI) / 5 - Math.PI / 2;
    const r = i % 2 === 0 ? outerRadius : innerRadius;
    const x = cx + r * Math.cos(angle);
    const y = cy + r * Math.sin(angle);
    points.push(`${i === 0 ? "M" : "L"} ${x.toFixed(2)} ${y.toFixed(2)}`);
  }
  points.push("Z");
  return points.join(" ");
}

interface ScatterDotProps {
  cx?: number;
  cy?: number;
  payload?: ParetoDesign;
  selectedId?: string | null;
  onSelect?: (id: string) => void;
}

const CustomScatterDot: React.FC<ScatterDotProps> = ({
  cx,
  cy,
  payload,
  selectedId,
  onSelect
}) => {
  if (cx == null || cy == null || !payload) return null;

  const isVerified = Boolean(payload.is_verified);
  // Match selection by design_id (pareto_id), strictly not by array index
  const isSelected = payload.pareto_id === selectedId;

  return (
    <g
      tabIndex={-1}
      role="button"
      aria-label={`Design ${payload.pareto_id}${isVerified ? ", verified" : ""}${isSelected ? ", selected" : ""}`}
      onClick={(e) => {
        e.stopPropagation();
        onSelect?.(payload.pareto_id);
      }}
      className="cursor-pointer transition-transform hover:scale-125 focus:outline-none"
    >
      {/* Outer selection ring */}
      {isSelected && (
        <circle
          cx={cx}
          cy={cy}
          r={isVerified ? 12 : 10}
          fill="none"
          stroke="var(--ink)"
          strokeWidth={2.5}
          className="transition-all"
        />
      )}

      {/* Verified design: filled star; Standard: circle */}
      {isVerified ? (
        <path
          d={getStarPath(cx, cy, isSelected ? 8 : 6.5, isSelected ? 3.8 : 3.2)}
          fill="var(--warn)"
          stroke="var(--surface)"
          strokeWidth={1}
        />
      ) : (
        <circle
          cx={cx}
          cy={cy}
          r={isSelected ? 6 : 4.5}
          fill="var(--link)"
          stroke="var(--surface)"
          strokeWidth={1}
        />
      )}
    </g>
  );
};

function ParetoExplorerContent() {
  const searchParams = useSearchParams();
  const initialCity = (searchParams?.get("city") as CityKey) || "Jodhpur";
  const initialDesign = searchParams?.get("design") || null;
  const [selectedCity, setSelectedCity] = useState<CityKey>(initialCity);
  const [selectedDesignId, setSelectedDesignId] = useState<string | null>(initialDesign);
  const [filterVerifiedOnly, setFilterVerifiedOnly] = useState<boolean>(false);
  const [showTable, setShowTable] = useState<boolean>(false);

  const inspectorRef = useRef<HTMLDivElement>(null);

  const { r1, r2 } = getReferencesForCity(selectedCity);
  const s3Result = getS3ResultForCity(selectedCity);
  const allDesigns = useMemo(() => getParetoDesigns(selectedCity), [selectedCity]);

  const verifiedDesigns = useMemo(
    () => allDesigns.filter((d) => d.is_verified),
    [allDesigns]
  );

  // Filtered designs: 100 designs by default; 10 when verified-only is active
  const displayDesigns = useMemo(() => {
    if (filterVerifiedOnly) {
      return verifiedDesigns;
    }
    return allDesigns;
  }, [allDesigns, verifiedDesigns, filterVerifiedOnly]);

  // Selected design object: matched strictly by pareto_id
  const selectedDesign = useMemo(() => {
    if (selectedDesignId) {
      const found = allDesigns.find((d) => d.pareto_id === selectedDesignId);
      if (found) return found;
    }
    // Default to knee point or first design
    const knee = allDesigns.find((d: any) => d.selection_role === "Knee_Point");
    return knee || allDesigns[Math.floor(allDesigns.length / 2)] || allDesigns[0];
  }, [allDesigns, selectedDesignId]);

  // Keyboard navigation handler for chart
  const handleChartKeyDown = (e: React.KeyboardEvent) => {
    if (!displayDesigns.length) return;
    const currentIndex = displayDesigns.findIndex(
      (d) => d.pareto_id === selectedDesign?.pareto_id
    );
    if (e.key === "ArrowRight" || e.key === "ArrowDown") {
      e.preventDefault();
      const nextIndex =
        currentIndex < displayDesigns.length - 1 ? currentIndex + 1 : 0;
      setSelectedDesignId(displayDesigns[nextIndex].pareto_id);
    } else if (e.key === "ArrowLeft" || e.key === "ArrowUp") {
      e.preventDefault();
      const prevIndex =
        currentIndex > 0 ? currentIndex - 1 : displayDesigns.length - 1;
      setSelectedDesignId(displayDesigns[prevIndex].pareto_id);
    }
  };

  // Presets: lowest discomfort, lowest energy, knee point
  const applyPreset = (preset: "lowest_discomfort" | "lowest_energy" | "knee") => {
    let target: ParetoDesign | undefined;
    if (preset === "lowest_discomfort") {
      target = [...allDesigns].sort((a, b) => a.O1_ml - b.O1_ml)[0];
    } else if (preset === "lowest_energy") {
      target = [...allDesigns].sort((a, b) => a.O2 - b.O2)[0];
    } else {
      // Find labeled knee point, or compute minimum normalized euclidean distance to ideal point
      target = allDesigns.find((d: any) => d.selection_role === "Knee_Point");
      if (!target) {
        const minO1 = Math.min(...allDesigns.map((d) => d.O1_ml));
        const maxO1 = Math.max(...allDesigns.map((d) => d.O1_ml));
        const minO2 = Math.min(...allDesigns.map((d) => d.O2));
        const maxO2 = Math.max(...allDesigns.map((d) => d.O2));
        target = [...allDesigns].sort((a, b) => {
          const distA = Math.hypot(
            (a.O1_ml - minO1) / (maxO1 - minO1 || 1),
            (a.O2 - minO2) / (maxO2 - minO2 || 1)
          );
          const distB = Math.hypot(
            (b.O1_ml - minO1) / (maxO1 - minO1 || 1),
            (b.O2 - minO2) / (maxO2 - minO2 || 1)
          );
          return distA - distB;
        })[0];
      }
    }

    if (target) {
      setSelectedDesignId(target.pareto_id);
      inspectorRef.current?.scrollIntoView({ behavior: "smooth", block: "nearest" });
    }
  };

  // Export single design as JSON
  const exportSelectedDesignJson = () => {
    if (!selectedDesign) return;
    const blob = new Blob([JSON.stringify(selectedDesign, null, 2)], {
      type: "application/json"
    });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `ClimateAdapt_Shelter_${selectedCity}_${selectedDesign.pareto_id}.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  // Export current city Pareto set as CSV
  const exportCityParetoCsv = () => {
    const headers = [
      "pareto_id",
      "city",
      "status",
      "O1_ml_discomfort_pct",
      "O1_adapt_pct",
      "O2_hvac_energy_kwh_m2_yr",
      "roof_insulation_mm",
      "wall_insulation_mm",
      "wall_mass_class",
      "roof_solar_absorptance",
      "glazing_wwr_pct",
      "orientation_deg",
      "shading_depth_m",
      "ventilation_ach",
      "verified_O1_ml_pct",
      "verified_O2_kwh_m2_yr",
      "O1_error_pp",
      "O2_error_pct"
    ];

    const rows = displayDesigns.map((d) => [
      d.pareto_id,
      d.city,
      d.is_verified ? "Verified" : "Pareto",
      d.O1_ml.toFixed(2),
      d.O1_adapt.toFixed(2),
      d.O2.toFixed(2),
      Math.round(d.roof_insulation_thickness * 1000),
      Math.round(d.wall_insulation_thickness * 1000),
      d.wall_mass_class,
      d.roof_solar_absorptance.toFixed(2),
      Math.round(d.wwr <= 1 ? d.wwr * 100 : d.wwr),
      Math.round(d.orientation),
      d.shading_depth.toFixed(2),
      d.ventilation_ach.toFixed(1),
      d.verified_O1_ml != null ? d.verified_O1_ml.toFixed(2) : "",
      d.verified_O2 != null ? d.verified_O2.toFixed(2) : "",
      d.verified_O1_ml != null ? (d.verified_O1_ml - d.O1_ml).toFixed(2) : "",
      d.verified_O2 != null && d.O2
        ? (((d.verified_O2 - d.O2) / d.O2) * 100).toFixed(1)
        : ""
    ]);

    const csvContent = [headers.join(","), ...rows.map((r) => r.join(","))].join("\n");
    const blob = new Blob([csvContent], { type: "text/csv;charset=utf-8;" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `ClimateAdapt_Pareto_${selectedCity}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="space-y-8 pb-16">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-[var(--line)] pb-4">
        <div>
          <div className="flex items-center space-x-2">
            <h1 className="text-3xl font-semibold text-[var(--ink)] tracking-tight flex items-center space-x-3">
              <Layers className="w-7 h-7 text-[var(--primary)]" />
              <span>Multi-Objective Pareto Explorer</span>
            </h1>
            <Badge variant="primary">Flagship</Badge>
          </div>
          <p className="text-sm text-[var(--ink-2)] mt-1 max-w-2xl">
            Non-dominated shelter designs derived by NSGA-II optimization (Pop=100, Gen=200, seed 42) minimizing occupant discomfort hours and annual HVAC energy.
          </p>
        </div>

        {/* City Picker */}
        <div className="flex items-center space-x-3 bg-[var(--surface-2)] border border-[var(--line)] p-2 rounded-[8px]">
          <span className="text-xs text-[var(--ink-2)]">Target station:</span>
          <select
            aria-label="Target climate station"
            value={selectedCity}
            onChange={(e) => {
              setSelectedCity(e.target.value as CityKey);
              setSelectedDesignId(null);
            }}
            className="bg-[var(--surface)] text-[var(--ink)] font-medium text-xs py-1.5 px-3 rounded-[6px] border border-[var(--line)] focus:outline-none focus:ring-2 focus:ring-[var(--primary)]"
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
      <div className="flex flex-wrap items-center justify-between gap-3 p-4 rounded-[8px] bg-[var(--surface-2)] border border-[var(--line)]">
        <div className="flex items-center space-x-2">
          <Sparkles className="w-4 h-4 text-[var(--primary)]" />
          <span className="text-xs font-semibold text-[var(--ink)]">
            Recommend for me:
          </span>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <button
            onClick={() => applyPreset("lowest_discomfort")}
            className="px-3.5 py-1.5 rounded-[6px] text-xs font-medium bg-[var(--surface)] hover:bg-[var(--surface-2)] text-[var(--ink)] border border-[var(--line)] transition flex items-center space-x-1.5 shadow-sm"
          >
            <TrendingDown className="w-3.5 h-3.5 text-[var(--hot)]" />
            <span>Lowest discomfort hours</span>
          </button>
          <button
            onClick={() => applyPreset("lowest_energy")}
            className="px-3.5 py-1.5 rounded-[6px] text-xs font-medium bg-[var(--surface)] hover:bg-[var(--surface-2)] text-[var(--ink)] border border-[var(--line)] transition flex items-center space-x-1.5 shadow-sm"
          >
            <TrendingDown className="w-3.5 h-3.5 text-[var(--warn)]" />
            <span>Lowest HVAC energy</span>
          </button>
          <div className="flex items-center">
            <button
              onClick={() => applyPreset("knee")}
              className="px-3.5 py-1.5 rounded-l-[6px] text-xs font-medium bg-[var(--surface)] hover:bg-[var(--surface-2)] text-[var(--ink)] border border-[var(--line)] border-r-0 transition flex items-center space-x-1.5 shadow-sm"
            >
              <Award className="w-3.5 h-3.5 text-[var(--primary)]" />
              <span>Balanced (Knee point design)</span>
            </button>
            <span
              className="px-2 py-1.5 bg-[var(--surface)] border border-[var(--line)] rounded-r-[6px] text-[var(--ink-2)] hover:text-[var(--ink)] cursor-help flex items-center"
              title="Knee point: The balanced design closest to the ideal minimum in normalized multi-objective space, providing the best trade-off where marginal comfort gain equals marginal energy expenditure."
            >
              <Info className="w-3.5 h-3.5" />
            </span>
          </div>
        </div>

        {/* View toggles & table / CSV buttons */}
        <div className="flex items-center space-x-2 text-xs">
          <label className="flex items-center space-x-1.5 cursor-pointer text-[var(--ink)] select-none">
            <input
              type="checkbox"
              checked={filterVerifiedOnly}
              onChange={(e) => {
                const checked = e.target.checked;
                setFilterVerifiedOnly(checked);
                if (checked && selectedDesign && !selectedDesign.is_verified) {
                  const firstVerified = allDesigns.find((d) => d.is_verified);
                  if (firstVerified) setSelectedDesignId(firstVerified.pareto_id);
                }
              }}
              className="accent-[var(--primary)] rounded"
            />
            <span>EnergyPlus verified only ({verifiedDesigns.length})</span>
          </label>
          <button
            onClick={() => setShowTable(!showTable)}
            className="px-2.5 py-1.5 rounded-[6px] bg-[var(--surface)] border border-[var(--line)] text-[var(--ink)] hover:bg-[var(--surface-2)] transition ml-2 flex items-center space-x-1.5"
            title="Toggle data table"
          >
            <TableIcon className="w-3.5 h-3.5" />
            <span>{showTable ? "Hide table" : "Show as table"}</span>
          </button>
          <button
            onClick={exportCityParetoCsv}
            className="px-2.5 py-1.5 rounded-[6px] bg-[var(--surface)] border border-[var(--line)] text-[var(--ink)] hover:bg-[var(--surface-2)] transition flex items-center space-x-1.5"
            title="Download all Pareto designs as CSV"
          >
            <FileSpreadsheet className="w-3.5 h-3.5" />
            <span>Download CSV</span>
          </button>
        </div>
      </div>

      {/* Main Section: Scatter Chart + Selected Design Inspector */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
        {/* Pareto Scatter Chart */}
        <div className="lg:col-span-8 min-w-0 rounded-[8px] border border-[var(--line)] bg-[var(--surface)] p-6 space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-base font-semibold text-[var(--ink)] flex items-center space-x-2">
                <span>Pareto trade-off frontier: Discomfort vs energy</span>
              </h2>
              <p className="text-xs text-[var(--ink-2)] mt-0.5">
                Click any point or use arrow keys to inspect full envelope variables and verification error.
              </p>
            </div>
            <div className="flex items-center space-x-3 text-xs tabular-nums">
              <span className="flex items-center space-x-1.5 text-[var(--ink-2)]">
                <span className="w-2.5 h-2.5 rounded-full bg-[var(--link)] inline-block" />
                <span>All Pareto ({allDesigns.length})</span>
              </span>
              <span className="flex items-center space-x-1.5 text-[var(--warn)] font-medium">
                <Star className="w-3.5 h-3.5 fill-[var(--warn)] text-[var(--warn)]" />
                <span>Verified ({verifiedDesigns.length})</span>
              </span>
            </div>
          </div>

          {/* Full Card Chart Container (min-h-[420px], height 460px) with keyboard arrow navigation */}
          <div
            tabIndex={0}
            role="region"
            aria-label="Pareto trade-off scatter plot. Use left and right arrow keys to navigate between designs."
            onKeyDown={handleChartKeyDown}
            className="w-full h-[460px] min-h-[420px] focus:outline-none focus:ring-1 focus:ring-[var(--primary)] rounded-[6px]"
          >
            <ResponsiveContainer width="100%" height="100%">
              <ScatterChart margin={{ top: 20, right: 30, bottom: 50, left: 30 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="var(--line)" strokeOpacity={0.4} />
                <XAxis
                  type="number"
                  dataKey="O1_ml"
                  name="Hours uncomfortable"
                  unit="%"
                  stroke="var(--ink-2)"
                  fontSize={12}
                  domain={["auto", "auto"]}
                  tick={{ fill: "var(--ink-2)", fontSize: 11 }}
                  label={{
                    value: "Hours uncomfortable (%)",
                    position: "insideBottom",
                    offset: -12,
                    fill: "var(--ink)",
                    fontSize: 13,
                    fontWeight: 600
                  }}
                />
                <YAxis
                  type="number"
                  dataKey="O2"
                  name="Heating & cooling energy"
                  unit=" kWh/m²/yr"
                  stroke="var(--ink-2)"
                  fontSize={12}
                  domain={["auto", "auto"]}
                  tick={{ fill: "var(--ink-2)", fontSize: 11 }}
                  label={{
                    value: "Heating & cooling energy (kWh/m²/yr)",
                    angle: -90,
                    position: "insideLeft",
                    offset: -10,
                    fill: "var(--ink)",
                    fontSize: 13,
                    fontWeight: 600
                  }}
                />
                <ZAxis range={[50, 180]} />
                <Tooltip
                  cursor={{ strokeDasharray: "3 3" }}
                  content={({ active, payload }) => {
                    if (active && payload && payload.length) {
                      const data = payload[0].payload as ParetoDesign;
                      return (
                        <div className="p-3 rounded-[8px] bg-[var(--surface)] border border-[var(--line)] shadow-md text-xs space-y-1.5 tabular-nums">
                          <div className="font-semibold text-[var(--ink)] flex items-center justify-between gap-3">
                            <code>{data.pareto_id}</code>
                            {data.is_verified ? (
                              <span className="text-[var(--warn)] font-medium flex items-center space-x-1">
                                <Star className="w-3 h-3 fill-[var(--warn)]" />
                                <span>Verified</span>
                              </span>
                            ) : (
                              <span className="text-[var(--ink-2)]">Pareto</span>
                            )}
                          </div>
                          <div className="text-[var(--hot)]">
                            Discomfort O1: {formatDiscomfortPct(data.O1_ml)}
                          </div>
                          <div className="text-[var(--ink)]">
                            HVAC Energy O2: {formatEnergyValue(data.O2)}
                          </div>
                          <div className="text-[var(--ink-2)]">
                            Adaptive 90%: {formatDiscomfortPct(data.O1_adapt)}
                          </div>
                          <div className="text-[11px] text-[var(--primary)] pt-1 border-t border-[var(--line)]">
                            Click or arrow to inspect envelope
                          </div>
                        </div>
                      );
                    }
                    return null;
                  }}
                />

                {/* Pareto scatter dots rendered with custom shape (star for verified, circle for others, ring for selected) */}
                <Scatter
                  name="Pareto Designs"
                  data={displayDesigns}
                  shape={
                    <CustomScatterDot
                      selectedId={selectedDesign?.pareto_id}
                      onSelect={setSelectedDesignId}
                    />
                  }
                  onClick={(entry: any) => {
                    const id = entry?.pareto_id || entry?.payload?.pareto_id;
                    if (id) setSelectedDesignId(id);
                  }}
                />

                {/* Reference Shelter R1 Lightweight Dot */}
                {r1 && (
                  <ReferenceDot
                    x={r1.O1_ml}
                    y={r1.O2}
                    r={7}
                    fill="var(--bad)"
                    stroke="var(--surface)"
                    strokeWidth={2}
                    label={{
                      value: "R1 Lightweight",
                      position: "top",
                      fill: "var(--bad)",
                      fontSize: 12,
                      fontWeight: 500
                    }}
                  />
                )}

                {/* Reference Shelter R2 Conventional Dot */}
                {r2 && (
                  <ReferenceDot
                    x={r2.O1_ml}
                    y={r2.O2}
                    r={7}
                    fill="var(--warn)"
                    stroke="var(--surface)"
                    strokeWidth={2}
                    label={{
                      value: "R2 Conventional",
                      position: "top",
                      fill: "var(--warn)",
                      fontSize: 12,
                      fontWeight: 500
                    }}
                  />
                )}
              </ScatterChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Selected Design Card & Verification Inspector */}
        <div className="lg:col-span-4 min-w-0 space-y-4" ref={inspectorRef}>
          <div className="rounded-[8px] border border-[var(--line)] bg-[var(--surface)] p-6 space-y-4 shadow-sm">
            <div className="flex flex-wrap items-center justify-between gap-2 border-b border-[var(--line)] pb-3">
              <div>
                <span className="text-xs font-semibold text-[var(--primary)] block uppercase tracking-wider">
                  Design inspector
                </span>
                <h2 className="text-lg font-semibold text-[var(--ink)] flex items-center space-x-2">
                  <code>{selectedDesign?.pareto_id || "Design"}</code>
                  {selectedDesign?.is_verified && (
                    <Badge variant="warn">★ Verified</Badge>
                  )}
                </h2>
              </div>

              <button
                onClick={exportSelectedDesignJson}
                className="px-2.5 py-1.5 rounded-[6px] bg-[var(--surface-2)] border border-[var(--line)] text-[var(--ink)] hover:bg-[var(--surface)] transition flex items-center space-x-1.5 text-xs font-medium"
                title="Download design JSON"
              >
                <Download className="w-3.5 h-3.5" />
                <span>Download design (JSON)</span>
              </button>
            </div>

            {/* Objective Metrics */}
            <div className="grid grid-cols-2 gap-2 text-xs tabular-nums">
              <div className="p-3 rounded-[8px] bg-[var(--surface-2)] border border-[var(--line)]">
                <span className="text-[var(--ink-2)] block text-[11px]">Hours uncomfortable</span>
                <span className="text-xl font-semibold text-[var(--hot)]">
                  {formatDiscomfortPct(selectedDesign?.O1_ml)}
                </span>
                <span className="text-[11px] text-[var(--ink-2)] block">ML comfort model</span>
              </div>

              <div className="p-3 rounded-[8px] bg-[var(--surface-2)] border border-[var(--line)]">
                <span className="text-[var(--ink-2)] block text-[11px]">Heating & cooling energy</span>
                <span className="text-xl font-semibold text-[var(--ink)]">
                  {selectedDesign?.O2 != null ? selectedDesign.O2.toFixed(1) : "—"}
                </span>
                <span className="text-[11px] text-[var(--ink-2)] block">kWh/m²/yr</span>
              </div>
            </div>

            {/* Baseline Reference Deltas */}
            {selectedDesign && r1 && r2 && (
              <div className="p-3 rounded-[8px] bg-[var(--surface-2)] border border-[var(--line)] text-xs tabular-nums space-y-1.5">
                <div className="text-[11px] text-[var(--ink-2)] font-semibold">Reference baselines</div>
                <div className="flex justify-between items-center text-[12px]">
                  <span className="text-[var(--ink-2)]">vs R1 Lightweight:</span>
                  <span className="text-[var(--good)] font-semibold">
                    {formatPercentagePoints(selectedDesign.O1_ml - r1.O1_ml)} | {formatEnergyDelta(selectedDesign.O2 - r1.O2)}
                  </span>
                </div>
                <div className="flex justify-between items-center text-[12px]">
                  <span className="text-[var(--ink-2)]">vs R2 Conventional:</span>
                  <span className="text-[var(--good)] font-semibold">
                    {formatPercentagePoints(selectedDesign.O1_ml - r2.O1_ml)} | {formatEnergyDelta(selectedDesign.O2 - r2.O2)}
                  </span>
                </div>
              </div>
            )}

            {/* Direct Simulation Verification Error or Not Verified Fallback */}
            {selectedDesign?.is_verified ? (
              <div className="p-3 rounded-[8px] bg-[var(--surface-2)] border border-[var(--line)] space-y-2 text-xs tabular-nums">
                <div className="flex items-center justify-between text-[var(--primary)] font-semibold">
                  <span className="flex items-center space-x-1">
                    <Star className="w-3.5 h-3.5 fill-[var(--warn)] text-[var(--warn)]" />
                    <span>EnergyPlus ground truth</span>
                  </span>
                  <span className="text-[11px] bg-[var(--surface)] px-1.5 py-0.5 rounded border border-[var(--line)]">
                    Direct simulation
                  </span>
                </div>
                <div className="grid grid-cols-2 gap-2 text-[12px]">
                  <div className="p-2 rounded bg-[var(--surface)] border border-[var(--line)]">
                    <span className="text-[var(--ink-2)] block text-[10px]">Verified O1 Discomfort</span>
                    <strong className="text-[var(--ink)] block text-sm">
                      {formatDiscomfortPct(selectedDesign.verified_O1_ml)}
                    </strong>
                    <span className="text-[11px] text-[var(--ink-2)]">
                      O1 error: <strong className="text-[var(--primary)]">{formatO1Error(selectedDesign.verified_O1_ml, selectedDesign.O1_ml)}</strong>
                    </span>
                  </div>
                  <div className="p-2 rounded bg-[var(--surface)] border border-[var(--line)]">
                    <span className="text-[var(--ink-2)] block text-[10px]">Verified O2 Energy</span>
                    <strong className="text-[var(--ink)] block text-sm">
                      {formatEnergyValue(selectedDesign.verified_O2)}
                    </strong>
                    <span className="text-[11px] text-[var(--ink-2)]">
                      O2 error: <strong className="text-[var(--primary)]">{formatO2Error(selectedDesign.verified_O2, selectedDesign.O2)}</strong>
                    </span>
                  </div>
                </div>
              </div>
            ) : (
              <div className="p-3 rounded-[8px] bg-[var(--surface-2)] border border-[var(--line)] space-y-1 text-xs tabular-nums">
                <div className="flex items-center justify-between text-[var(--ink)] font-semibold">
                  <span>Physical verification:</span>
                  <span className="text-[var(--ink-2)] font-normal">Not verified</span>
                </div>
                <p className="text-[11px] text-[var(--ink-2)] leading-relaxed">
                  Surrogate estimation. 10 designs per climate zone undergo full-physics EnergyPlus re-simulation.
                </p>
              </div>
            )}

            {/* Envelope Variables Listing with Central Formatter */}
            <div className="space-y-2 pt-2 border-t border-[var(--line)] text-xs tabular-nums">
              <div className="flex justify-between">
                <span className="text-[var(--ink-2)]">Roof insulation:</span>
                <span className="text-[var(--ink)] font-semibold">
                  {formatInsulationMm(selectedDesign?.roof_insulation_thickness)}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-[var(--ink-2)]">Wall insulation:</span>
                <span className="text-[var(--ink)] font-semibold">
                  {formatInsulationMm(selectedDesign?.wall_insulation_thickness)}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-[var(--ink-2)]">Wall mass class:</span>
                <span className="text-[var(--ink)] font-semibold">
                  {formatWallMassClass(selectedDesign?.wall_mass_class)}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-[var(--ink-2)]">Roof solar absorptance:</span>
                <span className="text-[var(--ink)] font-semibold">
                  {formatSolarAbsorptance(selectedDesign?.roof_solar_absorptance)}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-[var(--ink-2)]">Glazing ratio (WWR):</span>
                <span className="text-[var(--ink)] font-semibold">
                  {formatGlazingPct(selectedDesign?.wwr)}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-[var(--ink-2)]">Azimuth orientation:</span>
                <span className="text-[var(--ink)] font-semibold">
                  {formatAzimuthWithCompass(selectedDesign?.orientation)}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-[var(--ink-2)]">Overhang shading depth:</span>
                <span className="text-[var(--ink)] font-semibold">
                  {formatOverhangM(selectedDesign?.shading_depth)}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-[var(--ink-2)]">Natural ventilation rate:</span>
                <span className="text-[var(--ink)] font-semibold">
                  {formatVentilationAch(selectedDesign?.ventilation_ach)}
                </span>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Accessible Data Table View */}
      {showTable && (
        <div className="rounded-[8px] bg-[var(--surface)] border border-[var(--line)] p-6 space-y-4">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
            <div>
              <h2 className="text-base font-semibold text-[var(--ink)]">
                Pareto designs data table ({selectedCity})
              </h2>
              <p className="text-xs text-[var(--ink-2)]">
                Showing {displayDesigns.length} non-dominated designs. Click any row to inspect in detail.
              </p>
            </div>
            <div className="flex items-center space-x-2">
              <button
                onClick={exportCityParetoCsv}
                className="px-2.5 py-1.5 rounded-[6px] bg-[var(--surface-2)] border border-[var(--line)] text-[var(--ink)] hover:bg-[var(--surface)] transition flex items-center space-x-1.5 text-xs font-medium"
              >
                <FileSpreadsheet className="w-3.5 h-3.5" />
                <span>Export CSV</span>
              </button>
            </div>
          </div>

          <div className="overflow-x-auto rounded-[8px] border border-[var(--line)]">
            <table
              className="w-full text-xs tabular-nums text-left divide-y divide-[var(--line)]"
              aria-label={`Pareto designs table for ${selectedCity}`}
            >
              <thead className="bg-[var(--surface-2)] text-[var(--ink-2)]">
                <tr>
                  <th scope="col" className="py-2.5 px-3 text-left">Design ID</th>
                  <th scope="col" className="py-2.5 px-3 text-left">Status</th>
                  <th scope="col" className="py-2.5 px-3 text-right">Hours Uncomfortable</th>
                  <th scope="col" className="py-2.5 px-3 text-right">Adaptive 90%</th>
                  <th scope="col" className="py-2.5 px-3 text-right">HVAC Energy</th>
                  <th scope="col" className="py-2.5 px-3 text-right">Roof Ins</th>
                  <th scope="col" className="py-2.5 px-3 text-right">Wall Ins</th>
                  <th scope="col" className="py-2.5 px-3 text-left">Mass</th>
                  <th scope="col" className="py-2.5 px-3 text-right">Absorptance</th>
                  <th scope="col" className="py-2.5 px-3 text-right">Glazing</th>
                  <th scope="col" className="py-2.5 px-3 text-right">Orientation</th>
                  <th scope="col" className="py-2.5 px-3 text-right">Overhang</th>
                  <th scope="col" className="py-2.5 px-3 text-right">Ventilation</th>
                  <th scope="col" className="py-2.5 px-3 text-right">O1 Error</th>
                  <th scope="col" className="py-2.5 px-3 text-right">O2 Error</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[var(--line)] text-[var(--ink)] bg-[var(--surface)]">
                {displayDesigns.map((d) => {
                  const isSelected = selectedDesign?.pareto_id === d.pareto_id;
                  return (
                    <tr
                      key={d.pareto_id}
                      onClick={() => setSelectedDesignId(d.pareto_id)}
                      className={`cursor-pointer transition hover:bg-[var(--surface-2)]/60 ${
                        isSelected ? "bg-[var(--surface-2)] font-semibold" : ""
                      }`}
                    >
                      <th scope="row" className="py-2 px-3 font-mono font-normal text-left">
                        {d.pareto_id}
                      </th>
                      <td className="py-2 px-3 text-left">
                        {d.is_verified ? (
                          <span className="text-[var(--warn)] font-semibold flex items-center space-x-1">
                            <Star className="w-3 h-3 fill-[var(--warn)]" />
                            <span>Verified</span>
                          </span>
                        ) : (
                          <span className="text-[var(--ink-2)]">Pareto</span>
                        )}
                      </td>
                      <td className="py-2 px-3 text-right text-[var(--hot)]">{formatDiscomfortPct(d.O1_ml)}</td>
                      <td className="py-2 px-3 text-right">{formatDiscomfortPct(d.O1_adapt)}</td>
                      <td className="py-2 px-3 text-right">{formatEnergyValue(d.O2)}</td>
                      <td className="py-2 px-3 text-right">{formatInsulationMm(d.roof_insulation_thickness)}</td>
                      <td className="py-2 px-3 text-right">{formatInsulationMm(d.wall_insulation_thickness)}</td>
                      <td className="py-2 px-3 text-left">{formatWallMassClass(d.wall_mass_class)}</td>
                      <td className="py-2 px-3 text-right">{formatSolarAbsorptance(d.roof_solar_absorptance)}</td>
                      <td className="py-2 px-3 text-right">{formatGlazingPct(d.wwr)}</td>
                      <td className="py-2 px-3 text-right">{formatAzimuthWithCompass(d.orientation)}</td>
                      <td className="py-2 px-3 text-right">{formatOverhangM(d.shading_depth)}</td>
                      <td className="py-2 px-3 text-right">{formatVentilationAch(d.ventilation_ach)}</td>
                      <td className="py-2 px-3 text-right">
                        {formatO1Error(d.verified_O1_ml, d.O1_ml)}
                      </td>
                      <td className="py-2 px-3 text-right">
                        {formatO2Error(d.verified_O2, d.O2)}
                      </td>
                    </tr>
                  );
                })}
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
    <Suspense fallback={<div className="py-20 text-center text-[var(--ink-2)] text-sm">Loading Multi-Objective Pareto Explorer...</div>}>
      <ParetoExplorerContent />
    </Suspense>
  );
}
