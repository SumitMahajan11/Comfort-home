"use client";

import React, { useId } from "react";

export interface SliderTick {
  value: number;
  label: string;
}

export interface SliderProps {
  label: string;
  value: number;
  min: number;
  max: number;
  step?: number;
  unit?: string;
  displayValue?: string;
  ticks?: SliderTick[];
  onChange: (value: number) => void;
  disabled?: boolean;
  description?: string;
  id?: string;
  className?: string;
}

export const Slider: React.FC<SliderProps> = ({
  label,
  value,
  min,
  max,
  step = 1,
  unit = "",
  displayValue,
  ticks,
  onChange,
  disabled = false,
  description,
  id,
  className = "",
}) => {
  const generatedId = useId();
  const inputId = id || generatedId;

  return (
    <div className={`flex flex-col gap-2 ${className}`}>
      <div className="flex items-center justify-between gap-2">
        <label
          htmlFor={inputId}
          className="text-xs font-medium text-[var(--ink)] cursor-pointer select-none"
        >
          {label}
        </label>
        <div className="text-xs font-semibold tabular-nums text-[var(--ink)] bg-[var(--surface-2)] border border-[var(--line)] px-2 py-0.5 rounded-[6px] min-w-[3.75rem] text-right inline-block">
          {displayValue ? (
            displayValue
          ) : (
            <>
              {value}
              {unit && <span className="ml-0.5 text-[var(--ink-2)] font-normal">{unit}</span>}
            </>
          )}
        </div>
      </div>

      <div className="relative w-full">
        <input
          id={inputId}
          type="range"
          min={min}
          max={max}
          step={step}
          value={value}
          disabled={disabled}
          onChange={(e) => onChange(parseFloat(e.target.value))}
          className="w-full h-2 bg-[var(--surface-2)] rounded-lg appearance-none cursor-pointer accent-[var(--primary)] focus:outline-none focus:ring-2 focus:ring-[var(--primary)] focus:ring-offset-2 focus:ring-offset-[var(--bg)] disabled:opacity-50 disabled:cursor-not-allowed border border-[var(--line)]"
        />

        {ticks && ticks.length > 0 && (
          <div className="relative w-full h-5 mt-1 select-none pointer-events-none">
            {ticks.map((t) => {
              const pct = Math.max(0, Math.min(100, ((t.value - min) / (max - min)) * 100));
              let transform = "translateX(-50%)";
              if (pct <= 0) transform = "translateX(0%)";
              else if (pct >= 100) transform = "translateX(-100%)";

              return (
                <div
                  key={`${t.value}-${t.label}`}
                  className="absolute top-0 text-[10px] tabular-nums text-[var(--ink-2)] flex flex-col items-center"
                  style={{ left: `${pct}%`, transform }}
                >
                  <span className="w-0.5 h-1 bg-[var(--line)] mb-0.5 block" />
                  <span>{t.label}</span>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {description && (
        <p className="text-[12px] text-[var(--ink-2)] leading-tight">
          {description}
        </p>
      )}
    </div>
  );
};

export default Slider;
