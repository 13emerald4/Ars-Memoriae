import { createContext, useContext, useState, useCallback, ReactNode, useEffect, useRef } from 'react'
import { createPortal } from 'react-dom'
import type { LexiconGlossItem } from '../api/types'
import { LexiconPopover } from './LexiconPopover'

export interface ActiveDeckContext {
  cardId?: string | null
  deckName?: string | null
  thematicNature?: string | null
  existingGlosses?: LexiconGlossItem[]
  onGlossesUpdated?: (glosses: LexiconGlossItem[]) => void
}

export type MarginLookupListener = (term: string, context?: string | null) => void
export type MarginPopulateListener = (
  entries: LexiconGlossItem[],
  serverUpdatedGlosses?: LexiconGlossItem[] | null,
) => void

interface LexiconContextValue {
  openLexicon: (
    term?: string | null,
    context?: string | null,
    position?: { x: number; y: number } | null,
    overrideDeckContext?: ActiveDeckContext | null,
  ) => void
  closeLexicon: () => void
  isLexiconOpen: boolean
  setActiveDeckContext: (ctx: ActiveDeckContext | null) => void
  activeDeckContext: ActiveDeckContext | null
  syncCardGlosses: (cardId: string | null | undefined, glosses: LexiconGlossItem[]) => void
  registerDocument: (doc: Document | null | undefined) => () => void
  registerMarginListener: (listener: MarginLookupListener | null) => () => void
  hasMarginListener: boolean
  registerPopulateListener: (listener: MarginPopulateListener | null) => () => void
  populateCardGlosses: (
    entries: LexiconGlossItem[],
    serverUpdatedGlosses?: LexiconGlossItem[] | null,
  ) => void
}

const LexiconContext = createContext<LexiconContextValue | null>(null)

export function useLexicon() {
  const ctx = useContext(LexiconContext)
  if (!ctx) {
    throw new Error('useLexicon must be used within a LexiconProvider')
  }
  return ctx
}

export function useOptionalLexicon() {
  return useContext(LexiconContext)
}

