import type { CardRecord, CardReference, DeckRecord, LexiconGlossItem } from './types.ts'
import type {
  ParsedCardGuide,
  ParsedChapter,
  ParsedCourseGuide,
  ParsedDocLink,
  ParsedReadingBlock,
  ParsedTerm,
} from './socraticGuideParser.ts'

export interface SocraticLessonData {
  source_guide: string
  chapter_number: number | null
  chapter_title: string | null
  deck_name: string | null
  card_kind: string | null
  card_slug: string | null
  core_idea: string | null
  rule: string | null
  readings: ParsedReadingBlock[]
  terms: ParsedTerm[]
  invariants: string | null
  types: string | null
  memory_model: string | null
  trap: string | null
  failure_mode: string | null
  think_it_through: string | null
  doc_links: ParsedDocLink[]
}

export interface LessonResponse {
  available: boolean
  reason: string | null
  body: string
  key_points: string[]
  generated: boolean
  model_used: string | null
  cached: boolean
  citations: CardReference[]
  socratic?: SocraticLessonData | null
}

export interface SocraticGuideResponse {
  message: string
  on_track: boolean
  degraded: boolean
  degraded_reason: string | null
  model_used: string | null
}

function normalizeKey(text: string): string {
  return text
    .toLowerCase()
    .replace(/[`*_~]/g, '')
    .replace(/\s+/g, ' ')
    .trim()
}

function tokenizeConcepts(text: string): Set<string> {
  const stop = new Set([
    'the', 'and', 'for', 'with', 'that', 'this', 'from', 'into', 'when', 'what', 'which',
    'your', 'have', 'does', 'will', 'then', 'only', 'each', 'make', 'sure', 'about', 'there',
    'their', 'been', 'being', 'more', 'most', 'some', 'than', 'also', 'just', 'like', 'they',
  ])
  const tokens = text
    .toLowerCase()
    .replace(/[^a-z0-9_$.]+/g, ' ')
    .split(/\s+/)
    .filter((w) => w.length >= 3 && !stop.has(w))
  return new Set(tokens)
}

/** Find the matching ParsedCardGuide for any CardRecord (by tag, slug, normalized title, or code snippet). */
export function matchCardToGuide(
  card: Pick<CardRecord, 'title' | 'front' | 'tags' | 'starter_code'>,
  course: ParsedCourseGuide,
  deckName?: string | null,
): ParsedCardGuide | null {
  if (!course.cards.length) return null

  const tags = (card.tags || []).map((t) => t.toLowerCase())

  // 1. Direct tag match: guide:<id> or slug:<slug> or raw slug
  for (const t of tags) {
    if (t.startsWith('guide:')) {
      const id = t.slice('guide:'.length)
      const hit = course.cards.find((c) => c.id.toLowerCase() === id || c.slug.toLowerCase() === id)
      if (hit) return hit
    }
    const slugHit = course.cards.find((c) => c.slug.toLowerCase() === t)
    if (slugHit) return slugHit
  }

  // 2. Exact normalized title match (excluding generic titles like "What does this print?")
  const normTitle = normalizeKey(card.title || '')
  if (normTitle && !normTitle.startsWith('what does this print') && !normTitle.startsWith('does this compile')) {
    const titleHit = course.cards.find((c) => normalizeKey(c.title) === normTitle)
    if (titleHit) return titleHit
  }

  // 3. Slug mentioned inside front or title (e.g. "(js01-typeof)")
  const frontNorm = normalizeKey(card.front || '')
  for (const g of course.cards) {
    if (/^(js|ts)\d+-/.test(g.slug) && (frontNorm.includes(g.slug) || normTitle.includes(g.slug))) {
      return g
    }
  }

  // 4. Function/code signature or snippet match
  const starterNorm = normalizeKey(card.starter_code || '')
  for (const g of course.cards) {
    if (g.snippetCode && frontNorm.includes(normalizeKey(g.snippetCode.slice(0, 60)))) {
      return g
    }
    if (starterNorm && g.starterCode && starterNorm.slice(0, 48) === normalizeKey(g.starterCode).slice(0, 48)) {
      if (!deckName || normalizeKey(deckName) === normalizeKey(g.deckName)) {
        return g
      }
    }
  }

  // 5. Exact prompt match
  if (frontNorm.length >= 24) {
    const promptHit = course.cards.find((g) => {
      const gp = normalizeKey(g.prompt)
      return gp.length >= 24 && (frontNorm.includes(gp.slice(0, 60)) || gp.includes(frontNorm.slice(0, 60)))
    })
    if (promptHit) return promptHit
  }

  return null
}

function buildThinkItThrough(guide: ParsedCardGuide, chapter: ParsedChapter | undefined): string {
  if (chapter?.ponder) {
    return chapter.ponder
  }
  if (guide.failure && guide.invariants) {
    return `Before answering, check this invariant: ${guide.invariants} Why would a naive approach fail here (${guide.failure.replace(/\.$/, '')})?`
  }
  if (guide.trap) {
    return `Keep this pitfall in mind: ${guide.trap} How does it change your approach on the boundary inputs?`
  }
  return 'Trace the types and values step by step before committing your answer.'
}

function buildNonSpoilingKeyPoints(guide: ParsedCardGuide, chapter: ParsedChapter | undefined): string[] {
  const points: string[] = []
  if (guide.trap) points.push(`Trap to avoid: ${guide.trap}`)
  if (guide.invariants) points.push(`Invariant: ${guide.invariants}`)
  if (guide.types) points.push(`Types: ${guide.types}`)
  if (chapter?.rule && points.length < 4) points.push(`Rule of thumb: ${chapter.rule}`)
  return points.slice(0, 4)
}

function buildNonSpoilingMarkdownBody(
  guide: ParsedCardGuide,
  chapter: ParsedChapter | undefined,
): string {
  const blocks: string[] = []

  const coreIdea = guide.readings[0]?.coreIdea || chapter?.coreIdea
  if (coreIdea) {
    blocks.push(`**Core idea:** ${coreIdea}`)
  }

  for (const reading of guide.readings) {
    for (const sec of reading.sections) {
      if (sec.question) {
        blocks.push(`### ${sec.question}\n\n${sec.body}`)
      } else if (sec.body) {
        blocks.push(sec.body)
      }
    }
  }

  if (blocks.length === 0 && chapter?.coreIdea) {
    blocks.push(chapter.coreIdea)
  }

  return blocks.join('\n\n')
}

