import { useEffect, useMemo, useState } from 'react'
import { CodeEditor, type LineHintData } from './CodeEditor'
import type { DeckDocMessage, QueueItem } from '../api/types'
import { computeTokenDiff } from './AnswerComparison'
import type { LogicWarning } from '../utils/logicGuard'
import {
  computeExpectedLines,
  getFirstTargetLine,
  formatTargetLineSummary,
  findIncompleteLineNumber,
  DEFAULT_TARGET_HIGHLIGHT_COLOR,
} from '../utils/expectedCodeUtils'
import { HighlightColorPicker } from './HighlightColorPicker'
import { storage } from '../utils/storage'

export type TilePaneTab = 'solution' | 'tests' | 'reference' | 'ref_tests' | 'starter_tests'

export interface TiledEditorPaneProps {
  paneId: 'left' | 'right'
  currentTab: TilePaneTab
  onTabChange: (tab: TilePaneTab) => void
  answer: string
  onAnswerChange: (code: string) => void
  testCode: string
  onTestCodeChange: (code: string) => void
  cleanRefCode: string
  starterTestsCode: string
  cleanRefTestsCode?: string
  codeLanguage: string
  revealed: boolean
  onReveal: () => void
  onHide?: () => void
  item: QueueItem | null
  copiedRef: boolean
  onCopyRef: (code: string) => void
  copiedStarterTests: boolean
  onCopyStarterTests: (code: string) => void
  copiedRefTests?: boolean
  onCopyRefTests?: (code: string) => void
  height?: string
  onRun?: () => void
  onSubmit?: () => void
  // Socratic Line Hint props
  activeLineHint?: LineHintData | null
  lineHintLoading?: boolean
  onRequestLineHint?: (lineNumber: number, lineText: string) => void
  onDismissLineHint?: () => void
  onCursorChange?: (line: number, col: number) => void
  onGradeSolution?: () => void
  grading?: boolean
  learnMode?: boolean
  onUnlockTests?: () => void
  overlookedPhrases?: string[]
  matchedPhrases?: string[]
  // Real-time Logic Guard props
  logicGuardEnabled?: boolean
  onLogicGuardToggle?: (enabled: boolean) => void
  onLogicWarningChange?: (warning: LogicWarning | null) => void
  // Synced active AI model
  activeModel?: string | null
  onActiveModelChange?: (modelId: string) => void
  fillHeight?: boolean
  executionSummary?: string | null
  sharedQaHistory?: DeckDocMessage[]
  onSharedQaHistoryChange?: (
    updater: DeckDocMessage[] | ((prev: DeckDocMessage[]) => DeckDocMessage[]),
  ) => void
}