export function LexiconProvider({ children }: { children: ReactNode }) {
  const [isOpen, setIsOpen] = useState(false)
  const isOpenRef = useRef(false)
  isOpenRef.current = isOpen

  const marginListenersRef = useRef<Set<MarginLookupListener>>(new Set())
  const [hasMarginListener, setHasMarginListener] = useState(false)

  const registerMarginListener = useCallback((listener: MarginLookupListener | null) => {
    if (!listener) {
      marginListenersRef.current.clear()
      setHasMarginListener(false)
      return () => {}
    }
    marginListenersRef.current.add(listener)
    setHasMarginListener(marginListenersRef.current.size > 0)
    return () => {
      marginListenersRef.current.delete(listener)
      setHasMarginListener(marginListenersRef.current.size > 0)
    }
  }, [])

  const populateListenersRef = useRef<Set<MarginPopulateListener>>(new Set())
  const registerPopulateListener = useCallback((listener: MarginPopulateListener | null) => {
    if (!listener) {
      populateListenersRef.current.clear()
      return () => {}
    }
    populateListenersRef.current.add(listener)
    return () => {
      populateListenersRef.current.delete(listener)
    }
  }, [])

  const [registeredDocs, setRegisteredDocs] = useState<Document[]>([])
  const registerDocument = useCallback((doc: Document | null | undefined) => {
    if (!doc || doc === document) return () => {}
    setRegisteredDocs((prev) => (prev.includes(doc) ? prev : [...prev, doc]))
    return () => {
      setRegisteredDocs((prev) => prev.filter((d) => d !== doc))
    }
  }, [])

  const [term, setTerm] = useState<string | null>(null)
  const [context, setContext] = useState<string | null>(null)
  const [position, setPosition] = useState<{ x: number; y: number } | null>(null)
  const [activeDeckContext, setActiveDeckContext] = useState<ActiveDeckContext | null>(null)
  const activeDeckContextRef = useRef<ActiveDeckContext | null>(null)
  activeDeckContextRef.current = activeDeckContext
  const [currentLookupDeckContext, setCurrentLookupDeckContext] = useState<ActiveDeckContext | null>(null)

  const syncCardGlosses = useCallback(
    (cardId: string | null | undefined, glosses: LexiconGlossItem[]) => {
      if (!cardId) return
      setActiveDeckContext((prev) =>
        prev && prev.cardId === cardId ? { ...prev, existingGlosses: glosses } : prev,
      )
      setCurrentLookupDeckContext((prev) =>
        prev && prev.cardId === cardId ? { ...prev, existingGlosses: glosses } : prev,
      )
    },
    [],
  )

  const populateCardGlosses = useCallback(
    (entries: LexiconGlossItem[], serverUpdatedGlosses?: LexiconGlossItem[] | null) => {
      if (serverUpdatedGlosses && activeDeckContextRef.current?.cardId) {
        syncCardGlosses(activeDeckContextRef.current.cardId, serverUpdatedGlosses)
        activeDeckContextRef.current.onGlossesUpdated?.(serverUpdatedGlosses)
      }
      populateListenersRef.current.forEach((listener) => {
        listener(entries, serverUpdatedGlosses)
      })
    },
    [syncCardGlosses],
  )

  // Floating selection pill state
  const [selectionPill, setSelectionPill] = useState<{
    text: string
    contextText: string
    x: number
    y: number
    targetDoc: Document
  } | null>(null)
  const selectionPillRef = useRef(selectionPill)
  selectionPillRef.current = selectionPill

  const openLexicon = useCallback(
    (
      newTerm?: string | null,
      newContext?: string | null,
      newPos?: { x: number; y: number } | null,
      overrideDeckContext?: ActiveDeckContext | null,
    ) => {
      const prevDoc = selectionPillRef.current?.targetDoc
      setSelectionPill(null)
      try {
        window.getSelection()?.removeAllRanges()
        if (prevDoc && prevDoc !== document) {
          prevDoc.getSelection()?.removeAllRanges()
        }
      } catch {
        // ignore
      }

      if (marginListenersRef.current.size > 0) {
        marginListenersRef.current.forEach((listener) => {
          listener(newTerm ?? '', newContext ?? null)
        })
        return
      }

      isOpenRef.current = true
      setTerm(newTerm ?? null)
      setContext(newContext ?? null)
      setPosition(newPos ?? null)
      setCurrentLookupDeckContext(
        overrideDeckContext !== undefined ? overrideDeckContext : activeDeckContextRef.current,
      )
      setIsOpen(true)
    },
    [],
  )

  const closeLexicon = useCallback(() => {
    isOpenRef.current = false
    setIsOpen(false)
    setTerm(null)
    setSelectionPill(null)
  }, [])

  // Listen for text selection across main and registered popout reading/lesson documents
  useEffect(() => {
    const docs = [document, ...registeredDocs]
    const cleanups: Array<() => void> = []

    const handleSelectionForDoc = (doc: Document, e: Event) => {
      if (isOpenRef.current) return

      const activeEl = doc.activeElement
      if (activeEl && (activeEl.tagName === 'INPUT' || activeEl.tagName === 'TEXTAREA')) {
        setSelectionPill(null)
        return
      }

      const target = e.target as HTMLElement | null
      if (target && target.closest('[data-lexicon-trigger="true"]')) {
        return
      }

      const sel = doc.getSelection()
      if (!sel || sel.isCollapsed) {
        setSelectionPill(null)
        return
      }

      const rawText = sel.toString().trim()
      if (rawText.length >= 2 && rawText.length <= 60 && !rawText.includes('\n')) {
        try {
          const range = sel.getRangeAt(0)
          const rect = range.getBoundingClientRect()
          if (rect.width > 0 && rect.height > 0) {
            const parentBlock = range.commonAncestorContainer.parentElement
            const contextText = parentBlock?.textContent?.slice(0, 500) || rawText

            setSelectionPill({
              text: rawText,
              contextText,
              x: rect.left + rect.width / 2,
              y: Math.max(10, rect.top - 8),
              targetDoc: doc,
            })
            return
          }
        } catch {
          // Ignore invalid selection ranges
        }
      }
      setSelectionPill(null)
    }

    const handleAltClickForDoc = (doc: Document, e: MouseEvent) => {
      if (!e.altKey) return
      let word = ''
      if (doc.caretRangeFromPoint) {
        const range = doc.caretRangeFromPoint(e.clientX, e.clientY)
        if (range && range.startContainer.nodeType === Node.TEXT_NODE) {
          const text = range.startContainer.textContent || ''
          const offset = range.startOffset
          const left = text.slice(0, offset).search(/[a-zA-Z0-9_\-.]+$/)
          const rightMatch = text.slice(offset).match(/^[a-zA-Z0-9_\-.()]+/)
          const right = rightMatch ? rightMatch[0].length : 0
          if (left !== -1) {
            word = text.slice(left, offset + right)
          }
        }
      }
      if (word.trim().length >= 2) {
        e.preventDefault()
        e.stopPropagation()
        openLexicon(
          word.trim(),
          (e.target as HTMLElement)?.textContent || word,
          {
            x: e.clientX,
            y: e.clientY,
          },
          activeDeckContextRef.current,
        )
      }
    }

    for (const doc of docs) {
      try {
        if (doc.defaultView?.closed) continue
      } catch {
        continue
      }
      const onSel = (e: Event) => handleSelectionForDoc(doc, e)
      const onAlt = (e: MouseEvent) => handleAltClickForDoc(doc, e)
      doc.addEventListener('mouseup', onSel)
      doc.addEventListener('keyup', onSel)
      doc.addEventListener('click', onAlt)
      cleanups.push(() => {
        try {
          doc.removeEventListener('mouseup', onSel)
          doc.removeEventListener('keyup', onSel)
          doc.removeEventListener('click', onAlt)
        } catch {
          // ignore if popup was closed
        }
      })
    }

    return () => {
      cleanups.forEach((fn) => fn())
    }
  }, [openLexicon, registeredDocs])

  const pillElement =
    selectionPill && !isOpen ? (
      <div
        style={{
          position: 'fixed',
          left: `${selectionPill.x}px`,
          top: `${selectionPill.y}px`,
          zIndex: 9998,
          transform: 'translate(-50%, -100%)',
        }}
        className="animate-in fade-in zoom-in-95 duration-100"
      >
        <button
          type="button"
          data-lexicon-trigger="true"
          onMouseDown={(e) => {
            e.stopPropagation()
          }}
          onClick={(e) => {
            e.preventDefault()
            e.stopPropagation()
            const targetText = selectionPill.text
            const targetCtx = selectionPill.contextText
            const targetPos = { x: selectionPill.x, y: selectionPill.y }
            openLexicon(targetText, targetCtx, targetPos, activeDeckContextRef.current)
          }}
          className="flex items-center gap-1.5 rounded-full border border-sky-400/50 bg-sky-950/95 px-3 py-1 text-xs font-semibold text-sky-200 shadow-xl backdrop-blur hover:bg-sky-900 hover:border-sky-300 transition-all hover:scale-105 active:scale-95 cursor-pointer"
        >
          <span>
            Define{' '}
            <strong className="text-white">
              &ldquo;{selectionPill.text.length > 22
                ? selectionPill.text.slice(0, 20) + '…'
                : selectionPill.text}&rdquo;
            </strong>
          </span>
        </button>
      </div>
    ) : null

  return (
    <LexiconContext.Provider
      value={{
        openLexicon,
        closeLexicon,
        isLexiconOpen: isOpen,
        setActiveDeckContext,
        activeDeckContext,
        syncCardGlosses,
        registerDocument,
        registerMarginListener,
        hasMarginListener,
        registerPopulateListener,
        populateCardGlosses,
      }}
    >
      {children}

      {/* Floating Definition Pill above highlighted text (supports popout window documents) */}
      {pillElement &&
        (selectionPill?.targetDoc && selectionPill.targetDoc !== document && selectionPill.targetDoc.body
          ? createPortal(pillElement, selectionPill.targetDoc.body)
          : pillElement)}

      {/* Full Lexicon & Concordance Popover */}
      {isOpen && (
        <LexiconPopover
          term={term}
          context={context}
          cardId={currentLookupDeckContext?.cardId ?? activeDeckContext?.cardId}
          deckName={currentLookupDeckContext?.deckName ?? activeDeckContext?.deckName}
          thematicNature={currentLookupDeckContext?.thematicNature ?? activeDeckContext?.thematicNature}
          existingGlosses={currentLookupDeckContext?.existingGlosses ?? activeDeckContext?.existingGlosses}
          onAddedToCard={(updatedGlosses) => {
            const cId = currentLookupDeckContext?.cardId ?? activeDeckContext?.cardId
            syncCardGlosses(cId, updatedGlosses)
            currentLookupDeckContext?.onGlossesUpdated?.(updatedGlosses)
            activeDeckContext?.onGlossesUpdated?.(updatedGlosses)
          }}
          position={position}
          onClose={closeLexicon}
          onLookupNewTerm={(t) => setTerm(t)}
        />
      )}
    </LexiconContext.Provider>
  )
}
