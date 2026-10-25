"use client";

import React, { useState } from "react";
import { CityKey } from "@/types";
import { CITIES_DATA } from "@/lib/constants";
import { MapPin, AlertTriangle, ShieldCheck, Thermometer } from "lucide-react";

interface IndiaClimateMapProps {
  selectedCity: CityKey;
  onSelectCity: (city: CityKey) => void;
  className?: string;
}

// Normalized SVG positions for the 5 cities on India boundary
const CITY_COORDS_SVG: Record<CityKey, { x: number; y: number }> = {
  Shimla: { x: 300, y: 155 },
  New_Delhi: { x: 310, y: 220 },
  Jodhpur: { x: 235, y: 260 },
  Mumbai: { x: 230, y: 460 },
  Bengaluru: { x: 290, y: 585 }
};

export const IndiaClimateMap: React.FC<IndiaClimateMapProps> = ({
  selectedCity,
  onSelectCity,
  className = ""
}) => {
  const [hoveredCity, setHoveredCity] = useState<CityKey | null>(null);

  const activeHover = hoveredCity || selectedCity;
  const activeCityInfo = CITIES_DATA[activeHover];

  return (
    <div className={`relative flex flex-col md:flex-row items-center justify-between rounded-2xl glass-panel p-6 overflow-hidden ${className}`}>
      {/* SVG Map of India with stylized boundary */}
      <div className="relative w-full max-w-[420px] aspect-[4/5] flex items-center justify-center">
        <svg
          viewBox="0 0 600 750"
          className="w-full h-full drop-shadow-2xl select-none"
          fill="none"
          xmlns="http://www.w3.org/2000/svg"
        >
          {/* Subtle grid background */}
          <defs>
            <pattern id="grid" width="30" height="30" patternUnits="userSpaceOnUse">
              <path d="M 30 0 L 0 0 0 30" fill="none" stroke="rgba(42, 127, 142, 0.12)" strokeWidth="0.8" />
            </pattern>
            <radialGradient id="glowTeal" cx="50%" cy="50%" r="50%">
              <stop offset="0%" stopColor="#2A7F8E" stopOpacity="0.8" />
              <stop offset="100%" stopColor="#2A7F8E" stopOpacity="0" />
            </radialGradient>
            <radialGradient id="glowAmber" cx="50%" cy="50%" r="50%">
              <stop offset="0%" stopColor="#F59E0B" stopOpacity="0.8" />
              <stop offset="100%" stopColor="#F59E0B" stopOpacity="0" />
            </radialGradient>
          </defs>

          <rect width="100%" height="100%" fill="url(#grid)" />

          {/* India Generalized Mainland Contour */}
          <path
            d="M 280,60 
               C 310,65 330,90 350,110 
               C 390,140 430,160 470,190 
               C 510,210 520,240 500,260 
               C 470,280 430,270 410,290 
               C 390,320 410,360 410,400 
               C 400,450 370,520 340,580 
               C 320,630 300,690 290,720 
               C 275,690 260,630 240,580 
               C 210,510 190,440 200,380 
               C 180,350 140,320 160,280 
               C 170,240 210,210 230,170 
               C 250,120 260,80 280,60 Z"
            className="fill-slate-200/90 dark:fill-[#0B1F3A]/70 stroke-teal-700/50 dark:stroke-teal-400/50"
            strokeWidth="2.5"
            strokeLinejoin="round"
          />

          {/* Connecting dashed climate lines */}
          <path
            d="M 300,155 L 310,220 L 235,260 L 230,460 L 290,585"
            className="stroke-teal-600/40 dark:stroke-sky-400/30"
            strokeWidth="1.5"
            strokeDasharray="4 4"
            fill="none"
          />

          {/* City Pin Markers */}
          {(Object.keys(CITY_COORDS_SVG) as CityKey[]).map((city) => {
            const { x, y } = CITY_COORDS_SVG[city];
            const isSelected = selectedCity === city;
            const isHovered = hoveredCity === city;
            const isMedium = CITIES_DATA[city].confidence === "Medium";
            const pinColor = isMedium ? "#0D9488" : "#D97706";

            return (
              <g
                key={city}
                className="cursor-pointer transition-all duration-200"
                onClick={() => onSelectCity(city)}
                onMouseEnter={() => setHoveredCity(city)}
                onMouseLeave={() => setHoveredCity(null)}
              >
                {/* Outer animated ripple */}
                <circle
                  cx={x}
                  cy={y}
                  r={isSelected ? 20 : 12}
                  fill={isMedium ? "url(#glowTeal)" : "url(#glowAmber)"}
                  className="animate-pulse"
                />

                {/* Main pin node */}
                <circle
                  cx={x}
                  cy={y}
                  r={isSelected ? 9 : 6.5}
                  fill={isSelected ? "#FFFFFF" : pinColor}
                  stroke={pinColor}
                  strokeWidth={isSelected ? 3 : 2}
                  className="transition-transform duration-150 hover:scale-125"
                />

                {/* City label tag on map */}
                <text
                  x={x + 12}
                  y={y + 4}
                  fontSize={isSelected ? "14" : "12"}
                  fontWeight={isSelected ? "700" : "600"}
                  fontFamily="system-ui"
                  className={`pointer-events-none select-none drop-shadow ${
                    isSelected ? "fill-teal-700 dark:fill-sky-300" : "fill-slate-900 dark:fill-slate-100"
                  }`}
                >
                  {CITIES_DATA[city].name}
                </text>
              </g>
            );
          })}
        </svg>
      </div>

      {/* Selected City Inspector Card */}
      <div className="w-full md:w-[320px] mt-4 md:mt-0 flex flex-col justify-between space-y-4 glass-card rounded-2xl p-5 shadow-xl">
        <div>
          <div className="flex items-center justify-between">
            <span className="text-xs uppercase font-mono tracking-wider text-teal-400">
              Climate Zone Station
            </span>
            <span
              className={`inline-flex items-center space-x-1 px-2.5 py-0.5 rounded-full text-xs font-semibold ${
                activeCityInfo.confidence === "Medium"
                  ? "bg-emerald-950/80 text-emerald-400 border border-emerald-700/50"
                  : "bg-amber-950/80 text-amber-400 border border-amber-700/50"
              }`}
            >
              {activeCityInfo.confidence === "Medium" ? (
                <ShieldCheck className="w-3.5 h-3.5" />
              ) : (
                <AlertTriangle className="w-3.5 h-3.5" />
              )}
              <span>{activeCityInfo.confidence} Confidence</span>
            </span>
          </div>

          <h3 className="text-2xl font-bold text-white mt-1.5 flex items-center space-x-2">
            <span>{activeCityInfo.name}</span>
            <span className="text-xs font-mono font-normal text-slate-400">({activeCityInfo.elevation})</span>
          </h3>

          <p className="text-sm font-medium text-teal-300 mt-0.5">
            {activeCityInfo.zone}
          </p>
        </div>

        <p className="text-xs text-slate-300 leading-relaxed">
          {activeCityInfo.description}
        </p>

        {/* Warning banner for low confidence / Shimla */}
        {activeCityInfo.envelopeAlert && (
          <div className="p-2.5 rounded-lg bg-amber-950/40 border border-amber-600/40 text-amber-200 text-xs flex items-start space-x-2">
            <AlertTriangle className="w-4 h-4 text-amber-400 shrink-0 mt-0.5" />
            <span>{activeCityInfo.envelopeAlert}</span>
          </div>
        )}

        {/* Technical Station Attributes */}
        <div className="pt-2 border-t border-slate-800 grid grid-cols-2 gap-2 text-xs font-mono">
          <div>
            <span className="text-slate-400 block text-[10px]">Dual-Judge Rank (rs)</span>
            <span className="text-slate-100 font-bold">{activeCityInfo.spearman.toFixed(3)}</span>
          </div>
          <div>
            <span className="text-slate-400 block text-[10px]">EPW Source</span>
            <span className="text-slate-100 font-bold truncate block" title={activeCityInfo.epw}>
              TMYx / ISHRAE
            </span>
          </div>
        </div>

        <button
          onClick={() => onSelectCity(activeHover)}
          className="w-full py-2.5 px-4 rounded-lg bg-teal-600 hover:bg-teal-500 text-white font-medium text-xs transition shadow-md flex items-center justify-center space-x-1.5"
        >
          <MapPin className="w-4 h-4" />
          <span>Explore {activeCityInfo.name} Shelter Data</span>
        </button>
      </div>
    </div>
  );
};
