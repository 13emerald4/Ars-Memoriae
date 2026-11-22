import type { CardRecord, Grade } from './types.ts'

const STOP_WORDS = new Set([
  'a', 'an', 'and', 'are', 'as', 'at', 'be', 'by', 'for', 'from', 'has', 'have',
  'in', 'is', 'it', 'its', 'of', 'on', 'or', 'that', 'the', 'to', 'was', 'were',
  'will', 'with', 'this', 'these', 'those', 'can', 'not', 'but', 'you', 'your',
])

export function tokenize(text: string): string[] {
  return (text || '')
    .toLowerCase()
    .replace(/[^a-z0-9_]+/g, ' ')
    .split(/\s+/)
    .filter((w) => w.length > 1 && !STOP_WORDS.has(w))
}

function trigrams(text: string): Set<string> {
  const clean = (text || '').toLowerCase().replace(/\s+/g, ' ').trim()
  const set = new Set<string>()
  if (clean.length < 3) {
    if (clean) set.add(clean)
    return set
  }
  for (let i = 0; i <= clean.length - 3; i++) {
    set.add(clean.slice(i, i + 3))
  }
  return set
}

export function jaccardSimilarity(a: string, b: string): number {
  const ta = new Set(tokenize(a))
  const tb = new Set(tokenize(b))
  if (ta.size === 0 && tb.size === 0) return 0
  let inter = 0
  for (const w of ta) if (tb.has(w)) inter++
  const union = ta.size + tb.size - inter
  return union === 0 ? 0 : inter / union
}

export function trigramSimilarity(a: string, b: string): number {
  const ta = trigrams(a)
  const tb = trigrams(b)
  if (ta.size === 0 && tb.size === 0) return 0
  let inter = 0
  for (const t of ta) if (tb.has(t)) inter++
  const union = ta.size + tb.size - inter
  return union === 0 ? 0 : inter / union
}

export function extractKeyPhrases(reference: string): string[] {
  const cleaned = reference
    .replace(/```[\s\S]*?```/g, (m) => m.replace(/```[a-z]*\n?/gi, '').replace(/```/g, ''))
    .trim()
  const parts = cleaned
    .split(/(?:[\n;•]+|\.\s+)/)
    .map((s) => s.replace(/^[-*0-9.)\s]+/, '').trim())
    .filter((s) => s.length >= 4)
  if (parts.length > 0) return parts.slice(0, 6)
  return cleaned ? [cleaned] : []
}

export interface GradingEvaluation {
  suggested_grade: Grade
  score: number
  confidence: number
  matched_points: string[]
  missed_points: string[]
  overlooked_phrases: string[]
  weaknesses: string[]
  improvements: string[]
  reasoning: string
  heuristic_overlap: number
}

