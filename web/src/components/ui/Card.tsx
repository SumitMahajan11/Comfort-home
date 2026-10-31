import React from "react";

export interface CardProps extends React.HTMLAttributes<HTMLDivElement> {
  children?: React.ReactNode;
}

export const Card: React.FC<CardProps> = ({ children, className = "", ...props }) => {
  return (
    <div
      className={`bg-[var(--surface)] border border-[var(--line)] rounded-[var(--radius)] shadow-[var(--shadow-subtle)] overflow-hidden transition-colors ${className}`}
      {...props}
    >
      {children}
    </div>
  );
};

export const CardHeader: React.FC<CardProps> = ({ children, className = "", ...props }) => {
  return (
    <div className={`p-4 sm:p-6 border-b border-[var(--line)] ${className}`} {...props}>
      {children}
    </div>
  );
};

export const CardTitle: React.FC<React.HTMLAttributes<HTMLHeadingElement>> = ({
  children,
  className = "",
  ...props
}) => {
  return (
    <h3
      className={`text-lg sm:text-xl font-serif font-semibold text-[var(--ink)] leading-snug ${className}`}
      {...props}
    >
      {children}
    </h3>
  );
};

export const CardDescription: React.FC<React.HTMLAttributes<HTMLParagraphElement>> = ({
  children,
  className = "",
  ...props
}) => {
  return (
    <p className={`text-sm text-[var(--ink-2)] mt-1 leading-relaxed ${className}`} {...props}>
      {children}
    </p>
  );
};

export const CardContent: React.FC<CardProps> = ({ children, className = "", ...props }) => {
  return (
    <div className={`p-4 sm:p-6 ${className}`} {...props}>
      {children}
    </div>
  );
};

export const CardFooter: React.FC<CardProps> = ({ children, className = "", ...props }) => {
  return (
    <div className={`p-4 sm:p-6 border-t border-[var(--line)] bg-[var(--surface-2)] flex items-center justify-between ${className}`} {...props}>
      {children}
    </div>
  );
};
