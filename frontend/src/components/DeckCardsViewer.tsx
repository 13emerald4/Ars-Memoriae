import { useEffect, useState, useMemo, useCallback, useRef } from 'react'
import { api } from '../api/client'
import type { Deck, DeckDocumentOut, DeckStats, QueueItem } from '../api/types'
import { CodeEditor } from './CodeEditor'
import { RichText } from './ui'
import { isCodeCard, extractCleanCode, detectCodeLanguage } from '../utils/codeUtils'
import { CardAnalyticsModal } from './CardAnalyticsModal'
import { CompactDeckDistributionBars, CompactCardProgressionBar } from './DeckReviewStatsBar'

export interface CardCommentItem {
  id: string
  text: string
  createdAt: string
}

export function loadCardComments(cardId: string): CardCommentItem[] {
  try {
    const raw = localStorage.getItem(`ars_card_comments_${cardId}`)
    return raw ? JSON.parse(raw) : []
  } catch {
    return []
  }
}

export function persistCardComments(cardId: string, list: CardCommentItem[]) {
  try {
    localStorage.setItem(`ars_card_comments_${cardId}`, JSON.stringify(list))
  } catch {
    // ignore
  }
}

export interface DeckCardsViewerProps {
  isOpen: boolean
  onClose: () => void
  deckId: string | null
  deckName?: string | null
  currentCardId?: string | null
  onSelectCard?: (card: QueueItem) => void
  codeLanguage?: string
  allDecks?: Deck[]
}

interface DropdownDeckNode {
  id: string
  title: string
  parentId: string | null
  elementCount: number
  stats?: DeckStats | null
  children: DropdownDeckNode[]
}

function buildDropdownDeckTree(decks: Deck[]): DropdownDeckNode[] {
  const childrenMap = new Map<string | null, Deck[]>()
  for (const d of decks) {
    const p = d.parent_id || null
    if (!childrenMap.has(p)) childrenMap.set(p, [])
    childrenMap.get(p)!.push(d)
  }

  function nodeFor(d: Deck): DropdownDeckNode {
    const kids = (childrenMap.get(d.id) || []).map(nodeFor)
    return {
      id: d.id,
      title: d.name,
      parentId: d.parent_id,
      elementCount: d.total_card_count ?? d.card_count,
      stats: d.stats,
      children: kids,
    }
  }

  const deckIds = new Set(decks.map((d) => d.id))
  const roots = decks.filter((d) => !d.parent_id || !deckIds.has(d.parent_id))
  return roots.map(nodeFor)
}

