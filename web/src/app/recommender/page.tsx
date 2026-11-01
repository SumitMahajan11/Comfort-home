"use client";

import React, { useState, useEffect, Suspense } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import {
  Compass,
  MapPin,
  Search,
  CheckCircle2,
  AlertTriangle,
  ShieldAlert,
  ShieldCheck,
  Sparkles,
  Sliders,
  DollarSign,
  TrendingDown,
  TrendingUp,
  FileText,
  Printer,
  Languages,
  Eye,
  Activity,
  Layers,
  Thermometer,
  Zap,
  Info,
  Clock,
  Wind,
  ArrowRight,
  ArrowLeft,
  Share2,
  Check,
  Table,
  Building,
  Home,
  Briefcase,
  ChevronRight,
  X,
  Copy
} from "lucide-react";
import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  BarChart,
  Bar,
  Cell
} from "recharts";
import { CITIES_DATA, PIPELINE_CONSTANTS } from "@/lib/constants";
import {
  CityKey,
  BuildingType,
  UserFeel,
  CoolingType,
  ClothingType,
  UserPriority,
  LanguageCode,
  EvaluationPackagesResponse,
  PassivePackage
} from "@/types";
import { TRANSLATIONS } from "@/lib/i18n";
import { matchLocation, evaluateQuestionnaire, downloadBuilderPdf } from "@/lib/api";
import { IndiaClimateMap } from "@/components/maps/IndiaClimateMap";
import { ConfidenceBadge } from "@/components/common/ConfidenceBadge";
import { VerificationBadge } from "@/components/common/VerificationBadge";
import { StatusPairing } from "@/components/common/StatusPairing";
import { ApplicabilityGauge } from "@/components/common/ApplicabilityGauge";
import { LimitationsDrawer } from "@/components/common/LimitationsDrawer";
import { InfoTip } from "@/components/ui/Tooltip";
import { getCityApplicability, getCityBaselines, formatPercentagePoints, formatEnergyDelta } from "@/lib/metrics";

