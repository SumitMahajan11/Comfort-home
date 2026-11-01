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
      className="w-full bg-[var(--surface-2)] border-b border-[var(--warn)]/40 text-[var(--ink)] text-xs px-4 py-2 transition shadow-sm z-40 sticky top-0"
    >
      <div className="max-w-7xl mx-auto flex items-center justify-between">
        <div className="flex items-center space-x-2">
          <ShieldAlert className="w-4 h-4 text-[var(--warn)] shrink-0" />
          <span>
            <strong className="text-[var(--ink)] font-semibold">Scientific Notice:</strong>{" "}
            <span className="text-[var(--ink-2)]">Simulation-based estimate, not a measured result or a construction quote.</span>
          </span>
        </div>

        <button
          onClick={handleDismiss}
          className="text-[var(--ink-2)] hover:text-[var(--ink)] p-1 rounded transition shrink-0 ml-4"
          title="Dismiss banner for this session"
          aria-label="Dismiss banner"
        >
          <X className="w-3.5 h-3.5" />
        </button>
      </div>
    </aside>

  );
};
