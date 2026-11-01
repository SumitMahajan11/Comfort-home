import React from "react";

export interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: "primary" | "secondary" | "ghost";
  size?: "sm" | "md" | "lg";
  icon?: React.ReactNode;
  children?: React.ReactNode;
}

export const Button: React.FC<ButtonProps> = ({
  variant = "secondary",
  size = "md",
  icon,
  children,
  className = "",
  disabled,
  ...props
}) => {
  const baseClasses =
    "inline-flex items-center justify-center font-medium transition-colors cursor-pointer select-none rounded-[var(--radius)] focus-ring disabled:opacity-50 disabled:cursor-not-allowed";

  const sizeClasses = {
    sm: "text-[13px] px-2.5 py-1.5 gap-1.5",
    md: "text-[14px] px-3.5 py-2 gap-2",
    lg: "text-[15px] px-4 py-2.5 gap-2.5",
  }[size];

  const variantClasses = {
    primary:
      "bg-[var(--primary)] text-[var(--primary-contrast)] hover:opacity-95 shadow-[var(--shadow-subtle)] border border-transparent font-semibold",
    secondary:
      "bg-[var(--surface)] text-[var(--ink)] border border-[var(--line)] hover:bg-[var(--surface-2)] shadow-[var(--shadow-subtle)]",
    ghost:
      "bg-transparent text-[var(--ink)] hover:bg-[var(--surface-2)] border border-transparent",
  }[variant];

  return (
    <button
      className={`${baseClasses} ${sizeClasses} ${variantClasses} ${className}`}
      disabled={disabled}
      {...props}
    >
      {icon && <span className="shrink-0">{icon}</span>}
      {children}
    </button>
  );
};