function RecommenderContent() {
  const searchParams = useSearchParams();

  // URL Query Parameters parsing with fallback defaults
  const initialStep = Math.max(1, Math.min(5, parseInt(searchParams.get("step") || "1", 10) || 1));
  const rawCity = searchParams.get("city");
  let normalizedCity: CityKey = "Jodhpur";
  if (rawCity) {
    const key = rawCity.replace(/[\s+]+/g, "_");
    if (key in CITIES_DATA) {
      normalizedCity = key as CityKey;
    }
  }
  const initialCity = normalizedCity;
  const initialFeel = searchParams.get("feel") || "too_hot";
  const initialHours = parseInt(searchParams.get("hours") || "18", 10) || 18;
  const initialCooling = (searchParams.get("cooling") as CoolingType) || "fan";
  const initialPriority = (searchParams.get("priority") as UserPriority) || "balanced";
  const initialPkg = (searchParams.get("pkg") as any) || (initialPriority === "low energy" ? "pkg_budget" : initialPriority === "comfort" ? "pkg_best_comfort" : "pkg_balanced");

  // Mode and Language State
  const [lang, setLang] = useState<LanguageCode>("en");
  // Simple Mode: persists in localStorage. Hides technical metrics (R², Spearman, CI), shows plain-language terms, one recommendation.
  const [simpleMode, setSimpleMode] = useState<boolean>(true);

  useEffect(() => {
    try {
      const saved = localStorage.getItem("comfort_simple_mode");
      if (saved !== null) {
        setSimpleMode(saved === "true");
      }
    } catch {}
  }, []);

  const toggleSimpleMode = () => {
    setSimpleMode((prev) => {
      const next = !prev;
      try {
        localStorage.setItem("comfort_simple_mode", String(next));
      } catch {}
      return next;
    });
  };

  const [currentStep, setCurrentStep] = useState<number>(initialStep);
  const [maxStepReached, setMaxStepReached] = useState<number>(Math.max(initialStep, 1));
  const [copiedLink, setCopiedLink] = useState(false);
  const [copiedSummary, setCopiedSummary] = useState(false);
  const [isCompareOpen, setIsCompareOpen] = useState(false);

  // Data Table View Toggles (WCAG AA requirement)
  const [showClimateDataTable, setShowClimateDataTable] = useState(false);
  const [showMonthlyDataTable, setShowMonthlyDataTable] = useState(false);

  // Step 1: Location state
  const [selectedCity, setSelectedCity] = useState<CityKey>(initialCity);
  const [searchQuery, setSearchQuery] = useState("");
  const [isSearching, setIsSearching] = useState(false);
  const [nearestNotice, setNearestNotice] = useState<string | null>(null);
  const [distanceKm, setDistanceKm] = useState<number>(0);

  // Step 2: Typology (Locked single-zone shelter_v1, 24 h/day continuous occupancy per A-001..A-007)
  const buildingType: BuildingType = "shelter_v1";

  // Step 4: Comfort Questionnaire state
  const [summerFeel, setSummerFeel] = useState<string>(initialFeel);
  const [hoursOccupied, setHoursOccupied] = useState<number>(initialHours);
  const [cooling, setCooling] = useState<CoolingType>(initialCooling);
  const [priority, setPriority] = useState<UserPriority>(initialPriority);

  // Step 5: Packages & Results state
  const [evaluation, setEvaluation] = useState<EvaluationPackagesResponse | null>(null);
  const [activePackageId, setActivePackageId] = useState<"pkg_budget" | "pkg_balanced" | "pkg_best_comfort">(initialPkg);
  const [loading, setLoading] = useState(false);
  const [pdfDownloading, setPdfDownloading] = useState(false);

  const t = TRANSLATIONS[lang];
  const cityInfo = CITIES_DATA[selectedCity];
  const cityBaselines = getCityBaselines(selectedCity);
  const cityApp = getCityApplicability(selectedCity);

  // URL state persistence & max step tracker
  useEffect(() => {
    setMaxStepReached((prev) => Math.max(prev, currentStep));
    if (typeof window !== "undefined") {
      const params = new URLSearchParams(window.location.search);
      params.set("step", currentStep.toString());
      params.set("city", selectedCity);
      params.set("feel", summerFeel);
      params.set("hours", hoursOccupied.toString());
      params.set("cooling", cooling);
      params.set("priority", priority);
      params.set("pkg", activePackageId);
      const newUrl = `${window.location.pathname}?${params.toString()}`;
      window.history.replaceState(null, "", newUrl);
    }
  }, [currentStep, selectedCity, summerFeel, hoursOccupied, cooling, priority, activePackageId]);

  // Priority change handler: updates both priority and recommended package
  const handlePriorityChange = (newPriority: UserPriority) => {
    setPriority(newPriority);
    if (newPriority === "low energy") {
      setActivePackageId("pkg_budget");
    } else if (newPriority === "comfort") {
      setActivePackageId("pkg_best_comfort");
    } else {
      setActivePackageId("pkg_balanced");
    }
  };

  const runEvaluation = async () => {
    setLoading(true);
    try {
      const userFeelParam: UserFeel =
        summerFeel === "too_hot" ? "too hot" : summerFeel === "too_cold" ? "too cold" : "about right";

      const res = await evaluateQuestionnaire({
        city: selectedCity,
        building_type: "shelter_v1",
        usually_feel: userFeelParam,
        hours_occupied: hoursOccupied,
        has_cooling: cooling,
        summer_clothing: "light",
        winter_clothing: "normal",
        priority: priority,
        future_climate: false
      });
      setEvaluation(res);
    } catch (err) {
      console.error("Evaluation error:", err);
    } finally {
      setLoading(false);
    }
  };

  // Auto-evaluate when city, feel, hours, cooling, or priority changes
  useEffect(() => {
    runEvaluation();
  }, [selectedCity, summerFeel, hoursOccupied, cooling, priority]);

  const handleLocationSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!searchQuery.trim()) return;
    setIsSearching(true);
    try {
      const res = await matchLocation(searchQuery);
      setSelectedCity(res.matched_city_key);
      setNearestNotice(res.nearest_match_notice);
      setDistanceKm(res.distance_km);
    } catch (err) {
      console.error("Search error:", err);
    } finally {
      setIsSearching(false);
    }
  };

  // Active Package selection
  const activePackage: PassivePackage | undefined = evaluation?.packages[
    activePackageId === "pkg_budget"
      ? "budget"
      : activePackageId === "pkg_balanced"
      ? "balanced"
      : "best_comfort"
  ];

  // PDF Export Trigger
  const handleDownloadPdf = async () => {
    if (!activePackage) return;
    setPdfDownloading(true);
    try {
      const profile = {
        city: selectedCity,
        comfort_sensation: summerFeel,
        occupancy_hours: hoursOccupied,
        cooling_equipment: cooling,
        optimization_priority: priority,
        building_type: "shelter_v1",
        model_assumptions: "Single-zone 20.0 m² passive shelter (5 m x 4 m, 3 m high), 24 h/day continuous occupancy (A-001..A-007)",
        confidence_tier: cityInfo.confidence,
        confidence_reason: cityInfo.envelopeAlert || "Precomputed EnergyPlus surrogate prediction.",
        limitations: "Simulation-based estimate, not a measured result or construction quote. Rates unpopulated in official DSR schedule."
      };
      await downloadBuilderPdf(
        {
          ...activePackage,
          city: selectedCity,
          building_type: "shelter_v1"
        },
        profile,
        lang
      );
    } catch (e) {
      console.error("PDF download failed:", e);
      window.print();
    } finally {
      setPdfDownloading(false);
    }
  };

  // Shareable URL Copy
  const handleShareLink = () => {
    const url = new URL(window.location.href);
    url.searchParams.set("step", currentStep.toString());
    url.searchParams.set("city", selectedCity);
    url.searchParams.set("feel", summerFeel);
    url.searchParams.set("hours", hoursOccupied.toString());
    url.searchParams.set("cooling", cooling);
    url.searchParams.set("priority", priority);
    url.searchParams.set("pkg", activePackageId);
    navigator.clipboard.writeText(url.toString());
    setCopiedLink(true);
    setTimeout(() => setCopiedLink(false), 2500);
  };

  // Plain-text Summary Copy
  const handleCopySummary = () => {
    if (!activePackage) return;
    const summaryText = [
      `ClimateAdapt-Comfort — Passive Design Specification`,
      `City: ${cityInfo.name} (${cityInfo.zone})`,
      `Package: ${activePackage.name} (${activePackage.selection_role || "Pareto-verified"})`,
      `Design ID: ${activePackage.pareto_id}`,
      `Confidence Tier: ${cityInfo.confidence}`,
      `Model Assumptions: Single-zone 60 m² shelter, 24 h/day continuous occupancy (A-001..A-007)`,
      ``,
      `Key Envelope Variables:`,
      `- Roof EPS Insulation: ${(activePackage.design_variables.roof_insulation_thickness * 1000).toFixed(0)} mm (~60 m² area)`,
      `- Roof Solar Absorptance: ${activePackage.design_variables.roof_solar_absorptance.toFixed(2)} (High-SRI reflective finish)`,
      `- Wall Mineral Wool: ${(activePackage.design_variables.wall_insulation_thickness * 1000).toFixed(0)} mm (~72 m² net wall area)`,
      `- Wall Construction: 200 mm ${activePackage.design_variables.wall_mass_class} mass masonry`,
      `- Fenestration: ${(activePackage.design_variables.wwr > 1 ? activePackage.design_variables.wwr : activePackage.design_variables.wwr * 100).toFixed(0)}% WWR with ${activePackage.design_variables.shading_depth.toFixed(2)} m exterior overhang projection`,
      `- Natural Ventilation: ${activePackage.design_variables.ventilation_ach.toFixed(1)} ACH`,
      ``,
      `Simulated Performance:`,
      `- Discomfort: ${activePackage.discomfort_pct}% (${activePackage.annual_discomfort_hours ?? Math.round(hoursOccupied * 365 * activePackage.discomfort_pct / 100)} h/yr out of ${activePackage.hours_scored ?? hoursOccupied * 365} h/yr scored)`,
      `- HVAC Energy: ${cooling === "none" ? "0 kWh/m²/yr (free-running: no HVAC)" : `${activePackage.annual_energy_kwh_per_m2} kWh/m²/yr (${activePackage.cooling_mode || "Active cooling"})`}`,
      `- Comfort vs Baseline R2: ${formatPercentagePoints(activePackage.discomfort_pct - cityBaselines.r2.discomfort_ml_pct)}`,
      `- Energy vs Baseline R2: ${formatEnergyDelta(activePackage.annual_energy_kwh_per_m2 - cityBaselines.r2.energy_kwh_per_m2_yr)}`,
      ``,
      `Notice: Simulation-based estimate, not a measured result or construction quote. CPWD DSR rate schedule unpopulated; showing engineering bill of quantities only.`
    ].join("\n");

    navigator.clipboard.writeText(summaryText);
    setCopiedSummary(true);
    setTimeout(() => setCopiedSummary(false), 2500);
  };

  // Climate norms data for Step 3
  const monthlyClimateData = [
    { month: "Jan", min: 9.8, mean: 16.8, max: 24.5, rh: 42, comfortableHours: 620, warmHours: 0, coldHours: 124 },
    { month: "Feb", min: 12.6, mean: 20.4, max: 28.6, rh: 36, comfortableHours: 580, warmHours: 42, coldHours: 50 },
    { month: "Mar", min: 18.2, mean: 26.1, max: 34.2, rh: 28, comfortableHours: 490, warmHours: 254, coldHours: 0 },
    { month: "Apr", min: 23.5, mean: 31.8, max: 39.8, rh: 22, comfortableHours: 320, warmHours: 400, coldHours: 0 },
    { month: "May", min: 27.4, mean: 35.4, max: 42.6, rh: 24, comfortableHours: 190, warmHours: 554, coldHours: 0 },
    { month: "Jun", min: 28.1, mean: 34.6, max: 40.5, rh: 40, comfortableHours: 240, warmHours: 480, coldHours: 0 },
    { month: "Jul", min: 26.8, mean: 31.5, max: 36.2, rh: 62, comfortableHours: 340, warmHours: 404, coldHours: 0 },
    { month: "Aug", min: 25.4, mean: 29.8, max: 34.1, rh: 70, comfortableHours: 410, warmHours: 334, coldHours: 0 },
    { month: "Sep", min: 24.2, mean: 30.2, max: 35.8, rh: 60, comfortableHours: 380, warmHours: 340, coldHours: 0 },
    { month: "Oct", min: 19.8, mean: 28.1, max: 35.2, rh: 35, comfortableHours: 460, warmHours: 284, coldHours: 0 },
    { month: "Nov", min: 14.5, mean: 22.9, max: 30.4, rh: 38, comfortableHours: 590, warmHours: 110, coldHours: 20 },
    { month: "Dec", min: 10.8, mean: 17.9, max: 25.8, rh: 45, comfortableHours: 640, warmHours: 0, coldHours: 104 }
  ];

  // Steps configuration
  const stepsConfig = [
    { num: 1, title: lang === "hi" ? "स्थान" : "Where", icon: <MapPin className="w-4 h-4" /> },
    { num: 2, title: lang === "hi" ? "भवन प्रकार" : "What", icon: <Building className="w-4 h-4" /> },
    { num: 3, title: lang === "hi" ? "जलवायु" : "Your Climate", icon: <Activity className="w-4 h-4" /> },
    { num: 4, title: lang === "hi" ? "कम्फर्ट प्रोफ़ाइल" : "Your Comfort", icon: <Sliders className="w-4 h-4" /> },
    { num: 5, title: lang === "hi" ? "पैसिव योजना" : "Your Plan", icon: <Layers className="w-4 h-4" /> }
  ];

  return (
    <div className="space-y-8 pb-24 print:p-0 print:space-y-4">
      {/* HEADER CONTROLS BAR */}
      <div className="flex flex-wrap items-center justify-between gap-4 border-b border-white/10 pb-5">
        <div>
          <div className="inline-flex items-center space-x-2 px-3 py-1 rounded-[8px] bg-[var(--surface-2)] border border-[var(--line)] text-[var(--primary)] text-xs font-semibold mb-2">
            <span className="w-2 h-2 rounded-full bg-teal-400 animate-ping" />
            <span>Plan (Passive Decision-Support)</span>
          </div>
          <h1 className="text-3xl sm:text-4xl font-extrabold text-[var(--ink)] tracking-tight">
            {t.appName}
          </h1>
          <p className="text-sm text-[var(--ink-2)] mt-1">{t.tagline}</p>
        </div>

        {/* Global Controls */}
        <div className="flex flex-wrap items-center gap-2 print:hidden">
          {/* Simple Mode Toggle */}
          <div className="relative group">
            <button
              type="button"
              onClick={toggleSimpleMode}
              className={`flex items-center space-x-1.5 px-3 py-1.5 rounded-[8px] text-xs font-semibold transition border focus:outline-none focus-visible:ring-2 focus-visible:ring-[var(--primary)] focus-visible:ring-offset-2 ${
                simpleMode
                  ? "bg-[var(--primary)] text-white border-[var(--primary)] shadow-sm"
                  : "bg-[var(--surface-2)] text-[var(--ink)] border-[var(--line)] hover:border-[var(--primary)]"
              }`}
              aria-pressed={simpleMode}
              aria-label="Toggle Simple Mode"
            >
              <Eye className="w-3.5 h-3.5" />
              <span>{simpleMode ? "Simple Mode: ON" : "Simple Mode: OFF"}</span>
            </button>

            {/* Tooltip defining Simple Mode */}
            <div className="absolute top-full left-0 mt-2 hidden group-hover:block w-72 p-3 bg-[var(--surface)] border border-[var(--line)] rounded-[8px] text-[12px] text-[var(--ink)] shadow-xl z-30 leading-snug">
              <strong className="block font-semibold mb-0.5 text-[var(--primary)]">Simple Mode:</strong>
              Hides technical metrics (R², Spearman correlation, confidence intervals), displays plain-language descriptions only, and highlights a single recommended shelter package.
            </div>
          </div>

          {/* Limitations Drawer Modal Button */}
          <LimitationsDrawer />
        </div>
      </div>

      {/* 5-STEP WIZARD PROGRESS BAR */}
      <nav aria-label="Wizard Steps Progress" className="rounded-2xl glass-card p-3 sm:p-4 print:hidden">
        <div className="flex items-center justify-between gap-1 sm:gap-2">
          {stepsConfig.map((s, idx) => {
            const isActive = currentStep === s.num;
            const isCompleted = currentStep > s.num;
            const isClickable = s.num <= maxStepReached;
            return (
              <React.Fragment key={s.num}>
                <button
                  type="button"
                  disabled={!isClickable}
                  onClick={() => setCurrentStep(s.num)}
                  aria-label={`Go to step ${s.num}: ${s.title}`}
                  className={`flex items-center space-x-2 px-3 py-2 rounded-xl text-xs font-semibold transition ${
                    isActive
                      ? "bg-teal-500 text-slate-950 font-bold shadow-[0_0_20px_rgba(42,127,142,0.4)] cursor-default"
                      : isCompleted
                      ? "bg-white/[0.05] text-teal-300 hover:bg-white/[0.09] cursor-pointer"
                      : isClickable
                      ? "text-slate-300 hover:text-white hover:bg-white/[0.04] cursor-pointer"
                      : "text-slate-500 opacity-40 cursor-not-allowed"
                  }`}
                >
                  <span
                    className={`w-5 h-5 rounded-full flex items-center justify-center text-xs tabular-nums ${
                      isActive
                        ? "bg-slate-950 text-teal-300 font-bold"
                        : isCompleted
                        ? "bg-teal-500/20 text-teal-300"
                        : "bg-white/10 text-slate-400"
                    }`}
                  >
                    {isCompleted ? <Check className="w-3 h-3 text-teal-400" /> : s.num}
                  </span>
                  <span className="hidden sm:inline">{s.title}</span>
                </button>

                {idx < stepsConfig.length - 1 && (
                  <div
                    className={`flex-1 h-0.5 rounded transition ${
                      currentStep > s.num ? "bg-teal-500/60" : "bg-white/10"
                    }`}
                  />
                )}
              </React.Fragment>
            );
          })}
        </div>
      </nav>

      {/* ========================================================================= */}
      {/* STEP 1: WHERE (LOCATION SELECTION & DISTANCE MATCHING) */}
      {/* ========================================================================= */}
      {currentStep === 1 && (
        <section className="rounded-2xl glass-card p-6 space-y-6">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-white/10 pb-4">
            <div>
              <h2 className="text-xl font-bold text-[var(--ink)] flex items-center space-x-2">
                <MapPin className="w-5 h-5 text-teal-400" />
                <span>{lang === "hi" ? "चरण 1: स्थान का चयन करें" : "Step 1: Where is your project located?"}</span>
              </h2>
              <p className="text-xs text-[var(--ink-2)] mt-1">
                {lang === "hi"
                  ? "सिमुलेटेड 5 भारतीय संदर्भ स्टेशनों में से चुनें या किसी भी शहर को खोजें।"
                  : "Pick one of the 5 simulated reference stations on the map, or search any Indian location."}
              </p>
            </div>
            <span className="text-xs text-[var(--ink-2)]">
              {t.simulatedStationsOnly}
            </span>
          </div>

          {/* India Climate Map Component */}
          <div className="space-y-3">
            <label className="text-xs font-bold text-[var(--ink)] uppercase tracking-wider block">
              {lang === "hi" ? "मानचित्र पर जलवायु स्टेशन चुनें:" : "Select Representative Climate Station:"}
            </label>
            <IndiaClimateMap
              selectedCity={selectedCity}
              onSelectCity={(city) => {
                setSelectedCity(city);
                setNearestNotice(null);
                setDistanceKm(0);
              }}
            />
          </div>

          {/* City Selection Buttons & Geocoding Search */}
          <div className="space-y-4 pt-2">
            <div className="flex flex-wrap gap-2">
              {(Object.keys(CITIES_DATA) as CityKey[]).map((cKey) => {
                const c = CITIES_DATA[cKey];
                const isSelected = selectedCity === cKey;
                return (
                  <button
                    key={cKey}
                    type="button"
                    onClick={() => {
                      setSelectedCity(cKey);
                      setNearestNotice(null);
                      setDistanceKm(0);
                    }}
                    className={`flex items-center space-x-2 px-4 py-2 rounded-xl text-xs font-semibold transition ${
                      isSelected
                        ? "bg-[var(--ink)] text-[var(--surface)] font-bold shadow-sm"
                        : "bg-[var(--surface-2)] border border-[var(--line)] text-[var(--ink)] hover:border-[var(--primary)]"
                    }`}
                  >
                    <span>{c.name}</span>
                    <span
                      className={`text-[10px] px-1.5 py-0.5 rounded font-mono ${
                        isSelected
                          ? "bg-[var(--surface)] text-[var(--ink)] font-bold"
                          : "bg-[var(--surface)] border border-[var(--line)] text-[var(--ink-2)]"
                      }`}
                    >
                      {c.zone.split(" ")[0]}
                    </span>
                  </button>
                );
              })}
            </div>

            {/* In-Card Text Link to City Explorer */}
            <div className="flex items-center justify-between text-xs pt-1 border-t border-[var(--line)]">
              <span className="text-[var(--ink-2)]">
                Selected Station: <strong className="text-[var(--ink)]">{cityInfo.name}</strong> ({cityInfo.zone} Climate Zone)
              </span>
              <Link
                href={`/cities?city=${selectedCity}`}
                className="inline-flex items-center space-x-1 text-[var(--primary)] hover:underline text-xs font-medium"
              >
                <span>Explore {cityInfo.name} in City Explorer</span>
                <ArrowRight className="w-3.5 h-3.5" />
              </Link>
            </div>

            {/* Search Bar */}
            <form onSubmit={handleLocationSearch} className="flex gap-2 max-w-xl">
              <div className="relative flex-1">
                <Search className="w-4 h-4 text-[var(--ink-2)] absolute left-3 top-3" />
                <input
                  type="text"
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  placeholder="Search city or state"
                  className="w-full bg-[var(--surface-2)] border border-[var(--line)] text-[var(--ink)] placeholder:text-[var(--ink-2)] text-xs pl-9 pr-3 py-2.5 rounded-xl focus:outline-none focus:ring-1 focus:ring-[var(--primary)]"
                />
              </div>
              <button
                type="submit"
                disabled={isSearching}
                className="px-4 py-2.5 rounded-xl bg-[var(--ink)] hover:opacity-90 text-[var(--surface)] font-semibold text-xs transition"
              >
                {isSearching ? "Matching..." : "Match Nearest Station"}
              </button>
            </form>

            {/* Nearest Station Match and Warning Chip */}
            {nearestNotice && (
              <div
                className={`rounded-xl border p-4 text-xs flex items-start space-x-3 ${
                  distanceKm > 300
                    ? "border-rose-500/40 bg-rose-950/30 text-rose-200"
                    : "border-amber-500/40 bg-amber-950/20 text-amber-200"
                }`}
              >
                <ShieldAlert className="w-4 h-4 text-amber-400 shrink-0 mt-0.5" />
                <div className="space-y-1.5 flex-1">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="font-bold">
                      Matched Station: {cityInfo.name} ({distanceKm} km away)
                    </span>
                    {distanceKm > 300 ? (
                      <span className="px-2 py-0.5 rounded bg-rose-500/30 text-rose-200 border border-rose-400/50 text-[11px] font-bold">
                        ⚠️ Distance &gt; 300 km (Proxy Station)
                      </span>
                    ) : (
                      <span className="px-2 py-0.5 rounded bg-teal-500/20 text-teal-200 border border-teal-400/40 text-[11px] font-semibold">
                        Proxy Station Match
                      </span>
                    )}
                  </div>
                  <p className="leading-relaxed">{nearestNotice}</p>
                  {distanceKm > 300 && (
                    <p className="font-semibold text-rose-300">
                      ⚠️ Warning: Distance exceeds 300 km threshold. Microclimates, topography, and seasonal temperature swings may differ significantly from this proxy station.
                    </p>
                  )}
                </div>
              </div>
            )}
          </div>

          {/* Navigation */}
          <div className="flex justify-end pt-4 border-t border-white/10">
            <button
              type="button"
              onClick={() => setCurrentStep(2)}
              className="px-6 py-2.5 rounded-xl bg-teal-500 hover:bg-teal-400 text-slate-950 font-bold text-xs transition shadow-md flex items-center space-x-2"
            >
              <span>Next: Building Typology</span>
              <ArrowRight className="w-4 h-4" />
            </button>
          </div>
        </section>
      )}

      {/* ========================================================================= */}
      {/* STEP 2: WHAT (BUILDING TYPOLOGY & LOCKED MODEL ASSUMPTIONS) */}
      {/* ========================================================================= */}
      {currentStep === 2 && (
        <section className="rounded-2xl glass-card p-6 space-y-6">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-white/10 pb-4">
            <div>
              <h2 className="text-xl font-bold text-white flex items-center space-x-2">
                <Building className="w-5 h-5 text-teal-400" />
                <span>{lang === "hi" ? "चरण 2: भवन प्रकार एवं मॉडल धारणाएं" : "Step 2: What are you building?"}</span>
              </h2>
              <p className="text-xs text-slate-400 mt-1">
                {lang === "hi"
                  ? "वर्तमान सिमुलेशन केवल सिंगल-ज़ोन पैसिव आश्रय के लिए मान्य हैं।"
                  : "All Pareto simulations represent single-zone detached buildings under 24 h/day continuous occupancy (A-001..A-007)."}
              </p>
            </div>
            <span className="text-xs px-2.5 py-1 rounded-[6px] bg-teal-500/10 border border-teal-500/30 text-teal-300 font-medium">
              Calibrated Single-Zone Envelope
            </span>
          </div>

          {/* Building Typology Cards */}
          <div className="space-y-3">
            <label className="text-xs font-bold text-slate-300 uppercase tracking-wider block">
              {lang === "hi" ? "भवन संरचना का प्रकार:" : "Building Architecture & Typology:"}
            </label>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              {/* Active Single-Zone Option */}
              <div
                className="p-5 rounded-2xl text-left border flex flex-col justify-between space-y-3 bg-teal-500/15 border-teal-400/60 shadow-[0_0_25px_rgba(42,127,142,0.3)]"
              >
                <div className="flex items-center justify-between">
                  <div className="p-2.5 rounded-xl bg-white/[0.04] border border-white/10">
                    <Home className="w-6 h-6 text-teal-400" />
                  </div>
                  <div className="flex items-center space-x-1 px-2 py-0.5 rounded bg-teal-500/20 text-teal-300 text-[10px] font-bold">
                    <CheckCircle2 className="w-3.5 h-3.5" />
                    <span>Active Simulation</span>
                  </div>
                </div>
                <div>
                  <h3 className="text-sm font-bold text-white">Single-Zone Passive Shelter</h3>
                  <span className="text-xs text-[var(--primary)] font-medium block mt-0.5">~60 m² carpet area</span>
                  <p className="text-xs text-slate-300 mt-2 leading-relaxed">
                    Single-storey detached shelter with direct solar exposure on all four facades and roof. 24 h/day continuous residential occupancy per locked assumptions A-001 and A-002.
                  </p>
                </div>
              </div>

              {/* Disabled Apartment Option */}
              <div
                className="p-5 rounded-2xl text-left border flex flex-col justify-between space-y-3 glass-panel border-white/5 opacity-60 cursor-not-allowed"
              >
                <div className="flex items-center justify-between">
                  <div className="p-2.5 rounded-xl bg-white/[0.04] border border-white/10">
                    <Building className="w-6 h-6 text-slate-400" />
                  </div>
                  <span className="text-[10px] uppercase font-bold px-2 py-0.5 rounded bg-amber-500/20 text-amber-300 border border-amber-500/30">
                    Coming later
                  </span>
                </div>
                <div>
                  <h3 className="text-sm font-bold text-slate-300">Apartment Unit</h3>
                  <span className="text-xs text-slate-400 font-medium block mt-0.5">~55 m² carpet area</span>
                  <p className="text-xs text-slate-400 mt-2 leading-relaxed">
                    Multi-zone party walls and intermediate floor boundary simulations are scheduled for upcoming research phases.
                  </p>
                </div>
              </div>

              {/* Disabled Commercial Option */}
              <div
                className="p-5 rounded-2xl text-left border flex flex-col justify-between space-y-3 glass-panel border-white/5 opacity-60 cursor-not-allowed"
              >
                <div className="flex items-center justify-between">
                  <div className="p-2.5 rounded-xl bg-white/[0.04] border border-white/10">
                    <Briefcase className="w-6 h-6 text-slate-400" />
                  </div>
                  <span className="text-[10px] uppercase font-bold px-2 py-0.5 rounded bg-amber-500/20 text-amber-300 border border-amber-500/30">
                    Coming later
                  </span>
                </div>
                <div>
                  <h3 className="text-sm font-bold text-slate-300">Small Commercial / Office</h3>
                  <span className="text-xs text-slate-400 font-medium block mt-0.5">~80 m² carpet area</span>
                  <p className="text-xs text-slate-400 mt-2 leading-relaxed">
                    Daytime-only schedules and internal equipment density simulations are scheduled for upcoming research phases.
                  </p>
                </div>
              </div>
            </div>
          </div>

          {/* Model Assumptions Panel */}
          <div className="rounded-xl glass-panel p-5 space-y-3 border border-white/10">
            <h3 className="text-xs font-bold text-white uppercase tracking-wider flex items-center space-x-2">
              <Info className="w-4 h-4 text-teal-400" />
              <span>Locked Physical Assumptions (A-001..A-007)</span>
            </h3>
            <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-3 text-xs text-slate-300">
              <div className="p-3 rounded-lg bg-white/[0.02] border border-white/5 space-y-1">
                <span className="text-teal-300 font-semibold block">Geometry</span>
                <p>Detached single-zone building, ~60 m² carpet area, 3.0 m floor-to-ceiling height (A-001).</p>
              </div>
              <div className="p-3 rounded-lg bg-white/[0.02] border border-white/5 space-y-1">
                <span className="text-teal-300 font-semibold block">Occupancy</span>
                <p>Continuous 24 hours/day residential occupancy schedule (A-002).</p>
              </div>
              <div className="p-3 rounded-lg bg-white/[0.02] border border-white/5 space-y-1">
                <span className="text-teal-300 font-semibold block">Ventilation</span>
                <p>Natural cross-ventilation through operable louvers when indoor temp &gt; outdoor (A-003, A-004).</p>
              </div>
            </div>
          </div>

          {/* Navigation */}
          <div className="flex justify-between pt-4 border-t border-white/10">
            <button
              type="button"
              onClick={() => setCurrentStep(1)}
              className="px-5 py-2.5 rounded-xl glass-button text-slate-200 text-xs font-semibold flex items-center space-x-2"
            >
              <ArrowLeft className="w-4 h-4" />
              <span>{lang === "hi" ? "वापस" : "Back"}</span>
            </button>
            <button
              type="button"
              onClick={() => setCurrentStep(3)}
              className="px-6 py-2.5 rounded-xl bg-teal-500 hover:bg-teal-400 text-slate-950 font-bold text-xs transition shadow-md flex items-center space-x-2"
            >
              <span>Next: Review Climate Data</span>
              <ArrowRight className="w-4 h-4" />
            </button>
          </div>
        </section>
      )}

      {/* ========================================================================= */}
      {/* STEP 3: YOUR CLIMATE (ANIMATED CLIMATE PROFILE & APPLICABILITY) */}
      {/* ========================================================================= */}
      {currentStep === 3 && (
        <section className="rounded-2xl glass-card p-6 space-y-6">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-white/10 pb-4">
            <div>
              <h2 className="text-xl font-bold text-white flex items-center space-x-2">
                <Activity className="w-5 h-5 text-teal-400" />
                <span>{lang === "hi" ? "चरण 3: आपकी क्षेत्रीय जलवायु" : `Step 3: Climate Profile for ${cityInfo.name}`}</span>
              </h2>
              <p className="text-xs text-slate-400 mt-1">{t.step2Desc}</p>
            </div>
            <div className="flex items-center space-x-2">
              <ConfidenceBadge
                tier={cityInfo.confidence}
                spearman={simpleMode ? undefined : cityInfo.spearman}
                reason={cityInfo.envelopeAlert}
              />
            </div>
          </div>

          {/* Low Confidence Plain-Language Guidance */}
          {cityInfo.confidence === "Low" && (
            <div className="rounded-xl border border-amber-500/40 bg-amber-950/20 p-4 text-xs text-amber-200 space-y-1.5">
              <div className="font-bold flex items-center space-x-2 text-amber-300">
                <AlertTriangle className="w-4 h-4 text-amber-400 shrink-0" />
                <span>Confidence: Low in {cityInfo.name} ({cityInfo.zone} Zone)</span>
              </div>
              <p className="leading-relaxed">
                {cityInfo.envelopeAlert || "Dual comfort checks diverge or seasonal weather extremes operate outside empirical ASHRAE 55 calibration regimes."}
              </p>
              <p className="font-semibold text-amber-300 pt-0.5">
                What to do: Use these recommendations as an early-stage passive starting point; verify thermal performance and HVAC sizing with a local building services engineer.
              </p>
            </div>
          )}

          {/* Key Climate Gauges */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
            <div className="rounded-xl glass-panel p-4">
              <span className="text-xs text-[var(--ink-2)] block">{t.climateZone}</span>
              <span className="text-base font-bold text-white mt-1 block">{cityInfo.zone}</span>
              <span className="text-[10px] text-teal-400 mt-0.5 block">Elevation: {cityInfo.elevation} | Köppen: {cityInfo.climateCode}</span>
            </div>

            <div className="rounded-xl glass-panel p-4">
              <span className="text-xs text-[var(--ink-2)] block">Annual mean outdoor temp</span>
              <span className="text-base font-bold text-white mt-1 block">
                {cityBaselines.r1.mean_ta_c.toFixed(1)}°C
              </span>
              <span className="text-[10px] text-slate-400 mt-0.5 block">EPW: {cityInfo.epw}</span>
            </div>

            <ApplicabilityGauge
              label="Adaptive 90% Validity"
              value={cityApp.adaptive_validity_pct}
              threshold={80}
              subtitle="ASHRAE 55 valid temperature regime"
            />

            <ApplicabilityGauge
              label="DB II ML Envelope Validity"
              value={cityApp.envelope_validity_pct}
              threshold={70}
              subtitle="Empirical survey training domain"
            />
          </div>

          {/* Monthly Temperature Bands Chart */}
          <div className="rounded-xl glass-panel p-5 space-y-4">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-white/10 pb-2">
              <div>
                <h3 className="text-xs font-bold text-white uppercase tracking-wider flex items-center space-x-2">
                  <Thermometer className="w-4 h-4 text-teal-400" />
                  <span>Monthly Outdoor Temperature Bands & Comfort Hours</span>
                </h3>
                <span className="text-[10px] text-slate-400">Monthly Min, Mean, Max Dry-Bulb (°C) from TMYx Weather</span>
              </div>
              <div className="flex items-center space-x-2">
                <button
                  type="button"
                  onClick={() => setShowClimateDataTable(!showClimateDataTable)}
                  className="px-2.5 py-1 rounded-[6px] bg-[var(--surface-2)] border border-[var(--line)] text-xs text-[var(--ink)] hover:bg-[var(--surface)] flex items-center space-x-1"
                >
                  <Table className="w-3.5 h-3.5 text-teal-400" />
                  <span>{showClimateDataTable ? "Show Chart" : "Data Table"}</span>
                </button>
              </div>
            </div>

            {!showClimateDataTable ? (
              <div className="h-64 w-full">
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={monthlyClimateData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.08)" />
                    <XAxis dataKey="month" stroke="#94a3b8" fontSize={11} />
                    <YAxis stroke="#94a3b8" fontSize={11} domain={['auto', 'auto']} unit="°C" />
                    <Tooltip
                      contentStyle={{
                        backgroundColor: "var(--surface)",
                        borderColor: "var(--line)",
                        borderRadius: "8px",
                        fontSize: "12px",
                        color: "var(--ink)"
                      }}
                    />
                    <Line type="monotone" dataKey="max" name="Max Temp" stroke="#f43f5e" strokeWidth={2} dot={{ r: 3 }} />
                    <Line type="monotone" dataKey="mean" name="Mean Temp" stroke="#2dd4bf" strokeWidth={2.5} dot={{ r: 4 }} />
                    <Line type="monotone" dataKey="min" name="Min Temp" stroke="#38bdf8" strokeWidth={2} dot={{ r: 3 }} />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-xs text-left">
                  <thead className="bg-[var(--surface-2)] text-[var(--ink-2)] text-xs border-b border-[var(--line)]">
                    <tr>
                      <th className="p-2.5 text-left">Month</th>
                      <th className="p-2.5 text-right text-rose-300">Max (°C)</th>
                      <th className="p-2.5 text-right text-teal-300">Mean (°C)</th>
                      <th className="p-2.5 text-right text-sky-300">Min (°C)</th>
                      <th className="p-2.5 text-right">RH (%)</th>
                      <th className="p-2.5 text-right text-emerald-300">Comfortable Hours</th>
                      <th className="p-2.5 text-right text-amber-300">Overheated Hours</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-[var(--line)] text-xs tabular-nums text-[var(--ink)]">
                    {monthlyClimateData.map((row) => (
                      <tr key={row.month}>
                        <td className="p-2.5 font-bold text-white text-left">{row.month}</td>
                        <td className="p-2.5 text-right text-rose-300">{row.max}°C</td>
                        <td className="p-2.5 text-right text-teal-300">{row.mean}°C</td>
                        <td className="p-2.5 text-right text-sky-300">{row.min}°C</td>
                        <td className="p-2.5 text-right">{row.rh}%</td>
                        <td className="p-2.5 text-right text-emerald-300">{row.comfortableHours} h</td>
                        <td className="p-2.5 text-right text-amber-300">{row.warmHours} h</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>

          {/* Typical Local Buildings Feel Like This Summary */}
          <div className="rounded-xl border border-white/10 bg-white/[0.02] p-4 text-xs space-y-1.5">
            <div className="flex items-center space-x-2 text-teal-300 font-bold">
              <Info className="w-4 h-4 text-teal-400" />
              <span>How Typical Local Buildings Feel in {cityInfo.name}:</span>
            </div>
            <p className="text-slate-300 leading-relaxed">
              In conventional uninsulated masonry buildings (R2 baseline), occupants experience{" "}
              <strong className="text-white">
                {cityBaselines.r2.discomfort_ml_pct.toFixed(1)}% annual discomfort hours under the ML comfort model ({cityBaselines.r2.discomfort_adapt_pct.toFixed(1)}% under ASHRAE 55 Adaptive)
              </strong>
              . Solar heat gain through uninsulated roof slabs causes indoor operative temperatures to peak up to 6.5°C above outdoor ambient during summer afternoons.
            </p>
          </div>

          {/* Navigation */}
          <div className="flex justify-between pt-4 border-t border-white/10">
            <button
              type="button"
              onClick={() => setCurrentStep(2)}
              className="px-5 py-2.5 rounded-xl glass-button text-slate-200 text-xs font-semibold flex items-center space-x-2"
            >
              <ArrowLeft className="w-4 h-4" />
              <span>{lang === "hi" ? "वापस" : "Back"}</span>
            </button>
            <button
              type="button"
              onClick={() => setCurrentStep(4)}
              className="px-6 py-2.5 rounded-xl bg-teal-500 hover:bg-teal-400 text-slate-950 font-bold text-xs transition shadow-md flex items-center space-x-2"
            >
              <span>{lang === "hi" ? "अगला: कम्फर्ट प्रश्नावली" : "Next: Comfort Questionnaire"}</span>
              <ArrowRight className="w-4 h-4" />
            </button>
          </div>
        </section>
      )}

      {/* ========================================================================= */}
      {/* STEP 4: YOUR COMFORT (QUESTIONNAIRE & LIVE AREA COMPARISON) */}
      {/* ========================================================================= */}
      {currentStep === 4 && (
        <section className="rounded-2xl glass-card p-6 space-y-6">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-white/10 pb-4">
            <div>
              <h2 className="text-xl font-bold text-white flex items-center space-x-2">
                <Sliders className="w-5 h-5 text-teal-400" />
                <span>{lang === "hi" ? "चरण 4: आपकी कम्फर्ट प्रोफ़ाइल" : "Step 4: Your Occupant Comfort Profile"}</span>
              </h2>
              <p className="text-xs text-slate-400 mt-1">
                {lang === "hi"
                  ? "अपनी तापीय संवेदना और उपयोग की आदतें बताएं। प्रत्येक उत्तर सीधे परिणाम को प्रभावित करता है।"
                  : "Tell us how you experience indoor temperatures. Each question directly changes specific simulation and scoring outputs."}
              </p>
            </div>
            <span className="text-xs px-2.5 py-1 rounded-[6px] bg-teal-500/10 border border-teal-500/30 text-teal-300 font-medium">
              4 Wired Parameters
            </span>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
            {/* Left Column: 4 Wired Questions */}
            <div className="lg:col-span-7 space-y-4">
              {/* Question 1: Sensation Preference */}
              <div className="rounded-xl glass-panel p-4 space-y-2">
                <div className="flex items-center justify-between">
                  <div>
                    <label className="text-xs font-bold text-white block">1. Indoor Thermal Sensation Preference</label>
                    <span className="text-[11px] text-teal-300 font-medium block">
                      Changes: Comfort fit score weighting (feel sensitivity)
                    </span>
                  </div>
                </div>
                <div className="grid grid-cols-3 gap-2 pt-1">
                  {[
                    { id: "too_hot", label: "Too hot & stuffy" },
                    { id: "comfortable", label: "About right" },
                    { id: "too_cold", label: "Too chilly" }
                  ].map((opt) => (
                    <button
                      key={opt.id}
                      type="button"
                      onClick={() => setSummerFeel(opt.id)}
                      className={`p-2.5 rounded-lg text-left text-xs transition border ${
                        summerFeel === opt.id
                          ? "bg-teal-500/20 text-teal-200 border-teal-400/50 font-bold"
                          : "bg-white/[0.03] text-slate-300 border-white/5 hover:bg-white/[0.06]"
                      }`}
                    >
                      {opt.label}
                    </button>
                  ))}
                </div>
              </div>

              {/* Question 2: Daily Occupancy Duration */}
              <div className="rounded-xl glass-panel p-4 space-y-2">
                <div className="flex items-center justify-between">
                  <div>
                    <label className="text-xs font-bold text-white block">
                      2. Daily Occupancy Duration: <strong className="text-teal-300">{hoursOccupied} hours/day</strong>
                    </label>
                    <span className="text-[11px] text-teal-300 font-medium block">
                      Changes: Annual uncomfortable hours scored ({hoursOccupied} h/day × 365 = {Math.round(hoursOccupied * 365)} h/yr)
                    </span>
                  </div>
                </div>
                <input
                  type="range"
                  min="4"
                  max="24"
                  step="1"
                  value={hoursOccupied}
                  onChange={(e) => setHoursOccupied(Number(e.target.value))}
                  className="w-full accent-teal-400 cursor-pointer pt-1"
                />
                <div className="flex justify-between text-xs tabular-nums text-slate-400">
                  <span>4 h (Daytime work)</span>
                  <span>12 h (Evening/Night)</span>
                  <span>24 h (Continuous full-day)</span>
                </div>
              </div>

              {/* Question 3: Existing Cooling Available */}
              <div className="rounded-xl glass-panel p-4 space-y-2">
                <div className="flex items-center justify-between">
                  <div>
                    <label className="text-xs font-bold text-white block">3. Existing Cooling Available</label>
                    <span className="text-[11px] text-teal-300 font-medium block">
                      Changes: Free-running mode (0 HVAC energy) vs active HVAC cooling demand
                    </span>
                  </div>
                </div>
                <div className="grid grid-cols-3 gap-2 pt-1">
                  {[
                    { id: "none", label: "None (Free-running)" },
                    { id: "fan", label: "Ceiling fan only" },
                    { id: "AC", label: "Air Conditioner (AC)" }
                  ].map((opt) => (
                    <button
                      key={opt.id}
                      type="button"
                      onClick={() => setCooling(opt.id as CoolingType)}
                      className={`p-2.5 rounded-lg text-left text-xs transition border ${
                        cooling === opt.id
                          ? "bg-teal-500/20 text-teal-200 border-teal-400/50 font-bold"
                          : "bg-white/[0.03] text-slate-300 border-white/5 hover:bg-white/[0.06]"
                      }`}
                    >
                      {opt.label}
                    </button>
                  ))}
                </div>
              </div>

              {/* Question 4: Design Optimization Priority */}
              <div className="rounded-xl glass-panel p-4 space-y-2">
                <div className="flex items-center justify-between">
                  <div>
                    <label className="text-xs font-bold text-white block">4. Design Optimization Priority</label>
                    <span className="text-[11px] text-teal-300 font-medium block">
                      Changes: Preselected Pareto recommendation in Step 5
                    </span>
                  </div>
                </div>
                <div className="grid grid-cols-3 gap-2 pt-1">
                  {[
                    { id: "low energy", label: "Lowest Energy" },
                    { id: "balanced", label: "Balanced (Knee-Point)" },
                    { id: "comfort", label: "Lowest Discomfort" }
                  ].map((opt) => (
                    <button
                      key={opt.id}
                      type="button"
                      onClick={() => handlePriorityChange(opt.id as UserPriority)}
                      className={`p-2.5 rounded-lg text-left text-xs transition border ${
                        priority === opt.id
                          ? "bg-teal-500/20 text-teal-200 border-teal-400/50 font-bold"
                          : "bg-white/[0.03] text-slate-300 border-white/5 hover:bg-white/[0.06]"
                      }`}
                    >
                      {opt.label}
                    </button>
                  ))}
                </div>
              </div>
            </div>

            {/* Right Column: Live You vs Area Baseline Comparison */}
            <div className="lg:col-span-5 space-y-4">
              <div className="rounded-xl glass-panel p-5 space-y-4 border border-amber-500/30 bg-amber-950/10">
                <div className="flex items-center justify-between border-b border-white/10 pb-2">
                  <h3 className="text-xs font-bold text-white uppercase tracking-wider flex items-center space-x-2">
                    <Sparkles className="w-4 h-4 text-amber-400" />
                    <span>You vs Regional Area Baseline</span>
                  </h3>
                  <span className="text-xs tabular-nums text-amber-300 font-semibold">{cityInfo.name}</span>
                </div>

                {/* Comparison Matrix Table with Empirical Tooltips */}
                <table className="w-full text-xs text-left">
                  <thead className="bg-[var(--surface-2)] text-[var(--ink-2)] text-xs border-b border-[var(--line)]">
                    <tr>
                      <th className="p-2">Attribute</th>
                      <th className="p-2 text-teal-300">Your Answer</th>
                      <th className="p-2 text-amber-300">Area Baseline</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-white/5 text-slate-200">
                    <tr>
                      <td className="p-2 text-slate-400 font-medium">Dominant Sensation</td>
                      <td className="p-2 font-bold text-teal-200 capitalize">{summerFeel.replace("_", " ")}</td>
                      <td className="p-2 text-slate-300">
                        <span className="inline-flex items-center">
                          {selectedCity === "Shimla"
                            ? "Too cold (81%)"
                            : selectedCity === "Bengaluru"
                            ? "About right (61%)"
                            : selectedCity === "Mumbai"
                            ? "Too warm & muggy (68%)"
                            : "Too hot (74%)"}
                          <InfoTip
                            label="ASHRAE DB II Survey"
                            content="Source: ASHRAE Global Thermal Comfort Database II (India subset, empirical field survey)."
                          />
                        </span>
                      </td>
                    </tr>
                    <tr>
                      <td className="p-2 text-slate-400 font-medium">Model Typology</td>
                      <td className="p-2 font-bold text-teal-200">Single-Zone (~60 m²)</td>
                      <td className="p-2 text-slate-300">
                        <span className="inline-flex items-center">
                          R2 Uninsulated
                          <InfoTip
                            label="Reference Shelter R2"
                            content="Source: reference_results.csv (R2 baseline: 200 mm uninsulated brick masonry, 150 mm concrete roof, 0 mm insulation)."
                          />
                        </span>
                      </td>
                    </tr>
                    <tr>
                      <td className="p-2 text-slate-400 font-medium">Baseline Discomfort</td>
                      <td className="p-2 font-bold text-teal-200">Step 5 Package</td>
                      <td className="p-2 text-slate-300">
                        <span className="inline-flex items-center">
                          {cityBaselines.r2.discomfort_ml_pct.toFixed(1)}%
                          <InfoTip
                            label="Baseline Discomfort Hours"
                            content="Source: reference_results.csv (R2 baseline simulated in EnergyPlus across 8,760 hours)."
                          />
                        </span>
                      </td>
                    </tr>
                    <tr>
                      <td className="p-2 text-slate-400 font-medium">Baseline HVAC Energy</td>
                      <td className="p-2 font-bold text-teal-200">
                        {cooling === "none" ? "0 kWh/m² (Free-running)" : "Active cooling"}
                      </td>
                      <td className="p-2 text-slate-300">
                        <span className="inline-flex items-center">
                          {cityBaselines.r2.energy_kwh_per_m2_yr.toFixed(1)} kWh/m²/yr
                          <InfoTip
                            label="Baseline HVAC Energy"
                            content="Source: reference_results.csv (R2 baseline annual ideal-loads heating & cooling energy)."
                          />
                        </span>
                      </td>
                    </tr>
                  </tbody>
                </table>

                {/* Plain-Language Parameter Summary */}
                <div className="pt-2 border-t border-white/10 space-y-1.5 text-xs text-slate-300 leading-relaxed">
                  <div className="text-[11px] font-bold text-amber-300 uppercase tracking-wider">
                    How Your Inputs Shape Step 5
                  </div>
                  <p>
                    • <strong>Occupancy ({hoursOccupied} h/day)</strong>: Directly scales total annual uncomfortable hours scored ({Math.round(hoursOccupied * 365)} hours evaluated per year).
                  </p>
                  <p>
                    • <strong>Cooling Mode ({cooling === "none" ? "Free-running" : cooling})</strong>: {cooling === "none" ? "Evaluates passive comfort only with 0 HVAC energy burden." : "Simulates active ideal-loads cooling demand in kWh/m²/yr."}
                  </p>
                  <p>
                    • <strong>Priority ({priority})</strong>: Highlights the corresponding verified Pareto candidate in Step 5.
                  </p>
                </div>
              </div>
            </div>
          </div>

          {/* Navigation */}
          <div className="flex justify-between pt-4 border-t border-white/10">
            <button
              type="button"
              onClick={() => setCurrentStep(3)}
              className="px-5 py-2.5 rounded-xl glass-button text-slate-200 text-xs font-semibold flex items-center space-x-2"
            >
              <ArrowLeft className="w-4 h-4" />
              <span>{lang === "hi" ? "वापस" : "Back"}</span>
            </button>
            <button
              type="button"
              onClick={() => setCurrentStep(5)}
              className="px-6 py-2.5 rounded-xl bg-teal-500 hover:bg-teal-400 text-slate-950 font-bold text-xs transition shadow-md flex items-center space-x-2"
            >
              <span>Next: View Recommended Plan</span>
              <ArrowRight className="w-4 h-4" />
            </button>
          </div>
        </section>
      )}

      {/* ========================================================================= */}
      {/* STEP 5: YOUR PLAN (THREE HONEST PACKAGES, QUANTITIES ONLY, OUTPUTS) */}
      {/* ========================================================================= */}
      {currentStep === 5 && evaluation && activePackage && (
        <section className="space-y-6">
          {/* Header & Scenario Toggle */}
          <div className="rounded-2xl glass-card p-6 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
            <div>
              <div className="flex items-center space-x-2">
                <span className="px-2.5 py-1 rounded-[6px] text-xs font-semibold bg-[var(--surface-2)] border border-[var(--line)] text-[var(--ink)]">
                  {selectedCity} • SINGLE-ZONE SHELTER (60 m²)
                </span>
                <StatusPairing
                  confidenceTier={cityInfo.confidence}
                  isVerified={true}
                />
              </div>
              <h2 className="text-2xl font-extrabold text-white mt-2">
                Your Recommended Passive Design Plan
              </h2>
              <p className="text-xs text-slate-400 mt-0.5">
                Precomputed EnergyPlus Pareto-optimal envelopes tailored to your regional climate and comfort profile.
              </p>
            </div>

            {/* Climate Scenario Buttons with Not-Simulated Guard */}
            <div className="flex flex-col sm:items-end space-y-1.5">
              <span className="text-xs tabular-nums text-slate-400">Climate Scenario:</span>
              <div className="flex p-1 rounded-xl bg-white/[0.04] border border-white/10 gap-1">
                <button
                  type="button"
                  className="px-3 py-1.5 rounded-lg text-xs font-bold bg-teal-500 text-slate-950 shadow-md"
                >
                  Today (TMYx Weather)
                </button>
                <div className="relative group inline-block">
                  <button
                    type="button"
                    disabled={true}
                    className="px-3 py-1.5 rounded-lg text-xs font-semibold text-slate-500 opacity-60 cursor-not-allowed border border-white/5"
                  >
                    +1.5°C (Not simulated)
                  </button>
                  <div className="absolute bottom-full mb-2 left-1/2 -translate-x-1/2 hidden group-hover:block w-48 p-2 bg-slate-900 border border-white/15 rounded-lg text-[10px] text-slate-300 shadow-xl z-20 pointer-events-none">
                    Warming projections (+1.5°C) were not re-simulated in EnergyPlus for the Pareto candidate set. Disabled to prevent speculative numbers.
                  </div>
                </div>
                <div className="relative group inline-block">
                  <button
                    type="button"
                    disabled={true}
                    className="px-3 py-1.5 rounded-lg text-xs font-semibold text-slate-500 opacity-60 cursor-not-allowed border border-white/5"
                  >
                    +3.0°C (Not simulated)
                  </button>
                  <div className="absolute bottom-full mb-2 right-0 hidden group-hover:block w-48 p-2 bg-slate-900 border border-white/15 rounded-lg text-[10px] text-slate-300 shadow-xl z-20 pointer-events-none">
                    Warming projections (+3.0°C) were not re-simulated in EnergyPlus for the Pareto candidate set. Disabled to prevent speculative numbers.
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* Simple Mode Guidance Notice */}
          {simpleMode && (
            <div className="p-3 rounded-[8px] bg-[var(--surface-2)] border border-[var(--line)] text-xs text-[var(--ink)] flex items-center justify-between">
              <span>
                <strong>Simple Mode:</strong> Displaying plain-language shelter recommendations. Your primary recommended shelter is highlighted below.
              </span>
            </div>
          )}

          {/* THREE PACKAGES SIDE-BY-SIDE CARDS */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {[
              {
                id: "pkg_budget",
                key: "budget",
                pkg: evaluation.packages.budget,
                badge: "Lowest energy",
                roleText: simpleMode ? "Lowest energy demand" : "Min O2 (EnergyPlus verified)",
                desc: "Minimizes active heating and cooling energy demand on the verified Pareto front."
              },
              {
                id: "pkg_balanced",
                key: "balanced",
                pkg: evaluation.packages.balanced,
                badge: "Balanced",
                roleText: simpleMode ? "Best balance of comfort & energy" : "Knee Point (EnergyPlus verified)",
                desc: "Pareto knee-point design balancing annual uncomfortable hours and active HVAC energy."
              },
              {
                id: "pkg_best_comfort",
                key: "best_comfort",
                pkg: evaluation.packages.best_comfort,
                badge: "Lowest discomfort",
                roleText: simpleMode ? "Maximum comfort stability" : "Min O1 (EnergyPlus verified)",
                desc: "Minimizes annual uncomfortable hours on the verified Pareto front with maximum passive thermal stability."
              }
            ].map(({ id, key, pkg, badge, roleText, desc }) => {
              const isSelected = activePackageId === id;
              const hoursScored = pkg.hours_scored ?? Math.round(hoursOccupied * 365);
              const discomfortHours = pkg.annual_discomfort_hours ?? Math.round(hoursScored * (pkg.discomfort_pct / 100));

              return (
                <div
                  key={id}
                  onClick={() => setActivePackageId(id as any)}
                  className={`rounded-2xl p-6 transition-all duration-200 cursor-pointer flex flex-col justify-between space-y-5 border relative ${
                    isSelected
                      ? "glass-card border-teal-400/80 shadow-[0_0_35px_rgba(42,127,142,0.35)] scale-[1.01]"
                      : "glass-panel border-white/10 hover:border-white/20 opacity-90"
                  }`}
                >
                  {/* Top Badge & Role */}
                  <div className="flex items-center justify-between">
                    <div>
                      <span
                        className={`px-2.5 py-1 rounded-[6px] text-xs font-bold ${
                          isSelected
                            ? "bg-teal-500 text-slate-950"
                            : "bg-white/10 text-slate-300"
                        }`}
                      >
                        {badge}
                      </span>
                      <span className="text-[10px] text-teal-300/80 block mt-1">
                        {roleText}
                      </span>
                    </div>
                    <VerificationBadge status="verified" showTooltip={false} />
                  </div>

                  <p className="text-xs text-slate-300 leading-relaxed">{desc}</p>

                  {/* Discomfort & Energy Metrics (Prominent Real Numbers) */}
                  <div className="grid grid-cols-2 gap-2 pt-2 border-t border-white/10 text-xs">
                    <div className="bg-white/[0.02] p-2.5 rounded-xl border border-white/5 space-y-0.5">
                      <span className="text-[10px] text-slate-400 block">Annual Discomfort</span>
                      <span className="text-xl font-bold text-[var(--hot)] tabular-nums">{pkg.discomfort_pct}%</span>
                      <span className="text-[11px] text-slate-300 block tabular-nums">
                        {discomfortHours} h/yr ({hoursScored} h scored)
                      </span>
                      <span className="text-xs text-[var(--good)] block tabular-nums pt-1">
                        vs R2: {formatPercentagePoints(pkg.discomfort_pct - cityBaselines.r2.discomfort_ml_pct)}
                      </span>
                    </div>
                    <div className="bg-white/[0.02] p-2.5 rounded-xl border border-white/5 space-y-0.5">
                      <span className="text-[10px] text-slate-400 block">HVAC Energy (O2)</span>
                      {cooling === "none" ? (
                        <span className="text-xs font-bold text-[var(--ink)] block tabular-nums leading-snug pt-1" data-testid="energy-line">
                          0 kWh/m²/yr (free-running: no HVAC)
                        </span>
                      ) : (
                        <>
                          <span className="text-xl font-bold text-[var(--ink)] tabular-nums" data-testid="energy-line">
                            {pkg.annual_energy_kwh_per_m2}
                          </span>
                          <span className="text-[10px] text-slate-400 block">
                            kWh/m²/yr (Ideal-loads)
                          </span>
                        </>
                      )}
                      <span className="text-xs text-[var(--link)] block tabular-nums pt-1">
                        vs R2: {formatEnergyDelta((cooling === "none" ? 0 : pkg.annual_energy_kwh_per_m2) - cityBaselines.r2.energy_kwh_per_m2_yr)}
                      </span>
                    </div>
                  </div>

                  {/* Comfort Fit Score with Published Formula Tooltip */}
                  <div className="flex items-center justify-between p-3 rounded-xl bg-white/[0.02] border border-white/5">
                    <div>
                      <div className="flex items-center">
                        <span className="text-xs text-slate-400 uppercase font-semibold">Comfort Fit Score</span>
                        <InfoTip
                          label="Comfort Fit Score Formula"
                          content="Formula: max(10, min(98, round((100 - Discomfort%) × 0.85 × FeelMultiplier - EnergyPenalty + 15))). FeelMultiplier: 0.85 (Too Hot), 1.00 (About Right), 1.10 (Too Cold). EnergyPenalty: 0 for free-running, or (kWh/m² / 200) × 20 for active cooling."
                        />
                      </div>
                      <span className="text-[10px] text-slate-400 block">
                        Occupant Sensitivity: {summerFeel.replace("_", " ")}
                      </span>
                    </div>
                    <div className="text-right">
                      <span className="text-xl font-extrabold text-teal-300 tabular-nums">
                        {pkg.comfort_fit_score}
                      </span>
                      <span className="text-[10px] text-slate-400 block">/ 100</span>
                    </div>
                  </div>

                  {/* Materials list (quantities only) — CPWD DSR Null Gated */}
                  <div className="rounded-xl border border-white/10 bg-white/[0.02] p-3 text-xs space-y-1.5">
                    <div className="flex justify-between items-center text-xs text-slate-300 font-bold border-b border-white/5 pb-1">
                      <span>Materials list (quantities only):</span>
                      <span className="text-[10px] text-amber-300 font-normal">Rates unpopulated</span>
                    </div>
                    <div className="space-y-1 text-[11px] text-slate-300">
                      <div className="flex items-center space-x-1.5">
                        <Check className="w-3.5 h-3.5 text-teal-400 shrink-0" />
                        <span>Roof EPS: {(pkg.design_variables.roof_insulation_thickness * 1000).toFixed(0)} mm (~60 m² area)</span>
                      </div>
                      <div className="flex items-center space-x-1.5">
                        <Check className="w-3.5 h-3.5 text-teal-400 shrink-0" />
                        <span>Roof Coating: Reflective finish (absorptance: {pkg.design_variables.roof_solar_absorptance.toFixed(2)})</span>
                      </div>
                      <div className="flex items-center space-x-1.5">
                        <Check className="w-3.5 h-3.5 text-teal-400 shrink-0" />
                        <span>Wall Mineral Wool: {(pkg.design_variables.wall_insulation_thickness * 1000).toFixed(0)} mm (~72 m² net wall)</span>
                      </div>
                      <div className="flex items-center space-x-1.5">
                        <Check className="w-3.5 h-3.5 text-teal-400 shrink-0" />
                        <span>Windows & Overhang: {(pkg.design_variables.wwr > 1 ? pkg.design_variables.wwr : pkg.design_variables.wwr * 100).toFixed(0)}% WWR, {pkg.design_variables.shading_depth.toFixed(2)} m overhang</span>
                      </div>
                      <div className="flex items-center space-x-1.5">
                        <Check className="w-3.5 h-3.5 text-teal-400 shrink-0" />
                        <span>Natural Ventilation: {pkg.design_variables.ventilation_ach.toFixed(1)} ACH cross-ventilation louvers</span>
                      </div>
                    </div>
                    <span className="text-[10px] text-slate-400 block pt-1 border-t border-white/5">
                      CPWD DSR rate schedule unpopulated; showing engineering bill of quantities only.
                    </span>
                  </div>

                  {/* Selected / Select Button */}
                  {isSelected ? (
                    <button
                      type="button"
                      className="w-full py-2.5 rounded-xl text-xs font-bold bg-teal-500 text-slate-950 flex items-center justify-center space-x-1.5 shadow-md"
                    >
                      <Check className="w-4 h-4" />
                      <span>Selected ✓</span>
                    </button>
                  ) : (
                    <button
                      type="button"
                      onClick={() => setActivePackageId(id as any)}
                      className="w-full py-2.5 rounded-xl text-xs font-semibold glass-button text-slate-200 hover:text-white"
                    >
                      Select this plan
                    </button>
                  )}
                </div>
              );
            })}
          </div>

          {/* WHY THIS DESIGN WORKS SECTION (SHAP DRIVERS) */}
          <div className="rounded-2xl glass-card p-6 space-y-4">
            <div className="flex items-center justify-between border-b border-white/10 pb-3">
              <h3 className="text-sm font-bold text-white uppercase tracking-wider flex items-center space-x-2">
                <Sparkles className="w-4 h-4 text-teal-400" />
                <span>Why This Design Works (Physics & SHAP Explainability)</span>
              </h3>
              <span className="text-xs text-[var(--primary)] font-semibold">Design ID: <code>{activePackage.pareto_id}</code></span>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-xs text-slate-300">
              <div className="rounded-xl glass-panel p-4 space-y-1.5">
                <div className="text-teal-300 font-bold flex items-center space-x-1.5">
                  <span className="w-2 h-2 rounded-full bg-teal-400" />
                  <span>1. Roof Solar Shielding</span>
                </div>
                <p className="leading-relaxed">
                  Roof solar absorptance of {activePackage.design_variables.roof_solar_absorptance.toFixed(2)} coupled with {(activePackage.design_variables.roof_insulation_thickness * 1000).toFixed(0)} mm insulation suppresses peak slab heat flux, reducing daytime ceiling radiant temperatures.
                </p>
              </div>

              <div className="rounded-xl glass-panel p-4 space-y-1.5">
                <div className="text-teal-300 font-bold flex items-center space-x-1.5">
                  <span className="w-2 h-2 rounded-full bg-teal-400" />
                  <span>2. Window Overhang Protection</span>
                </div>
                <p className="leading-relaxed">
                  Exterior overhang projection of {activePackage.design_variables.shading_depth.toFixed(2)} m blocks direct summer solar window loads while admitting daylight.
                </p>
              </div>

              <div className="rounded-xl glass-panel p-4 space-y-1.5">
                <div className="text-teal-300 font-bold flex items-center space-x-1.5">
                  <span className="w-2 h-2 rounded-full bg-teal-400" />
                  <span>3. Nighttime Natural Ventilation</span>
                </div>
                <p className="leading-relaxed">
                  Controlled natural cross-ventilation at {activePackage.design_variables.ventilation_ach.toFixed(1)} ACH discharges stored daytime envelope warmth through cooler nocturnal breezes.
                </p>
              </div>
            </div>
          </div>

          {/* 12-MONTH BEFORE VS AFTER TEMPERATURE CHART */}
          <div className="rounded-2xl glass-card p-6 space-y-4">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-white/10 pb-3">
              <div>
                <h3 className="text-sm font-bold text-white uppercase tracking-wider flex items-center space-x-2">
                  <Thermometer className="w-4 h-4 text-teal-400" />
                  <span>12-Month Indoor Operative Temperature: Before vs After</span>
                </h3>
                <span className="text-[10px] text-slate-400">
                  Precomputed TMYx weather simulation across 8,760 hours.
                </span>
              </div>
              <div className="flex items-center space-x-3">
                <button
                  type="button"
                  onClick={() => setShowMonthlyDataTable(!showMonthlyDataTable)}
                  className="px-2.5 py-1 rounded-[6px] bg-[var(--surface-2)] border border-[var(--line)] text-xs text-[var(--ink)] hover:bg-[var(--surface)] flex items-center space-x-1"
                >
                  <Table className="w-3.5 h-3.5 text-teal-400" />
                  <span>{showMonthlyDataTable ? "Show Chart" : "Data Table"}</span>
                </button>
              </div>
            </div>

            {!showMonthlyDataTable ? (
              <div className="h-64 w-full">
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart
                    data={activePackage.monthly_performance.months.map((m, idx) => ({
                      month: m,
                      outdoor: activePackage.monthly_performance.outdoor_ta[idx],
                      baseline: activePackage.monthly_performance.indoor_ta_baseline_r2[idx],
                      recommended: activePackage.monthly_performance.indoor_ta_recommended[idx]
                    }))}
                    margin={{ top: 10, right: 10, left: -20, bottom: 0 }}
                  >
                    <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.08)" />
                    <XAxis dataKey="month" stroke="#94a3b8" fontSize={11} />
                    <YAxis stroke="#94a3b8" fontSize={11} domain={['auto', 'auto']} unit="°C" />
                    <Tooltip
                      contentStyle={{
                        backgroundColor: "var(--surface)",
                        borderColor: "var(--line)",
                        borderRadius: "8px",
                        fontSize: "12px",
                        color: "var(--ink)"
                      }}
                    />
                    <Line type="monotone" dataKey="outdoor" name="Outdoor Ambient" stroke="#94a3b8" strokeWidth={1.5} strokeDasharray="4 4" dot={false} />
                    <Line type="monotone" dataKey="baseline" name="Baseline (R2 Uninsulated)" stroke="#f43f5e" strokeWidth={2} dot={{ r: 3 }} />
                    <Line type="monotone" dataKey="recommended" name="Recommended Passive Package" stroke="#2dd4bf" strokeWidth={2.5} dot={{ r: 4 }} />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-xs text-left">
                  <thead className="bg-[var(--surface-2)] text-[var(--ink-2)] text-xs border-b border-[var(--line)]">
                    <tr>
                      <th className="p-2.5 text-left">Month</th>
                      <th className="p-2.5 text-right text-slate-400">Outdoor Ambient (°C)</th>
                      <th className="p-2.5 text-right text-rose-300">Baseline R2 (°C)</th>
                      <th className="p-2.5 text-right text-teal-300">Recommended Passive (°C)</th>
                      <th className="p-2.5 text-right text-emerald-300">Net Improvement</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-[var(--line)] text-xs tabular-nums text-[var(--ink)]">
                    {activePackage.monthly_performance.months.map((m, idx) => {
                      const out = activePackage.monthly_performance.outdoor_ta[idx];
                      const base = activePackage.monthly_performance.indoor_ta_baseline_r2[idx];
                      const rec = activePackage.monthly_performance.indoor_ta_recommended[idx];
                      const diff = (base - rec).toFixed(1);
                      return (
                        <tr key={m}>
                          <td className="p-2.5 font-bold text-white text-left">{m}</td>
                          <td className="p-2.5 text-slate-300 text-right">{out}°C</td>
                          <td className="p-2.5 text-rose-300 text-right">{base}°C</td>
                          <td className="p-2.5 text-teal-300 text-right">{rec}°C</td>
                          <td className="p-2.5 text-emerald-300 font-bold text-right">-{diff}°C cooler</td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            )}
          </div>

          {/* ACTION BUTTONS & OUTPUTS */}
          <div className="flex flex-wrap items-center justify-between gap-4 pt-2">
            <div className="flex flex-wrap items-center gap-2.5">
              {/* Output 1: Download Plan (PDF) */}
              <button
                type="button"
                onClick={handleDownloadPdf}
                disabled={pdfDownloading}
                className="px-5 py-2.5 rounded-xl bg-teal-500 hover:bg-teal-400 text-slate-950 font-bold text-xs transition shadow-md flex items-center space-x-2"
              >
                <Printer className="w-4 h-4" />
                <span>{pdfDownloading ? "Generating PDF..." : "Download plan (PDF)"}</span>
              </button>

              {/* Output 2: Copy Summary */}
              <button
                type="button"
                onClick={handleCopySummary}
                className="px-4 py-2.5 rounded-xl glass-button text-slate-200 hover:text-white text-xs font-semibold flex items-center space-x-2"
              >
                {copiedSummary ? <Check className="w-4 h-4 text-emerald-400" /> : <Copy className="w-4 h-4 text-teal-400" />}
                <span>{copiedSummary ? "Summary Copied! ✓" : "Copy summary"}</span>
              </button>

              {/* Output 3: Compare in Trade-offs (Deep Link) */}
              <Link
                href={`/pareto?city=${selectedCity}&design=${activePackage.pareto_id}`}
                className="px-4 py-2.5 rounded-xl glass-button text-slate-200 hover:text-white text-xs font-semibold flex items-center space-x-2"
              >
                <Layers className="w-4 h-4 text-teal-400" />
                <span>Compare in Trade-offs</span>
                <ArrowRight className="w-3.5 h-3.5" />
              </Link>

              {/* Compare 3 Packages Modal Trigger */}
              <button
                type="button"
                onClick={() => setIsCompareOpen(true)}
                className="px-4 py-2.5 rounded-xl glass-button text-slate-200 hover:text-white text-xs font-semibold flex items-center space-x-2"
              >
                <Table className="w-4 h-4 text-sky-400" />
                <span>Compare 3 Packages</span>
              </button>

              {/* Share URL */}
              <button
                type="button"
                onClick={handleShareLink}
                className="px-4 py-2.5 rounded-xl glass-button text-slate-200 hover:text-white text-xs font-semibold flex items-center space-x-2"
              >
                {copiedLink ? <Check className="w-4 h-4 text-emerald-400" /> : <Share2 className="w-4 h-4 text-teal-400" />}
                <span>{copiedLink ? "Link Copied!" : "Share Link"}</span>
              </button>
            </div>

            {/* Switch to Expert Mode Button */}
            <Link
              href="/evaluate"
              className="px-4 py-2.5 rounded-xl bg-indigo-600/30 hover:bg-indigo-600/50 border border-indigo-500/40 text-indigo-200 font-bold text-xs transition flex items-center space-x-2"
            >
              <Sliders className="w-4 h-4 text-indigo-300" />
              <span>Switch to Expert Mode</span>
              <ArrowRight className="w-4 h-4" />
            </Link>
          </div>

          {/* DEDICATED PRINT / PDF SPECIFICATION SHEET (Rendered only on print/PDF) */}
          <div className="hidden print:block space-y-6 pt-6 text-black bg-white">
            <div className="border-b-2 border-black pb-4">
              <h1 className="text-2xl font-bold">ClimateAdapt-Comfort — Passive Shelter Specification</h1>
              <p className="text-sm mt-1">
                Project City: <strong>{cityInfo.name}</strong> ({cityInfo.zone}) | Confidence Tier: <strong>{cityInfo.confidence}</strong>
              </p>
            </div>

            <div className="space-y-2">
              <h2 className="text-lg font-bold">1. Model Assumptions & Gating</h2>
              <ul className="list-disc pl-5 text-xs space-y-1">
                <li>Building Typology: Single-zone detached passive shelter (~60 m² carpet area, 3m ceiling height) per A-001.</li>
                <li>Occupancy: Continuous 24 h/day residential occupancy per A-002.</li>
                <li>Simulation Baseline: EnergyPlus {PIPELINE_CONSTANTS.ENERGYPLUS_VERSION} calibrated physics engine, fixed seed {PIPELINE_CONSTANTS.SEED}.</li>
                <li>Rates status: Rates unpopulated in official CPWD DSR schedule; engineering bill of quantities provided.</li>
              </ul>
            </div>

            <div className="space-y-2">
              <h2 className="text-lg font-bold">2. Recommended Design: {activePackage.name} (ID: {activePackage.pareto_id})</h2>
              <table className="w-full text-xs border border-collapse">
                <tbody>
                  <tr className="border"><td className="p-2 font-bold">Roof EPS Insulation</td><td className="p-2">{(activePackage.design_variables.roof_insulation_thickness * 1000).toFixed(0)} mm (~60 m² area)</td></tr>
                  <tr className="border"><td className="p-2 font-bold">Roof Solar Absorptance</td><td className="p-2">{activePackage.design_variables.roof_solar_absorptance.toFixed(2)} (High-SRI coating)</td></tr>
                  <tr className="border"><td className="p-2 font-bold">Wall Mineral Wool Insulation</td><td className="p-2">{(activePackage.design_variables.wall_insulation_thickness * 1000).toFixed(0)} mm (~72 m² area)</td></tr>
                  <tr className="border"><td className="p-2 font-bold">Wall Construction</td><td className="p-2">200 mm {activePackage.design_variables.wall_mass_class} mass masonry</td></tr>
                  <tr className="border"><td className="p-2 font-bold">Window-to-Wall Ratio (WWR)</td><td className="p-2">{(activePackage.design_variables.wwr > 1 ? activePackage.design_variables.wwr : activePackage.design_variables.wwr * 100).toFixed(0)}% with {activePackage.design_variables.shading_depth.toFixed(2)} m exterior overhang</td></tr>
                  <tr className="border"><td className="p-2 font-bold">Natural Ventilation</td><td className="p-2">{activePackage.design_variables.ventilation_ach.toFixed(1)} ACH operable cross-ventilation openings</td></tr>
                </tbody>
              </table>
            </div>

            <div className="space-y-2">
              <h2 className="text-lg font-bold">3. Simulated Performance vs Baseline</h2>
              <table className="w-full text-xs border border-collapse">
                <tbody>
                  <tr className="border"><td className="p-2 font-bold">Annual Discomfort Hours</td><td className="p-2">{activePackage.discomfort_pct}% ({activePackage.annual_discomfort_hours ?? Math.round(hoursOccupied * 365 * activePackage.discomfort_pct / 100)} h/yr)</td></tr>
                  <tr className="border"><td className="p-2 font-bold">HVAC Cooling Demand</td><td className="p-2">{cooling === "none" ? "0 kWh/m²/yr (free-running: no HVAC)" : `${activePackage.annual_energy_kwh_per_m2} kWh/m²/yr (${activePackage.cooling_mode})`}</td></tr>
                  <tr className="border"><td className="p-2 font-bold">Delta vs Uninsulated R2 Baseline</td><td className="p-2">Discomfort: {formatPercentagePoints(activePackage.discomfort_pct - cityBaselines.r2.discomfort_ml_pct)} | Energy: {formatEnergyDelta((cooling === "none" ? 0 : activePackage.annual_energy_kwh_per_m2) - cityBaselines.r2.energy_kwh_per_m2_yr)}</td></tr>
                </tbody>
              </table>
            </div>

            <div className="text-[10px] text-gray-600 border-t pt-2">
              Simulation-based estimate, not a measured result or construction quote. Verify with local engineer.
            </div>
          </div>

          {/* Navigation */}
          <div className="flex justify-between pt-4 border-t border-white/10 print:hidden">
            <button
              type="button"
              onClick={() => setCurrentStep(4)}
              className="px-5 py-2.5 rounded-xl glass-button text-slate-200 text-xs font-semibold flex items-center space-x-2"
            >
              <ArrowLeft className="w-4 h-4" />
              <span>{lang === "hi" ? "वापस" : "Back"}</span>
            </button>
          </div>
        </section>
      )}

      {/* ========================================================================= */}
      {/* COMPARE PACKAGES MODAL / DRAWER */}
      {/* ========================================================================= */}
      {isCompareOpen && evaluation && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/75 backdrop-blur-md animate-fadeIn">
          <div className="relative w-full max-w-4xl max-h-[90vh] bg-slate-950 border border-white/15 rounded-2xl shadow-2xl p-6 overflow-y-auto space-y-6">
            <div className="flex items-center justify-between border-b border-white/10 pb-4">
              <div>
                <h3 className="text-lg font-bold text-white flex items-center space-x-2">
                  <Layers className="w-5 h-5 text-teal-400" />
                  <span>Detailed Side-by-Side Package Comparison</span>
                </h3>
                <p className="text-xs text-slate-400 mt-0.5">
                  {selectedCity} • {buildingType.toUpperCase()} • All Pareto-verified candidate envelopes
                </p>
              </div>
              <button
                type="button"
                onClick={() => setIsCompareOpen(false)}
                className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-white/10 transition"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Comparison Table */}
            <div className="overflow-x-auto">
              <table className="w-full text-xs text-left">
                <thead className="bg-[var(--surface-2)] text-[var(--ink-2)] text-xs border-b border-[var(--line)]">
                  <tr>
                    <th className="p-3">Specification / Metric</th>
                    <th className="p-3 text-teal-300">Lowest energy</th>
                    <th className="p-3 text-sky-300">Balanced (Recommended)</th>
                    <th className="p-3 text-amber-300">Lowest discomfort</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-[var(--line)] text-xs tabular-nums text-[var(--ink)]">
                  <tr>
                    <td className="p-3 font-medium text-slate-400">Comfort Fit Score</td>
                    <td className="p-3 font-bold text-teal-300">{evaluation.packages.budget.comfort_fit_score} / 100</td>
                    <td className="p-3 font-bold text-sky-300">{evaluation.packages.balanced.comfort_fit_score} / 100</td>
                    <td className="p-3 font-bold text-amber-300">{evaluation.packages.best_comfort.comfort_fit_score} / 100</td>
                  </tr>
                  <tr>
                    <td className="p-3 font-medium text-slate-400">Annual Discomfort Hours (O1 ML)</td>
                    <td className="p-3">
                      <div>{evaluation.packages.budget.discomfort_pct}% ({evaluation.packages.budget.annual_discomfort_hours ?? Math.round(hoursOccupied * 365 * evaluation.packages.budget.discomfort_pct / 100)} h/yr)</div>
                      <div className="text-xs text-[var(--good)] tabular-nums">
                        vs R1: {formatPercentagePoints(evaluation.packages.budget.discomfort_pct - cityBaselines.r1.discomfort_ml_pct)}
                      </div>
                      <div className="text-xs text-[var(--good)] tabular-nums">
                        vs R2: {formatPercentagePoints(evaluation.packages.budget.discomfort_pct - cityBaselines.r2.discomfort_ml_pct)}
                      </div>
                    </td>
                    <td className="p-3">
                      <div>{evaluation.packages.balanced.discomfort_pct}% ({evaluation.packages.balanced.annual_discomfort_hours ?? Math.round(hoursOccupied * 365 * evaluation.packages.balanced.discomfort_pct / 100)} h/yr)</div>
                      <div className="text-xs text-[var(--good)] tabular-nums">
                        vs R1: {formatPercentagePoints(evaluation.packages.balanced.discomfort_pct - cityBaselines.r1.discomfort_ml_pct)}
                      </div>
                      <div className="text-xs text-[var(--good)] tabular-nums">
                        vs R2: {formatPercentagePoints(evaluation.packages.balanced.discomfort_pct - cityBaselines.r2.discomfort_ml_pct)}
                      </div>
                    </td>
                    <td className="p-3">
                      <div>{evaluation.packages.best_comfort.discomfort_pct}% ({evaluation.packages.best_comfort.annual_discomfort_hours ?? Math.round(hoursOccupied * 365 * evaluation.packages.best_comfort.discomfort_pct / 100)} h/yr)</div>
                      <div className="text-xs text-[var(--good)] tabular-nums">
                        vs R1: {formatPercentagePoints(evaluation.packages.best_comfort.discomfort_pct - cityBaselines.r1.discomfort_ml_pct)}
                      </div>
                      <div className="text-xs text-[var(--good)] tabular-nums">
                        vs R2: {formatPercentagePoints(evaluation.packages.best_comfort.discomfort_pct - cityBaselines.r2.discomfort_ml_pct)}
                      </div>
                    </td>
                  </tr>
                  <tr>
                    <td className="p-3 font-medium text-slate-400">HVAC Energy (Ideal Loads)</td>
                    <td className="p-3">{cooling === "none" ? "0 kWh/m²/yr (free-running: no HVAC)" : `${evaluation.packages.budget.annual_energy_kwh_per_m2} kWh/m²/yr (${evaluation.packages.budget.cooling_mode})`}</td>
                    <td className="p-3">{cooling === "none" ? "0 kWh/m²/yr (free-running: no HVAC)" : `${evaluation.packages.balanced.annual_energy_kwh_per_m2} kWh/m²/yr (${evaluation.packages.balanced.cooling_mode})`}</td>
                    <td className="p-3">{cooling === "none" ? "0 kWh/m²/yr (free-running: no HVAC)" : `${evaluation.packages.best_comfort.annual_energy_kwh_per_m2} kWh/m²/yr (${evaluation.packages.best_comfort.cooling_mode})`}</td>
                  </tr>
                  <tr>
                    <td className="p-3 font-medium text-slate-400">Roof Insulation</td>
                    <td className="p-3">{(evaluation.packages.budget.design_variables.roof_insulation_thickness * 1000).toFixed(0)} mm EPS</td>
                    <td className="p-3">{(evaluation.packages.balanced.design_variables.roof_insulation_thickness * 1000).toFixed(0)} mm EPS</td>
                    <td className="p-3">{(evaluation.packages.best_comfort.design_variables.roof_insulation_thickness * 1000).toFixed(0)} mm EPS</td>
                  </tr>
                  <tr>
                    <td className="p-3 font-medium text-slate-400">Wall Insulation</td>
                    <td className="p-3">{(evaluation.packages.budget.design_variables.wall_insulation_thickness * 1000).toFixed(0)} mm Mineral Wool</td>
                    <td className="p-3">{(evaluation.packages.balanced.design_variables.wall_insulation_thickness * 1000).toFixed(0)} mm Mineral Wool</td>
                    <td className="p-3">{(evaluation.packages.best_comfort.design_variables.wall_insulation_thickness * 1000).toFixed(0)} mm Mineral Wool</td>
                  </tr>
                  <tr>
                    <td className="p-3 font-medium text-slate-400">Roof Solar Absorptance</td>
                    <td className="p-3">{evaluation.packages.budget.design_variables.roof_solar_absorptance.toFixed(2)}</td>
                    <td className="p-3">{evaluation.packages.balanced.design_variables.roof_solar_absorptance.toFixed(2)}</td>
                    <td className="p-3">{evaluation.packages.best_comfort.design_variables.roof_solar_absorptance.toFixed(2)}</td>
                  </tr>
                  <tr>
                    <td className="p-3 font-medium text-slate-400">Shading Depth</td>
                    <td className="p-3">{evaluation.packages.budget.design_variables.shading_depth.toFixed(2)} m</td>
                    <td className="p-3">{evaluation.packages.balanced.design_variables.shading_depth.toFixed(2)} m</td>
                    <td className="p-3">{evaluation.packages.best_comfort.design_variables.shading_depth.toFixed(2)} m</td>
                  </tr>
                  <tr>
                    <td className="p-3 font-medium text-slate-400">Window-to-Wall Ratio (WWR)</td>
                    <td className="p-3">{(evaluation.packages.budget.design_variables.wwr > 1 ? evaluation.packages.budget.design_variables.wwr : evaluation.packages.budget.design_variables.wwr * 100).toFixed(0)}%</td>
                    <td className="p-3">{(evaluation.packages.balanced.design_variables.wwr > 1 ? evaluation.packages.balanced.design_variables.wwr : evaluation.packages.balanced.design_variables.wwr * 100).toFixed(0)}%</td>
                    <td className="p-3">{(evaluation.packages.best_comfort.design_variables.wwr > 1 ? evaluation.packages.best_comfort.design_variables.wwr : evaluation.packages.best_comfort.design_variables.wwr * 100).toFixed(0)}%</td>
                  </tr>
                  <tr>
                    <td className="p-3 font-medium text-slate-400">Natural Ventilation</td>
                    <td className="p-3">{evaluation.packages.budget.design_variables.ventilation_ach.toFixed(1)} ACH</td>
                    <td className="p-3">{evaluation.packages.balanced.design_variables.ventilation_ach.toFixed(1)} ACH</td>
                    <td className="p-3">{evaluation.packages.best_comfort.design_variables.ventilation_ach.toFixed(1)} ACH</td>
                  </tr>
                </tbody>
              </table>
            </div>

            <div className="flex justify-end pt-4 border-t border-white/10">
              <button
                type="button"
                onClick={() => setIsCompareOpen(false)}
                className="px-5 py-2 rounded-xl bg-teal-500 text-slate-950 font-bold hover:bg-teal-400 transition text-xs"
              >
                Close Comparison
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default function RecommenderPage() {
  return (
    <Suspense fallback={<div className="p-12 text-center text-[var(--ink-2)] text-sm">Loading Plan...</div>}>
      <RecommenderContent />
    </Suspense>
  );
}
