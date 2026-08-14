import { useCallback, useEffect, useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '../api/client'
import type { Card, TreeNode } from '../api/types'
import { Empty, ErrorNote, PriorityBar, RichText, Section, Spinner } from '../components/ui'

/** The knowledge tree: one hierarchy over decks *and* reading material.
 *
 *  Reorganising is a "move to…" picker rather than drag-and-drop — a select is
 *  keyboard-reachable and needs no drag library, and moving a branch across a
 *  long scrolled tree is the case dragging handles worst.
 */
export default function Tree() {
  const [nodes, setNodes] = useState<TreeNode[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<unknown>(null)
  const [expanded, setExpanded] = useState<Set<string>>(new Set())
  const [highestOrderOnly, setHighestOrderOnly] = useState(false)

  const load = useCallback(async () => {
    try {
      const { nodes } = await api.tree()
      setNodes(nodes)
      // First load: open the top level so the tree isn't a wall of collapsed
      // rows, but leave deeper branches shut.
      setExpanded((prev) =>
        prev.size ? prev : new Set(nodes.filter((n) => !n.collapsed).map((n) => n.id)),
      )
    } catch (err) {
      setError(err)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    void load()
  }, [load])

  // Flat list of every node, for the "move to…" picker and the depth guides.
  const flat = useMemo(() => flatten(nodes), [nodes])

  if (loading) return <Spinner label="Loading your knowledge tree…" />

  return (
    <div className="space-y-6">
      <ErrorNote error={error} />

      <Section
        title="Knowledge tree"
        description="Everything you're learning in one hierarchy — topics, decks, articles and the extracts carved out of them. Priority flows down a branch."
        actions={
          <div className="flex flex-wrap items-center gap-2">
            <button
              type="button"
              className={`btn px-2.5 py-1 text-xs transition ${
                highestOrderOnly
                  ? 'border-sky-500/60 bg-sky-500/15 text-sky-200 ring-1 ring-sky-500/30'
                  : 'text-slate-400'
              }`}
              onClick={() => setHighestOrderOnly(!highestOrderOnly)}
              title="Show only top-level parent subjects, documents, and decks"
            >
              {highestOrderOnly ? '✓ Highest-order parents only' : 'Highest-order parents only'}
            </button>
            {!highestOrderOnly && (
              <>
                <button
                  type="button"
                  className="btn px-2 py-1 text-xs"
                  onClick={() => setExpanded(new Set(flat.map((f) => f.id)))}
                >
                  Expand all
                </button>
                <button
                  type="button"
                  className="btn px-2 py-1 text-xs"
                  onClick={() => setExpanded(new Set())}
                >
                  Collapse all
                </button>
              </>
            )}
            <NewTopic parentId={null} onDone={load} label="New topic" />
          </div>
        }
      >
        {nodes.length === 0 ? (
          <Empty title="Nothing here yet.">
            Add a deck or import something to read and it will appear in the tree.
          </Empty>
        ) : (
          <div className="space-y-1">
            {nodes.map((n) => (
              <NodeRow
                key={n.id}
                node={n}
                depth={0}
                all={flat}
                expanded={expanded}
                highestOrderOnly={highestOrderOnly}
                onToggle={(id) =>
                  setExpanded((prev) => {
                    const next = new Set(prev)
                    next.has(id) ? next.delete(id) : next.add(id)
                    return next
                  })
                }
                onChange={load}
              />
            ))}
          </div>
        )}
      </Section>
    </div>
  )
}

const KIND_ICON: Record<TreeNode['kind'], string> = {
  topic: '▤',
  deck: '🗂',
  source: '📄',
  extract: '✂',
}

const KIND_LABEL: Record<TreeNode['kind'], string> = {
  topic: 'topic',
  deck: 'deck',
  source: 'article',
  extract: 'extract',
}

function countDescendants(node: TreeNode): number {
  let count = node.children.length
  for (const c of node.children) {
    count += countDescendants(c)
  }
  return count
}

function NodeRow({
  node,
  depth,
  all,
  expanded,
  highestOrderOnly = false,
  onToggle,
  onChange,
}: {
  node: TreeNode
  depth: number
  all: Flat[]
  expanded: Set<string>
  highestOrderOnly?: boolean
  onToggle: (id: string) => void
  onChange: () => void
}) {
  const navigate = useNavigate()
  const [busy, setBusy] = useState(false)
  const [renaming, setRenaming] = useState(false)
  const [name, setName] = useState(node.title)
  const [showCards, setShowCards] = useState(false)
  const [error, setError] = useState<unknown>(null)

  const isOpen = expanded.has(node.id)
  const hasChildren = node.children.length > 0

  async function run(fn: () => Promise<unknown>) {
    setBusy(true)
    setError(null)
    try {
      await fn()
      onChange()
    } catch (err) {
      setError(err)
    } finally {
      setBusy(false)
    }
  }

  return (
    <div>
      <div
        className="group flex flex-wrap items-center gap-x-3 gap-y-2 rounded-lg border border-transparent px-2 py-2 hover:border-ink-line hover:bg-ink-soft/40"
        style={{ marginLeft: `${depth * 1.25}rem` }}
      >
        <button
          className={`w-4 shrink-0 text-xs text-slate-600 ${hasChildren && !highestOrderOnly ? 'hover:text-slate-300' : 'invisible'}`}
          onClick={() => !highestOrderOnly && onToggle(node.id)}
          aria-label={isOpen ? 'Collapse' : 'Expand'}
        >
          {isOpen ? '▾' : '▸'}
        </button>

        <span className="shrink-0 text-sm" title={KIND_LABEL[node.kind]}>
          {KIND_ICON[node.kind]}
        </span>

        {renaming ? (
          <form
            className="flex min-w-0 flex-1 gap-2"
            onSubmit={(e) => {
              e.preventDefault()
              setRenaming(false)
              void run(() => api.updateNode(node.id, { title: name.trim() }))
            }}
          >
            <input
              className="input flex-1 py-1 text-sm"
              value={name}
              autoFocus
              onChange={(e) => setName(e.target.value)}
              onBlur={() => setRenaming(false)}
            />
          </form>
        ) : (
          <button
            className="min-w-0 flex-1 truncate text-left text-sm text-slate-200"
            title={node.title}
            onClick={() => {
              if (node.extract_id) navigate(`/read/${node.extract_id}`)
              else if (hasChildren && !highestOrderOnly) onToggle(node.id)
            }}
          >
            {node.title}
          </button>
        )}

        <div className="flex shrink-0 flex-wrap items-center gap-2 text-xs">
          {hasChildren && highestOrderOnly && (
            <span className="chip border-sky-500/30 text-sky-200/90 bg-sky-500/10">
              {countDescendants(node)} sub-item{countDescendants(node) === 1 ? '' : 's'}
            </span>
          )}
          {node.locked && (
            <span
              className="chip border-amber-500/40 text-amber-300"
              title={
                node.requires_title
                  ? `Locked — needs ${node.mastery_threshold}% mastery on "${node.requires_title}"`
                  : 'Locked'
              }
            >
              🔒 locked
            </span>
          )}
          {(node.kind === 'topic' || node.kind === 'deck') && node.card_count > 0 && (
            <span
              className="chip"
              title={`${node.mastery_pct}% of cards in this branch have graduated to review`}
            >
              {node.mastery_pct}% mastered
            </span>
          )}
          {node.card_count > 0 && <span className="chip">{node.card_count} cards</span>}
          {node.due_count > 0 && <span className="chip text-sky-300">{node.due_count} due</span>}
          {node.new_count > 0 && <span className="chip">{node.new_count} new</span>}
          {node.extract_count > 0 && (
            <span className="chip">{node.extract_count} to read</span>
          )}
          <span
            className={node.priority_inherited ? 'opacity-40' : ''}
            title={node.priority_inherited ? 'Inherited from a parent branch' : 'Set on this node'}
          >
            <PriorityBar value={node.priority} />
          </span>
          <button
            className="btn px-2 py-1 text-xs"
            disabled={busy || node.locked}
            onClick={() => navigate(`/review?branch=${node.id}`)}
            title={node.locked ? "Locked — this branch isn't unlocked yet" : 'Study only this branch'}
          >
            Study
          </button>
          <PriorityMenu node={node} onApply={(p, cascade) =>
            run(() => api.updateNode(node.id, { priority: p, cascade }))
          } />
          <MoveMenu node={node} all={all} onMove={(parentId) =>
            run(() => api.moveNode(node.id, parentId))
          } />
          {(node.kind === 'topic' || node.kind === 'deck') && (
            <GateMenu
              node={node}
              all={all}
              onApply={(requiresNodeId, threshold) =>
                run(() =>
                  api.updateNode(node.id, {
                    requires_node_id: requiresNodeId,
                    mastery_threshold: threshold,
                  }),
                )
              }
            />
          )}
          <NewTopic parentId={node.id} onDone={onChange} label="+" title="Add a sub-topic" />
          {node.card_count > 0 && (
            <button
              className="btn px-2 py-1 text-xs"
              onClick={() => setShowCards((s) => !s)}
              title="List the cards in this branch"
            >
              {showCards ? 'Hide' : 'Cards'}
            </button>
          )}
          {!renaming && (
            <button
              className="btn px-2 py-1 text-xs"
              disabled={busy}
              onClick={() => {
                setName(node.title)
                setRenaming(true)
              }}
            >
              Rename
            </button>
          )}
          {node.kind === 'topic' && (
            <button
              className="btn btn-danger px-2 py-1 text-xs"
              disabled={busy}
              onClick={() => {
                if (
                  !confirm(
                    `Delete the topic “${node.title}”? Anything inside it moves up a level — nothing is deleted.`,
                  )
                )
                  return
                void run(() => api.deleteNode(node.id))
              }}
            >
              Delete
            </button>
          )}
        </div>
      </div>

      {error != null && (
        <div style={{ marginLeft: `${depth * 1.25 + 2}rem` }} className="my-1">
          <ErrorNote error={error} />
        </div>
      )}

      {showCards && <BranchCards nodeId={node.id} depth={depth} />}

      {!highestOrderOnly &&
        isOpen &&
        node.children.map((child) => (
          <NodeRow
            key={child.id}
            node={child}
            depth={depth + 1}
            all={all}
            expanded={expanded}
            highestOrderOnly={highestOrderOnly}
            onToggle={onToggle}
            onChange={onChange}
          />
        ))}
    </div>
  )
}

function BranchCards({ nodeId, depth }: { nodeId: string; depth: number }) {
  const [cards, setCards] = useState<Card[] | null>(null)
  const [error, setError] = useState<unknown>(null)

  useEffect(() => {
    api.branchCards(nodeId).then(setCards).catch(setError)
  }, [nodeId])

  return (
    <div style={{ marginLeft: `${depth * 1.25 + 2.5}rem` }} className="my-1 space-y-1">
      <ErrorNote error={error} />
      {!cards ? (
        <Spinner />
      ) : cards.length === 0 ? (
        <p className="text-xs text-slate-600">No cards in this branch.</p>
      ) : (
        cards.map((c) => (
          <div key={c.id} className="rounded border border-ink-line px-3 py-2">
            <RichText text={c.front} className="text-xs text-slate-300" />
            <div className="mt-1 flex flex-wrap gap-2 text-[11px]">
              <span className="chip">{c.state}</span>
              {c.due && <span className="chip">due {new Date(c.due).toLocaleDateString()}</span>}
              <span className="chip">p{c.priority}</span>
            </div>
          </div>
        ))
      )}
    </div>
  )
}

/** Priority, with the branch sweep kept as a separate deliberate action —
 *  writing a number onto every card under a branch shouldn't be a stray drag. */
function PriorityMenu({
  node,
  onApply,
}: {
  node: TreeNode
  onApply: (priority: number, cascade: boolean) => void
}) {
  const [open, setOpen] = useState(false)
  const [value, setValue] = useState(node.priority)

  if (!open) {
    return (
      <button className="btn px-2 py-1 text-xs" onClick={() => setOpen(true)}>
        Priority
      </button>
    )
  }

  return (
    <span className="flex items-center gap-1 rounded-lg border border-ink-line bg-ink px-2 py-1">
      <input
        type="range"
        min={0}
        max={100}
        value={value}
        className="w-20"
        onChange={(e) => setValue(Number(e.target.value))}
      />
      <span className="w-6 text-xs tabular-nums text-slate-400">{value}</span>
      <button
        className="btn px-2 py-0.5 text-[11px]"
        onClick={() => {
          onApply(value, false)
          setOpen(false)
        }}
        title="Set on this node only"
      >
        Set
      </button>
      <button
        className="btn px-2 py-0.5 text-[11px]"
        onClick={() => {
          onApply(value, true)
          setOpen(false)
        }}
        title="Write this priority onto everything in the branch"
      >
        Whole branch
      </button>
      <button className="px-1 text-xs text-slate-600" onClick={() => setOpen(false)}>
        ✕
      </button>
    </span>
  )
}

function MoveMenu({
  node,
  all,
  onMove,
}: {
  node: TreeNode
  all: Flat[]
  onMove: (parentId: string | null) => void
}) {
  // A branch can't be filed inside itself — the backend refuses it, and
  // offering it here would just be a button that errors.
  const banned = new Set(flatten([node]).map((n) => n.id))
  const options = all.filter((n) => !banned.has(n.id) && n.kind !== 'extract')

  return (
    <select
      className="input py-1 text-xs"
      value=""
      onChange={(e) => {
        if (e.target.value === '') return
        onMove(e.target.value === '__root__' ? null : e.target.value)
      }}
      title="Move this branch somewhere else"
    >
      <option value="">Move to…</option>
      {node.parent_id && <option value="__root__">Top level</option>}
      {options.map((n) => (
        <option key={n.id} value={n.id}>
          {' '.repeat(n.depth * 2)}
          {KIND_ICON[n.kind]} {n.title}
        </option>
      ))}
    </select>
  )
}

/** Mastery gating: lock a branch behind another branch's mastery percentage.
 *  Only topics and decks carry testable content, so only they can gate or be
 *  gated — the picker excludes sources, extracts, and this node itself. */
function GateMenu({
  node,
  all,
  onApply,
}: {
  node: TreeNode
  all: Flat[]
  onApply: (requiresNodeId: string | null, threshold: number) => void
}) {
  const [open, setOpen] = useState(false)
  const [target, setTarget] = useState(node.requires_node_id ?? '')
  const [threshold, setThreshold] = useState(node.mastery_threshold)

  const options = all.filter(
    (n) => n.id !== node.id && (n.kind === 'topic' || n.kind === 'deck'),
  )

  if (!open) {
    return (
      <button
        className={`btn px-2 py-1 text-xs ${node.requires_node_id ? 'border-amber-500/40 text-amber-300' : ''}`}
        onClick={() => setOpen(true)}
        title={
          node.requires_node_id
            ? `Gated on "${node.requires_title}" @ ${node.mastery_threshold}%`
            : 'Gate this branch behind another one\'s mastery'
        }
      >
        Gate
      </button>
    )
  }

  return (
    <span className="flex flex-wrap items-center gap-1 rounded-lg border border-ink-line bg-ink px-2 py-1">
      <select
        className="input w-40 py-1 text-xs"
        value={target}
        onChange={(e) => setTarget(e.target.value)}
      >
        <option value="">No prerequisite</option>
        {options.map((n) => (
          <option key={n.id} value={n.id}>
            {' '.repeat(n.depth * 2)}
            {KIND_ICON[n.kind]} {n.title}
          </option>
        ))}
      </select>
      {target && (
        <>
          <input
            type="number"
            min={1}
            max={100}
            className="input w-14 py-1 text-xs"
            value={threshold}
            onChange={(e) => setThreshold(Number(e.target.value))}
          />
          <span className="text-xs text-slate-500">%</span>
        </>
      )}
      <button
        className="btn px-2 py-0.5 text-[11px]"
        onClick={() => {
          onApply(target || null, threshold)
          setOpen(false)
        }}
      >
        Save
      </button>
      <button className="px-1 text-xs text-slate-600" onClick={() => setOpen(false)}>
        ✕
      </button>
    </span>
  )
}

function NewTopic({
  parentId,
  onDone,
  label,
  title,
}: {
  parentId: string | null
  onDone: () => void
  label: string
  title?: string
}) {
  const [open, setOpen] = useState(false)
  const [name, setName] = useState('')
  const [busy, setBusy] = useState(false)

  if (!open) {
    return (
      <button className="btn px-2 py-1 text-xs" onClick={() => setOpen(true)} title={title}>
        {label}
      </button>
    )
  }

  return (
    <form
      className="flex gap-2"
      onSubmit={async (e) => {
        e.preventDefault()
        if (!name.trim()) return
        setBusy(true)
        try {
          await api.createTopic({ title: name.trim(), parent_id: parentId })
          setName('')
          setOpen(false)
          onDone()
        } finally {
          setBusy(false)
        }
      }}
    >
      <input
        className="input w-40 py-1 text-xs"
        placeholder="Topic name"
        value={name}
        autoFocus
        onChange={(e) => setName(e.target.value)}
      />
      <button className="btn px-2 py-1 text-xs" disabled={busy}>
        Add
      </button>
      <button
        type="button"
        className="px-1 text-xs text-slate-600"
        onClick={() => setOpen(false)}
      >
        ✕
      </button>
    </form>
  )
}

/** Depth is derived here rather than sent by the API — it is a property of how
 *  the tree is drawn, not of the node. */
type Flat = TreeNode & { depth: number }

function flatten(nodes: TreeNode[], depth = 0): Flat[] {
  return nodes.flatMap((n) => [
    { ...n, depth },
    ...flatten(n.children, depth + 1),
  ])
}
