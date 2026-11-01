"use client";

import React from "react";
import { AlertTriangle, CheckCircle } from "lucide-react";

export interface ApplicabilityGaugeProps {
  label: string;
  value: number; // 0 to 100
  threshold?: number;
  subtitle?: string;
  className?: string;
}

export const ApplicabilityGauge: React.FC<ApplicabilityGaugeProps> = ({
  label,
  value,
  threshold = 70,
  subtitle,
  className = ""
}) => {
  const isHealthy = value >= threshold;
  const clampedValue = Math.min(100, Math.max(0, value));

  return (
    <div className={`rounded-[8px] border border-[var(--line)] bg-[var(--surface)] p-3.5 space-y-2 ${className}`}>
      <div className="flex items-center justify-between text-xs">
        <span className="text-[var(--ink)] font-medium text-xs">{label}</span>
        <div className="flex items-center space-x-1.5 tabular-nums">
          <span className={`font-semibold text-xs ${isHealthy ? "text-[var(--good)]" : "text-[var(--warn)]"}`}>
            {clampedValue.toFixed(1)}%
          </span>
          {isHealthy ? (
            <CheckCircle className="w-3.5 h-3.5 text-[var(--good)]" />
          ) : (
            <AlertTriangle className="w-3.5 h-3.5 text-[var(--warn)]" />
          )}
        </div>
      </div>

      {/* Progress Track */}
      <div className="w-full h-2 rounded-full bg-[var(--surface-2)] border border-[var(--line)] overflow-hidden relative">
        <div
          className={`h-full rounded-full transition-all duration-500 ${
            isHealthy ? "bg-[var(--good)]" : "bg-[var(--warn)]"
          }`}
          style={{ width: `${clampedValue}%` }}
        />
        {/* Threshold Marker */}
        <div
          className="absolute top-0 bottom-0 w-0.5 bg-[var(--ink-2)] opacity-50"
          style={{ left: `${threshold}%` }}
          title={`Recommended threshold: ${threshold}%`}
        />
      </div>

      {subtitle && (
        <p className="text-[12px] text-[var(--ink-2)] leading-tight">
          {subtitle} {!isHealthy && <span className="text-[var(--warn)] font-medium">(Extrapolation regime)</span>}
        </p>
      )}
    </div>
  );
};

export default ApplicabilityGauge;
