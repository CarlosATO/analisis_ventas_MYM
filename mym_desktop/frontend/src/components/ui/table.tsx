import { cn } from "@/lib/utils"

export function Table({ children, className }: { children: React.ReactNode; className?: string }) {
  return (
    <div className={cn("overflow-auto rounded-lg border border-[var(--border)]", className)}>
      <table className="w-full text-sm">{children}</table>
    </div>
  )
}

export function THead({ children }: { children: React.ReactNode }) {
  return (
    <thead className="bg-[var(--muted)] text-[var(--foreground)]">
      {children}
    </thead>
  )
}

export function TBody({ children }: { children: React.ReactNode }) {
  return <tbody>{children}</tbody>
}

export function TR({ children, className }: { children: React.ReactNode; className?: string }) {
  return (
    <tr className={cn("border-b border-[var(--border)] last:border-0", className)}>
      {children}
    </tr>
  )
}

export function TH({ children, className }: { children: React.ReactNode; className?: string }) {
  return (
    <th className={cn("px-4 py-3 text-left font-semibold text-sm", className)}>
      {children}
    </th>
  )
}

export function TD({ children, className }: { children: React.ReactNode; className?: string }) {
  return (
    <td className={cn("px-4 py-3 text-[var(--foreground)]", className)}>
      {children}
    </td>
  )
}
