import type { ReactNode } from 'react'

export function Spinner({ label }: { label?: string }) {
  return (
    <div className="flex items-center gap-3 text-sm text-slate-500">
      <span className="h-4 w-4 animate-spin rounded-full border-2 border-slate-700 border-t-sky-400" />
      {label ?? 'Loading…'}
    </div>
  )
}

export function ErrorNote({ error }: { error: unknown }) {
  if (!error) return null
  const message = error instanceof Error ? error.message : String(error)
  return (
    <div className="rounded-lg border border-rose-500/40 bg-rose-500/10 px-4 py-3 text-sm text-rose-200">
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

/** Renders plain text plus `![](url)` image and `[audio](url)` refs. */
export function RichText({ text, className = '' }: { text: string; className?: string }) {
  const parts = text.split(/(!\[\]\([^)]+\)|\[audio\]\([^)]+\))/g)
  return (
    <div className={`whitespace-pre-wrap break-words ${className}`}>
      {parts.map((part, i) => {
        const img = part.match(/^!\[\]\(([^)]+)\)$/)
        if (img) {
          const src = img[1].startsWith('/')
            ? `${import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000'}${img[1]}`
            : img[1]
          return (
            <img key={i} src={src} alt="" className="my-2 max-h-72 rounded-lg border border-ink-line" />
          )
        }
        const audio = part.match(/^\[audio\]\(([^)]+)\)$/)
        if (audio) {
          const src = audio[1].startsWith('/')
            ? `${import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000'}${audio[1]}`
            : audio[1]
          return <audio key={i} controls src={src} className="my-2 w-full" />
        }
        return <span key={i}>{part}</span>
      })}
    </div>
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
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4 backdrop-blur-sm">
      <div className="w-full max-w-lg rounded-2xl border border-ink-line bg-[#0d1117] p-6 shadow-2xl space-y-4">
        <div className="flex items-center justify-between border-b border-ink-line/80 pb-3">
          <h3 className="text-base font-bold text-slate-100">{title}</h3>
          <button
            onClick={onClose}
            className="rounded-lg p-1 text-slate-400 hover:bg-ink-soft hover:text-slate-200 transition"
          >
            ✕
          </button>
        </div>
        <div>{children}</div>
      </div>
    </div>
  )
}
