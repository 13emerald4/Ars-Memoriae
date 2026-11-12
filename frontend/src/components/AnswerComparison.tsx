import React, { useMemo } from 'react'
import { API_BASE } from '../api/client'
import { CodeEditor } from './CodeEditor'
import { looksLikeCode, extractCleanCode, detectCodeLanguage } from '../utils/codeUtils'

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

export const TOKEN_REGEX = /(!\[\]\([^)]+\)|\[audio\]\([^)]+\)|(?<=^|\n)\s*(?:\d+|[a-zA-Z]|[ivxIVX]+)[\.\)]\s+|[\p{L}\p{N}_$]+(?:-[\p{L}\p{N}_$]+)*|[^\s\p{L}\p{N}]+|\s+)/gu
export const CODE_TOKEN_REGEX = /(!\[\]\([^)]+\)|\[audio\]\([^)]+\)|[\p{L}\p{N}_$]+|[^\s\p{L}\p{N}]+|\s+)/gu

export function isWord(token: string): boolean {
  if (!token || /^\s+$/.test(token)) return false
  if (/^\s*(?:\d+|[a-zA-Z]|[ivxIVX]+)[\.\)]\s+$/u.test(token)) return false
  return /^[\p{L}\p{N}_$]+(?:-[\p{L}\p{N}_$]+)*$/u.test(token)
}

export function isCodeWord(token: string): boolean {
  if (!token || /^\s+$/.test(token)) return false
  return /^[\p{L}\p{N}_$]+$/u.test(token)
}

function normalize(token: string): string {
  return token
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .toLowerCase()
    .replace(/[^\p{L}\p{N}_$-]/gu, '')
}

function normalizeCode(token: string): string {
  return token
    .toLowerCase()
    .replace(/[^\p{L}\p{N}_$]/gu, '')
}

const CONTRACTIONS: Record<string, string[]> = {
  del: ['de', 'el'],
  al: ['a', 'el'],
  de: ['del'],
  a: ['al'],
}

const STOPWORDS = new Set([
  // Spanish
  'el', 'la', 'los', 'las', 'un', 'una', 'unos', 'unas',
  'y', 'e', 'o', 'u',
  'de', 'del', 'a', 'al', 'en', 'con', 'por', 'para', 'sin', 'sobre', 'tras', 'entre', 'hasta', 'desde', 'hacia',
  'que', 'se', 'su', 'sus', 'mi', 'mis', 'tu', 'tus',
  // English
  'the', 'a', 'an', 'and', 'or', 'but', 'nor',
  'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 'from', 'as', 'into', 'like', 'through',
  'after', 'over', 'between', 'out', 'against', 'during', 'without', 'before', 'under', 'around', 'among',
  'is', 'are', 'was', 'were', 'be', 'been', 'being', 'it', 'its', 'that', 'these', 'those',
])

function isStopword(token: string): boolean {
  return STOPWORDS.has(normalize(token))
}

function stripSuffix(w: string, regex: RegExp, minLen: number = 3): string {
  const match = w.match(regex)
  if (match) {
    const stripped = w.slice(0, -match[0].length)
    if (stripped.length >= minLen) {
      return stripped
    }
  }
  return w
}

function stem(word: string): string {
  let w = normalize(word)
  if (w.length <= 3) return w

  // Adverb suffix
  w = stripSuffix(w, /(?:mente)$/)

  // Spanish derivational suffixes (e.g. joyería -> joy, escultor -> escult, religioso -> religi)
  w = stripSuffix(w, /(?:erias|eria|eros|ero|istas|ista|ismos|ismo|idades|idad|iciones|icion|aciones|acion|siones|sion)$/)
  w = stripSuffix(w, /(?:itas|ita|itos|ito|uras|ura|ores|or|osas|osa|osos|oso|icas|ica|icos|ico|ales|al)$/)

  // Inflectional suffixes (plurals, verb endings)
  w = stripSuffix(w, /(?:ing|es|ed|s)$/)
  w = stripSuffix(w, /(?:aron|eron|ando|iendo|ados|adas|ado|idos|idas|ido|ar|er|ir|[aeo])$/)

  return w
}

