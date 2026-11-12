import React, { useCallback, useRef, useState } from 'react'

export interface ResizableSplitterProps {
  direction: 'horizontal' | 'vertical'
  onResize: (deltaPx: number) => void
  onResizeEnd?: () => void
  onDoubleClick?: () => void
  onToggleCollapse?: () => void
  isCollapsed?: boolean
  collapseTooltip?: string
  className?: string
  disabled?: boolean
  variant?: 'pill' | 'flush'
}

export function ResizableSplitter({
  direction,
  onResize,
  onResizeEnd,
  onDoubleClick,
  onToggleCollapse,
  isCollapsed = false,
  collapseTooltip,
  className = '',
  disabled = false,
  variant = 'pill',
}: ResizableSplitterProps) {
  const [isDragging, setIsDragging] = useState(false)
  const isDraggingRef = useRef(false)
  const startPosRef = useRef(0)

  const handlePointerDown = useCallback(
    (e: React.PointerEvent<HTMLDivElement>) => {
      if (disabled || e.button !== 0) return
      // Prevent text selection during drag
      e.preventDefault()
      e.stopPropagation()

      isDraggingRef.current = true
      setIsDragging(true)
      startPosRef.current = direction === 'horizontal' ? e.clientX : e.clientY

      const targetDoc = e.currentTarget.ownerDocument || document
      const targetWin = targetDoc.defaultView || window

      const handlePointerMove = (moveEvent: PointerEvent) => {
        if (!isDraggingRef.current) return
        moveEvent.preventDefault()

        const currentPos = direction === 'horizontal' ? moveEvent.clientX : moveEvent.clientY
        const delta = currentPos - startPosRef.current
        startPosRef.current = currentPos

        if (delta !== 0) {
          onResize(delta)
        }
      }

      const handlePointerUp = () => {
        isDraggingRef.current = false
        setIsDragging(false)
        targetWin.removeEventListener('pointermove', handlePointerMove)
        targetWin.removeEventListener('pointerup', handlePointerUp)
        targetWin.removeEventListener('pointercancel', handlePointerUp)
        targetDoc.body.style.removeProperty('user-select')
        targetDoc.body.style.removeProperty('cursor')

        if (onResizeEnd) {
          onResizeEnd()
        }
      }

      targetDoc.body.style.userSelect = 'none'
      targetDoc.body.style.cursor = direction === 'horizontal' ? 'col-resize' : 'row-resize'

      targetWin.addEventListener('pointermove', handlePointerMove, { passive: false })
      targetWin.addEventListener('pointerup', handlePointerUp)
      targetWin.addEventListener('pointercancel', handlePointerUp)
    },
    [direction, disabled, onResize, onResizeEnd],
  )

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (disabled) return
      const step = e.shiftKey ? 30 : 10
      if (direction === 'horizontal') {
        if (e.key === 'ArrowLeft') {
          e.preventDefault()
          onResize(-step)
          onResizeEnd?.()
        } else if (e.key === 'ArrowRight') {
          e.preventDefault()
          onResize(step)
          onResizeEnd?.()
        }
      } else {
        if (e.key === 'ArrowUp') {
          e.preventDefault()
          onResize(-step)
          onResizeEnd?.()
        } else if (e.key === 'ArrowDown') {
          e.preventDefault()
          onResize(step)
          onResizeEnd?.()
        }
      }
    },
    [direction, disabled, onResize, onResizeEnd],
  )

  const isH = direction === 'horizontal'
  const isFlush = variant === 'flush'

  return (
    <div
      role="separator"
      tabIndex={disabled ? -1 : 0}
      aria-orientation={direction}
      onPointerDown={handlePointerDown}
      onDoubleClick={onDoubleClick}
      onKeyDown={handleKeyDown}
      className={`group relative flex items-center justify-center shrink-0 transition-colors select-none z-10 ${
        isFlush
          ? isH
            ? 'w-1.5 cursor-col-resize bg-[#181a1f]'
            : 'h-1.5 cursor-row-resize bg-[#181a1f]'
          : isH
          ? 'w-2.5 -mx-1 cursor-col-resize py-1'
          : 'h-2.5 -my-1 cursor-row-resize px-1'
      } ${
        isDragging
          ? 'bg-sky-500/25'
          : isFlush
          ? 'hover:bg-sky-500/15'
          : 'hover:bg-sky-500/10'
      } ${className}`}
      title={
        collapseTooltip ||
        (isH
          ? 'Drag to adjust width (Double-click to reset)'
          : 'Drag to adjust height (Double-click to reset)')
      }
    >
      {/* Visual divider line */}
      <div
        className={`transition-all duration-150 ${
          isFlush
            ? isH
              ? 'w-px h-full'
              : 'h-px w-full'
            : `${isH ? 'w-[2px] h-full' : 'h-[2px] w-full'} rounded-full`
        } ${
          isDragging
            ? 'bg-sky-400 shadow-[0_0_8px_rgba(56,189,248,0.7)]'
            : isFlush
            ? 'bg-[#2a2d34] group-hover:bg-sky-400/70'
            : 'bg-ink-line group-hover:bg-sky-400/70'
        }`}
      />

      {/* Grip handle */}
      {isFlush ? (
        <div
          className={`pointer-events-none absolute rounded-full transition-colors ${
            isH ? 'w-[3px] h-8' : 'h-[3px] w-8'
          } ${
            isDragging
              ? 'bg-sky-300'
              : 'bg-slate-600/80 group-hover:bg-sky-400'
          }`}
        />
      ) : (
        <div
          className={`absolute rounded-full border border-ink-line bg-[#1e1e1e] shadow-sm flex items-center justify-center transition-all duration-150 ${
            isH ? 'w-3.5 h-6' : 'h-3.5 w-6'
          } ${
            isDragging
              ? 'border-sky-400 bg-sky-950 text-sky-200 scale-110 shadow-[0_0_10px_rgba(56,189,248,0.5)]'
              : 'group-hover:border-sky-400/80 group-hover:bg-[#282828] text-slate-400 group-hover:text-sky-300'
          }`}
        >
          {isH ? (
            <svg className="w-2 h-3" viewBox="0 0 6 10" fill="currentColor">
              <circle cx="1.5" cy="2" r="1" />
              <circle cx="4.5" cy="2" r="1" />
              <circle cx="1.5" cy="5" r="1" />
              <circle cx="4.5" cy="5" r="1" />
              <circle cx="1.5" cy="8" r="1" />
              <circle cx="4.5" cy="8" r="1" />
            </svg>
          ) : (
            <svg className="w-3 h-2" viewBox="0 0 10 6" fill="currentColor">
              <circle cx="2" cy="1.5" r="1" />
              <circle cx="2" cy="4.5" r="1" />
              <circle cx="5" cy="1.5" r="1" />
              <circle cx="5" cy="4.5" r="1" />
              <circle cx="8" cy="1.5" r="1" />
              <circle cx="8" cy="4.5" r="1" />
            </svg>
          )}
        </div>
      )}

      {/* Optional quick collapse toggle chevron button */}
      {onToggleCollapse && (
        <button
          type="button"
          tabIndex={-1}
          onClick={(e) => {
            e.stopPropagation()
            onToggleCollapse()
          }}
          className={`absolute z-20 flex items-center justify-center bg-[#202020] border border-ink-line text-slate-400 hover:text-sky-200 hover:border-sky-400 text-[10px] shadow transition-all ${
            isFlush
              ? isH
                ? 'top-1.5 rounded w-3.5 h-5'
                : 'right-2 rounded h-3.5 w-6 leading-none'
              : isH
              ? 'top-2 rounded-full w-4 h-4 hover:scale-110'
              : 'right-2 rounded-full w-4 h-4 hover:scale-110'
          }`}
          title={isCollapsed ? 'Expand panel' : 'Collapse panel'}
        >
          {isH ? (isCollapsed ? '›' : '‹') : isCollapsed ? 'v' : '^'}
        </button>
      )}
    </div>
  )
}

export default ResizableSplitter
