import { useEffect, type RefObject } from 'react'

const FOCUSABLE =
  'a[href], button:not([disabled]), textarea:not([disabled]), input:not([disabled]), select:not([disabled]), [tabindex]:not([tabindex="-1"])'

/** What makes a floating panel behave like a dialog for keyboard and
 *  screen-reader users: focus moves into it, Tab stays inside it, Escape
 *  closes it, and focus returns to whatever opened it.
 *
 *  Pair with `role="dialog"` (or "alertdialog") and `aria-modal="true"` on the
 *  panel element the ref points at. */
export function useDialogA11y(
  ref: RefObject<HTMLElement | null>,
  onClose: () => void,
  options: { active?: boolean; closeOnEscape?: boolean } = {},
) {
  const { active = true, closeOnEscape = true } = options

  useEffect(() => {
    if (!active) return
    const panel = ref.current
    if (!panel) return
    const doc = panel.ownerDocument
    const opener = doc.activeElement instanceof HTMLElement ? doc.activeElement : null

    // Honour an explicit autofocus target; otherwise the first control.
    if (!panel.contains(doc.activeElement)) {
      const preferred =
        panel.querySelector<HTMLElement>('[data-autofocus]') ??
        panel.querySelector<HTMLElement>(FOCUSABLE)
      ;(preferred ?? panel).focus({ preventScroll: true })
    }

    function onKeyDown(e: KeyboardEvent) {
      if (e.key === 'Escape' && closeOnEscape) {
        e.stopPropagation()
        onClose()
        return
      }
      if (e.key !== 'Tab' || !panel) return
      const items = Array.from(panel.querySelectorAll<HTMLElement>(FOCUSABLE)).filter(
        (el) => el.offsetParent !== null || el === doc.activeElement,
      )
      if (items.length === 0) {
        e.preventDefault()
        return
      }
      const first = items[0]
      const last = items[items.length - 1]
      const current = doc.activeElement
      if (e.shiftKey && (current === first || !panel.contains(current))) {
        e.preventDefault()
        last.focus()
      } else if (!e.shiftKey && (current === last || !panel.contains(current))) {
        e.preventDefault()
        first.focus()
      }
    }

    doc.addEventListener('keydown', onKeyDown, true)
    return () => {
      doc.removeEventListener('keydown', onKeyDown, true)
      if (opener && opener.isConnected) opener.focus({ preventScroll: true })
    }
    // onClose is intentionally not a dependency: callers pass inline closures,
    // and re-running this on every render would steal focus back each time.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [active, closeOnEscape, ref])
}
