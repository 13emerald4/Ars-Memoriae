import React, { useCallback, useMemo, useRef, useState } from 'react'

export interface LineHintData {
  hint: string
  line_number?: number
  lineNumber?: number
  current_line_text?: string
  currentLineText?: string
  target_concept?: string | null
  targetConcept?: string | null
}

export interface CodeEditorProps {
  code: string
  onChange: (code: string) => void
  language?: string
  onLanguageChange?: (lang: string) => void
  readOnly?: boolean
  height?: string
  onRun?: () => void
  onSubmit?: () => void
  onReset?: () => void
  running?: boolean
  submitting?: boolean
  hideHeader?: boolean
  hideFooter?: boolean
  borderless?: boolean
  placeholder?: string
  // Socratic Line Hint props
  activeLineHint?: LineHintData | null
  lineHintLoading?: boolean
  onRequestLineHint?: (lineNumber: number, lineText: string) => void
  onDismissLineHint?: () => void
  onCursorChange?: (line: number, col: number) => void
  onGradeSolution?: () => void
  grading?: boolean
}

const SUPPORTED_LANGUAGES = [
  { id: 'python', label: 'Python3' },
  { id: 'typescript', label: 'TypeScript' },
  { id: 'javascript', label: 'JavaScript' },
  { id: 'cpp', label: 'C++' },
  { id: 'java', label: 'Java' },
  { id: 'rust', label: 'Rust' },
  { id: 'go', label: 'Go' },
]

const CONTROL_KEYWORDS = new Set([
  'for',
  'in',
  'if',
  'else',
  'elif',
  'while',
  'return',
  'break',
  'continue',
  'yield',
  'pass',
  'try',
  'except',
  'finally',
  'raise',
  'with',
  'as',
  'import',
  'from',
  'assert',
  'is',
  'not',
  'and',
  'or',
  'switch',
  'case',
  'default',
])

const DEFINITION_KEYWORDS = new Set([
  'class',
  'def',
  'async',
  'await',
  'lambda',
  'function',
  'const',
  'let',
  'var',
  'export',
  'interface',
  'type',
])

const BUILTIN_TYPES = new Set([
  'int',
  'str',
  'float',
  'bool',
  'list',
  'dict',
  'set',
  'tuple',
  'List',
  'Dict',
  'Set',
  'Tuple',
  'Optional',
  'Any',
  'Union',
  'TreeNode',
  'ListNode',
  'Solution',
  'number',
  'string',
  'boolean',
  'void',
  'Array',
  'Map',
])

const BUILTIN_FUNCS = new Set([
  'enumerate',
  'range',
  'len',
  'print',
  'min',
  'max',
  'sum',
  'abs',
  'zip',
  'map',
  'filter',
  'sorted',
  'reversed',
  'all',
  'any',
  'isinstance',
  'iter',
  'next',
])

function escapeHtml(str: string): string {
  return str.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
}