/** Build a grounded, non-spoiling Socratic lesson for any card. */
export function buildSocraticLesson(
  card: CardRecord,
  deck: DeckRecord | undefined,
  course: ParsedCourseGuide,
): LessonResponse {
  const guide = matchCardToGuide(card, course, deck?.name)

  if (guide) {
    const primaryChapterNum = guide.chapterNumbers[0] ?? null
    const chapter = primaryChapterNum !== null ? course.chaptersByNumber.get(primaryChapterNum) : undefined
    const primaryReading = guide.readings[0]
    const coreIdea = primaryReading?.coreIdea || chapter?.coreIdea || course.decksByName.get(guide.deckName)?.coreIdea || null
    const chapterTitle = primaryReading?.chapterTitle || chapter?.title || guide.deckName
    const thinkItThrough = buildThinkItThrough(guide, chapter)
    const keyPoints = buildNonSpoilingKeyPoints(guide, chapter)
    const body = buildNonSpoilingMarkdownBody(guide, chapter)

    const citations: CardReference[] = []
    if (primaryChapterNum !== null) {
      citations.push({
        quote: coreIdea || chapterTitle,
        quote_verified: true,
        locator: `Ch. ${primaryChapterNum} · ${guide.deckName}`,
        source_title: `${guide.partTitle} (Socratic Study Guide)`,
        extract_id: null,
        passage: body,
      })
    }
    for (const dl of guide.docLinks) {
      citations.push({
        quote: dl.label,
        quote_verified: true,
        locator: dl.url,
        source_title: dl.label,
        extract_id: null,
        passage: null,
      })
    }

    const socratic: SocraticLessonData = {
      source_guide: `${guide.partTitle} · Study Guide`,
      chapter_number: primaryChapterNum,
      chapter_title: chapterTitle,
      deck_name: guide.deckName,
      card_kind: guide.kind,
      card_slug: guide.slug,
      core_idea: coreIdea,
      rule: chapter?.rule ?? null,
      readings: guide.readings,
      terms: guide.terms,
      invariants: guide.invariants,
      types: guide.types,
      memory_model: guide.memory,
      trap: guide.trap,
      failure_mode: guide.failure,
      think_it_through: thinkItThrough,
      doc_links: guide.docLinks,
    }

    return {
      available: true,
      reason: null,
      body,
      key_points: keyPoints,
      generated: true,
      model_used: 'socratic-study-guide',
      cached: true,
      citations,
      socratic,
    }
  }

  // Fallback for non-JS/TS cards: NEVER dump card.back verbatim as a spoiler!
  // Ground in verified source citations or deck/card documentation instead.
  if (card.references.length > 0) {
    const readingSections = card.references.map((ref) => ({
      question: ref.locator || ref.source_title || 'From the source reading',
      body: ref.passage || ref.quote,
    }))
    const body = card.references.map((r) => r.passage || r.quote).join('\n\n')
    const keyPoints: string[] = []
    if (deck?.documentation) keyPoints.push(deck.documentation)
    if (card.edge_cases.length > 0) {
      keyPoints.push(`Watch boundaries: ${card.edge_cases.join('; ')}`)
    }
    if (keyPoints.length === 0) {
      keyPoints.push('Connect the cited principle back to the exact mechanism asked by the prompt.')
    }

    return {
      available: true,
      reason: null,
      body,
      key_points: keyPoints,
      generated: false,
      model_used: 'source-citation',
      cached: true,
      citations: card.references,
      socratic: {
        source_guide: card.references[0]?.source_title || deck?.name || 'Source Reading',
        chapter_number: null,
        chapter_title: deck?.name || 'Source Context',
        deck_name: deck?.name ?? null,
        card_kind: card.template_kind,
        card_slug: null,
        core_idea: deck?.documentation ?? null,
        rule: null,
        readings: [
          {
            chapterTitle: card.references[0]?.source_title || 'Reference Reading',
            coreIdea: deck?.documentation || '',
            sections: readingSections,
          },
        ],
        terms: [],
        invariants: null,
        types: null,
        memory_model: null,
        trap: null,
        failure_mode: card.active_weaknesses[0] ?? null,
        think_it_through:
          'Before revealing the answer, explain the underlying mechanism in your own words using the passage above.',
        doc_links: [],
      },
    }
  }

  // No references attached: build a non-spoiling conceptual framing from deck/card metadata & edge cases
  const docContext = card.documentation || deck?.documentation || null
  const keyPoints: string[] = []
  if (card.time_complexity || card.space_complexity) {
    const parts = [
      card.time_complexity ? `Target time: ${card.time_complexity}` : null,
      card.space_complexity ? `Target space: ${card.space_complexity}` : null,
    ].filter(Boolean)
    keyPoints.push(parts.join(' · '))
  }
  for (const ec of card.edge_cases.slice(0, 3)) {
    keyPoints.push(`Edge case: ${ec}`)
  }
  if (card.active_weaknesses.length > 0) {
    keyPoints.push(`Past blind spot to watch: ${card.active_weaknesses[0]}`)
  }
  if (keyPoints.length === 0) {
    keyPoints.push('State the core invariant first, then verify how it behaves on boundary cases.')
  }

  const framingBody = docContext
    ? `${docContext}\n\nBefore answering, identify the core invariant and trace at least one boundary case.`
    : `Focus on the core invariant behind this ${deck?.name || 'topic'} question and trace a concrete example before committing your answer.`

  return {
    available: true,
    reason: null,
    body: framingBody,
    key_points: keyPoints,
    generated: false,
    model_used: 'conceptual-framing',
    cached: true,
    citations: [],
    socratic: {
      source_guide: deck?.name || 'Study Context',
      chapter_number: null,
      chapter_title: deck?.name || card.category || 'Mental Model',
      deck_name: deck?.name ?? null,
      card_kind: card.template_kind,
      card_slug: null,
      core_idea: docContext,
      rule: null,
      readings: [],
      terms: [],
      invariants:
        card.time_complexity || card.space_complexity
          ? `Aim for ${[card.time_complexity && `${card.time_complexity} time`, card.space_complexity && `${card.space_complexity} space`].filter(Boolean).join(', ')}.`
          : null,
      types: null,
      memory_model: null,
      trap: card.edge_cases.length > 0 ? `Watch boundary cases: ${card.edge_cases.join('; ')}.` : null,
      failure_mode: card.active_weaknesses[0] ?? null,
      think_it_through:
        'What invariant guarantees your answer holds for every valid input — including empty or boundary cases?',
      doc_links: [],
    },
  }
}

