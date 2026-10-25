"use client";

import React, { useState, useEffect } from "react";
import { X, ShieldAlert } from "lucide-react";

export const PersistentDisclaimer: React.FC = () => {
  const [dismissed, setDismissed] = useState(true);

  useEffect(() => {
    try {
      const isDismissed = sessionStorage.getItem("simulation_banner_dismissed");
      if (!isDismissed) {
        setDismissed(false);
      }
    } catch {
      setDismissed(false);
    }
  }, []);

  const handleDismiss = () => {
    setDismissed(true);
    try {
      sessionStorage.setItem("simulation_banner_dismissed", "true");
    } catch {}
  };

  if (dismissed) return null;

  return (
    <aside
      aria-label="Simulation Notice"
      className="w-full bg-navy-950/90 backdrop-blur-2xl border-b border-amber-500/30 text-amber-200 text-xs px-4 py-2 transition shadow-[0_4px_20px_rgba(245,158,11,0.15)] z-40 sticky top-0"
    >
      <div className="max-w-7xl mx-auto flex items-center justify-between">
        <div className="flex items-center space-x-2">
          <ShieldAlert className="w-4 h-4 text-amber-400 shrink-0 animate-pulse" />
          <span>
            <strong className="text-white font-semibold">Scientific Notice:</strong>{" "}
            Simulation-based estimate, not a measured result or a construction quote.
          </span>
        </div>

        <button
          onClick={handleDismiss}
          className="text-amber-400 hover:text-white p-1 rounded transition shrink-0 ml-4"
          title="Dismiss banner for this session"
          aria-label="Dismiss banner"
        >
          <X className="w-3.5 h-3.5" />
        </button>
      </div>
    </aside>
  );
};
