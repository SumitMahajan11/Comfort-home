"use client";

import React, { useState } from "react";
import { SuccessCriterion } from "@/types";
import { CheckCircle2, AlertCircle, XCircle, ChevronDown, ChevronUp, FileText } from "lucide-react";
import { Badge } from "@/components/ui/Badge";

interface CriteriaScorecardProps {
  criteria: SuccessCriterion[];
  className?: string;
}

export const CriteriaScorecard: React.FC<CriteriaScorecardProps> = ({
  criteria = [],
  className = ""
}) => {
  const [expandedId, setExpandedId] = useState<string | null>(null);

  const toggleExpand = (id: string) => {
    setExpandedId((prev) => (prev === id ? null : id));
  };

  const getStatusBadge = (status: "PASS" | "PARTIAL" | "FAIL") => {
    switch (status) {
      case "PASS":
        return (
          <Badge variant="good" icon={<CheckCircle2 className="w-3.5 h-3.5" />}>
            PASS
          </Badge>
        );
      case "PARTIAL":
        return (
          <Badge variant="warn" icon={<AlertCircle className="w-3.5 h-3.5" />}>
            PARTIAL (23/25)
          </Badge>
        );
      case "FAIL":
        return (
          <Badge variant="bad" icon={<XCircle className="w-3.5 h-3.5" />}>
            FAIL (Negative result)
          </Badge>
        );
    }
  };

  const list = criteria || [];

  return (
    <div className={`grid grid-cols-1 md:grid-cols-2 gap-4 ${className}`}>
      {list.map((c) => {
        const isExpanded = expandedId === c.id;

        return (
          <div
            key={c.id}
            className="rounded-[8px] border border-[var(--line)] bg-[var(--surface)] p-5 flex flex-col justify-between"
          >
            <div>
              <div className="flex items-center justify-between">
                <span className="text-xs font-semibold text-[var(--primary)]">
                  Criterion {c.id}
                </span>
                {getStatusBadge(c.status)}
              </div>

              <h3 className="text-base font-semibold text-[var(--ink)] mt-1.5 leading-snug">
                {c.name}
              </h3>

              <p className="text-xs text-[var(--ink-2)] mt-1 line-clamp-2">
                {c.threshold}
              </p>
            </div>

            {/* Card Footer with Details Toggle */}
            <div className="mt-3 pt-3 border-t border-[var(--line)] flex items-center justify-end text-xs">
              <button
                onClick={() => toggleExpand(c.id)}
                className="text-[var(--primary)] hover:underline font-medium inline-flex items-center space-x-1 transition text-xs"
              >
                <span>{isExpanded ? "Hide details" : "Details"}</span>
                {isExpanded ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
              </button>
            </div>

            {/* Expandable Explanation & Evidence Details */}
            {isExpanded && (
              <div className="mt-3 pt-3 border-t border-[var(--line)] text-xs text-[var(--ink)] leading-relaxed bg-[var(--surface-2)] p-3 rounded-[8px] space-y-2">
                <p>{c.explanation}</p>
                {c.id === "S1" && (
                  <div className="mt-2 tabular-nums text-xs grid grid-cols-2 gap-1 text-[var(--ink-2)]">
                    <div>ML champion: <strong className="text-[var(--ink)]">0.4785 F1</strong></div>
                    <div>Adaptive 90%: <strong className="text-[var(--ink)]">0.4939 F1</strong></div>
                    <div className="col-span-2 text-[var(--bad)] font-medium">Margin: -0.0154 (did not meet +0.05 threshold)</div>
                  </div>
                )}
                {c.id === "S2" && (
                  <div className="mt-2 tabular-nums text-xs text-[var(--ink-2)]">
                    <div>Mean O2 energy R²: <strong className="text-[var(--ink)]">0.987</strong></div>
                    <div className="text-[var(--warn)] font-medium">Under 0.95: Mumbai O1_ml (0.9406), Shimla warm_ml (0.9225)</div>
                  </div>
                )}
                {c.id === "S3" && (
                  <div className="mt-2 tabular-nums text-xs text-[var(--good)] font-medium">
                    36 of 50 verified designs beat both R1 and R2 across all 3 objectives in direct EnergyPlus runs.
                  </div>
                )}
                <div className="pt-2 border-t border-[var(--line)] flex items-center space-x-1 text-[var(--ink-2)] text-[11px]">
                  <FileText className="w-3 h-3 text-[var(--ink-2)]" />
                  <span>Evidence record: <code className="text-[var(--ink)] font-semibold">[{c.evidence}]</code></span>
                </div>
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
};

export default CriteriaScorecard;