export function evaluateTypedAnswer(
  typedAnswer: string,
  referenceAnswer: string,
  gradingBias = 0,
): GradingEvaluation {
  const trimmed = (typedAnswer || '').trim()
  const refTrimmed = (referenceAnswer || '').trim()

  if (!trimmed) {
    return {
      suggested_grade: 'again',
      score: 0,
      confidence: 0.95,
      matched_points: [],
      missed_points: extractKeyPhrases(refTrimmed),
      overlooked_phrases: extractKeyPhrases(refTrimmed).slice(0, 3),
      weaknesses: ['No recall response provided'],
      improvements: ['Attempt to recall at least one core mechanism or definition before revealing'],
      reasoning: 'Empty response — marked as Again so the card re-enters short-term recall.',
      heuristic_overlap: 0,
    }
  }

  const refTokens = tokenize(refTrimmed)
  const ansTokens = new Set(tokenize(trimmed))
  const uniqueRef = Array.from(new Set(refTokens))

  let refMatched = 0
  for (const t of uniqueRef) {
    if (ansTokens.has(t)) refMatched++
  }
  const recallRatio = uniqueRef.length > 0 ? refMatched / uniqueRef.length : 0
  const jaccard = jaccardSimilarity(trimmed, refTrimmed)
  const tri = trigramSimilarity(trimmed, refTrimmed)

  const exactNorm = trimmed.toLowerCase().replace(/\s+/g, ' ') === refTrimmed.toLowerCase().replace(/\s+/g, ' ')
  const rawOverlap = exactNorm ? 1 : Math.min(1, recallRatio * 0.55 + jaccard * 0.25 + tri * 0.2)
  const biasedOverlap = Math.max(0, Math.min(1, rawOverlap + gradingBias * 0.08))
  const score = Math.round(biasedOverlap * 100)

  const phrases = extractKeyPhrases(refTrimmed)
  const matched_points: string[] = []
  const missed_points: string[] = []

  for (const phrase of phrases) {
    const pTokens = tokenize(phrase)
    if (pTokens.length === 0) continue
    const hits = pTokens.filter((t) => ansTokens.has(t)).length
    if (hits / pTokens.length >= 0.45 || trimmed.toLowerCase().includes(phrase.toLowerCase())) {
      matched_points.push(phrase)
    } else {
      missed_points.push(phrase)
    }
  }

  let suggested_grade: Grade
  if (score >= 88) suggested_grade = 'easy'
  else if (score >= 65) suggested_grade = 'good'
  else if (score >= 40) suggested_grade = 'hard'
  else suggested_grade = 'again'

  const weaknesses: string[] = []
  const improvements: string[] = []
  if (missed_points.length > 0) {
    weaknesses.push(`Missed ${missed_points.length} key point${missed_points.length === 1 ? '' : 's'} from the reference`)
    improvements.push(`Explicitly include: "${missed_points[0].slice(0, 90)}"`)
  }
  if (trimmed.length < refTrimmed.length * 0.35 && score < 85) {
    improvements.push('Expand your explanation to cover the full mechanism or edge cases')
  }

  const reasoning = exactNorm
    ? 'Exact match with the reference answer.'
    : `Semantic token-overlap & trigram heuristic scored ${score}% (${matched_points.length}/${phrases.length || 1} key points matched). Review the diff and confirm or override the suggested grade.`

  return {
    suggested_grade,
    score,
    confidence: Number((0.55 + Math.abs(biasedOverlap - 0.5) * 0.7).toFixed(2)),
    matched_points,
    missed_points,
    overlooked_phrases: missed_points.slice(0, 3),
    weaknesses,
    improvements,
    reasoning,
    heuristic_overlap: Number(rawOverlap.toFixed(3)),
  }
}

export function computeRetrievability(card: CardRecord, nowMs = Date.now()): number {
  if (card.state === 'new' || !card.stability || !card.due) return 0
  const stabilityDays = Math.max(0.1, card.stability)
  const dueMs = new Date(card.due).getTime()
  const elapsedFromDueDays = (nowMs - dueMs) / 86_400_000
  const elapsedDays = Math.max(0, stabilityDays + elapsedFromDueDays)
  // FSRS forgetting curve: R(t, S) = (1 + t / (9 * S))^-1
  const r = Math.pow(1 + elapsedDays / (9 * stabilityDays), -1)
  return Number(Math.max(0.01, Math.min(1, r)).toFixed(3))
}