function highlightLeetCode(code: string): string {
  const regex =
    /(#[^\n]*|\/\/[^\n]*|"""[\s\S]*?"""|'''[\s\S]*?'''|"(?:\\.|[^"\\])*"|'(?:\\.|[^'\\])*'|\b\d+(?:\.\d+)?\b|\b[a-zA-Z_]\w*\b|->|==|!=|<=|>=|[()\[\]{}:,.<>=+\-*/%&|^~!]|\s+|[^\s\w]+)/g

  const tokens: string[] = []
  let m: RegExpExecArray | null
  while ((m = regex.exec(code)) !== null) {
    tokens.push(m[0])
  }

  let html = ''
  for (let idx = 0; idx < tokens.length; idx++) {
    const token = tokens[idx]
    if (/^\s+$/.test(token)) {
      html += escapeHtml(token)
      continue
    }

    // Check next non-whitespace token
    let nextToken = ''
    for (let j = idx + 1; j < tokens.length; j++) {
      if (!/^\s+$/.test(tokens[j])) {
        nextToken = tokens[j]
        break
      }
    }
    // Check prev non-whitespace token
    let prevToken = ''
    for (let j = idx - 1; j >= 0; j--) {
      if (!/^\s+$/.test(tokens[j])) {
        prevToken = tokens[j]
        break
      }
    }

    let color = '#eff1f6'
    if (token.startsWith('#') || token.startsWith('//')) {
      color = '#6a9955' // Comments green
    } else if (token.startsWith('"') || token.startsWith("'")) {
      color = '#ce9178' // Strings orange
    } else if (/^\d+/.test(token)) {
      color = '#b5cea8' // Numbers light green
    } else if (CONTROL_KEYWORDS.has(token)) {
      color = '#c586c0' // LeetCode control flow purple (for, in, if, return)
    } else if (DEFINITION_KEYWORDS.has(token)) {
      color = '#569cd6' // LeetCode definition blue (class, def)
    } else if (BUILTIN_TYPES.has(token) || prevToken === 'class') {
      color = '#4ec9b0' // LeetCode type teal (List, int, Solution)
    } else if (
      BUILTIN_FUNCS.has(token) ||
      prevToken === 'def' ||
      (nextToken === '(' && /^[a-zA-Z_]\w*$/.test(token))
    ) {
      color = '#dcdcaa' // LeetCode function yellow (twoSum, enumerate)
    } else if (token === 'self') {
      color = '#9cdcfe' // Self parameter light blue
    } else if (/^[a-zA-Z_]\w*$/.test(token)) {
      color = '#9cdcfe' // Variables light blue (seen, nums, target, complement, i)
    } else if (token === '(' || token === ')') {
      color = '#ffd700' // Gold brackets
    } else if (token === '[' || token === ']') {
      color = '#da70d6' // Orchid brackets
    } else if (token === '{' || token === '}') {
      color = '#179fff' // Sky braces
    } else {
      color = '#d4d4d4' // Operators and punctuation (:, =, ->, etc.)
    }

    html += `<span style="color: ${color}">${escapeHtml(token)}</span>`
  }

  return html
}

export function CodeEditor({
  code,
  onChange,
  language = 'python',
  onLanguageChange,
  readOnly = false,
  height = '420px',
  onRun,
  onSubmit,
  onReset,
  running = false,
  submitting = false,
  hideHeader = false,
  hideFooter = false,
  borderless = false,
  placeholder = '# Write your solution here...',
  activeLineHint,
  lineHintLoading = false,
  onRequestLineHint,
  onDismissLineHint,
  onCursorChange,
  onGradeSolution,
  grading = false,
}: CodeEditorProps) {
  const textareaRef = useRef<HTMLTextAreaElement | null>(null)
  const highlightRef = useRef<HTMLPreElement | null>(null)
  const lineNumbersRef = useRef<HTMLDivElement | null>(null)

  const [cursorLine, setCursorLine] = useState(1)
  const [cursorCol, setCursorCol] = useState(1)

  const lines = code.split('\n')
  const lineCount = Math.max(lines.length, 1)

  const updateCursorPosition = useCallback(() => {
    const textarea = textareaRef.current
    if (!textarea) return
    const pos = textarea.selectionStart ?? 0
    const textBefore = code.slice(0, pos)
    const lineList = textBefore.split('\n')
    const currentLineNumber = lineList.length
    const currentColNumber = (lineList[lineList.length - 1]?.length ?? 0) + 1

    setCursorLine(currentLineNumber)
    setCursorCol(currentColNumber)
    if (onCursorChange) {
      onCursorChange(currentLineNumber, currentColNumber)
    }
  }, [code, onCursorChange])

  const triggerLineHint = useCallback(
    (targetLine?: number) => {
      if (!onRequestLineHint) return
      const targetLineNum = targetLine ?? cursorLine
      const lineList = code.split('\n')
      const lineText = lineList[targetLineNum - 1] ?? ''
      onRequestLineHint(targetLineNum, lineText)
    },
    [code, cursorLine, onRequestLineHint]
  )

  const highlightedHtml = useMemo(() => {
    return highlightLeetCode(code)
  }, [code])

  // Synchronize scrolling between textarea, line numbers, and syntax-highlight overlay
  const handleScroll = useCallback(() => {
    if (textareaRef.current) {
      const { scrollTop, scrollLeft } = textareaRef.current
      if (lineNumbersRef.current) {
        lineNumbersRef.current.scrollTop = scrollTop
      }
      if (highlightRef.current) {
        highlightRef.current.scrollTop = scrollTop
        highlightRef.current.scrollLeft = scrollLeft
      }
    }
  }, [])

  // Handle Tab, Shift+Tab, Enter (auto-indent), auto-closing brackets, and shortcuts
  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    // Escape to dismiss Socratic line hint callout
    if (e.key === 'Escape' && (activeLineHint || lineHintLoading)) {
      e.preventDefault()
      e.stopPropagation()
      onDismissLineHint?.()
      return
    }

    // Alt + H Line Hint Shortcut
    if (e.altKey && (e.key === 'h' || e.key === 'H')) {
      e.preventDefault()
      e.stopPropagation()
      triggerLineHint()
      return
    }

    // Alt + G Grade My Solution Shortcut
    if (e.altKey && (e.key === 'g' || e.key === 'G')) {
      e.preventDefault()
      e.stopPropagation()
      if (onGradeSolution) {
        onGradeSolution()
      } else if (onSubmit) {
        onSubmit()
      }
      return
    }

    if (readOnly) return

    // Run / Submit Shortcuts
    if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
      e.preventDefault()
      if (e.shiftKey && onSubmit) {
        onSubmit()
      } else if (onRun) {
        onRun()
      }
      return
    }

    const textarea = textareaRef.current
    if (!textarea) return

    const { selectionStart, selectionEnd, value } = textarea

    // 1. Tab Key handling (4 spaces indentation)
    if (e.key === 'Tab') {
      e.preventDefault()
      const tabSpaces = '    '

      if (e.shiftKey) {
        const lineStart = value.lastIndexOf('\n', selectionStart - 1) + 1
        if (value.startsWith(tabSpaces, lineStart)) {
          const newValue = value.slice(0, lineStart) + value.slice(lineStart + 4)
          onChange(newValue)
          setTimeout(() => {
            textarea.selectionStart = Math.max(lineStart, selectionStart - 4)
            textarea.selectionEnd = Math.max(lineStart, selectionEnd - 4)
          }, 0)
        }
      } else {
        const newValue = value.slice(0, selectionStart) + tabSpaces + value.slice(selectionEnd)
        onChange(newValue)
        setTimeout(() => {
          textarea.selectionStart = textarea.selectionEnd = selectionStart + 4
        }, 0)
      }
      return
    }

    // 2. Auto-Indent on Enter
    if (e.key === 'Enter') {
      e.preventDefault()
      const lineStart = value.lastIndexOf('\n', selectionStart - 1) + 1
      const currentLine = value.slice(lineStart, selectionStart)
      const indentMatch = currentLine.match(/^\s*/)
      let indent = indentMatch ? indentMatch[0] : ''

      if (currentLine.trimEnd().endsWith(':') || currentLine.trimEnd().endsWith('{')) {
        indent += '    '
      }

      const insertText = '\n' + indent
      const newValue = value.slice(0, selectionStart) + insertText + value.slice(selectionEnd)
      onChange(newValue)
      setTimeout(() => {
        textarea.selectionStart = textarea.selectionEnd = selectionStart + insertText.length
      }, 0)
      return
    }

    // 3. Auto-Closing Pairs
    const pairs: Record<string, string> = {
      '(': ')',
      '[': ']',
      '{': '}',
      '"': '"',
      "'": "'",
      '`': '`',
    }

    if (pairs[e.key]) {
      const closeChar = pairs[e.key]
      if (selectionStart !== selectionEnd) {
        e.preventDefault()
        const selected = value.slice(selectionStart, selectionEnd)
        const newValue =
          value.slice(0, selectionStart) + e.key + selected + closeChar + value.slice(selectionEnd)
        onChange(newValue)
        setTimeout(() => {
          textarea.selectionStart = selectionStart + 1
          textarea.selectionEnd = selectionEnd + 1
        }, 0)
        return
      }

      if (e.key === '(' || e.key === '[' || e.key === '{') {
        e.preventDefault()
        const newValue =
          value.slice(0, selectionStart) + e.key + closeChar + value.slice(selectionEnd)
        onChange(newValue)
        setTimeout(() => {
          textarea.selectionStart = selectionStart + 1
        }, 0)
        return
      }
    }

    // 4. Backspace pair removal
    if (e.key === 'Backspace' && selectionStart === selectionEnd && selectionStart > 0) {
      const prevChar = value[selectionStart - 1]
      const nextChar = value[selectionStart]
      const matching: Record<string, string> = { '(': ')', '[': ']', '{': '}', '"': '"', "'": "'" }
      if (matching[prevChar] && matching[prevChar] === nextChar) {
        e.preventDefault()
        const newValue = value.slice(0, selectionStart - 1) + value.slice(selectionStart + 1)
        onChange(newValue)
        setTimeout(() => {
          textarea.selectionStart = textarea.selectionEnd = selectionStart - 1
        }, 0)
      }
    }
  }

  const copyCode = () => {
    void navigator.clipboard.writeText(code)
  }

  const hintLineNumber = activeLineHint?.line_number ?? activeLineHint?.lineNumber
  const hintCurrentLineText = activeLineHint?.current_line_text ?? activeLineHint?.currentLineText
  const hintTargetConcept = activeLineHint?.target_concept ?? activeLineHint?.targetConcept

  return (
    <div
      className={`flex flex-col ${
        borderless ? 'bg-[#1a1a1a]' : 'rounded-xl border border-[#282828] bg-[#1a1a1a] shadow-2xl'
      } text-[#eff1f6] overflow-hidden`}
    >
      {/* Primary Header & Sub-Header */}
      {!hideHeader && (
        <>
          <div className="flex items-center justify-between border-b border-[#282828] bg-[#262626] px-4 py-2 text-xs">
            <div className="flex items-center gap-2">
              <span className="text-[#2cbb5d] font-bold text-sm font-mono">&lt;/&gt;</span>
              <span className="font-semibold text-[#eff1f6] text-sm">Code</span>
            </div>

            <div className="flex items-center gap-2">
              {onReset && (
                <button
                  onClick={onReset}
                  title="Reset to boilerplate"
                  className="flex items-center gap-1 rounded px-2 py-1 text-[#8a8a8a] hover:bg-[#333333] hover:text-[#eff1f6] transition text-xs"
                >
                  🔄 <span className="hidden sm:inline">Reset</span>
                </button>
              )}
              <button
                onClick={copyCode}
                title="Copy code"
                className="flex items-center gap-1 rounded px-2 py-1 text-[#8a8a8a] hover:bg-[#333333] hover:text-[#eff1f6] transition text-xs"
              >
                📋 <span className="hidden sm:inline">Copy</span>
              </button>
            </div>
          </div>

          {/* Sub-Header: Language Selector & Auto Indicator (Matching LeetCode) */}
          <div className="flex items-center justify-between border-b border-[#282828] bg-[#1e1e1e] px-4 py-1.5 text-xs">
            <div className="flex items-center gap-2.5">
              {onLanguageChange ? (
                <select
                  value={language}
                  onChange={(e) => onLanguageChange(e.target.value)}
                  className="rounded bg-[#282828] px-2.5 py-1 text-xs font-medium text-[#eff1f6] border border-[#3a3a3a] focus:border-[#2cbb5d] focus:outline-none cursor-pointer"
                >
                  {SUPPORTED_LANGUAGES.map((lang) => (
                    <option key={lang.id} value={lang.id} className="bg-[#1e1e1e] text-[#eff1f6]">
                      {lang.label}
                    </option>
                  ))}
                </select>
              ) : (
                <span className="text-xs font-medium text-[#eff1f6]">Python3 ∨</span>
              )}

              <span className="text-xs text-[#8a8a8a] font-mono select-none">• Auto</span>
            </div>

            <div className="flex items-center gap-2">
              {onRequestLineHint && !readOnly && (
                <button
                  type="button"
                  onClick={() => triggerLineHint()}
                  disabled={lineHintLoading}
                  className={`flex items-center gap-1.5 rounded px-2.5 py-1 text-xs font-medium transition cursor-pointer ${
                    lineHintLoading
                      ? 'bg-amber-500/20 text-amber-300 border border-amber-500/40 animate-pulse'
                      : activeLineHint
                      ? 'bg-amber-500/25 text-amber-200 border border-amber-500/50 hover:bg-amber-500/35'
                      : 'bg-[#282828] hover:bg-[#333333] text-amber-300/90 border border-amber-500/30 hover:text-amber-200'
                  }`}
                  title={`Request Socratic Hint for line ${cursorLine} (Alt+H)`}
                >
                  <span>💡</span>
                  <span>{lineHintLoading ? 'Thinking…' : `Line ${cursorLine} Hint`}</span>
                  <span className="text-[10px] text-amber-400/60 font-mono hidden md:inline">(Alt+H)</span>
                </button>
              )}
              {onGradeSolution && !readOnly && (
                <button
                  type="button"
                  onClick={onGradeSolution}
                  disabled={grading || submitting || !code.trim()}
                  className={`flex items-center gap-1.5 rounded px-2.5 py-1 text-xs font-semibold transition cursor-pointer ${
                    grading || submitting
                      ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/40 animate-pulse'
                      : 'bg-emerald-600/25 hover:bg-emerald-600/40 text-emerald-200 border border-emerald-500/50 shadow-sm'
                  }`}
                  title="Grade your solution with local Qwen 2.5 Coder 7B (Alt+G)"
                >
                  <span>⚡</span>
                  <span>{grading || submitting ? 'Grading…' : 'Grade My Solution'}</span>
                  <span className="text-[10px] text-emerald-300/70 font-mono hidden md:inline">(Alt+G)</span>
                </button>
              )}
              {onRun && (
                <button
                  onClick={onRun}
                  disabled={running || submitting}
                  className="rounded bg-[#282828] hover:bg-[#333333] border border-[#3a3a3a] px-3 py-1 text-xs font-semibold text-[#eff1f6] transition disabled:opacity-40"
                >
                  {running ? 'Running…' : '▶ Run'}
                </button>
              )}
              {onSubmit && (
                <button
                  onClick={onSubmit}
                  disabled={running || submitting}
                  className="rounded bg-[#2cbb5d] hover:bg-[#2cbb5d]/90 px-3.5 py-1 text-xs font-semibold text-white transition disabled:opacity-40"
                >
                  {submitting ? 'Submitting…' : 'Submit'}
                </button>
              )}
            </div>
          </div>
        </>
      )}

      {/* Editor Body with LeetCode Colors and Line Numbers */}
      <div className="relative flex font-mono text-sm bg-[#1a1a1a]" style={{ height }}>
        {/* Line Numbers Gutter */}
        <div
          ref={lineNumbersRef}
          aria-hidden="true"
          className="select-none border-r border-[#2d2d2d] bg-[#1a1a1a] px-1.5 py-3 text-right font-mono text-xs text-[#858585] overflow-hidden leading-6"
          style={{ width: onRequestLineHint && !readOnly ? '56px' : '48px' }}
        >
          {Array.from({ length: lineCount }, (_, i) => {
            const lineNum = i + 1
            const isCurrent = lineNum === cursorLine
            const hasActiveHint = hintLineNumber === lineNum
            return (
              <div
                key={lineNum}
                className={`group flex items-center justify-end gap-1 px-1 rounded transition-colors ${
                  hasActiveHint
                    ? 'bg-amber-500/20 text-amber-300 font-bold'
                    : isCurrent
                    ? 'text-[#eff1f6] bg-[#2a2a2a]/60'
                    : 'hover:text-[#ccc]'
                }`}
              >
                {onRequestLineHint && !readOnly && (
                  <button
                    type="button"
                    tabIndex={-1}
                    onClick={(e) => {
                      e.stopPropagation()
                      triggerLineHint(lineNum)
                    }}
                    title={`Request Socratic Hint for line ${lineNum} (Alt+H)`}
                    className={`cursor-pointer text-[10px] transition-opacity hover:scale-110 ${
                      hasActiveHint
                        ? 'opacity-100'
                        : isCurrent
                        ? 'opacity-60 group-hover:opacity-100'
                        : 'opacity-0 group-hover:opacity-100'
                    }`}
                  >
                    💡
                  </button>
                )}
                <span>{lineNum}</span>
              </div>
            )
          })}
        </div>

        {/* Code Viewport with Syntax-Highlighted Underlay & Transparent Textarea */}
        <div className="relative flex-1 overflow-hidden">
          {/* Syntax Highlighted Underlay */}
          <pre
            ref={highlightRef}
            aria-hidden="true"
            dangerouslySetInnerHTML={{ __html: highlightedHtml + '\n' }}
            className="pointer-events-none absolute inset-0 m-0 p-3 font-mono text-[13px] leading-6 overflow-hidden whitespace-pre font-normal text-[#eff1f6]"
            style={{
              fontFamily: 'Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace',
              tabSize: 4,
            }}
          />

          {/* Textarea Input Overlay */}
          <textarea
            ref={textareaRef}
            value={code}
            onChange={(e) => {
              onChange(e.target.value)
              setTimeout(updateCursorPosition, 0)
            }}
            onKeyUp={updateCursorPosition}
            onClick={updateCursorPosition}
            onSelect={updateCursorPosition}
            onKeyDown={handleKeyDown}
            onScroll={handleScroll}
            readOnly={readOnly}
            spellCheck={false}
            autoCapitalize="off"
            autoComplete="off"
            autoCorrect="off"
            className="absolute inset-0 m-0 w-full h-full resize-none bg-transparent p-3 font-mono text-[13px] leading-6 text-transparent caret-white focus:outline-none whitespace-pre overflow-auto selection:bg-[#264f78]"
            style={{
              fontFamily: 'Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace',
              tabSize: 4,
            }}
            placeholder={placeholder}
          />
        </div>
      </div>

      {/* Inline Socratic Line Hint Callout Tray */}
      {(lineHintLoading || activeLineHint) && (
        <div className="border-t border-amber-500/30 bg-gradient-to-r from-[#201c13] via-[#1a1711] to-[#1c1812] px-4 py-3 text-xs text-amber-100 shadow-inner">
          <div className="flex items-start justify-between gap-3">
            <div className="flex items-start gap-2.5 min-w-0 flex-1">
              <span className="text-base select-none mt-0.5">💡</span>
              <div className="space-y-1.5 min-w-0 flex-1">
                <div className="flex items-center flex-wrap gap-2">
                  <span className="font-semibold text-amber-300 text-xs tracking-wide">
                    Socratic Hint · Line {hintLineNumber ?? cursorLine}
                  </span>
                  {hintTargetConcept && (
                    <span className="rounded-full bg-amber-500/20 px-2 py-0.5 text-[10px] font-medium text-amber-300 border border-amber-500/30">
                      {hintTargetConcept}
                    </span>
                  )}
                  {hintCurrentLineText && (
                    <span className="font-mono text-[11px] text-amber-200/80 bg-black/50 px-1.5 py-0.5 rounded truncate max-w-xs border border-white/5">
                      {hintCurrentLineText}
                    </span>
                  )}
                </div>

                {lineHintLoading ? (
                  <div className="flex items-center gap-2 text-amber-300/80 text-xs py-1">
                    <span className="inline-block w-3 h-3 rounded-full border-2 border-amber-400 border-t-transparent animate-spin"></span>
                    <span>Consulting Socratic Guide grounded in reference solution…</span>
                  </div>
                ) : (
                  <p className="text-xs text-slate-200 leading-relaxed font-sans whitespace-pre-line">
                    {activeLineHint?.hint}
                  </p>
                )}
              </div>
            </div>

            <div className="flex items-center gap-1.5 shrink-0">
              {onRequestLineHint && !lineHintLoading && (
                <button
                  type="button"
                  onClick={() => triggerLineHint(hintLineNumber ?? cursorLine)}
                  title="Ask for another hint or re-evaluate with current code"
                  className="rounded px-2 py-1 text-[11px] font-medium text-amber-300 hover:text-amber-100 hover:bg-amber-500/20 transition cursor-pointer flex items-center gap-1"
                >
                  <span>🔄</span>
                  <span className="hidden sm:inline">Another Hint</span>
                </button>
              )}
              {onDismissLineHint && (
                <button
                  type="button"
                  onClick={onDismissLineHint}
                  title="Dismiss hint (Escape)"
                  className="rounded p-1 text-slate-400 hover:text-slate-200 hover:bg-white/10 transition cursor-pointer text-xs"
                >
                  ✕
                </button>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Footer Info */}
      {!hideFooter && (
        <div className="flex items-center justify-between border-t border-[#282828] bg-[#1e1e1e] px-4 py-1 text-[11px] text-[#8a8a8a] font-mono">
          <div className="flex items-center gap-3">
            <span>{lineCount} lines</span>
            <span>{code.length} chars</span>
            <span className="text-[#eff1f6]">Ln {cursorLine}, Col {cursorCol}</span>
          </div>
          <div className="flex items-center gap-3 text-[10px] text-[#8a8a8a]">
            {onRequestLineHint && !readOnly && (
              <span className="text-amber-400/90">
                <kbd className="rounded bg-[#282828] px-1 py-0.5 text-amber-300 border border-amber-500/30">Alt+H</kbd> Line Hint
              </span>
            )}
            {onGradeSolution && !readOnly && (
              <span className="text-emerald-400/90">
                <kbd className="rounded bg-[#282828] px-1 py-0.5 text-emerald-300 border border-emerald-500/30">Alt+G</kbd> Grade
              </span>
            )}
            <span><kbd className="rounded bg-[#282828] px-1 py-0.5 text-[#eff1f6]">Ctrl+Enter</kbd> Run</span>
            <span><kbd className="rounded bg-[#282828] px-1 py-0.5 text-[#eff1f6]">Ctrl+Shift+Enter</kbd> Submit</span>
          </div>
        </div>
      )}
    </div>
  )
}
