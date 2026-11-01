import React from "react";

export interface StatProps {
  label: string;
  value: string | number;
  unit?: string;
  note?: string;
  trend?: "good" | "warn" | "bad" | "cool" | "hot" | "neutral";
  className?: string;
}

export const Stat: React.FC<StatProps> = ({
  label,
  value,
  unit,
  note,
  trend,
  className = "",
}) => {
  const getTrendColor = () => {
    switch (trend) {
      case "good":
        return "text-[var(--good)]";
      case "warn":
        return "text-[var(--warn)]";
      case "bad":
        return "text-[var(--bad)]";
      case "cool":
        return "text-[var(--cool)]";
      case "hot":
        return "text-[var(--hot)]";
      default:
        return "text-[var(--ink-2)]";
    }
  };

  return (
    <div
      className={`p-4 bg-[var(--surface)] border border-[var(--line)] rounded-[var(--radius)] flex flex-col justify-between text-left ${className}`}
    >
      <div className="text-[13px] font-medium text-[var(--ink-2)] leading-tight text-left">
        {label}
      </div>
      <div className="mt-2 flex items-baseline gap-1 text-left">
        <span className="text-2xl font-semibold tabular-nums text-[var(--ink)] tracking-tight text-left">
          {value}
        </span>
        {unit && (
          <span className="text-[13px] font-normal text-[var(--ink-2)]">
            {unit}
          </span>
        )}
      </div>
      {note && (
        <div
          className={`mt-2 text-[13px] leading-tight text-left ${
            trend ? getTrendColor() : "text-[var(--ink-2)]"
          }`}
        >
          {note}
        </div>
      )}
    </div>
  );
};

export default Stat;
