import type { LexiconGlossItem } from '../api/types'

const META_DEFINITION_HEADINGS = new Set([
  'answer',
  'note',
  'notes',
  'summary',
  'why',
  "here's why",
  'heres why',
  'example',
  'examples',
  'result',
  'output',
  'warning',
  'tip',
  'explanation',
  'key takeaway',
  'takeaway',
  'meaning',
  'context',
  'context in codebase',
  'solution',
  'reference',
  'rule',
  'invariant',
])

const STOP_SUBJECT_WORDS = new Set([
  'it',
  'that',
  'code',
  'line',
  'lines',
  'method',
  'function',
  'following',
  'terms',
  'the',
  'a',
  'an',
  'these',
  'those',
  'here',
  'snippet',
  'expression',
])

/** Normalizes a term string for deduplication without collapsing distinct names */
export function canonicalTermKey(term: string): string {
  let t = (term || '').trim().toLowerCase()
  if (t.startsWith('.')) {
    t = t.slice(1)
  }
  t = t.replace(/\([^)]*\)$/, '')
  return t.trim()
}

/** Detects whether a lexicon term is a code identifier/syntax token whose casing should be preserved */
export function looksLikeCodeTerm(term: string): boolean {
  const t = (term || '').trim()
  if (!t) return false
  return /[()._$[\]<>]|^[a-z]+[A-Z]|^(this|let|const|var|return|for|while|if|else|switch|case|break|continue|class|interface|type|enum|async|await|import|export|def|self|lambda|yield|try|catch|throw|new|null|undefined|true|false)$/.test(
    t,
  )
}

/** Checks if a term already exists in a card's lexicon glosses using canonical normalization */
export function isTermInGlosses(
  glosses: LexiconGlossItem[] | null | undefined,
  term: string | null | undefined,
): boolean {
  const t = (term || '').trim().toLowerCase()
  if (!t || !glosses || glosses.length === 0) return false
  const canon = canonicalTermKey(t)
  return glosses.some((g) => {
    const gt = (g.term || '').trim().toLowerCase()
    return gt === t || (canon.length > 0 && canonicalTermKey(gt) === canon)
  })
}

/** Extracts structured term definitions from an Ask Local LLM Q&A exchange */
export function extractTermDefinitionsFromQA(params: {
  question: string
  answer: string
  selectedCode?: string | null
  docCitation?: string | null
  language?: string
}): LexiconGlossItem[] {
  const { question, answer, selectedCode, docCitation, language = 'typescript' } = params
  if (!answer || !answer.trim()) return []

  const nowIso = new Date().toISOString()
  const results: LexiconGlossItem[] = []
  const seenKeys = new Set<string>()
  const contextExplanation = docCitation ? `Cited: ${docCitation}` : undefined

  const patterns: RegExp[] = [
    /^\s*(?:[-*•+]|\d+[.)])\s+(?:\*{1,2})?`([^`\n]{1,64})`(?:\*{1,2})?\s*(?::|—|–|-\s+)\s*(.+)$/,
    /^\s*(?:[-*•+]|\d+[.)])\s+\*\*([^*\n:]{1,64})\*\*\s*(?::|—|–|-\s+)\s*(.+)$/,
    /^\s*(?:[-*•+]|\d+[.)])\s+([A-Za-z_$.][A-Za-z0-9_$.()<>\[\]]{0,48})\s*:\s+(.{8,})$/,
    /^\s*(?:\*{1,2})?`([^`\n]{1,48})`(?:\*{1,2})?\s*:\s+(.{10,})$/,
  ]

  for (const line of answer.split(/\r?\n/)) {
    for (const pat of patterns) {
      const m = line.match(pat)
      if (m) {
        const rawTerm = m[1].trim().replace(/:$/, '').trim()
        const rawDef = m[2].trim()
        if (!rawTerm || !rawDef) break
        if (META_DEFINITION_HEADINGS.has(rawTerm.toLowerCase())) break
        const key = canonicalTermKey(rawTerm)
        if (key && !seenKeys.has(key)) {
          seenKeys.add(key)
          results.push({
            term: rawTerm,
            definition: rawDef,
            domain: language || 'Code',
            context_explanation: contextExplanation,
            source: 'Ask Local LLM',
            pinned_at: nowIso,
          })
        }
        break
      }
    }
  }

  if (results.length > 0) return results

  // Fallback for single-term definitional questions answered in prose
  const qClean = (question || '').trim()
  const isDefinitionalQ = /\b(?:explain|define|what\s+(?:is|are|does|do)|meaning\s+of|purpose\s+of|role\s+of|how\s+does|why\s+(?:do\s+we\s+)?use|what\s+happens\s+if)\b/i.test(
    qClean,
  )
  if (!isDefinitionalQ) return []

  let candidateTerm: string | null = null
  const backticked = qClean.match(/`([^`\n]{1,48})`/)
  if (backticked) {
    candidateTerm = backticked[1].trim()
  } else {
    const trig = qClean.match(
      /(?:what\s+(?:is|are|does)|define|explain|meaning\s+of|purpose\s+of|role\s+of|(?:don'?t|do\s+not|not)?\s*use)\s+([.`'"]?[A-Za-z_$.][A-Za-z0-9_$.()]{0,40}[`'"]?)/i,
    )
    if (trig) {
      const word = trig[1].replace(/^[`'"]+|[`'"?.!,]+$/g, '')
      if (!STOP_SUBJECT_WORDS.has(word.toLowerCase())) {
        candidateTerm = word
      }
    }
  }

  if (!candidateTerm && selectedCode) {
    const sel = selectedCode.trim()
    if (/^\.?[A-Za-z_$][A-Za-z0-9_$.()]{0,40}$/.test(sel)) {
      candidateTerm = sel
    }
  }

  if (candidateTerm) {
    let cleanAns = answer.trim().replace(/\s+/g, ' ')
    if (cleanAns.length > 420) {
      cleanAns = cleanAns.slice(0, 417).replace(/\s+\S*$/, '') + '...'
    }
    results.push({
      term: candidateTerm,
      definition: cleanAns,
      domain: language || 'Code',
      context_explanation: contextExplanation,
      source: 'Ask Local LLM',
      pinned_at: nowIso,
    })
  }

  return results
}
