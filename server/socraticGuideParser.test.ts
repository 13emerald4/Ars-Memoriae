import test from 'node:test'
import assert from 'node:assert/strict'
import { loadAllSocraticGuides, latexToMarkdown } from './socraticGuideParser.ts'
import {
  buildSeedCardFields,
  buildSocraticGuideReply,
  buildSocraticLesson,
  matchCardToGuide,
} from './socraticLessonService.ts'
import type { CardRecord, DeckRecord } from './types.ts'

const RAW_LATEX_LEAK_RE =
  /\\(code|textbf|textit|emph|textquotedbl|textquotesingle|textless|textgreater|textbackslash|item|begin|end|par|Needspace|hyperref|href|safemargin|readq|readchap|cardhead|cardsub|deckhead|trap|mantra|term|textcolor|enspace|smallskip|medskip|bigskip|noindent)\b/

function makeDummyCard(overrides: Partial<CardRecord>): CardRecord {
  return {
    id: 'card-test',
    user_id: 'user-1',
    note_id: 'note-1',
    deck_id: 'deck-1',
    template_slot: 'front_back',
    template_kind: 'code',
    grading_profile: 'code',
    state: 'new',
    due: null,
    stability: null,
    difficulty: null,
    priority: 80,
    lapse_count: 0,
    leech_flag: false,
    suspended: false,
    tags: [],
    front: '',
    back: '',
    image: null,
    back_image: null,
    occlusion: null,
    references: [],
    starter_code: null,
    starter_tests: null,
    test_cases: [],
    time_complexity: null,
    space_complexity: null,
    edge_cases: [],
    title: null,
    difficulty_label: null,
    category: null,
    documentation: null,
    thematic_nature: null,
    source_documents: [],
    lexicon_glosses: [],
    position: 0,
    memory_note: null,
    active_weaknesses: [],
    weakness_history: [],
    failure_reminder: null,
    last_grade: null,
    review_count: 0,
    is_schema_checkpoint: false,
    spatial_x: null,
    spatial_y: null,
    spatial_locus: null,
    mnemonic_vignette: null,
    created_at: new Date().toISOString(),
    ...overrides,
  }
}

test('latexToMarkdown converts macros, code blocks, quotes, and symbols cleanly', () => {
  const input = String.raw`Use \code{Number(\textquotedbl{}\textquotedbl{})} $\rightarrow$ \code{0}, and \textbf{never} trust \emph{coercion}.{\small\textit{Prints:}~\code{42 NaN 0}\enspace\textcolor{black!45}{|}\enspace \code{12 false}}\par\begin{lstlisting}[language=JavaScript]
console.log(Number("42"));
\end{lstlisting}`
  const md = latexToMarkdown(input)
  assert.ok(md.includes('`Number("")`'), `expected inline code, got: ${md}`)
  assert.ok(md.includes('→'), `expected arrow symbol, got: ${md}`)
  assert.ok(md.includes('**never**'), `expected bold, got: ${md}`)
  assert.ok(md.includes('*coercion*'), `expected emphasis, got: ${md}`)
  assert.ok(md.includes('```javascript\nconsole.log(Number("42"));\n```'), `expected fenced JS block, got: ${md}`)
  assert.equal(RAW_LATEX_LEAK_RE.test(md), false, `raw LaTeX leaked into: ${md}`)
})

test('parses all 4 study guide TeX files into 105 cards, 27 chapters, and 27 decks', () => {
  const course = loadAllSocraticGuides()
  assert.equal(course.parts.length, 4)
  assert.equal(course.parts[0].cards.length, 64)
  assert.equal(course.parts[1].cards.length, 19)
  assert.equal(course.parts[2].cards.length, 17)
  assert.equal(course.parts[3].cards.length, 5)
  assert.equal(course.cards.length, 105)
  assert.equal(course.chaptersByNumber.size, 27)
  assert.equal(course.decksByName.size, 27)
})

