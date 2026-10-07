import React, { useMemo } from 'react'

export interface TokenSegment {
  text: string
  type: 'matched' | 'missing' | 'neutral' | 'punct' | 'media'
}

export interface DiffStats {
  refWordCount: number
  userWordCount: number
  matchedCount: number
  missingCount: number
  recallPercent: number
}

const TOKEN_REGEX = /(!\[\]\([^)]+\)|\[audio\]\([^)]+\)|[a-zA-Z0-9_$]+(?:-[a-zA-Z0-9_$]+)*|[^\s\w]+|\s+)/g

function isWord(token: string): boolean {
  return /^[a-zA-Z0-9_$]+(?:-[a-zA-Z0-9_$]+)*$/.test(token)
}

function normalize(token: string): string {
  return token.toLowerCase().replace(/[^a-z0-9_$-]/g, '')
}

function stem(word: string): string {
  const w = normalize(word)
  if (w.length <= 3) return w
  return w.replace(/(?:ing|es|ed|s)$/, '')
}

/** Merges contiguous tokens of the same type when separated only by whitespace */
function mergeContiguousTokens(tokens: TokenSegment[]): TokenSegment[] {
  const merged: TokenSegment[] = []
  for (let i = 0; i < tokens.length; i++) {
    const curr = tokens[i]
    if (curr.type === 'punct' && /^\s+$/.test(curr.text) && merged.length > 0 && i + 1 < tokens.length) {
      const prev = merged[merged.length - 1]
      const next = tokens[i + 1]
      if (prev.type === next.type && prev.type !== 'punct') {
        prev.text += curr.text
        continue
      }
    }
    if (merged.length > 0 && merged[merged.length - 1].type === curr.type) {
      merged[merged.length - 1].text += curr.text
    } else {
      merged.push({ ...curr })
    }
  }
  return merged
}

