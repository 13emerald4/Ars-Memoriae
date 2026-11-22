import { useCallback, useEffect, useId, useRef, useState, type ReactNode } from 'react'

export interface NativePopoverProps {
  trigger: (props: {
    ref: React.RefObject<HTMLButtonElement | null>
    popoverTarget: string
    'aria-expanded': boolean
    'aria-controls': string
    onClick: () => void
  }) => ReactNode
  align?: 'left' | 'right'
  role?: 'dialog' | 'menu'
  ariaLabel: string
  className?: string
  children: (helpers: { close: () => void }) => ReactNode
  closeSignal?: string | number
}

/**
 * Floating menu/dialog powered by the native HTML Popover API (`popover="auto"`).
 * Renders in the browser Top Layer with automatic light-dismiss (click-outside & Escape)
 * and viewport-clamped positioning relative to its trigger element.
 */
export function NativePopover({
  trigger,
  align = 'right',
  role = 'dialog',
  ariaLabel,
  className = '',
  children,
  closeSignal,
}: NativePopoverProps) {
  const reactId = useId()
  const popoverId = `popover-${reactId.replace(/:/g, '')}`
  const triggerRef = useRef<HTMLButtonElement>(null)
  const popoverRef = useRef<HTMLDivElement>(null)
  const [open, setOpen] = useState(false)
  const [coords, setCoords] = useState<{ top: number; left: number } | null>(null)

  const updatePosition = useCallback(() => {
    const btn = triggerRef.current
    const pop = popoverRef.current
    if (!btn || !pop) return
    const rect = btn.getBoundingClientRect()
    const popRect = pop.getBoundingClientRect()
    const gap = 8
    const margin = 12
    const popWidth = popRect.width || 280
    const popHeight = popRect.height || 240

    let left = align === 'right' ? rect.right - popWidth : rect.left
    left = Math.max(margin, Math.min(left, window.innerWidth - popWidth - margin))

    let top = rect.bottom + gap
    if (top + popHeight > window.innerHeight - margin && rect.top - popHeight - gap > margin) {
      top = rect.top - popHeight - gap
    }
    setCoords({ top, left })
  }, [align])

  const close = useCallback(() => {
    const pop = popoverRef.current
    if (pop && pop.matches(':popover-open')) {
      try {
        pop.hidePopover()
      } catch {
        setOpen(false)
      }
    } else {
      setOpen(false)
    }
  }, [])

  useEffect(() => {
    if (closeSignal !== undefined) {
      close()
    }
  }, [closeSignal, close])

  useEffect(() => {
    const pop = popoverRef.current
    if (!pop) return
    const handleToggle = (e: Event) => {
      const toggleEvent = e as ToggleEvent
      const isOpen = toggleEvent.newState === 'open'
      setOpen(isOpen)
      if (isOpen) {
        requestAnimationFrame(() => updatePosition())
      }
    }
    pop.addEventListener('toggle', handleToggle)
    return () => pop.removeEventListener('toggle', handleToggle)
  }, [updatePosition])

  useEffect(() => {
    if (!open) return
    const onResize = () => updatePosition()
    window.addEventListener('resize', onResize)
    window.addEventListener('scroll', onResize, true)
    return () => {
      window.removeEventListener('resize', onResize)
      window.removeEventListener('scroll', onResize, true)
    }
  }, [open, updatePosition])

  const handleTriggerClick = useCallback(() => {
    // Wait a tick for native popovertarget toggle to open, then compute coords
    requestAnimationFrame(() => updatePosition())
  }, [updatePosition])

  return (
    <div className="relative inline-flex">
      {trigger({
        ref: triggerRef,
        popoverTarget: popoverId,
        'aria-expanded': open,
        'aria-controls': popoverId,
        onClick: handleTriggerClick,
      })}

      <div
        id={popoverId}
        ref={popoverRef}
        popover="auto"
        role={role}
        aria-label={ariaLabel}
        style={
          coords
            ? { position: 'fixed', top: `${coords.top}px`, left: `${coords.left}px`, inset: `${coords.top}px auto auto ${coords.left}px` }
            : undefined
        }
        className={`native-popover ${className}`.trim()}
      >
        {children({ close })}
      </div>
    </div>
  )
}