test('zero raw LaTeX macros leak into any parsed field across all 105 cards and 27 chapters', () => {
  const course = loadAllSocraticGuides()

  for (const ch of course.chaptersByNumber.values()) {
    for (const field of [ch.title, ch.coreIdea, ch.rule || '', ch.ponder || '']) {
      assert.equal(
        RAW_LATEX_LEAK_RE.test(field),
        false,
        `Raw LaTeX leaked in Chapter ${ch.chapterNumber}: ${field.slice(0, 200)}`,
      )
    }
  }

  for (const card of course.cards) {
    const fieldsToCheck: Array<[string, string]> = [
      ['title', card.title],
      ['deckName', card.deckName],
      ['prompt', card.prompt],
      ['solve', card.solve || ''],
      ['invariants', card.invariants || ''],
      ['memory', card.memory || ''],
      ['types', card.types || ''],
      ['failure', card.failure || ''],
      ['tests', card.tests || ''],
      ['trap', card.trap || ''],
      ['why', card.why || ''],
      ...card.terms.flatMap((t, i): Array<[string, string]> => [
        [`term[${i}].term`, t.term],
        [`term[${i}].definition`, t.definition],
      ]),
      ...card.readings.flatMap((r, ri): Array<[string, string]> => [
        [`reading[${ri}].chapterTitle`, r.chapterTitle],
        [`reading[${ri}].coreIdea`, r.coreIdea],
        ...r.sections.flatMap((s, si): Array<[string, string]> => [
          [`reading[${ri}].sec[${si}].q`, s.question],
          [`reading[${ri}].sec[${si}].body`, s.body],
        ]),
      ]),
    ]

    for (const [label, val] of fieldsToCheck) {
      // Strip fenced code blocks before checking for LaTeX macros (JS/TS code can legitimately contain \n or regexes)
      const withoutCode = val.replace(/```[\s\S]*?```/g, '')
      assert.equal(
        RAW_LATEX_LEAK_RE.test(withoutCode),
        false,
        `Raw LaTeX leaked in ${card.id} (${label}): ${withoutCode.slice(0, 240)}`,
      )
    }

    assert.ok(card.prompt.length > 5, `${card.id} missing prompt`)
    assert.ok(card.readings.length >= 1, `${card.id} missing From the readings section`)
    assert.ok(card.readings[0].sections.length >= 1, `${card.id} missing reading Q&A section`)
  }
})

test('parseCount(text) builds a non-spoiling Socratic lesson grounded in Ch. 1 readings', () => {
  const course = loadAllSocraticGuides()
  const guide = course.cards.find((c) => c.title === 'parseCount(text)')
  assert.ok(guide, 'Expected parseCount(text) card in parsed course')
  assert.equal(guide.deckName, '01 · Values, Variables & Types')
  assert.equal(guide.kind, 'write')
  assert.equal(guide.language, 'javascript')
  assert.equal(guide.difficulty, 'Easy')
  // Prompt must not duplicate title heading
  assert.equal(guide.prompt.startsWith('**parseCount(text)**'), false)
  assert.equal(guide.prompt.startsWith('parseCount(text)\n'), false)
  assert.ok(guide.starterCode?.includes('parseInt(text, 10)'))
  assert.ok(guide.solutionCode?.includes('text.trim() === ""'))
  assert.ok(guide.trap?.includes('`Number("")`'))

  const chapter = course.chaptersByNumber.get(1)
  const seeded = buildSeedCardFields(guide, chapter)
  const card = makeDummyCard({ ...seeded })
  const deck: DeckRecord = {
    id: 'deck-01',
    user_id: 'user-1',
    name: guide.deckName,
    parent_id: null,
    desired_retention_override: null,
    default_priority: 80,
    position: 0,
    target_event_date: null,
    target_event_title: null,
    documentation: null,
    thematic_nature: null,
    source_documents: [],
    created_at: new Date().toISOString(),
  }

  const lesson = buildSocraticLesson(card, deck, course)
  assert.equal(lesson.available, true)
  assert.equal(lesson.model_used, 'socratic-study-guide')
  assert.ok(lesson.socratic)
  assert.equal(lesson.socratic.chapter_number, 1)
  assert.equal(lesson.socratic.readings[0].sections[0].question, 'How do you turn text into a number safely?')
  assert.ok(lesson.socratic.readings[0].sections[0].body.includes('Number("42")'))
  assert.ok(lesson.socratic.trap?.includes('`Number("")`'))
  assert.ok(lesson.socratic.doc_links.some((d) => d.url.includes('Number/isInteger')))
  assert.ok(lesson.socratic.think_it_through && lesson.socratic.think_it_through.length > 20)

  // Non-spoiling guarantee: lesson body and readings must NOT contain the card's exact solution implementation
  assert.equal(lesson.body.includes('text.trim() === ""'), false)
  assert.equal(lesson.body.includes('Write `parseCount(text)`'), false)

  // Progressive Socratic guide turns
  const turn0 = buildSocraticGuideReply(card, deck, course, 'I tried parseInt(text, 10) but 12abc passes', [])
  assert.ok(turn0.message.includes('invariant') || turn0.message.includes('trap') || turn0.message.includes('Number("")'))
  const turn1 = buildSocraticGuideReply(card, deck, course, 'What fails on empty string?', [
    { role: 'student', text: 'I tried parseInt' },
    { role: 'guide', text: turn0.message },
  ])
  assert.ok(turn1.message.includes('parseInt') || turn1.message.includes('Number'))
  const turn2 = buildSocraticGuideReply(card, deck, course, 'Still stuck on steps', [
    { role: 'student', text: 'a' },
    { role: 'guide', text: turn0.message },
    { role: 'student', text: 'b' },
    { role: 'guide', text: turn1.message },
  ])
  assert.ok(turn2.message.includes('Strategy:') || turn2.message.includes('Verify'))
})

