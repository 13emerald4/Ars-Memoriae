import { useEffect, useRef, type ReactNode } from 'react'

export interface NativeDialogProps {
  open: boolean
  onClose: () => void
  ariaLabel?: string
  ariaLabelledBy?: string
  ariaDescribedBy?: string
  role?: 'dialog' | 'alertdialog'
  variant?: 'modal' | 'drawer' | 'palette'
  closeOnBackdrop?: boolean
  closeOnEscape?: boolean
  className?: string
  children: ReactNode
}

/**
 * Native HTML `<dialog>` wrapper rendered in the browser Top Layer via `.showModal()`.
 * Provides built-in `::backdrop`, automatic `inert` background focus trapping,
 * Escape handling, and pure-CSS `@starting-style` transitions without z-index wars.
 */
export function NativeDialog({
  open,
  onClose,
  ariaLabel,
  ariaLabelledBy,
  ariaDescribedBy,
  role,
  variant = 'modal',
  closeOnBackdrop = true,
  closeOnEscape = true,
  className = '',
  children,
}: NativeDialogProps) {
  const dialogRef = useRef<HTMLDialogElement>(null)
  const onCloseRef = useRef(onClose)
  onCloseRef.current = onClose

  useEffect(() => {
    if (!open) return
    const el = dialogRef.current
    if (!el) return

    if (!el.open) {
      try {
        el.showModal()
      } catch {
        // Fallback for non-standard environments where showModal may throw
        el.setAttribute('open', '')
      }
    }

    // Honour an explicit [data-autofocus] target inside the dialog
    const preferred = el.querySelector<HTMLElement>('[data-autofocus]')
    if (preferred) {
      preferred.focus({ preventScroll: true })
    }

    return () => {
      if (el.open) {
        el.close()
      }
    }
  }, [open])

  if (!open) return null

  const variantClass =
    variant === 'drawer'
      ? 'native-dialog--drawer'
      : variant === 'palette'
        ? 'native-dialog--palette'
        : ''

  return (
    <dialog
      ref={dialogRef}
      role={role}
      aria-modal="true"
      aria-label={ariaLabel}
      aria-labelledby={ariaLabelledBy}
      aria-describedby={ariaDescribedBy}
      onCancel={(e) => {
        e.preventDefault()
        e.stopPropagation()
        if (closeOnEscape) {
          onCloseRef.current()
        }
      }}
      onMouseDown={(e) => {
        if (closeOnBackdrop && e.target === dialogRef.current) {
          e.stopPropagation()
          onCloseRef.current()
        }
      }}
      className={`native-dialog ${variantClass} ${className}`.trim()}
    >
      {children}
    </dialog>
  )
}
