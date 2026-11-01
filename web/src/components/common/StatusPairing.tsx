"use client";

import React from "react";
import { CheckCircle2 } from "lucide-react";
import { Tooltip } from "@/components/ui/Tooltip";

export interface StatusPairingProps {
  confidenceTier: "Medium" | "Low" | string;
  isVerified?: boolean;
  reason?: string;
  className?: string;
}

export const StatusPairing: React.FC<StatusPairingProps> = ({
  confidenceTier,
  isVerified = true,
  reason,
  className = ""
}) => {
  const isLow = confidenceTier === "Low";
  const defaultLowReason =
    reason ||
    "Sparse regional field survey data in DB II or moderate dual-judge agreement. Recommendations should be treated as directional guidance rather than exact predictions.";

  if (isVerified && isLow) {
    return (
      <div
        className={`inline-flex items-center space-x-1.5 px-3 py-1 rounded-[6px] text-xs border bg-[var(--surface-2)] border-[var(--line)] text-[var(--ink)] ${className}`}
      >
        <CheckCircle2 className="w-3.5 h-3.5 text-[var(--good)] shrink-0" />
        <span>Verified by simulation</span>
        <span className="text-[var(--ink-2)]">·</span>
        <span className="text-[var(--warn)] font-medium">Comfort estimate is low-confidence here</span>
        <Tooltip
          content={
            <div className="space-y-1 p-1 max-w-xs">
              <div className="font-semibold text-[var(--ink)]">Why is confidence low?</div>
              <p className="text-[12px] text-[var(--ink-2)] leading-relaxed">
                {defaultLowReason}
              </p>
            </div>
          }
        >
          <button
            type="button"
            className="text-[var(--primary)] underline hover:opacity-80 font-medium ml-0.5 focus:outline-none"
            aria-label="Why is comfort estimate low-confidence here?"
          >
            (why?)
          </button>
        </Tooltip>
      </div>
    );
  }

  return (
    <div
      className={`inline-flex items-center space-x-1.5 px-3 py-1 rounded-[6px] text-xs border bg-[var(--surface-2)] border-[var(--line)] text-[var(--ink)] ${className}`}
    >
      {isVerified && (
        <>
          <CheckCircle2 className="w-3.5 h-3.5 text-[var(--good)] shrink-0" />
          <span>Verified by simulation</span>
        </>
      )}
      {isVerified && confidenceTier && <span className="text-[var(--ink-2)]">·</span>}
      {confidenceTier && (
        <span className={isLow ? "text-[var(--warn)] font-medium" : "text-[var(--ink)]"}>
          {confidenceTier} confidence
        </span>
      )}
    </div>
  );
};

export default StatusPairing;
