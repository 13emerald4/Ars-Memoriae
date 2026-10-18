import React, { useState, useMemo } from 'react'
import { useNavigate } from 'react-router-dom'
import type { Deck, DeckStats, TreeNode } from '../api/types'
import { CompactDeckDistributionBars } from './DeckReviewStatsBar'

export type KnowledgeTreeTheme = 'modern' | 'classic'
export type DropPosition = 'before' | 'inside' | 'after'

export interface KnowledgeTreeNode {
  id: string
  title: string
  kind: 'root' | 'topic' | 'deck' | 'source' | 'extract'
  parentId: string | null
  elementCount: number
  dueCount?: number
  newCount?: number
  deckId?: string | null
  extractId?: string | null
  locked?: boolean
  children: KnowledgeTreeNode[]
  originalNode?: TreeNode
  originalDeck?: Deck
  stats?: DeckStats | null
}

interface KnowledgeTreeProps {
  rootTitle?: string
  nodes: KnowledgeTreeNode[]
  onSelectNode?: (node: KnowledgeTreeNode) => void
  onStudyNode?: (node: KnowledgeTreeNode, mode?: 'standard' | 'unseen' | 'all_run' | 'persist_all') => void
  onAddChild?: (parent: KnowledgeTreeNode | null) => void
  onRename?: (node: KnowledgeTreeNode) => void
  onDelete?: (node: KnowledgeTreeNode) => void
  onMove?: (node: KnowledgeTreeNode) => void
  onDropBranch?: (
    source: KnowledgeTreeNode,
    target: KnowledgeTreeNode,
    position: DropPosition,
  ) => void | Promise<void>
  onOpenCards?: (node: KnowledgeTreeNode) => void
  initialSelectedId?: string | null
}

/** 6-dots drag grip icon */
export function DragGripIcon({ className = 'w-3 h-3' }: { className?: string }) {
  return (
    <svg viewBox="0 0 20 20" fill="currentColor" className={`${className} shrink-0`}>
      <path d="M7 4a1.5 1.5 0 11-3 0 1.5 1.5 0 013 0zM7 10a1.5 1.5 0 11-3 0 1.5 1.5 0 013 0zM7 16a1.5 1.5 0 11-3 0 1.5 1.5 0 013 0zM16 4a1.5 1.5 0 11-3 0 1.5 1.5 0 013 0zM16 10a1.5 1.5 0 11-3 0 1.5 1.5 0 013 0zM16 16a1.5 1.5 0 11-3 0 1.5 1.5 0 013 0z" />
    </svg>
  )
}

/** Glowing incandescent lightbulb icon matching the root item */
export function LightbulbIcon({ className = 'w-4 h-4' }: { className?: string }) {
  return (
    <svg
      viewBox="0 0 24 24"
      className={`${className} text-amber-400 drop-shadow-[0_0_8px_rgba(251,191,36,0.45)] shrink-0`}
      fill="currentColor"
    >
      <path d="M12 2C8.13 2 5 5.13 5 9c0 2.38 1.19 4.47 3 5.74V17c0 .55.45 1 1 1h6c.55 0 1-.45 1-1v-2.26c1.81-1.27 3-3.36 3-5.74 0-3.87-3.13-7-7-7zm-3 18c0 .55.45 1 1 1h4c.55 0 1-.45 1-1v-.5H9v.5z" />
    </svg>
  )
}

/** Modern Topic [T] badge */
export function TopicIcon({ variant = 'yellow' }: { variant?: 'yellow' | 'green' }) {
  const isGreen = variant === 'green'
  return (
    <span
      className={`inline-flex items-center justify-center w-4 h-4 text-[10px] font-bold font-mono rounded shadow-xs select-none leading-none shrink-0 border ${
        isGreen
          ? 'bg-emerald-500/15 border-emerald-500/40 text-emerald-300'
          : 'bg-amber-500/15 border-amber-500/40 text-amber-300'
      }`}
      title={isGreen ? 'Active Concept / Group' : 'Topic'}
    >
      T
    </span>
  )
}

/** Chevron indicator for folding/unfolding tree branches */
function ChevronIcon({ expanded, className = 'w-3.5 h-3.5' }: { expanded: boolean; className?: string }) {
  return (
    <svg
      viewBox="0 0 20 20"
      fill="currentColor"
      className={`${className} transition-transform duration-150 ${expanded ? 'rotate-90 text-sky-400' : 'rotate-0 text-slate-400'}`}
    >
      <path
        fillRule="evenodd"
        d="M7.21 14.77a.75.75 0 01.02-1.06L11.168 10 7.23 6.29a.75.75 0 111.04-1.08l4.5 4.25a.75.75 0 010 1.08l-4.5 4.25a.75.75 0 01-1.06-.02z"
        clipRule="evenodd"
      />
    </svg>
  )
}


