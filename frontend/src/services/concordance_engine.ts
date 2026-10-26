/**
 * Exhaustive MIT 6.0001 Computational Thinking & Computer Science Lexicon.
 * Grounded in MIT 6.0001 (Introduction to Computer Science and Programming in Python)
 * by Profs. John V. Guttag, Eric Grimson, and Dr. Ana Bell.
 *
 * Entries are served as an on-demand static JSON asset from /data/guttag_lexicon.json
 * to keep the bundle lean while retaining full client-side concordance matching.
 */

export interface ConcordanceOccurrence {
  chapter: string
  section: string
  pageRange?: string
  contextSnippet: string
}

export type ConcordanceCategory =
  | 'Core Language & Primitives'
  | 'Control Flow & Iteration'
  | 'Memory, State & Runtime'
  | 'Functions & Abstractions'
  | 'Object-Oriented Design'
  | 'Data Structures & ADTs'
  | 'Strings & Text Processing'
  | 'Searching & Sorting'
  | 'Algorithmic Paradigms'
  | 'Graphs & Networks'
  | 'Complexity & Mathematics'
  | 'Bitwise & Binary Arithmetic'
  | 'Verification & Testing'
  | 'Exceptions & Error Handling'
  | 'Modules, Files & I/O'
  | 'Randomness & Simulation'
  | 'Statistics & Data Analysis'
  | 'Machine Learning & Clustering'

export interface ConcordanceEntry {
  id: string // e.g. "G-101"
  term: string
  category: ConcordanceCategory
  /** Surface forms matched in reading text. Always shaped `/\b(alt|alt)\b/gi`. */
  patterns: RegExp
  definition: string
  primaryLocation: string
  occurrences: ConcordanceOccurrence[]
  leetCodeRelevance: string
  /** Formal notation, signature, invariant, or complexity bound. */
  notation?: string
  /** Ids of sibling entries a reader should jump to next. */
  relatedIds?: string[]
}

export const CONCORDANCE_CATEGORIES: ConcordanceCategory[] = [
  'Core Language & Primitives',
  'Control Flow & Iteration',
  'Memory, State & Runtime',
  'Functions & Abstractions',
  'Object-Oriented Design',
  'Data Structures & ADTs',
  'Strings & Text Processing',
  'Searching & Sorting',
  'Algorithmic Paradigms',
  'Graphs & Networks',
  'Complexity & Mathematics',
  'Bitwise & Binary Arithmetic',
  'Verification & Testing',
  'Exceptions & Error Handling',
  'Modules, Files & I/O',
  'Randomness & Simulation',
  'Statistics & Data Analysis',
  'Machine Learning & Clustering',
]

export const GUTTAG_CONCORDANCE_LEXICON: ConcordanceEntry[] = []

interface CompiledEntry {
  entry: ConcordanceEntry
  /** Anchored clone used to resolve a matched span back to exactly one entry. */
  anchored: RegExp
  /** Longest literal alternative length — higher wins ties. */
  specificity: number
}

let COMPILED: CompiledEntry[] = []
const RESOLUTION_CACHE = new Map<string, ConcordanceEntry | null>()

const WORD_CHAR = /[A-Za-z0-9_]/

/** Does this alternative begin with something a `\b` can anchor against? */
function startsWithWordChar(alt: string): boolean {
  let i = 0
  while (i < alt.length) {
    const ch = alt[i]
    if (ch === '(') {
      i++
      if (alt.slice(i, i + 2) === '?:') i += 2
      continue
    }
    if (ch === '\\') return WORD_CHAR.test(alt[i + 1] ?? '')
    if (ch === '[') return false
    return WORD_CHAR.test(ch)
  }
  return false
}

/** Does this alternative end with something a `\b` can anchor against? */
function endsWithWordChar(alt: string): boolean {
  let i = alt.length - 1
  while (i >= 0) {
    const ch = alt[i]
    if (ch === '?' || ch === '*' || ch === '+') {
      i--
      continue
    }
    if (ch === ')') {
      if (i > 0 && alt[i - 1] === '\\') return false // literal ')'
      i--
      continue
    }
    if (ch === ']') return false
    if (i > 0 && alt[i - 1] === '\\') return WORD_CHAR.test(ch)
    return WORD_CHAR.test(ch)
  }
  return false
}

/**
 * Splits `/\b(alt1|alt2)\b/` into its top-level alternatives, respecting nesting
 * so that groups like `(y|ies)` are not split apart.
 */
function extractAlternatives(pattern: RegExp): string[] {
  let src = pattern.source
  src = src.replace(/^\\b/, '').replace(/\\b$/, '')
  if (src.startsWith('(') && src.endsWith(')')) {
    src = src.slice(1, -1)
  }

  const alts: string[] = []
  let depth = 0
  let current = ''
  for (let i = 0; i < src.length; i++) {
    const ch = src[i]
    if (ch === '\\') {
      current += ch + (src[i + 1] ?? '')
      i++
      continue
    }
    if (ch === '[') depth++
    else if (ch === ']') depth--
    else if (ch === '(') depth++
    else if (ch === ')') depth--

    if (ch === '|' && depth === 0) {
      alts.push(current)
      current = ''
      continue
    }
    current += ch
  }
  if (current) alts.push(current)
  return alts.filter(Boolean)
}