/** Build a progressive, card-grounded Socratic coaching reply for "Stuck? Ask your Guide". */
export function buildSocraticGuideReply(
  card: CardRecord,
  deck: DeckRecord | undefined,
  course: ParsedCourseGuide,
  studentMessage: string,
  history: Array<{ role?: string; text?: string }>,
): SocraticGuideResponse {
  const guide = matchCardToGuide(card, course, deck?.name)
  const guideTurns = history.filter((h) => h.role === 'guide').length

  if (guide) {
    const primaryChapter = guide.chapterNumbers[0]
      ? course.chaptersByNumber.get(guide.chapterNumbers[0])
      : undefined

    // Assess whether student's message already touches key concepts from solve/invariants/trap
    const studentTokens = tokenizeConcepts(studentMessage)
    const targetTokens = tokenizeConcepts(
      [guide.invariants, guide.trap, guide.solve, guide.types].filter(Boolean).join(' '),
    )
    let overlap = 0
    for (const tok of studentTokens) {
      if (targetTokens.has(tok)) overlap++
    }
    const onTrack = overlap >= 2 || (studentMessage.trim().length >= 20 && overlap >= 1)

    let message = ''
    if (guideTurns === 0) {
      const parts: string[] = []
      if (onTrack) {
        parts.push("You're on the right track.")
      }
      if (guide.invariants) {
        parts.push(`Start from the core invariant: ${guide.invariants}`)
      }
      if (guide.trap) {
        parts.push(`Watch out for this trap: ${guide.trap}`)
      }
      if (primaryChapter?.rule) {
        parts.push(`Keep in mind: "${primaryChapter.rule}"`)
      }
      parts.push('How does that constrain what you return or predict?')
      message = parts.join(' ')
    } else if (guideTurns === 1) {
      const parts: string[] = []
      if (guide.failure) {
        parts.push(`Common failure mode here: ${guide.failure}`)
      }
      if (guide.types) {
        parts.push(`Check the types carefully (${guide.types}).`)
      }
      if (guide.memory) {
        parts.push(`Memory picture: ${guide.memory}`)
      }
      parts.push('Walk through one tricky input line by line — what value do you get?')
      message = parts.join(' ')
    } else {
      const parts: string[] = []
      if (guide.solve) {
        parts.push(`Strategy: ${guide.solve}`)
      }
      if (guide.tests) {
        parts.push(`Verify your mental trace against these cases: ${guide.tests}`)
      }
      if (parts.length === 0) {
        parts.push(guide.why || 'Trace each branch on the boundary cases and check what comes out.')
      }
      message = parts.join(' ')
    }

    return {
      message,
      on_track: onTrack,
      degraded: false,
      degraded_reason: null,
      model_used: 'socratic-study-guide',
    }
  }

  // Non-guide card fallback
  const parts: string[] = []
  if (guideTurns === 0 && card.active_weaknesses.length > 0) {
    parts.push(`Watch a past blind spot on this card: ${card.active_weaknesses[0]}`)
  } else if (guideTurns === 0 && card.edge_cases.length > 0) {
    parts.push(`Consider these boundary cases first: ${card.edge_cases.join('; ')}.`)
  } else if (card.references.length > 0) {
    const ref = card.references[0]
    parts.push(`Re-anchor on ${ref.locator || ref.source_title || 'the source reading'}: what exact mechanism does it establish?`)
  } else if (deck?.documentation) {
    parts.push(`Tie your answer back to the core theme of ${deck.name}: ${deck.documentation}`)
  } else {
    parts.push('Break the question into the core invariant first, then verify one concrete edge case.')
  }

  return {
    message: parts.join(' '),
    on_track: studentMessage.trim().length > 15,
    degraded: false,
    degraded_reason: null,
    model_used: 'socratic-study-guide',
  }
}

