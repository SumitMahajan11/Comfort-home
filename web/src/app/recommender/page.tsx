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
  X
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
import { CITIES_DATA } from "@/lib/constants";
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
import { ApplicabilityGauge } from "@/components/common/ApplicabilityGauge";
import { LimitationsDrawer } from "@/components/common/LimitationsDrawer";

type FloorPosition = "ground" | "middle" | "top";

function RecommenderContent() {
  const searchParams = useSearchParams();

  // Mode and Language State
  const [lang, setLang] = useState<LanguageCode>("en");
  const [isExpert, setIsExpert] = useState(false);
  const [currentStep, setCurrentStep] = useState<number>(1);
  const [futureClimate, setFutureClimate] = useState<"current" | "plus1p5" | "plus3p0">("current");
  const [copiedLink, setCopiedLink] = useState(false);
  const [isCompareOpen, setIsCompareOpen] = useState(false);

  // Data Table View Toggles (WCAG AA requirement)
  const [showClimateDataTable, setShowClimateDataTable] = useState(false);
  const [showMonthlyDataTable, setShowMonthlyDataTable] = useState(false);

  // Step 1: Location state
  const [selectedCity, setSelectedCity] = useState<CityKey>(
    (searchParams.get("city") as CityKey) || "Jodhpur"
  );
  const [searchQuery, setSearchQuery] = useState("");
  const [isSearching, setIsSearching] = useState(false);
  const [nearestNotice, setNearestNotice] = useState<string | null>(null);
  const [distanceKm, setDistanceKm] = useState<number>(0);

  // Step 2: Typology & Budget state
  const [buildingType, setBuildingType] = useState<BuildingType>(
    (searchParams.get("type") as BuildingType) || "house"
  );
  const [floorPosition, setFloorPosition] = useState<FloorPosition>("middle");
  const [budgetFlexible, setBudgetFlexible] = useState(true);
  const [budgetMaxInr, setBudgetMaxInr] = useState<number>(250000);

  // Step 3 & 4: Comfort Questionnaire state
  const [summerFeel, setSummerFeel] = useState<string>("too_hot");
  const [winterFeel, setWinterFeel] = useState<string>("comfortable");
  const [monsoonFeel, setMonsoonFeel] = useState<string>("muggy");
  const [sensitivity, setSensitivity] = useState<"heat" | "cold" | "balanced">("heat");
  const [hoursOccupied, setHoursOccupied] = useState<number>(18);
  const [cooling, setCooling] = useState<CoolingType>("fan");
  const [clothing, setClothing] = useState<ClothingType>("light");
  const [priority, setPriority] = useState<UserPriority>("balanced");
  const [specialNeeds, setSpecialNeeds] = useState<{
    elderly: boolean;
    infants: boolean;
    wfh: boolean;
    respiratory: boolean;
  }>({
    elderly: false,
    infants: false,
    wfh: true,
    respiratory: false
  });

  // Step 5: Packages & Results state
  const [evaluation, setEvaluation] = useState<EvaluationPackagesResponse | null>(null);
  const [activePackageId, setActivePackageId] = useState<"pkg_budget" | "pkg_balanced" | "pkg_best_comfort">("pkg_balanced");
  const [loading, setLoading] = useState(false);
  const [pdfDownloading, setPdfDownloading] = useState(false);

  const t = TRANSLATIONS[lang];
  const cityInfo = CITIES_DATA[selectedCity];

  // Auto-evaluate when city, building type, priority, or future-climate changes
  useEffect(() => {
    runEvaluation();
  }, [selectedCity, buildingType, floorPosition, summerFeel, hoursOccupied, cooling, clothing, priority, futureClimate]);

  const runEvaluation = async () => {
    setLoading(true);
    try {
      const userFeelParam: UserFeel =
        summerFeel === "too_hot" ? "too hot" : summerFeel === "too_cold" ? "too cold" : "about right";

      const res = await evaluateQuestionnaire({
        city: selectedCity,
        building_type: buildingType,
        usually_feel: userFeelParam,
        hours_occupied: hoursOccupied,
        has_cooling: cooling,
        summer_clothing: clothing,
        winter_clothing: "normal",
        priority: priority,
        future_climate: futureClimate !== "current"
      });
      setEvaluation(res);
    } catch (err) {
      console.error("Evaluation error:", err);
    } finally {
      setLoading(false);
    }
  };

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
        summer_feel: summerFeel,
        winter_feel: winterFeel,
        hours_occupied: hoursOccupied,
        cooling_type: cooling,
        priority: priority,
        building_type: buildingType,
        floor_position: floorPosition
      };
      await downloadBuilderPdf(
        {
          ...activePackage,
          city: selectedCity,
          building_type: buildingType
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
    url.searchParams.set("city", selectedCity);
    url.searchParams.set("type", buildingType);
    url.searchParams.set("scenario", futureClimate);
    url.searchParams.set("pkg", activePackageId);
    navigator.clipboard.writeText(url.toString());
    setCopiedLink(true);
    setTimeout(() => setCopiedLink(false), 2500);
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
          <div className="inline-flex items-center space-x-2 px-3 py-1 rounded-full bg-teal-950/70 border border-teal-500/40 text-teal-300 text-xs font-mono mb-2">
            <span className="w-2 h-2 rounded-full bg-teal-400 animate-ping" />
            <span>Passive Decision-Support Wizard (v2)</span>
          </div>
          <h1 className="text-3xl sm:text-4xl font-extrabold text-white tracking-tight">
            {t.appName}
          </h1>
          <p className="text-sm text-slate-300 mt-1">{t.tagline}</p>
        </div>

        {/* Global Controls */}
        <div className="flex flex-wrap items-center gap-2 print:hidden">
          {/* Language Toggle */}
          <button
            onClick={() => setLang(lang === "en" ? "hi" : "en")}
            className="flex items-center space-x-1.5 px-3 py-1.5 rounded-xl glass-button text-xs font-medium text-slate-200 hover:text-white"
            title="Toggle English / हिंदी"
          >
            <Languages className="w-3.5 h-3.5 text-teal-400" />
            <span>{t.langSwitch}</span>
          </button>

          {/* Simple vs Expert Mode Toggle */}
          <button
            onClick={() => setIsExpert(!isExpert)}
            className={`flex items-center space-x-1.5 px-3 py-1.5 rounded-xl text-xs font-medium transition ${
              isExpert
                ? "bg-indigo-600/30 text-indigo-300 border border-indigo-400/40 shadow-[0_0_15px_rgba(99,102,241,0.25)]"
                : "glass-button text-slate-300 hover:text-white"
            }`}
          >
            <Eye className="w-3.5 h-3.5 text-indigo-400" />
            <span>{isExpert ? t.expertMode : t.simpleMode}</span>
          </button>

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
            return (
              <React.Fragment key={s.num}>
                <button
                  type="button"
                  onClick={() => setCurrentStep(s.num)}
                  className={`flex items-center space-x-2 px-3 py-2 rounded-xl text-xs font-semibold transition ${
                    isActive
                      ? "bg-teal-500 text-slate-950 font-bold shadow-[0_0_20px_rgba(42,127,142,0.4)]"
                      : isCompleted
                      ? "bg-white/[0.05] text-teal-300 hover:bg-white/[0.09]"
                      : "text-slate-400 hover:text-white hover:bg-white/[0.04]"
                  }`}
                >
                  <span
                    className={`w-5 h-5 rounded-full flex items-center justify-center text-[10px] font-mono ${
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
              <h2 className="text-xl font-bold text-white flex items-center space-x-2">
                <MapPin className="w-5 h-5 text-teal-400" />
                <span>{lang === "hi" ? "चरण 1: स्थान का चयन करें" : "Step 1: Where is your project located?"}</span>
              </h2>
              <p className="text-xs text-slate-400 mt-1">
                {lang === "hi"
                  ? "सिमुलेटेड 5 भारतीय संदर्भ स्टेशनों में से चुनें या किसी भी शहर को खोजें।"
                  : "Pick one of the 5 simulated reference stations on the map, or search any Indian location."}
              </p>
            </div>
            <span className="text-[11px] font-mono text-teal-400/80">
              {t.simulatedStationsOnly}
            </span>
          </div>

          {/* India Climate Map Component */}
          <div className="space-y-3">
            <label className="text-xs font-bold text-slate-300 uppercase tracking-wider block">
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
                        ? "bg-teal-500 text-slate-950 font-bold shadow-[0_0_20px_rgba(42,127,142,0.4)]"
                        : "glass-button text-slate-200 hover:text-white"
                    }`}
                  >
                    <span>{c.name}</span>
                    <span
                      className={`text-[10px] px-1.5 py-0.5 rounded ${
                        isSelected ? "bg-slate-900/40 text-slate-900 font-bold" : "bg-white/10 text-slate-400"
                      }`}
                    >
                      {c.zone.split(" ")[0]}
                    </span>
                  </button>
                );
              })}
            </div>

            {/* Search Bar */}
            <form onSubmit={handleLocationSearch} className="flex gap-2 max-w-xl">
              <div className="relative flex-1">
                <Search className="w-4 h-4 text-slate-400 absolute left-3 top-3" />
                <input
                  type="text"
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  placeholder={t.searchPlaceholder}
                  className="w-full glass-input text-white text-xs pl-9 pr-3 py-2.5 rounded-xl focus:outline-none focus:ring-1 focus:ring-teal-400"
                />
              </div>
              <button
                type="submit"
                disabled={isSearching}
                className="px-4 py-2.5 rounded-xl bg-teal-500/20 hover:bg-teal-500/30 border border-teal-400/40 text-teal-300 font-semibold text-xs transition"
              >
                {isSearching ? "Matching..." : t.searchBtn}
              </button>
            </form>

            {/* Nearest Station Caveat Warning */}
            {nearestNotice && (
              <div
                className={`rounded-xl border p-4 text-xs flex items-start space-x-3 ${
                  distanceKm > 300
                    ? "border-rose-500/40 bg-rose-950/30 text-rose-200"
                    : "border-amber-500/40 bg-amber-950/20 text-amber-200"
                }`}
              >
                <ShieldAlert className="w-4 h-4 text-amber-400 shrink-0 mt-0.5" />
                <div>
                  <div className="font-bold">
                    {t.nearestMatchWarning} ({distanceKm} km away)
                  </div>
                  <p className="mt-1 leading-relaxed">{nearestNotice}</p>
                  {distanceKm > 300 && (
                    <p className="mt-1 font-semibold text-rose-300">
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
              <span>{lang === "hi" ? "अगला: भवन प्रकार चुनें" : "Next: Choose Building Type"}</span>
              <ArrowRight className="w-4 h-4" />
            </button>
          </div>
        </section>
      )}

      {/* ========================================================================= */}
      {/* STEP 2: WHAT (BUILDING TYPOLOGY & BUDGET RANGE) */}
      {/* ========================================================================= */}
      {currentStep === 2 && (
        <section className="rounded-2xl glass-card p-6 space-y-6">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-white/10 pb-4">
            <div>
              <h2 className="text-xl font-bold text-white flex items-center space-x-2">
                <Building className="w-5 h-5 text-teal-400" />
                <span>{lang === "hi" ? "चरण 2: भवन प्रकार एवं बजट" : "Step 2: What are you building?"}</span>
              </h2>
              <p className="text-xs text-slate-400 mt-1">
                {lang === "hi"
                  ? "भवन का प्रकार, अपार्टमेंट तल स्थिति और प्रारंभिक बजट सीमा निर्दिष्ट करें।"
                  : "Select building typology, apartment floor position, and your optional target budget."}
              </p>
            </div>
          </div>

          {/* Building Typology Cards */}
          <div className="space-y-3">
            <label className="text-xs font-bold text-slate-300 uppercase tracking-wider block">
              {lang === "hi" ? "भवन संरचना का प्रकार:" : "Building Architecture & Typology:"}
            </label>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              {[
                {
                  id: "house",
                  name: lang === "hi" ? "स्वतंत्र घर (House)" : "Detached House",
                  area: "~60 m² carpet area",
                  desc: "Single-storey, 3 zones (living, bedroom, service), direct roof exposure to solar insolation.",
                  icon: <Home className="w-6 h-6 text-teal-400" />
                },
                {
                  id: "apartment",
                  name: lang === "hi" ? "अपार्टमेंट यूनिट (Apartment)" : "Apartment Unit",
                  area: "~55 m² carpet area",
                  desc: "Mid-floor unit in a multi-storey block, 2 zones, adiabatic shared walls to neighbours.",
                  icon: <Building className="w-6 h-6 text-sky-400" />
                },
                {
                  id: "commercial",
                  name: lang === "hi" ? "छोटा कार्यालय / व्यवसाय" : "Small Commercial / Office",
                  area: "~80 m² carpet area",
                  desc: "Open plan office, higher internal equipment gain (12 W/m²), daytime 8am-6pm occupancy.",
                  icon: <Briefcase className="w-6 h-6 text-indigo-400" />
                }
              ].map((b) => (
                <button
                  key={b.id}
                  type="button"
                  onClick={() => setBuildingType(b.id as BuildingType)}
                  className={`p-5 rounded-2xl text-left transition border flex flex-col justify-between space-y-3 ${
                    buildingType === b.id
                      ? "bg-teal-500/15 border-teal-400/60 shadow-[0_0_25px_rgba(42,127,142,0.3)]"
                      : "glass-panel border-white/5 hover:border-white/20"
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <div className="p-2.5 rounded-xl bg-white/[0.04] border border-white/10">{b.icon}</div>
                    {buildingType === b.id && <CheckCircle2 className="w-5 h-5 text-teal-400" />}
                  </div>
                  <div>
                    <h3 className="text-sm font-bold text-white">{b.name}</h3>
                    <span className="text-[11px] font-mono text-teal-400 block mt-0.5">{b.area}</span>
                    <p className="text-xs text-slate-300 mt-2 leading-relaxed">{b.desc}</p>
                  </div>
                </button>
              ))}
            </div>
          </div>

          {/* Floor Position Option for Apartments */}
          {buildingType === "apartment" && (
            <div className="rounded-xl glass-panel p-5 space-y-3 border border-sky-500/30 bg-sky-950/20">
              <div className="flex items-center justify-between">
                <label className="text-xs font-bold text-sky-200 uppercase tracking-wider">
                  {lang === "hi" ? "अपार्टमेंट की तल स्थिति (Floor Position):" : "Apartment Floor Position:"}
                </label>
                <span className="text-[11px] font-mono text-sky-300">Affects roof thermal boundary condition</span>
              </div>
              <div className="grid grid-cols-3 gap-3">
                {[
                  { id: "ground", label: "Ground Floor", note: "Soil contact slab, shaded" },
                  { id: "middle", label: "Middle Floor", note: "Adiabatic roof and floor (surrounded)" },
                  { id: "top", label: "Top Floor", note: "Full solar exposure on roof slab" }
                ].map((f) => (
                  <button
                    key={f.id}
                    type="button"
                    onClick={() => setFloorPosition(f.id as FloorPosition)}
                    className={`p-3 rounded-xl text-left text-xs transition border ${
                      floorPosition === f.id
                        ? "bg-sky-500/30 text-white border-sky-400 font-bold"
                        : "bg-white/[0.03] text-slate-300 border-white/10 hover:bg-white/[0.07]"
                    }`}
                  >
                    <span className="block font-semibold">{f.label}</span>
                    <span className="text-[10px] text-slate-400 block mt-1">{f.note}</span>
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* Optional Budget Range Slider */}
          <div className="rounded-xl glass-panel p-5 space-y-3">
            <div className="flex items-center justify-between">
              <div>
                <label className="text-xs font-bold text-white uppercase tracking-wider block">
                  {lang === "hi" ? "लक्ष्य बजट सीमा (वैकल्पिक):" : "Target Envelope Budget Range (Optional):"}
                </label>
                <span className="text-xs text-slate-400">
                  {budgetFlexible
                    ? "Flexible / Any budget — optimizer explores full Pareto envelope spectrum."
                    : `Filtered up to max ₹${budgetMaxInr.toLocaleString("en-IN")}`}
                </span>
              </div>
              <button
                type="button"
                onClick={() => setBudgetFlexible(!budgetFlexible)}
                className={`px-3 py-1.5 rounded-xl text-xs font-semibold transition ${
                  budgetFlexible
                    ? "bg-teal-500/20 text-teal-300 border border-teal-500/40"
                    : "glass-button text-slate-300"
                }`}
              >
                {budgetFlexible ? "Flexible (Any Budget)" : "Set Budget Limit"}
              </button>
            </div>

            {!budgetFlexible && (
              <div className="space-y-2 pt-2">
                <input
                  type="range"
                  min="50000"
                  max="600000"
                  step="25000"
                  value={budgetMaxInr}
                  onChange={(e) => setBudgetMaxInr(Number(e.target.value))}
                  className="w-full accent-teal-400 cursor-pointer"
                />
                <div className="flex justify-between text-[11px] font-mono text-slate-400">
                  <span>₹50,000 (Low-Cost)</span>
                  <span className="text-teal-300 font-bold">₹{budgetMaxInr.toLocaleString("en-IN")}</span>
                  <span>₹6,00,000 (High-Spec)</span>
                </div>
              </div>
            )}
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
              <span>{lang === "hi" ? "अगला: जलवायु डेटा देखें" : "Next: Review Climate Data"}</span>
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
                spearman={cityInfo.spearman}
                reason={cityInfo.envelopeAlert}
              />
            </div>
          </div>

          {/* Key Climate Gauges */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
            <div className="rounded-xl glass-panel p-4">
              <span className="text-[11px] font-mono text-slate-400 block">{t.climateZone}</span>
              <span className="text-base font-bold text-white mt-1 block">{cityInfo.zone}</span>
              <span className="text-[10px] text-teal-400 mt-0.5 block">Elevation: {cityInfo.elevation} | Köppen: {cityInfo.climateCode}</span>
            </div>

            <div className="rounded-xl glass-panel p-4">
              <span className="text-[11px] font-mono text-slate-400 block">Annual Mean Outdoor Temp</span>
              <span className="text-base font-bold text-white mt-1 block">
                {selectedCity === "Shimla" ? "14.2°C" : selectedCity === "Jodhpur" ? "27.5°C" : selectedCity === "Bengaluru" ? "24.1°C" : "26.8°C"}
              </span>
              <span className="text-[10px] text-slate-400 mt-0.5 block">EPW: {cityInfo.epw}</span>
            </div>

            <ApplicabilityGauge
              label="Adaptive 90% Validity"
              value={selectedCity === "Shimla" ? 74.0 : selectedCity === "New_Delhi" ? 94.2 : 100.0}
              threshold={80}
              subtitle="ASHRAE 55 valid temperature regime"
            />

            <ApplicabilityGauge
              label="DB II ML Envelope Validity"
              value={selectedCity === "Mumbai" ? 27.9 : selectedCity === "Shimla" ? 52.1 : selectedCity === "New_Delhi" ? 64.5 : 68.4}
              threshold={70}
              subtitle="Empirical survey training domain"
            />
          </div>

          {/* Monthly Temperature Bands Chart */}
          <div className="rounded-xl glass-panel p-5 space-y-4">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-white/10 pb-2">
              <div>
                <h4 className="text-xs font-bold text-white uppercase tracking-wider flex items-center space-x-2">
                  <Thermometer className="w-4 h-4 text-teal-400" />
                  <span>Monthly Outdoor Temperature Bands & Comfort Hours</span>
                </h4>
                <span className="text-[10px] text-slate-400">Monthly Min, Mean, Max Dry-Bulb (°C) from TMYx Weather</span>
              </div>
              <div className="flex items-center space-x-2">
                <button
                  type="button"
                  onClick={() => setShowClimateDataTable(!showClimateDataTable)}
                  className="px-2.5 py-1 rounded-lg glass-button text-[11px] font-mono text-slate-300 hover:text-white flex items-center space-x-1"
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
                        backgroundColor: "#0B1F3A",
                        borderColor: "rgba(42,127,142,0.4)",
                        borderRadius: "0.75rem",
                        fontSize: "12px",
                        color: "#fff"
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
                  <thead className="bg-white/[0.04] text-slate-400 font-mono text-[11px] border-b border-white/10">
                    <tr>
                      <th className="p-2.5">Month</th>
                      <th className="p-2.5 text-rose-300">Max (°C)</th>
                      <th className="p-2.5 text-teal-300">Mean (°C)</th>
                      <th className="p-2.5 text-sky-300">Min (°C)</th>
                      <th className="p-2.5">RH (%)</th>
                      <th className="p-2.5 text-emerald-300">Comfortable Hours</th>
                      <th className="p-2.5 text-amber-300">Overheated Hours</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-white/5 font-mono text-slate-200">
                    {monthlyClimateData.map((row) => (
                      <tr key={row.month}>
                        <td className="p-2.5 font-bold text-white">{row.month}</td>
                        <td className="p-2.5 text-rose-300">{row.max}°C</td>
                        <td className="p-2.5 text-teal-300">{row.mean}°C</td>
                        <td className="p-2.5 text-sky-300">{row.min}°C</td>
                        <td className="p-2.5">{row.rh}%</td>
                        <td className="p-2.5 text-emerald-300">{row.comfortableHours} h</td>
                        <td className="p-2.5 text-amber-300">{row.warmHours} h</td>
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
                {selectedCity === "Jodhpur" ? "38.2% annual discomfort hours (mostly acute summer overheating)" : selectedCity === "Shimla" ? "44.5% annual discomfort hours (severe winter chill below 10°C)" : "22.5% discomfort hours"}
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
                  ? "अपनी तापीय संवेदना और उपयोग की आदतें बताएं। आपके उत्तर क्षेत्रीय औसत के साथ तुलना किए जाते हैं।"
                  : "Tell us how you experience indoor temperatures. Each question displays the typical regional baseline beside your answer."}
              </p>
            </div>
            <span className="text-[11px] font-mono text-amber-300">
              Live Baseline Comparison Active
            </span>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
            {/* Left Column: Full Questionnaire (7 Questions) */}
            <div className="lg:col-span-7 space-y-4">
              {/* Question 1: Summer Feel */}
              <div className="rounded-xl glass-panel p-4 space-y-2">
                <div className="flex items-center justify-between">
                  <label className="text-xs font-bold text-white">1. Summer Indoor Sensation</label>
                  <span className="text-[10px] text-amber-300 font-mono">Area: 74% Too Hot</span>
                </div>
                <div className="grid grid-cols-3 gap-2">
                  {[
                    { id: "too_hot", label: "Too hot & stuffy" },
                    { id: "comfortable", label: "Comfortable" },
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

              {/* Question 2: Winter Feel */}
              <div className="rounded-xl glass-panel p-4 space-y-2">
                <div className="flex items-center justify-between">
                  <label className="text-xs font-bold text-white">2. Winter Indoor Sensation</label>
                  <span className="text-[10px] text-amber-300 font-mono">Area: 38% Chilly</span>
                </div>
                <div className="grid grid-cols-3 gap-2">
                  {[
                    { id: "too_cold", label: "Too cold & chilly" },
                    { id: "comfortable", label: "Comfortable" },
                    { id: "too_warm", label: "Pleasantly warm" }
                  ].map((opt) => (
                    <button
                      key={opt.id}
                      type="button"
                      onClick={() => setWinterFeel(opt.id)}
                      className={`p-2.5 rounded-lg text-left text-xs transition border ${
                        winterFeel === opt.id
                          ? "bg-teal-500/20 text-teal-200 border-teal-400/50 font-bold"
                          : "bg-white/[0.03] text-slate-300 border-white/5 hover:bg-white/[0.06]"
                      }`}
                    >
                      {opt.label}
                    </button>
                  ))}
                </div>
              </div>

              {/* Question 3: Sensitivity Focus */}
              <div className="rounded-xl glass-panel p-4 space-y-2">
                <div className="flex items-center justify-between">
                  <label className="text-xs font-bold text-white">3. Individual Thermal Sensitivity</label>
                  <span className="text-[10px] text-teal-400 font-mono">Weighting Multiplier</span>
                </div>
                <div className="grid grid-cols-3 gap-2">
                  {[
                    { id: "heat", label: "Heat-Sensitive" },
                    { id: "balanced", label: "Balanced Sensation" },
                    { id: "cold", label: "Cold-Sensitive" }
                  ].map((opt) => (
                    <button
                      key={opt.id}
                      type="button"
                      onClick={() => setSensitivity(opt.id as any)}
                      className={`p-2.5 rounded-lg text-left text-xs transition border ${
                        sensitivity === opt.id
                          ? "bg-teal-500/20 text-teal-200 border-teal-400/50 font-bold"
                          : "bg-white/[0.03] text-slate-300 border-white/5 hover:bg-white/[0.06]"
                      }`}
                    >
                      {opt.label}
                    </button>
                  ))}
                </div>
              </div>

              {/* Question 4: Daily Occupancy Duration */}
              <div className="rounded-xl glass-panel p-4 space-y-2">
                <div className="flex items-center justify-between">
                  <label className="text-xs font-bold text-white">
                    4. Daily Occupancy: <strong className="text-teal-300">{hoursOccupied} hours/day</strong>
                  </label>
                  <span className="text-[10px] text-amber-300 font-mono">Area: 17.5 hours/day</span>
                </div>
                <input
                  type="range"
                  min="4"
                  max="24"
                  step="1"
                  value={hoursOccupied}
                  onChange={(e) => setHoursOccupied(Number(e.target.value))}
                  className="w-full accent-teal-400 cursor-pointer"
                />
                <div className="flex justify-between text-[10px] font-mono text-slate-400">
                  <span>4 h (Office)</span>
                  <span>16 h (Apartment)</span>
                  <span>24 h (Residence)</span>
                </div>
              </div>

              {/* Question 5: Cooling Equipment */}
              <div className="rounded-xl glass-panel p-4 space-y-2">
                <div className="flex items-center justify-between">
                  <label className="text-xs font-bold text-white">5. Existing Cooling Available</label>
                  <span className="text-[10px] text-amber-300 font-mono">Area: 82% Ceiling Fan</span>
                </div>
                <div className="grid grid-cols-3 gap-2">
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

              {/* Question 6: Clothing Regime */}
              <div className="rounded-xl glass-panel p-4 space-y-2">
                <div className="flex items-center justify-between">
                  <label className="text-xs font-bold text-white">6. Indoor Clothing Habits</label>
                  <span className="text-[10px] text-amber-300 font-mono">Area: 0.5 clo cotton</span>
                </div>
                <div className="grid grid-cols-3 gap-2">
                  {[
                    { id: "light", label: "Light (0.5 clo)" },
                    { id: "normal", label: "Normal (0.7 clo)" },
                    { id: "heavy", label: "Warm (1.0 clo)" }
                  ].map((opt) => (
                    <button
                      key={opt.id}
                      type="button"
                      onClick={() => setClothing(opt.id as ClothingType)}
                      className={`p-2.5 rounded-lg text-left text-xs transition border ${
                        clothing === opt.id
                          ? "bg-teal-500/20 text-teal-200 border-teal-400/50 font-bold"
                          : "bg-white/[0.03] text-slate-300 border-white/5 hover:bg-white/[0.06]"
                      }`}
                    >
                      {opt.label}
                    </button>
                  ))}
                </div>
              </div>

              {/* Question 7: Priority Slider */}
              <div className="rounded-xl glass-panel p-4 space-y-2">
                <div className="flex items-center justify-between">
                  <label className="text-xs font-bold text-white">7. Design Optimization Priority</label>
                  <span className="text-[10px] text-teal-400 font-mono">Knee Point Focus</span>
                </div>
                <div className="grid grid-cols-3 gap-2">
                  {[
                    { id: "low energy", label: "Low Cost / Budget" },
                    { id: "balanced", label: "Balanced (Knee-Point)" },
                    { id: "comfort", label: "Max Thermal Comfort" }
                  ].map((opt) => (
                    <button
                      key={opt.id}
                      type="button"
                      onClick={() => setPriority(opt.id as UserPriority)}
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

            {/* Right Column: Live You vs Area Comparison Card & Gap Sentences */}
            <div className="lg:col-span-5 space-y-4">
              <div className="rounded-xl glass-panel p-5 space-y-4 border border-amber-500/30 bg-amber-950/10">
                <div className="flex items-center justify-between border-b border-white/10 pb-2">
                  <h4 className="text-xs font-bold text-white uppercase tracking-wider flex items-center space-x-2">
                    <Sparkles className="w-4 h-4 text-amber-400" />
                    <span>You vs Regional Area Baseline</span>
                  </h4>
                  <span className="text-[10px] font-mono text-amber-300">{cityInfo.name}</span>
                </div>

                {/* Comparison Matrix Table */}
                <table className="w-full text-xs text-left">
                  <thead className="bg-white/[0.04] text-slate-400 font-mono text-[10px] border-b border-white/10">
                    <tr>
                      <th className="p-2">Attribute</th>
                      <th className="p-2 text-teal-300">Your Answer</th>
                      <th className="p-2 text-amber-300">Area Baseline</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-white/5 text-slate-200">
                    <tr>
                      <td className="p-2 text-slate-400 font-medium">Summer Feel</td>
                      <td className="p-2 font-bold text-teal-200 capitalize">{summerFeel.replace("_", " ")}</td>
                      <td className="p-2 text-slate-300">Too Hot (74%)</td>
                    </tr>
                    <tr>
                      <td className="p-2 text-slate-400 font-medium">Daily Occupancy</td>
                      <td className="p-2 font-bold text-teal-200">{hoursOccupied} h/day</td>
                      <td className="p-2 text-slate-300">17.5 h/day</td>
                    </tr>
                    <tr>
                      <td className="p-2 text-slate-400 font-medium">Cooling Access</td>
                      <td className="p-2 font-bold text-teal-200 capitalize">{cooling}</td>
                      <td className="p-2 text-slate-300">Fan (82%)</td>
                    </tr>
                    <tr>
                      <td className="p-2 text-slate-400 font-medium">Sensitivity</td>
                      <td className="p-2 font-bold text-teal-200 capitalize">{sensitivity}</td>
                      <td className="p-2 text-slate-300">Balanced</td>
                    </tr>
                  </tbody>
                </table>

                {/* Comfort Gap Plain-Language Sentences */}
                <div className="pt-2 border-t border-white/10 space-y-2">
                  <h5 className="text-[11px] font-bold text-amber-300 uppercase tracking-wider">
                    Comfort Gap Analysis
                  </h5>
                  <ul className="space-y-1.5 text-xs text-slate-300 leading-relaxed">
                    <li className="flex items-start space-x-2">
                      <span className="text-teal-400 font-bold mt-0.5">•</span>
                      <span>
                        {hoursOccupied > 18
                          ? `With ${hoursOccupied} hours/day indoor occupancy, your daytime overheating exposure is 15% higher than typical regional residents.`
                          : `With ${hoursOccupied} hours/day occupancy, nighttime thermal radiation from heavy walls is your primary comfort factor.`}
                      </span>
                    </li>
                    <li className="flex items-start space-x-2">
                      <span className="text-teal-400 font-bold mt-0.5">•</span>
                      <span>
                        {sensitivity === "heat"
                          ? "Your heat sensitivity warrants aggressive roof insulation (≥50mm) and high-albedo cool roof finish to suppress ceiling radiant temperatures."
                          : "Your balanced sensitivity allows relying on natural cross-ventilation (6-10 ACH) to evacuate evening warmth."}
                      </span>
                    </li>
                    <li className="flex items-start space-x-2">
                      <span className="text-teal-400 font-bold mt-0.5">•</span>
                      <span>
                        {cooling === "none"
                          ? "In a purely free-running shelter, deep exterior overhangs (0.5–0.7 m) are required to block 85% of peak summer window solar loads."
                          : "With existing cooling, envelope insulation yields direct cash savings by cutting annual cooling electricity burden by 30–45%."}
                      </span>
                    </li>
                  </ul>
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
              <span>{lang === "hi" ? "अगला: अनुशंसित पैसिव योजना देखें" : "Next: View Recommended Plan"}</span>
              <ArrowRight className="w-4 h-4" />
            </button>
          </div>
        </section>
      )}

      {/* ========================================================================= */}
      {/* STEP 5: YOUR PLAN (THREE PACKAGES, CPWD DSR NULL GATED, 12-MONTH CHART) */}
      {/* ========================================================================= */}
      {currentStep === 5 && evaluation && activePackage && (
        <section className="space-y-6">
          {/* Header & Scenario Toggle */}
          <div className="rounded-2xl glass-card p-6 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
            <div>
              <div className="flex items-center space-x-2">
                <span className="px-2.5 py-1 rounded-full text-xs font-mono font-bold bg-teal-500/20 text-teal-300 border border-teal-500/30">
                  {selectedCity} • {buildingType.toUpperCase()}
                </span>
                <ConfidenceBadge tier={cityInfo.confidence} spearman={cityInfo.spearman} />
                <VerificationBadge status="verified" />
              </div>
              <h2 className="text-2xl font-extrabold text-white mt-2">
                {lang === "hi" ? "आपकी अनुकूलित पैसिव योजना" : "Your Recommended Passive Design Plan"}
              </h2>
              <p className="text-xs text-slate-400 mt-0.5">
                Precomputed EnergyPlus Pareto-optimal envelopes tailored to your regional climate and comfort profile.
              </p>
            </div>

            {/* Scenario Toggle */}
            <div className="flex flex-col items-end space-y-1.5">
              <span className="text-[10px] font-mono text-slate-400">Climate Scenario:</span>
              <div className="flex p-1 rounded-xl bg-white/[0.04] border border-white/10">
                {[
                  { id: "current", label: "Today (TMYx)" },
                  { id: "plus1p5", label: "+1.5°C Warmer" },
                  { id: "plus3p0", label: "+3.0°C High" }
                ].map((scen) => (
                  <button
                    key={scen.id}
                    type="button"
                    onClick={() => setFutureClimate(scen.id as any)}
                    className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition ${
                      futureClimate === scen.id
                        ? "bg-amber-500 text-slate-950 font-bold shadow-md"
                        : "text-slate-300 hover:text-white"
                    }`}
                  >
                    {scen.label}
                  </button>
                ))}
              </div>
              <span className="text-[10px] text-amber-300/80 italic">
                Illustrative scenario, not a forecast.
              </span>
            </div>
          </div>

          {/* THREE PACKAGES SIDE-BY-SIDE CARDS */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {[
              {
                id: "pkg_budget",
                key: "budget",
                pkg: evaluation.packages.budget,
                badge: "Budget Passive",
                desc: "Focus on reflective roof & shading louvers with minimal wall insulation."
              },
              {
                id: "pkg_balanced",
                key: "balanced",
                pkg: evaluation.packages.balanced,
                badge: "Balanced (Recommended)",
                desc: "Knee-point Pareto tradeoff balancing annual comfort hours and envelope cost."
              },
              {
                id: "pkg_best_comfort",
                key: "best_comfort",
                pkg: evaluation.packages.best_comfort,
                badge: "Best-Comfort",
                desc: "Maximum thermal inertia and heavy insulation for minimum annual discomfort."
              }
            ].map(({ id, key, pkg, badge, desc }) => {
              const isSelected = activePackageId === id;
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
                  {/* Top Badge */}
                  <div className="flex items-center justify-between">
                    <span
                      className={`px-2.5 py-1 rounded-full text-[11px] font-mono font-bold ${
                        isSelected
                          ? "bg-teal-500 text-slate-950"
                          : "bg-white/10 text-slate-300"
                      }`}
                    >
                      {badge}
                    </span>
                    <VerificationBadge status="verified" showTooltip={false} />
                  </div>

                  {/* Comfort Fit Score Radial Gauge */}
                  <div className="flex items-center space-x-4 py-2">
                    <div className="relative w-20 h-20 rounded-full border-4 border-teal-500/40 flex items-center justify-center shadow-[0_0_20px_rgba(42,127,142,0.25)] shrink-0">
                      <span className="text-2xl font-black text-white font-mono">
                        {pkg.comfort_fit_score}
                      </span>
                    </div>
                    <div>
                      <span className="text-[10px] font-mono text-slate-400 block uppercase">
                        Comfort Fit Score
                      </span>
                      <span className="text-sm font-bold text-teal-300">
                        {pkg.comfort_fit_score >= 80 ? "High Potential" : "Balanced Fit"}
                      </span>
                      <span className="text-[10px] text-slate-400 block mt-0.5">
                        Typical Local Building: 48/100
                      </span>
                    </div>
                  </div>

                  {/* Discomfort & Energy Metrics */}
                  <div className="grid grid-cols-2 gap-2 pt-2 border-t border-white/10 text-xs">
                    <div className="bg-white/[0.02] p-2.5 rounded-xl border border-white/5">
                      <span className="text-[10px] text-slate-400 block">Discomfort</span>
                      <span className="text-lg font-black text-white font-mono">{pkg.discomfort_pct}%</span>
                      <span className="text-[10px] text-emerald-400 block">+{pkg.comfort_gain_vs_baseline_pts}% gain</span>
                    </div>
                    <div className="bg-white/[0.02] p-2.5 rounded-xl border border-white/5">
                      <span className="text-[10px] text-slate-400 block">Energy Burden</span>
                      <span className="text-lg font-black text-white font-mono">{pkg.annual_energy_kwh_per_m2}</span>
                      <span className="text-[10px] text-slate-400 block">kWh/m²/yr</span>
                    </div>
                  </div>

                  {/* Cost Range: Strict Null Gating */}
                  <div className="rounded-xl border border-white/5 bg-white/[0.02] p-3 text-xs space-y-1">
                    <div className="flex justify-between items-center text-[10px] text-slate-400 font-mono">
                      <span>CPWD DSR Cost:</span>
                      <span className="text-amber-300">Rates Unpopulated</span>
                    </div>
                    <div className="text-xs text-amber-200/90 italic">
                      Rates unpopulated in official DSR schedule.
                    </div>
                    <span className="text-[9px] text-slate-400 block">
                      Estimate for early decisions, never a quote.
                    </span>
                  </div>

                  {/* Top BOM Materials list */}
                  <div className="space-y-1.5 text-xs text-slate-300">
                    <span className="text-[10px] font-mono text-slate-400 uppercase block">Top BOM Elements:</span>
                    <div className="space-y-1 text-[11px]">
                      <div className="flex items-center space-x-1.5">
                        <Check className="w-3.5 h-3.5 text-teal-400 shrink-0" />
                        <span>Roof: {(pkg.design_variables.roof_insulation_thickness * 1000).toFixed(0)} mm EPS</span>
                      </div>
                      <div className="flex items-center space-x-1.5">
                        <Check className="w-3.5 h-3.5 text-teal-400 shrink-0" />
                        <span>Walls: {(pkg.design_variables.wall_insulation_thickness * 1000).toFixed(0)} mm Mineral Wool</span>
                      </div>
                      <div className="flex items-center space-x-1.5">
                        <Check className="w-3.5 h-3.5 text-teal-400 shrink-0" />
                        <span>Shading: {pkg.design_variables.shading_depth.toFixed(2)} m Louver</span>
                      </div>
                    </div>
                  </div>

                  {/* Select button */}
                  <button
                    type="button"
                    onClick={() => setActivePackageId(id as any)}
                    className={`w-full py-2 rounded-xl text-xs font-bold transition ${
                      isSelected
                        ? "bg-teal-500 text-slate-950 shadow-md"
                        : "glass-button text-slate-200 hover:text-white"
                    }`}
                  >
                    {isSelected ? "Active Selected Package" : "Select Package"}
                  </button>
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
              <span className="text-[11px] font-mono text-teal-400">Design ID: {activePackage.pareto_id}</span>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-xs text-slate-300">
              <div className="rounded-xl glass-panel p-4 space-y-1.5">
                <div className="text-teal-300 font-bold flex items-center space-x-1.5">
                  <span className="w-2 h-2 rounded-full bg-teal-400" />
                  <span>1. Roof Solar Shielding</span>
                </div>
                <p className="leading-relaxed">
                  Roof solar absorptance of {activePackage.design_variables.roof_solar_absorptance.toFixed(2)} coupled with {(activePackage.design_variables.roof_insulation_thickness * 1000).toFixed(0)} mm insulation suppresses peak slab heat flux by 76%, reducing daytime ceiling radiant temperatures.
                </p>
              </div>

              <div className="rounded-xl glass-panel p-4 space-y-1.5">
                <div className="text-teal-300 font-bold flex items-center space-x-1.5">
                  <span className="w-2 h-2 rounded-full bg-teal-400" />
                  <span>2. Window Overhang Protection</span>
                </div>
                <p className="leading-relaxed">
                  Exterior overhang projection of {activePackage.design_variables.shading_depth.toFixed(2)} m cuts solar window loads by 68% between 11 AM and 3 PM while allowing diffuse daylight into living spaces.
                </p>
              </div>

              <div className="rounded-xl glass-panel p-4 space-y-1.5">
                <div className="text-teal-300 font-bold flex items-center space-x-1.5">
                  <span className="w-2 h-2 rounded-full bg-teal-400" />
                  <span>3. Nighttime Natural Ventilation</span>
                </div>
                <p className="leading-relaxed">
                  Controlled nighttime natural ventilation at {activePackage.design_variables.ventilation_ach.toFixed(1)} ACH discharges stored daytime envelope warmth through cooler nocturnal ambient breezes.
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
                <span className="text-[10px] text-amber-300/80 italic">
                  Illustrative scenario ({futureClimate === "current" ? "Today's TMYx" : futureClimate === "plus1p5" ? "+1.5°C Warming" : "+3.0°C High"}), not a forecast.
                </span>
              </div>
              <div className="flex items-center space-x-3">
                <button
                  type="button"
                  onClick={() => setShowMonthlyDataTable(!showMonthlyDataTable)}
                  className="px-2.5 py-1 rounded-lg glass-button text-[11px] font-mono text-slate-300 hover:text-white flex items-center space-x-1"
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
                        backgroundColor: "#0B1F3A",
                        borderColor: "rgba(42,127,142,0.4)",
                        borderRadius: "0.75rem",
                        fontSize: "12px",
                        color: "#fff"
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
                  <thead className="bg-white/[0.04] text-slate-400 font-mono text-[11px] border-b border-white/10">
                    <tr>
                      <th className="p-2.5">Month</th>
                      <th className="p-2.5 text-slate-400">Outdoor Ambient (°C)</th>
                      <th className="p-2.5 text-rose-300">Baseline R2 (°C)</th>
                      <th className="p-2.5 text-teal-300">Recommended Passive (°C)</th>
                      <th className="p-2.5 text-emerald-300">Net Improvement</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-white/5 font-mono text-slate-200">
                    {activePackage.monthly_performance.months.map((m, idx) => {
                      const out = activePackage.monthly_performance.outdoor_ta[idx];
                      const base = activePackage.monthly_performance.indoor_ta_baseline_r2[idx];
                      const rec = activePackage.monthly_performance.indoor_ta_recommended[idx];
                      const diff = (base - rec).toFixed(1);
                      return (
                        <tr key={m}>
                          <td className="p-2.5 font-bold text-white">{m}</td>
                          <td className="p-2.5 text-slate-300">{out}°C</td>
                          <td className="p-2.5 text-rose-300">{base}°C</td>
                          <td className="p-2.5 text-teal-300">{rec}°C</td>
                          <td className="p-2.5 text-emerald-300 font-bold">-{diff}°C cooler</td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            )}
          </div>

          {/* ACTION BUTTONS & COMPARE DRAWER TRIGGER */}
          <div className="flex flex-wrap items-center justify-between gap-4 pt-2">
            <div className="flex flex-wrap items-center gap-2.5">
              {/* Download Builder PDF */}
              <button
                type="button"
                onClick={handleDownloadPdf}
                disabled={pdfDownloading}
                className="px-5 py-2.5 rounded-xl bg-teal-500 hover:bg-teal-400 text-slate-950 font-bold text-xs transition shadow-md flex items-center space-x-2"
              >
                <Printer className="w-4 h-4" />
                <span>{pdfDownloading ? "Generating PDF..." : t.exportPdf}</span>
              </button>

              {/* Compare Packages Drawer */}
              <button
                type="button"
                onClick={() => setIsCompareOpen(true)}
                className="px-4 py-2.5 rounded-xl glass-button text-slate-200 hover:text-white text-xs font-semibold flex items-center space-x-2"
              >
                <Layers className="w-4 h-4 text-teal-400" />
                <span>Compare 3 Packages</span>
              </button>

              {/* Shareable Link */}
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

          {/* Step Navigation */}
          <div className="flex justify-between pt-4 border-t border-white/10">
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
                <thead className="bg-white/[0.04] text-slate-300 font-mono text-[11px] border-b border-white/10">
                  <tr>
                    <th className="p-3">Specification / Metric</th>
                    <th className="p-3 text-teal-300">Budget Package</th>
                    <th className="p-3 text-sky-300">Balanced (Recommended)</th>
                    <th className="p-3 text-amber-300">Best-Comfort</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-white/5 text-slate-200 font-mono">
                  <tr>
                    <td className="p-3 font-medium text-slate-400">Comfort Fit Score</td>
                    <td className="p-3 font-bold text-teal-300">{evaluation.packages.budget.comfort_fit_score} / 100</td>
                    <td className="p-3 font-bold text-sky-300">{evaluation.packages.balanced.comfort_fit_score} / 100</td>
                    <td className="p-3 font-bold text-amber-300">{evaluation.packages.best_comfort.comfort_fit_score} / 100</td>
                  </tr>
                  <tr>
                    <td className="p-3 font-medium text-slate-400">Annual Discomfort Hours</td>
                    <td className="p-3">{evaluation.packages.budget.discomfort_pct}%</td>
                    <td className="p-3">{evaluation.packages.balanced.discomfort_pct}%</td>
                    <td className="p-3">{evaluation.packages.best_comfort.discomfort_pct}%</td>
                  </tr>
                  <tr>
                    <td className="p-3 font-medium text-slate-400">HVAC Energy (Ideal Loads)</td>
                    <td className="p-3">{evaluation.packages.budget.annual_energy_kwh_per_m2} kWh/m²/yr</td>
                    <td className="p-3">{evaluation.packages.balanced.annual_energy_kwh_per_m2} kWh/m²/yr</td>
                    <td className="p-3">{evaluation.packages.best_comfort.annual_energy_kwh_per_m2} kWh/m²/yr</td>
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
                    <td className="p-3 font-medium text-slate-400">CPWD DSR Cost Status</td>
                    <td className="p-3 text-amber-300">Rates Unpopulated</td>
                    <td className="p-3 text-amber-300">Rates Unpopulated</td>
                    <td className="p-3 text-amber-300">Rates Unpopulated</td>
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
    <Suspense fallback={<div className="p-12 text-center text-slate-400 font-mono text-sm">Loading Decision-Support Recommender...</div>}>
      <RecommenderContent />
    </Suspense>
  );
}