function compileMasterRegex(entries: ConcordanceEntry[]): RegExp {
  if (entries.length === 0) return /(?!)/
  const alts = entries.flatMap((e) => extractAlternatives(e.patterns))
  const unique = Array.from(new Set(alts))
  unique.sort((a, b) => b.replace(/\\/g, '').length - a.replace(/\\/g, '').length)
  const bounded = unique.map((alt) => {
    const lb = startsWithWordChar(alt) ? '\\b' : ''
    const rb = endsWithWordChar(alt) ? '\\b' : ''
    return `${lb}(?:${alt})${rb}`
  })
  return new RegExp(`(?:${bounded.join('|')})`, 'gi')
}

export let CONCORDANCE_MASTER_REGEX: RegExp = /(?!)/

export function getConcordanceMasterRegex(): RegExp {
  return CONCORDANCE_MASTER_REGEX
}

let loadPromise: Promise<ConcordanceEntry[]> | null = null

export function isConcordanceLoaded(): boolean {
  return GUTTAG_CONCORDANCE_LEXICON.length > 0
}

export async function loadConcordanceLexicon(): Promise<ConcordanceEntry[]> {
  if (GUTTAG_CONCORDANCE_LEXICON.length > 0) {
    return GUTTAG_CONCORDANCE_LEXICON
  }
  if (loadPromise) {
    return loadPromise
  }

  loadPromise = (async () => {
    try {
      const res = await fetch('/data/guttag_lexicon.json')
      if (!res.ok) {
        throw new Error(`Failed to load lexicon: HTTP ${res.status}`)
      }
      const rawData = (await res.json()) as Array<
        Omit<ConcordanceEntry, 'patterns'> & { patterns: string }
      >
      const hydrated: ConcordanceEntry[] = rawData.map((e) => ({
        ...e,
        patterns: new RegExp(e.patterns, 'gi'),
      }))

      GUTTAG_CONCORDANCE_LEXICON.length = 0
      GUTTAG_CONCORDANCE_LEXICON.push(...hydrated)

      COMPILED = GUTTAG_CONCORDANCE_LEXICON.map((entry) => {
        const alts = extractAlternatives(entry.patterns)
        const specificity = alts.reduce(
          (max, a) => Math.max(max, a.replace(/\\/g, '').length),
          0
        )
        return {
          entry,
          anchored: new RegExp(`^(?:${alts.join('|')})$`, 'i'),
          specificity,
        }
      }).sort((a, b) => b.specificity - a.specificity)

      CONCORDANCE_MASTER_REGEX = compileMasterRegex(GUTTAG_CONCORDANCE_LEXICON)
      RESOLUTION_CACHE.clear()

      return GUTTAG_CONCORDANCE_LEXICON
    } catch (err) {
      console.warn('Concordance lexicon fetch failed:', err)
      loadPromise = null
      return []
    }
  })()

  return loadPromise
}

export const ensureConcordanceLoaded = loadConcordanceLexicon

// Automatically start background loading if running in browser
if (typeof window !== 'undefined') {
  void loadConcordanceLexicon()
}

/**
 * Resolves a matched span to the single most specific concordance entry.
 * Anchored matching prevents a generic entry ("type") from claiming a span that
 * belongs to a specific one ("abstract data type").
 */
export function resolveConcordanceEntry(matchedText: string): ConcordanceEntry | null {
  const key = matchedText.trim().toLowerCase()
  if (!key) return null

  const cached = RESOLUTION_CACHE.get(key)
  if (cached !== undefined) return cached

  let found: ConcordanceEntry | null = null
  for (const compiled of COMPILED) {
    if (compiled.anchored.test(key)) {
      found = compiled.entry
      break
    }
  }

  RESOLUTION_CACHE.set(key, found)
  return found
}

/** Look up an entry by its concordance id (e.g. "G-217"). */
export function getConcordanceEntryById(id: string): ConcordanceEntry | null {
  return GUTTAG_CONCORDANCE_LEXICON.find((e) => e.id === id) ?? null
}

/**
 * Finds a matching ConcordanceEntry for a given text token.
 * Retained for backwards compatibility; delegates to the specificity-ranked resolver.
 */
export function findConcordanceMatch(text: string): ConcordanceEntry | null {
  const trimmed = text.trim()
  if (!trimmed) return null

  const exact = resolveConcordanceEntry(trimmed)
  if (exact) return exact

  // Fall back to a containment scan for free-form phrases.
  for (const compiled of COMPILED) {
    compiled.entry.patterns.lastIndex = 0
    if (compiled.entry.patterns.test(trimmed)) return compiled.entry
  }
  return null
}

/** Free-text search across term, definition, id, notation, and transfer notes. */
export function searchConcordance(
  query: string,
  category: ConcordanceCategory | 'All' = 'All'
): ConcordanceEntry[] {
  const q = query.trim().toLowerCase()
  return GUTTAG_CONCORDANCE_LEXICON.filter((e) => {
    if (category !== 'All' && e.category !== category) return false
    if (!q) return true
    return (
      e.term.toLowerCase().includes(q) ||
      e.definition.toLowerCase().includes(q) ||
      e.id.toLowerCase().includes(q) ||
      e.category.toLowerCase().includes(q) ||
      (e.notation?.toLowerCase().includes(q) ?? false) ||
      e.leetCodeRelevance.toLowerCase().includes(q) ||
      e.primaryLocation.toLowerCase().includes(q)
    )
  })
}
