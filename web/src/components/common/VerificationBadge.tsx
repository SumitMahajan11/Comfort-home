"use client";

import React, { useState } from "react";
import { CheckCircle2, AlertCircle, HelpCircle } from "lucide-react";

export type VerificationStatus = "verified" | "light verification" | "estimated";

export interface VerificationBadgeProps {
  status: VerificationStatus;
  className?: string;
  showTooltip?: boolean;
}

export const VerificationBadge: React.FC<VerificationBadgeProps> = ({
  status,
  className = "",
  showTooltip = true
}) => {
  const [open, setOpen] = useState(false);

  const config = {
    verified: {
      label: "EnergyPlus verified",
      color: "bg-[var(--good)]/10 text-[var(--good)] border-[var(--good)]/30",
      icon: <CheckCircle2 className="w-3.5 h-3.5 text-[var(--good)]" />,
      desc: "Simulated directly in EnergyPlus 24.2 with full hourly thermodynamic simulation and verified against surrogate prediction."
    },
    "light verification": {
      label: "Light verification",
      color: "bg-[var(--warn)]/10 text-[var(--warn)] border-[var(--warn)]/30",
      icon: <AlertCircle className="w-3.5 h-3.5 text-[var(--warn)]" />,
      desc: "Predicted by cross-validated XGBoost surrogate model with high accuracy (R² ≥ 0.95), awaiting physical simulation check."
    },
    estimated: {
      label: "Estimated model",
      color: "bg-[var(--surface-2)] text-[var(--ink-2)] border-[var(--line)]",
      icon: <HelpCircle className="w-3.5 h-3.5 text-[var(--ink-2)]" />,
      desc: "Approximate interpolation or boundary envelope condition. Use for preliminary conceptual design guidance only."
    }
  }[status] || {
    label: status,
    color: "bg-[var(--surface-2)] text-[var(--ink-2)] border-[var(--line)]",
    icon: <HelpCircle className="w-3.5 h-3.5 text-[var(--ink-2)]" />,
    desc: "Simulation-based result."
  };

  return (
    <div className={`relative inline-block ${className}`}>
      <button
        type="button"
        onClick={() => setOpen(!open)}
        onMouseEnter={() => setOpen(true)}
        onMouseLeave={() => setOpen(false)}
        className={`inline-flex items-center space-x-1.5 px-2.5 py-1 rounded-[6px] text-xs font-medium border transition ${config.color}`}
      >
        {config.icon}
        <span>{config.label}</span>
      </button>

      {open && showTooltip && (
        <div className="absolute z-50 bottom-full left-0 mb-2 w-64 p-3 rounded-[8px] bg-[var(--surface)] border border-[var(--line)] shadow-sm text-xs text-[var(--ink)] pointer-events-none">
          <div className="font-semibold text-[var(--ink)] mb-1">{config.label}</div>
          <p className="text-[var(--ink-2)] text-[12px] leading-relaxed">{config.desc}</p>
        </div>
      )}
    </div>
  );
};

export default VerificationBadge;
