import React, { useCallback, useRef } from 'react'

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
}

const SUPPORTED_LANGUAGES = [
  { id: 'python', label: 'Python 3' },
  { id: 'typescript', label: 'TypeScript' },
  { id: 'javascript', label: 'JavaScript' },
  { id: 'cpp', label: 'C++' },
  { id: 'java', label: 'Java' },
  { id: 'rust', label: 'Rust' },
  { id: 'go', label: 'Go' },
]

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
}: CodeEditorProps) {
  const textareaRef = useRef<HTMLTextAreaElement | null>(null)
  const lineNumbersRef = useRef<HTMLDivElement | null>(null)

  const lines = code.split('\n')
  const lineCount = Math.max(lines.length, 1)

  // Synchronize scrolling between textarea and line numbers
  const handleScroll = useCallback(() => {
    if (textareaRef.current && lineNumbersRef.current) {
      lineNumbersRef.current.scrollTop = textareaRef.current.scrollTop
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
        // Un-indent current line
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
        // Indent
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

      // Extra indent if line ends with colon or open brace
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
      // If user selected text, wrap selection
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

      // Single insertion auto-close
      if (e.key === '(' || e.key === '[' || e.key === '{') {
        e.preventDefault()
        const newValue =
          value.slice(0, selectionStart) + e.key + closeChar + value.slice(selectionEnd)
        onChange(newValue)
        setTimeout(() => {
          textarea.selectionStart = textarea.selectionEnd = selectionStart + 1
        }, 0)
        return
      }
    }

    // 4. Backspace pair removal if empty inside
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
    <div className="flex flex-col rounded-xl border border-ink-line bg-[#0d1117] text-slate-200 overflow-hidden shadow-2xl">
      {/* Editor Header Toolbar */}
      <div className="flex flex-wrap items-center justify-between gap-2 border-b border-ink-line/80 bg-[#161b22] px-4 py-2 text-xs">
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-1.5 text-slate-400 font-mono">
            <span className="text-emerald-400 font-bold">&lt;/&gt;</span>
            <span className="font-semibold text-slate-300">Code</span>
          </div>

          {onLanguageChange && (
            <select
              value={language}
              onChange={(e) => onLanguageChange(e.target.value)}
              className="rounded border border-ink-line/80 bg-[#0d1117] px-2.5 py-1 text-xs font-medium text-slate-200 focus:border-sky-500 focus:outline-none"
            >
              {SUPPORTED_LANGUAGES.map((lang) => (
                <option key={lang.id} value={lang.id}>
                  {lang.label}
                </option>
              ))}
            </select>
          )}
        </div>

        <div className="flex items-center gap-2">
          {onReset && (
            <button
              onClick={onReset}
              title="Reset code to starter boilerplate"
              className="flex items-center gap-1 rounded px-2 py-1 text-slate-400 hover:bg-ink-soft hover:text-slate-200 transition"
            >
              🔄 <span className="hidden sm:inline">Reset</span>
            </button>
          )}
          <button
            onClick={copyCode}
            title="Copy code to clipboard"
            className="flex items-center gap-1 rounded px-2 py-1 text-slate-400 hover:bg-ink-soft hover:text-slate-200 transition"
          >
            📋 <span className="hidden sm:inline">Copy</span>
          </button>
        </div>
      </div>

      {/* Editor Body */}
      <div className="relative flex font-mono text-sm" style={{ height }}>
        {/* Line Numbers */}
        <div
          ref={lineNumbersRef}
          aria-hidden="true"
          className="select-none border-r border-ink-line/40 bg-[#090d13] px-3 py-3 text-right font-mono text-xs text-slate-600 overflow-hidden leading-6"
          style={{ width: '44px' }}
        >
          {Array.from({ length: lineCount }, (_, i) => (
            <div key={i + 1}>{i + 1}</div>
          ))}
        </div>

        {/* Textarea Input */}
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
          className="flex-1 resize-none bg-transparent p-3 font-mono text-sm leading-6 text-emerald-300 placeholder-slate-600 focus:outline-none whitespace-pre overflow-auto selection:bg-sky-500/30"
          placeholder="# Write your solution here..."
        />
      </div>

      {/* Editor Status / Shortcut Footer */}
      <div className="flex items-center justify-between border-t border-ink-line/60 bg-[#090d13] px-3 py-1 text-[11px] text-slate-500 font-mono">
        <div className="flex items-center gap-3">
          <span>{lineCount} lines</span>
          <span>{code.length} chars</span>
        </div>
        <div className="flex items-center gap-3">
          <span className="hidden sm:inline text-slate-500">
            <kbd className="rounded bg-ink-soft px-1 py-0.5 text-[10px] text-slate-300">Ctrl+Enter</kbd> Run
          </span>
          <span className="hidden sm:inline text-slate-500">
            <kbd className="rounded bg-ink-soft px-1 py-0.5 text-[10px] text-slate-300">Ctrl+Shift+Enter</kbd> Submit
          </span>
        </div>
      </div>
    </div>
  )
}