export function DeckCardsViewer({
  isOpen,
  onClose,
  deckId,
  deckName,
  currentCardId,
  onSelectCard,
  codeLanguage = 'typescript',
  allDecks: propDecks,
}: DeckCardsViewerProps) {
  const [cards, setCards] = useState<QueueItem[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [selectedCardId, setSelectedCardId] = useState<string | null>(null)
  const [analyticsCardId, setAnalyticsCardId] = useState<string | null>(null)
  const [searchQuery, setSearchQuery] = useState('')
  const [filterType, setFilterType] = useState<'all' | 'code' | 'flashcard'>('all')
  const [filterDifficulty, setFilterDifficulty] = useState<'all' | 'easy' | 'medium' | 'hard'>('all')
  const [copiedCode, setCopiedCode] = useState(false)
  const [showTestsSection, setShowTestsSection] = useState(false)

  // Active deck state (supports switching decks via dropdown in viewer)
  const [activeDeckId, setActiveDeckId] = useState<string | null>(deckId)
  const [activeDeckName, setActiveDeckName] = useState<string | null>(deckName || null)
  const [allDecks, setAllDecks] = useState<Deck[]>(propDecks || [])
  const [showDeckDropdown, setShowDeckDropdown] = useState(false)
  const [deckSearchQuery, setDeckSearchQuery] = useState('')
  const [expandedDeckIds, setExpandedDeckIds] = useState<Set<string>>(new Set())
  const dropdownRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    setActiveDeckId(deckId)
    setActiveDeckName(deckName || null)
  }, [deckId, deckName])

  // Fetch all decks and stats when viewer is open
  useEffect(() => {
    if (!isOpen) return
    api.decks().then((data) => {
      setAllDecks(data)
      setExpandedDeckIds(new Set(data.map((d) => d.id)))
    }).catch(() => {})
  }, [isOpen])

  // Close dropdown on click outside
  useEffect(() => {
    if (!showDeckDropdown) return
    const handleMouseDown = (e: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target as Node)) {
        setShowDeckDropdown(false)
      }
    }
    window.addEventListener('mousedown', handleMouseDown)
    return () => window.removeEventListener('mousedown', handleMouseDown)
  }, [showDeckDropdown])

  const currentDeck = useMemo(() => {
    if (!activeDeckId) return null
    return allDecks.find((d) => d.id === activeDeckId) || null
  }, [allDecks, activeDeckId])

  const currentDeckStats = useMemo(() => {
    return currentDeck?.stats || null
  }, [currentDeck])

  const deckTree = useMemo(() => {
    return buildDropdownDeckTree(allDecks)
  }, [allDecks])

  // High-level short comments for cards (displayed where "Active" badge sits)
  const [shortComments, setShortComments] = useState<Record<string, string>>(() => {
    try {
      const raw = localStorage.getItem('ars_card_short_comments')
      return raw ? JSON.parse(raw) : {}
    } catch {
      return {}
    }
  })
  const [editingShortCommentCardId, setEditingShortCommentCardId] = useState<string | null>(null)
  const [editingShortCommentText, setEditingShortCommentText] = useState('')

  const handleSaveShortComment = (cardId: string, text: string) => {
    const trimmed = text.trim()
    setShortComments((prev) => {
      const next = { ...prev }
      if (trimmed) {
        next[cardId] = trimmed
      } else {
        delete next[cardId]
      }
      try {
        localStorage.setItem('ars_card_short_comments', JSON.stringify(next))
      } catch {
        // ignore
      }
      return next
    })
    setEditingShortCommentCardId(null)
    setEditingShortCommentText('')
  }

  // Deck documentation state
  const [deckDocs, setDeckDocs] = useState<DeckDocumentOut[]>([])
  const [showDocsModal, setShowDocsModal] = useState(false)
  const [selectedFile, setSelectedFile] = useState<File | null>(null)
  const [docTitle, setDocTitle] = useState('')
  const [uploadingDoc, setUploadingDoc] = useState(false)
  const [docUploadError, setDocUploadError] = useState<string | null>(null)
  const [deletingDocId, setDeletingDocId] = useState<string | null>(null)

  // Neuroscience & Memory Palace state
  const [autoPalacing, setAutoPalacing] = useState(false)
  const [editingLocus, setEditingLocus] = useState('')
  const [editingMnemonic, setEditingMnemonic] = useState('')
  const [savingNeuroProps, setSavingNeuroProps] = useState(false)
  const [generatingMnemonic, setGeneratingMnemonic] = useState(false)

  // Fetch cards when opened
  const loadCards = useCallback(async (id: string) => {
    try {
      setLoading(true)
      setError(null)
      const data = await api.deckPersistItems(id)
      const sorted = [...data].sort((a, b) => {
        if (a.position != null && b.position != null) {
          return a.position - b.position
        }
        return 0
      })
      setCards(sorted)
      if (sorted.length > 0) {
        // If current card is in list, select it; otherwise select first card
        if (currentCardId && sorted.some((c) => c.id === currentCardId)) {
          setSelectedCardId(currentCardId)
        } else {
          setSelectedCardId(sorted[0].id)
        }
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err))
    } finally {
      setLoading(false)
    }
  }, [currentCardId])

  // Fetch deck documentation
  const loadDeckDocs = useCallback(async (id: string) => {
    try {
      const res = await api.getDeckDocuments(id)
      setDeckDocs(res?.documents || [])
    } catch {
      // ignore
    }
  }, [])

  useEffect(() => {
    if (isOpen && activeDeckId) {
      void loadCards(activeDeckId)
      void loadDeckDocs(activeDeckId)
    }
  }, [isOpen, activeDeckId, loadCards, loadDeckDocs])

  const handleSelectDeckFromDropdown = (id: string, name: string) => {
    setActiveDeckId(id)
    setActiveDeckName(name)
    setShowDeckDropdown(false)
    void loadCards(id)
    void loadDeckDocs(id)
  }

  const handleUploadDocument = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!activeDeckId || !selectedFile) return
    setUploadingDoc(true)
    setDocUploadError(null)
    try {
      const res = await api.uploadDeckDocument(activeDeckId, selectedFile, docTitle.trim() || undefined)
      setDeckDocs((prev) => [res, ...prev])
      setSelectedFile(null)
      setDocTitle('')
    } catch (err: any) {
      setDocUploadError(err?.message || 'Failed to upload document.')
    } finally {
      setUploadingDoc(false)
    }
  }

  const handleDeleteDocument = async (docId: string) => {
    if (!activeDeckId) return
    setDeletingDocId(docId)
    try {
      await api.deleteDeckDocument(activeDeckId, docId)
      setDeckDocs((prev) => prev.filter((d) => d.id !== docId && d.source_id !== docId))
    } catch (err: any) {
      alert(err?.message || 'Failed to delete document.')
    } finally {
      setDeletingDocId(null)
    }
  }

  // Close on Escape key
  useEffect(() => {
    if (!isOpen) return
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        e.preventDefault()
        onClose()
      }
    }
    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [isOpen, onClose])

  // Filter cards based on search query and filter pills
  const filteredCards = useMemo(() => {
    const q = searchQuery.toLowerCase().trim()
    return cards.filter((c) => {
      // Filter Type
      if (filterType === 'code' && !isCodeCard(c)) return false
      if (filterType === 'flashcard' && isCodeCard(c)) return false

      // Filter Difficulty
      if (filterDifficulty !== 'all') {
        const diff = (c.difficulty || '').toLowerCase()
        if (diff !== filterDifficulty) return false
      }

      // Search query
      if (q) {
        const titleMatch = (c.title || '').toLowerCase().includes(q)
        const frontMatch = (c.front || '').toLowerCase().includes(q)
        const backMatch = (c.back || '').toLowerCase().includes(q)
        const catMatch = (c.category || '').toLowerCase().includes(q)
        const tcMatch = (c.time_complexity || '').toLowerCase().includes(q)
        return titleMatch || frontMatch || backMatch || catMatch || tcMatch
      }

      return true
    })
  }, [cards, searchQuery, filterType, filterDifficulty])

  const selectedCard = useMemo(() => {
    return cards.find((c) => c.id === selectedCardId) || filteredCards[0] || null
  }, [cards, selectedCardId, filteredCards])

  // Card comments state
  const [commentsVersion, setCommentsVersion] = useState(0)
  const [showCommentsPopover, setShowCommentsPopover] = useState(false)
  const [newCommentText, setNewCommentText] = useState('')

  const currentCardComments = useMemo(() => {
    if (!selectedCard?.id) return []
    void commentsVersion
    return loadCardComments(selectedCard.id)
  }, [selectedCard?.id, commentsVersion])

  const handleAddComment = (e?: React.FormEvent) => {
    if (e) e.preventDefault()
    if (!selectedCard?.id || !newCommentText.trim()) return

    const newComment: CardCommentItem = {
      id: `${Date.now()}-${Math.random().toString(36).slice(2, 7)}`,
      text: newCommentText.trim(),
      createdAt: new Date().toISOString(),
    }
    const updated = [newComment, ...currentCardComments]
    persistCardComments(selectedCard.id, updated)
    setNewCommentText('')
    setCommentsVersion((v) => v + 1)
  }

  const handleDeleteComment = (commentId: string) => {
    if (!selectedCard?.id) return
    const updated = currentCardComments.filter((c) => c.id !== commentId)
    persistCardComments(selectedCard.id, updated)
    setCommentsVersion((v) => v + 1)
  }

  const handleCopyCode = async (code: string) => {
    try {
      await navigator.clipboard.writeText(code)
      setCopiedCode(true)
      setTimeout(() => setCopiedCode(false), 2000)
    } catch {
      // ignore
    }
  }

  // Synchronize editing fields with the currently selected card
  useEffect(() => {
    if (selectedCard) {
      setEditingLocus(selectedCard.spatial_locus || '')
      setEditingMnemonic(selectedCard.mnemonic_vignette || '')
    }
  }, [selectedCard?.id, selectedCard?.spatial_locus, selectedCard?.mnemonic_vignette])

  const handleToggleSchemaCheckpoint = async () => {
    if (!selectedCard) return
    setSavingNeuroProps(true)
    try {
      const nextVal = !selectedCard.is_schema_checkpoint
      await api.updateCardNeuroProps(selectedCard.id, { is_schema_checkpoint: nextVal })
      setCards((prev) =>
        prev.map((c) => (c.id === selectedCard.id ? { ...c, is_schema_checkpoint: nextVal } : c)),
      )
    } catch (err: any) {
      alert(err?.message || 'Failed to update schema checkpoint status.')
    } finally {
      setSavingNeuroProps(false)
    }
  }

  const handleSaveLocus = async () => {
    if (!selectedCard) return
    setSavingNeuroProps(true)
    try {
      const val = editingLocus.trim() || null
      await api.updateCardNeuroProps(selectedCard.id, { spatial_locus: val })
      setCards((prev) =>
        prev.map((c) => (c.id === selectedCard.id ? { ...c, spatial_locus: val || undefined } : c)),
      )
    } catch (err: any) {
      alert(err?.message || 'Failed to update spatial locus.')
    } finally {
      setSavingNeuroProps(false)
    }
  }

  const handleSaveMnemonic = async () => {
    if (!selectedCard) return
    setSavingNeuroProps(true)
    try {
      const val = editingMnemonic.trim() || null
      await api.updateCardNeuroProps(selectedCard.id, { mnemonic_vignette: val })
      setCards((prev) =>
        prev.map((c) => (c.id === selectedCard.id ? { ...c, mnemonic_vignette: val || undefined } : c)),
      )
    } catch (err: any) {
      alert(err?.message || 'Failed to update mnemonic vignette.')
    } finally {
      setSavingNeuroProps(false)
    }
  }

  const handleGenerateMnemonic = async () => {
    if (!selectedCard) return
    setGeneratingMnemonic(true)
    try {
      const res = await api.generateMnemonic(selectedCard.id)
      setEditingMnemonic(res.mnemonic_vignette)
      setCards((prev) =>
        prev.map((c) =>
          c.id === selectedCard.id ? { ...c, mnemonic_vignette: res.mnemonic_vignette } : c,
        ),
      )
    } catch (err: any) {
      alert(err?.message || 'Failed to generate mnemonic vignette.')
    } finally {
      setGeneratingMnemonic(false)
    }
  }

  const handleAutoPalace = async () => {
    if (!activeDeckId || activeDeckId === '__root__') return
    setAutoPalacing(true)
    try {
      await api.autoPalace(activeDeckId)
      await loadCards(activeDeckId)
    } catch (err: any) {
      alert(err?.message || 'Failed to auto-generate memory palace layout.')
    } finally {
      setAutoPalacing(false)
    }
  }

  const renderDropdownNode = (node: DropdownDeckNode, depth = 0): React.ReactNode => {
    const isCurrent = node.id === activeDeckId
    const hasKids = node.children && node.children.length > 0
    const isExpanded = expandedDeckIds.has(node.id)

    // Filter check: matches search query or has matching descendant
    const query = deckSearchQuery.trim().toLowerCase()
    const matchesQuery = !query || node.title.toLowerCase().includes(query)
    const hasMatchingChild = (children: DropdownDeckNode[]): boolean => {
      return children.some((c) => c.title.toLowerCase().includes(query) || hasMatchingChild(c.children))
    }
    if (query && !matchesQuery && !hasMatchingChild(node.children)) {
      return null
    }

    return (
      <div key={node.id} className="space-y-0.5">
        <div
          onClick={() => handleSelectDeckFromDropdown(node.id, node.title)}
          className={`flex items-center justify-between gap-2 px-2.5 py-1.5 rounded-xl transition cursor-pointer text-xs group ${
            isCurrent
              ? 'bg-sky-950/80 border border-sky-500/60 text-white shadow-md ring-1 ring-sky-500/30'
              : 'hover:bg-[#1a2233] text-slate-200 border border-transparent'
          }`}
          style={{ paddingLeft: `${Math.max(10, depth * 18 + 10)}px` }}
        >
          <div className="flex items-center gap-2 min-w-0 flex-1">
            {hasKids ? (
              <button
                type="button"
                onClick={(e) => {
                  e.stopPropagation()
                  setExpandedDeckIds((prev) => {
                    const next = new Set(prev)
                    if (next.has(node.id)) next.delete(node.id)
                    else next.add(node.id)
                    return next
                  })
                }}
                className="w-4 h-4 flex items-center justify-center rounded hover:bg-slate-700/50 text-slate-400 hover:text-sky-300 transition shrink-0"
                title={isExpanded ? 'Collapse subdecks' : 'Expand subdecks'}
              >
                <span className="text-[10px] select-none">{isExpanded ? '▼' : '▶'}</span>
              </button>
            ) : (
              <span className="w-4 shrink-0" />
            )}

            {/* Deck Icon [T] styled like Image 1 */}
            <span className="w-4 h-4 rounded flex items-center justify-center text-[10px] font-bold border border-amber-500/50 bg-amber-500/20 text-amber-300 shrink-0 select-none">
              T
            </span>

            <span className="font-medium truncate group-hover:text-white transition select-none">
              {node.title}
            </span>

            <span className="text-[11px] font-mono text-slate-400 shrink-0">
              ({node.elementCount})
            </span>
          </div>

          {/* Progression Bars in Dropdown Menu */}
          <div className="flex items-center gap-1.5 shrink-0">
            {node.stats && node.stats.total_cards > 0 && (
              <CompactDeckDistributionBars stats={node.stats} className="shrink-0" />
            )}
            {isCurrent && (
              <span className="text-sky-400 font-bold text-xs ml-1 select-none">✓</span>
            )}
          </div>
        </div>

        {/* Children indented with guide line */}
        {hasKids && (isExpanded || Boolean(query)) && (
          <div className="relative pl-1">
            <div
              className="absolute top-0 bottom-1 w-px bg-slate-700/50"
              style={{ left: `${depth * 18 + 18}px` }}
            />
            {node.children.map((child) => renderDropdownNode(child, depth + 1))}
          </div>
        )}
      </div>
    )
  }

  if (!isOpen) return null

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-label="Deck cards browser"
      className="fixed inset-0 z-50 flex items-center justify-center p-3 sm:p-5 bg-black/80 backdrop-blur-sm animate-in fade-in duration-200"
    >
      <div className="flex flex-col w-full max-w-7xl h-[92vh] max-h-[920px] rounded-2xl border border-sky-500/30 bg-[#12161f] shadow-2xl overflow-hidden text-slate-200">
        {/* ── Top Header Bar ── */}
        <div className="flex flex-wrap items-center justify-between border-b border-ink-line/80 bg-[#181e2b] px-4 py-3 gap-3">
          <div className="flex items-center gap-3">
            <div className="relative" ref={dropdownRef}>
              <div className="flex items-center gap-2">
                <button
                  type="button"
                  onClick={() => setShowDeckDropdown((prev) => !prev)}
                  className="flex items-center gap-2 px-2.5 py-1 -ml-2 rounded-xl border border-sky-500/30 hover:border-sky-400/60 bg-[#151c2a] hover:bg-[#1c2436] transition cursor-pointer text-left group shadow-sm"
                  title="Click to switch deck in viewer"
                >
                  <div className="flex items-center gap-1.5 min-w-0">
                    <span className="w-4 h-4 rounded flex items-center justify-center text-[10px] font-bold border border-amber-500/50 bg-amber-500/20 text-amber-300 shrink-0 select-none">
                      T
                    </span>
                    <h3 className="font-bold text-white text-sm sm:text-base group-hover:text-sky-200 transition truncate max-w-[240px] sm:max-w-md">
                      {currentDeck?.name || activeDeckName || deckName || selectedCard?.deck_name || 'Cards'}
                    </h3>
                    <span className="text-[10px] text-sky-400 transition ml-0.5 select-none shrink-0">
                      {showDeckDropdown ? '▲' : '▼'}
                    </span>
                  </div>

                  <span className="rounded-full bg-sky-950/90 border border-sky-500/40 px-2.5 py-0.5 text-xs font-mono text-sky-200 shrink-0">
                    {cards.length} {cards.length === 1 ? 'card' : 'cards'}
                  </span>

                  {/* Header Progression Bars for Current Deck */}
                  {currentDeckStats && currentDeckStats.total_cards > 0 && (
                    <CompactDeckDistributionBars stats={currentDeckStats} className="ml-1 shrink-0" />
                  )}
                </button>

                {loading && (
                  <span className="text-xs text-sky-400 animate-pulse">Loading…</span>
                )}
              </div>

              <p className="text-[11px] text-slate-400 mt-0.5">
                Browse cards in this deck. Click title to switch deck. <kbd className="px-1 rounded bg-[#252f42] text-[10px] font-mono border border-ink-line">Esc</kbd> to close.
              </p>

              {/* ── Dropdown Menu with Decks & Progression Bars ── */}
              {showDeckDropdown && (
                <div
                  className="absolute left-0 top-full mt-2 w-[340px] sm:w-[480px] max-h-[500px] rounded-2xl bg-[#121622] border border-sky-500/40 shadow-2xl z-50 backdrop-blur-xl flex flex-col animate-in fade-in zoom-in-95 duration-150 overflow-hidden"
                >
                  {/* Dropdown Header */}
                  <div className="p-3 border-b border-ink-line/80 bg-[#161c2b] flex items-center justify-between gap-2">
                    <div className="flex items-center gap-1.5 text-xs font-bold text-sky-300">
                      <span>Decks & Progression</span>
                      <span className="rounded-full bg-sky-500/20 px-2 py-0.2 text-[10px] font-mono text-sky-300">
                        {allDecks.length}
                      </span>
                    </div>
                    <button
                      type="button"
                      onClick={() => setShowDeckDropdown(false)}
                      className="text-slate-400 hover:text-slate-200 text-xs px-1.5 py-0.5 rounded hover:bg-white/10 cursor-pointer"
                    >
                      ✕
                    </button>
                  </div>

                  {allDecks.length > 5 && (
                    <div className="p-2 border-b border-ink-line/60 bg-[#141a27]">
                      <input
                        type="text"
                        value={deckSearchQuery}
                        onChange={(e) => setDeckSearchQuery(e.target.value)}
                        placeholder="Search decks…"
                        className="w-full text-xs rounded-lg bg-[#0d121c] border border-ink-line px-2.5 py-1 text-slate-100 placeholder-slate-500 focus:outline-none focus:border-sky-500"
                        autoFocus
                      />
                    </div>
                  )}

                  {/* Dropdown Items List with Tree/Hierarchy and Progression Bars */}
                  <div className="flex-1 overflow-y-auto p-2 space-y-1 divide-y divide-ink-line/20">
                    {deckTree.length === 0 ? (
                      <div className="p-4 text-center text-xs text-slate-500">
                        No decks found.
                      </div>
                    ) : (
                      deckTree.map((rootNode) => renderDropdownNode(rootNode, 0))
                    )}
                  </div>
                </div>
              )}
            </div>
          </div>

          <div className="flex items-center gap-2">
            {activeDeckId && (
              <>
                <button
                  type="button"
                  disabled={autoPalacing}
                  onClick={handleAutoPalace}
                  className="flex items-center gap-1.5 px-2.5 py-1 text-xs font-medium rounded-lg border border-purple-500/40 bg-purple-950/40 hover:bg-purple-900/50 text-purple-200 transition cursor-pointer shadow-sm disabled:opacity-40"
                  title="Auto-organize deck cards into virtual memory palace rooms and loci"
                >
                  <span>🏛️</span>
                  <span>{autoPalacing ? 'Palacing…' : 'Auto-Palace'}</span>
                </button>
                <button
                  type="button"
                  onClick={() => setShowDocsModal(true)}
                  className="flex items-center gap-1.5 px-2.5 py-1 text-xs font-medium rounded-lg border border-emerald-500/40 bg-emerald-950/40 hover:bg-emerald-900/50 text-emerald-200 transition cursor-pointer shadow-sm"
                  title="Manage attached reference documents for this deck"
                >
                  <span>📄</span>
                  <span>Deck Docs</span>
                  <span className="px-1.5 py-0.2 rounded-full bg-emerald-500/20 text-[10px] font-mono text-emerald-300">
                    {deckDocs.length}
                  </span>
                </button>
                <button
                  type="button"
                  onClick={() => {
                    void loadCards(activeDeckId)
                    void loadDeckDocs(activeDeckId)
                    void api.decks().then((data) => setAllDecks(data)).catch(() => {})
                  }}
                  className="flex items-center gap-1 px-2.5 py-1 text-xs font-medium rounded-lg border border-ink-line bg-[#1f2637] hover:bg-[#283248] text-slate-300 transition cursor-pointer"
                  title="Refresh"
                >
                  <span>↻</span>
                  <span className="hidden sm:inline">Refresh</span>
                </button>
              </>
            )}
            <button
              type="button"
              onClick={onClose}
              className="flex items-center justify-center w-7 h-7 rounded-lg text-slate-400 hover:text-white hover:bg-rose-500/20 hover:border-rose-500/30 border border-transparent transition cursor-pointer text-lg leading-none"
              title="Close (Esc)"
            >
              &times;
            </button>
          </div>
        </div>

        {/* ── Search & Filter Controls ── */}
        <div className="flex flex-wrap items-center justify-between gap-3 border-b border-ink-line/60 bg-[#141a26] px-4 py-2.5 text-xs">
          <div className="flex-1 min-w-[200px] max-w-md relative">
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search cards..."
              className="w-full rounded-lg border border-ink-line/80 bg-[#1b2233] px-3 py-1.5 text-xs text-slate-100 placeholder:text-slate-500 focus:outline-none focus:border-sky-500 focus:ring-1 focus:ring-sky-500 transition"
              autoFocus
            />
            {searchQuery && (
              <button
                type="button"
                onClick={() => setSearchQuery('')}
                className="absolute right-2.5 top-1.5 text-slate-400 hover:text-slate-200 cursor-pointer"
              >
                &times;
              </button>
            )}
          </div>

          <div className="flex flex-wrap items-center gap-2 text-xs">
            {/* Type filter */}
            <div className="inline-flex rounded-lg bg-[#1a2131] p-0.5 border border-ink-line/60">
              <button
                type="button"
                onClick={() => setFilterType('all')}
                className={`px-2 py-0.5 rounded text-[11px] font-medium transition cursor-pointer ${
                  filterType === 'all'
                    ? 'bg-sky-600/40 text-sky-100 border border-sky-500/50 shadow-sm font-semibold'
                    : 'text-slate-400 hover:text-slate-200'
                }`}
              >
                All ({cards.length})
              </button>
              <button
                type="button"
                onClick={() => setFilterType('code')}
                className={`px-2 py-0.5 rounded text-[11px] font-medium transition cursor-pointer ${
                  filterType === 'code'
                    ? 'bg-indigo-600/40 text-indigo-100 border border-indigo-500/50 shadow-sm font-semibold'
                    : 'text-slate-400 hover:text-slate-200'
                }`}
              >
                Code ({cards.filter(isCodeCard).length})
              </button>
              <button
                type="button"
                onClick={() => setFilterType('flashcard')}
                className={`px-2 py-0.5 rounded text-[11px] font-medium transition cursor-pointer ${
                  filterType === 'flashcard'
                    ? 'bg-emerald-600/40 text-emerald-100 border border-emerald-500/50 shadow-sm font-semibold'
                    : 'text-slate-400 hover:text-slate-200'
                }`}
              >
                Flashcards ({cards.filter((c) => !isCodeCard(c)).length})
              </button>
            </div>

            {/* Difficulty filter */}
            <div className="inline-flex rounded-lg bg-[#1a2131] p-0.5 border border-ink-line/60">
              <button
                type="button"
                onClick={() => setFilterDifficulty('all')}
                className={`px-2 py-0.5 rounded text-[11px] font-medium transition cursor-pointer ${
                  filterDifficulty === 'all'
                    ? 'bg-slate-700/60 text-slate-100 border border-slate-500/50 font-semibold'
                    : 'text-slate-400 hover:text-slate-200'
                }`}
              >
                All
              </button>
              <button
                type="button"
                onClick={() => setFilterDifficulty('easy')}
                className={`px-2 py-0.5 rounded text-[11px] font-medium transition cursor-pointer ${
                  filterDifficulty === 'easy'
                    ? 'bg-emerald-600/40 text-emerald-100 border border-emerald-500/50 font-semibold'
                    : 'text-emerald-400/80 hover:text-emerald-300'
                }`}
              >
                Easy
              </button>
              <button
                type="button"
                onClick={() => setFilterDifficulty('medium')}
                className={`px-2 py-0.5 rounded text-[11px] font-medium transition cursor-pointer ${
                  filterDifficulty === 'medium'
                    ? 'bg-amber-600/40 text-amber-100 border border-amber-500/50 font-semibold'
                    : 'text-amber-400/80 hover:text-amber-300'
                }`}
              >
                Med
              </button>
              <button
                type="button"
                onClick={() => setFilterDifficulty('hard')}
                className={`px-2 py-0.5 rounded text-[11px] font-medium transition cursor-pointer ${
                  filterDifficulty === 'hard'
                    ? 'bg-rose-600/40 text-rose-100 border border-rose-500/50 font-semibold'
                    : 'text-rose-400/80 hover:text-rose-300'
                }`}
              >
                Hard
              </button>
            </div>
          </div>
        </div>

        {/* ── Main 2-Column Split: List on Left, Preview on Right ── */}
        <div className="flex-1 grid grid-cols-1 md:grid-cols-12 min-h-0 divide-y md:divide-y-0 md:divide-x divide-ink-line/60">
          {/* ── Left Column: Cards List ── */}
          <div className="md:col-span-5 lg:col-span-4 flex flex-col h-full bg-[#10141d] min-h-0">
            <div className="p-2 border-b border-ink-line/50 text-[11px] font-medium text-slate-400 flex items-center justify-between bg-[#151a26]/70">
              <span>{filteredCards.length} of {cards.length} cards</span>
              {searchQuery && (
                <span className="text-sky-400 text-[10px]">Filtered</span>
              )}
            </div>

            <div className="flex-1 overflow-y-auto divide-y divide-ink-line/40 p-1.5 space-y-1">
              {error && (
                <div className="p-4 text-xs text-rose-300 bg-rose-950/30 border border-rose-500/30 rounded-lg">
                  Failed to load deck cards: {error}
                </div>
              )}

              {filteredCards.length === 0 && !loading && (
                <div className="p-8 text-center text-slate-500 text-xs">
                  No cards found matching your criteria.
                </div>
              )}

              {filteredCards.map((card, idx) => {
                const isSelected = card.id === selectedCard?.id
                const isCurrent = card.id === currentCardId
                const isCode = isCodeCard(card)
                const cardTitle = card.title || (card.front ? card.front.replace(/^#+\s*/, '').slice(0, 50) : `Card #${idx + 1}`)
                const cardComments = loadCardComments(card.id)

                return (
                  <button
                    key={card.id}
                    type="button"
                    onClick={() => setSelectedCardId(card.id)}
                    className={`group w-full text-left p-2.5 rounded-xl transition cursor-pointer flex flex-col gap-1.5 ${
                      isSelected
                        ? 'bg-sky-950/60 border border-sky-500/60 shadow-md ring-1 ring-sky-500/30'
                        : 'hover:bg-[#181f2e] border border-transparent text-slate-300'
                    }`}
                  >
                    <div className="flex items-center justify-between gap-1.5 min-w-0">
                      <div className="flex items-center gap-1.5 min-w-0 flex-1">
                        <span className="font-mono text-[10px] text-slate-500">#{idx + 1}</span>
                        <span className="font-semibold text-xs text-slate-100 truncate">
                          {cardTitle}
                        </span>
                        {cardComments.length > 0 && (
                          <span
                            className="shrink-0 flex items-center gap-0.5 px-1 py-0.2 rounded-full bg-sky-950/70 text-sky-300 border border-sky-500/40 text-[9px] font-mono"
                            title={`${cardComments.length} note(s)`}
                          >
                            <span>📝</span>
                            <span>{cardComments.length}</span>
                          </span>
                        )}
                      </div>

                      {/* Right side: High level short comment & Active badge */}
                      <div className="flex items-center gap-1 shrink-0">
                        {editingShortCommentCardId === card.id ? (
                          <div
                            className="flex items-center gap-1 z-10"
                            onClick={(e) => e.stopPropagation()}
                          >
                            <input
                              type="text"
                              autoFocus
                              value={editingShortCommentText}
                              onChange={(e) => setEditingShortCommentText(e.target.value)}
                              onKeyDown={(e) => {
                                if (e.key === 'Enter') {
                                  e.preventDefault()
                                  handleSaveShortComment(card.id, editingShortCommentText)
                                } else if (e.key === 'Escape') {
                                  e.preventDefault()
                                  setEditingShortCommentCardId(null)
                                }
                              }}
                              placeholder="Short comment..."
                              maxLength={45}
                              className="w-24 sm:w-32 text-[10px] px-1.5 py-0.5 rounded bg-[#0d131d] border border-amber-500/60 text-slate-100 placeholder-slate-500 focus:outline-none focus:ring-1 focus:ring-amber-500 font-sans"
                            />
                            <button
                              type="button"
                              onClick={(e) => {
                                e.stopPropagation()
                                handleSaveShortComment(card.id, editingShortCommentText)
                              }}
                              className="px-1 py-0.5 rounded bg-amber-600/80 hover:bg-amber-600 text-[9px] text-white font-medium cursor-pointer"
                              title="Save comment (Enter)"
                            >
                              ✓
                            </button>
                            {Boolean(shortComments[card.id]) && (
                              <button
                                type="button"
                                onClick={(e) => {
                                  e.stopPropagation()
                                  handleSaveShortComment(card.id, '')
                                }}
                                className="px-1 py-0.5 rounded bg-rose-950/60 hover:bg-rose-900 border border-rose-500/30 text-[9px] text-rose-300 cursor-pointer"
                                title="Clear comment"
                              >
                                ✕
                              </button>
                            )}
                          </div>
                        ) : shortComments[card.id] ? (
                          <span
                            onClick={(e) => {
                              e.stopPropagation()
                              setEditingShortCommentCardId(card.id)
                              setEditingShortCommentText(shortComments[card.id] || '')
                            }}
                            className="px-1.5 py-0.5 rounded bg-amber-500/15 hover:bg-amber-500/25 text-amber-200 border border-amber-500/40 text-[10px] font-medium max-w-[130px] truncate cursor-pointer transition flex items-center gap-1 shadow-sm"
                            title={`Click to edit comment: "${shortComments[card.id]}"`}
                          >
                            <span className="text-[9px]">💬</span>
                            <span className="truncate">{shortComments[card.id]}</span>
                          </span>
                        ) : (
                          <button
                            type="button"
                            onClick={(e) => {
                              e.stopPropagation()
                              setEditingShortCommentCardId(card.id)
                              setEditingShortCommentText('')
                            }}
                            className="opacity-0 group-hover:opacity-100 text-slate-400 hover:text-amber-300 text-[10px] px-1.5 py-0.5 rounded hover:bg-[#1f293d] border border-ink-line/60 transition cursor-pointer flex items-center gap-0.5"
                            title="Add short comment to card"
                          >
                            <span>+💬</span>
                          </button>
                        )}

                        {isCurrent && (
                          <span className="shrink-0 px-1.5 py-0.5 rounded bg-sky-500/20 text-sky-300 font-bold border border-sky-500/40 text-[9px]">
                            Active
                          </span>
                        )}
                      </div>
                    </div>

                    <div className="flex items-center justify-between gap-1.5 text-[10px]">
                      <div className="flex flex-wrap items-center gap-1.5 min-w-0">
                        {isCode ? (
                          <span className="px-1.5 py-0.2 rounded bg-indigo-500/15 text-indigo-300 border border-indigo-500/30 font-medium">
                            Code
                          </span>
                        ) : (
                          <span className="px-1.5 py-0.2 rounded bg-slate-700/30 text-slate-300 border border-slate-600/30 font-medium">
                            Flashcard
                          </span>
                        )}

                        {card.difficulty && (
                          <span
                            className={`px-1.5 py-0.2 rounded border font-medium ${
                              card.difficulty.toLowerCase() === 'easy'
                                ? 'bg-emerald-500/15 text-emerald-300 border-emerald-500/30'
                                : card.difficulty.toLowerCase() === 'hard'
                                ? 'bg-rose-500/15 text-rose-300 border-rose-500/30'
                                : 'bg-amber-500/15 text-amber-300 border-amber-500/30'
                            }`}
                          >
                            {card.difficulty}
                          </span>
                        )}

                        {card.time_complexity && (
                          <span className="px-1.5 py-0.2 rounded bg-sky-500/10 text-sky-300 border border-sky-500/30 font-mono text-[9px]">
                            {card.time_complexity}
                          </span>
                        )}

                        {card.state && (
                          <span className="text-slate-500 capitalize text-[10px]">
                            • {card.state}
                          </span>
                        )}

                        {card.is_schema_checkpoint && (
                          <span
                            className="px-1.5 py-0.2 rounded bg-amber-500/20 text-amber-200 border border-amber-500/40 font-medium text-[9px]"
                            title="Schema Checkpoint (mPFC Anchor)"
                          >
                            🏛️ Checkpoint
                          </span>
                        )}

                        {card.spatial_locus && (
                          <span
                            className="px-1.5 py-0.2 rounded bg-purple-500/20 text-purple-200 border border-purple-500/40 font-mono text-[9px] truncate max-w-[110px]"
                            title={`Memory Palace Locus: ${card.spatial_locus}`}
                          >
                            📍 {card.spatial_locus}
                          </span>
                        )}
                      </div>

                      <CompactCardProgressionBar card={card} className="shrink-0 ml-auto" />
                    </div>
                  </button>
                )
              })}
            </div>
          </div>

          {/* ── Right Column: Selected Card Detail Preview ── */}
          <div className="md:col-span-7 lg:col-span-8 flex flex-col h-full bg-[#121620] min-h-0 overflow-y-auto">
            {selectedCard ? (
              <div className="p-4 sm:p-6 space-y-5">
                {/* ── Preview Header & Action Bar ── */}
                <div className="flex flex-wrap items-start justify-between gap-3 pb-3 border-b border-ink-line/60">
                  <div className="space-y-1 max-w-xl">
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="rounded bg-sky-950/80 border border-sky-500/40 px-2 py-0.5 text-xs font-mono text-sky-200">
                        {isCodeCard(selectedCard) ? 'Code' : 'Flashcard'}
                      </span>
                      {selectedCard.category && (
                        <span className="rounded bg-slate-800 border border-slate-700 px-2 py-0.5 text-xs text-slate-300">
                          {selectedCard.category}
                        </span>
                      )}
                      {selectedCard.difficulty && (
                        <span
                          className={`rounded px-2 py-0.5 text-xs font-medium border ${
                            selectedCard.difficulty.toLowerCase() === 'easy'
                              ? 'bg-emerald-500/10 text-emerald-300 border-emerald-500/30'
                              : selectedCard.difficulty.toLowerCase() === 'hard'
                              ? 'bg-rose-500/10 text-rose-300 border-rose-500/30'
                              : 'bg-amber-500/10 text-amber-300 border-amber-500/30'
                          }`}
                        >
                          {selectedCard.difficulty}
                        </span>
                      )}
                      {selectedCard.time_complexity && (
                        <span className="rounded bg-sky-500/10 px-2 py-0.5 text-xs font-mono text-sky-300 border border-sky-500/30">
                          {selectedCard.time_complexity}
                        </span>
                      )}
                      {selectedCard.space_complexity && (
                        <span className="rounded bg-purple-500/10 px-2 py-0.5 text-xs font-mono text-purple-300 border border-purple-500/30">
                          {selectedCard.space_complexity}
                        </span>
                      )}
                      <CompactCardProgressionBar card={selectedCard} />
                    </div>
                    <div className="flex flex-wrap items-center gap-2.5 relative">
                      <h2 className="text-base sm:text-lg font-bold text-white">
                        {selectedCard.title || 'Card Preview'}
                      </h2>

                      {shortComments[selectedCard.id] && (
                        <span
                          onClick={() => {
                            setEditingShortCommentCardId(selectedCard.id)
                            setEditingShortCommentText(shortComments[selectedCard.id] || '')
                          }}
                          className="px-2 py-0.5 rounded-full bg-amber-500/15 hover:bg-amber-500/25 text-amber-200 border border-amber-500/40 text-xs font-medium cursor-pointer transition flex items-center gap-1 shadow-sm"
                          title="Click to edit short comment"
                        >
                          <span className="text-[10px]">💬</span>
                          <span>{shortComments[selectedCard.id]}</span>
                        </span>
                      )}

                      {/* Comments Trigger Button Immediately to the Right of Card Title */}
                      <div className="relative inline-flex items-center">
                        <button
                          type="button"
                          onClick={() => setShowCommentsPopover(!showCommentsPopover)}
                          className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-medium transition cursor-pointer ${
                            currentCardComments.length > 0
                              ? 'bg-sky-950/80 text-sky-200 border border-sky-400/50 hover:bg-sky-900 shadow-sm'
                              : 'bg-[#1e2738]/90 text-slate-400 hover:text-slate-200 border border-ink-line/80 hover:bg-[#253248]'
                          }`}
                          title={currentCardComments.length > 0 ? `${currentCardComments.length} comment(s) - Click to view or add` : 'Add comment to this card'}
                        >
                          <span className="text-[12px]">💬</span>
                          <span className="text-[11px]">
                            {currentCardComments.length > 0
                              ? `${currentCardComments.length} ${currentCardComments.length === 1 ? 'comment' : 'comments'}`
                              : '+ Comment'}
                          </span>
                        </button>

                        {/* Comments Dropdown Popover */}
                        {showCommentsPopover && (
                          <div className="absolute left-0 top-full mt-2 w-80 sm:w-96 rounded-xl bg-[#141b27] border border-sky-500/40 shadow-2xl p-3 z-50 animate-in fade-in zoom-in-95 duration-150 backdrop-blur-md">
                            <div className="flex items-center justify-between pb-2 mb-2 border-b border-ink-line/80">
                              <div className="flex items-center gap-1.5 text-xs font-bold text-sky-300">
                                <span>💬</span>
                                <span>Card Comments</span>
                                <span className="rounded-full bg-sky-500/20 px-1.5 py-0.2 text-[10px] text-sky-300 font-mono">
                                  {currentCardComments.length}
                                </span>
                              </div>
                              <button
                                type="button"
                                onClick={() => setShowCommentsPopover(false)}
                                className="text-slate-400 hover:text-slate-200 text-xs px-1 rounded hover:bg-white/10 cursor-pointer"
                              >
                                ✕
                              </button>
                            </div>

                            {/* Add Comment Input Form */}
                            <form onSubmit={handleAddComment} className="space-y-2 mb-3">
                              <textarea
                                value={newCommentText}
                                onChange={(e) => setNewCommentText(e.target.value)}
                                placeholder="Write a comment or note for this card..."
                                rows={2}
                                className="w-full text-xs rounded-lg bg-[#0d131d] border border-ink-line/80 text-slate-100 placeholder-slate-500 p-2 focus:outline-none focus:border-sky-500 focus:ring-1 focus:ring-sky-500 resize-none font-sans"
                                onKeyDown={(e) => {
                                  if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) {
                                    e.preventDefault()
                                    handleAddComment()
                                  }
                                }}
                              />
                              <div className="flex items-center justify-between">
                                <span className="text-[10px] text-slate-500">Ctrl+Enter to post</span>
                                <button
                                  type="submit"
                                  disabled={!newCommentText.trim()}
                                  className="px-3 py-1 rounded-md bg-sky-600 hover:bg-sky-500 disabled:opacity-40 text-white text-xs font-medium transition cursor-pointer shadow-sm"
                                >
                                  Add Comment
                                </button>
                              </div>
                            </form>

                            {/* Comments List */}
                            <div className="space-y-2 max-h-56 overflow-y-auto pr-1">
                              {currentCardComments.length === 0 ? (
                                <p className="text-center text-xs text-slate-500 py-3 italic">
                                  No comments yet. Leave a note or mnemonic for this card!
                                </p>
                              ) : (
                                currentCardComments.map((comment) => (
                                  <div
                                    key={comment.id}
                                    className="group p-2 rounded-lg bg-[#0d131d]/90 border border-ink-line/60 flex flex-col gap-1 text-xs"
                                  >
                                    <div className="flex items-center justify-between text-[10px] text-slate-400">
                                      <span>{new Date(comment.createdAt).toLocaleDateString(undefined, { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })}</span>
                                      <button
                                        type="button"
                                        onClick={() => handleDeleteComment(comment.id)}
                                        className="opacity-0 group-hover:opacity-100 text-rose-400 hover:text-rose-300 transition text-[11px] cursor-pointer"
                                        title="Delete comment"
                                      >
                                        🗑️
                                      </button>
                                    </div>
                                    <div className="text-slate-200 whitespace-pre-wrap text-[11px] leading-relaxed break-words">
                                      {comment.text}
                                    </div>
                                  </div>
                                ))
                              )}
                            </div>
                          </div>
                        )}
                      </div>
                    </div>
                  </div>

                  {/* Action Buttons */}
                  <div className="flex flex-wrap items-center gap-2">
                    <button
                      type="button"
                      onClick={() => setAnalyticsCardId(selectedCard.id)}
                      className="flex items-center gap-1.5 px-3.5 py-1.5 rounded-lg border border-sky-500/40 bg-sky-500/15 hover:bg-sky-500/25 text-sky-200 text-xs font-semibold transition cursor-pointer"
                      title="View card analytics, memory retention dynamics, and weak points"
                    >
                      <span>📊</span>
                      <span>Analytics</span>
                    </button>

                    {onSelectCard && (
                      <button
                        type="button"
                        onClick={() => onSelectCard(selectedCard)}
                        className="flex items-center gap-1.5 px-3.5 py-1.5 rounded-lg bg-sky-600 hover:bg-sky-500 text-white text-xs font-semibold shadow-md transition cursor-pointer"
                        title="Study now"
                      >
                        <span>Study Now</span>
                      </button>
                    )}

                    {selectedCard.back && (
                      <button
                        type="button"
                        onClick={() => void handleCopyCode(extractCleanCode(selectedCard.back))}
                        className="flex items-center gap-1.5 px-3.5 py-1.5 rounded-lg border border-ink-line bg-[#1c2333] hover:bg-[#252f44] text-slate-200 text-xs font-medium transition cursor-pointer"
                        title="Copy"
                      >
                        <span>{copiedCode ? 'Copied' : 'Copy'}</span>
                      </button>
                    )}
                  </div>
                </div>

                {/* ── Prompt / Front Statement ── */}
                <div className="rounded-xl border border-ink-line/80 bg-[#161c28] p-4 space-y-2">
                  <div className="flex items-center justify-between text-xs font-semibold text-slate-400">
                    <span className="flex items-center gap-1.5">
                      <span>Question</span>
                    </span>
                  </div>
                  <div className="text-xs sm:text-sm text-slate-200 leading-relaxed">
                    <RichText text={selectedCard.front || 'No prompt specified'} />
                  </div>

                  {selectedCard.edge_cases && selectedCard.edge_cases.length > 0 && (
                    <div className="pt-2 border-t border-ink-line/50 text-xs flex flex-wrap items-center gap-2">
                      <span className="text-amber-400 font-medium">Edge Cases:</span>
                      {selectedCard.edge_cases.map((ec, i) => (
                        <span
                          key={i}
                          className="px-2 py-0.5 rounded bg-amber-500/10 text-amber-200 border border-amber-500/30 text-[11px]"
                        >
                          {ec}
                        </span>
                      ))}
                    </div>
                  )}
                </div>

                {/* ── Neuroscience & Spatial Scaffolding Panel ── */}
                <div className="rounded-xl border border-purple-500/30 bg-[#141224] p-4 space-y-3.5 shadow-md">
                  <div className="flex flex-wrap items-center justify-between gap-2 border-b border-purple-500/20 pb-2.5">
                    <div className="flex items-center gap-2">
                      <span className="text-base">🧠</span>
                      <div>
                        <h3 className="text-xs font-bold text-purple-200">
                          Neuroscience &amp; Memory Palace Scaffolding
                        </h3>
                        <p className="text-[10px] text-slate-400">
                          Hippocampal cognitive mapping, mPFC schema assimilation &amp; dual coding
                        </p>
                      </div>
                    </div>

                    {/* Schema Checkpoint Toggle */}
                    <button
                      type="button"
                      onClick={handleToggleSchemaCheckpoint}
                      disabled={savingNeuroProps}
                      className={`flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-xs font-medium border transition cursor-pointer disabled:opacity-50 ${
                        selectedCard.is_schema_checkpoint
                          ? 'bg-amber-500/25 text-amber-200 border-amber-500/60 shadow-sm'
                          : 'bg-[#1b1c2e] text-slate-400 border-ink-line/60 hover:text-slate-200 hover:border-slate-500'
                      }`}
                      title="Schema Checkpoints represent foundational structural concepts scheduled before leaf nodes"
                    >
                      <span>🏛️</span>
                      <span>{selectedCard.is_schema_checkpoint ? 'Schema Checkpoint (Active)' : 'Mark as Schema Checkpoint'}</span>
                    </button>
                  </div>

                  {/* Memory Palace Locus Input */}
                  <div className="grid grid-cols-1 sm:grid-cols-4 gap-2.5 items-end">
                    <div className="sm:col-span-3 space-y-1">
                      <label className="text-[11px] font-semibold text-slate-300 flex items-center gap-1">
                        <span>📍 Memory Palace Locus (Place Cell Anchor)</span>
                      </label>
                      <input
                        type="text"
                        value={editingLocus}
                        onChange={(e) => setEditingLocus(e.target.value)}
                        placeholder="e.g. Grand Vestibule - Stanza 1"
                        className="w-full text-xs rounded-lg bg-[#0c0d18] border border-purple-500/30 px-2.5 py-1.5 text-purple-100 placeholder-slate-600 focus:outline-none focus:border-purple-400"
                      />
                    </div>
                    <div className="flex items-center">
                      <button
                        type="button"
                        disabled={savingNeuroProps || editingLocus === (selectedCard.spatial_locus || '')}
                        onClick={handleSaveLocus}
                        className="w-full px-3 py-1.5 rounded-lg bg-purple-600/80 hover:bg-purple-600 disabled:opacity-40 text-white text-xs font-medium transition cursor-pointer shadow-sm"
                      >
                        {savingNeuroProps ? 'Saving…' : 'Save Locus'}
                      </button>
                    </div>
                  </div>

                  {/* Mnemonic Vignette (Dual Coding & Von Restorff Bizarreness) */}
                  <div className="space-y-1.5 pt-2 border-t border-purple-500/20">
                    <div className="flex items-center justify-between">
                      <label className="text-[11px] font-semibold text-slate-300 flex items-center gap-1">
                        <span>🎨 Bizarre Mnemonic Vignette (Dual Coding)</span>
                      </label>
                      <button
                        type="button"
                        disabled={generatingMnemonic}
                        onClick={handleGenerateMnemonic}
                        className="text-[11px] text-amber-300 hover:text-amber-200 flex items-center gap-1 transition cursor-pointer disabled:opacity-40"
                        title="Synthesize high-vividness multi-sensory mental vignette"
                      >
                        <span>✨</span>
                        <span>{generatingMnemonic ? 'Synthesizing…' : 'Synthesize Vignette'}</span>
                      </button>
                    </div>
                    <textarea
                      rows={2}
                      value={editingMnemonic}
                      onChange={(e) => setEditingMnemonic(e.target.value)}
                      placeholder="Multi-sensory mental imagery anchor combining exaggerated kinetic action, sound, and spatial locus..."
                      className="w-full text-xs rounded-lg bg-[#0c0d18] border border-purple-500/30 p-2 text-amber-100 placeholder-slate-600 focus:outline-none focus:border-purple-400 resize-none font-sans"
                    />
                    {editingMnemonic !== (selectedCard.mnemonic_vignette || '') && (
                      <div className="flex justify-end">
                        <button
                          type="button"
                          disabled={savingNeuroProps}
                          onClick={handleSaveMnemonic}
                          className="px-3 py-1 rounded bg-amber-600/80 hover:bg-amber-600 text-white text-[11px] font-medium transition cursor-pointer disabled:opacity-40"
                        >
                          {savingNeuroProps ? 'Saving…' : 'Save Vignette'}
                        </button>
                      </div>
                    )}
                  </div>
                </div>

                {/* ── Reference Solution ── */}
                <div className="rounded-xl border border-ink-line/80 bg-[#161c28] overflow-hidden space-y-0">
                  <div className="flex items-center justify-between px-4 py-2 border-b border-ink-line/70 bg-[#19202e] text-xs font-semibold text-slate-300">
                    <span className="flex items-center gap-1.5">
                      <span>Reference</span>
                    </span>
                    {selectedCard.time_complexity && (
                      <span className="font-mono text-[10px] text-sky-300">
                        Target: {selectedCard.time_complexity}
                      </span>
                    )}
                  </div>

                  {isCodeCard(selectedCard) ? (
                    <CodeEditor
                      code={extractCleanCode(selectedCard.back)}
                      onChange={() => {}}
                      language={detectCodeLanguage(selectedCard.back, codeLanguage)}
                      readOnly={true}
                      height="auto"
                      hideHeader={true}
                      borderless={true}
                      placeholder="// Reference solution"
                      context={selectedCard.title || selectedCard.front}
                      deckId={deckId}
                    />
                  ) : (
                    <div className="p-4 text-xs sm:text-sm text-slate-200 leading-relaxed">
                      <RichText text={selectedCard.back || 'No answer specified'} />
                    </div>
                  )}
                </div>

                {/* ── Starter Tests & Test Cases (Collapsible) ── */}
                {isCodeCard(selectedCard) && (
                  <div className="rounded-xl border border-ink-line/80 bg-[#161c28] overflow-hidden">
                    <button
                      type="button"
                      onClick={() => setShowTestsSection((prev) => !prev)}
                      className="w-full flex items-center justify-between px-4 py-2.5 bg-[#19202e] text-xs font-semibold text-slate-300 hover:bg-[#20293a] transition cursor-pointer"
                    >
                      <span className="flex items-center gap-1.5">
                        <span>Unit Tests</span>
                        {selectedCard.test_cases && selectedCard.test_cases.length > 0 && (
                          <span className="rounded-full bg-indigo-950/80 px-2 py-0.2 text-[10px] font-mono text-indigo-300 border border-indigo-500/30">
                            {selectedCard.test_cases.length} cases
                          </span>
                        )}
                      </span>
                      <span className="text-slate-400 text-xs">
                        {showTestsSection ? 'Hide' : 'Show'}
                      </span>
                    </button>

                    {showTestsSection && (
                      <div className="p-4 space-y-4 animate-in fade-in duration-150">
                        {/* Test Cases Table */}
                        {selectedCard.test_cases && selectedCard.test_cases.length > 0 && (
                          <div className="space-y-1.5">
                            <h4 className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider">
                              Test Cases
                            </h4>
                            <div className="overflow-x-auto rounded-lg border border-ink-line/60">
                              <table className="w-full text-left text-xs">
                                <thead className="bg-[#1f2637] text-slate-400 font-mono text-[11px] border-b border-ink-line/60">
                                  <tr>
                                    <th className="px-3 py-1.5">#</th>
                                    <th className="px-3 py-1.5">Input</th>
                                    <th className="px-3 py-1.5">Expected</th>
                                  </tr>
                                </thead>
                                <tbody className="divide-y divide-ink-line/40 font-mono text-[11px] bg-[#141924]">
                                  {selectedCard.test_cases.map((tc, idx) => (
                                    <tr key={idx} className="hover:bg-[#1a2130]">
                                      <td className="px-3 py-1.5 text-slate-500 font-bold">{idx + 1}</td>
                                      <td className="px-3 py-1.5 text-sky-200">
                                        {typeof tc.input === 'object'
                                          ? JSON.stringify(tc.input)
                                          : String(tc.input)}
                                      </td>
                                      <td className="px-3 py-1.5 text-emerald-300 font-semibold">
                                        {JSON.stringify(tc.expected)}
                                      </td>
                                    </tr>
                                  ))}
                                </tbody>
                              </table>
                            </div>
                          </div>
                        )}

                        {/* Starter Code */}
                        {selectedCard.starter_code && (
                          <div className="space-y-1.5">
                            <h4 className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider">
                              Starter Code
                            </h4>
                            <CodeEditor
                              code={selectedCard.starter_code}
                              onChange={() => {}}
                              language={codeLanguage}
                              readOnly={true}
                              height="140px"
                              hideHeader={true}
                              borderless={true}
                              context={selectedCard.title || selectedCard.front}
                              deckId={deckId}
                            />
                          </div>
                        )}

                        {/* Starter Tests */}
                        {selectedCard.starter_tests && (
                          <div className="space-y-1.5">
                            <h4 className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider">
                              Starter Tests
                            </h4>
                            <CodeEditor
                              code={selectedCard.starter_tests}
                              onChange={() => {}}
                              language={codeLanguage}
                              readOnly={true}
                              height="160px"
                              hideHeader={true}
                              borderless={true}
                              context={selectedCard.title || selectedCard.front}
                              deckId={deckId}
                            />
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                )}
              </div>
            ) : (
              <div className="flex flex-col items-center justify-center h-full p-8 text-center text-slate-500 space-y-2">
                <p className="text-sm">Select a card to preview.</p>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Deck Documentation Modal */}
      {showDocsModal && (
        <div className="fixed inset-0 z-60 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm animate-in fade-in duration-150">
          <div className="relative flex flex-col w-full max-w-2xl max-h-[85vh] rounded-2xl border border-emerald-500/40 bg-[#0f1728] text-slate-100 shadow-2xl overflow-hidden">
            {/* Header */}
            <div className="flex items-center justify-between border-b border-ink-line/80 bg-[#142034] px-5 py-3.5">
              <div className="flex items-center gap-2">
                <span className="text-xl">📄</span>
                <div>
                  <h3 className="text-sm font-bold text-emerald-200">
                    Deck Documentation · {deckName || 'Current Deck'}
                  </h3>
                  <p className="text-[11px] text-slate-400">
                    Attached documents are searched and cited by local LLMs when explaining highlighted code.
                  </p>
                </div>
              </div>
              <button
                type="button"
                onClick={() => {
                  setShowDocsModal(false)
                  setDocUploadError(null)
                  setSelectedFile(null)
                  setDocTitle('')
                }}
                className="flex items-center justify-center w-7 h-7 rounded-lg text-slate-400 hover:text-white hover:bg-white/10 transition cursor-pointer text-lg leading-none"
              >
                &times;
              </button>
            </div>

            {/* Body */}
            <div className="flex-1 overflow-y-auto p-5 space-y-5 text-xs">
              {/* Upload New Document Form */}
              <form onSubmit={handleUploadDocument} className="p-4 rounded-xl border border-emerald-500/30 bg-[#11242c]/40 space-y-3">
                <h4 className="text-xs font-semibold text-emerald-300 flex items-center gap-1.5">
                  <span>＋</span>
                  <span>Upload Reference Documentation</span>
                </h4>
                <p className="text-[11px] text-slate-400">
                  Supported formats: PDF, Markdown (.md), Plain Text (.txt), HTML, TypeScript (.ts, .tsx), JavaScript (.js), Python (.py), Java (.java), JSON.
                </p>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  <div>
                    <label className="block text-[11px] font-medium text-slate-300 mb-1">
                      Select File *
                    </label>
                    <input
                      type="file"
                      accept=".pdf,.txt,.md,.markdown,.html,.htm,.rst,.ts,.tsx,.js,.jsx,.py,.java,.json"
                      onChange={(e) => setSelectedFile(e.target.files?.[0] || null)}
                      required
                      className="w-full text-[11px] text-slate-300 file:mr-2.5 file:py-1 file:px-3 file:rounded-lg file:border file:border-emerald-500/40 file:text-[11px] file:font-semibold file:bg-emerald-950/60 file:text-emerald-200 hover:file:bg-emerald-900/80 cursor-pointer"
                    />
                  </div>
                  <div>
                    <label className="block text-[11px] font-medium text-slate-300 mb-1">
                      Document Title (optional)
                    </label>
                    <input
                      type="text"
                      value={docTitle}
                      onChange={(e) => setDocTitle(e.target.value)}
                      placeholder={selectedFile?.name || "e.g. Course Specification"}
                      className="w-full rounded-lg border border-ink-line/80 bg-[#1b2233] px-3 py-1.5 text-xs text-slate-100 placeholder:text-slate-500 focus:outline-none focus:border-emerald-500"
                    />
                  </div>
                </div>

                {docUploadError && (
                  <div className="p-2 rounded bg-rose-950/40 border border-rose-500/30 text-rose-300 text-[11px]">
                    {docUploadError}
                  </div>
                )}

                <div className="flex justify-end pt-1">
                  <button
                    type="submit"
                    disabled={!selectedFile || uploadingDoc}
                    className="flex items-center gap-1.5 px-3.5 py-1.5 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white font-medium text-xs shadow-md transition disabled:opacity-50 cursor-pointer"
                  >
                    {uploadingDoc ? (
                      <>
                        <span className="inline-block w-3 h-3 rounded-full border-2 border-white border-t-transparent animate-spin" />
                        <span>Extracting &amp; Segmenting…</span>
                      </>
                    ) : (
                      <>
                        <span>Upload &amp; Attach to Deck</span>
                      </>
                    )}
                  </button>
                </div>
              </form>

              {/* List of Attached Documents */}
              <div className="space-y-2.5">
                <h4 className="text-xs font-semibold text-slate-300 flex items-center justify-between">
                  <span>Attached Documents ({deckDocs.length})</span>
                  <span className="text-[11px] text-slate-400 font-normal">
                    {deckDocs.reduce((acc, d) => acc + (d.segment_count || 0), 0)} total citable segments
                  </span>
                </h4>

                {deckDocs.length === 0 ? (
                  <div className="p-6 rounded-xl border border-dashed border-ink-line/60 bg-[#131b2c]/30 text-center text-slate-400 space-y-1">
                    <p className="font-medium text-slate-300">No documents attached yet</p>
                    <p className="text-[11px]">
                      Upload course notes, specification PDFs, or source code above. You can then highlight any code block and press Alt+D to search these documents.
                    </p>
                  </div>
                ) : (
                  <div className="space-y-2">
                    {deckDocs.map((doc) => (
                      <div
                        key={doc.id}
                        className="p-3 rounded-xl border border-ink-line/80 bg-[#162136] flex items-start justify-between gap-3 hover:border-emerald-500/40 transition"
                      >
                        <div className="min-w-0 flex-1 space-y-1">
                          <div className="flex items-center gap-2">
                            <span className="text-emerald-400 font-bold">📄</span>
                            <span className="font-semibold text-slate-100 truncate text-xs">
                              {doc.title}
                            </span>
                            <span className="text-[10px] text-slate-400 font-mono truncate">
                              ({doc.filename})
                            </span>
                          </div>
                          <div className="flex items-center gap-2 text-[10px] text-slate-400">
                            <span className="text-emerald-300/90 font-medium">
                              {doc.segment_count} citable segment{doc.segment_count === 1 ? '' : 's'}
                            </span>
                            {doc.uploaded_at && (
                              <span>• Added {new Date(doc.uploaded_at).toLocaleDateString()}</span>
                            )}
                          </div>
                          {doc.locators && doc.locators.length > 0 && (
                            <div className="flex flex-wrap gap-1 pt-1">
                              {doc.locators.slice(0, 8).map((loc, lIdx) => (
                                <span
                                  key={lIdx}
                                  className="px-1.5 py-0.2 rounded bg-black/40 text-slate-300 font-mono text-[9px] border border-white/5"
                                >
                                  {loc}
                                </span>
                              ))}
                              {doc.locators.length > 8 && (
                                <span className="text-[9px] text-slate-500">
                                  +{doc.locators.length - 8} more
                                </span>
                              )}
                            </div>
                          )}
                        </div>
                        <button
                          type="button"
                          onClick={() => void handleDeleteDocument(doc.id)}
                          disabled={deletingDocId === doc.id}
                          className="px-2 py-1 rounded text-[11px] text-rose-400 hover:text-rose-200 hover:bg-rose-950/40 border border-transparent hover:border-rose-500/30 transition cursor-pointer"
                          title="Remove document from deck"
                        >
                          {deletingDocId === doc.id ? 'Removing…' : 'Remove'}
                        </button>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>

            {/* Footer */}
            <div className="flex items-center justify-between border-t border-ink-line/80 bg-[#142034] px-5 py-3 text-xs">
              <span className="text-slate-400">
                Tip: In the code editor, select any code and press <kbd className="px-1 py-0.5 rounded bg-black/50 text-emerald-300 border border-emerald-500/30 font-mono">Alt+D</kbd> to search docs or <kbd className="px-1 py-0.5 rounded bg-black/50 text-sky-300 border border-sky-500/30 font-mono">Alt+Q</kbd> to ask the local LLM.
              </span>
              <button
                type="button"
                onClick={() => setShowDocsModal(false)}
                className="px-3.5 py-1 rounded-lg border border-ink-line bg-[#1f2a40] hover:bg-[#283652] text-slate-200 font-medium cursor-pointer transition"
              >
                Done
              </button>
            </div>
          </div>
        </div>
      )}

      <CardAnalyticsModal
        cardId={analyticsCardId}
        isOpen={Boolean(analyticsCardId)}
        onClose={() => setAnalyticsCardId(null)}
        onCardUpdated={() => {
          if (deckId) void loadCards(deckId)
        }}
      />
    </div>
  )
}
export default DeckCardsViewer