/**
 * Suppresses isolated stopwords from turning green when they appear stranded
 * within entirely missed or unmatched clauses (e.g., "( Dama [de] Elche )").
 * Stopwords are only kept as matched if they are anchored to at least one adjacent
 * matched content word within the same clause/sentence.
 */
function pruneOrphanedStopwords(tokens: TokenSegment[]): { pruned: TokenSegment[]; revertedCount: number } {
  const hasContentWords = tokens.some((t) => isWord(t.text) && !isStopword(t.text))
  if (!hasContentWords) {
    return { pruned: tokens, revertedCount: 0 }
  }

  let revertedCount = 0
  const result = tokens.map((t) => ({ ...t }))
  const isSentenceBoundary = (text: string) => /[.\n!?;:]/.test(text)

  for (let i = 0; i < result.length; i++) {
    const curr = result[i]
    if (curr.type !== 'matched' || !isWord(curr.text) || !isStopword(curr.text)) {
      continue
    }

    // Check backwards for an anchored matched content word
    let precedingMatched = false
    for (let j = i - 1; j >= 0; j--) {
      const prev = result[j]
      if (isSentenceBoundary(prev.text)) {
        break
      }
      if (isWord(prev.text)) {
        if (!isStopword(prev.text)) {
          if (prev.type === 'matched') {
            precedingMatched = true
          }
          break
        }
      }
    }

    // Check forwards for an anchored matched content word
    let succeedingMatched = false
    for (let j = i + 1; j < result.length; j++) {
      const next = result[j]
      if (isSentenceBoundary(next.text)) {
        break
      }
      if (isWord(next.text)) {
        if (!isStopword(next.text)) {
          if (next.type === 'matched') {
            succeedingMatched = true
          }
          break
        }
      }
    }

    if (!precedingMatched && !succeedingMatched) {
      curr.type = 'missing'
      revertedCount++
    }
  }

  return { pruned: result, revertedCount }
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
  _extraOverlooked: string[] = [],
  extraMatched: string[] = [],
  isCodeMode?: boolean
): {
  userSegments: TokenSegment[]
  refSegments: TokenSegment[]
  stats: DiffStats
} {
  const isCode = isCodeMode ?? (looksLikeCode(refText) || looksLikeCode(userText))
  const tokenRegex = isCode ? CODE_TOKEN_REGEX : TOKEN_REGEX
  const wordCheck = isCode ? isCodeWord : isWord
  const normFn = isCode ? normalizeCode : normalize

  const userRawTokens = userText.match(tokenRegex) || []
  const refRawTokens = refText.match(tokenRegex) || []

  // User word sets
  const userWords = new Set<string>()
  const userStems = new Set<string>()
  let userWordCount = 0
  for (const t of userRawTokens) {
    if (wordCheck(t)) {
      userWordCount++
      const w = normFn(t)
      if (w) userWords.add(w)
      if (!isCode) {
        const st = stem(t)
        if (st.length >= 3) userStems.add(st)
      }
    }
  }

  // Ref word sets
  const refWords = new Set<string>()
  const refStems = new Set<string>()
  for (const t of refRawTokens) {
    if (wordCheck(t)) {
      const w = normFn(t)
      if (w) refWords.add(w)
      if (!isCode) {
        const st = stem(t)
        if (st.length >= 3) refStems.add(st)
      }
    }
  }

  function wordMatches(tok: string, targetWords: Set<string>, targetStems: Set<string>): boolean {
    const w = normFn(tok)
    if (!w) return false
    if (targetWords.has(w)) return true
    if (!isCode) {
      const contractions = CONTRACTIONS[w]
      if (contractions && contractions.some((c) => targetWords.has(c))) return true
      const st = stem(tok)
      if (st.length >= 3 && targetStems.has(st)) return true
    }
    return false
  }

  // Extra semantic matched words from LLM grader
  const matchedSet = new Set(extraMatched.map((p) => p.trim().toLowerCase()).filter(Boolean))
  const semanticMatchedWords = new Set<string>()
  for (const phrase of matchedSet) {
    const words = phrase.match(tokenRegex)?.filter(wordCheck).map(normFn) || []
    for (const w of words) {
      if (w) semanticMatchedWords.add(w)
    }
  }

  let refMatchedCount = 0
  let refMissingCount = 0

  // 1. Annotate Reference tokens
  const annotatedRef: TokenSegment[] = refRawTokens.map((tok) => {
    if (/^!\[\]\(/.test(tok) || /^\[audio\]\(/.test(tok)) {
      return { text: tok, type: 'media' }
    }
    if (!wordCheck(tok)) {
      return { text: tok, type: 'punct' }
    }

    const isMatch = wordMatches(tok, userWords, userStems) || semanticMatchedWords.has(normFn(tok))
    if (isMatch) {
      refMatchedCount++
      return { text: tok, type: 'matched' }
    }

    refMissingCount++
    return { text: tok, type: 'missing' }
  })

  // 2. Annotate User tokens
  const annotatedUser: TokenSegment[] = userRawTokens.map((tok) => {
    if (/^!\[\]\(/.test(tok) || /^\[audio\]\(/.test(tok)) {
      return { text: tok, type: 'media' }
    }
    if (!wordCheck(tok)) {
      return { text: tok, type: 'punct' }
    }

    const isMatch = wordMatches(tok, refWords, refStems)
    if (isMatch) {
      return { text: tok, type: 'matched' }
    }

    // Unmatched words in user answer are marked missing (rendered in light yellow)
    return { text: tok, type: 'missing' }
  })

  const { pruned: prunedRef, revertedCount } = isCode
    ? { pruned: annotatedRef, revertedCount: 0 }
    : pruneOrphanedStopwords(annotatedRef)
  refMatchedCount = Math.max(0, refMatchedCount - revertedCount)
  refMissingCount += revertedCount

  const prunedUser = isCode ? annotatedUser : pruneOrphanedStopwords(annotatedUser).pruned

  const mergedRef = mergeContiguousTokens(prunedRef)
  const mergedUser = mergeContiguousTokens(prunedUser)

  const refWordCount = refMatchedCount + refMissingCount
  const recallPercent = refWordCount > 0 ? Math.round((refMatchedCount / refWordCount) * 100) : 100

  return {
    userSegments: mergedUser,
    refSegments: mergedRef,
    stats: {
      refWordCount,
      userWordCount,
      matchedCount: refMatchedCount,
      missingCount: refMissingCount,
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
          const audio = seg.text.match(/^\[audio\]\(([^)]+)\)$/)
          if (audio) {
            const src = audio[1].startsWith('/')
              ? `${API_BASE}${audio[1]}`
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
                title="Recalled"
              >
                {seg.text}
              </mark>
            )
          }
          return <span key={i}>{seg.text}</span>
        } else {
          // User mode: highlight words that matched reference in emerald, and incorrect/unmatched in light yellow
          if (seg.type === 'matched') {
            return (
              <mark
                key={i}
                className="rounded border-b border-emerald-500/40 bg-emerald-500/20 px-1 py-0.5 text-emerald-200 font-medium"
                title="Matches reference"
              >
                {seg.text}
              </mark>
            )
          }
          if (seg.type === 'missing') {
            return (
              <mark
                key={i}
                className="rounded border-b-2 border-amber-400/80 bg-amber-500/20 px-1 py-0.5 text-amber-200 font-normal shadow-sm"
                title="Not in reference"
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
  const [refViewMode, setRefViewMode] = React.useState<'ide' | 'diff'>('ide')
  const hasUserAnswer = Boolean(userAnswer && userAnswer.trim().length > 0)
  const hasTestCode = Boolean(userTestCode && userTestCode.trim().length > 0)

  const isCode = Boolean(
    isCodeCard ||
      looksLikeCode(referenceAnswer) ||
      (hasUserAnswer && looksLikeCode(userAnswer))
  )
  const cleanRef = useMemo(() => (isCode ? extractCleanCode(referenceAnswer) : referenceAnswer), [isCode, referenceAnswer])
  const cleanUser = useMemo(() => (isCode ? extractCleanCode(userAnswer) : userAnswer), [isCode, userAnswer])
  const refLang = useMemo(
    () => (isCode ? detectCodeLanguage(cleanRef, codeLanguage) : codeLanguage),
    [isCode, cleanRef, codeLanguage]
  )

  const { userSegments, refSegments, stats } = useMemo(() => {
    const activeRef = isCode ? cleanRef : referenceAnswer
    const activeUser = isCode ? cleanUser : userAnswer
    const tokenRegex = isCode ? CODE_TOKEN_REGEX : TOKEN_REGEX
    const wordCheck = isCode ? isCodeWord : isWord

    if (!hasUserAnswer) {
      return {
        userSegments: [],
        refSegments: [{ text: activeRef, type: 'neutral' as const }],
        stats: {
          refWordCount: (activeRef.match(tokenRegex) || []).filter(wordCheck).length,
          userWordCount: 0,
          matchedCount: 0,
          missingCount: 0,
          recallPercent: 0,
        },
      }
    }
    return computeTokenDiff(activeUser, activeRef, overlookedPhrases, matchedPhrases, isCode)
  }, [userAnswer, referenceAnswer, hasUserAnswer, overlookedPhrases, matchedPhrases, isCode, cleanRef, cleanUser])

  return (
    <div className={`space-y-3 ${className}`}>
      {/* ── 1. User's Answer Directly Above Reference Answer ── */}
      <div className="rounded-lg border border-ink-line/80 bg-ink-soft/40 p-4 transition-colors">
        <div className="mb-2.5 flex flex-wrap items-center justify-between gap-2 border-b border-ink-line/40 pb-2">
          <div className="flex items-center gap-2">
            {isCode && hasTestCode ? (
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
                  Solution
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
                  Unit Tests
                </button>
              </div>
            ) : (
              <span className="text-xs font-semibold tracking-wide uppercase text-slate-300">
                {isCode ? 'Your Solution' : 'Your Answer'}
              </span>
            )}
            {hasUserAnswer && (
              <span className="rounded bg-white/5 px-1.5 py-0.5 text-[0.6875rem] font-mono text-slate-400">
                {stats.userWordCount} {stats.userWordCount === 1 ? 'word' : 'words'}
              </span>
            )}
          </div>

          {hasUserAnswer && stats.refWordCount > 0 && (
            <div className="flex items-center gap-2 text-[0.6875rem]">
              <span className="flex items-center gap-1 font-medium text-emerald-300">
                <span className="inline-block h-2 w-2 rounded-full bg-emerald-400" />
                {stats.matchedCount}/{stats.refWordCount} recalled ({stats.recallPercent}%)
              </span>
            </div>
          )}
        </div>

        {hasUserAnswer ? (
          isCode ? (
            <div className="rounded-lg border border-ink-line/80 overflow-hidden shadow-xs">
              <CodeEditor
                code={activeCodeTab === 'solution' ? cleanUser : userTestCode}
                onChange={() => {}}
                language={codeLanguage || refLang}
                readOnly={true}
                height="auto"
                hideHeader={true}
                hideFooter={true}
                borderless={true}
              />
            </div>
          ) : (
            <RenderTokenSegments
              segments={userSegments}
              mode="user"
              className="text-slate-200 leading-relaxed text-sm"
            />
          )
        ) : (
          <p className="text-sm italic text-slate-500 py-1">
            (No answer entered)
          </p>
        )}
      </div>

      {/* ── 2. Reference Answer Directly Below User Answer ── */}
      <div className="rounded-lg border border-ink-line bg-ink p-4">
        <div className="mb-2.5 flex flex-wrap items-center justify-between gap-2 border-b border-ink-line/40 pb-2">
          <div className="flex items-center gap-2">
            <span className="text-xs font-semibold tracking-wide uppercase text-slate-300">
              {isCode ? 'Reference Solution' : 'Reference'}
            </span>
            {isCode && (codeLanguage || refLang) && (
              <span className="rounded bg-sky-500/10 px-1.5 py-0.5 text-[0.6875rem] font-mono text-sky-300 border border-sky-500/30">
                {codeLanguage || refLang}
              </span>
            )}
            {timeComplexity && (
              <span className="text-xs font-mono text-sky-300 rounded bg-sky-500/10 px-1.5 py-0.5 border border-sky-500/30">
                {timeComplexity}
              </span>
            )}
            {isCode && hasUserAnswer && (
              <div className="inline-flex rounded-md bg-[#161616] p-0.5 border border-ink-line text-[0.6875rem] ml-1">
                <button
                  type="button"
                  onClick={() => setRefViewMode('ide')}
                  className={`px-2 py-0.5 rounded transition ${
                    refViewMode === 'ide'
                      ? 'bg-sky-600/30 text-sky-200 border border-sky-500/50 font-medium'
                      : 'text-slate-400 hover:text-slate-200'
                  }`}
                  title="IDE syntax-highlighted code format"
                >
                  IDE
                </button>
                <button
                  type="button"
                  onClick={() => setRefViewMode('diff')}
                  className={`px-2 py-0.5 rounded transition ${
                    refViewMode === 'diff'
                      ? 'bg-amber-600/30 text-amber-200 border border-amber-500/50 font-medium'
                      : 'text-slate-400 hover:text-slate-200'
                  }`}
                  title="Token diff comparison"
                >
                  Diff
                </button>
              </div>
            )}
          </div>

          {hasUserAnswer ? (
            <div className="flex items-center gap-3 text-[0.6875rem]">
              {stats.missingCount > 0 && (
                <span className="flex items-center gap-1.5 font-semibold text-amber-300" title="Missing">
                  <span className="inline-block h-2 w-2 rounded-full bg-amber-400 animate-pulse" />
                  Missing ({stats.missingCount})
                </span>
              )}
              {stats.matchedCount > 0 && (
                <span className="flex items-center gap-1.5 font-medium text-emerald-300" title="Recalled">
                  <span className="inline-block h-2 w-2 rounded-full bg-emerald-400" />
                  Recalled ({stats.matchedCount})
                </span>
              )}
            </div>
          ) : (
            (overlookedPhrases.length > 0 || matchedPhrases.length > 0) && (
              <div className="flex items-center gap-3 text-[0.6875rem]">
                {overlookedPhrases.length > 0 && (
                  <span className="flex items-center gap-1 font-medium text-amber-300">
                    <span className="inline-block h-2 w-2 rounded-full bg-amber-400" />
                    Overlooked
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

        {isCode && (!hasUserAnswer || refViewMode === 'ide') ? (
          <div className="rounded-lg border border-ink-line/80 overflow-hidden shadow-xs">
            <CodeEditor
              code={cleanRef}
              onChange={() => {}}
              language={codeLanguage || refLang}
              readOnly={true}
              height="auto"
              hideHeader={false}
              hideFooter={false}
              borderless={true}
              placeholder="// Reference solution"
            />
          </div>
        ) : hasUserAnswer ? (
          <RenderTokenSegments
            segments={refSegments}
            mode="ref"
            className={
              isCode
                ? 'text-slate-200 font-mono text-xs whitespace-pre-wrap leading-relaxed'
                : 'text-slate-200 leading-relaxed text-sm'
            }
          />
        ) : (
          <div
            className={`whitespace-pre-wrap break-words ${
              isCode
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
