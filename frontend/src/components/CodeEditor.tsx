import React, { useCallback, useMemo, useRef } from 'react'

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
}: CodeEditorProps) {
  const textareaRef = useRef<HTMLTextAreaElement | null>(null)
  const highlightRef = useRef<HTMLPreElement | null>(null)
  const lineNumbersRef = useRef<HTMLDivElement | null>(null)

  const lines = code.split('\n')
  const lineCount = Math.max(lines.length, 1)

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

  // Handle Tab, Shift+Tab, Enter (auto-indent), and auto-closing brackets
  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
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

  return (
    <div className="flex flex-col rounded-xl border border-[#282828] bg-[#1a1a1a] text-[#eff1f6] overflow-hidden shadow-2xl">
      {/* Primary Header: </> Code */}
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

      {/* Editor Body with LeetCode Colors and Line Numbers */}
      <div className="relative flex font-mono text-sm bg-[#1a1a1a]" style={{ height }}>
        {/* Line Numbers Gutter */}
        <div
          ref={lineNumbersRef}
          aria-hidden="true"
          className="select-none border-r border-[#2d2d2d] bg-[#1a1a1a] px-3 py-3 text-right font-mono text-xs text-[#858585] overflow-hidden leading-6"
          style={{ width: '48px' }}
        >
          {Array.from({ length: lineCount }, (_, i) => (
            <div key={i + 1}>{i + 1}</div>
          ))}
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
            onChange={(e) => onChange(e.target.value)}
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
            placeholder="# Write your solution here..."
          />
        </div>
      </div>

      {/* Footer Info */}
      <div className="flex items-center justify-between border-t border-[#282828] bg-[#1e1e1e] px-4 py-1 text-[11px] text-[#8a8a8a] font-mono">
        <div className="flex items-center gap-3">
          <span>{lineCount} lines</span>
          <span>{code.length} chars</span>
        </div>
        <div className="flex items-center gap-3 text-[10px] text-[#8a8a8a]">
          <span><kbd className="rounded bg-[#282828] px-1 py-0.5 text-[#eff1f6]">Ctrl+Enter</kbd> Run</span>
          <span><kbd className="rounded bg-[#282828] px-1 py-0.5 text-[#eff1f6]">Ctrl+Shift+Enter</kbd> Submit</span>
        </div>
      </div>
    </div>
  )
}
