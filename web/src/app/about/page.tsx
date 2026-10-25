"use client";

import React, { useState } from "react";
import { getProjectMetadata } from "@/lib/data";
import {
  HelpCircle,
  Cpu,
  GitBranch,
  ShieldAlert,
  Search,
  BookOpen,
  ArrowRight,
  Terminal,
  Database,
  Layers,
  Sparkles,
  CheckCircle2,
  AlertTriangle
} from "lucide-react";

export default function AboutPage() {
  const meta = getProjectMetadata();
  const [decisionFilter, setDecisionFilter] = useState("");

  const filteredDecisions = meta.decisions.filter(
    (d) =>
      d.id.toLowerCase().includes(decisionFilter.toLowerCase()) ||
      d.title.toLowerCase().includes(decisionFilter.toLowerCase()) ||
      d.description.toLowerCase().includes(decisionFilter.toLowerCase())
  );

  const pipelineSteps = [
    { title: "1. DB II Data", desc: "109,033 survey votes; clean 58,512 complete cases." },
    { title: "2. Comfort Classifier", desc: "Calibrated Champion model + Adaptive 90% dual judge." },
    { title: "3. EnergyPlus Batch", desc: "10,000 runs across 5 Indian climate stations (2 modes)." },
    { title: "4. Dual-Judge Coupling", desc: "43.69M hourly records scored for O1_ml, O1_adapt, O2." },
    { title: "5. XGBoost Surrogates", desc: "25 Optuna-tuned regressors predicting objectives." },
    { title: "6. NSGA-II Optimization", desc: "500 non-dominated Pareto designs derived (100/city)." },
    { title: "7. Direct Verification", desc: "50 designs re-simulated directly in EnergyPlus (S3 PASS)." },
    { title: "8. SHAP & Dashboard", desc: "TreeExplainer local drivers & interactive decision app." }
  ];

  const limitations = [
    { title: "Field Survey Building Typologies", desc: "DB II records are predominantly offices, classrooms, and standard multi-family housing, rather than emergency disaster or temporary shelters." },
    { title: "Simulated Rather Than Measured", desc: "All indoor temperatures, discomfort hours, and energy savings are derived from EnergyPlus simulations and surrogate models. There is zero physical sensor validation." },
    { title: "Shimla Cold-Zone Extrapolation (D-011)", desc: "DB II has zero labelled sensation votes for the Shimla building (460 rows, all TSV missing). Furthermore, winter temperatures drop below the 10°C Adaptive 90% validity boundary (73.97% valid share)." },
    { title: "Semi-Arid vs True Desert Coverage", desc: "Hot-dry data in DB II originates mostly from semi-arid Indian stations (Jaipur/Ahmedabad); hyper-arid desert classes have only 2 buildings each." },
    { title: "Behavioral Variables are Scenario Assumptions", desc: "Occupant metabolic rate (1.1 met), air velocity (0.15 m/s), and dynamic clothing schedules are fixed modeling assumptions, not empirical predictions." }
  ];

  return (
    <div className="space-y-10 pb-16">
      {/* Header */}
      <div className="border-b border-slate-800 pb-4">
        <h1 className="text-3xl font-bold text-white tracking-tight flex items-center space-x-3">
          <HelpCircle className="w-7 h-7 text-teal-400" />
          <span>About ClimateAdapt-Comfort & Methodology</span>
        </h1>
        <p className="text-sm text-slate-300 mt-1 max-w-2xl">
          Complete scientific architecture, locked engineering decisions, scenario assumptions, known limitations, and one-command reproduction.
        </p>
      </div>

      {/* Pipeline Diagram Flow */}
      <div className="rounded-2xl glass-card p-6 space-y-5">
        <div>
          <span className="text-[10px] font-mono uppercase tracking-wider text-teal-400">
            End-to-End System Architecture
          </span>
          <h3 className="text-lg font-bold text-white mt-1">
            Integrated Comfort Prediction, Building Simulation & Multi-Objective Pipeline
          </h3>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
          {pipelineSteps.map((step, idx) => (
            <div
              key={idx}
              className="p-3.5 rounded-xl glass-panel relative space-y-1.5"
            >
              <div className="text-xs font-bold text-teal-300 font-mono">
                {step.title}
              </div>
              <p className="text-[11px] text-slate-400 leading-snug">
                {step.desc}
              </p>
            </div>
          ))}
        </div>
      </div>

      {/* Assumptions Log (A-001..A-007) */}
      <div className="rounded-2xl glass-card p-6 space-y-4">
        <div className="flex items-center space-x-2">
          <BookOpen className="w-5 h-5 text-teal-400" />
          <h3 className="text-lg font-bold text-white">
            Scenario Assumptions Log (A-001 to A-007)
          </h3>
        </div>
        <p className="text-xs text-slate-400">
          Locked modeling parameters defined in <code className="text-slate-300">docs/PROJECT_SPEC.md</code>.
        </p>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-xs">
          {meta.assumptions.map((a) => (
            <div key={a.id} className="p-3.5 rounded-xl glass-panel space-y-1">
              <div className="flex items-center justify-between">
                <span className="font-mono font-bold text-teal-400">{a.id}</span>
                <span className="font-semibold text-white">{a.name}</span>
              </div>
              <p className="text-[11px] text-slate-300 leading-snug">{a.value}</p>
            </div>
          ))}
        </div>
      </div>

      {/* Locked Decisions Log (D-001..D-019) */}
      <div className="rounded-2xl glass-card p-6 space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div>
            <h3 className="text-lg font-bold text-white">
              Locked Decision Log (D-001 to D-019)
            </h3>
            <p className="text-xs text-slate-400 mt-0.5">
              Binding architectural and methodological decisions recorded in <code className="text-slate-300">docs/TRACKER.md</code>.
            </p>
          </div>

          {/* Decision search bar */}
          <div className="flex items-center px-3 py-1.5 rounded-xl glass-input w-full sm:w-64">
            <Search className="w-3.5 h-3.5 text-slate-400 mr-2 shrink-0" />
            <input
              type="text"
              value={decisionFilter}
              onChange={(e) => setDecisionFilter(e.target.value)}
              placeholder="Search decisions..."
              className="bg-transparent text-xs text-white placeholder-slate-400 focus:outline-none w-full"
            />
          </div>
        </div>

        <div className="divide-y divide-slate-800">
          {filteredDecisions.map((d) => (
            <div key={d.id} className="py-3 flex flex-col sm:flex-row sm:items-baseline justify-between gap-2 text-xs">
              <div className="space-y-0.5">
                <div className="flex items-center space-x-2">
                  <span className="font-mono font-bold text-teal-400">{d.id}:</span>
                  <span className="font-semibold text-white">{d.title}</span>
                </div>
                <p className="text-[11px] text-slate-300 pl-6 leading-snug">{d.description}</p>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Known Limitations */}
      <div className="rounded-2xl glass-card p-6 border-amber-500/40 bg-amber-950/20 space-y-4 shadow-[0_0_25px_rgba(245,158,11,0.1)]">
        <div className="flex items-center space-x-2 text-amber-300">
          <ShieldAlert className="w-5 h-5 text-amber-400" />
          <h3 className="text-lg font-bold">
            Mandatory Known Limitations (Project Spec Section 10)
          </h3>
        </div>
        <p className="text-xs text-amber-200/80">
          State in every final report and presentation; essential for honest scientific transparency.
        </p>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-xs">
          {limitations.map((lim, idx) => (
            <div key={idx} className="p-3.5 rounded-xl glass-panel space-y-1">
              <span className="font-semibold text-amber-300 block">{lim.title}</span>
              <p className="text-[11px] text-slate-300 leading-snug">{lim.desc}</p>
            </div>
          ))}
        </div>
      </div>

      {/* Reproduction Commands */}
      <div className="rounded-2xl glass-card p-6 space-y-3">
        <div className="flex items-center space-x-2">
          <Terminal className="w-5 h-5 text-teal-400" />
          <h3 className="text-lg font-bold text-white">
            One-Command Reproduction Pipeline
          </h3>
        </div>
        <p className="text-xs text-slate-400">
          Run all stages or execute unit testing using the local virtual environment:
        </p>

        <div className="p-4 rounded-xl glass-panel font-mono text-xs text-teal-300 space-y-2 overflow-x-auto border-white/10">
          <div># 1. Run unit and UI tests (13 passed, 1 skipped)</div>
          <div className="text-white">.\.venv\Scripts\python.exe -m pytest tests/ -v</div>
          <div className="pt-2"># 2. Launch Streamlit decision dashboard</div>
          <div className="text-white">.\.venv\Scripts\python.exe -m streamlit run src/app/app.py</div>
          <div className="pt-2"># 3. Re-export pipeline data to web JSON</div>
          <div className="text-white">.\.venv\Scripts\python.exe tools/export_web_data.py</div>
          <div className="pt-2"># 4. Start Next.js production web app</div>
          <div className="text-white">cd web &amp;&amp; npm run dev</div>
        </div>
      </div>
    </div>
  );
}
