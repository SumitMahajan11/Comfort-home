"use client";

import React, { useState } from "react";
import { SuccessCriterion } from "@/types";
import { CheckCircle2, AlertCircle, XCircle, ChevronDown, ChevronUp, FileText } from "lucide-react";

interface CriteriaScorecardProps {
  criteria: SuccessCriterion[];
  className?: string;
}

export const CriteriaScorecard: React.FC<CriteriaScorecardProps> = ({
  criteria = [],
  className = ""
}) => {
  const [expandedId, setExpandedId] = useState<string | null>(null);

  const toggleExpand = (id: string) => {
    setExpandedId((prev) => (prev === id ? null : id));
  };

  const getStatusBadge = (status: "PASS" | "PARTIAL" | "FAIL") => {
    switch (status) {
      case "PASS":
        return (
          <span className="inline-flex items-center space-x-1.5 px-3 py-1 rounded-full text-xs font-bold bg-emerald-500/15 text-emerald-300 border border-emerald-400/40 shadow-[0_0_12px_rgba(16,185,129,0.25),inset_0_1px_0_rgba(255,255,255,0.2)]">
            <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
            <span>PASS</span>
          </span>
        );
      case "PARTIAL":
        return (
          <span className="inline-flex items-center space-x-1.5 px-3 py-1 rounded-full text-xs font-bold bg-amber-500/15 text-amber-300 border border-amber-400/40 shadow-[0_0_12px_rgba(245,158,11,0.25),inset_0_1px_0_rgba(255,255,255,0.2)]">
            <AlertCircle className="w-3.5 h-3.5 text-amber-400" />
            <span>PARTIAL (23/25)</span>
          </span>
        );
      case "FAIL":
        return (
          <span className="inline-flex items-center space-x-1.5 px-3 py-1 rounded-full text-xs font-bold bg-rose-500/15 text-rose-300 border border-rose-400/40 shadow-[0_0_12px_rgba(239,68,68,0.25),inset_0_1px_0_rgba(255,255,255,0.2)]">
            <XCircle className="w-3.5 h-3.5 text-rose-400" />
            <span>FAIL (Negative Result)</span>
          </span>
        );
    }
  };

  const list = criteria || [];

  return (
    <div className={`grid grid-cols-1 md:grid-cols-2 gap-4 ${className}`}>
      {list.map((c) => {
        const isExpanded = expandedId === c.id;

        return (
          <div
            key={c.id}
            className="rounded-2xl glass-card p-5 flex flex-col justify-between"
          >
            <div>
              <div className="flex items-center justify-between">
                <span className="text-xs font-mono font-bold text-teal-400 tracking-wider">
                  Criterion {c.id}
                </span>
                {getStatusBadge(c.status)}
              </div>

              <h4 className="text-base font-semibold text-white mt-1.5 leading-snug">
                {c.name}
              </h4>

              <p className="text-xs text-slate-300 mt-1 line-clamp-2">
                {c.threshold}
              </p>
            </div>

            {/* Quick Evidence Highlight */}
            <div className="mt-3 pt-3 border-t border-slate-800/80 flex items-center justify-between text-xs">
              <span className="font-mono text-slate-400 flex items-center space-x-1">
                <FileText className="w-3 h-3 text-slate-400" />
                <span>Evidence: <strong className="text-slate-200">[{c.evidence}]</strong></span>
              </span>

              <button
                onClick={() => toggleExpand(c.id)}
                className="text-teal-400 hover:text-teal-300 font-medium inline-flex items-center space-x-1 transition text-xs"
              >
                <span>{isExpanded ? "Less" : "Explanation"}</span>
                {isExpanded ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
              </button>
            </div>

            {/* Expandable Explanation Details */}
            {isExpanded && (
              <div className="mt-3 pt-3 border-t border-slate-800 text-xs text-slate-300 leading-relaxed bg-slate-950/40 p-3 rounded-lg border border-slate-800">
                <p>{c.explanation}</p>
                {c.id === "S1" && (
                  <div className="mt-2 font-mono text-[11px] grid grid-cols-2 gap-1 text-slate-300">
                    <div>ML Champion: <strong className="text-white">0.4785 F1</strong></div>
                    <div>Adaptive 90%: <strong className="text-white">0.4939 F1</strong></div>
                    <div className="col-span-2 text-rose-300">Margin: -0.0154 (did not meet +0.05 threshold)</div>
                  </div>
                )}
                {c.id === "S2" && (
                  <div className="mt-2 font-mono text-[11px] text-slate-300">
                    <div>Mean O2 Energy R²: <strong className="text-white">0.987</strong></div>
                    <div className="text-amber-300">Under 0.95: Mumbai O1_ml (0.9406), Shimla warm_ml (0.9225)</div>
                  </div>
                )}
                {c.id === "S3" && (
                  <div className="mt-2 font-mono text-[11px] text-emerald-300">
                    36 of 50 verified designs beat both R1 and R2 across all 3 objectives in direct EnergyPlus runs.
                  </div>
                )}
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
};
