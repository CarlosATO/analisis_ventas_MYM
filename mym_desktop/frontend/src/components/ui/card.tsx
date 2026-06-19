import { cn } from "@/lib/utils"

type CardProps = { children: React.ReactNode; className?: string; style?: React.CSSProperties }

export function Card({ children, className, style }: CardProps) {
  return (
    <div className={cn("rounded-xl border border-[var(--border)] bg-[var(--card)] p-4 shadow-[var(--shadow-soft)]", className)} style={style}>
      {children}
    </div>
  )
}

export function CardTitle({ children, className, style }: CardProps) {
  return (
    <div className={cn("text-lg font-semibold text-[var(--card-foreground)]", className)} style={style}>
      {children}
    </div>
  )
}

export function CardValue({ children, className, style }: CardProps) {
  return (
    <div className={cn("text-2xl font-bold text-[var(--accent)]", className)} style={style}>
      {children}
    </div>
  )
}