export function scheduleFsrs(
  card: CardRecord,
  grade: Grade,
  desiredRetention = 0.9,
): {
  next_due: string
  new_stability: number
  new_difficulty: number
  state: CardRecord['state']
  interval_days: number
  lapse_count: number
} {
  const curS = card.stability ?? 1.0
  const curD = card.difficulty ?? 5.0
  let newD = curD
  let newS = curS
  let state: CardRecord['state'] = card.state
  let lapseCount = card.lapse_count

  if (grade === 'again') {
    newD = Math.min(10, curD + 1.2)
    newS = Math.max(0.25, curS * 0.35)
    state = card.state === 'new' ? 'learning' : 'relearning'
    lapseCount += 1
  } else if (grade === 'hard') {
    newD = Math.min(10, curD + 0.4)
    newS = card.state === 'new' ? 1.2 : Math.max(1, curS * 1.25)
    state = 'review'
  } else if (grade === 'good') {
    newD = Math.max(1, curD - 0.1)
    newS = card.state === 'new' ? 3.0 : Math.max(2, curS * (2.2 - curD * 0.08))
    state = 'review'
  } else {
    newD = Math.max(1, curD - 0.6)
    newS = card.state === 'new' ? 6.0 : Math.max(4, curS * (3.1 - curD * 0.09))
    state = 'review'
  }

  // Convert desired retention into interval scaling factor
  const retentionFactor = Math.max(0.3, Math.min(2.0, (1 / desiredRetention - 1) / (1 / 0.9 - 1)))
  const rawInterval = grade === 'again' ? 0.01 : Math.max(0.5, newS * retentionFactor)
  const intervalDays = Number(rawInterval.toFixed(2))
  const nextDueMs =
    grade === 'again'
      ? Date.now() + 10 * 60 * 1000
      : Date.now() + Math.round(intervalDays * 86_400_000)

  return {
    next_due: new Date(nextDueMs).toISOString(),
    new_stability: Number(newS.toFixed(2)),
    new_difficulty: Number(newD.toFixed(2)),
    state,
    interval_days: intervalDays,
    lapse_count: lapseCount,
  }
}

export function formatIntervalHuman(days: number): string {
  if (days < 1 / 24) return `${Math.max(1, Math.round(days * 1440))}m`
  if (days < 1) return `${Math.max(1, Math.round(days * 24))}h`
  if (days < 30) return `${Math.round(days)}d`
  if (days < 365) return `${(days / 30).toFixed(1)}mo`
  return `${(days / 365).toFixed(1)}y`
}

export function previewNextIntervals(card: CardRecord, desiredRetention = 0.9) {
  return {
    again: formatIntervalHuman(scheduleFsrs(card, 'again', desiredRetention).interval_days),
    hard: formatIntervalHuman(scheduleFsrs(card, 'hard', desiredRetention).interval_days),
    good: formatIntervalHuman(scheduleFsrs(card, 'good', desiredRetention).interval_days),
    easy: formatIntervalHuman(scheduleFsrs(card, 'easy', desiredRetention).interval_days),
  }
}

export function lintAtomicity(front: string, back: string, templateKind = 'basic') {
  const wf = (front || '').trim().split(/\s+/).filter(Boolean).length
  const wb = (back || '').trim().split(/\s+/).filter(Boolean).length
  const total = wf + wb
  const issues: Array<{ severity: 'info' | 'warning' | 'danger'; code: string; message: string; suggestion: string }> = []
  let score = 100

  if (wb > 60 && templateKind !== 'code') {
    score -= 30
    issues.push({
      severity: 'danger',
      code: 'LONG_ANSWER',
      message: `Back has ${wb} words (recommended <= 40 words for atomic recall).`,
      suggestion: 'Split this card into 2–3 smaller, single-fact cards.',
    })
  } else if (wb > 35 && templateKind !== 'code') {
    score -= 15
    issues.push({
      severity: 'warning',
      code: 'MODERATE_ANSWER',
      message: `Back has ${wb} words, which may test multiple facts at once.`,
      suggestion: 'Tighten the reference answer or extract secondary points into sibling cards.',
    })
  }

  if (/\band\b.*\band\b/i.test(front) || (front.match(/\?/g) || []).length > 1) {
    score -= 20
    issues.push({
      severity: 'warning',
      code: 'COMPOUND_PROMPT',
      message: 'Prompt appears to ask multiple questions simultaneously.',
      suggestion: 'Ask one unambiguous question per card.',
    })
  }

  if (wf < 3) {
    score -= 15
    issues.push({
      severity: 'info',
      code: 'VAGUE_PROMPT',
      message: 'Very short prompt may lack sufficient retrieval cues.',
      suggestion: 'Add domain context so the prompt uniquely identifies the target concept.',
    })
  }

  return {
    score: Math.max(0, score),
    is_atomic: score >= 75,
    word_count_front: wf,
    word_count_back: wb,
    word_count_total: total,
    issues,
  }
}
