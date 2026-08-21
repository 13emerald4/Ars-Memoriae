import { useCallback, useEffect, useState } from 'react'
import { api, ApiError } from '../api/client'
import type {
  AcceptDeckResponse,
  AtomicityLintResult,
  Card,
  Deck,
  DecomposedCardItem,
  DocumentUpload,
  GenerateDeckResponse,
  ImportResult,
  JsonImportResult,
  NoteType,
  OcclusionShape,
  SequentialClozeItem,
} from '../api/types'
import { OcclusionEditor } from '../components/Occlusion'
import { Empty, ErrorNote, PriorityBar, RichText, Section, Spinner } from '../components/ui'

export default function Decks() {
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

  if (loading) return <Spinner />

  return (
    <div className="space-y-6">
      <ErrorNote error={error} />
      <DeckList decks={decks} selected={selected} onSelect={setSelected} onChange={load} />
      {selected && (
        <>
          <AddNote deckId={selected} noteTypes={noteTypes} onAdded={load} />
          <SequentialClozePanel deckId={selected} onAdded={load} />
          <AddOcclusion deckId={selected} onAdded={load} />
          <Browser deckId={selected} onChange={load} />
        </>
      )}
      <DocumentDeckPanel onImported={load} />
      <ImportPanel onImported={load} />
      <JsonImportPanel onImported={load} />
    </div>
  )
}

/** Upload a document -> the model proposes cards that each cite the passage
 *  they came from -> you approve -> the citations are kept and shown during
 *  review, after you answer. Nothing is written until you accept. */
const GENERATION_MODELS = [
  { id: 'gemini-2.5-flash', name: 'Gemini 2.5 Flash', badge: 'Recommended (Fast)' },
  { id: 'gemini-2.0-flash', name: 'Gemini 2.0 Flash', badge: 'Fast & High Quota' },
  { id: 'gemini-2.0-flash-lite', name: 'Gemini 2.0 Flash Lite', badge: 'Max Throughput' },
  { id: 'gemini-3.7-flash', name: 'Gemini 3.7 Flash', badge: 'Hybrid Preview' },
  { id: 'gemini-2.5-pro', name: 'Gemini 2.5 Pro', badge: 'Frontier Reasoning' },
  { id: 'gemini-2.0-pro-exp-02-05', name: 'Gemini 2.0 Pro Exp', badge: 'Deep Reasoning' },
]

const THINKING_LEVELS = [
  { id: 'dynamic', label: 'Dynamic (Default)', budget: undefined, hint: 'Model decides' },
  { id: 'off', label: 'Off (0 tokens)', budget: 0, hint: 'Fastest output' },
  { id: 'low', label: 'Low (1k tokens)', budget: 1024, hint: 'Quick checks' },
  { id: 'med', label: 'Medium (2k tokens)', budget: 2048, hint: 'Balanced' },
  { id: 'high', label: 'High (8k tokens)', budget: 8192, hint: 'Complex STEM/proofs' },
]

function DocumentDeckPanel({ onImported }: { onImported: () => void }) {
  const [doc, setDoc] = useState<DocumentUpload | null>(null)
  const [deckName, setDeckName] = useState('')
  const [selectedModel, setSelectedModel] = useState('gemini-2.5-flash')
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
      setAccepted(await api.acceptDeck(doc.source_id, deckName.trim() || doc.title, cards))
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
                : generated.reason === 'no_api_key'
                  ? 'Add a Google API key in Settings to generate cards.'
                  : `Card generation was temporarily unavailable (${generated.reason}).`}
            </p>
            {generated.warnings.length > 0 && (
              <p className="mt-1.5 text-xs text-amber-300/80">
                Details: {generated.warnings[0]}
              </p>
            )}
            <p className="mt-2 text-xs text-slate-400">
              Free-tier or preview models (like Gemini 3.7 Flash) may experience brief capacity spikes. Click &ldquo;Retry generating cards&rdquo; above or select a different model in Settings.
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
  const [name, setName] = useState('')
  const [busy, setBusy] = useState(false)

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
      description="Per-deck priority and retention are the “% bias per subject” controls."
      actions={
        <div className="flex flex-wrap items-center gap-2">
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
          <form
            className="flex gap-2"
            onSubmit={async (e) => {
              e.preventDefault()
              if (!name.trim()) return
              setBusy(true)
              try {
                await api.createDeck({ name: name.trim() })
                setName('')
                onChange()
              } finally {
                setBusy(false)
              }
            }}
          >
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
        </div>
      }
    >
      <div className="space-y-2">
        {decks.length === 0 ? (
          <p className="text-xs text-slate-500 py-2">No decks created yet. Add one above or import a document.</p>
        ) : (
          decks.map((d) => (
            <div
              key={d.id}
              className={`flex flex-wrap items-center justify-between gap-3 rounded-lg border p-3 transition ${
                selected === d.id ? 'border-sky-500/40 bg-sky-500/5' : 'border-ink-line'
              }`}
            >
              <button className="min-w-0 flex-1 text-left" onClick={() => onSelect(d.id)}>
                <p className="font-medium text-slate-200">{d.name}</p>
                <p className="mt-1 flex flex-wrap gap-2 text-xs text-slate-500">
                  <span className="chip">{d.card_count} cards</span>
                  <span className="chip">{d.due_count} due</span>
                  <span className="chip">{d.new_count} new</span>
                </p>
              </button>

              <div className="flex flex-wrap items-center gap-3">
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
  onAdded,
}: {
  deckId: string
  noteTypes: NoteType[]
  onAdded: () => void
}) {
  const [noteTypeId, setNoteTypeId] = useState(noteTypes[0]?.id ?? '')
  const [front, setFront] = useState('')
  const [back, setBack] = useState('')
  const [clozeText, setClozeText] = useState('')
  const [tags, setTags] = useState('')
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
        })
      }
      setFront('')
      setBack('')
      setDecomposedCards(null)
      setAtomicity(null)
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
      })
      setFront('')
      setBack('')
      setClozeText('')
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