export function KnowledgeTree({
  rootTitle = 'All',
  nodes,
  onSelectNode,
  onStudyNode,
  onAddChild,
  onRename,
  onDelete,
  onMove,
  onDropBranch,
  onOpenCards,
  initialSelectedId,
}: KnowledgeTreeProps) {
  const navigate = useNavigate()
  const [theme, setTheme] = useState<KnowledgeTreeTheme>(() => {
    return (localStorage.getItem('knowledgeTree.theme') as KnowledgeTreeTheme) || 'modern'
  })

  const [expanded, setExpanded] = useState<Set<string>>(() => {
    // Default: expand root and top-level branches
    const initial = new Set<string>(['__root__'])
    nodes.forEach((n) => initial.add(n.id))
    return initial
  })

  const [selectedId, setSelectedId] = useState<string>(initialSelectedId || '__root__')
  const [searchQuery, setSearchQuery] = useState('')
  const [showSearch, setShowSearch] = useState(false)

  // Drag and Drop state
  const [draggingNode, setDraggingNode] = useState<KnowledgeTreeNode | null>(null)
  const [dropTargetId, setDropTargetId] = useState<string | null>(null)
  const [dropPosition, setDropPosition] = useState<DropPosition | null>(null)

  const toggleTheme = () => {
    setTheme((prev) => {
      const next = prev === 'modern' ? 'classic' : 'modern'
      localStorage.setItem('knowledgeTree.theme', next)
      return next
    })
  }

  const [showBars, setShowBars] = useState<boolean>(() => {
    if (typeof localStorage === 'undefined') return true
    return localStorage.getItem('knowledgeTree.showProgressBars') !== '0'
  })

  const toggleBars = () => {
    setShowBars((prev) => {
      const next = !prev
      localStorage.setItem('knowledgeTree.showProgressBars', next ? '1' : '0')
      return next
    })
  }

  // Rolled-up totals
  const rootTotals = useMemo(() => {
    let elements = 0
    let due = 0
    let newCards = 0

    const walk = (items: KnowledgeTreeNode[]) => {
      for (const item of items) {
        elements += item.elementCount || 0
        due += item.dueCount || 0
        newCards += item.newCount || 0
      }
    }
    walk(nodes)
    return { elements, due, newCards }
  }, [nodes])

  // Rolled-up root collection stats
  const rootStats = useMemo<DeckStats>(() => {
    let totalCards = 0
    let viewedCards = 0
    let newCards = 0
    let learningCards = 0
    let reviewCards = 0
    let dueCards = 0
    let totalReviews = 0
    const diffCounts: Record<string, number> = { Easy: 0, Medium: 0, Hard: 0, Unrated: 0 }
    const ratingCounts: Record<string, number> = { Again: 0, Hard: 0, Good: 0, Easy: 0, Unrated: 0 }

    for (const n of nodes) {
      if (n.stats) {
        totalCards += n.stats.total_cards || 0
        viewedCards += n.stats.viewed_cards || 0
        newCards += n.stats.new_cards || 0
        learningCards += n.stats.learning_cards || 0
        reviewCards += n.stats.review_cards || 0
        dueCards += n.stats.due_cards || 0
        totalReviews += n.stats.total_reviews || 0
        for (const [k, v] of Object.entries(n.stats.difficulty_counts || {})) {
          diffCounts[k] = (diffCounts[k] || 0) + v
        }
        for (const [k, v] of Object.entries(n.stats.rating_counts || {})) {
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
      name: rootTitle,
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
  }, [nodes, rootTitle])

  // Lookup map
  const allNodesMap = useMemo(() => {
    const map = new Map<string, KnowledgeTreeNode>()
    const rootNode: KnowledgeTreeNode = {
      id: '__root__',
      title: rootTitle,
      kind: 'root',
      parentId: null,
      elementCount: rootTotals.elements,
      dueCount: rootTotals.due,
      newCount: rootTotals.newCards,
      stats: rootStats,
      children: nodes,
    }
    map.set('__root__', rootNode)

    const walk = (list: KnowledgeTreeNode[]) => {
      for (const n of list) {
        map.set(n.id, n)
        if (n.children && n.children.length > 0) {
          walk(n.children)
        }
      }
    }
    walk(nodes)
    return map
  }, [nodes, rootTitle, rootTotals, rootStats])

  const selectedNode = allNodesMap.get(selectedId) || allNodesMap.get('__root__')!

  const toggleExpand = (id: string, e: React.MouseEvent) => {
    e.stopPropagation()
    setExpanded((prev) => {
      const next = new Set(prev)
      if (next.has(id)) next.delete(id)
      else next.add(id)
      return next
    })
  }

  const expandAll = () => {
    const next = new Set<string>(['__root__'])
    allNodesMap.forEach((_, id) => next.add(id))
    setExpanded(next)
  }

  const collapseAll = () => {
    setExpanded(new Set(['__root__']))
  }

  const handleNodeClick = (node: KnowledgeTreeNode) => {
    setSelectedId(node.id)
    if (onSelectNode) onSelectNode(node)
  }

  // Precompute invalid drop targets (source itself + all descendants) to prevent cyclic graphs
  const invalidTargetIds = useMemo(() => {
    if (!draggingNode) return new Set<string>()
    const ids = new Set<string>([draggingNode.id])
    const walk = (n: KnowledgeTreeNode) => {
      for (const child of n.children || []) {
        ids.add(child.id)
        walk(child)
      }
    }
    walk(draggingNode)
    return ids
  }, [draggingNode])

  const handleDragStart = (node: KnowledgeTreeNode, e: React.DragEvent) => {
    e.stopPropagation()
    setDraggingNode(node)
    e.dataTransfer.setData('text/plain', node.title)
    e.dataTransfer.effectAllowed = 'move'
  }

  const handleDragEnd = () => {
    setDraggingNode(null)
    setDropTargetId(null)
    setDropPosition(null)
  }

  const handleDragOverNode = (node: KnowledgeTreeNode, e: React.DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
    if (!draggingNode || invalidTargetIds.has(node.id)) {
      e.dataTransfer.dropEffect = 'none'
      if (dropTargetId === node.id) {
        setDropTargetId(null)
        setDropPosition(null)
      }
      return
    }

    e.dataTransfer.dropEffect = 'move'
    if (node.id === '__root__') {
      setDropTargetId('__root__')
      setDropPosition('inside')
      return
    }

    const rect = e.currentTarget.getBoundingClientRect()
    const relY = (e.clientY - rect.top) / rect.height
    let pos: DropPosition = 'inside'
    if (relY < 0.28) {
      pos = 'before'
    } else if (relY > 0.72) {
      pos = 'after'
    } else {
      pos = 'inside'
    }

    setDropTargetId(node.id)
    setDropPosition(pos)
  }

  const handleDropOnNode = (targetNode: KnowledgeTreeNode, e: React.DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
    const source = draggingNode
    const target = targetNode
    const pos = dropPosition

    setDraggingNode(null)
    setDropTargetId(null)
    setDropPosition(null)

    if (!source || !pos) return
    if (invalidTargetIds.has(target.id)) return
    if (source.id === target.id) return

    onDropBranch?.(source, target, pos)
  }

  const [studyModalNode, setStudyModalNode] = useState<KnowledgeTreeNode | null>(null)

  const handleStudyAction = (
    targetNode = selectedNode,
    mode: 'standard' | 'unseen' | 'all_run' | 'persist_all' = 'standard'
  ) => {
    if (onStudyNode) {
      onStudyNode(targetNode, mode)
    } else {
      if (mode === 'unseen') {
        if (targetNode.id === '__root__') {
          navigate('/review?persist=1&unseen=1')
        } else if (targetNode.deckId) {
          navigate(`/review?deck=${targetNode.deckId}&persist=1&unseen=1`)
        } else {
          navigate(`/review?branch=${targetNode.id}&persist=1&unseen=1`)
        }
      } else if (mode === 'all_run') {
        if (targetNode.deckId) {
          navigate(`/review?deck=${targetNode.deckId}&run=all`)
        } else {
          navigate('/review?run=all')
        }
      } else if (mode === 'persist_all') {
        if (targetNode.deckId) {
          navigate(`/review?deck=${targetNode.deckId}&persist=1`)
        } else {
          navigate('/review?persist=1')
        }
      } else {
        if (targetNode.id === '__root__') {
          navigate('/review')
        } else if (targetNode.deckId) {
          navigate(`/review?deck=${targetNode.deckId}`)
        } else {
          navigate(`/review?branch=${targetNode.id}`)
        }
      }
    }
  }

  const handleLearnClick = (targetNode = selectedNode) => {
    if (targetNode.newCount !== undefined && targetNode.newCount > 0) {
      setStudyModalNode(targetNode)
    } else {
      handleStudyAction(targetNode, 'standard')
    }
  }

  const isClassic = theme === 'classic'

  // Styling palette
  const containerClasses = isClassic
    ? 'border-[#7A7A7A] bg-[#FFFFFF] text-[#000000]'
    : 'border-ink-line bg-ink-soft/40 text-slate-100 backdrop-blur-xs'

  const toolbarClasses = isClassic
    ? 'bg-[#ECE9D8] border-[#999999]'
    : 'bg-ink/70 border-ink-line/80'

  const guideLineColor = isClassic
    ? 'border-dotted border-[#808080]'
    : 'bg-slate-700/50'

  return (
    <div
      className={`flex flex-col rounded-xl border shadow-lg overflow-hidden select-none font-sans transition-all duration-200 ${containerClasses}`}
      style={{ minHeight: '440px' }}
    >
      {/* ── 1. Unified Knowledge Tree Toolbar ── */}
      <div className={`flex flex-wrap items-center justify-between border-b px-3 py-2 gap-2 text-xs ${toolbarClasses}`}>
        {/* Left Action Buttons */}
        <div className="flex items-center gap-1">
          {/* Add Subdeck */}
          <button
            type="button"
            className="flex items-center gap-1 px-2 py-1 rounded-md bg-slate-800/80 hover:bg-slate-700/80 text-slate-200 border border-slate-700/70 hover:border-slate-500 transition shadow-xs"
            title="Add Subdeck"
            onClick={() => onAddChild?.(selectedNode)}
          >
            <span className="text-sky-400 font-bold">+</span>
            <span>Add Subdeck</span>
          </button>

          <span className="h-4 w-px bg-slate-700/60 mx-1" />

          {/* Search / Filter Toggle */}
          <button
            type="button"
            className={`p-1.5 rounded-md hover:bg-slate-800 text-slate-300 hover:text-white transition ${
              showSearch ? 'bg-sky-500/20 text-sky-300 ring-1 ring-sky-500/40' : ''
            }`}
            title="Filter"
            onClick={() => setShowSearch(!showSearch)}
          >
            <svg viewBox="0 0 20 20" fill="currentColor" className="w-3.5 h-3.5">
              <path
                fillRule="evenodd"
                d="M9 3.5a5.5 5.5 0 100 11 5.5 5.5 0 000-11zM2 9a7 7 0 1112.452 4.391l3.328 3.329a.75.75 0 11-1.06 1.06l-3.329-3.328A7 7 0 012 9z"
                clipRule="evenodd"
              />
            </svg>
          </button>

          {/* Inspect Cards */}
          {selectedNode?.deckId && onOpenCards && (
            <button
              type="button"
              className="p-1.5 rounded-md hover:bg-slate-800 text-slate-300 hover:text-white transition"
              title="Inspect cards"
              onClick={() => onOpenCards(selectedNode)}
            >
              <svg viewBox="0 0 20 20" fill="currentColor" className="w-3.5 h-3.5">
                <path d="M10 12.5a2.5 2.5 0 100-5 2.5 2.5 0 000 5z" />
                <path
                  fillRule="evenodd"
                  d="M.664 10.59a1.651 1.651 0 010-1.186A10.004 10.004 0 0110 3c4.257 0 7.893 2.66 9.336 6.41.147.381.146.804 0 1.186A10.004 10.004 0 0110 17c-4.257 0-7.893-2.66-9.336-6.41zM14 10a4 4 0 11-8 0 4 4 0 018 0z"
                  clipRule="evenodd"
                />
              </svg>
            </button>
          )}

          {/* Rename */}
          {selectedNode?.id !== '__root__' && onRename && (
            <button
              type="button"
              className="p-1.5 rounded-md hover:bg-slate-800 text-slate-300 hover:text-white transition"
              title="Rename"
              onClick={() => onRename(selectedNode)}
            >
              <svg viewBox="0 0 20 20" fill="currentColor" className="w-3.5 h-3.5">
                <path d="M2.695 14.763l-1.262 3.154a.5.5 0 00.65.65l3.155-1.262a4 4 0 001.343-.885L17.5 5.5a2.121 2.121 0 00-3-3L3.58 13.42a4 4 0 00-.885 1.343z" />
              </svg>
            </button>
          )}

          {/* Move */}
          {selectedNode?.id !== '__root__' && onMove && (
            <button
              type="button"
              className="p-1.5 rounded-md hover:bg-slate-800 text-slate-300 hover:text-white transition"
              title="Move"
              onClick={() => onMove(selectedNode)}
            >
              <svg viewBox="0 0 20 20" fill="currentColor" className="w-3.5 h-3.5">
                <path
                  fillRule="evenodd"
                  d="M15.312 11.424a5.5 5.5 0 01-9.201 2.466l-.312-.311h2.451a.75.75 0 000-1.5H4.5a.75.75 0 00-.75.75v3.75a.75.75 0 001.5 0v-2.122l.37.37a7 7 0 0011.722-3.14.75.75 0 00-1.53-.263zM4.688 8.576a5.5 5.5 0 019.201-2.466l.312.311H11.75a.75.75 0 000 1.5h3.75a.75.75 0 00.75-.75V3.421a.75.75 0 00-1.5 0v2.122l-.37-.37A7 7 0 002.608 8.313a.75.75 0 001.53.263z"
                  clipRule="evenodd"
                />
              </svg>
            </button>
          )}

          {/* Delete */}
          {selectedNode?.id !== '__root__' && onDelete && (
            <button
              type="button"
              className="p-1.5 rounded-md hover:bg-rose-500/20 text-rose-400 hover:text-rose-200 transition"
              title="Delete"
              onClick={() => onDelete(selectedNode)}
            >
              <svg viewBox="0 0 20 20" fill="currentColor" className="w-3.5 h-3.5">
                <path
                  fillRule="evenodd"
                  d="M8.75 1A2.75 2.75 0 006 3.75v.443c-.795.077-1.584.176-2.365.298a.75.75 0 10.23 1.482l.149-.022.841 10.518A2.75 2.75 0 007.596 19h4.807a2.75 2.75 0 002.742-2.53l.841-10.52.149.023a.75.75 0 00.23-1.482A41.03 41.03 0 0014 4.193V3.75A2.75 2.75 0 0011.25 1h-2.5zM10 4c.84 0 1.673.025 2.5.075V3.75c0-.69-.56-1.25-1.25-1.25h-2.5c-.69 0-1.25.56-1.25 1.25v.325C8.327 4.025 9.16 4 10 4zM8.58 7.72a.75.75 0 00-1.5.06l.3 7.5a.75.75 0 101.5-.06l-.3-7.5zm4.34.06a.75.75 0 10-1.5-.06l-.3 7.5a.75.75 0 101.5.06l.3-7.5z"
                  clipRule="evenodd"
                />
              </svg>
            </button>
          )}

          <span className="h-4 w-px bg-slate-700/60 mx-1" />

          {/* Progress Bars Toggle */}
          <button
            type="button"
            className={`px-2 py-0.5 rounded text-[11px] font-medium transition flex items-center gap-1 ${
              showBars
                ? 'bg-sky-500/20 text-sky-200 border border-sky-500/40'
                : 'text-slate-400 hover:text-slate-100 hover:bg-slate-800 border border-transparent'
            }`}
            title="Toggle progress bars"
            onClick={toggleBars}
          >
            <span>Bars</span>
          </button>

          {/* Expand / Collapse All */}
          <button
            type="button"
            className="px-2 py-0.5 rounded text-[11px] text-slate-400 hover:text-slate-100 hover:bg-slate-800 transition"
            onClick={expandAll}
          >
            Expand All
          </button>
          <button
            type="button"
            className="px-2 py-0.5 rounded text-[11px] text-slate-400 hover:text-slate-100 hover:bg-slate-800 transition"
            onClick={collapseAll}
          >
            Collapse All
          </button>
        </div>

        {/* Right Action: Primary Learn & Theme Switcher */}
        <div className="flex items-center gap-2">
          {/* Subtle Theme Switcher */}
          <button
            type="button"
            onClick={toggleTheme}
            className="text-[11px] px-2 py-0.5 rounded border border-slate-700/80 bg-slate-800/60 text-slate-400 hover:text-slate-200 hover:bg-slate-800 transition"
            title="Toggle theme"
          >
            {isClassic ? 'Win32' : 'Modern UI'}
          </button>

          {/* Direct Unseen Button */}
          {selectedNode.newCount !== undefined && selectedNode.newCount > 0 && (
            <button
              type="button"
              onClick={() => handleStudyAction(selectedNode, 'unseen')}
              className="flex items-center gap-1 px-2.5 py-1 rounded-lg bg-amber-500/20 hover:bg-amber-500/30 text-amber-200 border border-amber-500/40 font-semibold text-xs shadow-xs hover:scale-[1.02] active:scale-95 transition"
              title={`Study only the ${selectedNode.newCount} unseen cards until all are seen`}
            >
              <span>Unseen ({selectedNode.newCount})</span>
            </button>
          )}

          {/* Learn Button */}
          <button
            type="button"
            onClick={() => handleLearnClick(selectedNode)}
            className="flex items-center gap-1.5 px-3 py-1 rounded-lg bg-emerald-500/20 hover:bg-emerald-500/30 text-emerald-300 border border-emerald-500/40 font-semibold text-xs shadow-xs hover:scale-[1.02] active:scale-95 transition"
            title={
              selectedNode.id === '__root__'
                ? 'Learn All Decks'
                : `Learn: ${selectedNode.title}`
            }
          >
            <span>Learn</span>
            {selectedNode.dueCount !== undefined && selectedNode.dueCount > 0 && (
              <span className="chip px-1.5 py-0 text-[10px] bg-emerald-500/30 border-emerald-400/50 text-white font-bold">
                {selectedNode.dueCount}
              </span>
            )}
          </button>
        </div>
      </div>

      {/* Expandable Search / Filter Bar */}
      {showSearch && (
        <div className={`p-2 border-b flex items-center gap-2 ${toolbarClasses}`}>
          <span className="text-xs text-slate-400">Filter:</span>
          <input
            type="text"
            className="input py-1 px-2.5 text-xs flex-1 max-w-sm rounded-lg"
            placeholder="Type to filter titles..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            autoFocus
          />
          {searchQuery && (
            <button
              type="button"
              className="text-xs text-slate-400 hover:text-white px-1"
              onClick={() => setSearchQuery('')}
            >
              Clear
            </button>
          )}
        </div>
      )}

      {/* ── 2. Tree Hierarchy Area ── */}
      <div
        className="flex-1 p-3 overflow-auto text-sm leading-relaxed"
        style={{ minHeight: '340px' }}
      >
        {/* Root Node */}
        <div className="relative">
          <div
            className={`group relative flex items-center gap-2 py-1.5 px-2 rounded-lg cursor-pointer transition-all duration-150 ${
              selectedId === '__root__'
                ? 'bg-sky-500/15 text-sky-100 border border-sky-500/35 shadow-xs ring-1 ring-sky-500/20'
                : 'text-slate-300 hover:text-white hover:bg-slate-800/60 border border-transparent'
            } ${
              dropTargetId === '__root__'
                ? 'ring-2 ring-sky-400 bg-sky-500/25 border-sky-400 shadow-md'
                : ''
            }`}
            onDragOver={(e) => handleDragOverNode(allNodesMap.get('__root__')!, e)}
            onDrop={(e) => handleDropOnNode(allNodesMap.get('__root__')!, e)}
            onClick={() =>
              handleNodeClick({
                id: '__root__',
                title: rootTitle,
                kind: 'root',
                parentId: null,
                elementCount: rootTotals.elements,
                dueCount: rootTotals.due,
                newCount: rootTotals.newCards,
                children: nodes,
              })
            }
          >
            {/* Expand / Collapse Chevron */}
            <button
              type="button"
              draggable={false}
              onClick={(e) => toggleExpand('__root__', e)}
              className="p-0.5 rounded hover:bg-slate-700/40 text-slate-400 hover:text-slate-200 transition shrink-0"
            >
              <ChevronIcon expanded={expanded.has('__root__')} />
            </button>

            {/* Glowing Lightbulb for Root */}
            <LightbulbIcon className="w-4 h-4" />

            {/* Title & Count */}
            <span className="font-semibold truncate">
              {rootTitle}
            </span>
            <span className="text-xs text-slate-400 font-mono tabular-nums">
              ({rootTotals.elements})
            </span>

            {/* Distribution bars on Root */}
            {showBars && rootStats.total_cards > 0 && (
              <CompactDeckDistributionBars stats={rootStats} className="ml-2 shrink-0" />
            )}

            {/* Drop Indicator on Root */}
            {dropTargetId === '__root__' && draggingNode && (
              <span className="chip border-sky-400 bg-sky-500/30 text-sky-100 text-[10px] py-0 px-2 font-bold ml-auto animate-pulse">
                ↳ Move to Top-Level (Root)
              </span>
            )}

            {/* Badges */}
            {rootTotals.due > 0 && (
              <span className="chip border-sky-500/40 bg-sky-500/15 text-sky-300 text-[10px] py-0 px-2 font-semibold ml-auto shrink-0">
                {rootTotals.due} due
              </span>
            )}
            {rootTotals.newCards > 0 && (
              <span className="chip border-emerald-500/40 bg-emerald-500/15 text-emerald-300 text-[10px] py-0 px-2 font-semibold shrink-0">
                {rootTotals.newCards} new
              </span>
            )}
          </div>

          {/* Children under Root */}
          {expanded.has('__root__') && (
            <div className="relative pl-6 ml-2.5 mt-1">
              {/* Subtle vertical guide line */}
              <div className={`absolute left-[11px] top-0 bottom-2 w-px ${guideLineColor}`} />

              {nodes
                .filter((n) => !searchQuery || n.title.toLowerCase().includes(searchQuery.toLowerCase()))
                .map((child) => (
                  <KnowledgeTreeNodeComponent
                    key={child.id}
                    node={child}
                    depth={1}
                    expanded={expanded}
                    selectedId={selectedId}
                    searchQuery={searchQuery}
                    guideLineColor={guideLineColor}
                    isClassic={isClassic}
                    showBars={showBars}
                    draggingNode={draggingNode}
                    dropTargetId={dropTargetId}
                    dropPosition={dropPosition}
                    invalidTargetIds={invalidTargetIds}
                    onToggle={toggleExpand}
                    onSelect={handleNodeClick}
                    onDragStart={handleDragStart}
                    onDragEnd={handleDragEnd}
                    onDragOver={handleDragOverNode}
                    onDrop={handleDropOnNode}
                  />
                ))}
            </div>
          )}
        </div>
      </div>

      {/* ── 3. Bottom Status Bar ── */}
      <div className={`flex flex-wrap items-center justify-between border-t px-4 py-2.5 text-xs text-slate-400 gap-2 ${toolbarClasses}`}>
        <div className="flex items-center gap-2 truncate">
          <span className="text-slate-400">Selected:</span>
          <span className="font-semibold text-slate-200 truncate">
            {selectedNode.id === '__root__'
              ? `Entire Collection (${rootTotals.elements} cards)`
              : `${selectedNode.title} (${selectedNode.elementCount} cards)`}
          </span>
          {selectedNode.newCount !== undefined && selectedNode.newCount > 0 && (
            <span className="text-amber-300 font-medium font-mono">({selectedNode.newCount} unseen)</span>
          )}
          {selectedNode.dueCount !== undefined && selectedNode.dueCount > 0 && (
            <span className="text-sky-300 font-medium font-mono">({selectedNode.dueCount} due)</span>
          )}
        </div>

        <div className="flex items-center gap-2">
          {selectedNode.newCount !== undefined && selectedNode.newCount > 0 && (
            <button
              type="button"
              onClick={() => handleStudyAction(selectedNode, 'unseen')}
              className="flex items-center gap-1 rounded-md border border-amber-500/50 bg-amber-500/20 px-2.5 py-1 text-xs font-semibold text-amber-200 hover:bg-amber-500/30 transition shadow-xs cursor-pointer"
              title={`Study only the ${selectedNode.newCount} unseen cards until all are seen and grasped`}
            >
              <span>Study Unseen ({selectedNode.newCount})</span>
            </button>
          )}
          <button
            type="button"
            onClick={() => handleLearnClick(selectedNode)}
            className="btn btn-primary py-1 px-3 text-xs font-semibold shadow-xs"
          >
            {selectedNode.id === '__root__'
              ? 'Study Collection'
              : `Study Branch (${selectedNode.elementCount})`}
          </button>
        </div>
      </div>

      {/* Begin Deck Mode Option Modal */}
      {studyModalNode && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-xs animate-in fade-in duration-150"
          onClick={() => setStudyModalNode(null)}
        >
          <div
            className="relative w-full max-w-md rounded-2xl border border-sky-500/30 bg-[#0d131f] p-6 shadow-2xl text-left space-y-4"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-center justify-between pb-1 border-b border-ink-line/60">
              <div>
                <span className="text-[11px] font-bold uppercase tracking-wider text-amber-400">
                  Begin Deck
                </span>
                <h3 className="text-base font-bold text-slate-100">
                  {studyModalNode.title}
                </h3>
              </div>
              <button
                type="button"
                onClick={() => setStudyModalNode(null)}
                className="text-slate-400 hover:text-white text-lg leading-none cursor-pointer p-1"
                title="Close"
              >
                &times;
              </button>
            </div>

            <p className="text-xs text-slate-400">
              Choose how you would like to begin this deck:
            </p>

            <div className="space-y-2.5">
              {/* Option 1: Only Unseen Cards */}
              {studyModalNode.newCount !== undefined && studyModalNode.newCount > 0 ? (
                <button
                  type="button"
                  onClick={() => {
                    const node = studyModalNode
                    setStudyModalNode(null)
                    handleStudyAction(node, 'unseen')
                  }}
                  className="w-full text-left p-3.5 rounded-xl border border-amber-500/40 bg-amber-500/10 hover:bg-amber-500/20 hover:border-amber-400 transition group cursor-pointer"
                >
                  <div className="flex items-center justify-between mb-1">
                    <span className="font-semibold text-sm text-amber-200 group-hover:text-amber-100">
                      Only Unseen Cards
                    </span>
                    <span className="rounded-full bg-amber-500/20 px-2 py-0.5 text-[10px] font-mono font-bold text-amber-300">
                      {studyModalNode.newCount} unseen
                    </span>
                  </div>
                  <p className="text-xs text-slate-300 leading-relaxed">
                    Drill only previously unseen cards in this deck until all {studyModalNode.newCount} are introduced and rated Easy.
                  </p>
                </button>
              ) : null}

              {/* Option 2: Standard Review */}
              <button
                type="button"
                onClick={() => {
                  const node = studyModalNode
                  setStudyModalNode(null)
                  handleStudyAction(node, 'standard')
                }}
                className="w-full text-left p-3.5 rounded-xl border border-sky-500/30 bg-sky-500/10 hover:bg-sky-500/20 hover:border-sky-400 transition group cursor-pointer"
              >
                <div className="flex items-center justify-between mb-1">
                  <span className="font-semibold text-sm text-sky-200 group-hover:text-sky-100">
                    Standard Review
                  </span>
                  <span className="rounded-full bg-sky-500/20 px-2 py-0.5 text-[10px] font-mono text-sky-300">
                    {studyModalNode.dueCount || 0} due
                  </span>
                </div>
                <p className="text-xs text-slate-300 leading-relaxed">
                  Spaced repetition queue: review due cards first according to schedule before introducing new cards.
                </p>
              </button>

              {/* Option 3: All Cards Run */}
              <button
                type="button"
                onClick={() => {
                  const node = studyModalNode
                  setStudyModalNode(null)
                  handleStudyAction(node, 'all_run')
                }}
                className="w-full text-left p-3.5 rounded-xl border border-purple-500/30 bg-purple-500/10 hover:bg-purple-500/20 hover:border-purple-400 transition group cursor-pointer"
              >
                <div className="flex items-center justify-between mb-1">
                  <span className="font-semibold text-sm text-purple-200 group-hover:text-purple-100">
                    All Cards Run
                  </span>
                  <span className="rounded-full bg-purple-500/20 px-2 py-0.5 text-[10px] font-mono text-purple-300">
                    {studyModalNode.elementCount} cards
                  </span>
                </div>
                <p className="text-xs text-slate-300 leading-relaxed">
                  Review all cards consecutively from easiest to hardest, then FSRS takes over.
                </p>
              </button>
            </div>

            <div className="flex justify-end pt-1">
              <button
                type="button"
                onClick={() => setStudyModalNode(null)}
                className="btn border border-ink-line text-xs py-1.5 px-4 text-slate-400 hover:text-slate-200"
              >
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

/** Individual Recursive Node in Unified Knowledge Tree */
interface KnowledgeTreeNodeProps {
  node: KnowledgeTreeNode
  depth: number
  expanded: Set<string>
  selectedId: string
  searchQuery: string
  guideLineColor: string
  isClassic: boolean
  showBars: boolean
  draggingNode: KnowledgeTreeNode | null
  dropTargetId: string | null
  dropPosition: DropPosition | null
  invalidTargetIds: Set<string>
  onToggle: (id: string, e: React.MouseEvent) => void
  onSelect: (node: KnowledgeTreeNode) => void
  onDragStart: (node: KnowledgeTreeNode, e: React.DragEvent) => void
  onDragEnd: () => void
  onDragOver: (node: KnowledgeTreeNode, e: React.DragEvent) => void
  onDrop: (node: KnowledgeTreeNode, e: React.DragEvent) => void
}

function KnowledgeTreeNodeComponent({
  node,
  depth,
  expanded,
  selectedId,
  searchQuery,
  guideLineColor,
  isClassic,
  showBars,
  draggingNode,
  dropTargetId,
  dropPosition,
  invalidTargetIds,
  onToggle,
  onSelect,
  onDragStart,
  onDragEnd,
  onDragOver,
  onDrop,
}: KnowledgeTreeNodeProps) {
  const isSelected = selectedId === node.id
  const hasChildren = node.children && node.children.length > 0
  const isOpen = expanded.has(node.id)

  const isDraggingThis = draggingNode?.id === node.id
  const isDropTarget = dropTargetId === node.id

  const renderIcon = () => {
    if (node.kind === 'source' || node.kind === 'extract') {
      return <LightbulbIcon className="w-3.5 h-3.5" />
    }
    if (depth === 1) {
      return <TopicIcon variant="green" />
    }
    return <TopicIcon variant="yellow" />
  }

  return (
    <div className="relative py-0.5">
      {/* Horizontal connector line */}
      <div className={`absolute -left-3.5 top-3.5 w-3 h-px ${guideLineColor}`} />

      {/* Node Row */}
      <div
        draggable={!node.locked}
        onDragStart={(e) => onDragStart(node, e)}
        onDragEnd={onDragEnd}
        onDragOver={(e) => onDragOver(node, e)}
        onDrop={(e) => onDrop(node, e)}
        className={`group relative flex items-center gap-1.5 py-1.5 px-2 rounded-lg cursor-pointer transition-all duration-150 ${
          isSelected
            ? 'bg-sky-500/15 text-sky-100 border border-sky-500/35 shadow-xs ring-1 ring-sky-500/20'
            : 'text-slate-300 hover:text-white hover:bg-slate-800/60 border border-transparent'
        } ${
          isDraggingThis ? 'opacity-35 ring-1 ring-dashed ring-slate-400 bg-slate-800/40' : ''
        } ${
          isDropTarget && dropPosition === 'inside'
            ? 'ring-2 ring-sky-400 bg-sky-500/20 border-sky-400 shadow-md'
            : ''
        }`}
        onClick={() => onSelect(node)}
      >
        {/* Drop Indicators: Before and After insertion lines */}
        {isDropTarget && dropPosition === 'before' && (
          <div className="absolute -top-1 left-1 right-1 h-1 bg-sky-400 rounded-full shadow-[0_0_8px_rgba(56,189,248,0.9)] z-20 pointer-events-none flex items-center">
            <span className="text-[9px] font-bold text-sky-950 bg-sky-300 px-1 rounded-xs ml-2 shadow-xs">▲ Insert Before</span>
          </div>
        )}
        {isDropTarget && dropPosition === 'after' && (
          <div className="absolute -bottom-1 left-1 right-1 h-1 bg-sky-400 rounded-full shadow-[0_0_8px_rgba(56,189,248,0.9)] z-20 pointer-events-none flex items-center">
            <span className="text-[9px] font-bold text-sky-950 bg-sky-300 px-1 rounded-xs ml-2 shadow-xs">▼ Insert After</span>
          </div>
        )}

        {/* Drag Handle Grip */}
        <span
          className="opacity-0 group-hover:opacity-70 hover:!opacity-100 transition-opacity p-0.5 -ml-1 text-slate-500 hover:text-slate-200 cursor-grab active:cursor-grabbing shrink-0"
          title="Drag to reorder or re-parent branch"
        >
          <DragGripIcon className="w-3.5 h-3.5" />
        </span>

        {/* Chevron */}
        {hasChildren ? (
          <button
            type="button"
            draggable={false}
            onClick={(e) => onToggle(node.id, e)}
            className="p-0.5 rounded hover:bg-slate-700/40 text-slate-400 hover:text-slate-200 transition shrink-0"
          >
            <ChevronIcon expanded={isOpen} />
          </button>
        ) : (
          <span className="w-3.5 shrink-0" />
        )}

        {/* Node Icon */}
        {renderIcon()}

        {/* Title */}
        <span className="truncate select-none font-medium text-xs">
          {node.title}
        </span>

        {/* Count */}
        <span className="text-[11px] text-slate-400 font-mono tabular-nums shrink-0">
          ({node.elementCount})
        </span>

        {/* Inline Compact Distribution Bars */}
        {showBars && node.stats && node.stats.total_cards > 0 && (
          <CompactDeckDistributionBars stats={node.stats} className="ml-1 shrink-0" />
        )}

        {/* Drop inside indicator badge */}
        {isDropTarget && dropPosition === 'inside' && (
          <span className="text-[10px] font-semibold text-sky-200 bg-sky-950/90 px-1.5 py-0.5 rounded border border-sky-400/60 ml-auto shrink-0 animate-pulse">
            ↳ Move Inside
          </span>
        )}

        {/* Missing Documents Indicator Badge */}
        {(node.title.startsWith('!') || node.title.includes('[!]')) && (
          <span
            className="inline-flex items-center justify-center text-[10px] font-bold w-4 h-4 rounded-full bg-amber-500/20 text-amber-300 border border-amber-500/40 ml-1 shrink-0 select-none shadow-xs"
            title="Documents missing / pending instructor release to make cards"
          >
            !
          </span>
        )}

        {/* Locked Badge */}
        {node.locked && <span className="text-[10px] ml-1 text-amber-400 font-mono">[Locked]</span>}

        {/* Unseen Count Chip */}
        {node.newCount !== undefined && node.newCount > 0 && (
          <span
            className="chip border-amber-500/40 bg-amber-500/15 text-amber-300 text-[10px] py-0 px-1.5 font-semibold ml-auto shrink-0"
            title={`${node.newCount} unseen cards`}
          >
            {node.newCount} new
          </span>
        )}

        {/* Due Count Chip */}
        {node.dueCount !== undefined && node.dueCount > 0 && (
          <span className={`chip border-sky-500/40 bg-sky-500/15 text-sky-300 text-[10px] py-0 px-1.5 font-semibold shrink-0 ${node.newCount ? 'ml-1' : 'ml-auto'}`}>
            {node.dueCount} due
          </span>
        )}
      </div>

      {/* Subtree Children */}
      {hasChildren && isOpen && (
        <div className="relative pl-6 ml-2.5 mt-0.5">
          {/* Vertical guide line for children */}
          <div className={`absolute left-[11px] top-0 bottom-2 w-px ${guideLineColor}`} />

          {node.children
            .filter((c) => !searchQuery || c.title.toLowerCase().includes(searchQuery.toLowerCase()))
            .map((child) => (
              <KnowledgeTreeNodeComponent
                key={child.id}
                node={child}
                depth={depth + 1}
                expanded={expanded}
                selectedId={selectedId}
                searchQuery={searchQuery}
                guideLineColor={guideLineColor}
                isClassic={isClassic}
                showBars={showBars}
                draggingNode={draggingNode}
                dropTargetId={dropTargetId}
                dropPosition={dropPosition}
                invalidTargetIds={invalidTargetIds}
                onToggle={onToggle}
                onSelect={onSelect}
                onDragStart={onDragStart}
                onDragEnd={onDragEnd}
                onDragOver={onDragOver}
                onDrop={onDrop}
              />
            ))}
        </div>
      )}
    </div>
  )
}
