"use client";

import React, { useState } from "react";
import { ShieldCheck, ShieldAlert, Info } from "lucide-react";

export interface ConfidenceBadgeProps {
  tier: "Medium" | "Low" | string;
  reason?: string;
  spearman?: number;
  className?: string;
  showTooltip?: boolean;
}

export const ConfidenceBadge: React.FC<ConfidenceBadgeProps> = ({
  tier,
  reason,
  spearman,
  className = "",
  showTooltip = true
}) => {
  const [open, setOpen] = useState(false);
  const isMedium = tier === "Medium";

  return (
    <div className={`relative inline-block ${className}`}>
      <button
        type="button"
        onClick={() => setOpen(!open)}
        onMouseEnter={() => setOpen(true)}
        onMouseLeave={() => setOpen(false)}
        className={`inline-flex items-center space-x-1.5 px-2.5 py-1 rounded-full text-xs font-semibold font-mono border transition ${
          isMedium
            ? "bg-amber-500/15 text-amber-300 border-amber-500/30 hover:bg-amber-500/25"
            : "bg-rose-500/15 text-rose-300 border-rose-500/30 hover:bg-rose-500/25"
        }`}
        aria-label={`Confidence tier: ${tier}`}
      >
        {isMedium ? (
          <ShieldCheck className="w-3.5 h-3.5 text-amber-400" />
        ) : (
          <ShieldAlert className="w-3.5 h-3.5 text-rose-400" />
        )}
        <span>Confidence: {tier}</span>
        {showTooltip && <Info className="w-3 h-3 opacity-60 ml-0.5" />}
      </button>

      {/* Tooltip explaining Decision D-017 */}
      {open && showTooltip && (
        <div className="absolute z-50 bottom-full left-0 mb-2 w-72 p-3 rounded-xl bg-slate-950/95 backdrop-blur-md border border-white/15 shadow-2xl text-[11px] text-slate-200 pointer-events-none">
          <div className="flex items-center space-x-1.5 text-teal-300 font-bold mb-1">
            <Info className="w-3.5 h-3.5" />
            <span>Decision D-017 Confidence Tier</span>
          </div>
          <p className="text-slate-300 leading-relaxed mb-1.5">
            {reason ||
              (isMedium
                ? "Medium confidence: Good dual-judge rank agreement (r_s ≥ 0.90) and high envelope validity."
                : "Low confidence: Moderate/low dual-judge agreement or sparse training data (e.g. cold-climate extrapolation).")}
          </p>
          {spearman !== undefined && (
            <div className="pt-1 border-t border-white/10 font-mono text-[10px] text-slate-400 flex justify-between">
              <span>Dual-Judge Spearman:</span>
              <span className="text-teal-300 font-bold">{spearman >= 0 ? `+${spearman.toFixed(3)}` : spearman.toFixed(3)}</span>
            </div>
          )}
        </div>
      )}
    </div>
  );
};