function Browser({ deckId, onChange }: { deckId: string; onChange: () => void }) {
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
            </div>
          ))}
        </div>
      )}
    </Section>
  )
}

function ImportPanel({ onImported }: { onImported: () => void }) {
  const [result, setResult] = useState<ImportResult | null>(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<unknown>(null)

  return (
    <Section
      title="Import from Anki"
      description="Upload a .apkg. Review history is replayed through FSRS so years of scheduling signal aren't lost."
    >
      <input
        type="file"
        accept=".apkg,.colpkg"
        disabled={busy}
        className="block w-full text-sm text-slate-400 file:mr-4 file:rounded-lg file:border-0 file:bg-sky-500/15 file:px-4 file:py-2 file:text-sm file:text-sky-200 hover:file:bg-sky-500/25"
        onChange={async (e) => {
          const file = e.target.files?.[0]
          if (!file) return
          setBusy(true)
          setError(null)
          setResult(null)
          try {
            setResult(await api.importApkg(file))
            onImported()
          } catch (err) {
            setError(err)
          } finally {
            setBusy(false)
            e.target.value = ''
          }
        }}
      />
      {busy && <div className="mt-3"><Spinner label="Parsing collection and replaying history…" /></div>}
      <ErrorNote error={error} />

      {result && (
        <div className="mt-4 space-y-3">
          <div className="flex flex-wrap gap-2 text-xs">
            <span className="chip">{result.notes_mapped} notes</span>
            <span className="chip">{result.cards_mapped} cards</span>
            <span className="chip">{result.review_logs_mapped} reviews replayed</span>
            <span className="chip">{result.decks_created} decks</span>
            {result.media_copied > 0 && <span className="chip">{result.media_copied} media</span>}
          </div>
          {/* §11 & §15: the warnings list must be genuinely visible, not buried. */}
          {result.warnings.length > 0 && (
            <div className="rounded-lg border border-amber-500/40 bg-amber-500/10 p-4">
              <p className="text-xs font-semibold uppercase tracking-wide text-amber-200">
                What didn't map cleanly
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

// Paste-ready prompt for an external LLM chat — kept in sync with
// docs/llm-flashcard-json-prompt.md. Requires "quote" on every card so the
// import creates a citation, which is what Learn & Practice teaches from.
const LLM_PROMPT = `You are generating flashcards for a spaced-repetition app. The user types a full answer from memory (not multiple choice), so cards must have one clear, checkable answer — not vague or multi-part.

Output ONLY a JSON array, no prose before or after. Each element is one card:

Basic (question/answer):
{
  "front": "<question, one fact>",
  "back": "<the answer>",
  "quote": "<1-4 sentence excerpt from the source that states this fact>",
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
- "quote" is REQUIRED on every card. It's what the app teaches from before quizzing (Learn & Practice) — write it as a short, self-contained explanation of the fact, not just the bare answer restated. If you're working from a source document, quote it directly; if you're writing from general knowledge, write 1-4 sentences that would teach a newcomer the concept.
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
        <button className="btn" onClick={() => setOpen(true)}>
          Paste or upload JSON
        </button>
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
