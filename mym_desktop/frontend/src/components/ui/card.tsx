import { cn } from "@/lib/utils"

export function Card({ children, className }: { children: React.ReactNode; className?: string }) {
  return (
    <div className={cn("rounded-lg border border-[var(--border)] bg-[var(--card)] p-4", className)}>
      {children}
    </div>
  )
}

export function CardTitle({ children, className }: { children: React.ReactNode; className?: string }) {
  return (
    <div className={cn("text-lg font-semibold text-[var(--foreground)]", className)}>
      {children}
    </div>
  )
}

export function CardValue({ children, className }: { children: React.ReactNode; className?: string }) {
  return (
    <div className={cn("text-2xl font-bold text-[var(--accent)]", className)}>
      {children}
    </div>
  )
}
