"use client";

import React, { useState, useRef, useEffect, useId } from "react";
import { HelpCircle } from "lucide-react";

export interface TooltipProps {
  content: React.ReactNode;
  children: React.ReactNode;
  className?: string;
  side?: "top" | "bottom" | "left" | "right";
}

export const Tooltip: React.FC<TooltipProps> = ({
  content,
  children,
  className = "",
  side = "top",
}) => {
  const [isVisible, setIsVisible] = useState(false);
  const tooltipId = useId();
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape" && isVisible) {
        setIsVisible(false);
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [isVisible]);

  const getPositionClasses = () => {
    switch (side) {
      case "bottom":
        return "top-full mt-2 left-1/2 -translate-x-1/2";
      case "left":
        return "right-full mr-2 top-1/2 -translate-y-1/2";
      case "right":
        return "left-full ml-2 top-1/2 -translate-y-1/2";
      case "top":
      default:
        return "bottom-full mb-2 left-1/2 -translate-x-1/2";
    }
  };

  return (
    <span
      ref={containerRef as unknown as React.RefObject<HTMLSpanElement>}
      className={`relative inline-flex items-center ${className}`}
      onMouseEnter={() => setIsVisible(true)}
      onMouseLeave={() => setIsVisible(false)}
      onFocus={() => setIsVisible(true)}
      onBlur={() => setIsVisible(false)}
    >
      <span aria-describedby={isVisible ? tooltipId : undefined}>
        {children}
      </span>
      {isVisible && (
        <span
          id={tooltipId}
          role="tooltip"
          className={`absolute z-50 px-2.5 py-1.5 text-xs text-[var(--ink)] bg-[var(--surface)] border border-[var(--line)] rounded-[8px] shadow-sm max-w-xs whitespace-normal pointer-events-none transition-opacity ${getPositionClasses()}`}
        >
          {content}
        </span>
      )}
    </span>
  );
};

export interface InfoTipProps {
  label: string;
  content: React.ReactNode;
  className?: string;
}

export const InfoTip: React.FC<InfoTipProps> = ({
  label,
  content,
  className = "",
}) => {
  return (
    <Tooltip content={content} className={className}>
      <button
        type="button"
        className="inline-flex items-center justify-center text-[var(--ink-2)] hover:text-[var(--primary)] focus:outline-none focus:ring-2 focus:ring-[var(--primary)] rounded-full p-0.5 ml-1 transition-colors"
        aria-label={`More information about ${label}`}
      >
        <HelpCircle className="w-3.5 h-3.5" />
      </button>
    </Tooltip>
  );
};

export default Tooltip;
