import { cn } from "@/lib/utils"

type TableProps = React.HTMLAttributes<HTMLElement> & { children: React.ReactNode; className?: string; style?: React.CSSProperties }
type ThProps = React.ThHTMLAttributes<HTMLTableCellElement> & { children: React.ReactNode; className?: string; style?: React.CSSProperties }

export function Table({ children, className, style }: TableProps) {
  return (
    <div className={cn("overflow-auto rounded-lg border border-[var(--border)]", className)} style={style}>
      <table className="w-full text-sm">{children}</table>
    </div>
  )
}

export function THead({ children }: { children: React.ReactNode }) {
  return (
    <thead className="bg-[var(--surface-strong)] text-[var(--foreground)]">
      {children}
    </thead>
  )
}

export function TBody({ children }: { children: React.ReactNode }) {
  return <tbody>{children}</tbody>
}

export function TR({ children, className, style, ...props }: TableProps) {
  return (
    <tr className={cn("border-b border-[var(--border)] last:border-0", className)} style={style} {...props}>
      {children}
    </tr>
  )
}

export function TH({ children, className, style, ...props }: ThProps) {
  return (
    <th className={cn("px-4 py-3 text-left font-semibold text-sm", className)} style={style} {...props}>
      {children}
    </th>
  )
}

export function TD({ children, className, style, ...props }: React.TdHTMLAttributes<HTMLTableCellElement> & { children: React.ReactNode; className?: string; style?: React.CSSProperties }) {
  return (
    <td className={cn("px-4 py-3 text-[var(--foreground)]", className)} style={style} {...props}>
      {children}
    </td>
  )
}
