"use client";

import React, { useState, useMemo } from "react";
import { getSurrogateMetrics } from "@/lib/data";
import { CITIES_DATA } from "@/lib/constants";
import { CityKey } from "@/types";
import { Badge } from "@/components/ui/Badge";
import {
  Activity,
  Award,
  FileText,
  Info,
  AlertTriangle,
  ArrowUpDown,
  ArrowUp,
  ArrowDown
} from "lucide-react";

type SortKey = "name" | "type" | "cvF1" | "holdoutF1" | "ci" | "status";

export default function ModelLabPage() {
  const surrMetrics = getSurrogateMetrics();
  const [activeTab, setActiveTab] = useState<"leaderboard" | "surrogates" | "phases">("leaderboard");

  // Sorting state for leaderboard
  const [sortKey, setSortKey] = useState<SortKey>("holdoutF1");
  const [sortDir, setSortDir] = useState<"asc" | "desc">("desc");

  // Leaderboard data with CI formatted as "0.XXXX–0.YYYY"
  const rawModels = [
    { name: "Adaptive 90% (ASHRAE 55)", type: "Physical Baseline", cvF1: 0.4397, holdoutF1: 0.4939, ci: "0.4907–0.4971", status: "Best Baseline" },
    { name: "Adaptive 80% (ASHRAE 55)", type: "Physical Baseline", cvF1: 0.3900, holdoutF1: 0.4899, ci: "0.4868–0.4931", status: "Baseline" },
    { name: "Ablation A3 (Outdoor Temp)", type: "ML Champion (XGBoost)", cvF1: 0.4733, holdoutF1: 0.4785, ci: "0.4754–0.4816", status: "ML Champion" },
    { name: "Ablation A2 (Cooling Type)", type: "ML Model (XGBoost)", cvF1: 0.4724, holdoutF1: 0.4706, ci: "0.4674–0.4737", status: "Ablation" },
    { name: "Ablation A1 (Without Tr)", type: "ML Model (XGBoost)", cvF1: 0.4648, holdoutF1: 0.4700, ci: "0.4665–0.4729", status: "Ablation" },
    { name: "IMAC NV 90% (Indian Standard)", type: "Physical Baseline", cvF1: 0.4312, holdoutF1: 0.4775, ci: "0.4742–0.4807", status: "Baseline" },
    { name: "IMAC MM 90% (Mixed-Mode)", type: "Physical Baseline", cvF1: 0.3941, holdoutF1: 0.4820, ci: "0.4788–0.4853", status: "Baseline" },
    { name: "PMV / PPD (Fanger Model)", type: "Physical Baseline", cvF1: 0.4332, holdoutF1: 0.4681, ci: "0.4645–0.4716", status: "Baseline" },
    { name: "XGBoost Complete-Case", type: "ML Model (XGBoost)", cvF1: 0.4712, holdoutF1: 0.4685, ci: "0.4653–0.4717", status: "ML Baseline" },
    { name: "Random Forest Classifier", type: "ML Model (Scikit-Learn)", cvF1: 0.4610, holdoutF1: 0.4636, ci: "0.4604–0.4668", status: "ML Baseline" },
    { name: "Multi-Layer Perceptron (MLP)", type: "ML Model (Neural Net)", cvF1: 0.4520, holdoutF1: 0.4571, ci: "0.4538–0.4603", status: "ML Baseline" },
    { name: "Multinomial Logistic Regression", type: "Linear Model", cvF1: 0.4215, holdoutF1: 0.4474, ci: "0.4442–0.4506", status: "ML Baseline" }
  ];

  const handleSort = (key: SortKey) => {
    if (sortKey === key) {
      setSortDir(sortDir === "asc" ? "desc" : "asc");
    } else {
      setSortKey(key);
      setSortDir(key === "cvF1" || key === "holdoutF1" ? "desc" : "asc");
    }
  };

  const sortedModels = useMemo(() => {
    return [...rawModels].sort((a, b) => {
      let cmp = 0;
      if (sortKey === "cvF1" || sortKey === "holdoutF1") {
        cmp = a[sortKey] - b[sortKey];
      } else {
        cmp = a[sortKey].localeCompare(b[sortKey]);
      }
      return sortDir === "asc" ? cmp : -cmp;
    });
  }, [rawModels, sortKey, sortDir]);

  // 5 Cities x 5 Targets Matrix
  const cities: CityKey[] = ["Jodhpur", "Mumbai", "New_Delhi", "Bengaluru", "Shimla"];
  const targets = ["O1_ml", "warm_ml", "cool_ml", "O1_adapt", "O2"] as const;

  const targetLabels: Record<string, string> = {
    O1_ml: "O1 ML Discomfort (%)",
    warm_ml: "Warm ML (%)",
    cool_ml: "Cool ML (%)",
    O1_adapt: "O1 Adapt Discomfort (%)",
    O2: "O2 HVAC Energy (kWh/m²)"
  };

  const getMetric = (city: CityKey, target: string) => {
    return surrMetrics.find((m) => m.city === city && m.target === target);
  };

  // Evidence log milestones timeline without "Phase N"
  const milestones = [
    { title: "Data Audit & Integrity", status: "DONE", evidence: "E-001..E-003", details: "109,033 DB II rows verified. 1,760 Indian EPW files indexed. EnergyPlus smoke test passed." },
    { title: "EDA & Baseline Recalculation", status: "DONE", evidence: "E-004..E-007", details: "3-class TSV balance audited. Imputation of radiant temperature strictly banned (D-005)." },
    { title: "Clean Data & Comfort Models", status: "DONE", evidence: "E-008..E-015", details: "58,512 complete cases isolated. S1 evaluated as FAIL (-0.0154 margin vs Adaptive 90%). ML Champion serialized." },
    { title: "Batch Simulation Engine", status: "DONE", evidence: "E-016..E-017", details: "10,000 EnergyPlus runs dispatched across 5 cities with 99.88% completion (9,988 successful runs)." },
    { title: "Coupling & XGBoost Surrogates", status: "DONE", evidence: "E-018..E-019", details: "43.69M hourly series scored by dual judges. 25 surrogates tuned with Optuna; S2 PARTIAL (23/25 pass)." },
    { title: "NSGA-II Multi-Objective Optimization", status: "DONE", evidence: "E-020", details: "500 Pareto designs derived. 50 verified in EnergyPlus. S3 PASS confirmed across all 5 climate zones." },
    { title: "TreeExplainer SHAP & Dashboard", status: "DONE", evidence: "E-021", details: "Global SHAP attributions and 5-page decision-support app built; AppTest automated test passed." },
    { title: "Packaging & Claims Audit", status: "DONE (FROZEN)", evidence: "E-022..E-024", details: "100% claims verified against literal evidence logs. Released as frozen benchmark v1.1.3." }
  ];

  const renderSortIcon = (key: SortKey) => {
    if (sortKey !== key) {
      return <ArrowUpDown className="w-3.5 h-3.5 text-[var(--ink-2)]/60 shrink-0" />;
    }
    return sortDir === "asc" ? (
      <ArrowUp className="w-3.5 h-3.5 text-[var(--primary)] shrink-0" />
    ) : (
      <ArrowDown className="w-3.5 h-3.5 text-[var(--primary)] shrink-0" />
    );
  };

  return (
    <div className="space-y-6 pb-16">
      {/* Header */}
      <div className="border-b border-[var(--line)] pb-4">
        <h1 className="text-3xl font-semibold text-[var(--ink)] tracking-tight flex items-center space-x-3">
          <Activity className="w-7 h-7 text-[var(--primary)]" />
          <span>Model Lab & Benchmark Registry</span>
        </h1>
        <p className="text-sm text-[var(--ink-2)] mt-1 max-w-2xl">
          Empirical classification benchmarks, XGBoost surrogate response surfaces, and literal verification evidence.
        </p>
      </div>

      {/* Tabs */}
      <div className="flex items-center space-x-1 p-1 bg-[var(--surface-2)] border border-[var(--line)] rounded-[8px]">
        <button
          onClick={() => setActiveTab("leaderboard")}
          className={`py-2 px-4 rounded-[6px] font-medium text-xs transition ${
            activeTab === "leaderboard"
              ? "bg-[var(--surface)] text-[var(--ink)] font-semibold shadow-sm border border-[var(--line)]"
              : "text-[var(--ink-2)] hover:text-[var(--ink)]"
          }`}
        >
          Comfort models
        </button>
        <button
          onClick={() => setActiveTab("surrogates")}
          className={`py-2 px-4 rounded-[6px] font-medium text-xs transition ${
            activeTab === "surrogates"
              ? "bg-[var(--surface)] text-[var(--ink)] font-semibold shadow-sm border border-[var(--line)]"
              : "text-[var(--ink-2)] hover:text-[var(--ink)]"
          }`}
        >
          Fast estimators (25)
        </button>
        <button
          onClick={() => setActiveTab("phases")}
          className={`py-2 px-4 rounded-[6px] font-medium text-xs transition ${
            activeTab === "phases"
              ? "bg-[var(--surface)] text-[var(--ink)] font-semibold shadow-sm border border-[var(--line)]"
              : "text-[var(--ink-2)] hover:text-[var(--ink)]"
          }`}
        >
          Evidence log
        </button>
      </div>

      {/* TAB 1: Comfort Model Leaderboard */}
      {activeTab === "leaderboard" && (
        <div className="rounded-[8px] border border-[var(--line)] bg-[var(--surface)] p-6 space-y-4">
          <div className="flex flex-col sm:flex-row sm:items-baseline justify-between gap-2">
            <div>
              <h3 className="text-lg font-semibold text-[var(--ink)]">
                Comfort sensation models evaluated on identical complete cases (58,512 rows)
              </h3>
              <p className="text-xs text-[var(--ink-2)] mt-0.5">
                Evaluation under Leave-One-Köppen-Group-Out (LOGO) cross-validation with 95% bootstrap confidence intervals.
              </p>
            </div>
          </div>

          {/* Plain statement above table */}
          <div className="p-4 rounded-[var(--radius)] bg-[var(--surface-2)] border border-[var(--line)] text-[13px] text-[var(--ink)] flex items-start space-x-2.5">
            <Info className="w-4 h-4 text-[var(--primary)] shrink-0 mt-0.5" />
            <p className="font-medium leading-relaxed">
              The best ML model scored 0.0154 lower than the adaptive baseline, so it is not claimed to be better.
            </p>
          </div>

          <div className="overflow-x-auto rounded-[var(--radius)] border border-[var(--line)]">
            <table className="w-full text-xs tabular-nums text-left divide-y divide-[var(--line)] border-collapse">
              <thead>
                <tr className="bg-[var(--surface-2)] text-[var(--ink-2)] sticky top-16 z-10 shadow-sm border-b border-[var(--line)]">
                  <th
                    onClick={() => handleSort("name")}
                    className="py-3 px-4 text-left cursor-pointer hover:text-[var(--ink)] select-none bg-[var(--surface-2)]"
                  >
                    <div className="flex items-center space-x-1.5">
                      <span>Model name</span>
                      {renderSortIcon("name")}
                    </div>
                  </th>
                  <th
                    onClick={() => handleSort("type")}
                    className="py-3 px-4 text-left cursor-pointer hover:text-[var(--ink)] select-none bg-[var(--surface-2)]"
                  >
                    <div className="flex items-center space-x-1.5">
                      <span>Type</span>
                      {renderSortIcon("type")}
                    </div>
                  </th>
                  <th
                    onClick={() => handleSort("cvF1")}
                    className="py-3 px-4 text-right cursor-pointer hover:text-[var(--ink)] select-none bg-[var(--surface-2)]"
                  >
                    <div className="flex items-center justify-end space-x-1.5">
                      <span>CV Macro-F1</span>
                      {renderSortIcon("cvF1")}
                    </div>
                  </th>
                  <th
                    onClick={() => handleSort("holdoutF1")}
                    className="py-3 px-4 text-right cursor-pointer hover:text-[var(--ink)] select-none bg-[var(--surface-2)]"
                  >
                    <div className="flex items-center justify-end space-x-1.5">
                      <span>Holdout Macro-F1</span>
                      {renderSortIcon("holdoutF1")}
                    </div>
                  </th>
                  <th
                    onClick={() => handleSort("ci")}
                    className="py-3 px-4 text-right cursor-pointer hover:text-[var(--ink)] select-none bg-[var(--surface-2)]"
                  >
                    <div className="flex items-center justify-end space-x-1.5">
                      <span>95% Bootstrap CI</span>
                      {renderSortIcon("ci")}
                    </div>
                  </th>
                  <th
                    onClick={() => handleSort("status")}
                    className="py-3 px-4 text-left cursor-pointer hover:text-[var(--ink)] select-none min-w-[140px] whitespace-nowrap bg-[var(--surface-2)]"
                  >
                    <div className="flex items-center space-x-1.5">
                      <span>Status</span>
                      {renderSortIcon("status")}
                    </div>
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[var(--line)] text-[var(--ink)] bg-[var(--surface)]">
                {sortedModels.map((m, idx) => (
                  <tr
                    key={idx}
                    className={`transition hover:bg-[var(--surface-2)]/60 ${
                      m.status === "Best Baseline"
                        ? "font-semibold bg-[var(--surface-2)]/30"
                        : m.status === "ML Champion"
                        ? "font-semibold"
                        : ""
                    }`}
                  >
                    <td className="py-3 px-4">
                      <div className="flex items-center space-x-2">
                        {m.status === "Best Baseline" && <Award className="w-4 h-4 text-[var(--warn)] shrink-0" />}
                        {m.status === "ML Champion" && <Award className="w-4 h-4 text-[var(--primary)] shrink-0" />}
                        <span>{m.name}</span>
                      </div>
                    </td>
                    <td className="py-3 px-4 text-[var(--ink-2)]">{m.type}</td>
                    <td className="py-3 px-4 text-right tabular-nums">{m.cvF1.toFixed(4)}</td>
                    <td className="py-3 px-4 text-right tabular-nums font-semibold">{m.holdoutF1.toFixed(4)}</td>
                    <td className="py-3 px-4 text-right tabular-nums text-[var(--ink-2)]">{m.ci}</td>
                    <td className="py-3 px-4 min-w-[140px] whitespace-nowrap">
                      <span className="inline-block whitespace-nowrap px-2.5 py-0.5 rounded-[4px] text-[13px] bg-[var(--surface-2)] border border-[var(--line)] font-medium">
                        {m.status}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* TAB 2: Surrogate Accuracy Heatmap Matrix */}
      {activeTab === "surrogates" && (
        <div className="rounded-[8px] border border-[var(--line)] bg-[var(--surface)] p-6 space-y-4">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
            <div>
              <h3 className="text-lg font-semibold text-[var(--ink)]">
                25 XGBoost surrogate accuracy matrix (R² test scores)
              </h3>
              <p className="text-xs text-[var(--ink-2)] mt-0.5">
                Target: R² ≥ 0.95 on held-out test designs. S2 status: <strong>PARTIAL (23/25 PASS)</strong>. Mean O2 R² = 0.987.
              </p>
            </div>
            <div className="flex items-center space-x-2 text-xs shrink-0">
              <span className="inline-flex items-center space-x-1 px-2.5 py-1 rounded-[4px] bg-[var(--good)]/10 text-[var(--good)] border border-[var(--good)]/30 font-medium">
                <span>Passing: R² ≥ 0.95</span>
              </span>
              <span className="inline-flex items-center space-x-1 px-2.5 py-1 rounded-[4px] bg-amber-500/15 text-amber-800 dark:text-amber-200 border border-amber-500/40 font-medium">
                <AlertTriangle className="w-3.5 h-3.5 text-amber-600 dark:text-amber-400" />
                <span>Failing: R² &lt; 0.95</span>
              </span>
            </div>
          </div>

          <div className="overflow-x-auto rounded-[var(--radius)] border border-[var(--line)]">
            <table className="w-full text-xs tabular-nums text-left divide-y divide-[var(--line)] border-collapse">
              <thead>
                <tr className="bg-[var(--surface-2)] text-[var(--ink-2)] sticky top-16 z-10 shadow-sm border-b border-[var(--line)]">
                  <th className="py-3 px-4 text-left bg-[var(--surface-2)]">Climate zone station</th>
                  {targets.map((t) => (
                    <th key={t} className="py-3 px-4 text-right bg-[var(--surface-2)]">{targetLabels[t]}</th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-[var(--line)] text-[var(--ink)] bg-[var(--surface)]">
                {cities.map((city) => (
                  <tr key={city} className="hover:bg-[var(--surface-2)]/60 transition">
                    <td className="py-3 px-4 text-left font-semibold">
                      <div className="flex items-center space-x-2">
                        <span>{CITIES_DATA[city].name}</span>
                        <span className="text-[13px] text-[var(--ink-2)] font-normal">({CITIES_DATA[city].climateCode})</span>
                      </div>
                    </td>
                    {targets.map((t) => {
                      const m = getMetric(city, t);
                      const r2 = m?.r2 ?? 0;
                      const passes = r2 >= 0.95;

                      if (!passes) {
                        return (
                          <td key={t} className="py-3 px-4 text-right">
                            <span
                              className="inline-flex items-center space-x-1.5 px-2.5 py-1 rounded-[4px] font-semibold text-xs bg-amber-500/15 text-amber-900 dark:text-amber-200 border border-amber-500/40 shadow-sm"
                              title={`MAE: ${m?.mae?.toFixed(2) ?? '—'}, NMAE: ${m?.nmae_pct?.toFixed(1) ?? '—'}% (Below 0.95 threshold)`}
                            >
                              <AlertTriangle className="w-3.5 h-3.5 text-amber-600 dark:text-amber-400 shrink-0" />
                              <span>{r2.toFixed(4)}</span>
                              <span className="text-[10px] font-bold uppercase tracking-wider text-amber-700 dark:text-amber-300">Fail</span>
                            </span>
                          </td>
                        );
                      }

                      // Heatmap shading for passing cells
                      const isHighAccuracy = r2 >= 0.985;
                      return (
                        <td key={t} className="py-3 px-4 text-right">
                          <span
                            className={`inline-block px-2.5 py-1 rounded-[4px] font-semibold text-xs ${
                              isHighAccuracy
                                ? "bg-emerald-500/15 text-emerald-800 dark:text-emerald-300 border border-emerald-500/30"
                                : "bg-[var(--good)]/10 text-[var(--good)] border border-[var(--good)]/30"
                            }`}
                            title={`MAE: ${m?.mae?.toFixed(2) ?? '—'}, NMAE: ${m?.nmae_pct?.toFixed(1) ?? '—'}%`}
                          >
                            {r2.toFixed(4)}
                          </span>
                        </td>
                      );
                    })}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <div className="p-4 rounded-[var(--radius)] bg-[var(--surface-2)] border border-[var(--line)] text-xs text-[var(--ink-2)] flex items-start space-x-2.5">
            <Info className="w-4 h-4 text-[var(--warn)] shrink-0 mt-0.5" />
            <span className="text-[13px] leading-relaxed">
              <strong>Threshold rule: R² ≥ 0.95</strong>. The two targets falling marginally below the 0.95 threshold are highlighted above: <strong>Mumbai O1_ml (R² = 0.9406)</strong> and <strong>Shimla warm_ml (R² = 0.9225)</strong>. All 5 annual HVAC energy surrogates (O2) achieved high accuracy with mean R² = 0.987.
            </span>
          </div>
        </div>
      )}

      {/* TAB 3: Evidence Log without Phase N */}
      {activeTab === "phases" && (
        <div className="space-y-4">
          <div className="rounded-[8px] border border-[var(--line)] bg-[var(--surface)] p-6 space-y-4">
            <h3 className="text-lg font-semibold text-[var(--ink)] flex items-center space-x-2">
              <FileText className="w-5 h-5 text-[var(--primary)]" />
              <span>Project milestones & verification evidence log</span>
            </h3>
            <p className="text-xs text-[var(--ink-2)]">
              Strict evidence gating contract: zero claims without literal command execution logs in <code>reports/evidence/</code>.
            </p>

            <div className="divide-y divide-[var(--line)]">
              {milestones.map((m, idx) => (
                <div key={idx} className="py-4 flex flex-col md:flex-row md:items-center justify-between gap-2">
                  <div className="space-y-1">
                    <div className="flex items-center space-x-2">
                      <span className="font-semibold text-sm text-[var(--ink)]">{m.title}</span>
                      <Badge variant="good">
                        {m.status}
                      </Badge>
                    </div>
                    <p className="text-xs text-[var(--ink-2)]">{m.details}</p>
                  </div>

                  <div className="flex items-center space-x-2 text-xs text-[var(--ink-2)] shrink-0">
                    <FileText className="w-3.5 h-3.5 text-[var(--ink-2)]" />
                    <span>Evidence: <code className="text-[var(--ink)] font-medium">[{m.evidence}]</code></span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
