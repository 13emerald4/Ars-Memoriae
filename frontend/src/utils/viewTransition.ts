/**
 * Safe wrapper around the browser View Transitions API (`document.startViewTransition`).
 * Respects `prefers-reduced-motion: reduce` and falls back to synchronous execution
 * in environments where View Transitions are unavailable.
 */

export interface ViewTransitionDocumentLike {
  startViewTransition?: (updateCallback: () => void) => unknown
}

export function shouldUseViewTransition(
  doc: ViewTransitionDocumentLike | null | undefined,
  prefersReducedMotion: boolean,
): boolean {
  if (prefersReducedMotion) return false
  return Boolean(doc && typeof doc.startViewTransition === 'function')
}

export function runViewTransition(
  update: () => void,
  options?: {
    doc?: ViewTransitionDocumentLike | null
    prefersReducedMotion?: boolean
  },
): boolean {
  const doc =
    options?.doc !== undefined
      ? options.doc
      : typeof document !== 'undefined'
        ? (document as unknown as ViewTransitionDocumentLike)
        : null

  const prefersReducedMotion =
    options?.prefersReducedMotion !== undefined
      ? options.prefersReducedMotion
      : typeof window !== 'undefined' &&
          typeof window.matchMedia === 'function' &&
          window.matchMedia('(prefers-reduced-motion: reduce)').matches

  if (!shouldUseViewTransition(doc, prefersReducedMotion)) {
    update()
    return false
  }

  try {
    doc!.startViewTransition!(update)
    return true
  } catch {
    update()
    return false
  }
}
