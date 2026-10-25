"use client";

import React, { useState } from "react";
import { X, ShieldAlert, AlertTriangle, FileText, CheckCircle2, ExternalLink } from "lucide-react";

export interface LimitationsDrawerProps {
  buttonText?: string;
  className?: string;
}

export const LimitationsDrawer: React.FC<LimitationsDrawerProps> = ({
  buttonText = "View Scientific Limitations & Evidence",
  className = ""
}) => {
  const [isOpen, setIsOpen] = useState(false);

  return (
    <>
      <button
        type="button"
        onClick={() => setIsOpen(true)}
        className={`inline-flex items-center space-x-1.5 px-3 py-1.5 rounded-xl border border-amber-500/30 bg-amber-950/20 hover:bg-amber-950/40 text-amber-300 text-xs font-semibold transition ${className}`}
      >
        <ShieldAlert className="w-3.5 h-3.5 text-amber-400" />
        <span>{buttonText}</span>
      </button>

      {isOpen && (
        <div className="fixed inset-0 z-50 flex justify-end bg-black/70 backdrop-blur-sm animate-fadeIn">
          {/* Backdrop Click */}
          <div className="absolute inset-0" onClick={() => setIsOpen(false)} />

          {/* Drawer Content */}
          <aside className="relative z-10 w-full max-w-xl h-full bg-slate-950 border-l border-white/10 shadow-2xl p-6 overflow-y-auto space-y-6">
            <div className="flex items-center justify-between border-b border-white/10 pb-4">
              <div className="flex items-center space-x-2.5">
                <div className="p-2 rounded-xl bg-amber-500/20 text-amber-300 border border-amber-500/30">
                  <ShieldAlert className="w-5 h-5 text-amber-400" />
                </div>
                <div>
                  <h3 className="text-base font-bold text-white">Project Scope & Scientific Limitations</h3>
                  <p className="text-xs text-slate-400">Non-negotiable disclosures and evidence records</p>
                </div>
              </div>
              <button
                onClick={() => setIsOpen(false)}
                className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-white/10 transition"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Core Honest Disclosures */}
            <div className="space-y-4 text-xs">
              {/* Disclosure 1 */}
              <div className="rounded-xl border border-amber-500/30 bg-amber-950/20 p-4 space-y-2">
                <div className="flex items-center space-x-2 text-amber-300 font-bold">
                  <AlertTriangle className="w-4 h-4 text-amber-400" />
                  <span>5 Representative Cities Only (Decision D-001)</span>
                </div>
                <p className="text-slate-300 leading-relaxed">
                  EnergyPlus thermodynamic simulations were precomputed exclusively for Jodhpur, Mumbai, New Delhi, Bengaluru, and Shimla. When selecting any other Indian location, the application identifies the geographically nearest station via Haversine distance and flags this clearly as a proxy match.
                </p>
              </div>

              {/* Disclosure 2 */}
              <div className="rounded-xl border border-rose-500/30 bg-rose-950/20 p-4 space-y-2">
                <div className="flex items-center space-x-2 text-rose-300 font-bold">
                  <AlertTriangle className="w-4 h-4 text-rose-400" />
                  <span>Dual Comfort Judge Divergence (Phase S1 Audit: FAIL)</span>
                </div>
                <p className="text-slate-300 leading-relaxed">
                  ASHRAE 55 Adaptive 90% achieved macro-F1 of 0.4939 against physical sensation votes, while the ML thermal classifier achieved 0.4785. The two judges diverge significantly in cold climates (Spearman rank correlation r_s = -0.09 in Shimla). Both judges are shown side-by-side to prevent misleading consensus.
                </p>
                <div className="font-mono text-[10px] text-slate-400">
                  Evidence: reports/evidence/phase1_dual_judge_eval.txt
                </div>
              </div>

              {/* Disclosure 3 */}
              <div className="rounded-xl border border-amber-500/30 bg-amber-950/20 p-4 space-y-2">
                <div className="flex items-center space-x-2 text-amber-300 font-bold">
                  <AlertTriangle className="w-4 h-4 text-amber-400" />
                  <span>Shimla Sensation Vote Gap (Decision D-011)</span>
                </div>
                <p className="text-slate-300 leading-relaxed">
                  All 460 DB II records in Shimla lack occupant thermal sensation votes. Model predictions in Shimla represent cold-climate extrapolation, and ASHRAE 55 Adaptive is invalid during sub-10°C hours (26.0% of annual hours).
                </p>
              </div>

              {/* Disclosure 4 */}
              <div className="rounded-xl border border-white/10 bg-white/[0.02] p-4 space-y-2">
                <div className="flex items-center space-x-2 text-teal-300 font-bold">
                  <FileText className="w-4 h-4 text-teal-400" />
                  <span>CPWD DSR Cost Ranges (Decision D-025)</span>
                </div>
                <p className="text-slate-300 leading-relaxed">
                  All cost estimates are early-stage exploratory approximations based on CPWD Delhi Schedule of Rates (DSR). Unpopulated items in official schedules are explicitly noted as null rather than fabricated. These estimates are NOT construction contractor bids or quotes.
                </p>
              </div>

              {/* Disclosure 5 */}
              <div className="rounded-xl border border-white/10 bg-white/[0.02] p-4 space-y-2">
                <div className="flex items-center space-x-2 text-teal-300 font-bold">
                  <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                  <span>Simulation Assumptions A-001 through A-007</span>
                </div>
                <ul className="list-disc pl-4 space-y-1 text-slate-300">
                  <li>24-hour continuous residential occupancy assumption</li>
                  <li>Metabolic rate fixed at 1.1 met (light seated domestic activity)</li>
                  <li>Indoor air velocity 0.15 m/s still air baseline</li>
                  <li>Adaptive clothing model (0.5 clo summer, 1.0 clo winter)</li>
                  <li>Ideal-loads dual setpoints: cooling at 26°C, heating at 20°C</li>
                </ul>
              </div>
            </div>

            <div className="pt-4 border-t border-white/10 flex justify-between items-center text-xs">
              <span className="text-slate-400 font-mono">Seed: 42 fixed | Zero live cloud API calls</span>
              <button
                onClick={() => setIsOpen(false)}
                className="px-4 py-2 rounded-xl bg-teal-500 text-slate-950 font-bold hover:bg-teal-400 transition"
              >
                Close Disclosures
              </button>
            </div>
          </aside>
        </div>
      )}
    </>
  );
};
