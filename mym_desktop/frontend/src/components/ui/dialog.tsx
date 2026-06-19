import * as React from "react"
import { X } from "lucide-react"
import { cn } from "@/lib/utils"

interface DialogProps {
  open: boolean
  onClose: () => void
  title?: string
  children: React.ReactNode
  className?: string
}

export function Dialog({ open, onClose, title, children, className }: DialogProps) {
  if (!open) return null

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <div className="fixed inset-0 bg-black/50" onClick={onClose} />
      <div className={cn(
        "relative z-50 w-full max-w-4xl max-h-[85vh] overflow-y-auto rounded-lg border border-[var(--border)] bg-[var(--card)] p-6 shadow-xl",
        className
      )}>
        <div className="flex items-center justify-between mb-4">
          {title && (
            <h2 className="text-lg font-semibold text-[var(--foreground)]">{title}</h2>
          )}
          <button
            onClick={onClose}
            className="rounded-md p-1 text-[var(--muted)] hover:text-[var(--foreground)] hover:bg-[var(--muted)] cursor-pointer"
          >
            <X className="h-5 w-5" />
          </button>
        </div>
        {children}
      </div>
    </div>
  )
}
