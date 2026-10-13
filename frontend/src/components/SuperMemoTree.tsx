import React, { useState, useMemo } from 'react'
import { useNavigate } from 'react-router-dom'
import type { Deck, TreeNode } from '../api/types'

export type SuperMemoTheme = 'modern' | 'classic'

export interface SuperMemoNode {
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
  children: SuperMemoNode[]
  originalNode?: TreeNode
  originalDeck?: Deck
}

interface SuperMemoTreeProps {
  rootTitle?: string
  nodes: SuperMemoNode[]
  onSelectNode?: (node: SuperMemoNode) => void
  onStudyNode?: (node: SuperMemoNode) => void
  onAddChild?: (parent: SuperMemoNode | null) => void
  onRename?: (node: SuperMemoNode) => void
  onDelete?: (node: SuperMemoNode) => void
  onMove?: (node: SuperMemoNode) => void
  onOpenCards?: (node: SuperMemoNode) => void
  initialSelectedId?: string | null
}

/** Glowing incandescent lightbulb icon matching SuperMemo's root item */
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


export function SuperMemoTree({
  rootTitle = 'All',
  nodes,
  onSelectNode,
  onStudyNode,
  onAddChild,
  onRename,
  onDelete,
  onMove,
  onOpenCards,
  initialSelectedId,
}: SuperMemoTreeProps) {
  const navigate = useNavigate()
  const [theme, setTheme] = useState<SuperMemoTheme>(() => {
    return (localStorage.getItem('supermemo.treeTheme') as SuperMemoTheme) || 'modern'
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

  const toggleTheme = () => {
    setTheme((prev) => {
      const next = prev === 'modern' ? 'classic' : 'modern'
      localStorage.setItem('supermemo.treeTheme', next)
      return next
    })
  }

  // Rolled-up totals
  const rootTotals = useMemo(() => {
    let elements = 0
    let due = 0
    let newCards = 0

    const walk = (items: SuperMemoNode[]) => {
      for (const item of items) {
        elements += item.elementCount || 0
        due += item.dueCount || 0
        newCards += item.newCount || 0
      }
    }
    walk(nodes)
    return { elements, due, newCards }
  }, [nodes])

  // Lookup map
  const allNodesMap = useMemo(() => {
    const map = new Map<string, SuperMemoNode>()
    const rootNode: SuperMemoNode = {
      id: '__root__',
      title: rootTitle,
      kind: 'root',
      parentId: null,
      elementCount: rootTotals.elements,
      dueCount: rootTotals.due,
      newCount: rootTotals.newCards,
      children: nodes,
    }
    map.set('__root__', rootNode)

    const walk = (list: SuperMemoNode[]) => {
      for (const n of list) {
        map.set(n.id, n)
        if (n.children && n.children.length > 0) {
          walk(n.children)
        }
      }
    }
    walk(nodes)
    return map
  }, [nodes, rootTitle, rootTotals])

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

  const handleNodeClick = (node: SuperMemoNode) => {
    setSelectedId(node.id)
    if (onSelectNode) onSelectNode(node)
  }

  const handleLearn = (targetNode = selectedNode) => {
    if (onStudyNode) {
      onStudyNode(targetNode)
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
      {/* ── 1. Modern SuperMemo Toolbar ── */}
      <div className={`flex flex-wrap items-center justify-between border-b px-3 py-2 gap-2 text-xs ${toolbarClasses}`}>
        {/* Left Action Buttons */}
        <div className="flex items-center gap-1">
          {/* Add Subdeck */}
          <button
            type="button"
            className="flex items-center gap-1 px-2 py-1 rounded-md bg-slate-800/80 hover:bg-slate-700/80 text-slate-200 border border-slate-700/70 hover:border-slate-500 transition shadow-xs"
            title="Add Child Subdeck / Topic"
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
            title="Filter Knowledge Tree"
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
              title="Inspect cards in selected deck"
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
              title="Rename selected deck"
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
              title="Move / Re-parent selected branch"
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
              title="Delete selected deck"
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
            title="Toggle between Modern Seamless and Classic Win32 layout"
          >
            {isClassic ? 'Win32' : 'Modern UI'}
          </button>

          {/* Learn Button */}
          <button
            type="button"
            onClick={() => handleLearn(selectedNode)}
            className="flex items-center gap-1.5 px-3 py-1 rounded-lg bg-emerald-500/20 hover:bg-emerald-500/30 text-emerald-300 border border-emerald-500/40 font-semibold text-xs shadow-xs hover:scale-[1.02] active:scale-95 transition"
            title={
              selectedNode.id === '__root__'
                ? 'Learn Entire Collection (All Decks)'
                : `Learn Branch: ${selectedNode.title}`
            }
          >
            <span>⚡ Learn</span>
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
            className={`group flex items-center gap-2 py-1.5 px-2 rounded-lg cursor-pointer transition-all duration-150 ${
              selectedId === '__root__'
                ? 'bg-sky-500/15 text-sky-100 border border-sky-500/35 shadow-xs ring-1 ring-sky-500/20'
                : 'text-slate-300 hover:text-white hover:bg-slate-800/60 border border-transparent'
            }`}
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
              onClick={(e) => toggleExpand('__root__', e)}
              className="p-0.5 rounded hover:bg-slate-700/40 text-slate-400 hover:text-slate-200 transition"
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

            {/* Badges */}
            {rootTotals.due > 0 && (
              <span className="chip border-sky-500/40 bg-sky-500/15 text-sky-300 text-[10px] py-0 px-2 font-semibold ml-1">
                {rootTotals.due} due
              </span>
            )}
            {rootTotals.newCards > 0 && (
              <span className="chip border-emerald-500/40 bg-emerald-500/15 text-emerald-300 text-[10px] py-0 px-2 font-semibold">
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
                  <SuperMemoTreeNode
                    key={child.id}
                    node={child}
                    depth={1}
                    expanded={expanded}
                    selectedId={selectedId}
                    searchQuery={searchQuery}
                    guideLineColor={guideLineColor}
                    isClassic={isClassic}
                    onToggle={toggleExpand}
                    onSelect={handleNodeClick}
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
          {selectedNode.dueCount !== undefined && selectedNode.dueCount > 0 && (
            <span className="text-sky-300 font-medium">({selectedNode.dueCount} due)</span>
          )}
        </div>

        <button
          type="button"
          onClick={() => handleLearn(selectedNode)}
          className="btn btn-primary py-1 px-3 text-xs font-semibold shadow-xs"
        >
          {selectedNode.id === '__root__'
            ? 'Study Collection'
            : `Study Branch (${selectedNode.elementCount})`}
        </button>
      </div>
    </div>
  )
}

/** Individual Recursive Node in SuperMemo Knowledge Tree */
interface SuperMemoTreeNodeProps {
  node: SuperMemoNode
  depth: number
  expanded: Set<string>
  selectedId: string
  searchQuery: string
  guideLineColor: string
  isClassic: boolean
  onToggle: (id: string, e: React.MouseEvent) => void
  onSelect: (node: SuperMemoNode) => void
}

function SuperMemoTreeNode({
  node,
  depth,
  expanded,
  selectedId,
  searchQuery,
  guideLineColor,
  isClassic,
  onToggle,
  onSelect,
}: SuperMemoTreeNodeProps) {
  const isSelected = selectedId === node.id
  const hasChildren = node.children && node.children.length > 0
  const isOpen = expanded.has(node.id)

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
        className={`group flex items-center gap-1.5 py-1.5 px-2 rounded-lg cursor-pointer transition-all duration-150 ${
          isSelected
            ? 'bg-sky-500/15 text-sky-100 border border-sky-500/35 shadow-xs ring-1 ring-sky-500/20'
            : 'text-slate-300 hover:text-white hover:bg-slate-800/60 border border-transparent'
        }`}
        onClick={() => onSelect(node)}
      >
        {/* Chevron */}
        {hasChildren ? (
          <button
            type="button"
            onClick={(e) => onToggle(node.id, e)}
            className="p-0.5 rounded hover:bg-slate-700/40 text-slate-400 hover:text-slate-200 transition"
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
        {node.locked && <span className="text-[10px] ml-1">🔒</span>}

        {/* Due Count Chip */}
        {node.dueCount !== undefined && node.dueCount > 0 && (
          <span className="chip border-sky-500/40 bg-sky-500/15 text-sky-300 text-[10px] py-0 px-1.5 font-semibold ml-auto shrink-0">
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
              <SuperMemoTreeNode
                key={child.id}
                node={child}
                depth={depth + 1}
                expanded={expanded}
                selectedId={selectedId}
                searchQuery={searchQuery}
                guideLineColor={guideLineColor}
                isClassic={isClassic}
                onToggle={onToggle}
                onSelect={onSelect}
              />
            ))}
        </div>
      )}
    </div>
  )
}
