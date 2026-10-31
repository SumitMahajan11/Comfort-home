"use client";

import React, { useId } from "react";

export interface ToggleProps {
  label: string;
  checked: boolean;
  onChange: (checked: boolean) => void;
  disabled?: boolean;
  description?: string;
  id?: string;
  className?: string;
}

export const Toggle: React.FC<ToggleProps> = ({
  label,
  checked,
  onChange,
  disabled = false,
  description,
  id,
  className = "",
}) => {
  const generatedId = useId();
  const toggleId = id || generatedId;

  return (
    <div className={`flex items-start justify-between gap-3 ${className}`}>
      <div className="flex flex-col">
        <label
          htmlFor={toggleId}
          className={`text-xs font-medium cursor-pointer select-none ${
            disabled ? "text-[var(--ink-2)] opacity-60" : "text-[var(--ink)]"
          }`}
        >
          {label}
        </label>
        {description && (
          <span className="text-[12px] text-[var(--ink-2)] leading-tight mt-0.5">
            {description}
          </span>
        )}
      </div>

      <button
        id={toggleId}
        type="button"
        role="switch"
        aria-checked={checked}
        disabled={disabled}
        onClick={() => onChange(!checked)}
        className={`relative inline-flex h-6 w-11 shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out focus:outline-none focus:ring-2 focus:ring-[var(--primary)] focus:ring-offset-2 focus:ring-offset-[var(--bg)] disabled:opacity-50 disabled:cursor-not-allowed ${
          checked ? "bg-[var(--primary)]" : "bg-[var(--line)]"
        }`}
      >
        <span
          className={`pointer-events-none inline-block h-5 w-5 rounded-full bg-[var(--surface)] shadow transform ring-0 transition duration-200 ease-in-out ${
            checked ? "translate-x-5" : "translate-x-0"
          }`}
        />
      </button>
    </div>
  );
};

export default Toggle;
