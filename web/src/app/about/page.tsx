"use client";

import React, { useState, useMemo } from "react";
import { getProjectMetadata } from "@/lib/data";
import {
  HelpCircle,
  ShieldAlert,
  Search,
  BookOpen,
  Terminal,
  Layers,
  FileCode,
  Scale,
  Copy,
  Check,
  X
} from "lucide-react";

interface CommandStep {
  title: string;
  command: string;
}

export default function AboutPage() {
  const meta = getProjectMetadata();
  const [decisionFilter, setDecisionFilter] = useState("");
  const [shellTab, setShellTab] = useState<"powershell" | "bash">("powershell");
  const [copiedIndex, setCopiedIndex] = useState<string | null>(null);

  const handleCopy = (command: string, id: string) => {
    navigator.clipboard.writeText(command);
    setCopiedIndex(id);
    setTimeout(() => {
      setCopiedIndex((current) => (current === id ? null : current));
    }, 2000);
  };

  const filteredDecisions = useMemo(() => {
    const q = decisionFilter.trim().toLowerCase();
    if (!q) return meta.decisions;
    return meta.decisions.filter(
      (d) =>
        d.id.toLowerCase().includes(q) ||
        d.title.toLowerCase().includes(q) ||
        d.description.toLowerCase().includes(q)
    );
  }, [meta.decisions, decisionFilter]);

  const limitations = [
    {
      title: "Field survey building typologies",
      desc: "DB II records are predominantly offices, classrooms, and standard multi-family housing, rather than emergency disaster or temporary shelters."
    },
    {
      title: "Simulated rather than measured",
      desc: "All indoor temperatures, discomfort hours, and energy savings are derived from EnergyPlus simulations and surrogate models. There is zero physical sensor validation."
    },
    {
      title: "Shimla cold-zone extrapolation (D-011)",
      desc: "DB II has zero labelled sensation votes for the Shimla building (460 rows, all TSV missing). Furthermore, winter temperatures drop below the 10°C Adaptive 90% validity boundary (73.97% valid share)."
    },
    {
      title: "Semi-arid vs true desert coverage",
      desc: "Hot-dry data in DB II originates mostly from semi-arid Indian stations (Jaipur/Ahmedabad); hyper-arid desert classes have only 2 buildings each."
    },
    {
      title: "Behavioral variables are scenario assumptions",
      desc: "Occupant metabolic rate (1.1 met), air velocity (0.15 m/s), and dynamic clothing schedules are fixed modeling assumptions, not empirical predictions."
    }
  ];

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

  const powerShellCommands: CommandStep[] = [
    {
      title: "Run unit and verification tests",
      command: ".\\.venv\\Scripts\\python.exe -m pytest tests/ -v"
    },
    {
      title: "Launch Streamlit legacy decision dashboard",
      command: ".\\.venv\\Scripts\\python.exe -m streamlit run src/app/app.py"
    },
    {
      title: "Re-export pipeline data to web JSON",
      command: ".\\.venv\\Scripts\\python.exe tools/export_web_data.py"
    },
    {
      title: "Navigate to web application directory",
      command: "cd web"
    },
    {
      title: "Start development web server",
      command: "npm run dev"
    }
  ];

  const bashCommands: CommandStep[] = [
    {
      title: "Run unit and verification tests",
      command: "./.venv/bin/python -m pytest tests/ -v"
    },
    {
      title: "Launch Streamlit legacy decision dashboard",
      command: "./.venv/bin/python -m streamlit run src/app/app.py"
    },
    {
      title: "Re-export pipeline data to web JSON",
      command: "./.venv/bin/python tools/export_web_data.py"
    },
    {
      title: "Navigate to web application directory",
      command: "cd web"
    },
    {
      title: "Start development web server",
      command: "npm run dev"
    }
  ];

  const activeCommands = shellTab === "powershell" ? powerShellCommands : bashCommands;

  const tocItems = [
    { id: "limitations", label: "Mandatory limitations", icon: ShieldAlert },
    { id: "architecture", label: "System architecture", icon: Layers },
    { id: "assumptions", label: "Scenario assumptions", icon: BookOpen },
    { id: "decisions", label: "Engineering decisions", icon: FileCode },
    { id: "licences", label: "Data licences & terms", icon: Scale },
    { id: "reproduction", label: "Reproduction pipeline", icon: Terminal }
  ];

  return (
    <div className="space-y-8 pb-16">
      {/* Header */}
      <div className="border-b border-[var(--line)] pb-4">
        <h1 className="text-3xl font-semibold text-[var(--ink)] tracking-tight flex items-center space-x-3">
          <HelpCircle className="w-7 h-7 text-[var(--primary)]" />
          <span>About ClimateAdapt-Comfort & Methodology</span>
        </h1>
        <p className="text-sm text-[var(--ink-2)] mt-1 max-w-2xl">
          Complete scientific architecture, locked engineering decisions, scenario assumptions, known limitations, and reproduction commands.
        </p>
      </div>

      {/* Main Container: Two-column on desktop (sticky TOC + content), single column on mobile */}
      <div className="lg:flex lg:gap-8 items-start">
        {/* Sticky Desktop Table of Contents */}
        <aside className="hidden lg:block w-60 shrink-0">
          <div className="sticky top-20 rounded-[8px] border border-[var(--line)] bg-[var(--surface)] p-4 space-y-3">
            <div className="text-[11px] font-bold text-[var(--ink-2)] uppercase tracking-wider">
              On this page
            </div>
            <nav className="space-y-1 text-xs">
              {tocItems.map((item) => (
                <a
                  key={item.id}
                  href={`#${item.id}`}
                  className="flex items-center space-x-2 py-1.5 px-2.5 rounded-[6px] text-[var(--ink-2)] hover:text-[var(--ink)] hover:bg-[var(--surface-2)] transition font-medium"
                >
                  <item.icon className="w-3.5 h-3.5 shrink-0 text-[var(--primary)]" />
                  <span className="truncate">{item.label}</span>
                </a>
              ))}
            </nav>
          </div>
        </aside>

        {/* Content Column */}
        <div className="flex-1 min-w-0 space-y-8">
          {/* SECTION 1: Mandatory Limitations (FIRST SECTION) */}
          <section
            id="limitations"
            className="scroll-mt-20 rounded-[8px] border border-[var(--line)] bg-[var(--surface)] p-6 space-y-4"
          >
            <div className="flex items-center space-x-2 text-[var(--warn)]">
              <ShieldAlert className="w-5 h-5 shrink-0" />
              <h2 className="text-lg font-semibold text-[var(--ink)]">
                Mandatory known limitations (Project Spec Section 10)
              </h2>
            </div>
            <p className="text-xs text-[var(--ink-2)] leading-relaxed">
              Essential for honest scientific transparency; must be stated in every research report and publication.
            </p>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-xs">
              {limitations.map((lim, idx) => (
                <div
                  key={idx}
                  className="p-3.5 rounded-[8px] border border-[var(--line)] bg-[var(--surface-2)] space-y-1"
                >
                  <span className="font-semibold text-[var(--ink)] block">{lim.title}</span>
                  <p className="text-[12px] text-[var(--ink-2)] leading-relaxed">{lim.desc}</p>
                </div>
              ))}
            </div>
          </section>

          {/* SECTION 2: Pipeline Diagram Flow */}
          <section
            id="architecture"
            className="scroll-mt-20 rounded-[8px] border border-[var(--line)] bg-[var(--surface)] p-6 space-y-5"
          >
            <div>
              <span className="text-xs font-semibold text-[var(--primary)]">
                End-to-end system architecture
              </span>
              <h2 className="text-lg font-semibold text-[var(--ink)] mt-1">
                Integrated comfort prediction, building simulation & multi-objective pipeline
              </h2>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-3">
              {pipelineSteps.map((step, idx) => (
                <div
                  key={idx}
                  className="p-3.5 rounded-[8px] border border-[var(--line)] bg-[var(--surface-2)] relative space-y-1.5"
                >
                  <div className="text-xs font-semibold text-[var(--ink)]">
                    {step.title}
                  </div>
                  <p className="text-[12px] text-[var(--ink-2)] leading-snug">
                    {step.desc}
                  </p>
                </div>
              ))}
            </div>
          </section>

          {/* SECTION 3: Scenario Assumptions (A-001 · Title format) */}
          <section
            id="assumptions"
            className="scroll-mt-20 rounded-[8px] border border-[var(--line)] bg-[var(--surface)] p-6 space-y-4"
          >
            <div className="flex items-center space-x-2">
              <BookOpen className="w-5 h-5 text-[var(--primary)] shrink-0" />
              <h2 className="text-lg font-semibold text-[var(--ink)]">
                Scenario assumptions log (A-001 to A-007)
              </h2>
            </div>
            <p className="text-xs text-[var(--ink-2)]">
              Locked modeling parameters defined in <code>docs/PROJECT_SPEC.md</code>.
            </p>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-xs">
              {meta.assumptions.map((a) => (
                <div
                  key={a.id}
                  className="p-3.5 rounded-[8px] border border-[var(--line)] bg-[var(--surface-2)] space-y-1.5"
                >
                  <div className="flex items-center space-x-1.5 text-xs">
                    <code className="text-xs text-[var(--primary)] font-semibold font-mono">{a.id}</code>
                    <span className="text-[var(--ink-2)]">·</span>
                    <span className="font-semibold text-[var(--ink)]">{a.name}</span>
                  </div>
                  <p className="text-[12px] text-[var(--ink-2)] leading-relaxed">{a.value}</p>
                </div>
              ))}
            </div>
          </section>

          {/* SECTION 4: Locked Engineering Decisions (D-001..D-025) */}
          <section
            id="decisions"
            className="scroll-mt-20 rounded-[8px] border border-[var(--line)] bg-[var(--surface)] p-6 space-y-4"
          >
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
              <div>
                <h2 className="text-lg font-semibold text-[var(--ink)]">
                  Locked Engineering Decisions Ledger
                </h2>
                <p className="text-xs text-[var(--ink-2)]">
                  Immutable architectural choices preserved across all pipelines.
                </p>
              </div>

              <div className="flex items-center px-3 py-1.5 rounded-[8px] border border-[var(--line)] bg-[var(--surface-2)] w-full sm:w-72">
                <Search className="w-3.5 h-3.5 text-[var(--ink-2)] mr-2 shrink-0" />
                <input
                  type="text"
                  value={decisionFilter}
                  onChange={(e) => setDecisionFilter(e.target.value)}
                  placeholder="Search decisions by ID or text..."
                  className="bg-transparent text-xs text-[var(--ink)] placeholder-[var(--ink-2)] focus:outline-none w-full"
                  aria-label="Search decisions"
                />
                {decisionFilter && (
                  <button
                    onClick={() => setDecisionFilter("")}
                    className="text-[var(--ink-2)] hover:text-[var(--ink)] ml-1"
                    aria-label="Clear filter"
                  >
                    <X className="w-3.5 h-3.5" />
                  </button>
                )}
              </div>
            </div>

            <div className="text-xs text-[var(--ink-2)] flex items-center justify-between pt-1">
              <span>Showing {filteredDecisions.length} of {meta.decisions.length} decisions</span>
              {decisionFilter && (
                <button
                  onClick={() => setDecisionFilter("")}
                  className="text-[var(--primary)] hover:underline font-medium"
                >
                  Reset filter
                </button>
              )}
            </div>

            {filteredDecisions.length === 0 ? (
              <div className="p-8 text-center rounded-[8px] border border-dashed border-[var(--line)] text-xs text-[var(--ink-2)] space-y-2">
                <p>No engineering decisions found matching &ldquo;{decisionFilter}&rdquo;.</p>
                <button
                  onClick={() => setDecisionFilter("")}
                  className="px-3 py-1 rounded-[4px] bg-[var(--surface-2)] border border-[var(--line)] text-[var(--ink)] hover:text-[var(--primary)] font-medium"
                >
                  Clear search
                </button>
              </div>
            ) : (
              <div className="divide-y divide-[var(--line)]">
                {filteredDecisions.map((d) => (
                  <div key={d.id} className="py-3 space-y-1 text-xs">
                    <div className="flex items-center space-x-2">
                      <code className="text-xs text-[var(--primary)] font-semibold font-mono">{d.id}:</code>
                      <span className="font-semibold text-[var(--ink)]">{d.title}</span>
                    </div>
                    <p className="text-[12px] text-[var(--ink-2)] leading-relaxed pl-6">{d.description}</p>
                  </div>
                ))}
              </div>
            )}
          </section>

          {/* SECTION 5: Data Licences and Open Science Terms */}
          <section
            id="licences"
            className="scroll-mt-20 rounded-[8px] border border-[var(--line)] bg-[var(--surface)] p-6 space-y-3"
          >
            <div className="flex items-center space-x-2">
              <Scale className="w-5 h-5 text-[var(--primary)] shrink-0" />
              <h2 className="text-lg font-semibold text-[var(--ink)]">
                Data licences and terms of use
              </h2>
            </div>
            <p className="text-xs text-[var(--ink-2)]">
              All data and tools used in ClimateAdapt-Comfort adhere to open-science licensing:
            </p>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3 text-xs pt-1">
              <div className="p-3.5 rounded-[8px] border border-[var(--line)] bg-[var(--surface-2)] space-y-1">
                <span className="font-semibold text-[var(--ink)] block">ASHRAE Global DB II</span>
                <p className="text-[12px] text-[var(--ink-2)] leading-relaxed">
                  Open Database License (ODbL) / ODC-By v1.0. 109,033 field comfort records across global and Indian buildings.
                </p>
              </div>
              <div className="p-3.5 rounded-[8px] border border-[var(--line)] bg-[var(--surface-2)] space-y-1">
                <span className="font-semibold text-[var(--ink)] block">EnergyPlus Simulation</span>
                <p className="text-[12px] text-[var(--ink-2)] leading-relaxed">
                  Open-source BSD 3-Clause licence developed by NREL and U.S. Department of Energy.
                </p>
              </div>
              <div className="p-3.5 rounded-[8px] border border-[var(--line)] bg-[var(--surface-2)] space-y-1">
                <span className="font-semibold text-[var(--ink)] block">CPWD DSR Cost Data</span>
                <p className="text-[12px] text-[var(--ink-2)] leading-relaxed">
                  Government of India Central Public Works Department Delhi Schedule of Rates (public reference).
                </p>
              </div>
              <div className="p-3.5 rounded-[8px] border border-[var(--line)] bg-[var(--surface-2)] space-y-1">
                <span className="font-semibold text-[var(--ink)] block">Survey of India Map Boundary</span>
                <p className="text-[12px] text-[var(--ink-2)] leading-relaxed">
                  Official external boundary via DataMeet Maps under Open Database License (ODbL) v1.0. EPW station coordinates projected using Albers Equal Area Conic.
                </p>
              </div>
            </div>
          </section>

          {/* SECTION 6: Reproduction Commands */}
          <section
            id="reproduction"
            className="scroll-mt-20 rounded-[8px] border border-[var(--line)] bg-[var(--surface)] p-6 space-y-4"
          >
            <div className="flex items-center justify-between gap-3 flex-wrap">
              <div className="flex items-center space-x-2">
                <Terminal className="w-5 h-5 text-[var(--primary)] shrink-0" />
                <h2 className="text-lg font-semibold text-[var(--ink)]">
                  Reproduction pipeline commands
                </h2>
              </div>

              {/* Shell Tabs */}
              <div className="flex items-center space-x-1 p-1 bg-[var(--surface-2)] border border-[var(--line)] rounded-[6px]">
                <button
                  onClick={() => setShellTab("powershell")}
                  className={`py-1 px-3 rounded-[4px] font-medium text-xs transition ${
                    shellTab === "powershell"
                      ? "bg-[var(--surface)] text-[var(--ink)] font-semibold shadow-sm border border-[var(--line)]"
                      : "text-[var(--ink-2)] hover:text-[var(--ink)]"
                  }`}
                >
                  PowerShell (Windows)
                </button>
                <button
                  onClick={() => setShellTab("bash")}
                  className={`py-1 px-3 rounded-[4px] font-medium text-xs transition ${
                    shellTab === "bash"
                      ? "bg-[var(--surface)] text-[var(--ink)] font-semibold shadow-sm border border-[var(--line)]"
                      : "text-[var(--ink-2)] hover:text-[var(--ink)]"
                  }`}
                >
                  Bash (macOS / Linux)
                </button>
              </div>
            </div>

            <p className="text-xs text-[var(--ink-2)]">
              Isolated single-command execution blocks with copy button. Virtual environment paths are matched to each operating system:
            </p>

            <div className="space-y-3">
              {activeCommands.map((step, idx) => {
                const stepKey = `${shellTab}-${idx}`;
                const isCopied = copiedIndex === stepKey;

                return (
                  <div
                    key={idx}
                    className="p-3.5 rounded-[8px] border border-[var(--line)] bg-[var(--surface-2)] space-y-2"
                  >
                    <div className="flex items-center justify-between text-xs">
                      <span className="font-semibold text-[var(--ink)]">
                        {idx + 1}. {step.title}
                      </span>
                      <button
                        onClick={() => handleCopy(step.command, stepKey)}
                        className="inline-flex items-center space-x-1.5 px-2.5 py-1 rounded-[4px] bg-[var(--surface)] border border-[var(--line)] hover:border-[var(--primary)] text-[var(--ink)] hover:text-[var(--primary)] transition text-[11px] font-medium shrink-0"
                        aria-label={`Copy command: ${step.command}`}
                      >
                        {isCopied ? (
                          <>
                            <Check className="w-3.5 h-3.5 text-[var(--good)]" />
                            <span className="text-[var(--good)] font-semibold">Copied!</span>
                          </>
                        ) : (
                          <>
                            <Copy className="w-3.5 h-3.5 text-[var(--ink-2)]" />
                            <span>Copy</span>
                          </>
                        )}
                      </button>
                    </div>

                    <pre className="p-2.5 rounded-[6px] bg-[var(--surface)] border border-[var(--line)] font-mono text-[11px] text-[var(--ink)] overflow-x-auto select-all">
                      <code>{step.command}</code>
                    </pre>
                  </div>
                );
              })}
            </div>
          </section>
        </div>
      </div>
    </div>
  );
}