test('matches cards by slug or title even without explicit guide tag', () => {
  const course = loadAllSocraticGuides()
  const byTitle = matchCardToGuide(
    { title: 'parseCount(text)', front: 'Write parseCount(text)...', tags: [], starter_code: null },
    course,
  )
  assert.equal(byTitle?.title, 'parseCount(text)')

  const bySlug = matchCardToGuide(
    { title: 'What does this print? (ts15-emits-anyway)', front: 'tsc reports...', tags: [], starter_code: null },
    course,
  )
  assert.equal(bySlug?.slug, 'ts15-emits-anyway')
  assert.ok((bySlug?.terms.length ?? 0) >= 1)
  assert.equal(bySlug?.terms[0].term, 'Type erasure')

  const labCard = matchCardToGuide(
    { title: 'parseCsv(text)', front: 'Write parseCsv(text)...', tags: [], starter_code: null },
    course,
  )
  assert.equal(labCard?.partNumber, 4)
  assert.equal(labCard?.deckName, '26 · JavaScript Labs')
})

test('non-JS/TS cards do not leak card.back verbatim in the Socratic lesson', () => {
  const course = loadAllSocraticGuides()
  const card = makeDummyCard({
    title: 'Amortized Array Append',
    front: 'Why is dynamic array append O(1) amortized?',
    back: 'SECRET_VERBATIM_ANSWER_GEOMETRIC_SERIES_2N',
    template_kind: 'basic',
    grading_profile: 'conceptual',
    tags: ['algorithms'],
    edge_cases: ['Capacity starts at 0 or 1'],
  })
  const deck: DeckRecord = {
    id: 'deck-algo',
    user_id: 'user-1',
    name: 'Algorithms & Complexity',
    parent_id: null,
    desired_retention_override: null,
    default_priority: 80,
    position: 0,
    target_event_date: null,
    target_event_title: null,
    documentation: 'Core algorithmic invariants and amortized analysis.',
    thematic_nature: 'Computer Science',
    source_documents: [],
    created_at: new Date().toISOString(),
  }

  const lesson = buildSocraticLesson(card, deck, course)
  assert.equal(lesson.available, true)
  assert.equal(lesson.body.includes('SECRET_VERBATIM_ANSWER_GEOMETRIC_SERIES_2N'), false)
  assert.ok(lesson.socratic?.think_it_through)
})
