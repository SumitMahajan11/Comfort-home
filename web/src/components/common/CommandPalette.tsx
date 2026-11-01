"use client";

import React, { useEffect, useState, useRef, useMemo } from "react";
import { useRouter } from "next/navigation";
import { Search, MapPin, Sliders, Layers, HelpCircle, Activity, Sparkles, X, FileCode } from "lucide-react";
import { CITIES_DATA } from "@/lib/constants";
import { getProjectMetadata } from "@/lib/data";
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
  keywords?: string[];
}

export const CommandPalette: React.FC<CommandPaletteProps> = ({
  isOpen,
  onClose,
  onSelectCity
}) => {
  const router = useRouter();
  const [query, setQuery] = useState("");
  const [selectedIndex, setSelectedIndex] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);
  const previousActiveElement = useRef<HTMLElement | null>(null);
  const meta = getProjectMetadata();

  // Focus management: save active element before opening, restore on close, focus input
  useEffect(() => {
    if (isOpen) {
      previousActiveElement.current = document.activeElement as HTMLElement;
      const timer = setTimeout(() => {
        setQuery("");
        setSelectedIndex(0);
        inputRef.current?.focus();
      }, 0);
      return () => clearTimeout(timer);
    } else {
      if (previousActiveElement.current && typeof previousActiveElement.current.focus === "function") {
        previousActiveElement.current.focus();
      }
    }
  }, [isOpen]);

  // Keyboard shortcut listener for Cmd+K / Ctrl+K and Esc
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && (e.key === "k" || e.key === "K")) {
        e.preventDefault();
        if (isOpen) {
          onClose();
        }
      } else if (e.key === "Escape" && isOpen) {
        e.preventDefault();
        onClose();
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [isOpen, onClose]);

  const allItems: CommandItem[] = useMemo(() => {
    const pages: CommandItem[] = [
      {
        id: "page-overview",
        category: "Pages",
        title: "Overview & Evidence Scorecard",
        subtitle: "Headline facts, Survey of India map, S1-S4 research results",
        action: () => { router.push("/"); onClose(); },
        icon: <Activity className="w-4 h-4 text-[var(--primary)]" />,
        keywords: ["home", "landing", "scorecard", "kpi"]
      },
      {
        id: "page-plan",
        category: "Pages",
        title: "Plan my shelter",
        subtitle: "Passive decision-support wizard: climate, typology, budget & packages",
        action: () => { router.push("/recommender"); onClose(); },
        icon: <Sparkles className="w-4 h-4 text-[var(--primary)]" />,
        keywords: ["wizard", "recommender", "packages", "design"]
      },
      {
        id: "page-cities",
        category: "Pages",
        title: "City Explorer",
        subtitle: "5 Indian climate zones, EPW weather files & applicability gauges",
        action: () => { router.push("/cities"); onClose(); },
        icon: <MapPin className="w-4 h-4 text-[var(--primary)]" />,
        keywords: ["stations", "weather", "epw", "zones"]
      },
      {
        id: "page-evaluate",
        category: "Pages",
        title: "Evaluate a Design",
        subtitle: "8 variable sliders, live surrogate predictions, R1/R2 comparison & 3D shelter",
        action: () => { router.push("/evaluate"); onClose(); },
        icon: <Sliders className="w-4 h-4 text-[var(--primary)]" />,
        keywords: ["sliders", "surrogate", "3d", "custom"]
      },
      {
        id: "page-pareto",
        category: "Pages",
        title: "Pareto Explorer (Trade-offs)",
        subtitle: "Multi-objective trade-off frontier, verified designs, knee point & presets",
        action: () => { router.push("/pareto"); onClose(); },
        icon: <Layers className="w-4 h-4 text-[var(--primary)]" />,
        keywords: ["pareto", "frontier", "trade-offs", "optimization", "nsga"]
      },
      {
        id: "page-explain",
        category: "Pages",
        title: "Explain (SHAP Feature Attribution)",
        subtitle: "Global & local feature impacts, physical drivers, sensitivity heatmap",
        action: () => { router.push("/explain"); onClose(); },
        icon: <Sparkles className="w-4 h-4 text-[var(--primary)]" />,
        keywords: ["shap", "features", "importance", "explainability"]
      },
      {
        id: "page-models",
        category: "Pages",
        title: "Model Lab",
        subtitle: "Comfort models leaderboard, 25 surrogates accuracy matrix & evidence log",
        action: () => { router.push("/models"); onClose(); },
        icon: <Activity className="w-4 h-4 text-[var(--primary)]" />,
        keywords: ["leaderboard", "surrogates", "benchmarks", "accuracy"]
      },
      {
        id: "page-about",
        category: "Pages",
        title: "About / Methods / Limitations",
        subtitle: "Pipeline diagram, locked engineering decisions, scenario assumptions, reproduction",
        action: () => { router.push("/about"); onClose(); },
        icon: <HelpCircle className="w-4 h-4 text-[var(--primary)]" />,
        keywords: ["methods", "decisions", "assumptions", "reproduction", "limitations"]
      }
    ];

    const cities: CommandItem[] = (Object.keys(CITIES_DATA) as CityKey[]).map((c) => ({
      id: `city-${c}`,
      category: "Cities",
      title: `${CITIES_DATA[c].name} (${CITIES_DATA[c].zone})`,
      subtitle: `${CITIES_DATA[c].confidence} Confidence • Spearman rs = ${CITIES_DATA[c].spearman.toFixed(3)}`,
      action: () => {
        if (onSelectCity) onSelectCity(c);
        router.push(`/cities?city=${c}`);
        onClose();
      },
      icon: <MapPin className="w-4 h-4 text-amber-500" />,
      keywords: [c, CITIES_DATA[c].name.toLowerCase(), CITIES_DATA[c].climateCode.toLowerCase()]
    }));

    const presets: CommandItem[] = [
      {
        id: "preset-knee",
        category: "Presets",
        title: "Balanced Knee Point Preset",
        subtitle: "Optimal Pareto trade-off balancing discomfort reduction and HVAC energy",
        action: () => { router.push("/pareto?preset=knee"); onClose(); },
        icon: <Sparkles className="w-4 h-4 text-emerald-500" />,
        keywords: ["pareto", "knee", "balanced", "compromise"]
      },
      {
        id: "preset-energy",
        category: "Presets",
        title: "Lowest Energy Shelter Preset",
        subtitle: "Minimizes annual HVAC energy (kWh/m²/yr)",
        action: () => { router.push("/pareto?preset=energy"); onClose(); },
        icon: <Sparkles className="w-4 h-4 text-emerald-500" />,
        keywords: ["pareto", "energy", "lowest", "hvac", "o2"]
      },
      {
        id: "preset-comfort",
        category: "Presets",
        title: "Lowest Discomfort Preset",
        subtitle: "Minimizes annual discomfort hours percentage (O1)",
        action: () => { router.push("/pareto?preset=comfort"); onClose(); },
        icon: <Sparkles className="w-4 h-4 text-emerald-500" />,
        keywords: ["pareto", "comfort", "discomfort", "o1"]
      }
    ];

    // All decisions from metadata (D-001, D-005, D-011, D-014, D-015, D-017, D-018, etc.)
    const decisions: CommandItem[] = meta.decisions.map((d) => ({
      id: `decision-${d.id.toLowerCase()}`,
      category: "Decisions",
      title: `${d.id}: ${d.title}`,
      subtitle: d.description,
      action: () => {
        router.push("/about#decisions");
        onClose();
      },
      icon: <FileCode className="w-4 h-4 text-indigo-500" />,
      keywords: [d.id.toLowerCase(), d.id.replace("-", "").toLowerCase(), d.title.toLowerCase()]
    }));

    return [...pages, ...cities, ...presets, ...decisions];
  }, [meta.decisions, onSelectCity, router, onClose]);

  // Fuzzy match query against title, subtitle, category, ID, and keywords
  const filteredItems = useMemo(() => {
    const raw = query.trim().toLowerCase();
    if (!raw) return allItems;

    const normalized = raw.replace(/\s+/g, "");

    return allItems.filter((item) => {
      const titleLower = item.title.toLowerCase();
      const subLower = item.subtitle.toLowerCase();
      const catLower = item.category.toLowerCase();
      const idLower = item.id.toLowerCase();

      // Direct substring match
      if (
        titleLower.includes(raw) ||
        subLower.includes(raw) ||
        catLower.includes(raw) ||
        idLower.includes(raw)
      ) {
        return true;
      }

      // Normalized match (e.g. "d005" matches "d-005")
      if (
        idLower.replace("-", "").includes(normalized) ||
        titleLower.replace(/[\s-]+/g, "").includes(normalized)
      ) {
        return true;
      }

      // Keyword match
      if (item.keywords && item.keywords.some((k) => k.includes(raw) || normalized.includes(k))) {
        return true;
      }

      return false;
    });
  }, [allItems, query]);

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
    <div
      className="fixed inset-0 z-50 flex items-start justify-center pt-20 px-4 bg-black/70 backdrop-blur-sm animate-in fade-in duration-150"
      onClick={onClose}
    >
      <div
        className="w-full max-w-2xl bg-[var(--surface)] border border-[var(--line)] rounded-[8px] shadow-2xl overflow-hidden flex flex-col"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Search Input Bar */}
        <div className="flex items-center px-4 py-3 border-b border-[var(--line)] bg-[var(--surface)]">
          <Search className="w-5 h-5 text-[var(--ink-2)] shrink-0 mr-3" />
          <input
            ref={inputRef}
            type="text"
            value={query}
            onChange={(e) => {
              setQuery(e.target.value);
              setSelectedIndex(0);
            }}
            onKeyDown={handleKeyDown}
            placeholder="Search pages, cities, decisions"
            className="w-full bg-transparent text-[var(--ink)] placeholder-[var(--ink-2)] text-sm focus:outline-none"
            aria-label="Search pages, cities, decisions"
          />
          <button
            onClick={onClose}
            className="p-1 rounded text-[var(--ink-2)] hover:text-[var(--ink)] transition ml-2"
            aria-label="Close search"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Results List (Shows >= 8 items with scrolling that never cuts off an item) */}
        <div className="max-h-[460px] overflow-y-auto p-2 divide-y divide-[var(--line)]/50 overscroll-contain">
          {filteredItems.length === 0 ? (
            <div className="py-12 text-center text-[var(--ink-2)] text-sm font-medium">
              No matches
            </div>
          ) : (
            filteredItems.map((item, index) => {
              const isSelected = index === selectedIndex;
              return (
                <div
                  key={item.id}
                  onClick={() => item.action()}
                  onMouseEnter={() => setSelectedIndex(index)}
                  className={`flex items-center space-x-3 px-3 py-2.5 rounded-[6px] cursor-pointer transition select-none ${
                    isSelected
                      ? "bg-[var(--surface-2)] border border-[var(--line)] text-[var(--ink)]"
                      : "text-[var(--ink)] hover:bg-[var(--surface-2)]/60"
                  }`}
                >
                  <div className="p-2 rounded-[6px] bg-[var(--surface)] border border-[var(--line)] shrink-0">
                    {item.icon}
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center space-x-2">
                      <span className="font-semibold text-sm truncate text-[var(--ink)]">
                        {item.title}
                      </span>
                      <span className="text-[11px] px-1.5 py-0.5 rounded-[4px] bg-[var(--surface-2)] border border-[var(--line)] text-[var(--ink-2)] shrink-0 font-medium">
                        {item.category}
                      </span>
                    </div>
                    <p className="text-xs text-[var(--ink-2)] truncate mt-0.5">
                      {item.subtitle}
                    </p>
                  </div>
                </div>
              );
            })
          )}
        </div>

        {/* Footer shortcuts helper */}
        <div className="px-4 py-2.5 border-t border-[var(--line)] bg-[var(--surface-2)] flex items-center justify-between text-[12px] text-[var(--ink-2)]">
          <div className="flex items-center space-x-3">
            <span>
              <kbd className="px-1.5 py-0.5 rounded bg-[var(--surface)] border border-[var(--line)] tabular-nums font-mono text-[11px]">
                ↑↓
              </kbd>{" "}
              navigate
            </span>
            <span>
              <kbd className="px-1.5 py-0.5 rounded bg-[var(--surface)] border border-[var(--line)] font-mono text-[11px]">
                ↵
              </kbd>{" "}
              select
            </span>
            <span>
              <kbd className="px-1.5 py-0.5 rounded bg-[var(--surface)] border border-[var(--line)] font-mono text-[11px]">
                esc
              </kbd>{" "}
              close
            </span>
          </div>
          <span className="text-[11px] font-medium text-[var(--ink-2)]">
            {filteredItems.length} result{filteredItems.length === 1 ? "" : "s"}
          </span>
        </div>
      </div>
    </div>
  );
};

export default CommandPalette;
