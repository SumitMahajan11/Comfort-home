"use client";

import React, { useState } from "react";
import Link from "next/link";
import { getProjectMetadata } from "@/lib/data";
import { getOverviewFacts } from "@/lib/metrics";
import { GLOSSARY } from "@/lib/glossary";
import { CityKey } from "@/types";
import { IndiaClimateMap } from "@/components/maps/IndiaClimateMap";
import { CriteriaScorecard } from "@/components/common/CriteriaScorecard";
import { InfoTip } from "@/components/ui/Tooltip";
import { CITIES_DATA } from "@/lib/constants";
import {
  Compass,
  ArrowRight,
  Sparkles,
  Layers,
  Sliders,
  ShieldCheck,
  ShieldAlert,
  BarChart3
} from "lucide-react";

export default function OverviewPage() {
  const meta = getProjectMetadata();
  const facts = getOverviewFacts();
  const [selectedCity, setSelectedCity] = useState<CityKey>("Jodhpur");

  const lowConfidenceCities = Object.values(CITIES_DATA)
    .filter((c) => c.confidence === "Low")
    .map((c) => c.name);
  const lowConfidenceCount = lowConfidenceCities.length;
  const totalCitiesCount = Object.keys(CITIES_DATA).length;
  const lowConfidenceText =
    lowConfidenceCities.length <= 2
      ? lowConfidenceCities.join(" and ")
      : `${lowConfidenceCities.slice(0, -1).join(", ")}, and ${lowConfidenceCities[lowConfidenceCities.length - 1]}`;

  return (
    <div className="space-y-8 pb-8">
      {/* Hero Section */}
      <section className="relative pt-4 pb-2 space-y-6">
        <div className="text-center max-w-3xl mx-auto space-y-4">
          <div className="inline-flex items-center space-x-2 px-3 py-1 rounded-[var(--radius)] bg-[var(--surface-2)] border border-[var(--line)] text-[var(--primary)] text-xs font-semibold">
            <span className="w-2 h-2 rounded-full bg-[var(--primary)]" />
            <span>Passive shelter envelope decision-support</span>
          </div>

          <h1 className="text-3xl sm:text-4xl font-semibold text-[var(--ink)] tracking-tight leading-tight">
            Find a low-energy, comfortable shelter design for your Indian city.
          </h1>

          <p className="text-base text-[var(--ink-2)] leading-relaxed max-w-prose mx-auto">
            ClimateAdapt-Comfort helps architects, engineers, and planners select envelope materials and window configurations that minimize{" "}
            <span className="inline-flex items-center text-[var(--ink)] font-medium">
              hours uncomfortable
              <InfoTip
                label="hours uncomfortable"
                content={`${GLOSSARY.o1.technicalName}: ${GLOSSARY.o1.definition}`}
              />
            </span>{" "}
            and{" "}
            <span className="inline-flex items-center text-[var(--ink)] font-medium">
              heating & cooling energy
              <InfoTip
                label="heating & cooling energy"
                content={`${GLOSSARY.o2.technicalName}: ${GLOSSARY.o2.definition}`}
              />
            </span>{" "}
            using{" "}
            <span className="inline-flex items-center text-[var(--ink)] font-medium">
              fast estimators trained on simulations
              <InfoTip
                label="fast estimator"
                content={`${GLOSSARY.surrogate.technicalName}: ${GLOSSARY.surrogate.definition}`}
              />
            </span>{" "}
            and{" "}
            <span className="inline-flex items-center text-[var(--ink)] font-medium">
              best trade-off designs
              <InfoTip
                label="best trade-off designs"
                content={`${GLOSSARY.pareto.technicalName}: ${GLOSSARY.pareto.definition}`}
              />
            </span>.
          </p>

          {/* Quick CTA Actions */}
          <div className="flex flex-wrap items-center justify-center gap-3 pt-2">
            <Link
              href="/recommender"
              className="px-5 py-2.5 rounded-[var(--radius)] bg-[var(--primary)] hover:opacity-90 text-[var(--primary-contrast)] font-semibold text-sm transition shadow-sm flex items-center space-x-2"
            >
              <Sparkles className="w-4 h-4 text-[var(--primary-contrast)]" />
              <span>Plan my shelter</span>
              <ArrowRight className="w-4 h-4 ml-1" />
            </Link>
            <Link
              href="/models"
              className="px-5 py-2.5 rounded-[var(--radius)] bg-[var(--surface-2)] hover:bg-[var(--surface)] border border-[var(--line)] text-[var(--ink)] font-semibold text-sm transition flex items-center space-x-2"
            >
              <span>See how it was tested</span>
              <ArrowRight className="w-4 h-4 ml-1" />
            </Link>
          </div>
        </div>

        {/* 3 Plain-Language Facts */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 pt-2">
          {facts.map((fact) => (
            <div
              key={fact.id}
              className="p-4 sm:p-6 rounded-[var(--radius)] border border-[var(--line)] bg-[var(--surface)] flex flex-col justify-between text-left"
            >
              <div>
                <div className="text-[13px] font-medium text-[var(--ink-2)] text-left">
                  {fact.label}
                </div>
                <div className="mt-2 text-2xl font-bold text-[var(--ink)] tabular-nums text-left">
                  {fact.value}
                </div>
              </div>
              <p className="mt-2 text-[13px] text-[var(--ink-2)] leading-snug text-left">
                {fact.explanation}
              </p>
            </div>
          ))}
        </div>
      </section>

      {/* Before You Rely on This Panel */}
      <section className="rounded-[var(--radius)] border border-[var(--warn)]/40 bg-[var(--warn)]/5 p-4 sm:p-6 space-y-4">
        <div className="flex items-center space-x-2 text-[var(--warn)]">
          <ShieldAlert className="w-5 h-5 shrink-0" />
          <h2 className="text-base font-semibold text-[var(--ink)]">
            Before you rely on this tool
          </h2>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs text-[var(--ink-2)] leading-relaxed">
          <div className="space-y-2">
            <div>
              <strong className="text-[var(--ink)] block mb-0.5">Which comfort check drives recommendations?</strong>
              <p>
                Comfort is evaluated using two complementary checks: the standard physical Adaptive 90% comfort rule and an empirical machine learning model. Check whether{" "}
                <span className="inline-flex items-center text-[var(--ink)] font-medium">
                  our two comfort checks agree
                  <InfoTip
                    label="dual comfort checks"
                    content={`${GLOSSARY.dualJudge.technicalName}: ${GLOSSARY.dualJudge.definition}`}
                  />
                </span>{" "}
                before adopting any recommendation.
              </p>
            </div>
            <div>
              <strong className="text-[var(--ink)] block mb-0.5">ML model did NOT beat the adaptive baseline (S1 FAIL):</strong>
              <p>
                Under cross-validation across climate zones, the ML comfort model achieved 0.4785 macro-F1 vs 0.4939 for the standard adaptive baseline (reported as S1 FAIL). Because the ML model did not outperform standard rules, both standards are preserved side by side.
              </p>
            </div>
          </div>

          <div className="space-y-2">
            <div>
              <strong className="text-[var(--ink)] block mb-0.5">Results are simulated, not measured:</strong>
              <p>
                All indoor temperatures, comfort hours, and energy savings are derived from EnergyPlus thermodynamic simulations and fast surrogates. There is zero physical on-site sensor validation.
              </p>
            </div>
            <div>
              <strong className="text-[var(--ink)] block mb-0.5">
                {lowConfidenceCount} of {totalCitiesCount} cities are low-confidence:
              </strong>
              <p>
                <span data-testid="low-confidence-cities">{lowConfidenceText}</span> are low-confidence stations due to cold-climate extrapolation or lower judge agreement. In these cities,{" "}
                <span className="inline-flex items-center text-[var(--ink)] font-medium">
                  treat recommendations as a rough guide
                  <InfoTip
                    label="treat as a rough guide"
                    content={`${GLOSSARY.lowConfidence.technicalName}: ${GLOSSARY.lowConfidence.definition}`}
                  />
                </span>{" "}
                rather than exact performance promises.
              </p>
            </div>
          </div>
        </div>

        <div className="pt-2 border-t border-[var(--warn)]/20 flex flex-wrap items-center gap-4 text-xs font-semibold">
          <Link
            href="/models"
            className="text-[var(--primary)] hover:underline inline-flex items-center space-x-1"
          >
            <span>Inspect comfort model evaluation</span>
            <ArrowRight className="w-3.5 h-3.5" />
          </Link>
          <Link
            href="/about"
            className="text-[var(--primary)] hover:underline inline-flex items-center space-x-1"
          >
            <span>Read full methodology and known limitations</span>
            <ArrowRight className="w-3.5 h-3.5" />
          </Link>
        </div>
      </section>

      {/* Interactive Map Section */}
      <section className="space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-end justify-between gap-2 border-b border-[var(--line)] pb-3">
          <div>
            <h2 className="text-2xl font-semibold text-[var(--ink)] tracking-tight flex items-center space-x-2">
              <Compass className="w-5 h-5 text-[var(--primary)]" />
              <span>5 Indian climate zones & applicability</span>
            </h2>
            <p className="text-xs text-[var(--ink-2)] mt-0.5">
              Select any station to inspect climate boundaries, weather data, and check whether our two comfort checks agree.
            </p>
          </div>
          <Link
            href={`/cities?city=${selectedCity}`}
            className="text-xs font-semibold text-[var(--primary)] hover:underline flex items-center space-x-1"
          >
            <span>View full city explorer</span>
            <ArrowRight className="w-3.5 h-3.5" />
          </Link>
        </div>

        <IndiaClimateMap
          selectedCity={selectedCity}
          onSelectCity={(city) => setSelectedCity(city)}
        />
      </section>

      {/* Research Results Scorecard (S1 - S4) */}
      <section id="research-results" className="space-y-4 scroll-mt-20">
        <div className="flex items-center justify-between border-b border-[var(--line)] pb-3">
          <div>
            <h2 className="text-2xl font-semibold text-[var(--ink)] tracking-tight flex items-center space-x-2">
              <ShieldCheck className="w-5 h-5 text-[var(--primary)]" />
              <span>Research results</span>
            </h2>
            <p className="text-xs text-[var(--ink-2)] mt-0.5">
              Empirical evaluation against locked thresholds defined in project specifications. Evidence IDs are accessible within each expanded details panel.
            </p>
          </div>
        </div>

        <CriteriaScorecard criteria={meta.success_criteria} />
      </section>

      {/* 3 Equal Feature Cards */}
      <section className="grid grid-cols-1 md:grid-cols-3 gap-6 pt-2">
        <Link
          href="/evaluate"
          className="rounded-[var(--radius)] border border-[var(--line)] bg-[var(--surface)] p-4 sm:p-6 group flex flex-col justify-between hover:bg-[var(--surface-2)]/40 transition"
        >
          <div className="space-y-2">
            <div className="p-3 rounded-[var(--radius)] bg-[var(--surface-2)] border border-[var(--line)] text-[var(--primary)] w-fit transition">
              <Sliders className="w-6 h-6" />
            </div>
            <h3 className="text-lg font-semibold text-[var(--ink)] transition">
              Evaluate a shelter
            </h3>
            <p className="text-[13px] text-[var(--ink-2)] leading-relaxed">
              Adjust 8 envelope variables in real time with live fast estimator predictions, reference comparisons, and an interactive 3D model.
            </p>
          </div>
          <div className="pt-4 flex items-center text-[13px] font-semibold text-[var(--primary)]">
            <span>Open interactive evaluator</span>
            <ArrowRight className="w-4 h-4 ml-1 group-hover:translate-x-1 transition" />
          </div>
        </Link>

        <Link
          href="/pareto"
          className="rounded-[var(--radius)] border border-[var(--line)] bg-[var(--surface)] p-4 sm:p-6 group flex flex-col justify-between hover:bg-[var(--surface-2)]/40 transition"
        >
          <div className="space-y-2">
            <div className="p-3 rounded-[var(--radius)] bg-[var(--surface-2)] border border-[var(--line)] text-[var(--primary)] w-fit transition">
              <Layers className="w-6 h-6" />
            </div>
            <h3 className="text-lg font-semibold text-[var(--ink)] transition">
              Best trade-off designs
            </h3>
            <p className="text-[13px] text-[var(--ink-2)] leading-relaxed">
              Explore 500 optimal envelope designs across 5 climate zones with interactive trade-off charts, simulation-verified designs, and custom data export.
            </p>
          </div>
          <div className="pt-4 flex items-center text-[13px] font-semibold text-[var(--primary)]">
            <span>Explore trade-off designs</span>
            <ArrowRight className="w-4 h-4 ml-1 group-hover:translate-x-1 transition" />
          </div>
        </Link>

        <Link
          href="/explain"
          className="rounded-[var(--radius)] border border-[var(--line)] bg-[var(--surface)] p-4 sm:p-6 group flex flex-col justify-between hover:bg-[var(--surface-2)]/40 transition"
        >
          <div className="space-y-2">
            <div className="p-3 rounded-[var(--radius)] bg-[var(--surface-2)] border border-[var(--line)] text-[var(--primary)] w-fit transition">
              <BarChart3 className="w-6 h-6" />
            </div>
            <h3 className="text-lg font-semibold text-[var(--ink)] transition">
              Performance drivers
            </h3>
            <p className="text-[13px] text-[var(--ink-2)] leading-relaxed">
              Understand which physical features govern discomfort hours and energy savings using SHAP feature attribution plots and local drivers.
            </p>
          </div>
          <div className="pt-4 flex items-center text-[13px] font-semibold text-[var(--primary)]">
            <span>View performance explanations</span>
            <ArrowRight className="w-4 h-4 ml-1 group-hover:translate-x-1 transition" />
          </div>
        </Link>
      </section>
    </div>
  );
}
