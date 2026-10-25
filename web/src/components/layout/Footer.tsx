"use client";

import React from "react";
import Link from "next/link";
import { ShieldCheck, GitBranch, Cpu, Database, Award } from "lucide-react";

export const Footer: React.FC = () => {
  return (
    <footer className="w-full border-t border-slate-800 bg-slate-950 text-slate-400 text-xs py-10 mt-20 no-print">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-8">
          {/* Col 1: Project Identity */}
          <div className="space-y-3">
            <div className="flex items-center space-x-2">
              <div className="w-3 h-3 rounded-full bg-teal-400 shadow-sm" />
              <span className="font-bold text-sm text-white tracking-tight">
                ClimateAdapt-Comfort
              </span>
            </div>
            <p className="text-slate-400 leading-relaxed text-[11px]">
              Multi-objective decision-support framework integrating ASHRAE DB II field comfort survey models, EnergyPlus building simulation, XGBoost surrogates, and NSGA-II optimization.
            </p>
            <div className="flex items-center space-x-2 text-[10px] font-mono text-teal-400">
              <GitBranch className="w-3.5 h-3.5" />
              <span>Release v1.1.3 (Frozen Audit Benchmark)</span>
            </div>
          </div>

          {/* Col 2: Evidence Gating Contract */}
          <div className="space-y-2">
            <h5 className="font-semibold text-xs text-white uppercase tracking-wider font-mono">
              Evidence Contract
            </h5>
            <ul className="space-y-1.5 text-[11px]">
              <li className="flex items-center space-x-1.5">
                <ShieldCheck className="w-3.5 h-3.5 text-emerald-400 shrink-0" />
                <span>Zero fabricated metrics (Rule 1)</span>
              </li>
              <li className="flex items-center space-x-1.5">
                <Database className="w-3.5 h-3.5 text-teal-400 shrink-0" />
                <span>Raw DB II & weather immutable</span>
              </li>
              <li className="flex items-center space-x-1.5">
                <Cpu className="w-3.5 h-3.5 text-blue-400 shrink-0" />
                <span>Fixed seed 42 reproducible</span>
              </li>
              <li className="flex items-center space-x-1.5">
                <Award className="w-3.5 h-3.5 text-amber-400 shrink-0" />
                <span>Negative results reported honestly (S1 FAIL)</span>
              </li>
            </ul>
          </div>

          {/* Col 3: Research Navigation */}
          <div className="space-y-2">
            <h5 className="font-semibold text-xs text-white uppercase tracking-wider font-mono">
              Research Links
            </h5>
            <ul className="space-y-1.5 text-[11px]">
              <li>
                <Link href="/cities" className="hover:text-teal-300 transition">
                  5 Indian Climate Stations & EPW
                </Link>
              </li>
              <li>
                <Link href="/pareto" className="hover:text-teal-300 transition">
                  Pareto Frontiers & Verified Designs
                </Link>
              </li>
              <li>
                <Link href="/explain" className="hover:text-teal-300 transition">
                  TreeExplainer SHAP Feature Impacts
                </Link>
              </li>
              <li>
                <Link href="/models" className="hover:text-teal-300 transition">
                  Comfort Model Leaderboard & Surrogates
                </Link>
              </li>
              <li>
                <Link href="/about" className="hover:text-teal-300 transition">
                  Locked Decisions D-001..D-019
                </Link>
              </li>
            </ul>
          </div>

          {/* Col 4: Licensing & Citation */}
          <div className="space-y-2">
            <h5 className="font-semibold text-xs text-white uppercase tracking-wider font-mono">
              Data & Ethics
            </h5>
            <p className="text-[11px] leading-relaxed">
              Trained on ASHRAE DB II (ODbL / ODC-By v1.0). EnergyPlus simulated under BSD licence. Educational use only. No paid or cloud APIs.
            </p>
            <div className="pt-2 text-[10px] text-slate-500">
              © 2026 ClimateAdapt-Comfort Team. All verification outputs logged under <code className="text-slate-400">reports/evidence/</code>.
            </div>
          </div>
        </div>
      </div>
    </footer>
  );
};
