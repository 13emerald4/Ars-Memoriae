import { useCallback, useEffect, useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api, ApiError } from '../api/client'
import { SuperMemoTree, type SuperMemoNode } from '../components/SuperMemoTree'
import type {
  AcceptDeckResponse,
  AtomicityLintResult,
  Card,
  Deck,
  DeckStats,
  DecomposedCardItem,
  DocumentUpload,
  GenerateDeckResponse,
  JsonImportResult,
  NoteType,
  OcclusionShape,
  SequentialClozeItem,
} from '../api/types'
import { DeckReviewStatsBar, CompactDeckDistributionBars } from '../components/DeckReviewStatsBar'
import { OcclusionEditor } from '../components/Occlusion'
import { Empty, ErrorNote, PriorityBar, RichText, Section, Spinner } from '../components/ui'

export default function Decks() {
  const navigate = useNavigate()
  const [decks, setDecks] = useState<Deck[]>([])
  const [noteTypes, setNoteTypes] = useState<NoteType[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<unknown>(null)
  const [selected, setSelected] = useState<string | null>(null)

  const load = useCallback(async () => {
    try {
      const [d, nt] = await Promise.all([api.decks(), api.noteTypes()])
      setDecks(d)
      setNoteTypes(nt)
      setSelected((prev) => prev ?? d[0]?.id ?? null)
    } catch (err) {
      setError(err)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    void load()
  }, [load])

  const selectedDeck = decks.find((d) => d.id === selected) || null

  const collectionStats = useMemo<DeckStats>(() => {
    let totalCards = 0
    let viewedCards = 0
    let newCards = 0
    let learningCards = 0
    let reviewCards = 0
    let dueCards = 0
    let totalReviews = 0
    const diffCounts: Record<string, number> = { Easy: 0, Medium: 0, Hard: 0, Unrated: 0 }
    const ratingCounts: Record<string, number> = { Again: 0, Hard: 0, Good: 0, Easy: 0, Unrated: 0 }

    const rootDecks = decks.filter(
      (d) => !d.parent_id || !decks.some((other) => other.id === d.parent_id),
    )
    for (const d of rootDecks) {
      if (d.stats) {
        totalCards += d.stats.total_cards || 0
        viewedCards += d.stats.viewed_cards || 0
        newCards += d.stats.new_cards || 0
        learningCards += d.stats.learning_cards || 0
        reviewCards += d.stats.review_cards || 0
        dueCards += d.stats.due_cards || 0
        totalReviews += d.stats.total_reviews || 0
        for (const [k, v] of Object.entries(d.stats.difficulty_counts || {})) {
          diffCounts[k] = (diffCounts[k] || 0) + v
        }
        for (const [k, v] of Object.entries(d.stats.rating_counts || {})) {
          ratingCounts[k] = (ratingCounts[k] || 0) + v
        }
      }
    }

    const round4 = (n: number) => Math.round(n * 10000) / 10000
    const viewedRatio = totalCards > 0 ? round4(viewedCards / totalCards) : 0
    const diffProps: Record<string, number> = {}
    for (const [k, v] of Object.entries(diffCounts)) {
      if (v > 0 || ['Easy', 'Medium', 'Hard'].includes(k)) {
        diffProps[k] = totalCards > 0 ? round4(v / totalCards) : 0
      }
    }
    const ratingProps: Record<string, number> = {}
    for (const [k, v] of Object.entries(ratingCounts)) {
      if (v > 0 || ['Again', 'Hard', 'Good', 'Easy'].includes(k)) {
        ratingProps[k] = totalCards > 0 ? round4(v / totalCards) : 0
      }
    }

    return {
      id: '__root__',
      name: 'Entire Collection (All Decks)',
      total_cards: totalCards,
      viewed_cards: viewedCards,
      new_cards: newCards,
      learning_cards: learningCards,
      review_cards: reviewCards,
      due_cards: dueCards,
      viewed_ratio: viewedRatio,
      difficulty_counts: diffCounts,
      difficulty_proportions: diffProps,
      rating_counts: ratingCounts,
      rating_proportions: ratingProps,
      total_reviews: totalReviews,
    }
  }, [decks])

  if (loading) return <Spinner />

  return (
    <div className="space-y-6">
      <ErrorNote error={error} />
      <DeckList decks={decks} selected={selected} onSelect={setSelected} onChange={load} />

      {/* Full Progress & Distribution Bars for Selected Deck or Entire Collection */}
      <DeckReviewStatsBar
        deckId={selectedDeck ? selectedDeck.id : '__root__'}
        deckName={selectedDeck ? selectedDeck.name : 'All Decks'}
        stats={selectedDeck ? selectedDeck.stats : collectionStats}
        onStudyDeck={(id) => {
          if (id === '__root__') navigate('/review')
          else navigate(`/review?deck=${id}`)
        }}
        onOpenDeckViewer={
          selectedDeck
            ? () => {
                const el = document.getElementById('deck-browser-section')
                if (el) el.scrollIntoView({ behavior: 'smooth' })
              }
            : undefined
        }
      />

      {selectedDeck && (
        <DeckDocumentationPanel deck={selectedDeck} onChange={load} />
      )}
      {selectedDeck && (
        <div id="deck-browser-section" className="space-y-6">
          <AddNote deckId={selectedDeck.id} noteTypes={noteTypes} deck={selectedDeck} onAdded={load} />
          <SequentialClozePanel deckId={selectedDeck.id} onAdded={load} />
          <AddOcclusion deckId={selectedDeck.id} onAdded={load} />
          <Browser deckId={selectedDeck.id} deck={selectedDeck} onChange={load} />
        </div>
      )}
      <DocumentDeckPanel onImported={load} />
      <JsonImportPanel onImported={load} />
      <LlmPromptPanel />
    </div>
  )
}

function DeckDocumentationPanel({ deck, onChange }: { deck: Deck; onChange: () => void }) {
  const [editing, setEditing] = useState(false)
  const [thematicNature, setThematicNature] = useState(deck.thematic_nature || '')
  const [documentation, setDocumentation] = useState(deck.documentation || '')
  const formatDocString = (d: any): string => {
    if (typeof d === 'string') {
      try {
        const parsed = JSON.parse(d)
        if (typeof parsed === 'object' && parsed !== null) return formatDocString(parsed)
      } catch {
        return d
      }
      return d
    }
    if (typeof d === 'object' && d !== null) {
      const name = d.title || d.name || d.filename || 'Document'
      const pages = d.pages ? ` (pp. ${d.pages})` : ''
      return `${name}${pages}`
    }
    return String(d)
  }

  const [sourceDocsText, setSourceDocsText] = useState(
    (deck.source_documents || []).map(formatDocString).join('\n'),
  )
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<unknown>(null)

  useEffect(() => {
    setThematicNature(deck.thematic_nature || '')
    setDocumentation(deck.documentation || '')
    setSourceDocsText(
      (deck.source_documents || []).map(formatDocString).join('\n'),
    )
    setEditing(false)
  }, [deck.id, deck.thematic_nature, deck.documentation, deck.source_documents])

  async function handleSave() {
    setBusy(true)
    setError(null)
    try {
      const parsedDocs = sourceDocsText
        .split('\n')
        .map((s) => s.trim())
        .filter(Boolean)
        .map((title) => ({ title }))
      await api.updateDeck(deck.id, {
        thematic_nature: thematicNature.trim() || null,
        documentation: documentation.trim() || null,
        source_documents: parsedDocs.length > 0 ? parsedDocs : null,
      })
      setEditing(false)
      onChange()
    } catch (err) {
      setError(err)
    } finally {
      setBusy(false)
    }
  }

  const sourceDocs = deck.source_documents || []

  return (
    <Section
      title={`Documentation & Provenance: ${deck.name}`}
      description="Thematic scope, creation documents, and documentation attached to this deck and inherited by all its cards."
      actions={
        <button
          type="button"
          onClick={() => setEditing((prev) => !prev)}
          className="btn px-2.5 py-1 text-xs"
        >
          {editing ? 'Cancel' : 'Edit Documentation & Theme'}
        </button>
      }
    >
      <ErrorNote error={error} />
      {editing ? (
        <div className="space-y-4 rounded-xl border border-sky-500/30 bg-sky-950/10 p-4">
          <div>
            <label className="block text-xs font-semibold text-slate-300 mb-1">
              Thematic Nature
            </label>
            <input
              className="input w-full text-xs"
              placeholder="e.g. Computer Science - Systems & Concurrency"
              value={thematicNature}
              onChange={(e) => setThematicNature(e.target.value)}
            />
            <p className="mt-1 text-[11px] text-slate-500">
              The high-level domain, discipline, or thematic context represented by this deck.
            </p>
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-300 mb-1">
              Attached Documentation &amp; Syllabus Notes
            </label>
            <textarea
              className="input w-full min-h-[6rem] text-xs font-mono"
              placeholder="Detailed documentation, overview of concepts, syllabus alignment, or memory hooks…"
              value={documentation}
              onChange={(e) => setDocumentation(e.target.value)}
            />
            <p className="mt-1 text-[11px] text-slate-500">
              Markdown supported. Inherited by each card unless overridden at the card level.
            </p>
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-300 mb-1">
              Source Documents Used in Creation
            </label>
            <textarea
              className="input w-full min-h-[4rem] text-xs font-mono"
              placeholder="One source document per line (e.g. Operating Systems: Three Easy Pieces Ch. 28)"
              value={sourceDocsText}
              onChange={(e) => setSourceDocsText(e.target.value)}
            />
            <p className="mt-1 text-[11px] text-slate-500">
              Document titles, papers, textbook chapters, or URLs used to create this deck.
            </p>
          </div>

          <div className="flex items-center justify-end gap-2 pt-2 border-t border-ink-line">
            <button
              type="button"
              className="btn text-xs px-3 py-1.5"
              onClick={() => setEditing(false)}
              disabled={busy}
            >
              Cancel
            </button>
            <button
              type="button"
              className="btn btn-primary text-xs px-3 py-1.5"
              onClick={handleSave}
              disabled={busy}
            >
              {busy ? 'Saving…' : 'Save Documentation'}
            </button>
          </div>
        </div>
      ) : (
        <div className="space-y-3">
          {/* Thematic Nature Banner */}
          <div className="flex flex-wrap items-center gap-2">
            <span className="text-xs font-semibold text-slate-400">Thematic Nature:</span>
            {deck.thematic_nature ? (
              <span className="rounded-md border border-sky-500/40 bg-sky-500/10 px-2.5 py-0.5 text-xs font-semibold text-sky-200">
                {deck.thematic_nature}
              </span>
            ) : (
              <span className="text-xs italic text-slate-500">
                None specified (click Edit Documentation &amp; Theme to set)
              </span>
            )}
          </div>

          {/* Source Documents */}
          <div className="space-y-1">
            <span className="text-xs font-semibold text-slate-400">Documents Used in Creation:</span>
            {sourceDocs.length > 0 ? (
              <div className="flex flex-wrap items-center gap-1.5 pt-1">
                {sourceDocs.map((doc: any, i: number) => {
                  const label = formatDocString(doc)
                  return (
                    <span
                      key={i}
                      className="chip border-emerald-500/40 bg-emerald-500/10 text-emerald-300 text-xs font-medium"
                    >
                      📄 {label}
                    </span>
                  )
                })}
              </div>
            ) : (
              <p className="text-xs italic text-slate-500 pt-0.5">
                No creation documents linked yet.
              </p>
            )}
          </div>

          {/* Documentation Content */}
          <div className="pt-2 border-t border-ink-line">
            <span className="text-xs font-semibold text-slate-400 block mb-1">
              Deck Documentation:
            </span>
            {deck.documentation ? (
              <div className="rounded-lg border border-ink-line bg-ink/40 p-3 text-xs leading-relaxed text-slate-300">
                <RichText text={deck.documentation} />
              </div>
            ) : (
              <p className="text-xs italic text-slate-500">
                No documentation added yet. Click &ldquo;Edit Documentation &amp; Theme&rdquo; to add background notes, syllabus objectives, and reference materials.
              </p>
            )}
          </div>
        </div>
      )}
    </Section>
  )
}

/** Upload a document -> the model proposes cards that each cite the passage
 *  they came from -> you approve -> the citations are kept and shown during
 *  review, after you answer. Nothing is written until you accept. */
const GENERATION_MODELS = [
  { id: 'qwen2.5-coder:7b', name: 'Qwen 2.5 Coder (7B Instruct)', badge: 'Local Engine' },
]

const THINKING_LEVELS = [
  { id: 'dynamic', label: 'Default', budget: undefined, hint: 'Standard inference' },
]

function DocumentDeckPanel({ onImported }: { onImported: () => void }) {
  const [doc, setDoc] = useState<DocumentUpload | null>(null)
  const [deckName, setDeckName] = useState('')
  const [thematicNature, setThematicNature] = useState('')
  const [docDocumentation, setDocDocumentation] = useState('')
  const [selectedModel, setSelectedModel] = useState('qwen2.5-coder:7b')
  const [selectedThinking, setSelectedThinking] = useState('dynamic')
  const [generated, setGenerated] = useState<GenerateDeckResponse | null>(null)
  const [chosen, setChosen] = useState<Set<number>>(new Set())
  const [accepted, setAccepted] = useState<AcceptDeckResponse | null>(null)
  const [busy, setBusy] = useState('')
  const [error, setError] = useState<unknown>(null)

  function reset() {
    setDoc(null)
    setGenerated(null)
    setChosen(new Set())
    setAccepted(null)
    setError(null)
    setDeckName('')
    setThematicNature('')
    setDocDocumentation('')
  }

  async function upload(file: File) {
    setBusy('Reading the document…')
    setError(null)
    setGenerated(null)
    setAccepted(null)
    try {
      const uploaded = await api.uploadDocument(file)
      setDoc(uploaded)
      if (!deckName.trim()) setDeckName(uploaded.title)
      setThematicNature(`${uploaded.title} — Key Concepts`)
      setDocDocumentation(`Deck generated from document "${uploaded.title}" (${uploaded.segment_count} sections analyzed).`)
    } catch (err) {
      setError(err)
    } finally {
      setBusy('')
    }
  }

  async function generate(startSection = 0) {
    if (!doc) return
    setBusy('Generating cards…')
    setError(null)
    try {
      const thinkingBudget = THINKING_LEVELS.find((t) => t.id === selectedThinking)?.budget
      const out = await api.generateDeck(doc.source_id, {
        start_section: startSection,
        max_sections: 4,
        model: selectedModel,
        thinking_budget: thinkingBudget,
      })
      setGenerated(out)
      // Everything is pre-selected: the user is reviewing a proposal, not
      // assembling one from scratch.
      setChosen(new Set(out.cards.map((_, i) => i)))
    } catch (err) {
      setError(err)
    } finally {
      setBusy('')
    }
  }

  async function accept() {
    if (!doc || !generated) return
    const cards = generated.cards.filter((_, i) => chosen.has(i))
    if (cards.length === 0) return
    setBusy('Creating cards…')
    setError(null)
    try {
      setAccepted(
        await api.acceptDeck(doc.source_id, deckName.trim() || doc.title, cards, {
          thematic_nature: thematicNature.trim() || undefined,
          documentation: docDocumentation.trim() || undefined,
        }),
      )
      onImported()
    } catch (err) {
      setError(err)
    } finally {
      setBusy('')
    }
  }

  return (
    <Section
      title="Generate a deck from a document"
      description="Upload a PDF, Markdown, or text file. Each generated card keeps a citation into the reading, shown after you answer it during review."
      actions={
        doc && (
          <button className="btn px-2 py-1 text-xs" onClick={reset}>
            Start over
          </button>
        )
      }
    >
      <div className="space-y-4">
        {!doc ? (
          <input
            type="file"
            accept=".pdf,.txt,.md,.markdown,.html,.htm,.rst"
            disabled={Boolean(busy)}
            className="block w-full text-sm text-slate-400 file:mr-4 file:rounded-lg file:border-0 file:bg-sky-500/15 file:px-4 file:py-2 file:text-sm file:text-sky-200 hover:file:bg-sky-500/25"
            onChange={(e) => {
              const file = e.target.files?.[0]
              if (file) void upload(file)
              e.target.value = ''
            }}
          />
        ) : (
          <div className="flex flex-wrap items-center gap-2 text-xs">
            <span className="chip">{doc.title}</span>
            <span className="chip">{doc.segment_count} sections</span>
            {doc.locators.slice(0, 4).map((l) => (
              <span key={l} className="chip text-slate-500">
                {l}
              </span>
            ))}
          </div>
        )}

        {doc && (!generated || generated.degraded) && (
          <div className="space-y-3 rounded-lg border border-ink-line bg-ink/40 p-3.5">
            <div className="grid gap-3 sm:grid-cols-3">
              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1">Deck name</label>
                <input
                  className="input w-full text-xs"
                  placeholder="Deck name"
                  value={deckName}
                  onChange={(e) => setDeckName(e.target.value)}
                />
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1">Model</label>
                <select
                  className="input w-full text-xs"
                  value={selectedModel}
                  onChange={(e) => setSelectedModel(e.target.value)}
                >
                  {GENERATION_MODELS.map((m) => (
                    <option key={m.id} value={m.id}>
                      {m.name} — {m.badge}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1">Thinking level</label>
                <select
                  className="input w-full text-xs"
                  value={selectedThinking}
                  onChange={(e) => setSelectedThinking(e.target.value)}
                >
                  {THINKING_LEVELS.map((t) => (
                    <option key={t.id} value={t.id}>
                      {t.label} ({t.hint})
                    </option>
                  ))}
                </select>
              </div>
            </div>

            <div className="flex justify-end pt-1">
              <button
                className="btn btn-primary"
                disabled={Boolean(busy)}
                onClick={() => generate(0)}
              >
                {generated?.degraded ? 'Retry generating cards' : 'Generate cards'}
              </button>
            </div>
          </div>
        )}

        {busy && <Spinner label={busy} />}
        <ErrorNote error={error} />

        {generated?.degraded && (
          <div className="rounded-lg border border-amber-500/40 bg-amber-500/10 px-4 py-3 text-sm text-amber-200">
            <p>
              {generated.reason === 'consent_not_given'
                ? 'LLM card generation needs your consent — turn it on in Settings.'
                : `Card generation was temporarily unavailable (${generated.reason}).`}
            </p>
            {generated.warnings.length > 0 && (
              <p className="mt-1.5 text-xs text-amber-300/80">
                Details: {generated.warnings[0]}
              </p>
            )}
            <p className="mt-2 text-xs text-slate-400">
              Check that Ollama is running and the model is pulled. Click &ldquo;Retry generating cards&rdquo; above or select a different model in Settings.
            </p>
          </div>
        )}

        {generated && !generated.degraded && !accepted && (
          <div className="space-y-3">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <p className="text-xs text-slate-500">
                {chosen.size} of {generated.cards.length} selected · sections{' '}
                {generated.sections_used}/{generated.sections_total}
              </p>
              <div className="flex gap-2">
                <button
                  className="btn px-2 py-1 text-xs"
                  onClick={() =>
                    setChosen(
                      chosen.size === generated.cards.length
                        ? new Set()
                        : new Set(generated.cards.map((_, i) => i)),
                    )
                  }
                >
                  {chosen.size === generated.cards.length ? 'Select none' : 'Select all'}
                </button>
                {generated.next_section !== null && (
                  <button
                    className="btn px-2 py-1 text-xs"
                    disabled={Boolean(busy)}
                    onClick={() => generate(generated.next_section!)}
                  >
                    Next sections
                  </button>
                )}
              </div>
            </div>

            {generated.cards.length === 0 ? (
              <Empty title="The model proposed no cards for these sections." />
            ) : (
              <div className="space-y-2">
                {generated.cards.map((card, i) => (
                  <label
                    key={i}
                    className={`flex cursor-pointer gap-3 rounded-lg border p-3 transition ${
                      chosen.has(i) ? 'border-sky-500/40 bg-sky-500/5' : 'border-ink-line'
                    }`}
                  >
                    <input
                      type="checkbox"
                      className="mt-1"
                      checked={chosen.has(i)}
                      onChange={() =>
                        setChosen((prev) => {
                          const next = new Set(prev)
                          next.has(i) ? next.delete(i) : next.add(i)
                          return next
                        })
                      }
                    />
                    <div className="min-w-0 flex-1">
                      <p className="text-sm text-slate-200">
                        {card.kind === 'cloze' ? card.cloze_text : card.front}
                      </p>
                      {card.kind !== 'cloze' && (
                        <p className="mt-1 text-sm text-slate-500">{card.back}</p>
                      )}
                      <div className="mt-2 flex flex-wrap items-center gap-2 text-xs">
                        <span className="chip">{card.kind}</span>
                        {card.locator && <span className="chip text-sky-300">{card.locator}</span>}
                        {!card.quote_verified && (
                          <span
                            className="chip text-amber-300"
                            title="The model's quote wasn't found in the source, so the full passage is cited instead."
                          >
                            passage cited
                          </span>
                        )}
                      </div>
                      {card.quote && (
                        <blockquote className="mt-2 border-l-2 border-sky-500/40 pl-3 text-xs italic text-slate-400">
                          “{card.quote}”
                        </blockquote>
                      )}
                    </div>
                  </label>
                ))}
              </div>
            )}

            {generated.warnings.length > 0 && (
              <div className="rounded-lg border border-amber-500/40 bg-amber-500/10 p-4">
                <p className="text-xs font-semibold uppercase tracking-wide text-amber-200">
                  Notes from generation
                </p>
                <ul className="mt-2 space-y-1.5 text-sm text-amber-100/90">
                  {generated.warnings.map((w, i) => (
                    <li key={i}>· {w}</li>
                  ))}
                </ul>
              </div>
            )}

            <div className="space-y-3 rounded-lg border border-ink-line bg-ink/40 p-3.5">
              <p className="text-xs font-semibold text-slate-300">
                Deck Thematic Nature &amp; Documentation
              </p>
              <div className="grid gap-3 sm:grid-cols-2">
                <div>
                  <label className="block text-xs font-medium text-slate-400 mb-1">
                    Thematic Nature
                  </label>
                  <input
                    className="input w-full text-xs"
                    placeholder="e.g. Distributed Systems & Consensus"
                    value={thematicNature}
                    onChange={(e) => setThematicNature(e.target.value)}
                  />
                </div>
                <div>
                  <label className="block text-xs font-medium text-slate-400 mb-1">
                    Deck Documentation
                  </label>
                  <input
                    className="input w-full text-xs"
                    placeholder="Documentation overview or syllabus notes"
                    value={docDocumentation}
                    onChange={(e) => setDocDocumentation(e.target.value)}
                  />
                </div>
              </div>
            </div>

            <div className="flex flex-wrap items-center gap-2">
              <input
                className="input w-56"
                placeholder="Deck name"
                value={deckName}
                onChange={(e) => setDeckName(e.target.value)}
              />
              <button
                className="btn btn-primary"
                disabled={Boolean(busy) || chosen.size === 0}
                onClick={accept}
              >
                Create {chosen.size} card{chosen.size === 1 ? '' : 's'}
              </button>
            </div>
          </div>
        )}

        {accepted && (
          <div className="space-y-2">
            <div className="flex flex-wrap gap-2 text-xs">
              <span className="chip">{accepted.deck_created ? 'created' : 'reused'} deck</span>
              <span className="chip">{accepted.notes_created} notes</span>
              <span className="chip">{accepted.cards_created} cards</span>
              <span className="chip">{accepted.references_created} citations</span>
            </div>
            <p className="text-xs text-slate-500">
              Review these cards and the reading will appear once you answer.
            </p>
            {generated?.next_section !== null && generated?.next_section !== undefined && (
              <button
                className="btn px-2 py-1 text-xs"
                onClick={() => {
                  setAccepted(null)
                  void generate(generated.next_section!)
                }}
              >
                Generate the next sections
              </button>
            )}
          </div>
        )}
      </div>
    </Section>
  )
}

function buildDeckTree(decks: Deck[]): SuperMemoNode[] {
  const childrenMap = new Map<string | null, Deck[]>()
  for (const d of decks) {
    const p = d.parent_id || null
    if (!childrenMap.has(p)) childrenMap.set(p, [])
    childrenMap.get(p)!.push(d)
  }

  function nodeFor(d: Deck): SuperMemoNode {
    const kids = (childrenMap.get(d.id) || []).map(nodeFor)
    return {
      id: d.id,
      title: d.name,
      kind: 'deck',
      parentId: d.parent_id,
      elementCount: d.total_card_count ?? d.card_count,
      dueCount: d.total_due_count ?? d.due_count,
      newCount: d.total_new_count ?? d.new_count,
      deckId: d.id,
      originalDeck: d,
      stats: d.stats,
      children: kids,
    }
  }

  const deckIds = new Set(decks.map((d) => d.id))
  const roots = decks.filter((d) => !d.parent_id || !deckIds.has(d.parent_id))
  return roots.map(nodeFor)
}

function DeckList({
  decks,
  selected,
  onSelect,
  onChange,
}: {
  decks: Deck[]
  selected: string | null
  onSelect: (id: string) => void
  onChange: () => void
}) {
  const navigate = useNavigate()
  const [name, setName] = useState('')
  const [parentId, setParentId] = useState<string>('')
  const [busy, setBusy] = useState(false)
  const [viewMode, setViewMode] = useState<'supermemo' | 'list'>('supermemo')

  const deckTreeNodes = useMemo(() => buildDeckTree(decks), [decks])
  const totalCollectionCards = useMemo(() => decks.reduce((sum, d) => sum + d.card_count, 0), [decks])
  const totalDue = useMemo(() => decks.reduce((sum, d) => sum + d.due_count, 0), [decks])
  const totalNew = useMemo(() => decks.reduce((sum, d) => sum + d.new_count, 0), [decks])

  const [detailedTheme, setDetailedTheme] = useState('')
  const [detailedDoc, setDetailedDoc] = useState('')
  const [detailedSources, setDetailedSources] = useState('')
  const [showDetailedCreate, setShowDetailedCreate] = useState(false)

  async function handleCreateDetailedDeck(e: React.FormEvent) {
    e.preventDefault()
    if (!name.trim()) return
    setBusy(true)
    try {
      const parsedDocs = detailedSources
        .split('\n')
        .map((s) => s.trim())
        .filter(Boolean)
        .map((title) => ({ title }))
      await api.createDeck({
        name: name.trim(),
        parent_id: parentId || undefined,
        thematic_nature: detailedTheme.trim() || undefined,
        documentation: detailedDoc.trim() || undefined,
        source_documents: parsedDocs.length > 0 ? parsedDocs : undefined,
      })
      setName('')
      setParentId('')
      setDetailedTheme('')
      setDetailedDoc('')
      setDetailedSources('')
      setShowDetailedCreate(false)
      onChange()
    } finally {
      setBusy(false)
    }
  }

  async function handleDeleteAll() {
    if (!confirm('Are you sure you want to delete ALL decks? All cards, notes, and progress in them will be permanently deleted.')) {
      return
    }
    setBusy(true)
    try {
      await api.deleteAllDecks()
      onChange()
    } finally {
      setBusy(false)
    }
  }

  async function handleDeleteDeck(deck: Deck) {
    if (!confirm(`Delete deck "${deck.name}" and all its ${deck.card_count} cards?`)) {
      return
    }
    setBusy(true)
    try {
      await api.deleteDeck(deck.id, true)
      onChange()
    } finally {
      setBusy(false)
    }
  }

  return (
    <Section
      title="Decks"
      description="Per-deck priority and retention are the “% bias per subject” controls. Organize subdecks hierarchically as in SuperMemo."
      actions={
        <div className="flex flex-wrap items-center gap-2">
          {/* View mode toggle */}
          <div className="flex items-center rounded-lg border border-slate-700 bg-slate-800/80 p-0.5 text-xs">
            <button
              type="button"
              className={`px-2 py-1 rounded transition ${
                viewMode === 'supermemo'
                  ? 'bg-sky-500/20 text-sky-200 font-semibold shadow-xs'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
              onClick={() => setViewMode('supermemo')}
            >
              🗂️ SuperMemo Tree
            </button>
            <button
              type="button"
              className={`px-2 py-1 rounded transition ${
                viewMode === 'list'
                  ? 'bg-sky-500/20 text-sky-200 font-semibold shadow-xs'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
              onClick={() => setViewMode('list')}
            >
              📋 Flat List
            </button>
          </div>

          <button
            type="button"
            className={`btn text-xs px-2.5 py-1 ${showDetailedCreate ? 'btn-primary' : ''}`}
            onClick={() => setShowDetailedCreate((prev) => !prev)}
            title="Create a new deck with attached documentation, thematic nature, and source documents"
          >
            {showDetailedCreate ? 'Cancel New Deck' : '+ New Deck with Documentation'}
          </button>

          {decks.length > 0 && (
            <button
              type="button"
              className="btn btn-danger text-xs px-2.5 py-1"
              disabled={busy}
              onClick={handleDeleteAll}
            >
              Delete all decks
            </button>
          )}

          {!showDetailedCreate && (
            <form
              className="flex flex-wrap items-center gap-2"
              onSubmit={async (e) => {
                e.preventDefault()
                if (!name.trim()) return
                setBusy(true)
                try {
                  await api.createDeck({ name: name.trim(), parent_id: parentId || undefined })
                  setName('')
                  setParentId('')
                  onChange()
                } finally {
                  setBusy(false)
                }
              }}
            >
              <select
                className="input w-36 text-xs py-1"
                value={parentId}
                onChange={(e) => setParentId(e.target.value)}
                title="Parent deck (optional for creating subdecks)"
              >
                <option value="">(No parent / Root)</option>
                {decks.map((d) => (
                  <option key={d.id} value={d.id}>
                    Inside {d.name}
                  </option>
                ))}
              </select>
              <input
                className="input w-36 text-xs py-1"
                placeholder="New deck name"
                value={name}
                onChange={(e) => setName(e.target.value)}
              />
              <button className="btn text-xs px-2.5 py-1" disabled={busy}>
                Add deck
              </button>
            </form>
          )}
        </div>
      }
    >
      <div className="space-y-3">
        {/* Detailed Deck Creation Form */}
        {showDetailedCreate && (
          <form
            onSubmit={handleCreateDetailedDeck}
            className="rounded-xl border border-sky-500/40 bg-sky-950/20 p-4 space-y-3 shadow-lg"
          >
            <div className="flex items-center justify-between">
              <h3 className="font-semibold text-sm text-sky-200">
                Create New Deck with Documentation &amp; Thematic Scope
              </h3>
              <button
                type="button"
                className="text-xs text-slate-400 hover:text-slate-200"
                onClick={() => setShowDetailedCreate(false)}
              >
                ✕ Close
              </button>
            </div>

            <div className="grid gap-3 sm:grid-cols-2">
              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1">
                  Deck Name *
                </label>
                <input
                  className="input w-full text-xs"
                  placeholder="e.g. Operating Systems: Virtual Memory"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  required
                />
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1">
                  Parent Deck (Hierarchical Tree)
                </label>
                <select
                  className="input w-full text-xs"
                  value={parentId}
                  onChange={(e) => setParentId(e.target.value)}
                >
                  <option value="">(Root / No parent)</option>
                  {decks.map((d) => (
                    <option key={d.id} value={d.id}>
                      Inside {d.name}
                    </option>
                  ))}
                </select>
              </div>
            </div>

            <div>
              <label className="block text-xs font-medium text-slate-300 mb-1">
                Thematic Nature
              </label>
              <input
                className="input w-full text-xs"
                placeholder="e.g. Computer Science - OS Virtual Memory, Paging & TLB"
                value={detailedTheme}
                onChange={(e) => setDetailedTheme(e.target.value)}
              />
              <p className="mt-1 text-[11px] text-slate-400">
                Thematic context attached to this deck and inherited by each created card.
              </p>
            </div>

            <div>
              <label className="block text-xs font-medium text-slate-300 mb-1">
                Deck Documentation &amp; Syllabus Notes
              </label>
              <textarea
                className="input w-full min-h-[5rem] text-xs font-mono"
                placeholder="Documentation markdown: objectives, definitions, core theorems, or review notes…"
                value={detailedDoc}
                onChange={(e) => setDetailedDoc(e.target.value)}
              />
            </div>

            <div>
              <label className="block text-xs font-medium text-slate-300 mb-1">
                Documents Used in Creation
              </label>
              <textarea
                className="input w-full min-h-[3.5rem] text-xs font-mono"
                placeholder="One source document title/URL per line (e.g. OSTEP Chapter 18, Lecture 7 Notes)"
                value={detailedSources}
                onChange={(e) => setDetailedSources(e.target.value)}
              />
              <p className="mt-1 text-[11px] text-slate-400">
                Provenance records: which textbooks, papers, or documents were used to create this deck.
              </p>
            </div>

            <div className="flex items-center justify-end gap-2 pt-2 border-t border-ink-line">
              <button
                type="button"
                className="btn text-xs px-3 py-1.5"
                onClick={() => setShowDetailedCreate(false)}
                disabled={busy}
              >
                Cancel
              </button>
              <button
                type="submit"
                className="btn btn-primary text-xs px-3 py-1.5"
                disabled={busy || !name.trim()}
              >
                {busy ? 'Creating Deck…' : 'Create Deck with Documentation'}
              </button>
            </div>
          </form>
        )}

        {/* Collection Study Hero Banner */}
        {decks.length > 0 && (
          <div className="flex flex-wrap items-center justify-between gap-3 p-3 rounded-lg border border-sky-500/30 bg-sky-500/10 mb-2">
            <div>
              <div className="flex items-center gap-2">
                <span className="font-bold text-sky-200 text-sm">Study Collection (All Decks)</span>
                <span className="chip border-sky-400/40 text-sky-200 bg-sky-500/20">{totalCollectionCards} cards</span>
                {totalDue > 0 && <span className="chip text-sky-300 font-semibold">{totalDue} due</span>}
                {totalNew > 0 && <span className="chip text-emerald-300">{totalNew} new</span>}
              </div>
              <p className="text-xs text-slate-400 mt-0.5">
                Study all {decks.length} deck{decks.length === 1 ? '' : 's'} in your collection all at once, interleaved by priority and FSRS schedule.
              </p>
            </div>
            <button
              type="button"
              onClick={() => navigate('/review')}
              className="btn btn-primary text-xs font-bold px-3 py-1.5 shadow-sm"
              title="Study all decks in the collection at once"
            >
              ⚡ Study All Decks
            </button>
          </div>
        )}

        {decks.length === 0 ? (
          <p className="text-xs text-slate-500 py-2">No decks created yet. Add one above or import a document.</p>
        ) : viewMode === 'supermemo' ? (
          <SuperMemoTree
            rootTitle="All Decks"
            nodes={deckTreeNodes}
            onSelectNode={(node) => {
              if (node.deckId) onSelect(node.deckId)
              else if (node.id === '__root__') onSelect('__root__')
            }}
            onStudyNode={(node) => {
              if (node.id === '__root__') {
                navigate('/review')
              } else if (node.deckId) {
                navigate(`/review?deck=${node.deckId}`)
              }
            }}
            onAddChild={(parent) => {
              const pDeckId = parent?.deckId || parent?.id
              if (pDeckId && pDeckId !== '__root__') {
                setParentId(pDeckId)
                const subName = prompt(`Enter subdeck name under "${parent?.title}":`)
                if (subName && subName.trim()) {
                  void (async () => {
                    setBusy(true)
                    try {
                      await api.createDeck({ name: subName.trim(), parent_id: pDeckId })
                      onChange()
                    } finally {
                      setBusy(false)
                    }
                  })()
                }
              } else {
                const newName = prompt('Enter top-level deck name:')
                if (newName && newName.trim()) {
                  void (async () => {
                    setBusy(true)
                    try {
                      await api.createDeck({ name: newName.trim() })
                      onChange()
                    } finally {
                      setBusy(false)
                    }
                  })()
                }
              }
            }}
            onRename={(node) => {
              if (!node.deckId) return
              const newName = prompt(`Rename deck "${node.title}" to:`, node.title)
              if (newName && newName.trim() && newName.trim() !== node.title) {
                void (async () => {
                  setBusy(true)
                  try {
                    await api.updateDeck(node.deckId!, { name: newName.trim() })
                    onChange()
                  } finally {
                    setBusy(false)
                  }
                })()
              }
            }}
            onDelete={(node) => {
              if (!node.originalDeck) return
              handleDeleteDeck(node.originalDeck)
            }}
            onDropBranch={(source, target, position) => {
              if (!source.deckId) return
              void (async () => {
                setBusy(true)
                try {
                  if (position === 'inside') {
                    const newParentId = target.id === '__root__' ? null : (target.deckId ?? null)
                    const existingChildren = decks.filter(
                      (d) => (d.parent_id ?? null) === newParentId && d.id !== source.deckId,
                    )
                    const maxPos = existingChildren.reduce((max, c) => Math.max(max, c.position ?? 0), -1)
                    await api.updateDeck(source.deckId!, {
                      parent_id: newParentId,
                      position: maxPos + 10,
                    })
                  } else {
                    // 'before' or 'after'
                    const newParentId = target.originalDeck?.parent_id ?? target.parentId ?? null
                    const siblings = decks
                      .filter((d) => (d.parent_id ?? null) === newParentId && d.id !== source.deckId)
                      .sort((a, b) => ((a.position ?? 0) - (b.position ?? 0)) || a.name.localeCompare(b.name))

                    const targetIdx = siblings.findIndex((s) => s.id === target.id)
                    const insertIdx = position === 'before'
                      ? (targetIdx === -1 ? 0 : targetIdx)
                      : (targetIdx === -1 ? siblings.length : targetIdx + 1)

                    const sourceDeck = decks.find((d) => d.id === source.deckId)
                    if (!sourceDeck) return
                    const newOrder = [...siblings]
                    newOrder.splice(insertIdx, 0, sourceDeck)

                    const items = newOrder.map((d, index) => ({
                      id: d.id,
                      parent_id: newParentId,
                      position: index * 10,
                    }))
                    await api.reorderDecks(items)
                  }
                  onChange()
                } catch (err) {
                  alert(`Failed to move branch: ${err instanceof Error ? err.message : String(err)}`)
                } finally {
                  setBusy(false)
                }
              })()
            }}
          />
        ) : (
          decks.map((d) => (
            <div
              key={d.id}
              className={`flex flex-wrap items-center justify-between gap-3 rounded-lg border p-3 transition ${
                selected === d.id ? 'border-sky-500/40 bg-sky-500/5' : 'border-ink-line'
              }`}
            >
              <button className="min-w-0 flex-1 text-left" onClick={() => onSelect(d.id)}>
                <div className="flex items-center gap-2">
                  <p className="font-medium text-slate-200">{d.name}</p>
                  {d.parent_id && (
                    <span className="text-[10px] px-1.5 py-0.5 rounded bg-slate-800 text-slate-400 border border-slate-700">
                      subdeck
                    </span>
                  )}
                </div>
                <p className="mt-1 flex flex-wrap items-center gap-2 text-xs text-slate-500">
                  <span className="chip">{d.card_count} cards</span>
                  {d.total_card_count !== undefined && d.total_card_count !== d.card_count && (
                    <span className="chip border-sky-500/40 text-sky-300">
                      {d.total_card_count} total (with subdecks)
                    </span>
                  )}
                  <span className="chip">{d.due_count} due</span>
                  <span className="chip">{d.new_count} new</span>
                  {d.stats && d.stats.total_cards > 0 && (
                    <CompactDeckDistributionBars stats={d.stats} />
                  )}
                </p>
              </button>

              <div className="flex flex-wrap items-center gap-3">
                <button
                  type="button"
                  onClick={(e) => {
                    e.stopPropagation()
                    navigate(`/review?deck=${d.id}`)
                  }}
                  className="btn btn-primary text-xs px-2.5 py-1 font-semibold"
                  title={`Study ${d.name} and all its subdecks`}
                >
                  Study
                </button>

                {d.card_count > 0 && (
                  <button
                    type="button"
                    onClick={(e) => {
                      e.stopPropagation()
                      navigate(`/review?deck=${d.id}&persist=1`)
                    }}
                    className="flex items-center gap-1.5 rounded-lg border border-amber-500/40 bg-amber-500/10 px-2.5 py-1 text-xs font-semibold text-amber-200 hover:bg-amber-500/20 hover:border-amber-400 transition shadow-sm"
                    title={`Persist reviewing ${d.name} until all cards are rated Easy`}
                  >
                    <span>⚡ Persist Review</span>
                  </button>
                )}

                {d.card_count > 0 && (
                  <button
                    type="button"
                    onClick={(e) => {
                      e.stopPropagation()
                      navigate(`/review?deck=${d.id}&run=all`)
                    }}
                    className="flex items-center gap-1.5 rounded-lg border border-purple-500/40 bg-purple-500/10 px-2.5 py-1 text-xs font-semibold text-purple-200 hover:bg-purple-500/20 hover:border-purple-400 transition shadow-sm"
                    title={`Run all cards in ${d.name} consecutively, easiest to hardest. Thereafter, FSRS takes over.`}
                  >
                    <span>🏁 All Cards Run</span>
                  </button>
                )}

                <button
                  type="button"
                  onClick={(e) => {
                    e.stopPropagation()
                    setParentId(d.id)
                  }}
                  className="btn text-xs px-2 py-1 text-slate-400 hover:text-slate-200"
                  title="Create a subdeck inside this deck"
                >
                  + Subdeck
                </button>

                <label className="flex items-center gap-2 text-xs text-slate-500">
                  priority
                  <input
                    type="range"
                    min={0}
                    max={100}
                    defaultValue={d.default_priority}
                    className="w-24"
                    onMouseUp={async (e) => {
                      await api.setPriority('deck', d.id, Number((e.target as HTMLInputElement).value))
                      onChange()
                    }}
                  />
                  <PriorityBar value={d.default_priority} />
                </label>

                <label className="flex items-center gap-2 text-xs text-slate-500">
                  retention
                  <input
                    type="number"
                    step={0.01}
                    min={0.7}
                    max={0.99}
                    defaultValue={d.desired_retention_override ?? ''}
                    placeholder="default"
                    className="input w-20 py-1 text-xs"
                    onBlur={async (e) => {
                      const raw = e.target.value.trim()
                      await api.updateDeck(d.id, {
                        desired_retention_override: raw ? Number(raw) : null,
                      })
                      onChange()
                    }}
                  />
                </label>

                <button
                  type="button"
                  title={`Delete deck ${d.name}`}
                  className="rounded p-1 text-xs text-slate-600 hover:bg-rose-500/15 hover:text-rose-300 transition"
                  onClick={() => handleDeleteDeck(d)}
                >
                  ✕
                </button>
              </div>
            </div>
          ))
        )}
      </div>
    </Section>
  )
}

function AddNote({
  deckId,
  noteTypes,
  deck,
  onAdded,
}: {
  deckId: string
  noteTypes: NoteType[]
  deck?: Deck | null
  onAdded: () => void
}) {
  const [noteTypeId, setNoteTypeId] = useState(noteTypes[0]?.id ?? '')
  const [front, setFront] = useState('')
  const [back, setBack] = useState('')
  const [clozeText, setClozeText] = useState('')
  const [tags, setTags] = useState('')
  const [showDocFields, setShowDocFields] = useState(false)
  const [cardThematicNature, setCardThematicNature] = useState('')
  const [cardDocumentation, setCardDocumentation] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<unknown>(null)

  // 🧠 Memory Champion: Extreme Atomicity Linter & AI Decomposition (§Feature 5)
  const [atomicity, setAtomicity] = useState<AtomicityLintResult | null>(null)
  const [decomposedCards, setDecomposedCards] = useState<DecomposedCardItem[] | null>(null)
  const [decomposing, setDecomposing] = useState(false)

  const noteType = noteTypes.find((n) => n.id === noteTypeId) ?? noteTypes[0]
  const isCloze = noteType?.template_kind === 'cloze'

  // Debounced Atomicity Linting
  useEffect(() => {
    if (isCloze || (!front.trim() && !back.trim())) {
      setAtomicity(null)
      return
    }
    const timer = setTimeout(() => {
      api
        .lintAtomicity(front, back, noteType?.template_kind)
        .then(setAtomicity)
        .catch(() => setAtomicity(null))
    }, 400)
    return () => clearTimeout(timer)
  }, [front, back, isCloze, noteType])

  async function handleDecompose() {
    if (!front.trim() || !back.trim()) return
    setDecomposing(true)
    setError(null)
    try {
      const resp = await api.decomposeCard(front, back)
      setDecomposedCards(resp.cards)
    } catch (err) {
      setError(err)
    } finally {
      setDecomposing(false)
    }
  }

  async function handleAddAllDecomposed() {
    if (!decomposedCards || decomposedCards.length === 0) return
    setBusy(true)
    setError(null)
    try {
      for (const card of decomposedCards) {
        await api.createNote({
          deck_id: deckId,
          note_type_id: noteTypeId,
          field_values: { Front: card.front, Back: card.back },
          tags: tags.split(',').map((t) => t.trim()).filter(Boolean),
          thematic_nature: cardThematicNature.trim() || undefined,
          documentation: cardDocumentation.trim() || undefined,
        })
      }
      setFront('')
      setBack('')
      setDecomposedCards(null)
      setAtomicity(null)
      setCardThematicNature('')
      setCardDocumentation('')
      onAdded()
    } catch (err) {
      setError(err)
    } finally {
      setBusy(false)
    }
  }

  async function submit(e: React.FormEvent) {
    e.preventDefault()
    setBusy(true)
    setError(null)
    try {
      await api.createNote({
        deck_id: deckId,
        note_type_id: noteTypeId,
        field_values: isCloze ? { Text: clozeText, Extra: back } : { Front: front, Back: back },
        tags: tags.split(',').map((t) => t.trim()).filter(Boolean),
        thematic_nature: cardThematicNature.trim() || undefined,
        documentation: cardDocumentation.trim() || undefined,
      })
      setFront('')
      setBack('')
      setClozeText('')
      setCardThematicNature('')
      setCardDocumentation('')
      setAtomicity(null)
      setDecomposedCards(null)
      onAdded()
    } catch (err) {
      setError(err)
    } finally {
      setBusy(false)
    }
  }

  return (
    <Section
      title="Add a note"
      description="The note type picks the grading rubric the LLM uses (§4.5)."
    >
      <form onSubmit={submit} className="space-y-3">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <select
            className="input max-w-xs"
            value={noteTypeId}
            onChange={(e) => setNoteTypeId(e.target.value)}
          >
            {noteTypes.map((n) => (
              <option key={n.id} value={n.id}>
                {n.name} · {n.template_kind} · {n.grading_profile}
              </option>
            ))}
          </select>

          {/* Atomicity Badge */}
          {atomicity && !isCloze && (
            <div className="flex items-center gap-2 text-xs">
              <span
                className={`chip font-medium ${
                  atomicity.score >= 90
                    ? 'border-emerald-500/40 bg-emerald-500/10 text-emerald-300'
                    : atomicity.score >= 70
                    ? 'border-amber-500/40 bg-amber-500/10 text-amber-300'
                    : 'border-rose-500/40 bg-rose-500/10 text-rose-300'
                }`}
              >
                Atomicity: {atomicity.score}/100{' '}
                {atomicity.is_atomic ? '✓ Atomic (1 Idea)' : '⚠ Compound / Complex'}
              </span>
            </div>
          )}
        </div>

        {isCloze ? (
          <textarea
            className="input min-h-[6rem] font-mono text-sm"
            placeholder="The {{c1::mitochondrion}} is the {{c2::powerhouse}} of the cell."
            value={clozeText}
            onChange={(e) => setClozeText(e.target.value)}
            required
          />
        ) : (
          <textarea
            className="input min-h-[4rem]"
            placeholder="Front (Prompt/Question)"
            value={front}
            onChange={(e) => setFront(e.target.value)}
            required
          />
        )}
        <textarea
          className="input min-h-[4rem]"
          placeholder={isCloze ? 'Extra (optional)' : 'Back (Answer/Recall Target)'}
          value={back}
          onChange={(e) => setBack(e.target.value)}
          required={!isCloze}
        />

        {/* Atomicity Issues & AI Decomposition Helper */}
        {atomicity && !atomicity.is_atomic && (
          <div className="rounded-lg border border-amber-500/30 bg-amber-500/10 p-3 space-y-2 text-xs">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <p className="font-semibold text-amber-200">
                🧠 Memory Athlete Advice: Non-atomic cards cause retrieval interference &amp; slower reaction times.
              </p>
              <button
                type="button"
                className="rounded border border-amber-500/40 bg-amber-500/20 px-2.5 py-1 text-xs font-medium text-amber-100 hover:bg-amber-500/30 transition flex items-center gap-1"
                disabled={decomposing}
                onClick={handleDecompose}
              >
                {decomposing ? '🤖 Decomposing with AI…' : '⚡ 1-Click AI Decompose'}
              </button>
            </div>
            <ul className="space-y-1 text-amber-300/90">
              {atomicity.issues.map((issue, idx) => (
                <li key={idx} className="flex items-start gap-1.5">
                  <span>·</span>
                  <span>
                    <strong>{issue.message}:</strong> {issue.suggestion}
                  </span>
                </li>
              ))}
            </ul>
          </div>
        )}

        {/* Decomposed Cards Preview */}
        {decomposedCards && decomposedCards.length > 0 && (
          <div className="rounded-lg border border-emerald-500/40 bg-emerald-500/10 p-3 space-y-3">
            <div className="flex items-center justify-between">
              <p className="text-xs font-semibold text-emerald-200">
                AI Suggested Atomic Breakdown ({decomposedCards.length} cards):
              </p>
              <button
                type="button"
                className="btn btn-primary px-2.5 py-1 text-xs"
                onClick={handleAddAllDecomposed}
                disabled={busy}
              >
                ✓ Add All {decomposedCards.length} Atomic Cards to Deck
              </button>
            </div>
            <div className="space-y-2">
              {decomposedCards.map((c, i) => (
                <div key={i} className="rounded border border-ink-line bg-ink/70 p-2.5 text-xs space-y-1">
                  <p className="text-slate-300 font-medium">Q: {c.front}</p>
                  <p className="text-emerald-300">A: {c.back}</p>
                </div>
              ))}
            </div>
          </div>
        )}

        <input
          className="input"
          placeholder="tags, comma separated"
          value={tags}
          onChange={(e) => setTags(e.target.value)}
        />

        {/* Card Documentation & Thematic Override */}
        <div>
          <button
            type="button"
            onClick={() => setShowDocFields((v) => !v)}
            className="text-xs text-sky-400 hover:text-sky-300 underline cursor-pointer"
          >
            {showDocFields ? 'Hide Card Documentation & Thematic Override' : '+ Card Documentation & Thematic Override'}
          </button>
          {showDocFields && (
            <div className="mt-2 space-y-2 rounded-lg border border-ink-line bg-ink/50 p-3 text-xs">
              <div>
                <label className="block text-slate-400 font-medium mb-1">
                  Card-Specific Thematic Nature (Leave blank to inherit &ldquo;{deck?.thematic_nature || 'Deck theme'}&rdquo;)
                </label>
                <input
                  className="input w-full text-xs"
                  placeholder="Card thematic override"
                  value={cardThematicNature}
                  onChange={(e) => setCardThematicNature(e.target.value)}
                />
              </div>
              <div>
                <label className="block text-slate-400 font-medium mb-1">
                  Card-Specific Documentation (Leave blank to inherit deck documentation)
                </label>
                <textarea
                  className="input w-full min-h-[3.5rem] text-xs font-mono"
                  placeholder="Card documentation notes, specific citations, or reference hooks…"
                  value={cardDocumentation}
                  onChange={(e) => setCardDocumentation(e.target.value)}
                />
              </div>
            </div>
          )}
        </div>

        <ErrorNote error={error} />
        <button className="btn btn-primary" disabled={busy}>
          {busy ? 'Adding…' : 'Add note'}
        </button>
        {isCloze && (
          <p className="text-xs text-slate-600">
            Each {'{{cN::…}}'} deletion becomes its own independently scheduled card.
          </p>
        )}
      </form>
    </Section>
  )
}

/** 🔗 Sequential Overlapping Chain Clozes (§Feature 5) */
function SequentialClozePanel({
  deckId,
  onAdded,
}: {
  deckId: string
  onAdded: () => void
}) {
  const [title, setTitle] = useState('')
  const [stepsText, setStepsText] = useState('')
  const [windowSize, setWindowSize] = useState(1)
  const [previewCards, setPreviewCards] = useState<SequentialClozeItem[]>([])
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<unknown>(null)
  const [successMsg, setSuccessMsg] = useState<string | null>(null)

  const steps = stepsText
    .split('\n')
    .map((s) => s.trim())
    .filter(Boolean)

  function handlePreview() {
    if (steps.length < 2) return
    setError(null)
    api
      .createSequentialCloze({
        title: title || 'Ordered Chain',
        steps,
        window_size: windowSize,
      })
      .then((res) => setPreviewCards(res.cards))
      .catch((err) => setError(err))
  }

  async function handleCreateChain() {
    if (steps.length < 2) return
    setBusy(true)
    setError(null)
    setSuccessMsg(null)
    try {
      const res = await api.createSequentialCloze({
        title: title || 'Ordered Chain',
        steps,
        window_size: windowSize,
        deck_id: deckId,
      })
      setSuccessMsg(`Created ${res.cards_created} sequential chain cards in this deck!`)
      setTitle('')
      setStepsText('')
      setPreviewCards([])
      onAdded()
    } catch (err) {
      setError(err)
    } finally {
      setBusy(false)
    }
  }

  return (
    <Section
      title="🔗 Sequential Chain Clozes"
      description="Memory athlete technique for ordered algorithms, protocols, cycles, and chronological events ($S_{k-1} \to [S_k] \to S_{k+1}$)."
    >
      <div className="space-y-3">
        <input
          className="input"
          placeholder="Chain Title (e.g. Krebs Cycle, CPR Protocol, Sorting Algorithm)"
          value={title}
          onChange={(e) => setTitle(e.target.value)}
        />
        <textarea
          className="input min-h-[7rem] font-mono text-sm leading-relaxed"
          placeholder={`Enter ordered steps (one per line):\n1. Glucose phosphorylation\n2. Glucose-6-phosphate isomerization\n3. Phosphofructokinase phosphorylation\n4. Fructose-1,6-bisphosphate cleavage`}
          value={stepsText}
          onChange={(e) => setStepsText(e.target.value)}
        />

        <div className="flex flex-wrap items-center justify-between gap-2">
          <div className="flex items-center gap-2 text-xs text-slate-400">
            <span>Context Window:</span>
            <button
              type="button"
              className={`chip ${windowSize === 1 ? 'border-sky-500/40 text-sky-300' : ''}`}
              onClick={() => setWindowSize(1)}
            >
              1 Prev &amp; 1 Next
            </button>
            <button
              type="button"
              className={`chip ${windowSize === 2 ? 'border-sky-500/40 text-sky-300' : ''}`}
              onClick={() => setWindowSize(2)}
            >
              2 Prev &amp; 2 Next
            </button>
          </div>

          <div className="flex items-center gap-2">
            <button
              type="button"
              className="btn"
              disabled={steps.length < 2}
              onClick={handlePreview}
            >
              👁 Preview Chain
            </button>
            <button
              type="button"
              className="btn btn-primary"
              disabled={busy || steps.length < 2}
              onClick={handleCreateChain}
            >
              {busy ? 'Creating Cards…' : `Create ${steps.length} Chain Cards`}
            </button>
          </div>
        </div>

        {successMsg && (
          <p className="rounded-lg border border-emerald-500/40 bg-emerald-500/10 p-3 text-xs text-emerald-200">
            ✓ {successMsg}
          </p>
        )}

        <ErrorNote error={error} />

        {previewCards.length > 0 && (
          <div className="space-y-2 pt-2 border-t border-ink-line">
            <p className="text-xs font-semibold text-slate-300">
              Chain Preview ({previewCards.length} cards):
            </p>
            <div className="space-y-2 max-h-64 overflow-y-auto pr-1">
              {previewCards.map((c, i) => (
                <div key={i} className="rounded border border-ink-line bg-ink/70 p-3 text-xs space-y-1.5">
                  <div className="flex items-center justify-between text-slate-500 text-[10px]">
                    <span>Step {c.step_index} of {c.total_steps}</span>
                    <span className="chip text-[10px]">Chain Cloze</span>
                  </div>
                  <p className="text-slate-200 whitespace-pre-line leading-relaxed">{c.front}</p>
                  <p className="text-emerald-300 border-t border-ink-line/50 pt-1">
                    <strong>Target:</strong> {c.back}
                  </p>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </Section>
  )
}

/** Image occlusion authoring (§14 Phase 4): upload a picture, drag masks over
 *  it, and each mask becomes an independently scheduled card. */
function AddOcclusion({ deckId, onAdded }: { deckId: string; onAdded: () => void }) {
  const [image, setImage] = useState<string | null>(null)
  const [shapes, setShapes] = useState<OcclusionShape[]>([])
  const [header, setHeader] = useState('')
  const [extra, setExtra] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<unknown>(null)
  const [open, setOpen] = useState(false)

  async function save() {
    if (!image || shapes.length === 0) return
    setBusy(true)
    setError(null)
    try {
      const types = await api.noteTypes()
      let nt = types.find((n) => n.template_kind === 'image_occlusion')
      if (!nt) {
        nt = await api.createNoteType({
          name: 'Image Occlusion',
          template_kind: 'image_occlusion',
          fields: { fields: ['Image', 'Shapes', 'Header', 'Back Extra'] },
        })
      }
      await api.createNote({
        deck_id: deckId,
        note_type_id: nt.id,
        field_values: {
          Image: image,
          Shapes: shapes,
          Header: header,
          'Back Extra': extra,
        },
      })
      setImage(null)
      setShapes([])
      setHeader('')
      setExtra('')
      onAdded()
    } catch (err) {
      setError(err)
    } finally {
      setBusy(false)
    }
  }

  if (!open) {
    return (
      <Section title="Image occlusion" description="Mask regions of a diagram; each becomes its own card.">
        <button className="btn" onClick={() => setOpen(true)}>
          Create an occlusion note
        </button>
      </Section>
    )
  }

  return (
    <Section
      title="Image occlusion"
      description="Drag over the image to mask regions. Each mask schedules independently."
      actions={
        <button className="btn px-2 py-1 text-xs" onClick={() => setOpen(false)}>
          Close
        </button>
      }
    >
      <div className="space-y-4">
        {!image ? (
          <input
            type="file"
            accept="image/*"
            disabled={busy}
            className="block w-full text-sm text-slate-400 file:mr-4 file:rounded-lg file:border-0 file:bg-sky-500/15 file:px-4 file:py-2 file:text-sm file:text-sky-200 hover:file:bg-sky-500/25"
            onChange={async (e) => {
              const file = e.target.files?.[0]
              if (!file) return
              setBusy(true)
              setError(null)
              try {
                const { url } = await api.uploadMedia(file)
                setImage(url)
              } catch (err) {
                setError(err)
              } finally {
                setBusy(false)
                e.target.value = ''
              }
            }}
          />
        ) : (
          <>
            <OcclusionEditor image={image} shapes={shapes} onChange={setShapes} />
            <input
              className="input"
              placeholder="Header shown on every card (optional)"
              value={header}
              onChange={(e) => setHeader(e.target.value)}
            />
            <input
              className="input"
              placeholder="Extra note shown on the back (optional)"
              value={extra}
              onChange={(e) => setExtra(e.target.value)}
            />
            <div className="flex flex-wrap gap-2">
              <button className="btn btn-primary" onClick={save} disabled={busy || shapes.length === 0}>
                {busy ? 'Saving…' : `Create ${shapes.length} card${shapes.length === 1 ? '' : 's'}`}
              </button>
              <button className="btn" onClick={() => { setImage(null); setShapes([]) }}>
                Use a different image
              </button>
            </div>
          </>
        )}
        <ErrorNote error={error} />
      </div>
    </Section>
  )
}

function Browser({ deckId, deck, onChange }: { deckId: string; deck?: Deck | null; onChange: () => void }) {
  const [cards, setCards] = useState<Card[]>([])
  const [search, setSearch] = useState('')
  const [loading, setLoading] = useState(true)

  const load = useCallback(async () => {
    setLoading(true)
    try {
      setCards(await api.cards({ deck_id: deckId, include_suspended: true, limit: 200 }))
    } finally {
      setLoading(false)
    }
  }, [deckId])

  useEffect(() => {
    void load()
  }, [load])

  const shown = cards.filter(
    (c) =>
      !search ||
      c.front.toLowerCase().includes(search.toLowerCase()) ||
      c.back.toLowerCase().includes(search.toLowerCase()),
  )

  return (
    <Section
      title={`Cards (${cards.length})`}
      description="Everything in this deck, including what the queue isn't showing today."
      actions={
        <input
          className="input w-56"
          placeholder="Search…"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
      }
    >
      {loading ? (
        <Spinner />
      ) : shown.length === 0 ? (
        <Empty title="No cards here yet." />
      ) : (
        <div className="space-y-2">
          {shown.map((c) => (
            <div key={c.id} className="rounded-lg border border-ink-line p-3">
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div className="min-w-0 flex-1">
                  <RichText text={c.front} className="text-sm text-slate-200" />
                  <RichText text={c.back} className="mt-1 text-sm text-slate-500" />
                </div>
                <div className="flex items-center gap-2">
                  <button
                    className="btn px-2 py-1 text-xs"
                    onClick={async () => {
                      await api.suspendCard(c.id, !c.suspended)
                      await load()
                      onChange()
                    }}
                  >
                    {c.suspended ? 'Unsuspend' : 'Suspend'}
                  </button>
                  <button
                    className="btn btn-danger px-2 py-1 text-xs"
                    onClick={async () => {
                      if (!confirm('Delete this note and all its cards?')) return
                      await api.deleteNote(c.note_id)
                      await load()
                      onChange()
                    }}
                  >
                    Delete
                  </button>
                </div>
              </div>

              <div className="mt-2 flex flex-wrap items-center gap-2 text-xs">
                {(c.thematic_nature || deck?.thematic_nature) && (
                  <span className="chip border-sky-500/40 text-sky-300 font-medium">
                    Theme: {c.thematic_nature || deck?.thematic_nature}
                  </span>
                )}
                <span className="chip">{c.state}</span>
                <span className="chip">{c.template_slot}</span>
                {c.due && <span className="chip">due {new Date(c.due).toLocaleDateString()}</span>}
                {c.stability != null && <span className="chip">S {c.stability.toFixed(1)}d</span>}
                {c.difficulty != null && <span className="chip">D {c.difficulty.toFixed(1)}</span>}
                {c.lapse_count > 0 && <span className="chip">{c.lapse_count} lapses</span>}
                {c.leech_flag && <span className="chip text-rose-300">leech</span>}
                {c.suspended && <span className="chip text-amber-300">suspended</span>}
                {c.tags.map((t) => (
                  <span key={t} className="chip">
                    #{t}
                  </span>
                ))}
                <PriorityBar value={c.priority} />
              </div>

              {(c.documentation || deck?.documentation) && (
                <div className="mt-2 text-xs border-l-2 border-slate-700/80 bg-slate-900/40 px-2.5 py-1 text-slate-400 rounded-r">
                  <span className="font-semibold text-slate-300">Documentation: </span>
                  {c.documentation || deck?.documentation}
                </div>
              )}

              {((c.source_documents && c.source_documents.length > 0) || (deck?.source_documents && deck.source_documents.length > 0)) && (
                <div className="mt-1.5 flex flex-wrap items-center gap-1.5 text-xs">
                  <span className="text-[11px] text-slate-500">Sources:</span>
                  {(c.source_documents && c.source_documents.length > 0 ? c.source_documents : deck?.source_documents || []).map((sd: any, idx: number) => (
                    <span key={idx} className="chip text-[10px] border-emerald-500/30 text-emerald-300 bg-emerald-500/5">
                      📄 {typeof sd === 'string' ? sd : sd.title || JSON.stringify(sd)}
                    </span>
                  ))}
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </Section>
  )
}

const JSON_IMPORT_EXAMPLE = `[
  { "front": "hablar", "back": "to speak", "tags": ["verbs"] },
  { "kind": "cloze", "cloze_text": "The {{c1::mitochondrion}} is the powerhouse." }
]

or wrap it: { "deck": "Spanish", "notes": [ ... ] }
or paste straight from an LLM export: { "card_type": "qa", "question": "...", "answer": "..." }

add "quote" (+ optional "locator"/"source_title") to a note to enable Learn & Practice on it`

// Paste-ready prompts for external LLM chats — kept in sync with
// docs/llm-flashcard-json-prompt.md.

export const COURSE_TEXTBOOK_PROMPT = `You are an expert Computer Science educator creating high-yield study cards from textbook and course resources.
Analyze the source material provided below and intelligently determine the best learning method for each topic:

1. If the concept is best mastered by writing code (algorithms, data structure manipulation, functions, recursion, logic):
   -> Create a CODING problem ("card_type": "code").
2. If the concept is theoretical, architectural, definitional, or system-level:
   -> Create a CONCEPTUAL flashcard ("card_type": "qa").

Language instruction:
- Use the language taught in the course material (TypeScript/JavaScript or Python). The IDE workbench sandbox supports TypeScript, JavaScript, and Python natively.
- For TypeScript: write clean typed function or class Solution signatures (e.g. 'function twoSum(nums: number[], target: number): number[]').
- For Python: write Python 3 signatures (e.g. 'def twoSum(nums: list[int], target: int) -> list[int]:').

Output ONLY a JSON array containing both types:

--- CODING CARD FORMAT ---
{
  "card_type": "code",
  "title": "<Concise problem title, e.g. 'Binary Search on Rotated Array'>",
  "category": "<e.g. Arrays, Dynamic Programming, Trees, Concurrency, Systems>",
  "difficulty": "Easy" | "Medium" | "Hard",
  "front": "<Problem statement with input/output format, examples, and constraints>",
  "starter_code": "<TypeScript or Python function signature and boilerplate for the student to write>",
  "back": "<Optimal TypeScript or Python solution with Time & Space complexity commentary>",
  "test_cases": [
    {"input": {"nums": [4,5,6,7,0,1,2], "target": 0}, "expected": 4},
    {"input": {"nums": [4,5,6,7,0,1,2], "target": 3}, "expected": -1}
  ],
  "time_complexity": "O(log n)",
  "space_complexity": "O(1)",
  "edge_cases": ["Target not found", "Single element array", "Array rotated at 0"],
  "quote": "<1-4 sentence textbook excerpt explaining the underlying algorithm or principle>",
  "locator": "<Chapter/Section/Page>"
}

--- CONCEPTUAL CARD FORMAT ---
{
  "card_type": "qa",
  "front": "<Clear, checkable conceptual question>",
  "back": "<Accurate, complete explanation with essential terminology>",
  "quote": "<Verbatim excerpt from the textbook explaining this principle>",
  "locator": "<Chapter/Section/Page>",
  "tags": ["<topic>"]
}

Rules:
- Intelligently classify: Use "code" for algorithms/coding logic; use "qa" for definitions/theorems/concepts.
- "quote" is REQUIRED on every card. It powers the Pre-Answer Primer ("Review Related Content") and reference reading citations.
- "back" on both types must be precise and comprehensive so the automated LLM grader can highlight any overlooked points.
- Provide 2-4 realistic "test_cases" on every coding card so it can execute in the sandbox.

Material to process:
<PASTE YOUR TEXTBOOK CHAPTER / NOTES HERE>`

export const CODING_ONLY_PROMPT = `You are generating LeetCode-style coding problems for an IDE spaced-repetition app. The user writes and executes code in an IDE sandbox supporting TypeScript, JavaScript, and Python.

Output ONLY a JSON array where each element is an executable coding problem in the course's target language (TypeScript or Python):

{
  "card_type": "code",
  "title": "<Problem title>",
  "category": "<e.g., Arrays & Hashing, Two Pointers, Trees, Dynamic Programming>",
  "difficulty": "Easy" | "Medium" | "Hard",
  "front": "<Problem statement with input/output format, examples, and constraints>",
  "starter_code": "<TypeScript function signature (e.g. function solve(...): ReturnType) or Python signature>",
  "back": "<Optimal solution in TypeScript or Python with Time & Space complexity commentary>",
  "test_cases": [
    {"input": {...}, "expected": ...},
    {"input": {...}, "expected": ...}
  ],
  "time_complexity": "O(n)",
  "space_complexity": "O(1)",
  "edge_cases": ["Empty input", "Negative values", "Duplicates"],
  "quote": "<1-4 sentence excerpt explaining the core algorithmic pattern>",
  "locator": "<section or chapter>"
}

Generate coding problems from the material below:
<PASTE YOUR TOPIC / PROBLEM LIST HERE>`

export const LLM_PROMPT = `You are generating flashcards for a spaced-repetition app. The user types a full answer from memory (not multiple choice), so cards must have one clear, checkable answer with essential terminology — not vague or multi-part.

Output ONLY a JSON array, no prose before or after. Each element is one card:

Basic (question/answer):
{
  "front": "<question, one clear fact or concept>",
  "back": "<the complete answer containing key terms and core concept>",
  "quote": "<1-4 sentence excerpt from the source that explains this fact>",
  "locator": "<section/heading/page this came from, if known>",
  "source_title": "<title of the source material>",
  "tags": ["<topic>"]
}

Cloze (fill-in-the-blank, for terms/definitions embedded in a sentence):
{
  "kind": "cloze",
  "cloze_text": "<sentence with the key term wrapped like {{c1::term}}>",
  "back": "<extra context shown after grading, optional>",
  "quote": "<1-4 sentence excerpt from the source this sentence is drawn from>",
  "locator": "<section/heading/page>",
  "source_title": "<title of the source material>",
  "tags": ["<topic>"]
}

Rules:
- One card = one atomic fact. Split compound facts into separate cards.
- "front"/"cloze_text" must be answerable without seeing "back" first.
- "back" should state the core answer clearly with essential terminology. The app automatically evaluates student recall against "back" and highlights any omitted or overlooked concepts.
- "quote" is REQUIRED on every card. It powers the Pre-Answer Primer ("Review Related Content") and reference reading citations. Write 1-4 self-contained sentences from the source that explain the concept. During review, any concepts the student overlooks are highlighted directly in this quote!
- "locator" and "source_title" are optional but cheap — include them whenever you know where the fact came from.
- Keep "front"/"back"/"cloze_text" under ~500 characters; "quote" under ~800 characters.
- Use {{c1::x}}, {{c2::y}} for multiple deletions in one cloze sentence only when the deletions are genuinely linked; otherwise make separate cards.
- Do not invent facts. If the source doesn't support a fact, drop the card.

Generate cards from the material below:

<PASTE YOUR SOURCE TEXT / NOTES / TOPIC HERE>`

/** Bulk-create notes/cards from a hand-written or scripted JSON file — the
 *  non-Anki upload path. One request targets one deck (created if missing).
 *  Accepts a bare array (deck name comes from the field below) or an
 *  envelope with "deck" already inside it — and either "front"/"back" or the
 *  "card_type"/"question"/"answer" vocabulary common in LLM flashcard exports. */
function JsonImportPanel({ onImported }: { onImported: () => void }) {
  const [deckName, setDeckName] = useState('')
  const [text, setText] = useState('')
  const [result, setResult] = useState<JsonImportResult | null>(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<unknown>(null)
  const [open, setOpen] = useState(false)
  const [promptCopied, setPromptCopied] = useState(false)

  async function copyPrompt() {
    await navigator.clipboard.writeText(LLM_PROMPT)
    setPromptCopied(true)
    setTimeout(() => setPromptCopied(false), 2000)
  }

  async function submit() {
    setBusy(true)
    setError(null)
    setResult(null)
    try {
      const parsed = JSON.parse(text)
      if (Array.isArray(parsed)) {
        if (!deckName.trim()) throw new ApiError(400, 'Enter a deck name for this import.')
        setResult(await api.importJson(parsed, deckName.trim()))
      } else {
        // An explicit deck name in the field overrides one already in the
        // JSON, so re-uploading the same file into a different deck needs no
        // hand-editing.
        setResult(await api.importJson({ ...parsed, deck: deckName.trim() || parsed.deck }))
      }
      onImported()
    } catch (err) {
      setError(err instanceof SyntaxError ? new ApiError(400, `Invalid JSON: ${err.message}`) : err)
    } finally {
      setBusy(false)
    }
  }

  if (!open) {
    return (
      <Section title="Import from JSON" description="Bulk-create notes from a JSON file — no Anki required.">
        <div className="flex flex-wrap items-center gap-3">
          <button className="btn" onClick={() => setOpen(true)}>
            Paste or upload JSON
          </button>
          <button
            className="btn btn-secondary flex items-center gap-1.5 text-xs"
            onClick={copyPrompt}
            title="Copy prompt for ChatGPT/Claude/Gemini"
          >
            <span>{promptCopied ? '✓' : '📋'}</span>
            <span>{promptCopied ? 'Copied prompt!' : 'Quick copy LLM prompt'}</span>
          </button>
        </div>
      </Section>
    )
  }

  return (
    <Section
      title="Import from JSON"
      description="One deck per upload (created if it doesn't exist). A bare array of notes works, and question/answer-style fields from LLM exports are understood too."
      actions={
        <button className="btn px-2 py-1 text-xs" onClick={() => setOpen(false)}>
          Close
        </button>
      }
    >
      <div className="space-y-3">
        <div className="flex items-center justify-between gap-3 rounded-lg border border-ink-line bg-ink p-3">
          <p className="text-xs text-slate-400">
            No cards yet? Copy a ready-made prompt for ChatGPT/Claude/Gemini that writes the JSON
            for you — including citations for Learn &amp; Practice.
          </p>
          <button className="btn shrink-0 px-2 py-1 text-xs" onClick={copyPrompt}>
            {promptCopied ? 'Copied!' : 'Copy LLM prompt'}
          </button>
        </div>
        <input
          className="input"
          placeholder="Deck name (required for a bare array; overrides one already in the JSON)"
          value={deckName}
          onChange={(e) => setDeckName(e.target.value)}
        />
        <input
          type="file"
          accept=".json,application/json"
          disabled={busy}
          className="block w-full text-sm text-slate-400 file:mr-4 file:rounded-lg file:border-0 file:bg-sky-500/15 file:px-4 file:py-2 file:text-sm file:text-sky-200 hover:file:bg-sky-500/25"
          onChange={async (e) => {
            const file = e.target.files?.[0]
            if (!file) return
            setText(await file.text())
            if (!deckName.trim()) setDeckName(file.name.replace(/\.json$/i, ''))
            e.target.value = ''
          }}
        />
        <textarea
          className="input min-h-[10rem] font-mono text-xs"
          placeholder={JSON_IMPORT_EXAMPLE}
          value={text}
          onChange={(e) => setText(e.target.value)}
        />
        <button className="btn btn-primary" onClick={submit} disabled={busy || !text.trim()}>
          {busy ? 'Importing…' : 'Import'}
        </button>
        <ErrorNote error={error} />

        {result && (
          <div className="space-y-3">
            <div className="flex flex-wrap gap-2 text-xs">
              <span className="chip">
                {result.deck_created ? 'created' : 'reused'} deck
              </span>
              <span className="chip">{result.notes_created} notes</span>
              <span className="chip">{result.cards_created} cards</span>
              {result.citations_created > 0 && (
                <span className="chip text-sky-300">
                  {result.citations_created} with Learn &amp; Practice
                </span>
              )}
            </div>
            {result.warnings.length > 0 && (
              <div className="rounded-lg border border-amber-500/40 bg-amber-500/10 p-4">
                <p className="text-xs font-semibold uppercase tracking-wide text-amber-200">
                  Skipped rows
                </p>
                <ul className="mt-2 space-y-1.5 text-sm text-amber-100/90">
                  {result.warnings.map((w, i) => (
                    <li key={i}>· {w}</li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        )}
      </div>
    </Section>
  )
}

function LlmPromptPanel() {
  const [copied, setCopied] = useState(false)
  const [expanded, setExpanded] = useState(false)
  const [promptCategory, setPromptCategory] = useState<'course' | 'code' | 'general'>('course')

  const activePrompt =
    promptCategory === 'course'
      ? COURSE_TEXTBOOK_PROMPT
      : promptCategory === 'code'
      ? CODING_ONLY_PROMPT
      : LLM_PROMPT

  async function handleCopy() {
    await navigator.clipboard.writeText(activePrompt)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  return (
    <Section
      title="Prompts for LLM Deck & Course Creation"
      description="Copy these prompts into ChatGPT, Claude, Gemini, or DeepSeek along with your textbook or course resources to create flashcards and LeetCode-style coding problems."
      actions={
        <button
          onClick={handleCopy}
          className="btn btn-primary flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold"
          title="Copy selected prompt to clipboard"
        >
          <span>{copied ? '✓' : '📋'}</span>
          <span>{copied ? 'Prompt Copied!' : 'Quick Copy Selected Prompt'}</span>
        </button>
      }
    >
      <div className="space-y-3">
        {/* Category Tabs */}
        <div className="flex flex-wrap items-center gap-2 border-b border-ink-line/80 pb-2">
          <button
            type="button"
            onClick={() => setPromptCategory('course')}
            className={`flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs font-medium transition ${
              promptCategory === 'course'
                ? 'border border-sky-500/50 bg-sky-500/20 text-sky-200 font-semibold'
                : 'border border-transparent text-slate-400 hover:text-slate-200'
            }`}
          >
            <span>🎓</span>
            <span>Textbook &amp; Course (Auto-Classifies Code vs Theory)</span>
          </button>

          <button
            type="button"
            onClick={() => setPromptCategory('code')}
            className={`flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs font-medium transition ${
              promptCategory === 'code'
                ? 'border border-emerald-500/50 bg-emerald-500/20 text-emerald-200 font-semibold'
                : 'border border-transparent text-slate-400 hover:text-slate-200'
            }`}
          >
            <span>💻</span>
            <span>LeetCode Coding Problems Only</span>
          </button>

          <button
            type="button"
            onClick={() => setPromptCategory('general')}
            className={`flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs font-medium transition ${
              promptCategory === 'general'
                ? 'border border-indigo-500/50 bg-indigo-500/20 text-indigo-200 font-semibold'
                : 'border border-transparent text-slate-400 hover:text-slate-200'
            }`}
          >
            <span>🗂️</span>
            <span>General Flashcards Only</span>
          </button>
        </div>

        <div className="flex flex-wrap items-center justify-between gap-3 rounded-lg border border-ink-line/80 bg-ink-soft/40 p-3 text-xs text-slate-300">
          <div className="space-y-1">
            <span className="font-semibold text-slate-200">How to use:</span>
            <ol className="list-decimal list-inside text-slate-400 space-y-0.5">
              <li>Click <strong>Quick Copy Selected Prompt</strong> above.</li>
              <li>Paste it into any LLM chat (ChatGPT, Claude, Gemini, DeepSeek, etc.).</li>
              <li>Paste your textbook chapter, slides, or course notes at the bottom.</li>
              <li>Paste the generated JSON directly into <strong>Import from JSON</strong> above.</li>
            </ol>
          </div>
          <button
            onClick={() => setExpanded((e) => !e)}
            className="text-xs text-sky-400 hover:text-sky-300 transition font-medium self-start sm:self-center"
          >
            {expanded ? '▲ Hide Prompt Preview' : '▼ View Prompt Text'}
          </button>
        </div>

        {expanded && (
          <div className="relative rounded-lg border border-ink-line/80 bg-[#0d1117] p-3 text-xs font-mono text-slate-300">
            <div className="flex justify-between items-center mb-2 pb-2 border-b border-ink-line/40">
              <span className="text-[11px] text-slate-400 font-sans">
                {promptCategory === 'course'
                  ? '🎓 Hybrid Textbook Prompt (Auto-Classify Code vs Theory):'
                  : promptCategory === 'code'
                  ? '💻 Pure LeetCode Coding Problem Prompt:'
                  : '🗂️ Standard Flashcard Prompt:'}
              </span>
              <button
                onClick={handleCopy}
                className="btn btn-secondary px-2.5 py-0.5 text-[11px]"
              >
                {copied ? '✓ Copied' : 'Copy'}
              </button>
            </div>
            <pre className="whitespace-pre-wrap leading-relaxed select-all max-h-96 overflow-y-auto pr-2">
              {activePrompt}
            </pre>
          </div>
        )}
      </div>
    </Section>
  )
}

