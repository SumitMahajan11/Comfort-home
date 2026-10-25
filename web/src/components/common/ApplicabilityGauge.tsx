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
    <div className={`rounded-xl glass-panel p-3.5 space-y-2 ${className}`}>
      <div className="flex items-center justify-between text-xs">
        <span className="font-mono text-slate-300 font-medium">{label}</span>
        <div className="flex items-center space-x-1.5 font-mono">
          <span className={`font-bold ${isHealthy ? "text-emerald-400" : "text-amber-400"}`}>
            {clampedValue.toFixed(1)}%
          </span>
          {isHealthy ? (
            <CheckCircle className="w-3.5 h-3.5 text-emerald-400" />
          ) : (
            <AlertTriangle className="w-3.5 h-3.5 text-amber-400" />
          )}
        </div>
      </div>

      {/* Progress Track */}
      <div className="w-full h-2 rounded-full bg-white/10 overflow-hidden relative">
        <div
          className={`h-full rounded-full transition-all duration-500 ${
            isHealthy
              ? "bg-gradient-to-r from-teal-500 to-emerald-400"
              : "bg-gradient-to-r from-amber-500 to-rose-400"
          }`}
          style={{ width: `${clampedValue}%` }}
        />
        {/* Threshold Marker */}
        <div
          className="absolute top-0 bottom-0 w-0.5 bg-white/40"
          style={{ left: `${threshold}%` }}
          title={`Recommended threshold: ${threshold}%`}
        />
      </div>

      {subtitle && (
        <p className="text-[10px] text-slate-400 leading-tight">
          {subtitle} {!isHealthy && <span className="text-amber-300 font-semibold">(Extrapolation regime)</span>}
        </p>
      )}
    </div>
  );
};
