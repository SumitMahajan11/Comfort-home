import React from "react";
import { CheckCircle2, AlertTriangle, XCircle, Info, Sparkles, Flame, Snowflake } from "lucide-react";

export type BadgeVariant = "neutral" | "good" | "warn" | "bad" | "cool" | "hot" | "primary";

export interface BadgeProps extends React.HTMLAttributes<HTMLSpanElement> {
  variant?: BadgeVariant;
  icon?: React.ReactNode;
  children: React.ReactNode;
}

export const Badge: React.FC<BadgeProps> = ({
  variant = "neutral",
  icon,
  children,
  className = "",
  ...props
}) => {
  const defaultIcon = {
    neutral: <Info className="w-3.5 h-3.5 shrink-0" aria-hidden="true" />,
    good: <CheckCircle2 className="w-3.5 h-3.5 shrink-0" aria-hidden="true" />,
    warn: <AlertTriangle className="w-3.5 h-3.5 shrink-0" aria-hidden="true" />,
    bad: <XCircle className="w-3.5 h-3.5 shrink-0" aria-hidden="true" />,
    cool: <Snowflake className="w-3.5 h-3.5 shrink-0" aria-hidden="true" />,
    hot: <Flame className="w-3.5 h-3.5 shrink-0" aria-hidden="true" />,
    primary: <Sparkles className="w-3.5 h-3.5 shrink-0" aria-hidden="true" />,
  }[variant];

  const variantStyles = {
    neutral:
      "bg-[var(--surface-2)] text-[var(--ink)] border-[var(--line)]",
    good:
      "bg-[var(--surface)] text-[var(--good)] border-[var(--good)] font-medium",
    warn:
      "bg-[var(--surface)] text-[var(--warn)] border-[var(--warn)] font-medium",
    bad:
      "bg-[var(--surface)] text-[var(--bad)] border-[var(--bad)] font-medium",
    cool:
      "bg-[var(--surface)] text-[var(--cool)] border-[var(--cool)] font-medium",
    hot:
      "bg-[var(--surface)] text-[var(--hot)] border-[var(--hot)] font-medium",
    primary:
      "bg-[var(--surface)] text-[var(--primary)] border-[var(--primary)] font-semibold",
  }[variant];

  return (
    <span
      className={`inline-flex items-center gap-1.5 px-2.5 py-1 text-[13px] leading-tight rounded-[var(--radius)] border shadow-xs select-none ${variantStyles} ${className}`}
      {...props}
    >
      {icon !== undefined ? icon : defaultIcon}
      <span className="tabular-nums">{children}</span>
    </span>
  );
};
