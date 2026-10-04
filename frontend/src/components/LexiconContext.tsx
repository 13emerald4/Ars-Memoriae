import { createContext, useContext, useState, useCallback, ReactNode, useEffect, useRef } from 'react'
import { LexiconPopover } from './LexiconPopover'

interface LexiconContextValue {
  openLexicon: (term: string, context?: string | null, position?: { x: number; y: number } | null) => void
  closeLexicon: () => void
  isLexiconOpen: boolean
}

const LexiconContext = createContext<LexiconContextValue | null>(null)

export function useLexicon() {
  const ctx = useContext(LexiconContext)
  if (!ctx) {
    throw new Error('useLexicon must be used within a LexiconProvider')
  }
  return ctx
}

export function LexiconProvider({ children }: { children: ReactNode }) {
  const [isOpen, setIsOpen] = useState(false)
  const isOpenRef = useRef(false)
  isOpenRef.current = isOpen

  const [term, setTerm] = useState<string | null>(null)
  const [context, setContext] = useState<string | null>(null)
  const [position, setPosition] = useState<{ x: number; y: number } | null>(null)

  // Floating selection pill state
  const [selectionPill, setSelectionPill] = useState<{
    text: string
    contextText: string
    x: number
    y: number
  } | null>(null)

  const openLexicon = useCallback(
    (newTerm: string, newContext?: string | null, newPos?: { x: number; y: number } | null) => {
      isOpenRef.current = true
      setSelectionPill(null)
      try {
        window.getSelection()?.removeAllRanges()
      } catch {
        // ignore
      }
      setTerm(newTerm)
      setContext(newContext ?? null)
      setPosition(newPos ?? null)
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

  // Listen for text selection across any reading/lesson passages
  useEffect(() => {
    function handleSelectionChange(e: Event) {
      if (isOpenRef.current) return

      const activeEl = document.activeElement
      if (activeEl && (activeEl.tagName === 'INPUT' || activeEl.tagName === 'TEXTAREA')) {
        setSelectionPill(null)
        return
      }

      // If event happened inside the trigger pill, ignore
      const target = e.target as HTMLElement | null
      if (target && target.closest('[data-lexicon-trigger="true"]')) {
        return
      }

      const sel = window.getSelection()
      if (!sel || sel.isCollapsed) {
        setSelectionPill(null)
        return
      }

      const rawText = sel.toString().trim()
      // Accept terms between 2 and 60 characters (handles single words and compound phrases like "binary approximations")
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
            })
            return
          }
        } catch {
          // Ignore invalid selection ranges
        }
      }
      setSelectionPill(null)
    }

    function handleAltClick(e: MouseEvent) {
      if (!e.altKey) return
      let word = ''
      if (document.caretRangeFromPoint) {
        const range = document.caretRangeFromPoint(e.clientX, e.clientY)
        if (range && range.startContainer.nodeType === Node.TEXT_NODE) {
          const text = range.startContainer.textContent || ''
          const offset = range.startOffset
          const left = text.slice(0, offset).search(/[a-zA-Z0-9_\-]+$/)
          const rightMatch = text.slice(offset).match(/^[a-zA-Z0-9_\-]+/)
          const right = rightMatch ? rightMatch[0].length : 0
          if (left !== -1) {
            word = text.slice(left, offset + right)
          }
        }
      }
      if (word.trim().length >= 2) {
        e.preventDefault()
        e.stopPropagation()
        openLexicon(word.trim(), (e.target as HTMLElement)?.textContent || word, {
          x: e.clientX,
          y: e.clientY,
        })
      }
    }

    document.addEventListener('mouseup', handleSelectionChange)
    document.addEventListener('keyup', handleSelectionChange)
    document.addEventListener('click', handleAltClick)
    return () => {
      document.removeEventListener('mouseup', handleSelectionChange)
      document.removeEventListener('keyup', handleSelectionChange)
      document.removeEventListener('click', handleAltClick)
    }
  }, [openLexicon])

  return (
    <LexiconContext.Provider value={{ openLexicon, closeLexicon, isLexiconOpen: isOpen }}>
      {children}

      {/* Floating Definition Pill above highlighted text */}
      {selectionPill && !isOpen && (
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
              openLexicon(targetText, targetCtx, targetPos)
            }}
            className="flex items-center gap-1.5 rounded-full border border-sky-400/50 bg-sky-950/95 px-3 py-1 text-xs font-semibold text-sky-200 shadow-xl backdrop-blur hover:bg-sky-900 hover:border-sky-300 transition-all hover:scale-105 active:scale-95 cursor-pointer"
          >
            <span>📖</span>
            <span>
              Define{' '}
              <strong className="text-white">
                "{selectionPill.text.length > 22
                  ? selectionPill.text.slice(0, 20) + '…'
                  : selectionPill.text}"
              </strong>
            </span>
          </button>
        </div>
      )}

      {/* Full Lexicon & Concordance Popover */}
      {isOpen && (
        <LexiconPopover
          term={term}
          context={context}
          position={position}
          onClose={closeLexicon}
          onLookupNewTerm={(t) => setTerm(t)}
        />
      )}
    </LexiconContext.Provider>
  )
}
