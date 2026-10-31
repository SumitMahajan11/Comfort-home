"use client";

import React, { useState } from "react";
import { X, ShieldAlert, AlertTriangle, FileText, CheckCircle2 } from "lucide-react";

export interface LimitationsDrawerProps {
  buttonText?: string;
  className?: string;
}

export const LimitationsDrawer: React.FC<LimitationsDrawerProps> = ({
  buttonText = "View scientific limitations & evidence",
  className = ""
}) => {
  const [isOpen, setIsOpen] = useState(false);

  return (
    <>
      <button
        type="button"
        onClick={() => setIsOpen(true)}
        className={`inline-flex items-center space-x-1.5 px-3 py-1.5 rounded-[8px] border border-[var(--line)] bg-[var(--surface-2)] hover:bg-[var(--surface)] text-[var(--ink)] text-xs font-medium transition ${className}`}
      >
        <ShieldAlert className="w-3.5 h-3.5 text-[var(--warn)]" />
        <span>{buttonText}</span>
      </button>

      {isOpen && (
        <div className="fixed inset-0 z-50 flex justify-end bg-black/40 backdrop-blur-sm animate-fadeIn">
          {/* Backdrop Click */}
          <div className="absolute inset-0" onClick={() => setIsOpen(false)} />

          {/* Drawer Content */}
          <aside className="relative z-10 w-full max-w-xl h-full bg-[var(--surface)] border-l border-[var(--line)] shadow-lg p-6 overflow-y-auto space-y-6">
            <div className="flex items-center justify-between border-b border-[var(--line)] pb-4">
              <div className="flex items-center space-x-2.5">
                <div className="p-2 rounded-[8px] bg-[var(--surface-2)] text-[var(--warn)] border border-[var(--line)]">
                  <ShieldAlert className="w-5 h-5 text-[var(--warn)]" />
                </div>
                <div>
                  <h3 className="text-base font-semibold text-[var(--ink)]">Project scope & scientific limitations</h3>
                  <p className="text-xs text-[var(--ink-2)]">Non-negotiable disclosures and evidence records</p>
                </div>
              </div>
              <button
                onClick={() => setIsOpen(false)}
                className="p-1.5 rounded-[8px] text-[var(--ink-2)] hover:text-[var(--ink)] hover:bg-[var(--surface-2)] transition"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Core Honest Disclosures */}
            <div className="space-y-4 text-xs">
              {/* Disclosure 1 */}
              <div className="rounded-[8px] border border-[var(--line)] bg-[var(--surface-2)] p-4 space-y-2">
                <div className="flex items-center space-x-2 text-[var(--ink)] font-semibold">
                  <AlertTriangle className="w-4 h-4 text-[var(--warn)]" />
                  <span>5 Representative cities only (Decision D-001)</span>
                </div>
                <p className="text-[var(--ink-2)] leading-relaxed">
                  EnergyPlus thermodynamic simulations were precomputed exclusively for Jodhpur, Mumbai, New Delhi, Bengaluru, and Shimla. When selecting any other Indian location, the application identifies the geographically nearest station via Haversine distance and flags this clearly as a proxy match.
                </p>
              </div>

              {/* Disclosure 2 */}
              <div className="rounded-[8px] border border-[var(--line)] bg-[var(--surface-2)] p-4 space-y-2">
                <div className="flex items-center space-x-2 text-[var(--ink)] font-semibold">
                  <AlertTriangle className="w-4 h-4 text-[var(--bad)]" />
                  <span>Dual comfort judge divergence (Phase S1 audit: FAIL)</span>
                </div>
                <p className="text-[var(--ink-2)] leading-relaxed">
                  ASHRAE 55 Adaptive 90% achieved macro-F1 of 0.4939 against physical sensation votes, while the ML thermal classifier achieved 0.4785. The two judges diverge significantly in cold climates (Spearman rank correlation r_s = -0.09 in Shimla). Both judges are shown side-by-side to prevent misleading consensus.
                </p>
                <div className="text-xs text-[var(--ink-2)]">
                  Evidence: <code>reports/evidence/phase1_dual_judge_eval.txt</code>
                </div>
              </div>

              {/* Disclosure 3 */}
              <div className="rounded-[8px] border border-[var(--line)] bg-[var(--surface-2)] p-4 space-y-2">
                <div className="flex items-center space-x-2 text-[var(--ink)] font-semibold">
                  <AlertTriangle className="w-4 h-4 text-[var(--warn)]" />
                  <span>Shimla sensation vote gap (Decision D-011)</span>
                </div>
                <p className="text-[var(--ink-2)] leading-relaxed">
                  All 460 DB II records in Shimla lack occupant thermal sensation votes. Model predictions in Shimla represent cold-climate extrapolation, and ASHRAE 55 Adaptive is invalid during sub-10°C hours (26.0% of annual hours).
                </p>
              </div>

              {/* Disclosure 4 */}
              <div className="rounded-[8px] border border-[var(--line)] bg-[var(--surface-2)] p-4 space-y-2">
                <div className="flex items-center space-x-2 text-[var(--ink)] font-semibold">
                  <FileText className="w-4 h-4 text-[var(--link)]" />
                  <span>CPWD DSR cost ranges (Decision D-025)</span>
                </div>
                <p className="text-[var(--ink-2)] leading-relaxed">
                  All cost estimates are early-stage exploratory approximations based on CPWD Delhi Schedule of Rates (DSR). Unpopulated items in official schedules are explicitly noted as null rather than fabricated. These estimates are NOT construction contractor bids or quotes.
                </p>
              </div>

              {/* Disclosure 5 */}
              <div className="rounded-[8px] border border-[var(--line)] bg-[var(--surface-2)] p-4 space-y-2">
                <div className="flex items-center space-x-2 text-[var(--ink)] font-semibold">
                  <CheckCircle2 className="w-4 h-4 text-[var(--good)]" />
                  <span>Simulation assumptions A-001 through A-007</span>
                </div>
                <ul className="list-disc pl-4 space-y-1 text-[var(--ink-2)]">
                  <li>24-hour continuous residential occupancy assumption</li>
                  <li>Metabolic rate fixed at 1.1 met (light seated domestic activity)</li>
                  <li>Indoor air velocity 0.15 m/s still air baseline</li>
                  <li>Adaptive clothing model (0.5 clo summer, 1.0 clo winter)</li>
                  <li>Ideal-loads dual setpoints: cooling at 26°C, heating at 20°C</li>
                </ul>
              </div>
            </div>

            <div className="pt-4 border-t border-[var(--line)] flex justify-between items-center text-xs">
              <span className="text-[var(--ink-2)]">Seed: 42 fixed | Zero live cloud API calls</span>
              <button
                onClick={() => setIsOpen(false)}
                className="px-4 py-2 rounded-[8px] bg-[var(--primary)] text-white font-medium hover:opacity-90 transition"
              >
                Close disclosures
              </button>
            </div>
          </aside>
        </div>
      )}
    </>
  );
};

export default LimitationsDrawer;
