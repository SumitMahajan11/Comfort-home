"use client";

import React, { useState } from "react";
import Link from "next/link";
import { IndiaClimateMap } from "@/components/maps/IndiaClimateMap";
import { CriteriaScorecard } from "@/components/common/CriteriaScorecard";
import { getProjectMetadata } from "@/lib/data";
import { formatNumber } from "@/lib/utils";
import { CityKey } from "@/types";
import {
  Activity,
  Layers,
  Sliders,
  Sparkles,
  ArrowRight,
  Database,
  Cpu,
  ShieldCheck,
  Compass,
  CheckCircle2,
  AlertTriangle
} from "lucide-react";

export default function OverviewPage() {
  const meta = getProjectMetadata();
  const [selectedCity, setSelectedCity] = useState<CityKey>("Jodhpur");

  return (
    <div className="space-y-12 pb-16">
      {/* Hero Section */}
      <section className="relative pt-6 pb-2">
        <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-8">
          <div className="max-w-2xl space-y-4">
            <div className="inline-flex items-center space-x-2 px-3 py-1 rounded-full bg-teal-950/70 border border-teal-500/40 text-teal-300 text-xs font-mono">
              <span className="w-2 h-2 rounded-full bg-teal-400 animate-ping" />
              <span>Multi-Objective Passive Shelter Optimization</span>
            </div>

            <h1 className="text-4xl sm:text-5xl font-extrabold text-white tracking-tight leading-tight">
              Evidence-Gated Comfort Design Across{" "}
              <span className="text-transparent bg-clip-text bg-gradient-to-r from-teal-400 via-sky-300 to-indigo-300">
                Indian Climates
              </span>
            </h1>

            <p className="text-base text-slate-300 leading-relaxed">
              Does an empirical thermal sensation classifier coupled with EnergyPlus building simulation recommend shelter envelopes that minimize discomfort hours and HVAC energy demand? Explore 500 Pareto-optimal designs across 5 distinct Indian climate zones.
            </p>

            {/* Quick CTA Actions */}
            <div className="flex flex-wrap items-center gap-3 pt-2">
              <Link
                href="/recommender"
                className="px-5 py-2.5 rounded-xl bg-gradient-to-r from-teal-500/90 to-cyan-500/90 hover:from-teal-400 hover:to-cyan-400 text-slate-950 font-bold text-sm transition shadow-[0_0_25px_rgba(42,127,142,0.4)] flex items-center space-x-2"
              >
                <Sparkles className="w-4 h-4 text-slate-950" />
                <span>Start v2 Decision Support</span>
                <ArrowRight className="w-4 h-4 ml-1" />
              </Link>
              <Link
                href="/pareto"
                className="px-5 py-2.5 rounded-xl glass-button text-slate-100 font-semibold text-sm transition flex items-center space-x-2"
              >
                <Layers className="w-4 h-4 text-teal-400" />
                <span>Explore Pareto Frontiers</span>
              </Link>
              <Link
                href="/evaluate"
                className="px-5 py-2.5 rounded-xl glass-button text-slate-100 font-semibold text-sm transition flex items-center space-x-2"
              >
                <Sliders className="w-4 h-4 text-teal-400" />
                <span>Surrogate Evaluator</span>
              </Link>
            </div>
          </div>

          {/* Key Metric Highlights Card */}
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-2 gap-3 lg:w-[380px]">
            <div className="rounded-xl glass-card p-4">
              <span className="text-xs font-mono text-slate-400 block">DB II Records</span>
              <span className="text-2xl font-black text-white font-mono mt-1 block">
                {formatNumber(meta.kpis.survey_records, 0)}
              </span>
              <span className="text-[10px] text-teal-400 mt-0.5 block">58,512 complete-case</span>
            </div>

            <div className="rounded-xl glass-card p-4">
              <span className="text-xs font-mono text-slate-400 block">Simulations</span>
              <span className="text-2xl font-black text-white font-mono mt-1 block">
                {formatNumber(meta.kpis.total_simulations, 0)}
              </span>
              <span className="text-[10px] text-teal-400 mt-0.5 block">99.88% EnergyPlus pass</span>
            </div>

            <div className="rounded-xl glass-card p-4">
              <span className="text-xs font-mono text-slate-400 block">Surrogate Models</span>
              <span className="text-2xl font-black text-white font-mono mt-1 block">
                {meta.kpis.surrogate_models}
              </span>
              <span className="text-[10px] text-amber-400 mt-0.5 block">23/25 R² ≥ 0.95</span>
            </div>

            <div className="rounded-xl glass-card p-4">
              <span className="text-xs font-mono text-slate-400 block">Pareto Designs</span>
              <span className="text-2xl font-black text-white font-mono mt-1 block">
                {meta.kpis.pareto_designs}
              </span>
              <span className="text-[10px] text-emerald-400 mt-0.5 block">100 designs / city</span>
            </div>

            <div className="rounded-xl glass-card p-4 col-span-2 sm:col-span-1 lg:col-span-2 bg-gradient-to-br from-teal-950/40 to-slate-900/60 border-teal-500/30">
              <span className="text-xs font-mono text-slate-400 block">Physical Verification</span>
              <div className="flex items-baseline justify-between mt-1">
                <span className="text-2xl font-black text-emerald-400 font-mono">
                  {meta.kpis.verified_in_energyplus} Runs
                </span>
                <span className="text-xs font-bold text-emerald-300">
                  36/50 Beat Both Refs
                </span>
              </div>
              <span className="text-[10px] text-slate-400 mt-0.5 block">
                EnergyPlus direct simulation confirms Pareto superiority
              </span>
            </div>
          </div>
        </div>
      </section>

      {/* Interactive Map Section */}
      <section className="space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-end justify-between gap-2 border-b border-slate-800 pb-3">
          <div>
            <h2 className="text-2xl font-bold text-white tracking-tight flex items-center space-x-2">
              <Compass className="w-5 h-5 text-teal-400" />
              <span>5 Indian Climate Zones & Applicability</span>
            </h2>
            <p className="text-xs text-slate-400 mt-0.5">
              Select any station to inspect climate boundaries, weather station EPWs, and dual-judge agreement metrics.
            </p>
          </div>
          <Link
            href={`/cities?city=${selectedCity}`}
            className="text-xs font-medium text-teal-400 hover:text-teal-300 flex items-center space-x-1"
          >
            <span>View Full City Explorer</span>
            <ArrowRight className="w-3.5 h-3.5" />
          </Link>
        </div>

        <IndiaClimateMap
          selectedCity={selectedCity}
          onSelectCity={(city) => setSelectedCity(city)}
        />
      </section>

      {/* Success Criteria Scorecard (S1 - S4) */}
      <section className="space-y-4">
        <div className="flex items-center justify-between border-b border-slate-800 pb-3">
          <div>
            <h2 className="text-2xl font-bold text-white tracking-tight flex items-center space-x-2">
              <ShieldCheck className="w-5 h-5 text-teal-400" />
              <span>Project Success Criteria (S1 – S4)</span>
            </h2>
            <p className="text-xs text-slate-400 mt-0.5">
              Honest evaluation against locked thresholds defined in <code className="text-slate-300">docs/PROJECT_SPEC.md</code>.
            </p>
          </div>
        </div>

        <CriteriaScorecard criteria={meta.success_criteria} />
      </section>

      {/* Quick Portal Cards */}
      <section className="grid grid-cols-1 md:grid-cols-3 gap-4 pt-4">
        <Link
          href="/evaluate"
          className="rounded-2xl glass-card p-6 group flex flex-col justify-between"
        >
          <div className="space-y-2">
            <div className="p-3 rounded-xl bg-teal-500/15 text-teal-300 w-fit group-hover:scale-110 transition shadow-[0_0_15px_rgba(42,127,142,0.3)]">
              <Sliders className="w-6 h-6" />
            </div>
            <h3 className="text-lg font-bold text-white group-hover:text-teal-300 transition">
              Evaluate a Shelter
            </h3>
            <p className="text-xs text-slate-300 leading-relaxed">
              Adjust 8 design variables in real time with live surrogate predictions, R1/R2 comparison arrows, and an interactive 3D model.
            </p>
          </div>
          <div className="pt-4 flex items-center text-xs font-semibold text-teal-400">
            <span>Open Interactive Evaluator</span>
            <ArrowRight className="w-4 h-4 ml-1 group-hover:translate-x-1 transition" />
          </div>
        </Link>

        <Link
          href="/pareto"
          className="rounded-2xl glass-card p-6 group flex flex-col justify-between"
        >
          <div className="space-y-2">
            <div className="p-3 rounded-xl bg-sky-500/15 text-sky-300 w-fit group-hover:scale-110 transition shadow-[0_0_15px_rgba(56,189,248,0.3)]">
              <Layers className="w-6 h-6" />
            </div>
            <h3 className="text-lg font-bold text-white group-hover:text-sky-300 transition">
              Pareto Explorer
            </h3>
            <p className="text-xs text-slate-300 leading-relaxed">
              3D and 2D scatter plots of 100 non-dominated designs per climate zone, verified points, knee points, and custom export.
            </p>
          </div>
          <div className="pt-4 flex items-center text-xs font-semibold text-sky-400">
            <span>Explore Non-Dominated Fronts</span>
            <ArrowRight className="w-4 h-4 ml-1 group-hover:translate-x-1 transition" />
          </div>
        </Link>

        <Link
          href="/explain"
          className="rounded-2xl glass-card p-6 group flex flex-col justify-between"
        >
          <div className="space-y-2">
            <div className="p-3 rounded-xl bg-indigo-500/15 text-indigo-300 w-fit group-hover:scale-110 transition shadow-[0_0_15px_rgba(99,102,241,0.3)]">
              <Sparkles className="w-6 h-6" />
            </div>
            <h3 className="text-lg font-bold text-white group-hover:text-indigo-300 transition">
              SHAP Explainability
            </h3>
            <p className="text-xs text-slate-300 leading-relaxed">
              Understand which physical features govern discomfort and energy savings with global beeswarm plots and local waterfall drivers.
            </p>
          </div>
          <div className="pt-4 flex items-center text-xs font-semibold text-indigo-400">
            <span>View Model Explanations</span>
            <ArrowRight className="w-4 h-4 ml-1 group-hover:translate-x-1 transition" />
          </div>
        </Link>
      </section>
    </div>
  );
}
