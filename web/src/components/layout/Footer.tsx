"use client";

import React from "react";
import Link from "next/link";
import { ShieldCheck, GitBranch, Cpu, Database, Award, ExternalLink } from "lucide-react";

export const Footer: React.FC = () => {
  return (
    <footer className="w-full border-t border-[var(--line)] bg-[var(--surface-2)] text-[var(--ink-2)] text-xs py-8 mt-10 no-print">
      <div className="max-w-[1280px] mx-auto px-4 sm:px-6 lg:px-8">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-8">
          {/* Col 1: Project Identity */}
          <div className="space-y-3">
            <div className="flex items-center space-x-2">
              <div className="w-3 h-3 rounded-full bg-[var(--primary)] shadow-sm" />
              <span className="font-bold text-sm text-[var(--ink)] tracking-tight">
                ClimateAdapt-Comfort
              </span>
            </div>
            <p className="text-[var(--ink-2)] leading-relaxed text-[12px]">
              Multi-objective decision-support framework integrating ASHRAE DB II field comfort survey models, EnergyPlus building simulation, XGBoost surrogates, and NSGA-II optimization.
            </p>
            <div className="flex items-center space-x-2 text-[12px] text-[var(--primary)]">
              <GitBranch className="w-3.5 h-3.5" />
              <span>Release v1.1.3</span>
            </div>
          </div>

          {/* Col 2: Evidence Gating Contract */}
          <div className="space-y-2">
            <h3 className="font-semibold text-xs text-[var(--ink)]">
              Evidence contract
            </h3>
            <ul className="space-y-1.5 text-[12px]">
              <li className="flex items-center space-x-1.5">
                <ShieldCheck className="w-3.5 h-3.5 text-[var(--good)] shrink-0" />
                <span>Zero fabricated metrics</span>
              </li>
              <li className="flex items-center space-x-1.5">
                <Database className="w-3.5 h-3.5 text-[var(--link)] shrink-0" />
                <span>Raw DB II & weather immutable</span>
              </li>
              <li className="flex items-center space-x-1.5">
                <Cpu className="w-3.5 h-3.5 text-[var(--cool)] shrink-0" />
                <span>Fixed seed 42 reproducible</span>
              </li>
              <li className="flex items-center space-x-1.5">
                <Award className="w-3.5 h-3.5 text-[var(--warn)] shrink-0" />
                <span>Negative results reported honestly (S1 FAIL)</span>
              </li>
            </ul>
          </div>

          {/* Col 3: Research Navigation */}
          <div className="space-y-2">
            <h3 className="font-semibold text-xs text-[var(--ink)]">
              Research links
            </h3>
            <ul className="space-y-1.5 text-[12px]">
              <li>
                <Link href="/recommender" className="hover:text-[var(--primary)] transition">
                  Plan my shelter
                </Link>
              </li>
              <li>
                <Link href="/models" className="hover:text-[var(--primary)] transition">
                  Models & testing
                </Link>
              </li>
              <li>
                <Link href="/about" className="hover:text-[var(--primary)] transition">
                  About & methodology
                </Link>
              </li>
              <li>
                <Link href="/cities" className="hover:text-[var(--primary)] transition">
                  5 Indian climate stations & EPWs
                </Link>
              </li>
              <li>
                <Link href="/pareto" className="hover:text-[var(--primary)] transition">
                  Best trade-off designs (Pareto)
                </Link>
              </li>
              <li>
                <Link href="/explain" className="hover:text-[var(--primary)] transition">
                  SHAP feature explanations
                </Link>
              </li>
            </ul>
          </div>

          {/* Col 4: Licensing & Citation */}
          <div className="space-y-2">
            <h3 className="font-semibold text-xs text-[var(--ink)]">
              Data and open science
            </h3>
            <ul className="space-y-1.5 text-[12px]">
              <li>
                <a
                  href="https://github.com/CenterForTheBuiltEnvironment/ashrae-db-II"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="hover:text-[var(--primary)] transition inline-flex items-center space-x-1"
                >
                  <span>ASHRAE DB II GitHub repo</span>
                  <ExternalLink className="w-3 h-3 opacity-60" />
                </a>
              </li>
              <li>
                <Link href="/about#licences" className="hover:text-[var(--primary)] transition">
                  Data licences & terms
                </Link>
              </li>
            </ul>
            <p className="text-[12px] leading-relaxed text-[var(--ink-2)] pt-1">
              Trained on ASHRAE DB II (ODbL / ODC-By v1.0). EnergyPlus simulated under BSD licence. Educational use only. No paid or cloud APIs.
            </p>
            <div className="pt-2 text-[11px] text-[var(--ink-2)]">
              © 2026 ClimateAdapt-Comfort Team. All verification outputs logged under <code className="text-[var(--ink)]">reports/evidence/</code>.
            </div>
          </div>
        </div>
      </div>
    </footer>
  );
};
export default Footer;
