"use client";

import React, { useState } from "react";
import { getSurrogateMetrics, getModelsLeaderboard, getProjectMetadata } from "@/lib/data";
import { CITIES_DATA } from "@/lib/constants";
import { CityKey } from "@/types";
import { CriteriaScorecard } from "@/components/common/CriteriaScorecard";
import {
  Activity,
  Award,
  CheckCircle2,
  AlertCircle,
  XCircle,
  GitCommit,
  Layers,
  Cpu,
  BarChart2,
  FileText,
  Info
} from "lucide-react";

export default function ModelLabPage() {
  const meta = getProjectMetadata();
  const surrMetrics = getSurrogateMetrics();
  const leaderboardData = getModelsLeaderboard();
  const [activeTab, setActiveTab] = useState<"leaderboard" | "surrogates" | "phases">("leaderboard");


  // Leaderboard data from Phase 2 literal outputs
  const models = [
    { name: "Adaptive 90% (ASHRAE 55)", type: "Physical Baseline", cvF1: 0.4397, holdoutF1: 0.4939, ci: "[0.4907, 0.4971]", status: "Best Baseline" },
    { name: "Adaptive 80% (ASHRAE 55)", type: "Physical Baseline", cvF1: 0.3900, holdoutF1: 0.4899, ci: "[0.4868, 0.4931]", status: "Baseline" },
    { name: "Ablation A3 (Outdoor Temp)", type: "ML Champion (XGBoost)", cvF1: 0.4733, holdoutF1: 0.4785, ci: "[0.4754, 0.4816]", status: "ML Champion" },
    { name: "Ablation A2 (Cooling Type)", type: "ML Model (XGBoost)", cvF1: 0.4724, holdoutF1: 0.4706, ci: "[0.4674, 0.4737]", status: "Ablation" },
    { name: "Ablation A1 (Without Tr)", type: "ML Model (XGBoost)", cvF1: 0.4648, holdoutF1: 0.4700, ci: "[0.4665, 0.4729]", status: "Ablation" },
    { name: "IMAC NV 90% (Indian Standard)", type: "Physical Baseline", cvF1: 0.4312, holdoutF1: 0.4775, ci: "[0.4742, 0.4807]", status: "Baseline" },
    { name: "IMAC MM 90% (Mixed-Mode)", type: "Physical Baseline", cvF1: 0.3941, holdoutF1: 0.4820, ci: "[0.4788, 0.4853]", status: "Baseline" },
    { name: "PMV / PPD (Fanger Model)", type: "Physical Baseline", cvF1: 0.4332, holdoutF1: 0.4681, ci: "[0.4645, 0.4716]", status: "Baseline" },
    { name: "XGBoost Complete-Case", type: "ML Model (XGBoost)", cvF1: 0.4712, holdoutF1: 0.4685, ci: "[0.4653, 0.4717]", status: "ML Baseline" },
    { name: "Random Forest Classifier", type: "ML Model (Scikit-Learn)", cvF1: 0.4610, holdoutF1: 0.4636, ci: "[0.4604, 0.4668]", status: "ML Baseline" },
    { name: "Multi-Layer Perceptron (MLP)", type: "ML Model (Neural Net)", cvF1: 0.4520, holdoutF1: 0.4571, ci: "[0.4538, 0.4603]", status: "ML Baseline" },
    { name: "Multinomial Logistic Regression", type: "Linear Model", cvF1: 0.4215, holdoutF1: 0.4474, ci: "[0.4442, 0.4506]", status: "ML Baseline" }
  ];

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

  // Phase milestones timeline
  const phases = [
    { phase: "Phase 0", name: "Data Audit & Integrity", status: "DONE", evidence: "E-001..E-003", details: "109,033 DB II rows verified. 1,760 Indian EPW files indexed. EnergyPlus smoke test passed." },
    { phase: "Phase 1", name: "EDA & Baseline Recalculation", status: "DONE", evidence: "E-004..E-007", details: "3-class TSV balance audited. Imputation of radiant temperature strictly banned (D-005)." },
    { phase: "Phase 2", name: "Clean Data & Comfort Models", status: "DONE", evidence: "E-008..E-015", details: "58,512 complete cases isolated. S1 evaluated as FAIL (-0.0154 margin vs Adaptive 90%). ML Champion serialized." },
    { phase: "Phase 3", name: "Batch Simulation Engine", status: "DONE", evidence: "E-016..E-017", details: "10,000 EnergyPlus runs dispatched across 5 cities with 99.88% completion (9,988 successful runs)." },
    { phase: "Phase 4", name: "Coupling & XGBoost Surrogates", status: "DONE", evidence: "E-018..E-019", details: "43.69M hourly series scored by dual judges. 25 surrogates tuned with Optuna; S2 PARTIAL (23/25 pass)." },
    { phase: "Phase 5", name: "NSGA-II Multi-Objective Optimization", status: "DONE", evidence: "E-020", details: "500 Pareto designs derived. 50 verified in EnergyPlus. S3 PASS confirmed across all 5 climate zones." },
    { phase: "Phase 6", name: "TreeExplainer SHAP & Streamlit Dashboard", status: "DONE", evidence: "E-021", details: "Global SHAP attributions and 5-page decision-support app built; AppTest automated test passed." },
    { phase: "Phase 7", name: "Packaging & Claims Audit", status: "DONE (FROZEN)", evidence: "E-022..E-024", details: "100% claims verified against literal evidence logs. Released as frozen benchmark v1.1.3." }
  ];

  return (
    <div className="space-y-8 pb-16">
      {/* Header */}
      <div className="border-b border-slate-800 pb-4">
        <h1 className="text-3xl font-bold text-white tracking-tight flex items-center space-x-3">
          <Activity className="w-7 h-7 text-teal-400" />
          <span>Model Lab & Benchmark Registry</span>
        </h1>
        <p className="text-sm text-slate-300 mt-1 max-w-2xl">
          Scientific benchmark comparisons across physiological comfort models, surrogate regression accuracy matrices, and the complete audit timeline.
        </p>
      </div>

      {/* Success Criteria S1-S4 Audit Scorecard (S1 FAIL and S2 PARTIAL prominently disclosed) */}
      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <h2 className="text-sm font-bold text-white uppercase tracking-wider font-mono">
            Empirical Success Criteria Scorecard (S1–S4)
          </h2>
          <span className="text-[11px] font-mono text-slate-400">Fixed Seed: 42 | Phase 0–7 Audited</span>
        </div>
        <CriteriaScorecard criteria={meta.criteria} />
      </div>

      {/* Tabs */}
      <div className="flex items-center space-x-2 p-1.5 rounded-2xl glass-panel">
        <button
          onClick={() => setActiveTab("leaderboard")}
          className={`py-2 px-4 rounded-xl font-semibold text-xs transition ${
            activeTab === "leaderboard"
              ? "bg-teal-500/20 text-teal-300 border border-teal-400/40 shadow-[0_0_15px_rgba(42,127,142,0.3)]"
              : "text-slate-400 hover:text-white hover:bg-white/5"
          }`}
        >
          Comfort Model Leaderboard (Phase 2)
        </button>
        <button
          onClick={() => setActiveTab("surrogates")}
          className={`py-2 px-4 rounded-xl font-semibold text-xs transition ${
            activeTab === "surrogates"
              ? "bg-teal-500/20 text-teal-300 border border-teal-400/40 shadow-[0_0_15px_rgba(42,127,142,0.3)]"
              : "text-slate-400 hover:text-white hover:bg-white/5"
          }`}
        >
          25 Surrogates Accuracy Matrix (Phase 4)
        </button>
        <button
          onClick={() => setActiveTab("phases")}
          className={`py-2 px-4 rounded-xl font-semibold text-xs transition ${
            activeTab === "phases"
              ? "bg-teal-500/20 text-teal-300 border border-teal-400/40 shadow-[0_0_15px_rgba(42,127,142,0.3)]"
              : "text-slate-400 hover:text-white hover:bg-white/5"
          }`}
        >
          Phases & Evidence Ledger
        </button>
      </div>

      {/* TAB 1: Comfort Model Leaderboard */}
      {activeTab === "leaderboard" && (
        <div className="rounded-2xl glass-card p-6 space-y-4">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
            <div>
              <h3 className="text-lg font-bold text-white">
                Comfort Sensation Models Evaluated on Identical Complete Cases (58,512 Rows)
              </h3>
              <p className="text-xs text-slate-400 mt-0.5">
                Evaluation under Leave-One-Köppen-Group-Out (LOGO) cross-validation with 95% bootstrap confidence intervals.
              </p>
            </div>
            <div className="p-2.5 rounded-xl bg-rose-950/60 border border-rose-700/50 text-rose-300 text-xs font-mono">
              S1 Result: <strong>FAIL</strong> (Margin: -0.0154 vs Adaptive 90%)
            </div>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-xs font-mono text-left divide-y divide-slate-800">
              <thead className="bg-slate-900/60 text-slate-400">
                <tr>
                  <th className="py-3 px-4">Model Name</th>
                  <th className="py-3 px-4">Type</th>
                  <th className="py-3 px-4">CV Macro-F1</th>
                  <th className="py-3 px-4">Holdout Macro-F1</th>
                  <th className="py-3 px-4">95% Bootstrap CI</th>
                  <th className="py-3 px-4">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60 text-slate-200">
                {models.map((m, idx) => (
                  <tr
                    key={idx}
                    className={`transition hover:bg-slate-800/60 ${
                      m.status === "Best Baseline"
                        ? "bg-amber-950/20 text-amber-200 font-bold"
                        : m.status === "ML Champion"
                        ? "bg-teal-950/30 text-teal-200 font-bold"
                        : ""
                    }`}
                  >
                    <td className="py-3 px-4 flex items-center space-x-2">
                      {m.status === "Best Baseline" && <Award className="w-4 h-4 text-amber-400" />}
                      {m.status === "ML Champion" && <Award className="w-4 h-4 text-teal-400" />}
                      <span>{m.name}</span>
                    </td>
                    <td className="py-3 px-4 text-slate-400">{m.type}</td>
                    <td className="py-3 px-4">{m.cvF1.toFixed(4)}</td>
                    <td className="py-3 px-4 text-white font-bold">{m.holdoutF1.toFixed(4)}</td>
                    <td className="py-3 px-4 text-slate-400">{m.ci}</td>
                    <td className="py-3 px-4">
                      <span className="px-2 py-0.5 rounded text-[10px] bg-slate-800 border border-slate-700">
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
        <div className="rounded-2xl glass-panel p-6 border border-slate-700/60 space-y-4">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
            <div>
              <h3 className="text-lg font-bold text-white">
                25 XGBoost Surrogate Accuracy Matrix (R² Test Scores)
              </h3>
              <p className="text-xs text-slate-400 mt-0.5">
                Target: R² ≥ 0.95 on held-out test designs. S2 status: <strong>PARTIAL (23/25 PASS)</strong>. Mean O2 R² = 0.987.
              </p>
            </div>
            <span className="text-xs font-mono text-slate-300">
              Green: R² ≥ 0.95 • Red: R² &lt; 0.95
            </span>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-xs font-mono text-center divide-y divide-slate-800 border border-slate-800 rounded-xl overflow-hidden">
              <thead className="bg-slate-900 text-slate-300">
                <tr>
                  <th className="py-3 px-4 text-left">Climate Zone Station</th>
                  {targets.map((t) => (
                    <th key={t} className="py-3 px-4">{targetLabels[t]}</th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800 text-slate-200">
                {cities.map((city) => (
                  <tr key={city} className="hover:bg-slate-800/40 transition">
                    <td className="py-3 px-4 text-left font-bold text-white flex items-center space-x-2">
                      <span>{CITIES_DATA[city].name}</span>
                      <span className="text-[10px] text-slate-400">({CITIES_DATA[city].climateCode})</span>
                    </td>
                    {targets.map((t) => {
                      const m = getMetric(city, t);
                      const r2 = m?.r2 ?? 0;
                      const passes = r2 >= 0.95;

                      return (
                        <td key={t} className="py-3 px-4">
                          <span
                            className={`inline-block px-2.5 py-1 rounded-md font-bold text-xs ${
                              passes
                                ? "bg-emerald-950/80 text-emerald-300 border border-emerald-700/60"
                                : "bg-rose-950/80 text-rose-300 border border-rose-700/60 font-black animate-pulse"
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

          <div className="p-3 rounded-xl bg-slate-900 border border-slate-800 text-xs text-slate-300 flex items-start space-x-2">
            <Info className="w-4 h-4 text-amber-400 shrink-0 mt-0.5" />
            <span>
              The two targets falling marginally below the 0.95 threshold are <strong>Mumbai O1_ml (R² = 0.9406)</strong> and <strong>Shimla warm_ml (R² = 0.9225)</strong>. All 5 annual HVAC energy surrogates (O2) achieved high accuracy with mean R² = 0.987.
            </span>
          </div>
        </div>
      )}

      {/* TAB 3: Phases & Evidence Ledger */}
      {activeTab === "phases" && (
        <div className="space-y-4">
          <div className="rounded-2xl glass-panel p-6 border border-slate-700/60 space-y-4">
            <h3 className="text-lg font-bold text-white flex items-center space-x-2">
              <GitCommit className="w-5 h-5 text-teal-400" />
              <span>Project Execution Phases & Verification Evidence</span>
            </h3>
            <p className="text-xs text-slate-400">
              Strict evidence gating contract: zero claims without literal command execution logs in <code className="text-slate-300">reports/evidence/</code>.
            </p>

            <div className="divide-y divide-slate-800">
              {phases.map((p, idx) => (
                <div key={idx} className="py-4 flex flex-col md:flex-row md:items-center justify-between gap-2">
                  <div className="space-y-1">
                    <div className="flex items-center space-x-2">
                      <span className="font-mono text-xs font-bold text-teal-400">{p.phase}</span>
                      <span className="font-bold text-sm text-white">{p.name}</span>
                      <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-emerald-950 text-emerald-400 border border-emerald-700/60">
                        {p.status}
                      </span>
                    </div>
                    <p className="text-xs text-slate-300">{p.details}</p>
                  </div>

                  <div className="flex items-center space-x-2 font-mono text-xs text-slate-400 shrink-0">
                    <FileText className="w-3.5 h-3.5 text-slate-400" />
                    <span>Evidence: <strong className="text-slate-200">[{p.evidence}]</strong></span>
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
