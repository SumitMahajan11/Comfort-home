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
      label: "EnergyPlus Verified",
      color: "bg-emerald-500/15 text-emerald-300 border-emerald-500/30",
      icon: <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />,
      desc: "Simulated directly in EnergyPlus 24.2 with full hourly thermodynamic simulation and verified against surrogate prediction."
    },
    "light verification": {
      label: "Light Verification",
      color: "bg-amber-500/15 text-amber-300 border-amber-500/30",
      icon: <AlertCircle className="w-3.5 h-3.5 text-amber-400" />,
      desc: "Predicted by cross-validated XGBoost surrogate model with high accuracy (R² ≥ 0.95), awaiting physical simulation check."
    },
    estimated: {
      label: "Estimated Model",
      color: "bg-slate-500/15 text-slate-300 border-slate-500/30",
      icon: <HelpCircle className="w-3.5 h-3.5 text-slate-400" />,
      desc: "Approximate interpolation or boundary envelope condition. Use for preliminary conceptual design guidance only."
    }
  }[status] || {
    label: status,
    color: "bg-slate-500/15 text-slate-300 border-slate-500/30",
    icon: <HelpCircle className="w-3.5 h-3.5 text-slate-400" />,
    desc: "Simulation-based result."
  };

  return (
    <div className={`relative inline-block ${className}`}>
      <button
        type="button"
        onClick={() => setOpen(!open)}
        onMouseEnter={() => setOpen(true)}
        onMouseLeave={() => setOpen(false)}
        className={`inline-flex items-center space-x-1.5 px-2.5 py-1 rounded-full text-xs font-semibold font-mono border transition ${config.color}`}
      >
        {config.icon}
        <span>{config.label}</span>
      </button>

      {open && showTooltip && (
        <div className="absolute z-50 bottom-full left-0 mb-2 w-64 p-3 rounded-xl bg-slate-950/95 backdrop-blur-md border border-white/15 shadow-2xl text-[11px] text-slate-200 pointer-events-none">
          <div className="font-bold text-white mb-1">{config.label}</div>
          <p className="text-slate-300 leading-relaxed">{config.desc}</p>
        </div>
      )}
    </div>
  );
};
