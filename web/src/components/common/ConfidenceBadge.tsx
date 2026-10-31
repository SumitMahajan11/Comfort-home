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
        className={`inline-flex items-center space-x-1.5 px-2.5 py-1 rounded-[6px] text-xs font-medium border transition ${
          isMedium
            ? "bg-[var(--warn)]/10 text-[var(--warn)] border-[var(--warn)]/30 hover:bg-[var(--warn)]/20"
            : "bg-[var(--bad)]/10 text-[var(--bad)] border-[var(--bad)]/30 hover:bg-[var(--bad)]/20"
        }`}
        aria-label={`Confidence tier: ${tier}`}
      >
        {isMedium ? (
          <ShieldCheck className="w-3.5 h-3.5 text-[var(--warn)]" />
        ) : (
          <ShieldAlert className="w-3.5 h-3.5 text-[var(--bad)]" />
        )}
        <span>Confidence: {tier}</span>
        {showTooltip && <Info className="w-3 h-3 opacity-60 ml-0.5" />}
      </button>

      {/* Tooltip explaining Decision D-017 */}
      {open && showTooltip && (
        <div className="absolute z-50 bottom-full left-0 mb-2 w-72 p-3 rounded-[8px] bg-[var(--surface)] border border-[var(--line)] shadow-sm text-xs text-[var(--ink)] pointer-events-none">
          <div className="flex items-center space-x-1.5 text-[var(--primary)] font-semibold mb-1">
            <Info className="w-3.5 h-3.5" />
            <span>Decision D-017 Confidence Tier</span>
          </div>
          <p className="text-[var(--ink-2)] leading-relaxed mb-1.5 text-[12px]">
            {reason ||
              (isMedium
                ? "Medium confidence: Good dual-judge rank agreement (r_s ≥ 0.90) and high envelope validity."
                : "Low confidence: Moderate/low dual-judge agreement or sparse training data (e.g. cold-climate extrapolation).")}
          </p>
          {spearman !== undefined && (
            <div className="pt-1 border-t border-[var(--line)] tabular-nums text-[12px] text-[var(--ink-2)] flex justify-between">
              <span>Dual-judge Spearman:</span>
              <span className="text-[var(--ink)] font-semibold">{spearman >= 0 ? `+${spearman.toFixed(3)}` : spearman.toFixed(3)}</span>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default ConfidenceBadge;
