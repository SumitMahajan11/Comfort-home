import React from "react";

export const Table = React.forwardRef<
  HTMLTableElement,
  React.HTMLAttributes<HTMLTableElement>
>(({ className = "", ...props }, ref) => (
  <div className="relative w-full overflow-auto rounded-[var(--radius)] border border-[var(--line)]">
    <table
      ref={ref}
      className={`w-full caption-bottom text-xs text-[var(--ink)] ${className}`}
      {...props}
    />
  </div>
));
Table.displayName = "Table";

export const TableHeader = React.forwardRef<
  HTMLTableSectionElement,
  React.HTMLAttributes<HTMLTableSectionElement>
>(({ className = "", ...props }, ref) => (
  <thead
    ref={ref}
    className={`bg-[var(--surface-2)] border-b border-[var(--line)] text-[var(--ink-2)] font-medium ${className}`}
    {...props}
  />
));
TableHeader.displayName = "TableHeader";

export const TableBody = React.forwardRef<
  HTMLTableSectionElement,
  React.HTMLAttributes<HTMLTableSectionElement>
>(({ className = "", ...props }, ref) => (
  <tbody
    ref={ref}
    className={`divide-y divide-[var(--line)] bg-[var(--surface)] ${className}`}
    {...props}
  />
));
TableBody.displayName = "TableBody";

export const TableFooter = React.forwardRef<
  HTMLTableSectionElement,
  React.HTMLAttributes<HTMLTableSectionElement>
>(({ className = "", ...props }, ref) => (
  <tfoot
    ref={ref}
    className={`border-t border-[var(--line)] bg-[var(--surface-2)] font-medium text-[var(--ink)] ${className}`}
    {...props}
  />
));
TableFooter.displayName = "TableFooter";

export const TableRow = React.forwardRef<
  HTMLTableRowElement,
  React.HTMLAttributes<HTMLTableRowElement>
>(({ className = "", ...props }, ref) => (
  <tr
    ref={ref}
    className={`transition-colors hover:bg-[var(--surface-2)]/60 data-[state=selected]:bg-[var(--surface-2)] ${className}`}
    {...props}
  />
));
TableRow.displayName = "TableRow";

export const TableHead = React.forwardRef<
  HTMLTableCellElement,
  React.ThHTMLAttributes<HTMLTableCellElement>
>(({ className = "", ...props }, ref) => (
  <th
    ref={ref}
    className={`h-9 px-3 text-left align-middle font-medium text-[var(--ink-2)] text-[13px] whitespace-nowrap ${className}`}
    {...props}
  />
));
TableHead.displayName = "TableHead";

export const TableCell = React.forwardRef<
  HTMLTableCellElement,
  React.TdHTMLAttributes<HTMLTableCellElement>
>(({ className = "", ...props }, ref) => (
  <td
    ref={ref}
    className={`p-3 align-middle text-[13px] text-[var(--ink)] tabular-nums ${className}`}
    {...props}
  />
));
TableCell.displayName = "TableCell";

export const TableCaption = React.forwardRef<
  HTMLTableCaptionElement,
  React.HTMLAttributes<HTMLTableCaptionElement>
>(({ className = "", ...props }, ref) => (
  <caption
    ref={ref}
    className={`mt-3 text-[13px] text-[var(--ink-2)] ${className}`}
    {...props}
  />
));
TableCaption.displayName = "TableCaption";

export default Table;
