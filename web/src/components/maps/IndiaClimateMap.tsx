"use client";

import React, { useState } from "react";
import { CityKey } from "@/types";
import { CITIES_DATA } from "@/lib/constants";
import { AlertTriangle, ShieldCheck, MapPin } from "lucide-react";
import { Badge } from "@/components/ui/Badge";
import indiaMapData from "@/data/india_map_soi.json";

interface IndiaClimateMapProps {
  selectedCity: CityKey;
  onSelectCity: (city: CityKey) => void;
  className?: string;
}

// 5 stations positioned with Albers Equal Area projection calibrated to Survey of India boundary
// Jodhpur: 26.24N 73.02E, Mumbai: 19.09N 72.87E, New Delhi: 28.57N 77.10E, Bengaluru: 12.95N 77.67E, Shimla: 31.10N 77.17E
const STATION_CONFIG: Record<
  CityKey,
  {
    x: number;
    y: number;
    labelAnchor: "start" | "end";
    labelDx: number;
    labelDy: number;
  }
> = {
  Shimla: {
    x: indiaMapData.stations.Shimla.x,
    y: indiaMapData.stations.Shimla.y,
    labelAnchor: "start",
    labelDx: 14,
    labelDy: -2
  },
  New_Delhi: {
    x: indiaMapData.stations.New_Delhi.x,
    y: indiaMapData.stations.New_Delhi.y,
    labelAnchor: "start",
    labelDx: 14,
    labelDy: 4
  },
  Jodhpur: {
    x: indiaMapData.stations.Jodhpur.x,
    y: indiaMapData.stations.Jodhpur.y,
    labelAnchor: "end",
    labelDx: -14,
    labelDy: 4 // Positioned to left to avoid collision with New Delhi
  },
  Mumbai: {
    x: indiaMapData.stations.Mumbai.x,
    y: indiaMapData.stations.Mumbai.y,
    labelAnchor: "end",
    labelDx: -14,
    labelDy: 4 // Positioned to left along western coast
  },
  Bengaluru: {
    x: indiaMapData.stations.Bengaluru.x,
    y: indiaMapData.stations.Bengaluru.y,
    labelAnchor: "start",
    labelDx: 14,
    labelDy: 4
  }
};

const CITY_KEYS: CityKey[] = ["Jodhpur", "Mumbai", "New_Delhi", "Bengaluru", "Shimla"];

