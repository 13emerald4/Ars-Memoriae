import { useCallback, useEffect, useRef, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { api } from '../api/client'
import type { Deck, Extract, Source, SuggestedCard } from '../api/types'
import { Empty, ErrorNote, Section, Spinner } from '../components/ui'

/** Incremental Reading (§8): import material, resurface it on a schedule, and
 *  carve cards out of it as understanding builds. */
export default function Read() {
  const { extractId } = useParams()
  return extractId ? <ExtractWorkspace extractId={extractId} /> : <SourceLibrary />
}

// ── library ─────────────────────────────────────────────────────────────────

function SourceLibrary() {
  const navigate = useNavigate()
  const [sources, setSources] = useState<Source[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<unknown>(null)
  const [mode, setMode] = useState<'text' | 'url'>('text')
  const [title, setTitle] = useState('')
  const [text, setText] = useState('')
  const [url, setUrl] = useState('')
  const [priority, setPriority] = useState(50)
  const [busy, setBusy] = useState(false)

  const load = useCallback(async () => {
    setLoading(true)
    try {
      setSources(await api.sources())
    } catch (err) {
      setError(err)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    void load()
  }, [load])

  async function add(e: React.FormEvent) {
    e.preventDefault()
    setBusy(true)
    setError(null)
    try {
      await api.createSource(
        mode === 'url'
          ? { url, title: title || undefined, priority }
          : { raw_text: text, title: title || undefined, priority },
      )
      setTitle('')
      setText('')
      setUrl('')
      await load()
    } catch (err) {
      setError(err)
    } finally {
      setBusy(false)
    }
  }

  async function openNext(source: Source) {
    const extracts = await api.extractsOf(source.id)
    const next = extracts.find((e) => e.status === 'active')
    if (next) navigate(`/read/${next.id}`)
  }

  return (
    <div className="space-y-6">
      <Section
        title="Add reading material"
        description="Paste text or a URL. It's split into extracts that resurface on a schedule — you never have to finish an article in one sitting."
      >
        <form onSubmit={add} className="space-y-3">
          <div className="flex gap-2">
            {(['text', 'url'] as const).map((m) => (
              <button
                key={m}
                type="button"
                className={`btn ${mode === m ? 'btn-primary' : ''}`}
                onClick={() => setMode(m)}
              >
                {m === 'text' ? 'Paste text' : 'From URL'}
              </button>
            ))}
          </div>

          <input
            className="input"
            placeholder="Title (optional)"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
          />

          {mode === 'text' ? (
            <textarea
              className="input min-h-[8rem] resize-y"
              placeholder="Paste an article, chapter, or set of notes…"
              value={text}
              onChange={(e) => setText(e.target.value)}
              required
            />
          ) : (
            <input
              className="input"
              type="url"
              placeholder="https://example.com/article"
              value={url}
              onChange={(e) => setUrl(e.target.value)}
              required
            />
          )}

          <div className="flex flex-wrap items-center gap-4">
            <label className="flex items-center gap-3 text-xs text-slate-500">
              Priority
              <input
                type="range"
                min={0}
                max={100}
                value={priority}
                onChange={(e) => setPriority(Number(e.target.value))}
                className="w-40"
              />
              <span className="tabular-nums text-slate-300">{priority}</span>
            </label>
            <button className="btn btn-primary" disabled={busy}>
              {busy ? 'Importing…' : 'Import'}
            </button>
          </div>
        </form>
        <ErrorNote error={error} />
      </Section>

      {loading ? (
        <Spinner />
      ) : sources.length === 0 ? (
        <Empty title="No reading material yet.">
          Incremental reading is what Anki doesn't do: keep sources in the same queue as your
          cards, and turn them into cards gradually.
        </Empty>
      ) : (
        <div className="space-y-2">
          {sources.map((s) => (
            <div key={s.id} className="card flex flex-wrap items-center justify-between gap-4">
              <div className="min-w-0">
                <p className="truncate font-medium text-slate-200">{s.title}</p>
                <p className="mt-1 flex flex-wrap gap-2 text-xs text-slate-500">
                  <span className="chip">{s.active_extract_count} left</span>
                  <span className="chip">{s.extract_count} extracts</span>
                  <span className="chip">priority {s.priority}</span>
                  <span className="chip">{s.status}</span>
                  {!s.for_reading && (
                    <span
                      className="chip text-slate-500"
                      title="Uploaded for card generation — never auto-surfaced in Review"
                    >
                      reference only
                    </span>
                  )}
                  {s.url && (
                    <a
                      href={s.url}
                      target="_blank"
                      rel="noreferrer"
                      className="chip hover:text-sky-300"
                    >
                      source ↗
                    </a>
                  )}
                </p>
              </div>
              <div className="flex gap-2">
                <button
                  className="btn"
                  disabled={s.active_extract_count === 0}
                  onClick={() => openNext(s)}
                >
                  Read next
                </button>
                <button
                  className="btn btn-danger"
                  onClick={async () => {
                    if (!confirm(`Delete "${s.title}"? Cards made from it are kept.`)) return
                    await api.deleteSource(s.id)
                    await load()
                  }}
                >
                  Delete
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

// ── the extract workspace ───────────────────────────────────────────────────

const GENERATION_MODELS = [
  { id: 'qwen2.5-coder:7b', name: 'Qwen 2.5 Coder (7B Instruct)', badge: 'Local Engine' },
]

const THINKING_LEVELS = [
  { id: 'dynamic', label: 'Default', budget: undefined },
]

function ExtractWorkspace({ extractId }: { extractId: string }) {
  const navigate = useNavigate()
  const [extract, setExtract] = useState<Extract | null>(null)
  const [decks, setDecks] = useState<Deck[]>([])
  const [deckId, setDeckId] = useState('')
  const [selectedModel, setSelectedModel] = useState('qwen2.5-coder:7b')
  const [selectedThinking, setSelectedThinking] = useState('dynamic')
  const [selection, setSelection] = useState('')
  const [suggestions, setSuggestions] = useState<SuggestedCard[]>([])
  const [chosen, setChosen] = useState<Set<number>>(new Set())
  const [notice, setNotice] = useState<string | null>(null)
  const [error, setError] = useState<unknown>(null)
  const [busy, setBusy] = useState<string | null>(null)
  const bodyRef = useRef<HTMLDivElement>(null)

  const load = useCallback(async () => {
    try {
      const [e, d] = await Promise.all([api.extract(extractId), api.decks()])
      setExtract(e)
      setDecks(d)
      setDeckId((prev) => prev || d[0]?.id || '')
    } catch (err) {
      setError(err)
    }
  }, [extractId])

  useEffect(() => {
    void load()
  }, [load])

  function captureSelection() {
    const sel = window.getSelection()?.toString().trim() ?? ''
    if (sel) setSelection(sel)
  }

  async function split() {
    if (!selection) return
    setBusy('split')
    setError(null)
    try {
      await api.splitExtract(extractId, { text: selection })
      setSelection('')
      setNotice('Extract carved out — it will resurface on its own schedule.')
      await load()
    } catch (err) {
      setError(err)
    } finally {
      setBusy(null)
    }
  }

  async function suggest() {
    setBusy('suggest')
    setError(null)
    setSuggestions([])
    const thinkingBudget = THINKING_LEVELS.find((t) => t.id === selectedThinking)?.budget
    try {
      const resp = await api.generateCards(extractId, {
        text: selection || undefined,
        max_cards: 5,
        model: selectedModel,
        thinking_budget: thinkingBudget,
      })
      if (resp.degraded) {
        setNotice(
          resp.reason === 'consent_not_given' || resp.reason === 'no_api_key'
            ? 'Card generation needs a Google API key and consent — see Settings. You can still make cards by hand below.'
            : `Card generation unavailable (${resp.reason}). Make them by hand below.`,
        )
      } else {
        setSuggestions(resp.suggestions)
        setChosen(new Set(resp.suggestions.map((_, i) => i)))
        if (resp.suggestions.length === 0) setNotice('The model found nothing worth carding here.')
      }
    } catch (err) {
      setError(err)
    } finally {
      setBusy(null)
    }
  }

  function makeClozeFromSelection() {
    if (!selection || !extract) return
    // Manual highlight-to-cloze: blank the selection inside its sentence.
    const sentence =
      extract.content
        .split(/(?<=[.!?])\s+/)
        .find((s) => s.includes(selection)) ?? extract.content.slice(0, 300)
    setSuggestions((prev) => [
      ...prev,
      {
        kind: 'cloze',
        front: '',
        back: '',
        cloze_text: sentence.replace(selection, `{{c1::${selection}}}`),
      },
    ])
    setChosen((prev) => new Set(prev).add(suggestions.length))
  }

  async function accept() {
    const cards = suggestions.filter((_, i) => chosen.has(i))
    if (cards.length === 0 || !deckId) return
    setBusy('accept')
    try {
      const { cards_created } = await api.acceptCards(extractId, deckId, cards)
      setSuggestions([])
      setChosen(new Set())
      setNotice(`${cards_created} card${cards_created === 1 ? '' : 's'} created.`)
      await load()
    } catch (err) {
      setError(err)
    } finally {
      setBusy(null)
    }
  }

  if (!extract) return <Spinner />

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex flex-wrap items-center gap-2">
          <button className="btn" onClick={() => navigate('/read')}>
            ← Library
          </button>
          <span className="chip">{extract.source_title}</span>
          <span className="chip">priority {extract.priority}</span>
        </div>
        <div className="flex gap-2">
          <button
            className="btn"
            onClick={async () => {
              await api.scheduleExtract(extractId, { days: 3 })
              navigate('/read')
            }}
          >
            Postpone 3d
          </button>
          <button
            className="btn"
            onClick={async () => {
              await api.scheduleExtract(extractId, { status: 'done' })
              navigate('/read')
            }}
          >
            Mark done
          </button>
        </div>
      </div>

      <div className="card">
        <p className="label">Select any passage to split it off or turn it into cards</p>
        <div
          ref={bodyRef}
          onMouseUp={captureSelection}
          onKeyUp={captureSelection}
          className="max-h-[30rem] select-text overflow-y-auto whitespace-pre-wrap text-[15px] leading-7 text-slate-200"
        >
          {extract.content}
        </div>
      </div>

      {selection && (
        <div className="card border-sky-500/30">
          <p className="label">Selected</p>
          <p className="text-sm italic text-slate-300">"{selection}"</p>
          <div className="mt-4 flex flex-wrap gap-2">
            <button className="btn" onClick={split} disabled={busy === 'split'}>
              {busy === 'split' ? 'Splitting…' : 'Split into its own extract'}
            </button>
            <button className="btn" onClick={makeClozeFromSelection}>
              Make a cloze from it
            </button>
            <button className="btn btn-primary" onClick={suggest} disabled={busy === 'suggest'}>
              {busy === 'suggest' ? 'Thinking…' : 'LLM assist: suggest cards'}
            </button>
            <button className="btn" onClick={() => setSelection('')}>
              Clear
            </button>
          </div>
        </div>
      )}

      <div className="flex flex-wrap items-center justify-between gap-3 rounded-lg border border-ink-line bg-ink/30 p-3 text-xs">
        <div className="flex flex-wrap items-center gap-3">
          <div className="flex items-center gap-1.5">
            <span className="text-slate-400 font-medium">Model:</span>
            <select
              className="input py-1 text-xs"
              value={selectedModel}
              onChange={(e) => setSelectedModel(e.target.value)}
            >
              {GENERATION_MODELS.map((m) => (
                <option key={m.id} value={m.id}>
                  {m.name} ({m.badge})
                </option>
              ))}
            </select>
          </div>

          <div className="flex items-center gap-1.5">
            <span className="text-slate-400 font-medium">Thinking:</span>
            <select
              className="input py-1 text-xs"
              value={selectedThinking}
              onChange={(e) => setSelectedThinking(e.target.value)}
            >
              {THINKING_LEVELS.map((t) => (
                <option key={t.id} value={t.id}>
                  {t.label}
                </option>
              ))}
            </select>
          </div>
        </div>

        {!selection && (
          <button className="btn btn-primary text-xs" onClick={suggest} disabled={busy === 'suggest'}>
            {busy === 'suggest' ? 'Thinking…' : 'LLM assist: suggest cards from this whole extract'}
          </button>
        )}
      </div>

      {notice && (
        <p className="rounded-lg border border-sky-500/25 bg-sky-500/5 px-4 py-3 text-sm text-sky-200/90">
          {notice}
        </p>
      )}
      <ErrorNote error={error} />

      {suggestions.length > 0 && (
        <Section
          title="Proposed cards"
          description="Nothing becomes a card until you accept it — same as grading."
          actions={
            <div className="flex items-center gap-2">
              <select className="input w-auto" value={deckId} onChange={(e) => setDeckId(e.target.value)}>
                {decks.map((d) => (
                  <option key={d.id} value={d.id}>
                    {d.name}
                  </option>
                ))}
              </select>
              <button className="btn btn-primary" onClick={accept} disabled={busy === 'accept'}>
                Add {chosen.size}
              </button>
            </div>
          }
        >
          <ul className="space-y-2">
            {suggestions.map((s, i) => (
              <li
                key={i}
                className={`rounded-lg border p-3 text-sm ${
                  chosen.has(i) ? 'border-sky-500/40 bg-sky-500/5' : 'border-ink-line'
                }`}
              >
                <label className="flex cursor-pointer gap-3">
                  <input
                    type="checkbox"
                    checked={chosen.has(i)}
                    onChange={() =>
                      setChosen((prev) => {
                        const next = new Set(prev)
                        next.has(i) ? next.delete(i) : next.add(i)
                        return next
                      })
                    }
                    className="mt-1"
                  />
                  <div className="min-w-0 flex-1 space-y-1">
                    <span className="chip">{s.kind}</span>
                    {s.kind === 'cloze' ? (
                      <textarea
                        className="input font-mono text-xs"
                        value={s.cloze_text ?? ''}
                        onChange={(e) =>
                          setSuggestions((prev) =>
                            prev.map((x, j) => (j === i ? { ...x, cloze_text: e.target.value } : x)),
                          )
                        }
                      />
                    ) : (
                      <div className="grid gap-2 sm:grid-cols-2">
                        <textarea
                          className="input text-xs"
                          value={s.front}
                          onChange={(e) =>
                            setSuggestions((prev) =>
                              prev.map((x, j) => (j === i ? { ...x, front: e.target.value } : x)),
                            )
                          }
                        />
                        <textarea
                          className="input text-xs"
                          value={s.back}
                          onChange={(e) =>
                            setSuggestions((prev) =>
                              prev.map((x, j) => (j === i ? { ...x, back: e.target.value } : x)),
                            )
                          }
                        />
                      </div>
                    )}
                  </div>
                </label>
              </li>
            ))}
          </ul>
        </Section>
      )}
    </div>
  )
}
