import React, { useMemo, useState } from 'react'
import {
  CONCORDANCE_CATEGORIES,
  CONCORDANCE_MASTER_REGEX,
  ConcordanceCategory,
  ConcordanceEntry,
  GUTTAG_CONCORDANCE_LEXICON,
  getConcordanceEntryById,
  resolveConcordanceEntry,
  searchConcordance,
} from '../services/concordance_engine'

export const CONCORDANCE_ENABLED_STORAGE_KEY = 'fundamentals_concordance_enabled'

export const getStoredConcordanceEnabled = (): boolean => {
  try {
    const raw = localStorage.getItem(CONCORDANCE_ENABLED_STORAGE_KEY)
    if (raw !== null) {
      return raw === 'true'
    }
  } catch {
    /* storage unavailable */
  }
  return true
}

export interface ConcordanceReaderProps {
  content: string
  enabled?: boolean
  onToggleEnabled?: (enabled: boolean) => void
}

export function ConcordanceReader({
  content,
  enabled: controlledEnabled,
  onToggleEnabled,
}: ConcordanceReaderProps) {
  const [internalEnabled, setInternalEnabled] = useState<boolean>(getStoredConcordanceEnabled)
  const isEnabled = controlledEnabled !== undefined ? controlledEnabled : internalEnabled

  const handleToggle = (next: boolean) => {
    if (onToggleEnabled) {
      onToggleEnabled(next)
    } else {
      setInternalEnabled(next)
      try {
        localStorage.setItem(CONCORDANCE_ENABLED_STORAGE_KEY, String(next))
      } catch {}
    }
  }
  const [hoveredEntry, setHoveredEntry] = useState<{
    entry: ConcordanceEntry
    x: number
    y: number
  } | null>(null)
  const [pinnedEntry, setPinnedEntry] = useState<ConcordanceEntry | null>(null)
  const [showLexiconModal, setShowLexiconModal] = useState(false)
  const [lexiconSearch, setLexiconSearch] = useState('')
  const [selectedCategory, setSelectedCategory] = useState<ConcordanceCategory | 'All'>('All')
  const [copiedId, setCopiedId] = useState<string | null>(null)

  // Single compiled regex over every indexed surface form, longest alternative first.
  const masterRegex = CONCORDANCE_MASTER_REGEX

  const handleMouseEnter = (
    e: React.MouseEvent<HTMLSpanElement>,
    entry: ConcordanceEntry
  ) => {
    const rect = e.currentTarget.getBoundingClientRect()
    setHoveredEntry({
      entry,
      x: rect.left,
      y: rect.bottom + 6,
    })
  }

  const handleMouseLeave = () => {
    setHoveredEntry(null)
  }

  const copyDefinition = (entry: ConcordanceEntry) => {
    const textToCopy = `[${entry.id}] ${entry.term} (${entry.primaryLocation}): ${entry.definition}`
    void navigator.clipboard.writeText(textToCopy)
    setCopiedId(entry.id)
    setTimeout(() => setCopiedId(null), 2500)
  }

  /**
   * Tokenizes text and attaches Strong's concordance tags to matching terms.
   */
  const tokenizeText = (text: string): React.ReactNode[] => {
    if (!isEnabled || !text) return [text]

    const parts: React.ReactNode[] = []
    let lastIndex = 0
    let match: RegExpExecArray | null

    const localRegex = new RegExp(masterRegex.source, 'gi')
    while ((match = localRegex.exec(text)) !== null) {
      const matchText = match[0]
      const startIndex = match.index

      if (startIndex > lastIndex) {
        parts.push(text.substring(lastIndex, startIndex))
      }

      // Resolve the span to the single most specific entry (anchored, cached).
      const entry = resolveConcordanceEntry(matchText)

      if (entry) {
        parts.push(
          <span
            key={`${startIndex}-${matchText}`}
            onMouseEnter={(e) => handleMouseEnter(e, entry)}
            onMouseLeave={handleMouseLeave}
            onClick={() => setPinnedEntry(entry)}
            className="inline-flex items-center gap-0.5 rounded px-1 py-0.2 text-sky-200 font-semibold border-b border-dashed border-sky-400/80 bg-sky-500/10 hover:bg-sky-500/25 hover:text-white cursor-pointer transition select-none"
            title={`Strong's Concordance: ${entry.id} - ${entry.term}`}
          >
            <span>{matchText}</span>
            <span className="text-[8px] font-mono text-sky-400 opacity-80">
              [{entry.id}]
            </span>
          </span>
        )
      } else {
        parts.push(matchText)
      }

      lastIndex = localRegex.lastIndex
    }

    if (lastIndex < text.length) {
      parts.push(text.substring(lastIndex))
    }

    return parts
  }

  /**
   * Parses inline markdown elements (bold **...**, code `...`, italic *...*)
   * and tokenizes the text within each formatting node.
   */
  const parseInlineMarkdown = (rawText: string): React.ReactNode[] => {
    // Match **bold**, `code`, or plain text chunks
    const inlineRegex = /(\*\*([^*]+)\*\*|`([^`]+)`|\*([^*]+)\*)/g
    const elements: React.ReactNode[] = []
    let lastPos = 0
    let m: RegExpExecArray | null

    while ((m = inlineRegex.exec(rawText)) !== null) {
      const start = m.index
      if (start > lastPos) {
        const plain = rawText.substring(lastPos, start)
        elements.push(...tokenizeText(plain))
      }

      if (m[2] !== undefined) {
        // Bold: **text**
        elements.push(
          <strong key={`bold-${start}`} className="font-bold text-slate-100">
            {tokenizeText(m[2])}
          </strong>
        )
      } else if (m[3] !== undefined) {
        // Code: `code`
        elements.push(
          <code
            key={`code-${start}`}
            className="rounded bg-[#161f2e] border border-sky-500/20 px-1.5 py-0.5 font-mono text-[11px] text-sky-300"
          >
            {tokenizeText(m[3])}
          </code>
        )
      } else if (m[4] !== undefined) {
        // Italic: *text*
        elements.push(
          <em key={`italic-${start}`} className="italic text-slate-300">
            {tokenizeText(m[4])}
          </em>
        )
      }

      lastPos = inlineRegex.lastIndex
    }

    if (lastPos < rawText.length) {
      const remaining = rawText.substring(lastPos)
      elements.push(...tokenizeText(remaining))
    }

    return elements
  }

  const renderRichText = (text: string) => {
    const lines = text.split('\n')
    const blocks: React.ReactNode[] = []

    for (let i = 0; i < lines.length; i++) {
      const line = lines[i]
      const lineIdx = i

      // Fenced code blocks render verbatim — never concordance-tagged.
      if (line.trim().startsWith('```')) {
        const lang = line.trim().slice(3).trim()
        const codeLines: string[] = []
        i++
        while (i < lines.length && !lines[i].trim().startsWith('```')) {
          codeLines.push(lines[i])
          i++
        }
        blocks.push(
          <div
            key={`fence-${lineIdx}`}
            className="my-3 overflow-hidden rounded-lg border border-ink-line/80 bg-[#05080d]"
          >
            {lang && (
              <div className="border-b border-ink-line/60 px-3 py-1 font-mono text-[10px] uppercase tracking-wider text-slate-500">
                {lang}
              </div>
            )}
            <pre className="overflow-x-auto px-3 py-2.5">
              <code className="font-mono text-[11px] leading-relaxed text-sky-200">
                {codeLines.join('\n')}
              </code>
            </pre>
          </div>
        )
        continue
      }

      blocks.push(renderLine(line, lineIdx))
    }

    return blocks
  }

  const renderLine = (line: string, lineIdx: number): React.ReactNode => {
    // Headers
    if (line.startsWith('# ')) {
      return (
        <h1
          key={lineIdx}
          className="text-base font-bold text-slate-100 border-b border-ink-line pb-2 mt-2 mb-3"
        >
          {parseInlineMarkdown(line.replace('# ', ''))}
        </h1>
      )
    }
    if (line.startsWith('## ')) {
      return (
        <h2
          key={lineIdx}
          className="text-sm font-bold text-sky-300 mt-4 mb-2"
        >
          {parseInlineMarkdown(line.replace('## ', ''))}
        </h2>
      )
    }
    if (line.startsWith('### ')) {
      return (
        <h3
          key={lineIdx}
          className="text-xs font-bold text-slate-200 mt-3 mb-1.5 flex items-center gap-1.5"
        >
          {parseInlineMarkdown(line.replace('### ', ''))}
        </h3>
      )
    }
    if (line.startsWith('#### ')) {
      return (
        <h4
          key={lineIdx}
          className="text-xs font-semibold text-slate-300 mt-2 mb-1"
        >
          {parseInlineMarkdown(line.replace('#### ', ''))}
        </h4>
      )
    }

    // Blockquotes
    if (line.startsWith('> ')) {
      return (
        <blockquote
          key={lineIdx}
          className="border-l-2 border-sky-400/70 bg-sky-950/20 pl-3 py-1 my-2 text-slate-200 italic text-xs leading-relaxed rounded-r-md"
        >
          {parseInlineMarkdown(line.replace('> ', ''))}
        </blockquote>
      )
    }

    // Horizontal Rule
    if (line.trim() === '---') {
      return <hr key={lineIdx} className="border-ink-line/80 my-3" />
    }

    // List Items (- ...)
    if (line.trim().startsWith('- ')) {
      return (
        <div key={lineIdx} className="flex items-start gap-2 my-1 pl-2 text-slate-300 text-xs">
          <span className="text-sky-400 mt-0.5">•</span>
          <div className="leading-relaxed">
            {parseInlineMarkdown(line.trim().replace(/^- /, ''))}
          </div>
        </div>
      )
    }

    // Numbered List Items (1. ...)
    const numMatch = line.trim().match(/^(\d+)\.\s+(.*)$/)
    if (numMatch) {
      return (
        <div key={lineIdx} className="flex items-start gap-2 my-1 pl-2 text-slate-300 text-xs">
          <span className="font-mono text-sky-400 font-bold text-[11px] min-w-[14px]">
            {numMatch[1]}.
          </span>
          <div className="leading-relaxed">
            {parseInlineMarkdown(numMatch[2])}
          </div>
        </div>
      )
    }

    // Standard Line
    return (
      <p key={lineIdx} className="my-1.5 leading-relaxed text-slate-300 text-xs">
        {parseInlineMarkdown(line)}
      </p>
    )
  }

  const categories: Array<ConcordanceCategory | 'All'> = useMemo(
    () => ['All', ...CONCORDANCE_CATEGORIES],
    []
  )

  const categoryCounts = useMemo(() => {
    const counts = new Map<string, number>()
    for (const entry of GUTTAG_CONCORDANCE_LEXICON) {
      counts.set(entry.category, (counts.get(entry.category) ?? 0) + 1)
    }
    counts.set('All', GUTTAG_CONCORDANCE_LEXICON.length)
    return counts
  }, [])

  const filteredLexicon = useMemo(
    () => searchConcordance(lexiconSearch, selectedCategory),
    [lexiconSearch, selectedCategory]
  )

  const renderedContent = useMemo(
    () => renderRichText(content),
    [content, isEnabled]
  )

  return (
    <div className="relative space-y-4">
      {/* Concordance Header Action Bar */}
      {isEnabled ? (
        <div className="flex flex-wrap items-center justify-between gap-2 rounded-lg border border-sky-500/30 bg-sky-950/20 px-3.5 py-2 text-xs">
          <div className="flex items-center gap-2">
            <span className="text-sm">📖</span>
            <span className="font-semibold text-sky-200">
              Exhaustive MIT 6.0001 CS Concordance Active
            </span>
            <span className="text-[10px] text-slate-400">
              ({GUTTAG_CONCORDANCE_LEXICON.length} indexed terms across {CONCORDANCE_CATEGORIES.length} domains — hover any concept for definition & cross-references)
            </span>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={() => setShowLexiconModal(true)}
              className="flex items-center gap-1.5 rounded-md bg-sky-500/20 border border-sky-500/40 px-2.5 py-1 text-[11px] font-bold text-sky-200 hover:bg-sky-500/30 transition shadow"
              title="Search all Strong's Concordance definitions and cross references"
            >
              <span>🔍 Lexicon Index</span>
              <span className="font-mono text-[9px] bg-sky-500/30 text-sky-100 px-1 py-0.2 rounded">
                {GUTTAG_CONCORDANCE_LEXICON.length}
              </span>
            </button>
            <button
              onClick={() => handleToggle(false)}
              className="flex items-center gap-1 rounded-md bg-slate-800/80 border border-slate-700 px-2 py-1 text-[11px] text-slate-400 hover:text-slate-200 hover:border-slate-600 transition"
              title="Hide all concordance annotations and inline identifiers"
            >
              <span>Disable</span>
            </button>
          </div>
        </div>
      ) : (
        <div className="flex flex-wrap items-center justify-between gap-2 rounded-lg border border-slate-800 bg-slate-900/40 px-3.5 py-2 text-xs">
          <div className="flex items-center gap-2 text-slate-400">
            <span className="text-sm">📖</span>
            <span>MIT 6.0001 Concordance annotations are currently disabled.</span>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={() => setShowLexiconModal(true)}
              className="flex items-center gap-1.5 rounded-md bg-slate-800/80 border border-slate-700 px-2 py-1 text-[11px] text-slate-400 hover:text-slate-200 transition"
            >
              <span>🔍 Browse Lexicon</span>
            </button>
            <button
              onClick={() => handleToggle(true)}
              className="flex items-center gap-1 rounded-md bg-sky-500/20 border border-sky-500/40 px-2.5 py-1 text-[11px] font-bold text-sky-300 hover:bg-sky-500/30 hover:text-white transition shadow-sm"
              title="Turn on concordance annotations and hover definitions"
            >
              <span>⚡ Enable Concordance</span>
            </button>
          </div>
        </div>
      )}

      {/* Main Formatted Reading */}
      <div className="prose prose-invert max-w-none text-xs leading-relaxed text-slate-200 bg-[#090d13] p-5 rounded-xl border border-ink-line/80 shadow-inner">
        {renderedContent}
      </div>

      {/* FLOATING HOVER CARD */}
      {hoveredEntry && !pinnedEntry && (
        <div
          style={{
            position: 'fixed',
            left: Math.min(hoveredEntry.x, window.innerWidth - 420),
            top: hoveredEntry.y,
            zIndex: 9999,
          }}
          className="w-[400px] rounded-xl border border-sky-500/50 bg-[#0d131f] p-4 text-xs shadow-2xl backdrop-blur-md animate-in fade-in zoom-in-95 duration-150 pointer-events-none"
        >
          <div className="flex items-center justify-between border-b border-sky-500/20 pb-2 mb-2">
            <div className="flex items-center gap-2">
              <span className="chip border-sky-400 bg-sky-950/60 text-sky-300 font-mono text-[10px]">
                {hoveredEntry.entry.id}
              </span>
              <h4 className="font-bold text-slate-100 text-sm">
                {hoveredEntry.entry.term}
              </h4>
            </div>
            <span className="chip border-slate-700 text-slate-400 text-[10px]">
              {hoveredEntry.entry.category}
            </span>
          </div>

          <p className="text-slate-300 leading-relaxed mb-3">
            {hoveredEntry.entry.definition}
          </p>

          {hoveredEntry.entry.notation && (
            <p className="mb-3 rounded-lg border border-amber-500/30 bg-amber-950/20 px-2.5 py-1.5 font-mono text-[11px] text-amber-200">
              {hoveredEntry.entry.notation}
            </p>
          )}

          <div className="space-y-1.5 border-t border-ink-line/60 pt-2 text-[11px]">
            <p className="text-sky-300 font-semibold">
              📚 Primary Reference: {hoveredEntry.entry.primaryLocation}
            </p>
            <p className="text-slate-400">
              📑 Appears in <strong>{hoveredEntry.entry.occurrences.length} other chapters</strong> (Click term to open full cross-chapter concordance).
            </p>
          </div>
        </div>
      )}

      {/* PINNED DETAILED CONCORDANCE MODAL */}
      {pinnedEntry && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4 backdrop-blur-sm">
          <div className="w-full max-w-2xl max-h-[85vh] flex flex-col rounded-2xl border border-sky-500/40 bg-[#0d131f] shadow-2xl overflow-hidden">
            {/* Modal Header */}
            <div className="flex items-center justify-between border-b border-sky-500/30 bg-[#121927] px-6 py-4">
              <div className="flex items-center gap-3">
                <span className="chip border-sky-400 bg-sky-950 text-sky-300 font-mono text-xs px-2.5 py-1">
                  {pinnedEntry.id}
                </span>
                <div>
                  <h3 className="text-base font-bold text-slate-100">
                    {pinnedEntry.term}
                  </h3>
                  <p className="text-[11px] text-slate-400 font-mono">
                    Category: {pinnedEntry.category} • Primary: {pinnedEntry.primaryLocation}
                  </p>
                </div>
              </div>

              <div className="flex items-center gap-2">
                <button
                  onClick={() => copyDefinition(pinnedEntry)}
                  className="rounded-lg border border-sky-500/30 bg-sky-950/40 px-2.5 py-1 text-[11px] font-semibold text-sky-300 hover:bg-sky-500/20 transition"
                  title="Copy definition"
                >
                  {copiedId === pinnedEntry.id ? '✓ Copied' : '📋 Copy'}
                </button>
                <button
                  onClick={() => setPinnedEntry(null)}
                  className="rounded-lg p-1.5 text-slate-400 hover:text-slate-200 hover:bg-white/10"
                >
                  ✕
                </button>
              </div>
            </div>

            {/* Modal Scrollable Body */}
            <div className="p-6 overflow-y-auto space-y-5 text-xs text-slate-300">
              {/* Formal MIT Definition */}
              <div className="rounded-xl border border-sky-500/30 bg-sky-950/20 p-4 space-y-1.5">
                <p className="font-bold text-sky-300 uppercase tracking-wider text-[10px]">
                  📖 Definition:
                </p>
                <p className="text-slate-200 text-sm leading-relaxed">
                  {pinnedEntry.definition}
                </p>
              </div>

              {/* Formal Notation / Invariant */}
              {pinnedEntry.notation && (
                <div className="rounded-xl border border-amber-500/30 bg-amber-950/20 p-4 space-y-1">
                  <p className="font-bold text-amber-300 uppercase tracking-wider text-[10px]">
                    ✎ Notation:
                  </p>
                  <p className="font-mono text-[12px] leading-relaxed text-amber-100">
                    {pinnedEntry.notation}
                  </p>
                </div>
              )}

              {/* LeetCode Transfer */}
              <div className="rounded-xl border border-emerald-500/30 bg-emerald-950/20 p-4 space-y-1">
                <p className="font-bold text-emerald-300 uppercase tracking-wider text-[10px]">
                  🎯 Application:
                </p>
                <p className="text-slate-200 leading-relaxed">
                  {pinnedEntry.leetCodeRelevance}
                </p>
              </div>

              {/* All Cross-Chapter References */}
              <div className="space-y-3">
                <h4 className="font-bold text-slate-100 text-xs uppercase tracking-wider flex items-center justify-between">
                  <span>📑 Concordance ({pinnedEntry.occurrences.length} references)</span>
                </h4>

                <div className="space-y-2.5">
                  {pinnedEntry.occurrences.map((occ, idx) => (
                    <div
                      key={idx}
                      className="rounded-xl border border-ink-line/80 bg-[#080d14] p-3.5 space-y-1.5"
                    >
                      <div className="flex items-center justify-between text-[11px] font-mono">
                        <span className="font-bold text-sky-300">
                          {occ.chapter} — {occ.section}
                        </span>
                        {occ.pageRange && (
                          <span className="text-slate-500">{occ.pageRange}</span>
                        )}
                      </div>
                      <p className="text-slate-300 italic pl-2 border-l-2 border-sky-500/50">
                        "{occ.contextSnippet}"
                      </p>
                    </div>
                  ))}
                </div>
              </div>

              {/* Related Concordance Entries */}
              {pinnedEntry.relatedIds && pinnedEntry.relatedIds.length > 0 && (
                <div className="space-y-2 border-t border-ink-line/60 pt-4">
                  <h4 className="font-bold text-slate-100 text-xs uppercase tracking-wider">
                    🔗 See Also
                  </h4>
                  <div className="flex flex-wrap gap-1.5">
                    {pinnedEntry.relatedIds.map((rid) => {
                      const related = getConcordanceEntryById(rid)
                      if (!related) return null
                      return (
                        <button
                          key={rid}
                          onClick={() => setPinnedEntry(related)}
                          className="rounded-lg border border-sky-500/30 bg-sky-950/30 px-2.5 py-1 text-[11px] font-semibold text-sky-200 hover:bg-sky-500/20 transition"
                        >
                          <span className="font-mono text-[10px] text-sky-400">{related.id}</span>{' '}
                          {related.term}
                        </button>
                      )
                    })}
                  </div>
                </div>
              )}
            </div>

            {/* Footer */}
            <div className="border-t border-ink-line/60 bg-[#121927] px-6 py-3 flex justify-end">
              <button
                onClick={() => setPinnedEntry(null)}
                className="btn btn-primary px-4 py-1.5 text-xs font-bold"
              >
                Close Concordance
              </button>
            </div>
          </div>
        </div>
      )}

      {/* FULL CONCORDANCE SEARCH / BROWSE MODAL */}
      {showLexiconModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4 backdrop-blur-sm">
          <div className="w-full max-w-4xl max-h-[88vh] flex flex-col rounded-2xl border border-sky-500/40 bg-[#0d131f] shadow-2xl overflow-hidden">
            <div className="flex items-center justify-between border-b border-sky-500/30 bg-[#121927] px-6 py-4">
              <div className="flex items-center gap-2.5">
                <span className="text-xl">📚</span>
                <div>
                  <h3 className="text-base font-bold text-slate-100">
                    MIT 6.0001 Computational Thinking Lexicon
                  </h3>
                  <p className="text-[11px] text-slate-400">
                    Search {GUTTAG_CONCORDANCE_LEXICON.length} computer science definitions across{' '}
                    {CONCORDANCE_CATEGORIES.length} domains (Grounded in MIT 6.0001 & Guttag text)
                  </p>
                </div>
              </div>
              <button
                onClick={() => setShowLexiconModal(false)}
                className="rounded-lg p-1.5 text-slate-400 hover:text-slate-200 hover:bg-white/10"
              >
                ✕
              </button>
            </div>

            {/* Search & Category Filter Bar */}
            <div className="p-4 border-b border-ink-line/60 bg-[#090d14] space-y-3">
              <input
                type="text"
                value={lexiconSearch}
                onChange={(e) => setLexiconSearch(e.target.value)}
                placeholder="Search any CS concept (e.g., Identity, Aliasing, Loop Invariant, Amortized, Topological Sort, Bitmask, Big-O, Memoization, Confusion Matrix)..."
                className="w-full rounded-xl border border-sky-500/30 bg-[#0d131f] px-4 py-2 text-xs text-slate-100 placeholder:text-slate-500 focus:outline-none focus:border-sky-400"
                autoFocus
              />

              {/* Category Filter Chips */}
              <div className="flex flex-wrap items-center gap-1.5 overflow-x-auto">
                {categories.map((cat) => (
                  <button
                    key={cat}
                    onClick={() => setSelectedCategory(cat)}
                    className={`rounded-lg px-2.5 py-1 text-[10px] font-semibold transition ${
                      selectedCategory === cat
                        ? 'bg-sky-500 text-white shadow'
                        : 'bg-[#121927] text-slate-400 hover:text-slate-200'
                    }`}
                  >
                    {cat}
                    <span className="ml-1 opacity-60">{categoryCounts.get(cat) ?? 0}</span>
                  </button>
                ))}
              </div>
            </div>

            {/* Lexicon Grid List */}
            <div className="p-6 overflow-y-auto space-y-3 text-xs max-h-[550px]">
              {filteredLexicon.map((entry) => (
                <div
                  key={entry.id}
                  onClick={() => {
                    setShowLexiconModal(false)
                    setPinnedEntry(entry)
                  }}
                  className="rounded-xl border border-ink-line/80 bg-[#080d14] p-4 space-y-2 hover:border-sky-500/50 hover:bg-sky-950/20 cursor-pointer transition"
                >
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <span className="chip border-sky-400 bg-sky-950 text-sky-300 font-mono text-[10px]">
                        {entry.id}
                      </span>
                      <h4 className="font-bold text-slate-100 text-sm">
                        {entry.term}
                      </h4>
                    </div>
                    <span className="chip border-slate-700 text-slate-400 text-[10px]">
                      {entry.category}
                    </span>
                  </div>

                  <p className="text-slate-300 leading-relaxed">
                    {entry.definition}
                  </p>

                  <div className="flex items-center justify-between text-[11px] text-slate-400 pt-1 border-t border-ink-line/40">
                    <span className="text-sky-300 font-mono">
                      📍 {entry.primaryLocation}
                    </span>
                    <span className="text-sky-400 font-semibold">{entry.occurrences.length} cross-chapter references ➔</span>
                  </div>
                </div>
              ))}

              {filteredLexicon.length === 0 && (
                <p className="text-center py-8 text-slate-500">
                  No concordance terms found matching "{lexiconSearch}".
                </p>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
