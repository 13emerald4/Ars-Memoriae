import { useState } from 'react'
import { CodeEditor, type LineHintData } from './CodeEditor'
import type { QueueItem } from '../api/types'

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
}: TiledEditorPaneProps) {
  const [cursorLine, setCursorLine] = useState(1)

  return (
    <div className="flex flex-col min-w-0 h-full">
      {/* ── Sub-Column Header & Tab Switcher ── */}
      <div className="flex items-center justify-between border-b border-ink-line/80 bg-[#1e1e1e]/90 px-3 py-1.5 text-xs">
        <div className="flex items-center gap-2">
          <div className="inline-flex rounded-md bg-[#161616] p-0.5 border border-ink-line">
            <button
              type="button"
              onClick={() => onTabChange('solution')}
              className={`px-2 py-0.5 text-xs font-medium rounded transition flex items-center gap-1.5 cursor-pointer ${
                currentTab === 'solution'
                  ? 'bg-sky-600/30 text-sky-200 border border-sky-500/50 shadow-sm'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
              title={`Edit implementation logic (${paneId} pane)`}
            >
              <span>💻</span>
              <span>Solution</span>
            </button>

            <button
              type="button"
              onClick={() => onTabChange('tests')}
              className={`px-2 py-0.5 text-xs font-medium rounded transition flex items-center gap-1.5 cursor-pointer ${
                currentTab === 'tests'
                  ? 'bg-indigo-600/30 text-indigo-200 border border-indigo-500/50 shadow-sm'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
              title={`Write unit tests with assertions (${paneId} pane)`}
            >
              <span>🧪</span>
              <span>Unit Tests</span>
              {testCode.trim() && (
                <span className="w-1.5 h-1.5 rounded-full bg-indigo-400"></span>
              )}
            </button>

            <button
              type="button"
              onClick={() => onTabChange('reference')}
              className={`px-2 py-0.5 text-xs font-medium rounded transition flex items-center gap-1.5 cursor-pointer ${
                currentTab === 'reference'
                  ? 'bg-emerald-600/30 text-emerald-200 border border-emerald-500/50 shadow-sm'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
              title={`View reference solution (${paneId} pane)`}
            >
              <span>📖</span>
              <span>Ref Solution</span>
            </button>

            {Boolean(cleanRefTestsCode.trim()) && (
              <button
                type="button"
                onClick={() => onTabChange('ref_tests')}
                className={`px-2 py-0.5 text-xs font-medium rounded transition flex items-center gap-1.5 cursor-pointer ${
                  currentTab === 'ref_tests'
                    ? 'bg-purple-600/30 text-purple-200 border border-purple-500/50 shadow-sm'
                    : 'text-slate-400 hover:text-slate-200'
                }`}
                title={`View completed reference test suite (${paneId} pane)`}
              >
                <span>🧪</span>
                <span>Ref Tests</span>
              </button>
            )}

            {Boolean(starterTestsCode.trim()) && (
              <button
                type="button"
                onClick={() => onTabChange('starter_tests')}
                className={`px-2 py-0.5 text-xs font-medium rounded transition flex items-center gap-1.5 cursor-pointer ${
                  currentTab === 'starter_tests'
                    ? 'bg-amber-600/30 text-amber-200 border border-amber-500/50 shadow-sm'
                    : 'text-slate-400 hover:text-slate-200'
                }`}
                title={`View original starter test suite (${paneId} pane)`}
              >
                <span>📋</span>
                <span>Starter Tests</span>
              </button>
            )}
          </div>
        </div>

        {/* ── Header Extras (Reset / Copy / Complexity / Lock) ── */}
        <div className="flex items-center gap-2">
          {currentTab === 'solution' && onRequestLineHint && (
            <button
              type="button"
              onClick={() => {
                const lineList = answer.split('\n')
                const lineText = lineList[cursorLine - 1] ?? ''
                onRequestLineHint(cursorLine, lineText)
              }}
              disabled={lineHintLoading}
              className={`flex items-center gap-1 rounded px-2 py-0.5 text-[11px] font-medium transition cursor-pointer ${
                lineHintLoading
                  ? 'bg-amber-500/20 text-amber-300 border border-amber-500/40 animate-pulse'
                  : activeLineHint
                  ? 'bg-amber-500/25 text-amber-200 border border-amber-500/50 hover:bg-amber-500/35'
                  : 'text-amber-300/90 hover:text-amber-200 hover:bg-amber-500/10 border border-amber-500/30'
              }`}
              title={`Request Socratic Hint for line ${cursorLine} (Alt+H)`}
            >
              <span>💡</span>
              <span>{lineHintLoading ? 'Thinking…' : `Line ${cursorLine} Hint`}</span>
              <span className="text-[10px] text-amber-400/60 font-mono hidden md:inline">(Alt+H)</span>
            </button>
          )}

          {currentTab === 'solution' && onGradeSolution && (
            <button
              type="button"
              onClick={onGradeSolution}
              disabled={grading || !answer.trim()}
              className={`flex items-center gap-1 rounded px-2.5 py-0.5 text-[11px] font-semibold transition cursor-pointer ${
                grading
                  ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/40 animate-pulse'
                  : 'bg-emerald-600/25 hover:bg-emerald-600/40 text-emerald-200 border border-emerald-500/50 shadow-sm'
              }`}
              title="Grade your solution with local Qwen 2.5 Coder 7B (Alt+G)"
            >
              <span>⚡</span>
              <span>{grading ? 'Grading…' : 'Grade My Solution'}</span>
              <span className="text-[10px] text-emerald-300/70 font-mono hidden md:inline">(Alt+G)</span>
            </button>
          )}

          {currentTab === 'solution' && item?.starter_code && (
            <button
              type="button"
              onClick={() => onAnswerChange(item.starter_code || '')}
              className="text-slate-400 hover:text-slate-200 text-[11px] underline cursor-pointer"
              title="Reset solution to original starter template"
            >
              Reset
            </button>
          )}

          {currentTab === 'tests' && (
            <button
              type="button"
              onClick={() => onTestCodeChange(starterTestsCode)}
              className="text-slate-400 hover:text-slate-200 text-[11px] underline cursor-pointer"
              title="Reset unit tests to starter assertions"
            >
              Reset
            </button>
          )}

          {currentTab === 'reference' && (
            <>
              {item?.time_complexity && (
                <span className="rounded bg-sky-500/10 px-1.5 py-0.5 text-[10px] font-mono text-sky-300 border border-sky-500/30">
                  {item.time_complexity}
                </span>
              )}
              {revealed ? (
                <button
                  type="button"
                  onClick={() => onCopyRef(cleanRefCode)}
                  className="flex items-center gap-1 text-[11px] font-medium text-slate-400 hover:text-slate-200 transition px-2 py-0.5 rounded hover:bg-[#2c2c2c] cursor-pointer"
                  title="Copy reference solution to clipboard"
                >
                  <span>{copiedRef ? '✓ Copied' : '📋 Copy'}</span>
                </button>
              ) : (
                <span className="text-[11px] text-amber-400/80 font-mono">🔒 Locked</span>
              )}
            </>
          )}

          {currentTab === 'ref_tests' && (
            <>
              {revealed ? (
                <>
                  <button
                    type="button"
                    onClick={() => onCopyRefTests?.(cleanRefTestsCode || '')}
                    className="flex items-center gap-1 text-[11px] font-medium text-slate-400 hover:text-slate-200 transition px-2 py-0.5 rounded hover:bg-[#2c2c2c] cursor-pointer"
                    title="Copy completed reference tests to clipboard"
                  >
                    <span>{copiedRefTests ? '✓ Copied' : '📋 Copy'}</span>
                  </button>
                  <button
                    type="button"
                    onClick={() => onTestCodeChange(cleanRefTestsCode || '')}
                    className="text-purple-300 hover:text-purple-200 hover:underline text-[11px] cursor-pointer"
                    title="Load completed reference tests into editable unit tests"
                  >
                    Load to tests
                  </button>
                </>
              ) : (
                <span className="text-[11px] text-purple-400/80 font-mono">🔒 Locked</span>
              )}
            </>
          )}

          {currentTab === 'starter_tests' && (
            <>
              <button
                type="button"
                onClick={() => onCopyStarterTests(starterTestsCode)}
                className="flex items-center gap-1 text-[11px] font-medium text-slate-400 hover:text-slate-200 transition px-2 py-0.5 rounded hover:bg-[#2c2c2c] cursor-pointer"
                title="Copy starter tests to clipboard"
              >
                <span>{copiedStarterTests ? '✓ Copied' : '📋 Copy'}</span>
              </button>
              <button
                type="button"
                onClick={() => onTestCodeChange(starterTestsCode)}
                className="text-slate-400 hover:text-slate-200 text-[11px] underline cursor-pointer"
                title="Load starter tests into editable unit tests"
              >
                Load to tests
              </button>
            </>
          )}
        </div>
      </div>

      {/* ── Sub-Column Editor Body ── */}
      {currentTab === 'solution' && (
        <CodeEditor
          code={answer}
          onChange={onAnswerChange}
          language={codeLanguage}
          height={height}
          hideHeader={true}
          borderless={true}
          onRun={onRun}
          onSubmit={onSubmit}
          placeholder="// Write your solution here..."
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
        />
      )}

      {currentTab === 'tests' && (
        <CodeEditor
          code={testCode}
          onChange={onTestCodeChange}
          language={codeLanguage}
          height={height}
          hideHeader={true}
          borderless={true}
          onRun={onRun}
          onSubmit={onSubmit}
          placeholder="// Write your unit tests here..."
        />
      )}

      {currentTab === 'reference' && (
        revealed ? (
          <CodeEditor
            code={cleanRefCode}
            onChange={() => {}}
            language={codeLanguage}
            readOnly={true}
            height={height}
            hideHeader={true}
            borderless={true}
            placeholder="// Reference solution"
          />
        ) : (
          <div
            className="flex flex-col items-center justify-center p-6 text-center bg-[#181818] text-slate-400 space-y-3"
            style={{ height }}
          >
            <div className="w-12 h-12 rounded-2xl bg-sky-500/10 border border-sky-500/20 flex items-center justify-center text-xl text-sky-400 shadow-inner">
              🔒
            </div>
            <div className="space-y-1">
              <h4 className="text-sm font-semibold text-slate-200">Reference Solution Hidden</h4>
              <p className="text-xs text-slate-400 max-w-xs leading-relaxed">
                Commit your implementation first, or reveal now to study and compare alongside your code.
              </p>
            </div>
            <button
              type="button"
              onClick={onReveal}
              className="btn btn-secondary text-xs flex items-center gap-1.5 px-3 py-1.5 mt-2 cursor-pointer"
            >
              <span>👁 Reveal Reference Solution</span>
            </button>
          </div>
        )
      )}

      {currentTab === 'ref_tests' && (
        revealed ? (
          <CodeEditor
            code={cleanRefTestsCode || ''}
            onChange={() => {}}
            language={codeLanguage}
            readOnly={true}
            height={height}
            hideHeader={true}
            borderless={true}
            placeholder="// Completed reference test suite"
          />
        ) : (
          <div
            className="flex flex-col items-center justify-center p-6 text-center bg-[#181818] text-slate-400 space-y-3"
            style={{ height }}
          >
            <div className="w-12 h-12 rounded-2xl bg-purple-500/10 border border-purple-500/20 flex items-center justify-center text-xl text-purple-400 shadow-inner">
              🔒
            </div>
            <div className="space-y-1">
              <h4 className="text-sm font-semibold text-slate-200">Completed Test Suite Hidden</h4>
              <p className="text-xs text-slate-400 max-w-xs leading-relaxed">
                Completed test solutions are hidden until revealed. Commit your implementation and tests or reveal below to view.
              </p>
            </div>
            <button
              type="button"
              onClick={onReveal}
              className="btn btn-secondary text-xs flex items-center gap-1.5 px-3 py-1.5 mt-2 cursor-pointer"
            >
              <span>👁 Reveal Reference Tests</span>
            </button>
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
          hideHeader={true}
          borderless={true}
          placeholder="// Starter test suite"
        />
      )}
    </div>
  )
}
export default TiledEditorPane
