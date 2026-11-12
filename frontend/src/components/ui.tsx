import { useId, useRef, type ReactNode } from 'react'
import { useDialogA11y } from '../hooks/useDialogA11y'

export function Spinner({ label }: { label?: string }) {
  return (
    <div className="flex items-center gap-3 text-sm text-slate-500" role="status" aria-live="polite">
      <span
        aria-hidden="true"
        className="h-4 w-4 animate-spin rounded-full border-2 border-slate-700 border-t-sky-400"
      />
      {label ?? 'Loading…'}
    </div>
  )
}

export function ErrorNote({ error }: { error: unknown }) {
  if (!error) return null
  const message = error instanceof Error ? error.message : String(error)
  return (
    <div
      role="alert"
      className="rounded-lg border border-rose-500/40 bg-rose-500/10 px-4 py-3 text-sm text-rose-200"
    >
      {message}
    </div>
  )
}

export function Empty({ title, children }: { title: string; children?: ReactNode }) {
  return (
    <div className="rounded-xl border border-dashed border-ink-line px-6 py-12 text-center">
      <p className="text-slate-300">{title}</p>
      {children && <div className="mt-3 text-sm text-slate-500">{children}</div>}
    </div>
  )
}

export function Section({
  title,
  description,
  children,
  actions,
}: {
  title: string
  description?: string
  children: ReactNode
  actions?: ReactNode
}) {
  return (
    <section className="card">
      <div className="mb-4 flex items-start justify-between gap-4">
        <div>
          <h2 className="text-sm font-semibold text-slate-200">{title}</h2>
          {description && <p className="mt-1 text-xs text-slate-500">{description}</p>}
        </div>
        {actions}
      </div>
      {children}
    </section>
  )
}

export function PriorityBar({ value }: { value: number }) {
  return (
    <span className="inline-flex items-center gap-2" title={`Priority ${value}/100`}>
      <span className="h-1.5 w-16 overflow-hidden rounded-full bg-ink-line">
        <span
          className="block h-full rounded-full bg-sky-400/70"
          style={{ width: `${Math.max(2, value)}%` }}
        />
      </span>
      <span className="text-xs tabular-nums text-slate-500">{value}</span>
    </span>
  )
}

export function Modal({
  title,
  onClose,
  children,
}: {
  title: string
  onClose: () => void
  children: ReactNode
}) {
  const panelRef = useRef<HTMLDivElement>(null)
  const titleId = useId()
  useDialogA11y(panelRef, onClose)

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4 backdrop-blur-sm"
      onMouseDown={(e) => {
        if (e.target === e.currentTarget) onClose()
      }}
    >
      <div
        ref={panelRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        tabIndex={-1}
        className="w-full max-w-lg rounded-2xl border border-ink-line bg-ink-soft p-6 shadow-2xl space-y-4 outline-none"
      >
        <div className="flex items-center justify-between border-b border-ink-line/80 pb-3">
          <h3 id={titleId} className="text-base font-bold text-slate-100">
            {title}
          </h3>
          <button
            type="button"
            onClick={onClose}
            className="rounded-lg p-1 text-slate-400 hover:bg-ink hover:text-slate-200 transition text-lg leading-none"
            aria-label="Close"
          >
            &times;
          </button>
        </div>
        <div>{children}</div>
      </div>
    </div>
  )
}
