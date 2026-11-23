import { useEffect, useMemo, useState } from 'react'
import type { CardReference, Lesson, QueueItem } from '../../api/types'
import { CodeEditor } from '../../components/CodeEditor'
import { OcclusionCard } from '../../components/Occlusion'
import { RichText } from '../../components/RichText'
import { Spinner } from '../../components/ui'
import { useLexicon } from '../../components/LexiconContext'
import { isCodeCard as checkIsCodeCard, looksLikeCode, extractCleanCode, detectCodeLanguage } from '../../utils/codeUtils'
import { storage } from '../../utils/storage'
import { HighlightedText } from './Feedback'
import { buildStarterTestCode, buildCompletedTestCode } from './helpers'
import { useReorderableSections } from '../../hooks/useReorderableSections'
import { ReorderableSectionFrame } from '../../components/ReorderableSectionFrame'

export type LessonSectionId = 'lesson' | 'question' | 'solution_preview'

/** Learn & Practice: the priming gate shown before testing a card's question.
 *
 *  Shows the user:
 *  1. The Question to be asked.
 *  2. The Verbatim Answer expected.
 *  3. (Optional) Supporting citations / lesson notes.
 *  Then prompts the user to enter the active recall / practice phase.
 */
export function LessonGate({
  item,
  lesson,
  loading: _loading,
  deckName,
  onContinue,
  onOpenSettings: _onOpenSettings,
  codeLanguage = 'typescript',
  activeModel,
  onActiveModelChange,
}: {
  item: QueueItem
  lesson: Lesson | null
  loading?: boolean
  deckName: string | null
  onContinue: () => void
  onOpenSettings?: () => void
  codeLanguage?: string
  activeModel?: string | null
  onActiveModelChange?: (modelId: string) => void
}) {
  const { openLexicon } = useLexicon()
  const isCode = checkIsCodeCard(item) || looksLikeCode(item.back)
  const cleanCode = useMemo(() => (isCode ? extractCleanCode(item.back) : ''), [isCode, item.back])
  const detectedLang = useMemo(
    () => (isCode ? detectCodeLanguage(cleanCode, codeLanguage) : codeLanguage),
    [isCode, cleanCode, codeLanguage]
  )

  const refTestsCode = useMemo(() => (isCode ? buildCompletedTestCode(item) : ''), [isCode, item])
  const starterTestsCode = useMemo(() => (isCode ? buildStarterTestCode(item) : ''), [isCode, item])
  const displayTestsCode = refTestsCode.trim() ? refTestsCode : starterTestsCode
  const testCases = item.test_cases || []
  const edgeCases = item.edge_cases || []
  const hasTests = Boolean(displayTestsCode.trim() || testCases.length > 0)

  const [codeLayout, setCodeLayout] = useState<'stacked' | 'split'>(() => {
    return (storage.get('memorization.learnGateCodeLayout') as 'stacked' | 'split') || 'stacked'
  })
  const [testsTab, setTestsTab] = useState<'all' | 'code' | 'cases'>('all')
  const [showTestsSection, setShowTestsSection] = useState(true)
  const [showSolutionPeek, setShowSolutionPeek] = useState(false)
  const [copiedAnswer, setCopiedAnswer] = useState(false)
  const [copiedTests, setCopiedTests] = useState(false)

  // Reset solution peek when moving to a different card
  useEffect(() => {
    setShowSolutionPeek(false)
  }, [item.id])

  const handleCopyAnswer = async () => {
    if (!cleanCode) return
    try {
      await navigator.clipboard.writeText(cleanCode)
      setCopiedAnswer(true)
      setTimeout(() => setCopiedAnswer(false), 1800)
    } catch {
      // ignore
    }
  }

  const handleCopyTests = async () => {
    const textToCopy = displayTestsCode.trim() || JSON.stringify(testCases, null, 2)
    if (!textToCopy) return
    try {
      await navigator.clipboard.writeText(textToCopy)
      setCopiedTests(true)
      setTimeout(() => setCopiedTests(false), 1800)
    } catch {
      // ignore
    }
  }

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Enter' && !e.shiftKey && !e.metaKey && !e.ctrlKey) {
        if (e.isComposing || e.keyCode === 229) {
          return
        }
        const target = e.target as HTMLElement
        if (target.tagName !== 'INPUT' && target.tagName !== 'TEXTAREA') {
          e.preventDefault()
          onContinue()
        }
      }
    }
    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [onContinue])

  const hasReferences = Boolean(item.references && item.references.length > 0)
  const thematic = item.card_thematic_nature || item.deck_thematic_nature
  const doc = item.card_documentation || item.deck_documentation

  const renderAnswerCard = () => (
    <div className="space-y-2 rounded-xl border border-emerald-500/40 bg-emerald-950/20 p-4">
      <div className="flex items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <span className="text-xs font-bold uppercase tracking-wider text-emerald-300 flex items-center gap-1.5">
            Answer · Solution
          </span>
          <span className="rounded bg-emerald-500/10 px-2 py-0.5 text-xs font-mono text-emerald-300 border border-emerald-500/30">
            {detectedLang}
          </span>
        </div>
        <div className="flex items-center gap-2">
          {cleanCode && (
            <button
              type="button"
              onClick={() => void handleCopyAnswer()}
              className="flex items-center gap-1 rounded border border-ink-line bg-[#161b24] hover:bg-[#1f2633] px-2 py-0.5 text-xs text-slate-300 hover:text-white transition cursor-pointer"
              title="Copy solution code to clipboard"
            >
              <span>{copiedAnswer ? 'Copied' : 'Copy'}</span>
            </button>
          )}
        </div>
      </div>

      <div className="rounded-lg border border-ink-line overflow-hidden shadow-sm">
        <CodeEditor
          code={cleanCode}
          onChange={() => {}}
          language={detectedLang}
          readOnly={true}
          height="auto"
          hideHeader={false}
          hideFooter={false}
          borderless={true}
          placeholder="// Expected answer solution"
          activeModel={activeModel}
          onActiveModelChange={onActiveModelChange}
        />
      </div>

      {(item.time_complexity || item.space_complexity) && (
        <div className="flex items-center gap-3 pt-1 text-xs text-emerald-400/90 font-mono">
          {item.time_complexity && <span>Time: {item.time_complexity}</span>}
          {item.space_complexity && <span>Space: {item.space_complexity}</span>}
        </div>
      )}
    </div>
  )

  const renderTestsCard = () => {
    if (!hasTests) return null

    return (
      <div className="space-y-3 rounded-xl border border-indigo-500/40 bg-indigo-950/20 p-4">
        {/* Header */}
        <div className="flex flex-wrap items-center justify-between gap-2 border-b border-indigo-500/20 pb-2.5">
          <div className="flex flex-wrap items-center gap-2">
            <span className="text-xs font-bold uppercase tracking-wider text-indigo-300 flex items-center gap-1.5">
              <span>Tests &amp; Verification</span>
            </span>
            {testCases.length > 0 && (
              <span className="rounded-full bg-indigo-500/15 border border-indigo-500/30 px-2 py-0.5 text-[0.625rem] font-mono text-indigo-200">
                {testCases.length} {testCases.length === 1 ? 'case' : 'cases'}
              </span>
            )}
            {/* View Sub-Tabs if both unit test code and test cases exist */}
            {displayTestsCode.trim() && testCases.length > 0 && (
              <div className="inline-flex rounded-md bg-[#121622] p-0.5 border border-ink-line text-[0.6875rem] ml-1">
                <button
                  type="button"
                  onClick={() => setTestsTab('all')}
                  className={`px-2 py-0.5 rounded transition cursor-pointer ${
                    testsTab === 'all'
                      ? 'bg-indigo-600/40 text-indigo-100 border border-indigo-500/50 font-semibold'
                      : 'text-slate-400 hover:text-slate-200'
                  }`}
                >
                  All
                </button>
                <button
                  type="button"
                  onClick={() => setTestsTab('code')}
                  className={`px-2 py-0.5 rounded transition cursor-pointer ${
                    testsTab === 'code'
                      ? 'bg-indigo-600/40 text-indigo-100 border border-indigo-500/50 font-semibold'
                      : 'text-slate-400 hover:text-slate-200'
                  }`}
                >
                  Unit Tests
                </button>
                <button
                  type="button"
                  onClick={() => setTestsTab('cases')}
                  className={`px-2 py-0.5 rounded transition cursor-pointer ${
                    testsTab === 'cases'
                      ? 'bg-indigo-600/40 text-indigo-100 border border-indigo-500/50 font-semibold'
                      : 'text-slate-400 hover:text-slate-200'
                  }`}
                >
                  Cases ({testCases.length})
                </button>
              </div>
            )}
          </div>

          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={() => void handleCopyTests()}
              className="flex items-center gap-1 rounded border border-ink-line bg-[#161b24] hover:bg-[#1f2633] px-2 py-0.5 text-xs text-slate-300 hover:text-white transition cursor-pointer"
              title="Copy unit tests to clipboard"
            >
              <span>{copiedTests ? 'Copied' : 'Copy Tests'}</span>
            </button>
            <button
              type="button"
              onClick={() => setShowTestsSection((prev) => !prev)}
              className="rounded border border-ink-line/60 bg-[#161b24] hover:bg-[#1f2633] px-2 py-0.5 text-xs text-slate-400 hover:text-slate-200 transition cursor-pointer"
              title={showTestsSection ? 'Collapse tests' : 'Expand tests'}
            >
              <span>{showTestsSection ? 'Hide' : 'Show'}</span>
            </button>
          </div>
        </div>

        {/* Content Body */}
        {showTestsSection && (
          <div className="space-y-4">
            {/* 1. Unit Tests Code */}
            {(testsTab === 'all' || testsTab === 'code') && displayTestsCode.trim() && (
              <div className="space-y-1.5">
                <div className="flex items-center justify-between text-xs text-slate-400">
                  <span className="font-semibold text-slate-200">Unit Test Suite</span>
                  <span className="font-mono text-[0.6875rem] text-indigo-300">{detectedLang}</span>
                </div>
                <div className="rounded-lg border border-ink-line overflow-hidden shadow-sm">
                  <CodeEditor
                    code={displayTestsCode}
                    onChange={() => {}}
                    language={detectedLang}
                    readOnly={true}
                    height="auto"
                    hideHeader={false}
                    hideFooter={false}
                    borderless={true}
                    placeholder="// Completed unit test suite"
                    activeModel={activeModel}
                    onActiveModelChange={onActiveModelChange}
                  />
                </div>
              </div>
            )}

            {/* 2. Structured Test Cases Table */}
            {(testsTab === 'all' || testsTab === 'cases') && testCases.length > 0 && (
              <div className="space-y-1.5">
                <div className="flex items-center justify-between text-xs text-slate-400">
                  <span className="font-semibold text-slate-200">Test Cases ({testCases.length})</span>
                </div>
                <div className="overflow-x-auto rounded-lg border border-ink-line/80">
                  <table className="w-full text-left text-xs">
                    <thead className="bg-[#182030] text-slate-300 font-mono text-[0.6875rem] border-b border-ink-line/80">
                      <tr>
                        <th className="px-3 py-2 w-10 text-slate-400">#</th>
                        <th className="px-3 py-2">Input</th>
                        <th className="px-3 py-2">Expected Output</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-ink-line/40 font-mono text-[0.6875rem] bg-[#10141f]">
                      {testCases.map((tc, idx) => (
                        <tr key={idx} className="hover:bg-[#161c2b] transition-colors">
                          <td className="px-3 py-2 text-slate-500 font-bold">{idx + 1}</td>
                          <td className="px-3 py-2 text-sky-200">
                            {typeof tc.input === 'object' && tc.input !== null
                              ? Object.entries(tc.input)
                                  .map(([k, v]) => `${k}: ${JSON.stringify(v)}`)
                                  .join(', ')
                              : JSON.stringify(tc.input)}
                          </td>
                          <td className="px-3 py-2 text-emerald-300 font-semibold">
                            {JSON.stringify(tc.expected)}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}

            {/* 3. Edge Cases */}
            {edgeCases.length > 0 && (
              <div className="rounded-lg bg-[#121622] border border-indigo-500/30 p-2.5 text-xs text-slate-300 space-y-1">
                <span className="font-semibold text-indigo-300 text-[0.6875rem] uppercase tracking-wider block">
                  Target Edge Cases &amp; Boundaries:
                </span>
                <ul className="list-disc list-inside space-y-0.5 text-slate-300 text-[0.6875rem]">
                  {edgeCases.map((ec, i) => (
                    <li key={i}>
                      <RichText text={ec} inline className="text-[0.6875rem] text-slate-300" />
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        )}
      </div>
    )
  }

  const hasStructuredSocratic = Boolean(
    lesson?.available &&
      lesson.socratic &&
      (lesson.socratic.readings.length > 0 ||
        lesson.socratic.core_idea ||
        lesson.socratic.trap ||
        lesson.socratic.invariants),
  )

  const shouldRenderTitleHeading = useMemo(() => {
    if (!item.title) return false
    const cleanTitle = item.title.trim().toLowerCase()
    const frontStart = (item.front || '')
      .trim()
      .replace(/^\*\*|\*\*$|^#+\s*/g, '')
      .toLowerCase()
    if (!frontStart) return true
    if (frontStart.startsWith(cleanTitle)) return false
    // Also skip generic duplicate headings like "What does this print? (js01-typeof)" when front starts with "What does this print?"
    const baseTitle = cleanTitle.replace(/\s*\([^)]*\)\s*$/, '').trim()
    if (baseTitle.length >= 8 && frontStart.startsWith(baseTitle)) return false
    return true
  }, [item.title, item.front])

  const {
    sections,
    isCustomized,
    draggingId,
    dragOverId,
    dropPosition,
    collapsedMap,
    moveSection,
    resetOrder,
    toggleCollapse,
    handleDragStart,
    handleDragOver,
    handleDragLeave,
    handleDrop,
    handleDragEnd,
  } = useReorderableSections<LessonSectionId>({
    storageKey: 'memorization.learnGateSectionOrder',
    defaultOrder: ['lesson', 'question', 'solution_preview'] as const,
    collapsedStorageKey: 'memorization.learnGateCollapsedSections',
  })

  return (
    <div className="card space-y-5">
      {/* ── Top Header Strip ── */}
      <div className="flex flex-wrap items-center justify-between gap-2 border-b border-ink-line pb-3 text-xs">
        <div className="flex flex-wrap items-center gap-2">
          {deckName && <span className="font-semibold text-slate-200">{deckName}</span>}
          <span className="text-slate-600">·</span>
          <span className="font-medium text-sky-300">Learn &amp; Practice</span>
          {item.difficulty && (
            <>
              <span className="text-slate-600">·</span>
              <span className="text-slate-400">{item.difficulty}</span>
            </>
          )}
        </div>

        <button
          type="button"
          onClick={() =>
            openLexicon(item.title || 'terminology', item.front || '', null, {
              cardId: item.id,
              deckName,
              thematicNature: thematic,
            })
          }
          className="flex items-center gap-1.5 rounded-md border border-sky-400/35 bg-sky-950/60 px-2.5 py-1 text-xs font-medium text-sky-200 hover:bg-sky-900/70 hover:border-sky-300 transition-colors cursor-pointer"
          title="Lexicon lookup"
        >
          <span>Lexicon</span>
        </button>
      </div>

      {/* Step Indicator Banner */}
      <div className="rounded-lg bg-sky-500/10 border border-sky-500/25 px-3.5 py-2.5 text-xs text-sky-200 flex flex-wrap items-center justify-between gap-3">
        <div className="flex flex-wrap items-center gap-2">
          <span className="font-semibold text-sky-300">Socratic Primer</span>
          <span className="text-slate-300">
            Build the mental model from the study guide below, then test your recall.
          </span>
        </div>
        <div className="flex items-center gap-2">
          {isCustomized && (
            <button
              type="button"
              onClick={resetOrder}
              className="px-2 py-0.5 rounded bg-slate-800 text-[0.6875rem] border border-slate-700 text-sky-300 hover:text-white hover:bg-slate-700 transition cursor-pointer flex items-center gap-1 shadow-xs"
              title="Reset sections to default order"
            >
              <span>↺ Reset Layout</span>
            </button>
          )}
          <kbd className="hidden sm:inline-block shrink-0 px-2 py-0.5 rounded bg-slate-900 text-[0.6875rem] font-mono border border-slate-700 text-sky-300">
            Enter ↵
          </kbd>
        </div>
      </div>

      {/* ── Reorderable Sections (User Draggable) ── */}
      <div className="space-y-4">
        {sections.map((sectionId, index) => {
          const isFirst = index === 0
          const isLast = index === sections.length - 1
          const isDragging = draggingId === sectionId
          const isDropBefore = dragOverId === sectionId && dropPosition === 'before'
          const isDropAfter = dragOverId === sectionId && dropPosition === 'after'
          const isCollapsed = Boolean(collapsedMap[sectionId])

          if (sectionId === 'lesson') {
            return (
              <ReorderableSectionFrame
                key="lesson"
                id="lesson"
                isCollapsed={isCollapsed}
                isFirst={isFirst}
                isLast={isLast}
                isDragging={isDragging}
                isDropBefore={isDropBefore}
                isDropAfter={isDropAfter}
                onDragStart={handleDragStart}
                onDragOver={handleDragOver}
                onDragLeave={handleDragLeave}
                onDrop={handleDrop}
                onDragEnd={handleDragEnd}
                onMoveUp={() => moveSection('lesson', 'up')}
                onMoveDown={() => moveSection('lesson', 'down')}
                onToggleCollapse={() => toggleCollapse('lesson')}
                className="rounded-xl border border-sky-500/40 bg-gradient-to-br from-sky-950/25 via-[#0e1422] to-slate-950/60 shadow-md overflow-hidden"
                renderHeader={({ dragHandle, moveButtons, collapseButton }) => (
                  <div className={`flex flex-wrap items-center justify-between gap-2 p-4 ${isCollapsed ? '' : 'border-b border-sky-500/20 pb-2.5'}`}>
                    <div className="flex items-center gap-2">
                      {dragHandle}
                      <span className="text-xs font-bold uppercase tracking-wider text-sky-300 flex items-center gap-1.5">
                        <span>🧠 Socratic Lesson · Mental Model &amp; Intuition</span>
                      </span>
                      {lesson?.model_used && (
                        <span className="chip text-[0.625rem] text-slate-400 border-sky-500/30 bg-sky-500/10">
                          {lesson.model_used}
                        </span>
                      )}
                      {isCollapsed && (
                        <span className="text-[0.6875rem] text-slate-500 italic">
                          (Collapsed — click + to expand)
                        </span>
                      )}
                    </div>
                    <div className="flex items-center gap-2">
                      {moveButtons}
                      {collapseButton}
                    </div>
                  </div>
                )}
              >
                <div className="p-4 pt-3">
                  {_loading ? (
                    <div className="py-4">
                      <Spinner label="Loading Socratic lesson…" />
                    </div>
                  ) : lesson && lesson.available ? (
                    <SocraticLessonPanel
                      lesson={lesson}
                      codeLanguage={detectedLang}
                      deckId={item.kind === 'card' ? item.deck_or_source_id : null}
                    />
                  ) : (
                    <div className="text-xs text-slate-300 leading-relaxed">
                      <RichText
                        text={doc || thematic || 'Review the core concepts and mental model for this card before testing.'}
                        codeLanguage={detectedLang}
                        deckId={item.kind === 'card' ? item.deck_or_source_id : null}
                      />
                    </div>
                  )}
                </div>
              </ReorderableSectionFrame>
            )
          }

          if (sectionId === 'question') {
            return (
              <ReorderableSectionFrame
                key="question"
                id="question"
                isCollapsed={isCollapsed}
                isFirst={isFirst}
                isLast={isLast}
                isDragging={isDragging}
                isDropBefore={isDropBefore}
                isDropAfter={isDropAfter}
                onDragStart={handleDragStart}
                onDragOver={handleDragOver}
                onDragLeave={handleDragLeave}
                onDrop={handleDrop}
                onDragEnd={handleDragEnd}
                onMoveUp={() => moveSection('question', 'up')}
                onMoveDown={() => moveSection('question', 'down')}
                onToggleCollapse={() => toggleCollapse('question')}
                className="rounded-xl border border-sky-500/30 bg-sky-950/15 overflow-hidden"
                renderHeader={({ dragHandle, moveButtons, collapseButton }) => (
                  <div className={`flex items-center justify-between p-4 ${isCollapsed ? '' : 'border-b border-sky-500/15 pb-2.5'}`}>
                    <div className="flex items-center gap-2">
                      {dragHandle}
                      <span className="text-xs font-bold uppercase tracking-wider text-sky-300 flex items-center gap-1.5">
                        Question
                      </span>
                      {item.category && (
                        <span className="chip text-[0.625rem] text-slate-400">{item.category}</span>
                      )}
                      {isCollapsed && (
                        <span className="text-[0.6875rem] text-slate-500 italic truncate max-w-xs">
                          ({item.title || item.front?.slice(0, 40) || 'Collapsed'})
                        </span>
                      )}
                    </div>
                    <div className="flex items-center gap-2">
                      {moveButtons}
                      {collapseButton}
                    </div>
                  </div>
                )}
              >
                <div className="p-4 pt-3 space-y-2.5">
                  {shouldRenderTitleHeading && item.title && (
                    <h3 className="text-base font-bold text-slate-100">{item.title}</h3>
                  )}

                  {item.occlusion ? (
                    <div className="space-y-2">
                      {item.occlusion.header && (
                        <p className="text-sm font-medium text-slate-200">{item.occlusion.header}</p>
                      )}
                      <OcclusionCard payload={item.occlusion} revealed={false} />
                    </div>
                  ) : (
                    <RichText
                      text={item.front || item.title || 'No prompt specified'}
                      className="text-sm md:text-base font-medium text-slate-100 leading-relaxed"
                      codeLanguage={detectedLang}
                      deckId={item.kind === 'card' ? item.deck_or_source_id : null}
                    />
                  )}
                </div>
              </ReorderableSectionFrame>
            )
          }

          if (sectionId === 'solution_preview') {
            return (
              <ReorderableSectionFrame
                key="solution_preview"
                id="solution_preview"
                isCollapsed={isCollapsed}
                isFirst={isFirst}
                isLast={isLast}
                isDragging={isDragging}
                isDropBefore={isDropBefore}
                isDropAfter={isDropAfter}
                onDragStart={handleDragStart}
                onDragOver={handleDragOver}
                onDragLeave={handleDragLeave}
                onDrop={handleDrop}
                onDragEnd={handleDragEnd}
                onMoveUp={() => moveSection('solution_preview', 'up')}
                onMoveDown={() => moveSection('solution_preview', 'down')}
                onToggleCollapse={() => toggleCollapse('solution_preview')}
                className="rounded-xl border border-ink-line/80 bg-ink/30 overflow-hidden"
                renderHeader={({ dragHandle, moveButtons, collapseButton }) => (
                  <div className="flex flex-wrap items-center justify-between gap-2 p-3.5">
                    <div className="flex items-center gap-2">
                      {dragHandle}
                      <div>
                        <span className="text-xs font-semibold text-slate-300 block">
                          Solution &amp; Verification Preview
                        </span>
                        <span className="text-[0.6875rem] text-slate-400">
                          {isCollapsed
                            ? 'Click + to expand preview card'
                            : 'Solution is hidden by default to support active recall. Click to inspect before starting the quiz.'}
                        </span>
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      {!isCollapsed && hasStructuredSocratic && (
                        <button
                          type="button"
                          onClick={() => setShowSolutionPeek((prev) => !prev)}
                          className="btn btn-secondary text-xs px-3 py-1 flex items-center gap-1.5 cursor-pointer hover:bg-slate-800 transition"
                        >
                          <span>{showSolutionPeek ? 'Hide Solution' : '👁 Peek Solution'}</span>
                        </button>
                      )}
                      {moveButtons}
                      {collapseButton}
                    </div>
                  </div>
                )}
              >
                {(!hasStructuredSocratic || showSolutionPeek) && (
                  <div className="p-3.5 pt-0 border-t border-ink-line/60 mt-2 space-y-4">
                    {item.occlusion ? (
                      <div className="space-y-2 rounded-xl border border-emerald-500/40 bg-emerald-950/20 p-4">
                        <span className="text-xs font-bold uppercase tracking-wider text-emerald-300 flex items-center gap-1.5">
                          Answer
                        </span>
                        <OcclusionCard payload={item.occlusion} revealed={true} />
                      </div>
                    ) : isCode ? (
                      <div className="space-y-3">
                        {hasTests && (
                          <div className="flex flex-wrap items-center justify-between gap-2 text-xs px-1">
                            <div className="flex items-center gap-1.5">
                              <span className="text-[0.6875rem] font-semibold uppercase tracking-wider text-slate-400">Layout:</span>
                              <div className="inline-flex rounded-lg bg-[#141822] p-0.5 border border-ink-line/60">
                                <button
                                  type="button"
                                  onClick={() => {
                                    setCodeLayout('stacked')
                                    storage.set('memorization.learnGateCodeLayout', 'stacked')
                                  }}
                                  className={`px-2.5 py-0.5 rounded text-xs font-medium transition cursor-pointer flex items-center gap-1.5 ${
                                    codeLayout === 'stacked'
                                      ? 'bg-slate-700/70 text-white border border-slate-500/50 shadow-sm font-semibold'
                                      : 'text-slate-400 hover:text-slate-200'
                                  }`}
                                >
                                  <span>Stacked</span>
                                </button>
                                <button
                                  type="button"
                                  onClick={() => {
                                    setCodeLayout('split')
                                    storage.set('memorization.learnGateCodeLayout', 'split')
                                  }}
                                  className={`hidden sm:flex px-2.5 py-0.5 rounded text-xs font-medium transition cursor-pointer items-center gap-1.5 ${
                                    codeLayout === 'split'
                                      ? 'bg-sky-600/40 text-sky-100 border border-sky-500/50 shadow-sm font-semibold'
                                      : 'text-slate-400 hover:text-slate-200'
                                  }`}
                                >
                                  <span>⧉ Side-by-Side</span>
                                </button>
                              </div>
                            </div>
                          </div>
                        )}

                        {codeLayout === 'split' && hasTests ? (
                          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 items-start">
                            {renderAnswerCard()}
                            {renderTestsCard()}
                          </div>
                        ) : (
                          <div className="space-y-4">
                            {renderAnswerCard()}
                            {renderTestsCard()}
                          </div>
                        )}
                      </div>
                    ) : (
                      <div className="space-y-2 rounded-xl border border-emerald-500/40 bg-emerald-950/20 p-4">
                        <span className="text-xs font-bold uppercase tracking-wider text-emerald-300 flex items-center gap-1.5">
                          Answer
                        </span>
                        <div className="rounded-lg border border-emerald-500/20 bg-slate-950/70 p-3.5">
                          <RichText
                            text={item.back || 'No answer specified'}
                            className="text-xs md:text-sm text-emerald-100 leading-relaxed font-mono whitespace-pre-wrap"
                          />
                        </div>
                        {(item.time_complexity || item.space_complexity) && (
                          <div className="flex items-center gap-3 pt-1 text-xs text-emerald-400/90 font-mono">
                            {item.time_complexity && <span>Time: {item.time_complexity}</span>}
                            {item.space_complexity && <span>Space: {item.space_complexity}</span>}
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                )}
              </ReorderableSectionFrame>
            )
          }

          return null
        })}
      </div>

      {/* ── 4. Supporting Context / Deck Documentation ── */}
      {(doc || hasReferences) && (
        <details className="rounded-lg border border-ink-line/80 bg-ink/40 p-3 text-xs text-slate-300 group">
          <summary className="cursor-pointer font-semibold text-slate-400 hover:text-slate-200 flex items-center gap-1.5 select-none">
            <span>Deck Documentation &amp; References</span>
          </summary>
          <div className="mt-3 space-y-3 pt-2 border-t border-ink-line/60">
            {doc && (
              <div>
                <span className="text-slate-400 font-medium block mb-1">Documentation:</span>
                <RichText text={doc} className="text-xs leading-relaxed text-slate-300" />
              </div>
            )}
            {hasReferences && (
              <div className="flex flex-wrap items-center gap-1.5 pt-1">
                <span className="text-slate-400 text-[0.6875rem]">Citations:</span>
                {item.references.map((ref, idx) => (
                  <span key={idx} className="chip text-[0.625rem] text-slate-400" title={ref.quote || undefined}>
                    {ref.source_title ?? ref.locator ?? 'source'}
                  </span>
                ))}
              </div>
            )}
          </div>
        </details>
      )}

      {/* ── 5. Call-to-action to enter Practice Phase ── */}
      <div className="pt-2">
        <button
          type="button"
          className="btn btn-primary w-full py-3 text-sm font-bold flex items-center justify-center gap-2 shadow-lg shadow-sky-950/40 hover:scale-[1.01] active:scale-[0.99] transition-all cursor-pointer"
          onClick={onContinue}
        >
          <span>Start Quiz</span>
          <span className="text-xs text-sky-300/80 font-normal">Enter ↵</span>
        </button>
      </div>
    </div>
  )
}

/** The card's Socratic Lesson after the reveal, shown under the reference
 *  answer. Adds loading, failure and collapse handling around
 *  SocraticLessonPanel; renders nothing when there is no lesson to teach.
 */
export function RevealedLesson({
  lesson,
  loading,
  error,
  codeLanguage,
  deckId,
}: {
  lesson: Lesson | null
  loading: boolean
  error: string | null
  codeLanguage?: string
  deckId?: string | null
}) {
  const [open, setOpen] = useState(true)

  if (!loading && !error && (!lesson || !lesson.available)) return null

  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between gap-2">
        <p className="label !mb-0">Learn &amp; Practice</p>
        <button
          type="button"
          onClick={() => setOpen((v) => !v)}
          className="text-xs text-slate-500 underline hover:text-slate-300"
          aria-expanded={open}
        >
          {open ? 'Hide lesson' : 'Show lesson'}
        </button>
      </div>
      {open &&
        (lesson && lesson.available ? (
          <SocraticLessonPanel lesson={lesson} codeLanguage={codeLanguage} deckId={deckId} />
        ) : loading ? (
          <Spinner label="Loading Socratic lesson…" />
        ) : (
          <p className="text-xs text-amber-300">Lesson unavailable: {error}</p>
        ))}
    </div>
  )
}

/** Structured, non-spoiling Socratic Lesson renderer shared by Learn & Practice and PrimerDrawer. */
export function SocraticLessonPanel({
  lesson,
  codeLanguage = 'javascript',
  deckId = null,
  compact = false,
}: {
  lesson: Lesson
  codeLanguage?: string
  deckId?: string | null
  compact?: boolean
}) {
  const s = lesson.socratic

  if (!s) {
    return (
      <div className="rounded-xl border border-indigo-500/30 bg-[#101522] p-4 space-y-3">
        <div className="flex items-center justify-between gap-2 border-b border-ink-line/70 pb-2">
          <span className="text-xs font-bold uppercase tracking-wider text-indigo-300">
            Socratic Lesson
          </span>
          {lesson.model_used && (
            <span className="text-[0.6875rem] font-mono text-slate-400">{lesson.model_used}</span>
          )}
        </div>
        <RichText
          text={lesson.body}
          className="text-sm leading-relaxed text-slate-200"
          codeLanguage={codeLanguage}
          deckId={deckId}
        />
        {lesson.key_points && lesson.key_points.length > 0 && (
          <div className="pt-2 border-t border-ink-line/60 space-y-1.5">
            <p className="text-[0.6875rem] font-bold uppercase tracking-wider text-sky-300">
              Key Principles &amp; Takeaways
            </p>
            <ul className="space-y-1.5 text-xs text-slate-200">
              {lesson.key_points.map((p, i) => (
                <li key={i} className="flex items-start gap-2">
                  <span className="text-emerald-400 mt-0.5 shrink-0">✓</span>
                  <div className="min-w-0 flex-1">
                    <RichText text={p} className="text-xs leading-relaxed text-slate-200" codeLanguage={codeLanguage} />
                  </div>
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>
    )
  }

  const hasMentalModelGrid = Boolean(s.invariants || s.types || s.memory_model || s.trap || s.failure_mode)

  return (
    <section
      aria-label="Socratic Lesson"
      className={`rounded-xl border border-indigo-500/30 bg-[#0e1320] ${compact ? 'p-3.5 space-y-3.5' : 'p-5 space-y-4'}`}
    >
      {/* Lesson Header */}
      <div className="flex flex-wrap items-start justify-between gap-2 border-b border-ink-line/70 pb-3">
        <div className="space-y-0.5 min-w-0">
          <div className="flex flex-wrap items-center gap-2 text-[0.6875rem] font-semibold uppercase tracking-wider text-indigo-300">
            <span>Socratic Lesson</span>
            {s.chapter_number !== null && (
              <>
                <span className="text-slate-600">·</span>
                <span className="text-slate-300">Ch. {s.chapter_number}</span>
              </>
            )}
            <span className="text-slate-600">·</span>
            <span className="text-slate-400 font-normal normal-case tracking-normal">{s.source_guide}</span>
          </div>
          {s.chapter_title && (
            <h2 className={`${compact ? 'text-sm' : 'text-base'} font-semibold text-slate-100 leading-snug`}>
              {s.chapter_title}
            </h2>
          )}
        </div>

        {s.doc_links.length > 0 && (
          <div className="flex flex-wrap items-center gap-2">
            {s.doc_links.map((dl, idx) => (
              <a
                key={idx}
                href={dl.url}
                target="_blank"
                rel="noopener noreferrer"
                className="text-xs text-sky-300 hover:text-sky-200 underline underline-offset-2 decoration-sky-500/50 transition-colors"
              >
                {dl.label} ↗
              </a>
            ))}
          </div>
        )}
      </div>

      {/* Core Idea */}
      {s.core_idea && (
        <div className="rounded-lg border-l-2 border-sky-400 bg-sky-950/25 px-3.5 py-2.5">
          <p className="text-[0.6875rem] font-semibold uppercase tracking-wider text-sky-300 mb-1">
            Core Mental Model
          </p>
          <RichText
            text={s.core_idea}
            className="text-sm text-slate-100 leading-relaxed"
            codeLanguage={codeLanguage}
            deckId={deckId}
          />
        </div>
      )}

      {/* From the Readings (Targeted Q&A with runnable examples) */}
      {s.readings.length > 0 && (
        <div className="space-y-4">
          {s.readings.map((block, bIdx) => (
            <div key={bIdx} className="space-y-3">
              {block.sections.map((sec, sIdx) => (
                <div
                  key={sIdx}
                  className="rounded-lg border border-ink-line/70 bg-[#121827] p-3.5 space-y-2"
                >
                  {sec.question && (
                    <h3 className="text-sm font-semibold text-sky-200 leading-snug">
                      {sec.question}
                    </h3>
                  )}
                  <RichText
                    text={sec.body}
                    className="text-sm leading-relaxed text-slate-200"
                    codeLanguage={codeLanguage}
                    deckId={deckId}
                    codeBlockLabel="Worked Example"
                  />
                </div>
              ))}
            </div>
          ))}
        </div>
      )}

      {/* Key Terms & Analogies */}
      {s.terms.length > 0 && (
        <div className="space-y-2">
          <p className="text-[0.6875rem] font-semibold uppercase tracking-wider text-slate-400">
            Key Terms &amp; Analogies
          </p>
          <dl className={`grid gap-2 ${s.terms.length > 1 && !compact ? 'grid-cols-1 md:grid-cols-2' : 'grid-cols-1'}`}>
            {s.terms.map((t, idx) => (
              <div
                key={idx}
                className="rounded-lg border border-ink-line/60 bg-ink/50 px-3 py-2 text-xs leading-relaxed"
              >
                <dt className="font-semibold text-indigo-200 mb-0.5">{t.term}</dt>
                <dd className="text-slate-300">
                  <RichText text={t.definition} inline className="text-xs leading-relaxed text-slate-300" codeLanguage={codeLanguage} />
                </dd>
              </div>
            ))}
          </dl>
        </div>
      )}

      {/* Invariants & Common Trap Grid */}
      {hasMentalModelGrid && (
        <div className={`grid gap-3 ${!compact ? 'grid-cols-1 md:grid-cols-2' : 'grid-cols-1'}`}>
          {(s.invariants || s.types || s.memory_model) && (
            <div className="rounded-lg border border-emerald-500/25 bg-emerald-950/15 p-3 space-y-2">
              <p className="text-[0.6875rem] font-semibold uppercase tracking-wider text-emerald-300">
                Invariants &amp; Mechanics
              </p>
              {s.invariants && (
                <div className="text-xs leading-relaxed text-slate-200">
                  <span className="font-semibold text-emerald-200">Invariant: </span>
                  <RichText text={s.invariants} inline className="text-xs text-slate-200" codeLanguage={codeLanguage} />
                </div>
              )}
              {s.types && (
                <div className="text-xs leading-relaxed text-slate-300">
                  <span className="font-semibold text-slate-200">Types: </span>
                  <RichText text={s.types} inline className="text-xs text-slate-300" codeLanguage={codeLanguage} />
                </div>
              )}
              {s.memory_model && (
                <div className="text-xs leading-relaxed text-slate-300">
                  <span className="font-semibold text-slate-200">Memory: </span>
                  <RichText text={s.memory_model} inline className="text-xs text-slate-300" codeLanguage={codeLanguage} />
                </div>
              )}
            </div>
          )}

          {(s.trap || s.failure_mode) && (
            <div className="rounded-lg border border-amber-500/30 bg-amber-950/15 p-3 space-y-2">
              <p className="text-[0.6875rem] font-semibold uppercase tracking-wider text-amber-300">
                Watch Out · Common Trap
              </p>
              {s.trap && (
                <div className="text-xs leading-relaxed text-amber-100">
                  <RichText text={s.trap} inline className="text-xs text-amber-100" codeLanguage={codeLanguage} />
                </div>
              )}
              {s.failure_mode && (
                <div className="text-xs leading-relaxed text-slate-300 border-t border-amber-500/20 pt-1.5">
                  <span className="font-semibold text-amber-200/90">Typical mistake: </span>
                  <RichText text={s.failure_mode} inline className="text-xs text-slate-300" codeLanguage={codeLanguage} />
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {/* Think It Through (Socratic reflection prompt) */}
      {(s.think_it_through || s.rule) && (
        <div className="rounded-lg border border-indigo-400/25 bg-indigo-950/20 px-3.5 py-2.5 space-y-1.5">
          {s.think_it_through && (
            <div>
              <p className="text-[0.6875rem] font-semibold uppercase tracking-wider text-indigo-300 mb-0.5">
                Think It Through
              </p>
              <RichText
                text={s.think_it_through}
                className="text-xs md:text-sm text-indigo-100 leading-relaxed"
                codeLanguage={codeLanguage}
                deckId={deckId}
              />
            </div>
          )}
          {s.rule && (
            <div className="text-xs leading-relaxed text-slate-300 border-t border-indigo-400/15 pt-1.5">
              <span className="font-semibold text-sky-300">Rule of thumb: </span>
              <RichText text={s.rule} inline className="text-xs text-slate-200" codeLanguage={codeLanguage} />
            </div>
          )}
        </div>
      )}

      {/* Fallback Key Points (rendered with RichText so inline code never shows raw backticks) */}
      {s.readings.length === 0 && !hasMentalModelGrid && lesson.key_points.length > 0 && (
        <div className="pt-1 space-y-1.5">
          <p className="text-[0.6875rem] font-semibold uppercase tracking-wider text-sky-300">
            Key Takeaways
          </p>
          <ul className="space-y-1.5 text-xs text-slate-200">
            {lesson.key_points.map((p, i) => (
              <li key={i} className="flex items-start gap-2">
                <span className="text-emerald-400 mt-0.5 shrink-0">✓</span>
                <div className="min-w-0 flex-1">
                  <RichText text={p} className="text-xs leading-relaxed text-slate-200" codeLanguage={codeLanguage} />
                </div>
              </li>
            ))}
          </ul>
        </div>
      )}
    </section>
  )
}

/** The reading a card came from, shown once the answer is revealed.
 *
 *  A verified quote is displayed as a quote; an unverified one was never
 *  stored, so what shows instead is the real passage — the guarantee being
 *  that anything presented in quotation marks genuinely appears in the source.
 */
export function ReferenceReadings({
  references,
  overlookedPhrases = [],
  matchedPhrases = [],
}: {
  references?: CardReference[]
  overlookedPhrases?: string[]
  matchedPhrases?: string[]
}) {
  const [expanded, setExpanded] = useState<Set<number>>(new Set())
  if (!references || references.length === 0) return null

  return (
    <div className="rounded-lg border border-ink-line bg-ink p-4">
      <p className="label">
        {references.length > 1 ? 'Reference readings' : 'Reference reading'}
      </p>
      <div className="mt-2 space-y-4">
        {references.map((ref, i) => {
          const showingPassage = expanded.has(i) || !ref.quote
          return (
            <div key={i}>
              <div className="mb-1.5 flex flex-wrap items-center gap-2 text-xs">
                {ref.locator && <span className="chip text-sky-300">{ref.locator}</span>}
                {ref.source_title && <span className="chip">{ref.source_title}</span>}
              </div>

              {ref.quote && !showingPassage ? (
                <blockquote className="border-l-2 border-sky-500/40 pl-3 text-sm italic leading-6 text-slate-300">
                  “
                  <HighlightedText
                    text={ref.quote}
                    overlookedPhrases={overlookedPhrases}
                    matchedPhrases={matchedPhrases}
                    className="inline"
                  />
                  ”
                </blockquote>
              ) : (
                ref.passage && (
                  <HighlightedText
                    text={ref.passage}
                    overlookedPhrases={overlookedPhrases}
                    matchedPhrases={matchedPhrases}
                    className="max-h-64 overflow-y-auto border-l-2 border-ink-line pl-3 text-sm leading-6 text-slate-300"
                  />
                )
              )}

              <div className="mt-2 flex flex-wrap gap-3 text-xs">
                {ref.quote && ref.passage && (
                  <button
                    className="text-slate-500 underline hover:text-slate-300"
                    onClick={() =>
                      setExpanded((prev) => {
                        const next = new Set(prev)
                        next.has(i) ? next.delete(i) : next.add(i)
                        return next
                      })
                    }
                  >
                    {showingPassage ? 'Show just the quote' : 'Show the full passage'}
                  </button>
                )}
                {ref.extract_id && (
                  <a
                    className="text-slate-500 underline hover:text-slate-300"
                    href={`/read/${ref.extract_id}`}
                  >
                    Open in Read
                  </a>
                )}
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}


/** Pre-Answer Primer: collapsible related content drawer allowing the student
 *  to optionally review source quotes, citations, or lesson before committing
 *  an answer to memory.
/** Collapsible card for thematic context, deck documentation, and creation source documents. */
export function ThematicDocumentationCard({ item }: { item: QueueItem }) {
  const [expanded, setExpanded] = useState(false)

  const theme = item.card_thematic_nature || item.deck_thematic_nature
  const doc = item.card_documentation || item.deck_documentation
  const sources = item.card_source_documents || item.deck_source_documents || []

  if (!theme && !doc && sources.length === 0) return null

  return (
    <div className="rounded-xl border border-sky-500/30 bg-gradient-to-r from-sky-950/20 to-ink-soft/40 p-3.5 space-y-2 text-xs backdrop-blur-xs">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="flex flex-wrap items-center gap-2">
          <span className="font-semibold text-sky-200">Thematic Context &amp; Documentation</span>
          {theme && (
            <span className="chip border-sky-400/40 text-sky-300 bg-sky-500/10 font-semibold">
              {theme}
            </span>
          )}
        </div>
        {doc && (
          <button
            type="button"
            onClick={() => setExpanded((prev) => !prev)}
            className="text-[0.6875rem] text-sky-300 hover:text-white underline cursor-pointer"
          >
            {expanded ? 'Hide Documentation' : 'View Documentation'}
          </button>
        )}
      </div>

      {sources.length > 0 && (
        <div className="flex flex-wrap items-center gap-1.5 pt-0.5">
          <span className="text-[0.6875rem] text-slate-400">Creation Documents:</span>
          {sources.map((sd: any, idx: number) => {
            let label = ''
            let quoteText = ''
            if (typeof sd === 'string') {
              try {
                const parsed = JSON.parse(sd)
                if (typeof parsed === 'object' && parsed !== null) {
                  sd = parsed
                } else {
                  label = sd
                }
              } catch {
                label = sd
              }
            }
            if (typeof sd === 'object' && sd !== null) {
              const name = sd.title || sd.name || sd.filename || 'Document'
              const locator = sd.locator ? ` (${sd.locator})` : ''
              const pages = !sd.locator && sd.pages ? ` (pp. ${sd.pages})` : ''
              label = `${name}${locator || pages}`
              quoteText = sd.quote || ''
            }
            return (
              <span
                key={idx}
                className="chip border-emerald-500/30 bg-emerald-500/10 text-emerald-300 text-[0.6875rem]"
                title={quoteText ? `Citation quote: "${quoteText}"` : undefined}
              >
                {label}
              </span>
            )
          })}
        </div>
      )}

      {expanded && doc && (
        <div className="mt-2 rounded-lg border border-ink-line/60 bg-ink/80 p-3 text-slate-300 leading-relaxed text-xs">
          <RichText text={doc} />
        </div>
      )}
    </div>
  )
}

export function PrimerDrawer({
  item,
  lesson,
  loading,
  onReady,
}: {
  item: QueueItem
  lesson: Lesson | null
  loading: boolean
  onReady: () => void
}) {
  const hasReferences = Boolean(item.references && item.references.length > 0)
  const hasLesson = Boolean(lesson && lesson.available && (lesson.socratic || lesson.body))
  const detectedLang = detectCodeLanguage(item.starter_code || item.front || '', 'javascript')

  return (
    <div className="mb-5 rounded-xl border border-sky-500/30 bg-sky-950/20 p-4 transition-all">
      <div className="mb-3 flex items-center justify-between gap-2 border-b border-sky-500/20 pb-2.5">
        <div className="flex items-center gap-2 text-xs font-semibold text-sky-300">
          <span>Socratic Primer</span>
          <span className="text-[0.6875rem] font-normal text-slate-400">Pre-recall mental model</span>
        </div>
        <button
          type="button"
          onClick={onReady}
          className="text-xs text-slate-400 underline hover:text-slate-200 cursor-pointer"
        >
          Dismiss
        </button>
      </div>

      {loading ? (
        <Spinner label="Loading primer…" />
      ) : (
        <div className="space-y-3">
          {hasLesson ? (
            <SocraticLessonPanel
              lesson={lesson!}
              codeLanguage={detectedLang}
              deckId={item.kind === 'card' ? item.deck_or_source_id : null}
              compact={true}
            />
          ) : hasReferences ? (
            <div className="space-y-2">
              <p className="text-xs font-medium text-sky-300">Citations:</p>
              <div className="max-h-56 space-y-2 overflow-y-auto pr-1">
                {item.references!.map((ref, idx) => (
                  <div key={idx} className="rounded border border-sky-500/20 bg-ink/60 p-2.5 text-xs text-slate-300">
                    <div className="mb-1 flex items-center gap-2 font-mono text-[0.625rem] text-sky-300">
                      {ref.locator && <span>[{ref.locator}]</span>}
                      {ref.source_title && <span>{ref.source_title}</span>}
                    </div>
                    {ref.quote && (
                      <blockquote className="border-l-2 border-sky-400/50 pl-2 italic text-slate-200">
                        “{ref.quote}”
                      </blockquote>
                    )}
                    {ref.passage && !ref.quote && (
                      <div className="whitespace-pre-wrap">{ref.passage}</div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          ) : (
            <div className="space-y-1 text-xs text-slate-400">
              <p>
                <strong className="text-slate-300">Deck:</strong> {item.deck_name}
              </p>
              <p className="text-slate-500">
                No external citations attached. Recall key concepts and prepare your response below.
              </p>
            </div>
          )}

          <div className="flex items-center justify-end border-t border-sky-500/20 pt-3">
            <button
              type="button"
              onClick={onReady}
              className="btn btn-primary flex items-center gap-1.5 px-3 py-1 text-xs font-semibold cursor-pointer"
            >
              <span>Answer</span>
              <span>&rarr;</span>
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