export function computeTokenDiff(
  userText: string,
  refText: string,
  extraOverlooked: string[] = [],
  extraMatched: string[] = []
): {
  userSegments: TokenSegment[]
  refSegments: TokenSegment[]
  stats: DiffStats
} {
  const userRawTokens = userText.match(TOKEN_REGEX) || []
  const refRawTokens = refText.match(TOKEN_REGEX) || []

  // Count user words for reference comparison
  const userWordCounts = new Map<string, number>()
  let userWordCount = 0
  for (const t of userRawTokens) {
    if (isWord(t)) {
      userWordCount++
      const w = normalize(t)
      userWordCounts.set(w, (userWordCounts.get(w) || 0) + 1)
    }
  }

  // Count ref words for user comparison
  const refWordCounts = new Map<string, number>()
  let refWordCount = 0
  for (const t of refRawTokens) {
    if (isWord(t)) {
      refWordCount++
      const w = normalize(t)
      refWordCounts.set(w, (refWordCounts.get(w) || 0) + 1)
    }
  }

  // Set of semantic phrases from LLM
  const overlookedSet = new Set(extraOverlooked.map((p) => p.trim().toLowerCase()).filter(Boolean))
  const matchedSet = new Set(extraMatched.map((p) => p.trim().toLowerCase()).filter(Boolean))

  let matchedCount = 0
  let missingCount = 0

  // 1. Annotate Reference tokens
  const annotatedRef: TokenSegment[] = refRawTokens.map((tok) => {
    if (/^!\[\]\(/.test(tok) || /^\[audio\]\(/.test(tok)) {
      return { text: tok, type: 'media' }
    }
    if (!isWord(tok)) {
      return { text: tok, type: 'punct' }
    }

    const w = normalize(tok)

    // Check if user has this exact word available
    if ((userWordCounts.get(w) || 0) > 0) {
      userWordCounts.set(w, (userWordCounts.get(w) || 0) - 1)
      matchedCount++
      return { text: tok, type: 'matched' }
    }

    // Check stem match fallback
    const st = stem(tok)
    for (const [uw, cnt] of userWordCounts.entries()) {
      if (cnt > 0 && stem(uw) === st) {
        userWordCounts.set(uw, cnt - 1)
        matchedCount++
        return { text: tok, type: 'matched' }
      }
    }

    // Otherwise, this token was missing from the user answer
    missingCount++
    return { text: tok, type: 'missing' }
  })

  // Also enforce extra overlooked phrases from LLM grader
  if (overlookedSet.size > 0) {
    for (const phrase of overlookedSet) {
      if (!phrase) continue
      const phraseWords = phrase.match(TOKEN_REGEX)?.filter(isWord).map(normalize) || []
      if (phraseWords.length === 0) continue
      for (const seg of annotatedRef) {
        if (seg.type === 'matched' && phraseWords.includes(normalize(seg.text))) {
          seg.type = 'missing'
          missingCount++
          if (matchedCount > 0) matchedCount--
        }
      }
    }
  }

  // Also enforce extra matched phrases from LLM grader
  if (matchedSet.size > 0) {
    for (const phrase of matchedSet) {
      if (!phrase) continue
      const phraseWords = phrase.match(TOKEN_REGEX)?.filter(isWord).map(normalize) || []
      if (phraseWords.length === 0) continue
      for (const seg of annotatedRef) {
        if (seg.type === 'missing' && phraseWords.includes(normalize(seg.text))) {
          seg.type = 'matched'
          matchedCount++
          if (missingCount > 0) missingCount--
        }
      }
    }
  }

  // 2. Annotate User tokens
  const annotatedUser: TokenSegment[] = userRawTokens.map((tok) => {
    if (/^!\[\]\(/.test(tok) || /^\[audio\]\(/.test(tok)) {
      return { text: tok, type: 'media' }
    }
    if (!isWord(tok)) {
      return { text: tok, type: 'punct' }
    }

    const w = normalize(tok)
    if ((refWordCounts.get(w) || 0) > 0) {
      refWordCounts.set(w, (refWordCounts.get(w) || 0) - 1)
      return { text: tok, type: 'matched' }
    }

    const st = stem(tok)
    for (const [rw, cnt] of refWordCounts.entries()) {
      if (cnt > 0 && stem(rw) === st) {
        refWordCounts.set(rw, cnt - 1)
        return { text: tok, type: 'matched' }
      }
    }

    return { text: tok, type: 'neutral' }
  })

  const mergedRef = mergeContiguousTokens(annotatedRef)
  const mergedUser = mergeContiguousTokens(annotatedUser)

  const recallPercent = refWordCount > 0 ? Math.round((matchedCount / refWordCount) * 100) : 100

  return {
    userSegments: mergedUser,
    refSegments: mergedRef,
    stats: {
      refWordCount,
      userWordCount,
      matchedCount,
      missingCount,
      recallPercent,
    },
  }
}

/** Renders media tags or marked segments */
function RenderTokenSegments({
  segments,
  mode,
  className = '',
}: {
  segments: TokenSegment[]
  mode: 'user' | 'ref'
  className?: string
}) {
  return (
    <div className={`whitespace-pre-wrap break-words ${className}`}>
      {segments.map((seg, i) => {
        if (seg.type === 'media') {
          const img = seg.text.match(/^!\[\]\(([^)]+)\)$/)
          if (img) {
            const src = img[1].startsWith('/')
              ? `${import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000'}${img[1]}`
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
          const audio = seg.text.match(/^\[audio\]\(([^)]+)\)$/)
          if (audio) {
            const src = audio[1].startsWith('/')
              ? `${import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000'}${audio[1]}`
              : audio[1]
            return <audio key={i} controls src={src} className="my-2 w-full" />
          }
        }

        if (mode === 'ref') {
          if (seg.type === 'missing') {
            return (
              <mark
                key={i}
                className="rounded border-b-2 border-amber-400 bg-amber-500/25 px-1 py-0.5 font-semibold text-amber-200 shadow-sm"
                title="Missing from your answer"
              >
                {seg.text}
              </mark>
            )
          }
          if (seg.type === 'matched') {
            return (
              <mark
                key={i}
                className="rounded border-b border-emerald-500/40 bg-emerald-500/20 px-1 py-0.5 text-emerald-200 font-normal"
                title="Successfully recalled in your answer"
              >
                {seg.text}
              </mark>
            )
          }
          return <span key={i}>{seg.text}</span>
        } else {
          // User mode: highlight words that matched reference in emerald
          if (seg.type === 'matched') {
            return (
              <mark
                key={i}
                className="rounded border-b border-emerald-500/40 bg-emerald-500/20 px-1 py-0.5 text-emerald-200 font-medium"
                title="Present in reference answer"
              >
                {seg.text}
              </mark>
            )
          }
          return <span key={i} className="text-slate-300">{seg.text}</span>
        }
      })}
    </div>
  )
}

export interface AnswerComparisonProps {
  userAnswer: string
  userTestCode?: string
  referenceAnswer: string
  isCodeCard?: boolean
  codeLanguage?: string
  timeComplexity?: string | null
  overlookedPhrases?: string[]
  matchedPhrases?: string[]
  className?: string
}

export function AnswerComparison({
  userAnswer,
  userTestCode = '',
  referenceAnswer,
  isCodeCard = false,
  codeLanguage = 'typescript',
  timeComplexity = null,
  overlookedPhrases = [],
  matchedPhrases = [],
  className = '',
}: AnswerComparisonProps) {
  const [activeCodeTab, setActiveCodeTab] = React.useState<'solution' | 'tests'>('solution')
  const hasUserAnswer = Boolean(userAnswer && userAnswer.trim().length > 0)
  const hasTestCode = Boolean(userTestCode && userTestCode.trim().length > 0)

  const { userSegments, refSegments, stats } = useMemo(() => {
    if (!hasUserAnswer) {
      return {
        userSegments: [],
        refSegments: [{ text: referenceAnswer, type: 'neutral' as const }],
        stats: {
          refWordCount: (referenceAnswer.match(TOKEN_REGEX) || []).filter(isWord).length,
          userWordCount: 0,
          matchedCount: 0,
          missingCount: 0,
          recallPercent: 0,
        },
      }
    }
    return computeTokenDiff(userAnswer, referenceAnswer, overlookedPhrases, matchedPhrases)
  }, [userAnswer, referenceAnswer, hasUserAnswer, overlookedPhrases, matchedPhrases])

  return (
    <div className={`space-y-3 ${className}`}>
      {/* ── 1. User's Answer Directly Above Reference Answer ── */}
      <div className="rounded-lg border border-ink-line/80 bg-ink-soft/40 p-4 transition-colors">
        <div className="mb-2.5 flex flex-wrap items-center justify-between gap-2 border-b border-ink-line/40 pb-2">
          <div className="flex items-center gap-2">
            {isCodeCard && hasTestCode ? (
              <div className="inline-flex rounded-md bg-[#161616] p-0.5 border border-ink-line">
                <button
                  type="button"
                  onClick={() => setActiveCodeTab('solution')}
                  className={`px-2 py-0.5 text-xs font-medium rounded transition ${
                    activeCodeTab === 'solution'
                      ? 'bg-sky-600/30 text-sky-200 border border-sky-500/50'
                      : 'text-slate-400 hover:text-slate-200'
                  }`}
                >
                  💻 Solution
                </button>
                <button
                  type="button"
                  onClick={() => setActiveCodeTab('tests')}
                  className={`px-2 py-0.5 text-xs font-medium rounded transition ${
                    activeCodeTab === 'tests'
                      ? 'bg-indigo-600/30 text-indigo-200 border border-indigo-500/50'
                      : 'text-slate-400 hover:text-slate-200'
                  }`}
                >
                  🧪 Unit Tests
                </button>
              </div>
            ) : (
              <span className="text-xs font-semibold tracking-wide uppercase text-slate-300">
                {isCodeCard ? 'Your Solution' : 'Your Answer'}
              </span>
            )}
            {hasUserAnswer && (
              <span className="rounded bg-white/5 px-1.5 py-0.5 text-[11px] font-mono text-slate-400">
                {stats.userWordCount} {stats.userWordCount === 1 ? 'word' : 'words'}
              </span>
            )}
          </div>

          {hasUserAnswer && stats.matchedCount > 0 && (
            <div className="flex items-center gap-2 text-[11px]">
              <span className="flex items-center gap-1 font-medium text-emerald-300">
                <span className="inline-block h-2 w-2 rounded-full bg-emerald-400" />
                {stats.matchedCount} of {stats.refWordCount} reference terms recalled ({stats.recallPercent}%)
              </span>
            </div>
          )}
        </div>

        {hasUserAnswer ? (
          isCodeCard ? (
            <pre className="p-3 rounded bg-[#121212] border border-ink-line/60 text-xs font-mono text-slate-200 overflow-x-auto whitespace-pre-wrap leading-relaxed">
              <code>{activeCodeTab === 'solution' ? userAnswer : userTestCode}</code>
            </pre>
          ) : (
            <RenderTokenSegments
              segments={userSegments}
              mode="user"
              className="text-slate-200 leading-relaxed text-sm"
            />
          )
        ) : (
          <p className="text-sm italic text-slate-500 py-1">
            (No answer typed — showing reference answer below)
          </p>
        )}
      </div>

      {/* ── 2. Reference Answer Directly Below User Answer ── */}
      <div className="rounded-lg border border-ink-line bg-ink p-4">
        <div className="mb-2.5 flex flex-wrap items-center justify-between gap-2 border-b border-ink-line/40 pb-2">
          <div className="flex items-center gap-2">
            <span className="text-xs font-semibold tracking-wide uppercase text-slate-300">
              {isCodeCard ? 'Reference Solution' : 'Reference Answer'}
            </span>
            {isCodeCard && codeLanguage && (
              <span className="rounded bg-sky-500/10 px-1.5 py-0.5 text-[11px] font-mono text-sky-300 border border-sky-500/30">
                {codeLanguage}
              </span>
            )}
            {timeComplexity && (
              <span className="text-xs font-mono text-sky-300 rounded bg-sky-500/10 px-1.5 py-0.5 border border-sky-500/30">
                {timeComplexity}
              </span>
            )}
          </div>

          {hasUserAnswer ? (
            <div className="flex items-center gap-3 text-[11px]">
              {stats.missingCount > 0 && (
                <span className="flex items-center gap-1.5 font-semibold text-amber-300" title="Words present in reference answer but omitted from your answer">
                  <span className="inline-block h-2 w-2 rounded-full bg-amber-400 animate-pulse" />
                  Missing from your answer ({stats.missingCount})
                </span>
              )}
              {stats.matchedCount > 0 && (
                <span className="flex items-center gap-1.5 font-medium text-emerald-300" title="Words present in both your answer and reference answer">
                  <span className="inline-block h-2 w-2 rounded-full bg-emerald-400" />
                  Recalled ({stats.matchedCount})
                </span>
              )}
            </div>
          ) : (
            (overlookedPhrases.length > 0 || matchedPhrases.length > 0) && (
              <div className="flex items-center gap-3 text-[11px]">
                {overlookedPhrases.length > 0 && (
                  <span className="flex items-center gap-1 font-medium text-amber-300">
                    <span className="inline-block h-2 w-2 rounded-full bg-amber-400" />
                    Overlooked in your answer
                  </span>
                )}
                {matchedPhrases.length > 0 && (
                  <span className="flex items-center gap-1 font-medium text-emerald-300">
                    <span className="inline-block h-2 w-2 rounded-full bg-emerald-400" />
                    Recalled
                  </span>
                )}
              </div>
            )
          )}
        </div>

        {hasUserAnswer ? (
          <RenderTokenSegments
            segments={refSegments}
            mode="ref"
            className={
              isCodeCard
                ? 'text-slate-200 font-mono text-xs whitespace-pre-wrap leading-relaxed'
                : 'text-slate-200 leading-relaxed text-sm'
            }
          />
        ) : (
          <div
            className={`whitespace-pre-wrap break-words ${
              isCodeCard
                ? 'text-slate-200 font-mono text-xs'
                : 'text-slate-200 text-sm leading-relaxed'
            }`}
          >
            {referenceAnswer}
          </div>
        )}
      </div>
    </div>
  )
}
