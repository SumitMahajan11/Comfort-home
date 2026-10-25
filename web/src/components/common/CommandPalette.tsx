"use client";

import React, { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { Search, MapPin, Sliders, Layers, HelpCircle, Activity, Sparkles, X } from "lucide-react";
import { CITIES_DATA } from "@/lib/constants";
import { CityKey } from "@/types";

interface CommandPaletteProps {
  isOpen: boolean;
  onClose: () => void;
  onSelectCity?: (city: CityKey) => void;
}

interface CommandItem {
  id: string;
  category: "Pages" | "Cities" | "Presets" | "Decisions";
  title: string;
  subtitle: string;
  action: () => void;
  icon: React.ReactNode;
}

export const CommandPalette: React.FC<CommandPaletteProps> = ({
  isOpen,
  onClose,
  onSelectCity
}) => {
  const router = useRouter();
  const [query, setQuery] = useState("");
  const [selectedIndex, setSelectedIndex] = useState(0);

  // Keyboard shortcut listener for Cmd+K / Ctrl+K
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === "k") {
        e.preventDefault();
        if (isOpen) onClose();
      } else if (e.key === "Escape" && isOpen) {
        onClose();
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [isOpen, onClose]);

  const allItems: CommandItem[] = [
    // Pages
    {
      id: "page-overview",
      category: "Pages",
      title: "Overview & Evidence Scorecard",
      subtitle: "Headline KPIs, India climate map, S1-S4 success criteria",
      action: () => { router.push("/"); onClose(); },
      icon: <Activity className="w-4 h-4 text-teal-400" />
    },
    {
      id: "page-cities",
      category: "Pages",
      title: "City Explorer",
      subtitle: "5 Indian climate zones, EPW weather files & applicability gauges",
      action: () => { router.push("/cities"); onClose(); },
      icon: <MapPin className="w-4 h-4 text-teal-400" />
    },
    {
      id: "page-evaluate",
      category: "Pages",
      title: "Evaluate a Design",
      subtitle: "8 variable sliders, live surrogate predictions, R1/R2 comparison & 3D shelter",
      action: () => { router.push("/evaluate"); onClose(); },
      icon: <Sliders className="w-4 h-4 text-teal-400" />
    },
    {
      id: "page-pareto",
      category: "Pages",
      title: "Pareto Explorer (Flagship)",
      subtitle: "Multi-objective 3D frontier, 100 designs/city, direct verification & presets",
      action: () => { router.push("/pareto"); onClose(); },
      icon: <Layers className="w-4 h-4 text-teal-400" />
    },
    {
      id: "page-explain",
      category: "Pages",
      title: "Explain (SHAP Attribution)",
      subtitle: "Global & local feature impacts, physical drivers, sensitivity heatmap",
      action: () => { router.push("/explain"); onClose(); },
      icon: <Sparkles className="w-4 h-4 text-teal-400" />
    },
    {
      id: "page-models",
      category: "Pages",
      title: "Model Lab",
      subtitle: "Comfort model leaderboard (macro-F1 CIs), 25 surrogates matrix & phase timeline",
      action: () => { router.push("/models"); onClose(); },
      icon: <Activity className="w-4 h-4 text-teal-400" />
    },
    {
      id: "page-about",
      category: "Pages",
      title: "About / Methods / Limitations",
      subtitle: "Simulation pipeline diagram, locked decisions D-001..D-019, reproduction steps",
      action: () => { router.push("/about"); onClose(); },
      icon: <HelpCircle className="w-4 h-4 text-teal-400" />
    },

    // Cities
    ...((Object.keys(CITIES_DATA) as CityKey[]).map((c) => ({
      id: `city-${c}`,
      category: "Cities" as const,
      title: `${CITIES_DATA[c].name} (${CITIES_DATA[c].zone})`,
      subtitle: `${CITIES_DATA[c].confidence} Confidence • Spearman rs = ${CITIES_DATA[c].spearman.toFixed(3)}`,
      action: () => {
        if (onSelectCity) onSelectCity(c);
        router.push(`/cities?city=${c}`);
        onClose();
      },
      icon: <MapPin className="w-4 h-4 text-amber-400" />
    }))),

    // Presets
    {
      id: "preset-knee",
      category: "Presets",
      title: "Balanced Knee Point Design",
      subtitle: "Optimal trade-off between thermal discomfort and HVAC energy",
      action: () => { router.push("/pareto?preset=knee"); onClose(); },
      icon: <Sparkles className="w-4 h-4 text-teal-300" />
    },
    {
      id: "preset-energy",
      category: "Presets",
      title: "Lowest Energy Shelter Preset",
      subtitle: "Minimizes annual kWh/m² cooling/heating demand",
      action: () => { router.push("/pareto?preset=energy"); onClose(); },
      icon: <Sparkles className="w-4 h-4 text-emerald-400" />
    },

    // Key Decisions
    {
      id: "decision-d017",
      category: "Decisions",
      title: "Decision D-017: Confidence Tiers",
      subtitle: "Medium requires Spearman rs >= 0.8 & Adaptive valid >= 80%; otherwise Low",
      action: () => { router.push("/about#decision-d017"); onClose(); },
      icon: <HelpCircle className="w-4 h-4 text-indigo-400" />
    },
    {
      id: "decision-d011",
      category: "Decisions",
      title: "Decision D-011: Shimla Extrapolation",
      subtitle: "Zero TSV sensation votes in DB II; cold winter hours carry explicit flag",
      action: () => { router.push("/about#decision-d011"); onClose(); },
      icon: <HelpCircle className="w-4 h-4 text-indigo-400" />
    }
  ];

  const filteredItems = allItems.filter(
    (item) =>
      item.title.toLowerCase().includes(query.toLowerCase()) ||
      item.subtitle.toLowerCase().includes(query.toLowerCase()) ||
      item.category.toLowerCase().includes(query.toLowerCase())
  );

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "ArrowDown") {
      e.preventDefault();
      setSelectedIndex((prev) => (prev + 1) % Math.max(1, filteredItems.length));
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setSelectedIndex((prev) => (prev - 1 + filteredItems.length) % Math.max(1, filteredItems.length));
    } else if (e.key === "Enter" && filteredItems[selectedIndex]) {
      e.preventDefault();
      filteredItems[selectedIndex].action();
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center pt-20 px-4 bg-black/70 backdrop-blur-sm animate-in fade-in duration-150">
      <div className="w-full max-w-2xl bg-slate-900 border border-slate-700/80 rounded-2xl shadow-2xl overflow-hidden flex flex-col">
        {/* Search Input Bar */}
        <div className="flex items-center px-4 py-3 border-b border-slate-800">
          <Search className="w-5 h-5 text-teal-400 shrink-0 mr-3" />
          <input
            type="text"
            value={query}
            onChange={(e) => {
              setQuery(e.target.value);
              setSelectedIndex(0);
            }}
            onKeyDown={handleKeyDown}
            placeholder="Type a command, city, page, or technical decision (e.g. Jodhpur, Pareto, D-017)..."
            className="w-full bg-transparent text-white placeholder-slate-400 text-sm focus:outline-none"
            autoFocus
          />
          <button
            onClick={onClose}
            className="p-1 rounded text-slate-400 hover:text-white transition"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Results List */}
        <div className="max-h-96 overflow-y-auto p-2 divide-y divide-slate-800/40">
          {filteredItems.length === 0 ? (
            <div className="py-8 text-center text-slate-400 text-sm">
              No matching pages, cities, or decisions found for &ldquo;{query}&rdquo;
            </div>
          ) : (
            filteredItems.map((item, index) => {
              const isSelected = index === selectedIndex;
              return (
                <div
                  key={item.id}
                  onClick={() => item.action()}
                  onMouseEnter={() => setSelectedIndex(index)}
                  className={`flex items-center space-x-3 px-3 py-2.5 rounded-xl cursor-pointer transition ${
                    isSelected ? "bg-slate-800 border border-slate-700 text-white" : "text-slate-300 hover:bg-slate-800/50"
                  }`}
                >
                  <div className="p-2 rounded-lg bg-slate-800/80 shrink-0">
                    {item.icon}
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center space-x-2">
                      <span className="font-semibold text-sm truncate text-slate-100">{item.title}</span>
                      <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-slate-800 text-teal-400">
                        {item.category}
                      </span>
                    </div>
                    <p className="text-xs text-slate-400 truncate">{item.subtitle}</p>
                  </div>
                </div>
              );
            })
          )}
        </div>

        {/* Footer shortcuts helper */}
        <div className="px-4 py-2 border-t border-slate-800 bg-slate-950/60 flex items-center justify-between text-[11px] font-mono text-slate-400">
          <div className="flex items-center space-x-3">
            <span><kbd className="px-1.5 py-0.5 rounded bg-slate-800 border border-slate-700">↑↓</kbd> navigate</span>
            <span><kbd className="px-1.5 py-0.5 rounded bg-slate-800 border border-slate-700">↵</kbd> select</span>
            <span><kbd className="px-1.5 py-0.5 rounded bg-slate-800 border border-slate-700">esc</kbd> close</span>
          </div>
          <span>ClimateAdapt-Comfort</span>
        </div>
      </div>
    </div>
  );
};
