import { useCallback, useEffect, useState } from 'react'
import { api } from '../api/client'
import type { Card, Deck, ImportResult, NoteType, OcclusionShape } from '../api/types'
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
          <AddOcclusion deckId={selected} onAdded={load} />
          <Browser deckId={selected} onChange={load} />
        </>
      )}
      <ImportPanel onImported={load} />
    </div>
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

  return (
    <Section
      title="Decks"
      description="Per-deck priority and retention are the “% bias per subject” controls."
      actions={
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
            className="input w-44"
            placeholder="New deck"
            value={name}
            onChange={(e) => setName(e.target.value)}
          />
          <button className="btn" disabled={busy}>
            Add
          </button>
        </form>
      }
    >
      <div className="space-y-2">
        {decks.map((d) => (
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

            <div className="flex items-center gap-4">
              <label className="flex items-center gap-2 text-xs text-slate-500">
                priority
                <input
                  type="range"
                  min={0}
                  max={100}
                  defaultValue={d.default_priority}
                  className="w-28"
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
                  className="input w-24 py-1 text-xs"
                  onBlur={async (e) => {
                    const raw = e.target.value.trim()
                    await api.updateDeck(d.id, {
                      desired_retention_override: raw ? Number(raw) : null,
                    })
                    onChange()
                  }}
                />
              </label>
            </div>
          </div>
        ))}
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

  const noteType = noteTypes.find((n) => n.id === noteTypeId) ?? noteTypes[0]
  const isCloze = noteType?.template_kind === 'cloze'

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
        <select className="input" value={noteTypeId} onChange={(e) => setNoteTypeId(e.target.value)}>
          {noteTypes.map((n) => (
            <option key={n.id} value={n.id}>
              {n.name} · {n.template_kind} · {n.grading_profile}
            </option>
          ))}
        </select>

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
            placeholder="Front"
            value={front}
            onChange={(e) => setFront(e.target.value)}
            required
          />
        )}
        <textarea
          className="input min-h-[4rem]"
          placeholder={isCloze ? 'Extra (optional)' : 'Back'}
          value={back}
          onChange={(e) => setBack(e.target.value)}
          required={!isCloze}
        />
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