export function TiledEditorPane({
  paneId,
  currentTab,
  onTabChange,
  answer,
  onAnswerChange,
  testCode,
  onTestCodeChange,
  cleanRefCode,
  starterTestsCode,
  cleanRefTestsCode = '',
  codeLanguage,
  revealed,
  onReveal,
  onHide,
  item,
  copiedRef,
  onCopyRef,
  copiedStarterTests,
  onCopyStarterTests,
  copiedRefTests = false,
  onCopyRefTests,
  height = '460px',
  onRun,
  onSubmit,
  activeLineHint,
  lineHintLoading,
  onRequestLineHint,
  onDismissLineHint,
  onCursorChange,
  onGradeSolution,
  grading,
  learnMode = false,
  onUnlockTests,
  overlookedPhrases = [],
  matchedPhrases = [],
  logicGuardEnabled = true,
  onLogicGuardToggle,
  onLogicWarningChange,
  activeModel,
  onActiveModelChange,
  fillHeight = false,
  executionSummary = null,
  sharedQaHistory,
  onSharedQaHistoryChange,
}: TiledEditorPaneProps) {
  const [cursorLine, setCursorLine] = useState(1)

  const [refViewMode, setRefViewMode] = useState<'ide' | 'diff' | 'hint'>(() => {
    return (storage.get('memorization.refViewMode') as 'ide' | 'diff' | 'hint') || 'ide'
  })

  const [manualRefHintLine, setManualRefHintLine] = useState<number | null>(null)
  const [manualRefTestsHintLine, setManualRefTestsHintLine] = useState<number | null>(null)

  const handleToggleRefViewMode = (mode: 'ide' | 'diff' | 'hint') => {
    setRefViewMode(mode)
    storage.set('memorization.refViewMode', mode)
  }

  const [focusTargetCode, setFocusTargetCode] = useState<boolean>(() => {
    const saved = storage.get('memorization.focusTargetCode')
    return saved !== null ? saved === 'true' : true
  })

  const handleToggleFocusTargetCode = () => {
    setFocusTargetCode((prev) => {
      const next = !prev
      storage.set('memorization.focusTargetCode', String(next))
      return next
    })
  }

  const [targetHighlightColor, setTargetHighlightColor] = useState<string>(() => {
    return storage.get('memorization.targetHighlightColor') || DEFAULT_TARGET_HIGHLIGHT_COLOR
  })

  const handleHighlightColorChange = (newColor: string) => {
    setTargetHighlightColor(newColor)
    storage.set('memorization.targetHighlightColor', newColor)
  }

  const targetRefLines = useMemo(() => {
    return computeExpectedLines(item?.starter_code, cleanRefCode)
  }, [item?.starter_code, cleanRefCode])

  const firstTargetRefLine = useMemo(() => {
    return getFirstTargetLine(targetRefLines)
  }, [targetRefLines])

  const targetRefTestsLines = useMemo(() => {
    return computeExpectedLines(starterTestsCode, cleanRefTestsCode)
  }, [starterTestsCode, cleanRefTestsCode])

  const firstTargetRefTestsLine = useMemo(() => {
    return getFirstTargetLine(targetRefTestsLines)
  }, [targetRefTestsLines])

  const detectedIncompleteLine = useMemo(() => {
    return findIncompleteLineNumber(answer, cleanRefCode)
  }, [answer, cleanRefCode])

  const totalRefLines = useMemo(() => {
    return cleanRefCode ? cleanRefCode.split('\n').length : 1
  }, [cleanRefCode])

  const activeRefHintLine = manualRefHintLine ?? detectedIncompleteLine

  // Reset manual hint pin only when switching reference code (card), never on Solution edits/cursor moves
  useEffect(() => {
    setManualRefHintLine(null)
  }, [cleanRefCode])

  const detectedTestsIncompleteLine = useMemo(() => {
    return findIncompleteLineNumber(testCode, cleanRefTestsCode)
  }, [testCode, cleanRefTestsCode])

  const totalRefTestsLines = useMemo(() => {
    return cleanRefTestsCode ? cleanRefTestsCode.split('\n').length : 1
  }, [cleanRefTestsCode])

  const activeRefTestsHintLine = manualRefTestsHintLine ?? detectedTestsIncompleteLine

  useEffect(() => {
    setManualRefTestsHintLine(null)
  }, [cleanRefTestsCode])

  const { refSegments, stats: refDiffStats } = useMemo(() => {
    if (!cleanRefCode || !answer.trim()) {
      return { refSegments: null, stats: null }
    }
    const diff = computeTokenDiff(answer, cleanRefCode, overlookedPhrases, matchedPhrases, true)
    return { refSegments: diff.refSegments, stats: diff.stats }
  }, [answer, cleanRefCode, overlookedPhrases, matchedPhrases])

  const { refTestsSegments, stats: refTestsDiffStats } = useMemo(() => {
    if (!cleanRefTestsCode || !testCode.trim()) {
      return { refTestsSegments: null, stats: null }
    }
    const diff = computeTokenDiff(testCode, cleanRefTestsCode, [], [], true)
    return { refTestsSegments: diff.refSegments, stats: diff.stats }
  }, [cleanRefTestsCode, testCode])

  return (
    <div className={`flex flex-col min-w-0 ${fillHeight ? 'h-full flex-1 min-h-0' : 'h-full'}`}>
      {/* ── Sub-Column Header & Tab Switcher ── */}
      <div className="h-9 min-h-[36px] shrink-0 flex flex-nowrap items-center justify-between border-b border-ink-line/80 bg-[#1e1e1e]/90 px-2.5 text-xs min-w-0 gap-2 overflow-x-auto no-scrollbar">
        <div className="flex items-center gap-1.5 shrink-0">
          <div className="inline-flex rounded-md bg-[#161616] p-0.5 border border-ink-line shrink-0">
            <button
              type="button"
              onClick={() => onTabChange('solution')}
              className={`px-2 py-0.5 text-xs font-medium rounded transition flex items-center gap-1 shrink-0 whitespace-nowrap cursor-pointer ${
                currentTab === 'solution'
                  ? 'bg-sky-600/30 text-sky-200 border border-sky-500/50 shadow-sm'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
              title={`Edit implementation logic (${paneId} pane)`}
            >
              <span>Solution</span>
            </button>

            <button
              type="button"
              onClick={() => onTabChange('tests')}
              className={`px-2 py-0.5 text-xs font-medium rounded transition flex items-center gap-1 shrink-0 whitespace-nowrap cursor-pointer ${
                currentTab === 'tests'
                  ? 'bg-indigo-600/30 text-indigo-200 border border-indigo-500/50 shadow-sm'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
              title={`Write unit tests with assertions (${paneId} pane)`}
            >
              <span>Tests</span>
              {testCode.trim() && (
                <span className="w-1.5 h-1.5 rounded-full bg-indigo-400"></span>
              )}
            </button>

            <button
              type="button"
              onClick={() => onTabChange('reference')}
              className={`px-2 py-0.5 text-xs font-medium rounded transition flex items-center gap-1 shrink-0 whitespace-nowrap cursor-pointer ${
                currentTab === 'reference'
                  ? 'bg-emerald-600/30 text-emerald-200 border border-emerald-500/50 shadow-sm'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
              title={`View reference solution (${paneId} pane)`}
            >
              <span>Ref</span>
            </button>

            {Boolean(cleanRefTestsCode.trim()) && (
              <button
                type="button"
                onClick={() => onTabChange('ref_tests')}
                className={`px-2 py-0.5 text-xs font-medium rounded transition flex items-center gap-1 shrink-0 whitespace-nowrap cursor-pointer ${
                  currentTab === 'ref_tests'
                    ? 'bg-purple-600/30 text-purple-200 border border-purple-500/50 shadow-sm'
                    : 'text-slate-400 hover:text-slate-200'
                }`}
                title={`View completed reference test suite (${paneId} pane)`}
              >
                <span>Ref Tests</span>
              </button>
            )}

            {Boolean(starterTestsCode.trim()) && (
              <button
                type="button"
                onClick={() => onTabChange('starter_tests')}
                className={`px-2 py-0.5 text-xs font-medium rounded transition flex items-center gap-1 shrink-0 whitespace-nowrap cursor-pointer ${
                  currentTab === 'starter_tests'
                    ? 'bg-amber-600/30 text-amber-200 border border-amber-500/50 shadow-sm'
                    : 'text-slate-400 hover:text-slate-200'
                }`}
                title={`View original starter test suite (${paneId} pane)`}
              >
                <span>Starter</span>
              </button>
            )}
          </div>
        </div>

        {/* ── Header Extras (Reset / Copy / Complexity / Actions) ── */}
        <div className="flex items-center gap-1.5 shrink-0">
          {currentTab === 'solution' && onRequestLineHint && (
            <button
              type="button"
              onClick={() => {
                const lineList = answer.split('\n')
                const lineText = lineList[cursorLine - 1] ?? ''
                onRequestLineHint(cursorLine, lineText)
              }}
              disabled={lineHintLoading}
              className={`flex items-center gap-1 rounded px-2 py-0.5 text-xs font-medium transition cursor-pointer shrink-0 whitespace-nowrap ${
                lineHintLoading
                  ? 'bg-amber-500/20 text-amber-300 border border-amber-500/40 animate-pulse'
                  : activeLineHint
                  ? 'bg-amber-500/25 text-amber-200 border border-amber-500/50 hover:bg-amber-500/35'
                  : 'text-amber-300/90 hover:text-amber-200 hover:bg-amber-500/10 border border-amber-500/30'
              }`}
              title={`Request Socratic Hint for line ${cursorLine} (Alt+H)`}
            >
              <span>{lineHintLoading ? 'Thinking…' : 'Hint'}</span>
              <span className="text-[0.625rem] text-amber-300/90 font-mono hidden xl:inline">(Alt+H)</span>
            </button>
          )}

          {currentTab === 'solution' && onLogicGuardToggle && (
            <button
              type="button"
              onClick={() => onLogicGuardToggle(!logicGuardEnabled)}
              className={`flex items-center gap-1 rounded px-2 py-0.5 text-xs font-medium transition cursor-pointer shrink-0 whitespace-nowrap ${
                logicGuardEnabled
                  ? 'bg-rose-500/20 text-rose-300 border border-rose-500/40 hover:bg-rose-500/30'
                  : 'text-slate-500 hover:text-slate-300 hover:bg-white/5 border border-white/10'
              }`}
              title={
                logicGuardEnabled
                  ? 'Logic Guard is ON: Warns if a flawed code line is written (Click to disable)'
                  : 'Logic Guard is OFF: Click to enable real-time logic flaw detection'
              }
            >
             <span>{logicGuardEnabled ? ' Guard: ON' : ' Guard: OFF'}</span>
            </button>
          )}

          {currentTab === 'solution' && onGradeSolution && (
            <button
              type="button"
              onClick={onGradeSolution}
              disabled={grading || !answer.trim()}
              className={`flex items-center gap-1 rounded px-2 py-0.5 text-xs font-semibold transition cursor-pointer shrink-0 whitespace-nowrap ${
                grading
                  ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/40 animate-pulse'
                  : 'bg-emerald-600/25 hover:bg-emerald-600/40 text-emerald-200 border border-emerald-500/50 shadow-sm'
              }`}
              title="Grade your solution with local Qwen 2.5 Coder 7B (Alt+G)"
            >
              <span>{grading ? 'Grading…' : 'Grade'}</span>
              <span className="text-[0.625rem] text-emerald-300/70 font-mono hidden xl:inline">(Alt+G)</span>
            </button>
          )}

          {currentTab === 'solution' && item?.starter_code && (
            <button
              type="button"
              onClick={() => onAnswerChange(item.starter_code || '')}
              className="text-slate-400 hover:text-slate-200 text-xs underline cursor-pointer shrink-0 whitespace-nowrap px-1"
              title="Reset solution to original starter template"
            >
              Reset
            </button>
          )}

          {currentTab === 'tests' && (
            <button
              type="button"
              onClick={() => onTestCodeChange(starterTestsCode)}
              className="text-slate-400 hover:text-slate-200 text-xs underline cursor-pointer shrink-0 whitespace-nowrap px-1"
              title="Reset unit tests to starter assertions"
            >
              Reset
            </button>
          )}

          {currentTab === 'reference' && (
            <>
              {item?.time_complexity && (
                <span className="rounded bg-sky-500/10 px-1.5 py-0.5 text-[0.625rem] font-mono text-sky-300 border border-sky-500/30 shrink-0 whitespace-nowrap">
                  {item.time_complexity}
                </span>
              )}
              {revealed || refViewMode === 'hint' ? (
                <>
                  <div className="inline-flex rounded-md bg-[#161616] p-0.5 border border-ink-line text-[0.6875rem] shrink-0">
                    <button
                      type="button"
                      onClick={() => handleToggleRefViewMode('ide')}
                      className={`px-2 py-0.5 rounded transition cursor-pointer ${
                        refViewMode === 'ide'
                          ? 'bg-sky-600/30 text-sky-200 border border-sky-500/50 font-medium'
                          : 'text-slate-400 hover:text-slate-200'
                      }`}
                      title="Full reference solution with IDE syntax highlighting"
                    >
                      IDE
                    </button>
                    {Boolean(answer.trim()) && (
                      <button
                        type="button"
                        onClick={() => handleToggleRefViewMode('diff')}
                        className={`px-2 py-0.5 rounded transition flex items-center gap-1 cursor-pointer ${
                          refViewMode === 'diff'
                            ? 'bg-amber-600/30 text-amber-200 border border-amber-500/50 font-medium'
                            : 'text-slate-400 hover:text-slate-200'
                        }`}
                        title="Token-by-token answer comparison diff against your Solution"
                      >
                        <span>Diff</span>
                        {refDiffStats && refDiffStats.missingCount > 0 && (
                          <span className="inline-block w-1.5 h-1.5 rounded-full bg-amber-400" />
                        )}
                      </button>
                    )}
                    <button
                      type="button"
                      onClick={() => handleToggleRefViewMode(refViewMode === 'hint' ? 'ide' : 'hint')}
                      className={`px-2 py-0.5 rounded transition flex items-center gap-1 cursor-pointer ${
                        refViewMode === 'hint'
                          ? 'bg-amber-500/30 text-amber-200 border border-amber-500/60 font-medium shadow-sm'
                          : 'text-slate-400 hover:text-slate-200'
                      }`}
                      title="Hint only mode: show only the current line of code solution left incomplete in Solution tab (Click to toggle)"
                    >
                     <span> Hint</span>
                    </button>
                  </div>

                  {refViewMode === 'ide' && targetRefLines.size > 0 && (
                    <div className="flex items-center gap-1.5 shrink-0">
                      <button
                        type="button"
                        onClick={handleToggleFocusTargetCode}
                        className={`px-2 py-0.5 rounded transition flex items-center gap-1 cursor-pointer text-xs ${
                          focusTargetCode
                            ? 'bg-emerald-600/30 text-emerald-200 border border-emerald-500/50 font-medium shadow-sm'
                            : 'text-slate-400 hover:text-slate-200 border border-transparent'
                        }`}
                        title={
                          focusTargetCode
                            ? 'Focus Target Code active: boilerplate starter code is dimmed. Click to show full brightness.'
                            : 'Click to focus target code (dims boilerplate starter code)'
                        }
                      >
                       <span> Target ({formatTargetLineSummary(targetRefLines)})</span>
                      </button>

                      <HighlightColorPicker
                        color={targetHighlightColor}
                        onChange={handleHighlightColorChange}
                      />

                      {firstTargetRefLine && firstTargetRefLine > 10 && (
                        <button
                          type="button"
                          onClick={() => setManualRefHintLine(firstTargetRefLine)}
                          className="hidden sm:flex items-center gap-0.5 text-[0.6875rem] text-emerald-400 hover:text-emerald-200 hover:underline cursor-pointer font-mono"
                          title={`Jump to first line of expected code (Line ${firstTargetRefLine})`}
                        >
                          ⤓ Ln {firstTargetRefLine}
                        </button>
                      )}
                    </div>
                  )}

                  {revealed && onHide && (
                    <button
                      type="button"
                      onClick={onHide}
                      className="flex items-center gap-1 text-xs font-medium text-amber-300 hover:text-amber-100 bg-amber-500/15 hover:bg-amber-500/25 border border-amber-500/40 transition px-2 py-0.5 rounded cursor-pointer shrink-0 whitespace-nowrap shadow-sm"
                      title="Hide reference solution and return to problem solving (Alt+U)"
                    >
                     <span> Hide</span>
                    </button>
                  )}

                  {refViewMode === 'hint' && (
                    <div className="flex items-center gap-1 text-[0.6875rem] font-mono shrink-0 bg-amber-950/40 border border-amber-500/30 px-1.5 py-0.5 rounded-md text-amber-200">
                      <button
                        type="button"
                        disabled={activeRefHintLine <= 1}
                        onClick={() => setManualRefHintLine(Math.max(1, activeRefHintLine - 1))}
                        className="px-1 py-0.2 rounded hover:bg-amber-500/20 disabled:opacity-30 cursor-pointer text-amber-300"
                        title="Previous line hint"
                      >
                        ◀
                      </button>
                      <span className="text-[0.625rem] font-semibold text-amber-100 whitespace-nowrap">
                        Ln {activeRefHintLine}/{totalRefLines}
                      </span>
                      <button
                        type="button"
                        disabled={activeRefHintLine >= totalRefLines}
                        onClick={() => setManualRefHintLine(Math.min(totalRefLines, activeRefHintLine + 1))}
                        className="px-1 py-0.2 rounded hover:bg-amber-500/20 disabled:opacity-30 cursor-pointer text-amber-300"
                        title="Next line hint"
                      >
                        ▶
                      </button>
                      {manualRefHintLine !== null && manualRefHintLine !== detectedIncompleteLine && (
                        <button
                          type="button"
                          onClick={() => setManualRefHintLine(null)}
                          className="text-[0.5625rem] underline text-amber-400 hover:text-amber-200 ml-1 cursor-pointer whitespace-nowrap"
                          title={`Reset to incomplete line (${detectedIncompleteLine})`}
                        >
                          Incomplete (Ln {detectedIncompleteLine})
                        </button>
                      )}
                      {revealed && onHide && (
                        <button
                          type="button"
                          onClick={onHide}
                          className="text-[0.625rem] text-amber-300 hover:text-white bg-amber-600/30 hover:bg-amber-600/50 border border-amber-400/40 px-1.5 py-0.5 rounded cursor-pointer transition font-medium ml-1"
                          title="Lock solution and return to problem solving with line hints"
                        >
                           Unreveal & Practice
                        </button>
                      )}
                    </div>
                  )}

                  {refViewMode === 'diff' && refDiffStats && (
                    <div className="hidden sm:flex items-center gap-1.5 text-[0.625rem] shrink-0 font-mono">
                      <span className="text-emerald-300 flex items-center gap-1 bg-emerald-950/50 px-1.5 py-0.5 rounded border border-emerald-500/30">
                        <span className="inline-block w-1.5 h-1.5 rounded-full bg-emerald-400" />
                        Recalled ({refDiffStats.matchedCount}/{refDiffStats.refWordCount})
                      </span>
                      {refDiffStats.missingCount > 0 && (
                        <span className="text-amber-300 flex items-center gap-1 bg-amber-950/50 px-1.5 py-0.5 rounded border border-amber-500/30">
                          <span className="inline-block w-1.5 h-1.5 rounded-full bg-amber-400" />
                          Missing ({refDiffStats.missingCount})
                        </span>
                      )}
                    </div>
                  )}

                  <button
                    type="button"
                    onClick={() => {
                      if (refViewMode === 'hint') {
                        const lines = cleanRefCode.split('\n')
                        const hintLineText = lines[activeRefHintLine - 1] ?? ''
                        onCopyRef(hintLineText)
                      } else {
                        onCopyRef(cleanRefCode)
                      }
                    }}
                    className="flex items-center gap-1 text-xs font-medium text-slate-400 hover:text-slate-200 transition px-2 py-0.5 rounded hover:bg-[#2c2c2c] cursor-pointer shrink-0 whitespace-nowrap"
                    title={refViewMode === 'hint' ? `Copy line ${activeRefHintLine} hint` : "Copy reference solution to clipboard"}
                  >
                    <span>{copiedRef ? (refViewMode === 'hint' ? 'Copied hint' : 'Copied') : (refViewMode === 'hint' ? 'Copy hint' : 'Copy')}</span>
                  </button>
                </>
              ) : (
                <div className="flex items-center gap-1.5">
                  <button
                    type="button"
                    onClick={() => handleToggleRefViewMode('hint')}
                    className="px-2 py-0.5 rounded transition flex items-center gap-1 text-xs font-medium bg-amber-500/15 text-amber-200 border border-amber-500/40 hover:bg-amber-500/25 cursor-pointer shrink-0"
                    title="Peek only the line of code currently incomplete without revealing the full solution"
                  >
                   <span> Line Hint</span>
                  </button>
                  <span className="text-xs text-amber-400/80 font-mono shrink-0 whitespace-nowrap">Locked</span>
                </div>
              )}
            </>
          )}

          {currentTab === 'ref_tests' && (
            <>
              {revealed || learnMode || refViewMode === 'hint' ? (
                <>
                  <div className="inline-flex rounded-md bg-[#161616] p-0.5 border border-ink-line text-[0.6875rem] shrink-0">
                    <button
                      type="button"
                      onClick={() => handleToggleRefViewMode('ide')}
                      className={`px-2 py-0.5 rounded transition cursor-pointer ${
                        refViewMode === 'ide'
                          ? 'bg-sky-600/30 text-sky-200 border border-sky-500/50 font-medium'
                          : 'text-slate-400 hover:text-slate-200'
                      }`}
                      title="IDE syntax-highlighted tests format"
                    >
                      IDE
                    </button>
                    {Boolean(testCode.trim()) && (
                      <button
                        type="button"
                        onClick={() => handleToggleRefViewMode('diff')}
                        className={`px-2 py-0.5 rounded transition flex items-center gap-1 cursor-pointer ${
                          refViewMode === 'diff'
                            ? 'bg-amber-600/30 text-amber-200 border border-amber-500/50 font-medium'
                            : 'text-slate-400 hover:text-slate-200'
                        }`}
                        title="Token-by-token comparison diff against your unit tests"
                      >
                        <span>Diff</span>
                        {refTestsDiffStats && refTestsDiffStats.missingCount > 0 && (
                          <span className="inline-block w-1.5 h-1.5 rounded-full bg-amber-400" />
                        )}
                      </button>
                    )}
                    <button
                      type="button"
                      onClick={() => handleToggleRefViewMode(refViewMode === 'hint' ? 'ide' : 'hint')}
                      className={`px-2 py-0.5 rounded transition flex items-center gap-1 cursor-pointer ${
                        refViewMode === 'hint'
                          ? 'bg-amber-500/30 text-amber-200 border border-amber-500/60 font-medium shadow-sm'
                          : 'text-slate-400 hover:text-slate-200'
                      }`}
                      title="Hint only mode: show only current incomplete test line (Click to toggle)"
                    >
                     <span> Hint</span>
                    </button>
                  </div>

                  {refViewMode === 'ide' && targetRefTestsLines.size > 0 && (
                    <div className="flex items-center gap-1.5 shrink-0">
                      <button
                        type="button"
                        onClick={handleToggleFocusTargetCode}
                        className={`px-2 py-0.5 rounded transition flex items-center gap-1 cursor-pointer text-xs ${
                          focusTargetCode
                            ? 'bg-emerald-600/30 text-emerald-200 border border-emerald-500/50 font-medium shadow-sm'
                            : 'text-slate-400 hover:text-slate-200'
                        }`}
                        title={
                          focusTargetCode
                            ? 'Focus Target Tests active: boilerplate starter tests are dimmed. Click to show full brightness.'
                            : 'Click to focus target tests (dims boilerplate)'
                        }
                      >
                       <span> Target ({formatTargetLineSummary(targetRefTestsLines)})</span>
                      </button>

                      <HighlightColorPicker
                        color={targetHighlightColor}
                        onChange={handleHighlightColorChange}
                      />

                      {firstTargetRefTestsLine && firstTargetRefTestsLine > 10 && (
                        <button
                          type="button"
                          onClick={() => setManualRefTestsHintLine(firstTargetRefTestsLine)}
                          className="hidden sm:flex items-center gap-0.5 text-[0.6875rem] text-emerald-400 hover:text-emerald-200 hover:underline cursor-pointer font-mono"
                          title={`Jump to first line of expected tests (Line ${firstTargetRefTestsLine})`}
                        >
                          ⤓ Ln {firstTargetRefTestsLine}
                        </button>
                      )}
                    </div>
                  )}

                  {revealed && onHide && (
                    <button
                      type="button"
                      onClick={onHide}
                      className="flex items-center gap-1 text-xs font-medium text-amber-300 hover:text-amber-100 bg-amber-500/15 hover:bg-amber-500/25 border border-amber-500/40 transition px-2 py-0.5 rounded cursor-pointer shrink-0 whitespace-nowrap shadow-sm"
                      title="Hide reference tests and return to problem solving (Alt+U)"
                    >
                     <span> Hide</span>
                    </button>
                  )}

                  {refViewMode === 'hint' && (
                    <div className="flex items-center gap-1 text-[0.6875rem] font-mono shrink-0 bg-amber-950/40 border border-amber-500/30 px-1.5 py-0.5 rounded-md text-amber-200">
                      <button
                        type="button"
                        disabled={activeRefTestsHintLine <= 1}
                        onClick={() => setManualRefTestsHintLine(Math.max(1, activeRefTestsHintLine - 1))}
                        className="px-1 py-0.2 rounded hover:bg-amber-500/20 disabled:opacity-30 cursor-pointer text-amber-300"
                        title="Previous test line hint"
                      >
                        ◀
                      </button>
                      <span className="text-[0.625rem] font-semibold text-amber-100 whitespace-nowrap">
                        Ln {activeRefTestsHintLine}/{totalRefTestsLines}
                      </span>
                      <button
                        type="button"
                        disabled={activeRefTestsHintLine >= totalRefTestsLines}
                        onClick={() => setManualRefTestsHintLine(Math.min(totalRefTestsLines, activeRefTestsHintLine + 1))}
                        className="px-1 py-0.2 rounded hover:bg-amber-500/20 disabled:opacity-30 cursor-pointer text-amber-300"
                        title="Next test line hint"
                      >
                        ▶
                      </button>
                      {manualRefTestsHintLine !== null && manualRefTestsHintLine !== detectedTestsIncompleteLine && (
                        <button
                          type="button"
                          onClick={() => setManualRefTestsHintLine(null)}
                          className="text-[0.5625rem] underline text-amber-400 hover:text-amber-200 ml-1 cursor-pointer whitespace-nowrap"
                          title={`Reset to incomplete test line (${detectedTestsIncompleteLine})`}
                        >
                          Incomplete (Ln {detectedTestsIncompleteLine})
                        </button>
                      )}
                    </div>
                  )}

                  <button
                    type="button"
                    onClick={() => {
                      if (refViewMode === 'hint') {
                        const lines = (cleanRefTestsCode || '').split('\n')
                        const hintLineText = lines[activeRefTestsHintLine - 1] ?? ''
                        onCopyRefTests?.(hintLineText)
                      } else {
                        onCopyRefTests?.(cleanRefTestsCode || '')
                      }
                    }}
                    className="flex items-center gap-1 text-xs font-medium text-slate-400 hover:text-slate-200 transition px-2 py-0.5 rounded hover:bg-[#2c2c2c] cursor-pointer shrink-0 whitespace-nowrap"
                    title={refViewMode === 'hint' ? `Copy line ${activeRefTestsHintLine} test hint` : "Copy completed reference tests to clipboard"}
                  >
                    <span>{copiedRefTests ? (refViewMode === 'hint' ? 'Copied hint' : 'Copied') : (refViewMode === 'hint' ? 'Copy hint' : 'Copy')}</span>
                  </button>
                  <button
                    type="button"
                    onClick={() => onTestCodeChange(cleanRefTestsCode || '')}
                    className="text-purple-300 hover:text-purple-200 hover:underline text-xs cursor-pointer shrink-0 whitespace-nowrap"
                    title="Load completed reference tests into editable unit tests"
                  >
                    Load to tests
                  </button>
                </>
              ) : (
                <div className="flex items-center gap-1.5">
                  <button
                    type="button"
                    onClick={() => handleToggleRefViewMode('hint')}
                    className="px-2 py-0.5 rounded transition flex items-center gap-1 text-xs font-medium bg-amber-500/15 text-amber-200 border border-amber-500/40 hover:bg-amber-500/25 cursor-pointer shrink-0"
                    title="Peek only the test line currently incomplete"
                  >
                   <span> Test Hint</span>
                  </button>
                  <button
                    type="button"
                    onClick={onUnlockTests || onReveal}
                    className="text-xs text-purple-400/90 hover:text-purple-300 underline font-mono shrink-0 whitespace-nowrap cursor-pointer"
                    title="Unlock and view completed test suite"
                  >
                    Unlock Tests
                  </button>
                </div>
              )}
            </>
          )}

          {currentTab === 'starter_tests' && (
            <>
              <button
                type="button"
                onClick={() => onCopyStarterTests(starterTestsCode)}
                className="flex items-center gap-1 text-xs font-medium text-slate-400 hover:text-slate-200 transition px-2 py-0.5 rounded hover:bg-[#2c2c2c] cursor-pointer shrink-0 whitespace-nowrap"
                title="Copy starter tests to clipboard"
              >
                <span>{copiedStarterTests ? 'Copied' : 'Copy'}</span>
              </button>
              <button
                type="button"
                onClick={() => onTestCodeChange(starterTestsCode)}
                className="text-slate-400 hover:text-slate-200 text-xs underline cursor-pointer shrink-0 whitespace-nowrap"
                title="Load starter tests into editable unit tests"
              >
                Load to tests
              </button>
            </>
          )}
        </div>
      </div>

      {/* ── Sub-Column Editor Body ── */}
      <div className={fillHeight ? 'flex-1 min-h-0 flex flex-col overflow-hidden' : 'flex flex-col'}>
        {currentTab === 'solution' && (
          <CodeEditor
            code={answer}
            onChange={onAnswerChange}
            language={codeLanguage}
            height={height}
            fillHeight={fillHeight}
            compactFooter={true}
            hideHeader={true}
            borderless={true}
            onRun={onRun}
            onSubmit={onSubmit}
            placeholder="// Write your solution here..."
            context={item?.front || item?.deck_name}
            deckId={item?.kind === 'card' ? item.deck_or_source_id : null}
            cardId={item?.id ?? null}
            userCode={answer}
            userTestCode={testCode}
            executionSummary={executionSummary}
            revealed={revealed}
            sharedQaHistory={sharedQaHistory}
            onSharedQaHistoryChange={onSharedQaHistoryChange}
            activeModel={activeModel}
            onActiveModelChange={onActiveModelChange}
            activeLineHint={activeLineHint}
            lineHintLoading={lineHintLoading}
            onRequestLineHint={onRequestLineHint}
            onDismissLineHint={onDismissLineHint}
            onCursorChange={(l, c) => {
              setCursorLine(l)
              onCursorChange?.(l, c)
            }}
            onGradeSolution={onGradeSolution}
            grading={grading}
            cleanRefCode={cleanRefCode}
            logicGuardEnabled={logicGuardEnabled}
            onLogicGuardToggle={onLogicGuardToggle}
            onLogicWarningChange={onLogicWarningChange}
          />
        )}

        {currentTab === 'tests' && (
          <CodeEditor
            code={testCode}
            onChange={onTestCodeChange}
            language={codeLanguage}
            height={height}
            fillHeight={fillHeight}
            compactFooter={true}
            hideHeader={true}
            borderless={true}
            onRun={onRun}
            onSubmit={onSubmit}
            context={item?.front || item?.deck_name}
            deckId={item?.kind === 'card' ? item.deck_or_source_id : null}
            cardId={item?.id ?? null}
            userCode={answer}
            userTestCode={testCode}
            executionSummary={executionSummary}
            revealed={revealed}
            sharedQaHistory={sharedQaHistory}
            onSharedQaHistoryChange={onSharedQaHistoryChange}
            activeModel={activeModel}
            onActiveModelChange={onActiveModelChange}
            placeholder="// Write your unit tests here..."
          />
        )}

        {currentTab === 'reference' && (
          revealed || refViewMode === 'hint' ? (
            <CodeEditor
              code={cleanRefCode}
              onChange={() => {}}
              language={codeLanguage}
              readOnly={true}
              height={height}
              fillHeight={fillHeight}
              compactFooter={true}
              hideHeader={true}
              borderless={true}
              placeholder="// Reference solution"
              context={item?.front || item?.deck_name}
              deckId={item?.kind === 'card' ? item.deck_or_source_id : null}
              cardId={item?.id ?? null}
              userCode={answer}
              userTestCode={testCode}
              executionSummary={executionSummary}
              revealed={revealed}
              sharedQaHistory={sharedQaHistory}
              onSharedQaHistoryChange={onSharedQaHistoryChange}
              activeModel={activeModel}
              onActiveModelChange={onActiveModelChange}
              diffSegments={refViewMode === 'diff' ? refSegments : null}
              diffStats={refViewMode === 'diff' ? refDiffStats : null}
              hintOnly={refViewMode === 'hint'}
              hintOnlyLine={activeRefHintLine}
              onHintOnlyLineChange={setManualRefHintLine}
              targetLineNumbers={targetRefLines}
              focusTargetCode={focusTargetCode}
              targetHighlightColor={targetHighlightColor}
              initialScrollLine={firstTargetRefLine ?? undefined}
            />
          ) : (
            <div
              className={`flex flex-col items-center justify-center p-6 text-center bg-[#181818] text-slate-400 space-y-3 ${
                fillHeight ? 'flex-1 min-h-[180px]' : ''
              }`}
              style={fillHeight ? undefined : { height }}
            >
              <div className="w-12 h-12 rounded-2xl bg-sky-500/10 border border-sky-500/20 flex items-center justify-center text-sky-400 shadow-inner font-mono text-sm font-bold">
                [Locked]
              </div>
              <div className="space-y-1">
                <h4 className="text-sm font-semibold text-slate-200">Reference Solution Hidden</h4>
                <p className="text-xs text-slate-400 max-w-xs leading-relaxed">
                  Commit your implementation first, or reveal now to study and compare alongside your code.
                </p>
              </div>
              <div className="flex items-center gap-2 mt-2">
                <button
                  type="button"
                  onClick={onReveal}
                  className="btn btn-secondary text-xs flex items-center gap-1.5 px-3 py-1.5 cursor-pointer"
                >
                  <span>Reveal Reference Solution</span>
                </button>
                <button
                  type="button"
                  onClick={() => handleToggleRefViewMode('hint')}
                  className="px-3 py-1.5 rounded-lg border border-amber-500/40 bg-amber-500/15 hover:bg-amber-500/25 text-amber-200 text-xs font-semibold transition cursor-pointer flex items-center gap-1"
                  title="Peek only the line of code currently incomplete without revealing the full solution"
                >
                 <span> Peek Line Hint Only</span>
                </button>
              </div>
            </div>
          )
        )}

        {currentTab === 'ref_tests' && (
          revealed || learnMode || refViewMode === 'hint' ? (
            <CodeEditor
              code={cleanRefTestsCode || ''}
              onChange={() => {}}
              language={codeLanguage}
              readOnly={true}
              height={height}
              fillHeight={fillHeight}
              compactFooter={true}
              hideHeader={true}
              borderless={true}
              placeholder="// Completed reference test suite"
              context={item?.front || item?.deck_name}
              deckId={item?.kind === 'card' ? item.deck_or_source_id : null}
              cardId={item?.id ?? null}
              userCode={answer}
              userTestCode={testCode}
              executionSummary={executionSummary}
              revealed={revealed}
              sharedQaHistory={sharedQaHistory}
              onSharedQaHistoryChange={onSharedQaHistoryChange}
              activeModel={activeModel}
              onActiveModelChange={onActiveModelChange}
              diffSegments={refViewMode === 'diff' ? refTestsSegments : null}
              diffStats={refViewMode === 'diff' ? refTestsDiffStats : null}
              hintOnly={refViewMode === 'hint'}
              hintOnlyLine={activeRefTestsHintLine}
              onHintOnlyLineChange={setManualRefTestsHintLine}
              targetLineNumbers={targetRefTestsLines}
              focusTargetCode={focusTargetCode}
              targetHighlightColor={targetHighlightColor}
              initialScrollLine={firstTargetRefTestsLine ?? undefined}
            />
          ) : (
            <div
              className={`flex flex-col items-center justify-center p-6 text-center bg-[#181818] text-slate-400 space-y-3 ${
                fillHeight ? 'flex-1 min-h-[180px]' : ''
              }`}
              style={fillHeight ? undefined : { height }}
            >
              <div className="w-12 h-12 rounded-2xl bg-purple-500/10 border border-purple-500/20 flex items-center justify-center text-purple-400 shadow-inner font-mono text-sm font-bold">
                [Locked]
              </div>
              <div className="space-y-1">
                <h4 className="text-sm font-semibold text-slate-200">Completed Test Suite Hidden</h4>
                <p className="text-xs text-slate-400 max-w-xs leading-relaxed">
                  Completed test solutions are hidden until revealed. Commit your implementation and tests or reveal below to view.
                </p>
              </div>
              <div className="flex items-center gap-2 mt-2">
                <button
                  type="button"
                  onClick={onUnlockTests || onReveal}
                  className="btn btn-secondary text-xs flex items-center gap-1.5 px-3 py-1.5 cursor-pointer"
                >
                  <span>View Reference Tests</span>
                </button>
                <button
                  type="button"
                  onClick={() => handleToggleRefViewMode('hint')}
                  className="px-3 py-1.5 rounded-lg border border-amber-500/40 bg-amber-500/15 hover:bg-amber-500/25 text-amber-200 text-xs font-semibold transition cursor-pointer flex items-center gap-1"
                  title="Peek only the test line currently incomplete"
                >
                 <span> Peek Line Hint Only</span>
                </button>
              </div>
            </div>
          )
        )}

        {currentTab === 'starter_tests' && (
          <CodeEditor
            code={starterTestsCode}
            onChange={() => {}}
            language={codeLanguage}
            readOnly={true}
            height={height}
            fillHeight={fillHeight}
            compactFooter={true}
            hideHeader={true}
            borderless={true}
            context={item?.front || item?.deck_name}
            deckId={item?.kind === 'card' ? item.deck_or_source_id : null}
            cardId={item?.id ?? null}
            userCode={answer}
            userTestCode={testCode}
            executionSummary={executionSummary}
            revealed={revealed}
            sharedQaHistory={sharedQaHistory}
            onSharedQaHistoryChange={onSharedQaHistoryChange}
            activeModel={activeModel}
            onActiveModelChange={onActiveModelChange}
            placeholder="// Starter test suite"
          />
        )}
      </div>
    </div>
  )
}
export default TiledEditorPane