export const IndiaClimateMap: React.FC<IndiaClimateMapProps> = ({
  selectedCity,
  onSelectCity,
  className = ""
}) => {
  const [hoveredCity, setHoveredCity] = useState<CityKey | null>(null);

  const activeCity = hoveredCity || selectedCity;
  const activeCityInfo = CITIES_DATA[activeCity];

  return (
    <div
      className={`relative flex flex-col space-y-4 rounded-[8px] border border-[var(--line)] bg-[var(--surface)] p-5 sm:p-6 ${className}`}
    >
      {/* City Chips Row (Syncs bidirectionally with map clicks and keyboard) */}
      <div className="flex flex-wrap items-center gap-2 pb-2 border-b border-[var(--line)]">
        <span className="text-xs font-semibold text-[var(--ink-2)] mr-1 flex items-center gap-1">
          <MapPin className="w-3.5 h-3.5 text-[var(--primary)]" />
          <span>Select Station:</span>
        </span>
        {CITY_KEYS.map((city) => {
          const isSelected = selectedCity === city;
          const conf = CITIES_DATA[city].confidence;
          return (
            <button
              key={city}
              type="button"
              onClick={() => onSelectCity(city)}
              className={`px-3 py-1 rounded-[6px] text-xs font-semibold transition-all duration-150 border flex items-center space-x-1.5 focus:outline-none focus-visible:ring-2 focus-visible:ring-[var(--primary)] focus-visible:ring-offset-2 ${
                isSelected
                  ? "bg-[var(--primary)] text-white border-[var(--primary)] shadow-sm"
                  : "bg-[var(--surface-2)] text-[var(--ink)] border-[var(--line)] hover:border-[var(--primary)] hover:bg-[var(--surface)]"
              }`}
              aria-pressed={isSelected}
            >
              <span>{CITIES_DATA[city].name}</span>
              <span
                className={`w-2 h-2 rounded-full ${
                  conf === "Medium" ? "bg-emerald-400" : "bg-amber-400"
                }`}
                title={`${conf} confidence`}
              />
            </button>
          );
        })}
      </div>

      {/* Main Content: Map + Side Inspector Card */}
      <div className="flex flex-col lg:flex-row items-stretch gap-6 min-h-[420px]">
        {/* SVG Map of India */}
        <div className="relative flex-1 min-h-[420px] w-full flex flex-col items-center justify-center bg-[var(--surface-2)]/30 rounded-[8px] border border-[var(--line)] p-4">
          <svg
            viewBox={indiaMapData.viewBox}
            className="w-full h-full max-h-[540px] select-none"
            fill="none"
            xmlns="http://www.w3.org/2000/svg"
            aria-label="Map of India showing 5 representative climate stations"
          >
            {/* Survey of India Official External Boundary Outline */}
            <path
              d={indiaMapData.path}
              className="fill-[var(--surface-2)] stroke-[var(--line)] hover:fill-[var(--surface-2)]/80 transition-colors"
              strokeWidth="1.5"
              strokeLinejoin="round"
              strokeLinecap="round"
            />

            {/* Connecting Climate Geometry Lines */}
            <path
              d={`M ${STATION_CONFIG.Shimla.x},${STATION_CONFIG.Shimla.y} L ${STATION_CONFIG.New_Delhi.x},${STATION_CONFIG.New_Delhi.y} L ${STATION_CONFIG.Jodhpur.x},${STATION_CONFIG.Jodhpur.y} L ${STATION_CONFIG.Mumbai.x},${STATION_CONFIG.Mumbai.y} L ${STATION_CONFIG.Bengaluru.x},${STATION_CONFIG.Bengaluru.y}`}
              className="stroke-[var(--ink-2)] opacity-30"
              strokeWidth="1.5"
              strokeDasharray="4 4"
              fill="none"
            />

            {/* 5 Climate Station Pins & Labels */}
            {CITY_KEYS.map((city) => {
              const cfg = STATION_CONFIG[city];
              const isSelected = selectedCity === city;
              const isHovered = hoveredCity === city;
              const isMedium = CITIES_DATA[city].confidence === "Medium";
              const pinColor = isMedium ? "var(--good)" : "var(--warn)";

              return (
                <g
                  key={city}
                  tabIndex={0}
                  role="button"
                  aria-label={`${CITIES_DATA[city].name}, ${CITIES_DATA[city].zone}`}
                  aria-pressed={isSelected}
                  className="cursor-pointer transition-all duration-150 outline-none group focus-visible:outline-none"
                  onClick={() => onSelectCity(city)}
                  onKeyDown={(e) => {
                    if (e.key === "Enter" || e.key === " ") {
                      e.preventDefault();
                      onSelectCity(city);
                    }
                  }}
                  onMouseEnter={() => setHoveredCity(city)}
                  onMouseLeave={() => setHoveredCity(null)}
                >
                  {/* Outer pulse / focus ring (diameter >= 12px) */}
                  {(isSelected || isHovered) && (
                    <circle
                      cx={cfg.x}
                      cy={cfg.y}
                      r={14}
                      fill={pinColor}
                      fillOpacity={0.2}
                      className="animate-pulse"
                    />
                  )}

                  {/* Marker Node (diameter >= 14px: r=7, r=9 when selected) */}
                  <circle
                    cx={cfg.x}
                    cy={cfg.y}
                    r={isSelected ? 9 : 7}
                    fill={isSelected ? "var(--surface)" : pinColor}
                    stroke={isSelected ? "var(--primary)" : pinColor}
                    strokeWidth={isSelected ? 3 : 2}
                    className="transition-transform duration-150 group-focus-visible:stroke-[var(--primary)] group-focus-visible:stroke-[3px]"
                  />

                  {/* Station Label (>= 13px font, collision avoidance via specific anchors) */}
                  <text
                    x={cfg.x + cfg.labelDx}
                    y={cfg.y + cfg.labelDy}
                    textAnchor={cfg.labelAnchor}
                    fontSize={isSelected ? "14" : "13"}
                    fontWeight={isSelected ? "700" : "500"}
                    className="pointer-events-none select-none fill-[var(--ink)]"
                  >
                    {CITIES_DATA[city].name}
                  </text>
                </g>
              );
            })}
          </svg>

          {/* Legal Boundary Source Footnote */}
          <div className="w-full text-right text-[11px] text-[var(--ink-2)] pt-2 select-none">
            Boundary source: Survey of India (SOI) official external boundary (ODbL via Datameet)
          </div>
        </div>

        {/* Selected City Inspector Card (Beside map on desktop, below on mobile) */}
        <div className="w-full lg:w-[320px] shrink-0 flex flex-col justify-between space-y-4 rounded-[8px] border border-[var(--line)] bg-[var(--surface-2)] p-5">
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-xs text-[var(--ink-2)] font-medium">
                Representative station
              </span>
              <Badge
                variant={activeCityInfo.confidence === "Medium" ? "good" : "warn"}
                icon={
                  activeCityInfo.confidence === "Medium" ? (
                    <ShieldCheck className="w-3.5 h-3.5" />
                  ) : (
                    <AlertTriangle className="w-3.5 h-3.5" />
                  )
                }
              >
                {activeCityInfo.confidence} confidence
              </Badge>
            </div>

            <div>
              <h3 className="text-xl font-bold text-[var(--ink)] flex items-baseline space-x-2">
                <span>{activeCityInfo.name}</span>
                <span className="text-xs font-normal text-[var(--ink-2)]">
                  ({activeCityInfo.elevation})
                </span>
              </h3>
              <p className="text-xs font-semibold text-[var(--primary)] mt-0.5">
                {activeCityInfo.zone}
              </p>
            </div>

            <p className="text-xs text-[var(--ink)] leading-relaxed">
              {activeCityInfo.description}
            </p>

            {/* Warning banner for low confidence / Shimla cold boundary */}
            {activeCityInfo.envelopeAlert && (
              <div className="p-2.5 rounded-[6px] bg-[var(--surface)] border border-[var(--line)] text-xs flex items-start space-x-2">
                <AlertTriangle className="w-4 h-4 text-[var(--warn)] shrink-0 mt-0.5" />
                <span className="text-[var(--ink)] text-[12px] leading-snug">
                  {activeCityInfo.envelopeAlert}
                </span>
              </div>
            )}
          </div>

          {/* Technical Station Attributes */}
          <div className="pt-3 border-t border-[var(--line)] grid grid-cols-2 gap-2 text-xs">
            <div>
              <span className="text-[var(--ink-2)] block text-[11px]">Dual-judge rank (rs)</span>
              <span className="text-[var(--ink)] font-semibold tabular-nums text-[13px]">
                {activeCityInfo.spearman.toFixed(3)}
              </span>
            </div>
            <div>
              <span className="text-[var(--ink-2)] block text-[11px]">EPW weather file</span>
              <span
                className="text-[var(--ink)] font-semibold truncate block text-[13px]"
                title={activeCityInfo.epw}
              >
                TMYx / ISHRAE
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default IndiaClimateMap;
