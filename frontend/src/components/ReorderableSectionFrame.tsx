import React from 'react'
import { DragGripIcon } from './KnowledgeTree'

export interface ReorderableControls {
  dragHandle: React.ReactNode
  moveButtons: React.ReactNode
  collapseButton: React.ReactNode
}

export interface ReorderableSectionFrameProps<T extends string> {
  id: T
  children: React.ReactNode
  isCollapsed?: boolean
  isFirst: boolean
  isLast: boolean
  isDragging: boolean
  isDropBefore: boolean
  isDropAfter: boolean
  onDragStart: (id: T, e: React.DragEvent) => void
  onDragOver: (id: T, e: React.DragEvent) => void
  onDragLeave: (id: T, e: React.DragEvent) => void
  onDrop: (id: T, e: React.DragEvent) => void
  onDragEnd: () => void
  onMoveUp: () => void
  onMoveDown: () => void
  onToggleCollapse: () => void
  renderHeader: (controls: ReorderableControls) => React.ReactNode
  className?: string
}

export function ReorderableSectionFrame<T extends string>({
  id,
  children,
  isCollapsed = false,
  isFirst,
  isLast,
  isDragging,
  isDropBefore,
  isDropAfter,
  onDragStart,
  onDragOver,
  onDragLeave,
  onDrop,
  onDragEnd,
  onMoveUp,
  onMoveDown,
  onToggleCollapse,
  renderHeader,
  className = '',
}: ReorderableSectionFrameProps<T>) {
  const dragHandle = (
    <div
      draggable
      onDragStart={(e) => onDragStart(id, e)}
      onDragEnd={onDragEnd}
      className="p-1 -ml-1 text-slate-500 hover:text-sky-300 cursor-grab active:cursor-grabbing transition rounded hover:bg-sky-500/10 flex items-center justify-center shrink-0"
      title="Drag to reorder this section"
    >
      <DragGripIcon className="w-3.5 h-3.5" />
    </div>
  )

  const moveButtons = (
    <div className="flex items-center gap-0.5 text-slate-400">
      <button
        type="button"
        disabled={isFirst}
        onClick={(e) => {
          e.stopPropagation()
          onMoveUp()
        }}
        className="p-1 rounded hover:bg-slate-800 hover:text-sky-200 disabled:opacity-20 disabled:hover:bg-transparent disabled:hover:text-slate-400 transition cursor-pointer"
        title="Move section up"
        aria-label="Move section up"
      >
        <svg viewBox="0 0 20 20" fill="currentColor" className="w-3.5 h-3.5">
          <path
            fillRule="evenodd"
            d="M14.77 12.79a.75.75 0 01-1.06-.02L10 8.832 6.29 12.77a.75.75 0 11-1.08-1.04l4.25-4.5a.75.75 0 011.08 0l4.25 4.5a.75.75 0 01-.02 1.06z"
            clipRule="evenodd"
          />
        </svg>
      </button>
      <button
        type="button"
        disabled={isLast}
        onClick={(e) => {
          e.stopPropagation()
          onMoveDown()
        }}
        className="p-1 rounded hover:bg-slate-800 hover:text-sky-200 disabled:opacity-20 disabled:hover:bg-transparent disabled:hover:text-slate-400 transition cursor-pointer"
        title="Move section down"
        aria-label="Move section down"
      >
        <svg viewBox="0 0 20 20" fill="currentColor" className="w-3.5 h-3.5">
          <path
            fillRule="evenodd"
            d="M5.23 7.21a.75.75 0 011.06.02L10 11.168l3.71-3.938a.75.75 0 111.08 1.04l-4.25 4.5a.75.75 0 01-1.08 0l-4.25-4.5a.75.75 0 01.02-1.06z"
            clipRule="evenodd"
          />
        </svg>
      </button>
    </div>
  )

  const collapseButton = (
    <button
      type="button"
      onClick={(e) => {
        e.stopPropagation()
        onToggleCollapse()
      }}
      className="p-1 rounded hover:bg-slate-800 hover:text-white transition cursor-pointer text-xs font-mono font-bold w-5 h-5 flex items-center justify-center text-slate-400"
      title={isCollapsed ? 'Expand section' : 'Collapse section to save space'}
      aria-label={isCollapsed ? 'Expand section' : 'Collapse section'}
    >
      {isCollapsed ? '+' : '−'}
    </button>
  )

  const dropRing = isDropBefore
    ? 'border-t-2 border-t-sky-400 shadow-[0_-4px_12px_rgba(56,189,248,0.25)]'
    : isDropAfter
    ? 'border-b-2 border-b-sky-400 shadow-[0_4px_12px_rgba(56,189,248,0.25)]'
    : ''

  const dragOpacity = isDragging
    ? 'opacity-35 ring-2 ring-sky-400/80 ring-dashed scale-[0.99] transition-transform'
    : ''

  return (
    <div
      onDragOver={(e) => onDragOver(id, e)}
      onDragLeave={(e) => onDragLeave(id, e)}
      onDrop={(e) => onDrop(id, e)}
      className={`transition-all duration-150 ${dropRing} ${dragOpacity} ${className}`}
    >
      {renderHeader({ dragHandle, moveButtons, collapseButton })}
      {!isCollapsed && children}
    </div>
  )
}
