import { useCallback, useRef, useState } from 'react'
import type { OcclusionPayload, OcclusionShape } from '../api/types'

const MEDIA_BASE = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000'

export function mediaUrl(path: string): string {
  return path.startsWith('/') ? `${MEDIA_BASE}${path}` : path
}

/** Review-time rendering of an occlusion card (§14 Phase 4).
 *
 *  Every region stays masked and the one being tested is highlighted, so the
 *  card asks "what is *this*" rather than leaking the answer via the other
 *  labels. On reveal, only the target opens. */
export function OcclusionCard({
  payload,
  revealed,
}: {
  payload: OcclusionPayload
  revealed: boolean
}) {
  return (
    <figure className="relative inline-block max-w-full overflow-hidden rounded-lg border border-ink-line">
      <img src={mediaUrl(payload.image)} alt="" className="block max-h-[28rem] w-auto max-w-full" />
      <svg
        viewBox="0 0 100 100"
        preserveAspectRatio="none"
        className="pointer-events-none absolute inset-0 h-full w-full"
      >
        {payload.shapes.map((s) => {
          const isTarget = s.id === payload.target
          if (isTarget && revealed) {
            return (
              <rect
                key={s.id}
                x={s.x * 100}
                y={s.y * 100}
                width={s.w * 100}
                height={s.h * 100}
                fill="none"
                stroke="#38bdf8"
                strokeWidth={0.6}
                vectorEffect="non-scaling-stroke"
              />
            )
          }
          return (
            <rect
              key={s.id}
              x={s.x * 100}
              y={s.y * 100}
              width={s.w * 100}
              height={s.h * 100}
              fill={isTarget ? '#0ea5e9' : '#1e293b'}
              fillOpacity={isTarget ? 0.92 : 0.97}
              stroke={isTarget ? '#7dd3fc' : '#334155'}
              strokeWidth={0.5}
              vectorEffect="non-scaling-stroke"
            />
          )
        })}
      </svg>
    </figure>
  )
}

interface EditorProps {
  image: string
  shapes: OcclusionShape[]
  onChange: (shapes: OcclusionShape[]) => void
}

/** Drag on the image to add a mask. Coordinates are stored as fractions of the
 *  image so a mask lands in the same place at any display size. */
export function OcclusionEditor({ image, shapes, onChange }: EditorProps) {
  const boxRef = useRef<HTMLDivElement>(null)
  const [draft, setDraft] = useState<{ x: number; y: number; w: number; h: number } | null>(null)
  const start = useRef<{ x: number; y: number } | null>(null)
  const [selected, setSelected] = useState<string | null>(null)

  const toFraction = useCallback((e: React.MouseEvent) => {
    const rect = boxRef.current?.getBoundingClientRect()
    if (!rect) return { x: 0, y: 0 }
    return {
      x: Math.min(1, Math.max(0, (e.clientX - rect.left) / rect.width)),
      y: Math.min(1, Math.max(0, (e.clientY - rect.top) / rect.height)),
    }
  }, [])

  function onDown(e: React.MouseEvent) {
    if (e.button !== 0) return
    start.current = toFraction(e)
    setDraft(null)
  }

  function onMove(e: React.MouseEvent) {
    if (!start.current) return
    const p = toFraction(e)
    setDraft({
      x: Math.min(start.current.x, p.x),
      y: Math.min(start.current.y, p.y),
      w: Math.abs(p.x - start.current.x),
      h: Math.abs(p.y - start.current.y),
    })
  }

  function onUp() {
    if (draft && draft.w > 0.01 && draft.h > 0.01) {
      const used = new Set(shapes.map((s) => s.id))
      let n = 1
      while (used.has(`o${n}`)) n += 1
      onChange([...shapes, { id: `o${n}`, ...round(draft), label: '' }])
    }
    start.current = null
    setDraft(null)
  }

  return (
    <div className="space-y-3">
      <div
        ref={boxRef}
        onMouseDown={onDown}
        onMouseMove={onMove}
        onMouseUp={onUp}
        onMouseLeave={onUp}
        className="relative inline-block max-w-full cursor-crosshair select-none overflow-hidden rounded-lg border border-ink-line"
      >
        <img
          src={mediaUrl(image)}
          alt=""
          draggable={false}
          className="block max-h-[28rem] w-auto max-w-full"
        />
        <svg
          viewBox="0 0 100 100"
          preserveAspectRatio="none"
          className="pointer-events-none absolute inset-0 h-full w-full"
        >
          {shapes.map((s) => (
            <rect
              key={s.id}
              x={s.x * 100}
              y={s.y * 100}
              width={s.w * 100}
              height={s.h * 100}
              fill={selected === s.id ? '#0ea5e9' : '#1e293b'}
              fillOpacity={0.85}
              stroke={selected === s.id ? '#7dd3fc' : '#475569'}
              strokeWidth={0.6}
              vectorEffect="non-scaling-stroke"
            />
          ))}
          {draft && (
            <rect
              x={draft.x * 100}
              y={draft.y * 100}
              width={draft.w * 100}
              height={draft.h * 100}
              fill="#0ea5e9"
              fillOpacity={0.4}
              stroke="#7dd3fc"
              strokeWidth={0.6}
              vectorEffect="non-scaling-stroke"
            />
          )}
        </svg>
      </div>

      <p className="text-xs text-slate-600">
        Drag on the image to mask a region. Each mask becomes its own card, scheduled
        independently. Labels are optional — add them and the LLM can grade typed answers.
      </p>

      {shapes.length > 0 && (
        <ul className="space-y-2">
          {shapes.map((s, i) => (
            <li
              key={s.id}
              className="flex items-center gap-2"
              onMouseEnter={() => setSelected(s.id)}
              onMouseLeave={() => setSelected(null)}
            >
              <span className="chip w-10 justify-center">{s.id}</span>
              <input
                className="input flex-1 py-1 text-xs"
                placeholder="Label (optional) — e.g. “Frontal lobe”"
                value={s.label ?? ''}
                onChange={(e) =>
                  onChange(shapes.map((x, j) => (j === i ? { ...x, label: e.target.value } : x)))
                }
              />
              <button
                type="button"
                className="btn btn-danger px-2 py-1 text-xs"
                onClick={() => onChange(shapes.filter((_, j) => j !== i))}
              >
                Remove
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}

function round(r: { x: number; y: number; w: number; h: number }) {
  const f = (n: number) => Math.round(n * 10000) / 10000
  return { x: f(r.x), y: f(r.y), w: f(r.w), h: f(r.h) }
}
