import { API_BASE } from '../../api/client'
import type { SubmitAnswerResponse } from '../../api/types'
import { DiscreteModelSelector } from './ModelControls'
import { GRADE_STYLE } from './helpers'

/** §4.1 step 5: show the score *and* the reasoning, so the model is auditable.
 *
 *  The score (0-100) is the actual grading feedback — correctness against key
 *  concepts and keyword match. The grade chip next to it is only the FSRS
 *  scheduling bucket that score landed in; "confidence" is a separate axis
 *  entirely (how sure the model is in its own score), so it's labelled to
 *  avoid being read as a second correctness number.
 */
export function GradeReasoning({
  result,
  installedModels = [],
  activeModel,
  grading = false,
  hasAnswer = false,
  onSelectModel,
  onGradeWithModel,
}: {
  result: SubmitAnswerResponse
  installedModels?: string[]
  activeModel?: string
  grading?: boolean
  hasAnswer?: boolean
  onSelectModel?: (m: string) => void
  onGradeWithModel?: (m: string) => void
}) {
  const pct = Math.round(result.confidence * 100)
  return (
    <div className="rounded-lg border border-ink-line bg-ink p-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="flex flex-wrap items-center gap-2">
          {result.score !== null && (
            <span className={`chip text-base font-semibold ${GRADE_STYLE[result.suggested_grade]}`}>
              {Math.round(result.score)}%
            </span>
          )}
          <span className={`chip capitalize ${GRADE_STYLE[result.suggested_grade]}`}>
            {result.suggested_grade}
          </span>
          <span className="chip">model confidence {pct}%</span>
          {result.model_used && <span className="chip">{result.model_used}</span>}
          {result.cached && <span className="chip">cached</span>}
          {result.heuristic_overlap !== null && (
            <span className="chip">keyword overlap {Math.round(result.heuristic_overlap * 100)}%</span>
          )}
        </div>

        {onSelectModel && onGradeWithModel && (
          <div className="flex items-center gap-1.5">
            <span className="text-[0.6875rem] text-slate-400">Retry with:</span>
            <DiscreteModelSelector
              activeModel={activeModel || result.model_used || 'qwen2.5-coder:3b'}
              installedModels={installedModels}
              grading={grading}
              hasAnswer={hasAnswer}
              isRevealed={true}
              onSelectModel={onSelectModel}
              onGradeWithModel={onGradeWithModel}
            />
          </div>
        )}
      </div>

      {result.reasoning && <p className="mt-3 text-sm text-slate-300">{result.reasoning}</p>}

      {result.needs_confirmation && (
        <p className="mt-3 rounded border border-amber-500/30 bg-amber-500/10 px-3 py-2 text-xs text-amber-200">
          This grade disagreed with the keyword check, or the model wasn't confident — worth a
          second look before you accept it.
        </p>
      )}

      {result.automaticity_exceeded && (
        <p className="mt-3 rounded border border-amber-500/30 bg-amber-500/10 px-3 py-2 text-xs text-amber-200">
          {result.automaticity_note || 'Reaction latency exceeded target automaticity threshold.'}
        </p>
      )}
    </div>
  )
}
/** Prominent callout card for overlooked or unconsidered content post-grading. */
export function OverlookedAnalysisCard({ result }: { result: SubmitAnswerResponse }) {
  const hasMissed = result.missed_points.length > 0
  const hasOverlookedPhrases = Boolean(result.overlooked_phrases && result.overlooked_phrases.length > 0)
  const isComplete = !hasMissed && !hasOverlookedPhrases && (result.score === null || result.score >= 90)

  if (isComplete) {
    return (
      <div className="flex items-center gap-2 rounded-lg border border-emerald-500/40 bg-emerald-500/10 p-3.5 text-xs text-emerald-200">
        
        <div>
          <span className="font-semibold">Complete Recall:</span> All key concepts recalled.
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-3">
      {(hasMissed || hasOverlookedPhrases) && (
        <div className="rounded-lg border border-amber-500/40 bg-amber-500/10 p-4">
          <div className="flex items-center gap-2 text-sm font-semibold text-amber-200">
            
            <span>Overlooked</span>
          </div>
          <p className="mt-1 text-xs text-amber-300/80">
            Omitted from answer:
          </p>
          {hasMissed && (
            <ul className="mt-2.5 space-y-1.5 text-sm text-amber-100">
              {result.missed_points.map((p, i) => (
                <li key={i} className="flex items-start gap-2">
                  <span className="font-bold text-amber-400">•</span>
                  <span>{p}</span>
                </li>
              ))}
            </ul>
          )}
          {hasOverlookedPhrases && (
            <div className="mt-3 border-t border-amber-500/20 pt-2.5">
              <p className="mb-1.5 text-[0.6875rem] font-medium text-amber-300/70">
                Omitted Phrases:
              </p>
              <div className="flex flex-wrap gap-1.5">
                {result.overlooked_phrases!.map((phrase, i) => (
                  <span
                    key={i}
                    className="inline-flex items-center rounded border border-amber-500/30 bg-amber-500/20 px-2 py-0.5 text-xs font-medium text-amber-200"
                  >
                    {phrase}
                  </span>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {result.matched_points.length > 0 && (
        <div className="rounded-lg border border-emerald-500/30 bg-emerald-500/10 p-3">
          <div className="flex items-center gap-1.5 text-xs font-semibold text-emerald-200">
            <span>Recalled</span>
          </div>
          <ul className="mt-1.5 space-y-1 text-xs text-emerald-100/90">
            {result.matched_points.map((p, i) => (
              <li key={i} className="flex items-start gap-1.5">
                <svg className="w-3 h-3 text-emerald-400 shrink-0" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5"><polyline points="20 6 9 17 4 12"/></svg>
                <span>{p}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Longitudinal Weakness Memory: Improvements & Resolved Pitfalls */}
      {result.improvements && result.improvements.length > 0 && (
        <div className="rounded-lg border border-emerald-500/50 bg-emerald-500/15 p-3.5">
          <div className="flex items-center gap-2 text-xs font-semibold text-emerald-200">
            
            <span>Resolved Weakness</span>
          </div>
          <p className="mt-1 text-[0.6875rem] text-emerald-300/80">
            Resolved from previous reviews:
          </p>
          <ul className="mt-2 space-y-1 text-xs text-emerald-100">
            {result.improvements.map((imp, i) => (
              <li key={i} className="flex items-start gap-1.5">
                <svg className="w-3 h-3 text-emerald-400 shrink-0" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5"><polyline points="20 6 9 17 4 12"/></svg>
                <span>{imp}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Longitudinal Weakness Memory: Persistent Recurring Blind Spots */}
      {result.persistent_weaknesses && result.persistent_weaknesses.length > 0 && (
        <div className="rounded-lg border border-rose-500/40 bg-rose-500/15 p-3.5">
          <div className="flex items-center gap-2 text-xs font-semibold text-rose-200">
            
            <span>Recurring Weakness</span>
          </div>
          <p className="mt-1 text-[0.6875rem] text-rose-300/80">
            Flagged in prior reviews:
          </p>
          <ul className="mt-2 space-y-1 text-xs text-rose-100">
            {result.persistent_weaknesses.map((pw, i) => (
              <li key={i} className="flex items-start gap-1.5">
                <span className="text-rose-400 font-bold">•</span>
                <span>{pw}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Longitudinal Weakness Memory: Newly Logged Flaws Stored for Next Time */}
      {result.weaknesses && result.weaknesses.length > 0 && (
        <div className="rounded-lg border border-amber-500/30 bg-amber-500/10 p-3 text-xs">
          <div className="flex items-center gap-1.5 font-semibold text-amber-200">
            
            <span>Saved to Memory:</span>
          </div>
          <p className="mt-1 text-[0.6875rem] text-amber-300/70">
            Noted for future reviews:
          </p>
          <ul className="mt-1.5 space-y-1 text-xs text-amber-100">
            {result.weaknesses.map((w, i) => (
              <li key={i} className="flex items-start gap-1.5">
                <span className="text-amber-400 font-bold">•</span>
                <span>{w}</span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  )
}

export interface TermHighlight {
  term: string
  type: 'overlooked' | 'matched'
}

export function highlightParts(text: string, terms: TermHighlight[]) {
  if (!terms.length || !text) return [{ text, type: null }]

  // Sort terms by length descending so longer phrases match first
  const sorted = [...terms]
    .filter((t) => t.term && t.term.trim().length > 1)
    .sort((a, b) => b.term.length - a.term.length)

  if (sorted.length === 0) return [{ text, type: null }]

  const uniqueTerms: TermHighlight[] = []
  const seen = new Set<string>()
  for (const t of sorted) {
    const key = t.term.trim().toLowerCase()
    if (!seen.has(key)) {
      seen.add(key)
      uniqueTerms.push({ term: t.term.trim(), type: t.type })
    }
  }

  const escaped = uniqueTerms
    .map((t) => t.term.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'))
    .join('|')

  let regex: RegExp
  try {
    regex = new RegExp(`(${escaped})`, 'gi')
  } catch {
    return [{ text, type: null }]
  }

  const parts = text.split(regex)
  const termMap = new Map<string, 'overlooked' | 'matched'>()
  for (const t of uniqueTerms) {
    termMap.set(t.term.toLowerCase(), t.type)
  }

  return parts
    .map((part) => ({
      text: part,
      type: termMap.get(part.toLowerCase()) || null,
    }))
    .filter((p) => p.text.length > 0)
}

/** Highlights text with amber for overlooked terms and emerald for matched terms. */
export function HighlightedText({
  text,
  overlookedPhrases = [],
  matchedPhrases = [],
  className = '',
}: {
  text: string
  overlookedPhrases?: string[]
  matchedPhrases?: string[]
  className?: string
}) {
  if (!text) return null

  const terms: TermHighlight[] = [
    ...overlookedPhrases.map((t) => ({ term: t, type: 'overlooked' as const })),
    ...matchedPhrases.map((t) => ({ term: t, type: 'matched' as const })),
  ]

  const mediaParts = text.split(/(!\[\]\([^)]+\)|\[audio\]\([^)]+\))/g)

  return (
    <div className={`whitespace-pre-wrap break-words ${className}`}>
      {mediaParts.map((part, i) => {
        const img = part.match(/^!\[\]\(([^)]+)\)$/)
        if (img) {
          const src = img[1].startsWith('/')
            ? `${API_BASE}${img[1]}`
            : img[1]
          return (
            <img
              key={i}
              src={src}
              alt=""
              className="my-2 max-h-72 rounded-lg border border-ink-line"
            />
          )
        }
        const audio = part.match(/^\[audio\]\(([^)]+)\)$/)
        if (audio) {
          const src = audio[1].startsWith('/')
            ? `${API_BASE}${audio[1]}`
            : audio[1]
          return <audio key={i} controls src={src} className="my-2 w-full" />
        }

        const segments = highlightParts(part, terms)
        return (
          <span key={i}>
            {segments.map((seg, j) => {
              if (seg.type === 'overlooked') {
                return (
                  <mark
                    key={j}
                    className="rounded border-b-2 border-amber-400 bg-amber-500/25 px-1 py-0.5 font-semibold text-amber-200 shadow-sm"
                    title="Overlooked"
                  >
                    {seg.text}
                  </mark>
                )
              }
              if (seg.type === 'matched') {
                return (
                  <mark
                    key={j}
                    className="rounded border-b border-emerald-500/40 bg-emerald-500/20 px-1 py-0.5 text-emerald-200"
                    title="Recalled"
                  >
                    {seg.text}
                  </mark>
                )
              }
              return <span key={j}>{seg.text}</span>
            })}
          </span>
        )
      })}
    </div>
  )
}