/** Build seeded card payload fields from a ParsedCardGuide so every course card is rich and self-contained. */
export function buildSeedCardFields(
  guide: ParsedCardGuide,
  chapter: ParsedChapter | undefined,
): {
  title: string
  front: string
  back: string
  template_kind: 'code' | 'basic'
  grading_profile: 'code' | 'conceptual'
  starter_code: string | null
  edge_cases: string[]
  difficulty_label: string | null
  category: string
  tags: string[]
  documentation: string | null
  thematic_nature: string
  references: CardReference[]
  lexicon_glosses: LexiconGlossItem[]
} {
  const isExecutableCodeCard = guide.kind === 'write' || guide.kind === 'fix' || guide.kind === 'types'
  const langFence = guide.language === 'typescript' ? 'ts' : 'js'

  // Build front: prompt + snippet code (for predict/compile cards where code is part of the question)
  let front = guide.prompt
  if (!isExecutableCodeCard && guide.snippetCode) {
    front = `${guide.prompt}\n\n\`\`\`${langFence}\n${guide.snippetCode}\n\`\`\``
  }

  // Build back: verified solution code or output + Why explanation
  let back = ''
  if (guide.solutionCode) {
    back = `\`\`\`${langFence}\n${guide.solutionCode}\n\`\`\``
    if (guide.why) {
      back += `\n\n**Why:** ${guide.why}`
    }
  } else if (guide.solutionOutput) {
    back = `\`\`\`text\n${guide.solutionOutput}\n\`\`\``
    if (guide.why) {
      back += `\n\n**Why:** ${guide.why}`
    }
  } else if (guide.why) {
    back = guide.why
  }

  const edgeCases: string[] = []
  if (guide.trap) edgeCases.push(guide.trap)
  if (guide.tests) edgeCases.push(`Check cases: ${guide.tests}`)

  const primaryChapterNum = guide.chapterNumbers[0]
  const references: CardReference[] = []
  if (guide.readings.length > 0) {
    const r = guide.readings[0]
    references.push({
      quote: r.coreIdea || chapter?.coreIdea || guide.deckName,
      quote_verified: true,
      locator: primaryChapterNum ? `Ch. ${primaryChapterNum} · ${guide.deckName}` : guide.deckName,
      source_title: `${guide.partTitle} (Socratic Study Guide)`,
      extract_id: null,
      passage: r.sections.map((s) => `${s.question}\n${s.body}`).join('\n\n'),
    })
  }

  const lexicon_glosses: LexiconGlossItem[] = guide.terms.map((t) => ({
    term: t.term,
    source: 'Socratic Study Guide',
    definition: t.definition,
    domain: guide.language === 'typescript' ? 'TypeScript' : 'JavaScript',
  }))

  const docLines: string[] = []
  if (guide.docLinks.length > 0) {
    docLines.push(
      `Documentation: ${guide.docLinks.map((d) => `[${d.label}](${d.url})`).join(' · ')}`,
    )
  }
  if (chapter?.rule) {
    docLines.push(`Rule: ${chapter.rule}`)
  }

  const displayTitle =
    guide.kind === 'predict' || guide.kind === 'compile'
      ? `${guide.title} (${guide.slug})`
      : guide.title

  return {
    title: displayTitle,
    front,
    back,
    template_kind: isExecutableCodeCard ? 'code' : 'basic',
    grading_profile: isExecutableCodeCard ? 'code' : 'conceptual',
    starter_code: isExecutableCodeCard ? guide.starterCode : null,
    edge_cases: edgeCases,
    difficulty_label: guide.difficulty,
    category: guide.deckName,
    tags: [
      `guide:${guide.id}`,
      guide.slug,
      guide.language,
      guide.kind,
      `part-${guide.partNumber}`,
    ],
    documentation: docLines.length > 0 ? docLines.join('\n') : null,
    thematic_nature: `${guide.partTitle} / ${guide.deckName}`,
    references,
    lexicon_glosses,
  }
}
