import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { createPortal } from 'react-dom'
import { api } from '../api/client'
import {
  getModelDisplayInfo,
  isAntigravityModel,
  type DeckDocMessage,
  type ExplainCodeSelectionResponse,
  type LexiconGlossItem,
} from '../api/types'
import type { DiffStats, TokenSegment } from './AnswerComparison'
import { checkLineLogic, type LogicWarning } from '../utils/logicGuard'
import { hexToRgb, DEFAULT_TARGET_HIGHLIGHT_COLOR } from '../utils/expectedCodeUtils'
import { useOptionalLexicon } from './LexiconContext'
import { AddToDefinitionsPrompt } from './AddToDefinitionsPrompt'
import { extractTermDefinitionsFromQA, isTermInGlosses } from '../utils/lexiconExtractor'

export interface LineHintData {
  hint: string
  line_number?: number
  lineNumber?: number
  current_line_text?: string
  currentLineText?: string
  target_concept?: string | null
  targetConcept?: string | null
  error?: string | null
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
  // Context for LLM explanations (e.g. card title or problem prompt)
  context?: string | null
  // Deck ID for grounding code against attached documentation
  deckId?: string | null
  // Synced active model from parent view / user settings
  activeModel?: string | null
  onActiveModelChange?: (modelId: string) => void
  // Socratic Line Hint props
  activeLineHint?: LineHintData | null
  lineHintLoading?: boolean
  onRequestLineHint?: (lineNumber: number, lineText: string) => void
  onDismissLineHint?: () => void
  onCursorChange?: (line: number, col: number) => void
  onGradeSolution?: () => void
  grading?: boolean
  // Token diff highlighting against reference answer
  diffSegments?: TokenSegment[] | null
  diffStats?: DiffStats | null
  // Hint Only mode (e.g. for reference solution viewing)
  hintOnly?: boolean
  hintOnlyLine?: number
  onHintOnlyLineChange?: (line: number) => void
  // Real-time Logic Guard against reference solution
  cleanRefCode?: string
  logicGuardEnabled?: boolean
  onLogicGuardToggle?: (enabled: boolean) => void
  onLogicWarningChange?: (warning: LogicWarning | null) => void
  // Target solution highlighting
  targetLineNumbers?: Set<number> | null
  focusTargetCode?: boolean
  targetHighlightColor?: string
  initialScrollLine?: number
  // Layout & shared card-context AI caching props
  fillHeight?: boolean
  compactFooter?: boolean
  cardId?: string | null
  userCode?: string | null
  userTestCode?: string | null
  executionSummary?: string | null
  revealed?: boolean
  sharedQaHistory?: DeckDocMessage[]
  onSharedQaHistoryChange?: (
    updater: DeckDocMessage[] | ((prev: DeckDocMessage[]) => DeckDocMessage[]),
  ) => void
}

// Only what the backend runner can execute (code_practice.RUNNABLE_LANGUAGES).
const SUPPORTED_LANGUAGES = [
  { id: 'python', label: 'Python3' },
  { id: 'typescript', label: 'TypeScript' },
  { id: 'javascript', label: 'JavaScript' },
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

function renderDiffSegment(text: string, type: string): string {
  if (!text) return ''
  const leadingWsMatch = text.match(/^\s+/)
  const trailingWsMatch = text.match(/\s+$/)
  const leadingWs = leadingWsMatch ? leadingWsMatch[0] : ''
  const trailingWs = trailingWsMatch ? trailingWsMatch[0] : ''
  const core = text.slice(leadingWs.length, text.length - trailingWs.length)

  if (!core) {
    return escapeHtml(text)
  }

  let coreHtml = ''
  if (type === 'missing') {
    coreHtml = `<span class="diff-segment-missing" style="background-color: rgba(245, 158, 11, 0.32); color: #fef08a; box-shadow: inset 0 -2px 0 #f59e0b; border-radius: 3px;" title="Missing from your solution">${escapeHtml(core)}</span>`
  } else if (type === 'matched') {
    coreHtml = `<span class="diff-segment-matched" style="background-color: rgba(16, 185, 129, 0.22); color: #a7f3d0; box-shadow: inset 0 -1px 0 rgba(16, 185, 129, 0.6); border-radius: 3px;" title="Matches your solution">${escapeHtml(core)}</span>`
  } else if (type === 'punct') {
    coreHtml = `<span style="color: #858585;">${escapeHtml(core)}</span>`
  } else {
    coreHtml = highlightLeetCode(core)
  }

  return escapeHtml(leadingWs) + coreHtml + escapeHtml(trailingWs)
}

function renderDocExplanation(text: string) {
  const paragraphs = text.split(/\n\s*\n/)
  return paragraphs.map((p, idx) => {
    const trimmed = p.trim()
    if (!trimmed) return null

    const isVerbatim = trimmed.includes('Verbatim Specification') || trimmed.startsWith('>')
    const isMeaningApp = trimmed.includes('Meaning & Application') || trimmed.includes('Relevant Rules') || trimmed.includes('Documentation Details') || trimmed.includes('→ Explanation.')
    const isCitedDoc = trimmed.includes('Cited Document') || trimmed.includes('Found in Docs')
    const isKeyTakeaway = trimmed.includes('Key Takeaway')

    // Citation is already shown in the top header badge; suppress redundant box
    if (isCitedDoc) {
      return null
    }

    // If it's a verbatim specification block
    if (isVerbatim) {
      let quoteText = trimmed
      if (quoteText.includes('**→ Verbatim Specification.**')) {
        quoteText = quoteText.replace(/\*\*→\s*Verbatim Specification\.\*\*/i, '').trim()
      }
      quoteText = quoteText.replace(/^>\s*/gm, '').trim()

      return (
        <div
          key={idx}
          className="rounded-lg border-l-4 border-emerald-400 bg-emerald-950/30 border-y border-r border-emerald-500/20 p-3 shadow-sm space-y-1.5"
        >
          <div className="flex items-center gap-1.5 text-emerald-400 font-bold text-[10px] tracking-wider uppercase">
            <span>📖</span>
            <span>Verbatim Specification</span>
          </div>
          <div className="font-mono text-[12px] leading-relaxed text-emerald-100/95 whitespace-pre-wrap pl-0.5">
            {quoteText}
          </div>
        </div>
      )
    }

    // If it's a Meaning & Application block
    if (isMeaningApp) {
      let bodyText = trimmed
      if (bodyText.includes('**→ Meaning & Application.**')) {
        bodyText = bodyText.replace(/\*\*→\s*Meaning\s*(?:&|and)\s*Application\.\*\*/i, '').trim()
      } else if (bodyText.includes('**→ Relevant Rules.**')) {
        bodyText = bodyText.replace(/\*\*→\s*Relevant Rules\.\*\*/i, '').trim()
      } else if (bodyText.includes('**→ Documentation Details.**')) {
        bodyText = bodyText.replace(/\*\*→\s*Documentation Details\.\*\*/i, '').trim()
      }
      // Clean up punctuation spacing around inline backticks: e.g. " `token` ," -> " `token`,"
      bodyText = bodyText.replace(/\s+([,.:;?!])/g, '$1')

      const parts = bodyText.split(/(\*\*[^*]+\*\*|`[^`]+`)/g)

      return (
        <div
          key={idx}
          className="rounded-lg bg-black/40 border border-white/5 p-3.5 space-y-1.5 shadow-sm"
        >
          <div className="flex items-center gap-1.5 text-emerald-300 font-bold text-[11px] tracking-wider uppercase">
            <span>💡</span>
            <span>Meaning & Application</span>
          </div>
          <div className="text-[13px] leading-6 text-slate-100 font-sans">
            {parts.map((part, pIdx) => {
              if (part.startsWith('**') && part.endsWith('**')) {
                return (
                  <strong key={pIdx} className="text-emerald-300 font-semibold">
                    {part.slice(2, -2)}
                  </strong>
                )
              }
              if (part.startsWith('`') && part.endsWith('`')) {
                return (
                  <code
                    key={pIdx}
                    className="px-1.5 py-0.5 rounded bg-emerald-950/60 text-emerald-300 font-mono text-[12px] border border-emerald-500/25 inline-block my-0.5"
                  >
                    {part.slice(1, -1)}
                  </code>
                )
              }
              return <span key={pIdx}>{part}</span>
            })}
          </div>
        </div>
      )
    }

    // Key takeaway block
    if (isKeyTakeaway) {
      let bodyText = trimmed
      if (bodyText.includes('**→ Key Takeaway.**')) {
        bodyText = bodyText.replace(/\*\*→\s*Key Takeaway\.\*\*/i, '').trim()
      }
      bodyText = bodyText.replace(/\s+([,.:;?!])/g, '$1')
      const parts = bodyText.split(/(\*\*[^*]+\*\*|`[^`]+`)/g)

      return (
        <div
          key={idx}
          className="flex items-start gap-2.5 rounded-lg bg-sky-950/30 border border-sky-500/30 px-3.5 py-2.5 text-sky-100 shadow-sm"
        >
          <span className="text-sky-400 font-bold text-sm shrink-0 mt-0.5">⚡</span>
          <div className="text-[12px] leading-relaxed text-sky-100/90 font-sans">
            <span className="font-semibold text-sky-300 mr-1.5">Key Takeaway:</span>
            {parts.map((part, pIdx) => {
              if (part.startsWith('**') && part.endsWith('**')) {
                return (
                  <strong key={pIdx} className="text-sky-200 font-semibold">
                    {part.slice(2, -2)}
                  </strong>
                )
              }
              if (part.startsWith('`') && part.endsWith('`')) {
                return (
                  <code
                    key={pIdx}
                    className="px-1.5 py-0.5 rounded bg-black/60 text-sky-200 font-mono text-[11px] border border-sky-500/20"
                  >
                    {part.slice(1, -1)}
                  </code>
                )
              }
              return <span key={pIdx}>{part}</span>
            })}
          </div>
        </div>
      )
    }

    // Parse simple inline bolding (**text**) and code (`code`)
    const parts = trimmed.split(/(\*\*[^*]+\*\*|`[^`]+`)/g)

    return (
      <div
        key={idx}
        className="p-3 rounded-lg bg-black/30 border border-white/10 text-slate-200 text-[13px] leading-relaxed"
      >
        <p>
          {parts.map((part, pIdx) => {
            if (part.startsWith('**') && part.endsWith('**')) {
              const boldContent = part.slice(2, -2)
              return (
                <strong key={pIdx} className="text-white font-semibold">
                  {boldContent}
                </strong>
              )
            }
            if (part.startsWith('`') && part.endsWith('`')) {
              return (
                <code
                  key={pIdx}
                  className="px-1.5 py-0.5 rounded bg-black/60 text-emerald-200 font-mono text-[11px] border border-emerald-500/20"
                >
                  {part.slice(1, -1)}
                </code>
              )
            }
            return <span key={pIdx}>{part}</span>
          })}
        </p>
      </div>
    )
  })
}

function renderFormattedMarkdown(text: string) {
  const paragraphs = text.split(/\n\s*\n/)
  return paragraphs.map((p, idx) => {
    const trimmed = p.trim()
    if (!trimmed) return null

    // Code block check ```lang ... ```
    if (trimmed.startsWith('```') && trimmed.endsWith('```')) {
      const codeLines = trimmed.slice(3, -3).replace(/^[a-z0-9_-]+\n/i, '')
      return (
        <pre
          key={idx}
          className="my-1.5 p-2 rounded bg-black/70 border border-emerald-500/25 font-mono text-[11px] text-emerald-200 overflow-x-auto whitespace-pre leading-relaxed"
        >
          {codeLines}
        </pre>
      )
    }

    const lines = trimmed.split('\n')
    return (
      <div key={idx} className="space-y-1 text-[12px] leading-relaxed text-slate-200 font-sans">
        {lines.map((line, lIdx) => {
          const isBullet = line.trim().startsWith('- ') || line.trim().startsWith('* ')
          const cleanLine = isBullet ? line.trim().slice(2) : line
          const parts = cleanLine.split(/(\*\*[^*]+\*\*|`[^`]+`)/g)
          return (
            <div key={lIdx} className={isBullet ? 'flex items-start gap-1.5 pl-1.5' : ''}>
              {isBullet && <span className="text-emerald-400 font-bold shrink-0 mt-0.5">•</span>}
              <div>
                {parts.map((part, pIdx) => {
                  if (part.startsWith('**') && part.endsWith('**')) {
                    return (
                      <strong key={pIdx} className="text-emerald-300 font-semibold">
                        {part.slice(2, -2)}
                      </strong>
                    )
                  }
                  if (part.startsWith('`') && part.endsWith('`')) {
                    return (
                      <code
                        key={pIdx}
                        className="px-1.5 py-0.5 rounded bg-emerald-950/70 text-emerald-300 font-mono text-[11px] border border-emerald-500/25 inline-block mx-0.5"
                      >
                        {part.slice(1, -1)}
                      </code>
                    )
                  }
                  return <span key={pIdx}>{part}</span>
                })}
              </div>
            </div>
          )
        })}
      </div>
    )
  })
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
  // Context & grounding
  context,
  deckId,
  activeModel,
  onActiveModelChange,
  activeLineHint,
  lineHintLoading = false,
  onRequestLineHint,
  onDismissLineHint,
  onCursorChange,
  onGradeSolution,
  grading = false,
  diffSegments = null,
  diffStats = null,
  hintOnly = false,
  hintOnlyLine = 1,
  onHintOnlyLineChange,
  cleanRefCode,
  logicGuardEnabled = true,
  onLogicGuardToggle,
  onLogicWarningChange,
  targetLineNumbers = null,
  focusTargetCode = false,
  targetHighlightColor = DEFAULT_TARGET_HIGHLIGHT_COLOR,
  initialScrollLine,
  fillHeight = false,
  compactFooter = false,
  cardId = null,
  userCode,
  userTestCode,
  executionSummary = null,
  revealed = false,
  sharedQaHistory,
  onSharedQaHistoryChange,
}: CodeEditorProps) {
  const textareaRef = useRef<HTMLTextAreaElement | null>(null)
  const highlightRef = useRef<HTMLPreElement | null>(null)
  const lineNumbersRef = useRef<HTMLDivElement | null>(null)
  const editorContainerRef = useRef<HTMLDivElement | null>(null)
  const lexiconCtx = useOptionalLexicon()

  const [cursorLine, setCursorLine] = useState(1)
  const [cursorCol, setCursorCol] = useState(1)

  // Real-time Logic Guard state
  const [activeLogicWarning, setActiveLogicWarning] = useState<LogicWarning | null>(null)
  const prevCursorLineRef = useRef<number>(1)

  useEffect(() => {
    if (!logicGuardEnabled && activeLogicWarning) {
      setActiveLogicWarning(null)
      onLogicWarningChange?.(null)
    }
  }, [logicGuardEnabled, activeLogicWarning, onLogicWarningChange])

  useEffect(() => {
    setActiveLogicWarning(null)
  }, [cleanRefCode])

  useEffect(() => {
    if (initialScrollLine && initialScrollLine > 1 && textareaRef.current) {
      const lineHeightPx = 24
      const targetScrollTop = Math.max(0, (initialScrollLine - 3) * lineHeightPx)
      textareaRef.current.scrollTop = targetScrollTop
      if (lineNumbersRef.current) {
        lineNumbersRef.current.scrollTop = targetScrollTop
      }
      if (highlightRef.current) {
        highlightRef.current.scrollTop = targetScrollTop
      }
    }
  }, [initialScrollLine])

  // Selection & Deck Documentation Search state
  const [selectedText, setSelectedText] = useState('')
  const [floatingPillPos, setFloatingPillPos] = useState<{ top: number; left: number } | null>(null)
  const [isSearchingDocs, setIsSearchingDocs] = useState(false)
  const [docSearchResult, setDocSearchResult] = useState<
    (ExplainCodeSelectionResponse & { selectedSnippet: string }) | null
  >(null)
  const [docSearchError, setDocSearchError] = useState<string | null>(null)
  const [docAddStatus, setDocAddStatus] = useState<'idle' | 'saving' | 'added' | 'dismissed'>('idle')
  const [docAddError, setDocAddError] = useState<string | null>(null)
  const [showDocMatches, setShowDocMatches] = useState(false)
  const [selectedModel, setSelectedModel] = useState<string | null>(() => activeModel || null)
  const [availableModels, setAvailableModels] = useState<string[]>([])
  const [copiedDocResult, setCopiedDocResult] = useState(false)

  // Sync internal selectedModel whenever parent activeModel switches
  useEffect(() => {
    if (activeModel) {
      setSelectedModel(activeModel)
    }
  }, [activeModel])

  // Interactive Deck Documentation & Local LLM Q&A state (shared across panes when provided)
  const [localQaHistory, setLocalQaHistory] = useState<DeckDocMessage[]>([])
  const qaHistory = sharedQaHistory ?? localQaHistory
  const setQaHistory = useCallback(
    (updater: DeckDocMessage[] | ((prev: DeckDocMessage[]) => DeckDocMessage[])) => {
      if (onSharedQaHistoryChange) {
        onSharedQaHistoryChange(updater)
      } else {
        setLocalQaHistory(updater)
      }
    },
    [onSharedQaHistoryChange],
  )
  const [dismissedQaPrompts, setDismissedQaPrompts] = useState<Record<number, boolean>>({})
  const [savingQaPromptIdx, setSavingQaPromptIdx] = useState<number | null>(null)
  const [qaInput, setQaInput] = useState('')
  const [isAskingQuestion, setIsAskingQuestion] = useState(false)
  const [qaError, setQaError] = useState<string | null>(null)
  const [isQaOpen, setIsQaOpen] = useState(false)
  const [activeQaSnippet, setActiveQaSnippet] = useState<string>('')
  const qaThreadEndRef = useRef<HTMLDivElement | null>(null)
  const qaInputRef = useRef<HTMLInputElement | null>(null)
  const [isPoppedOut, setIsPoppedOut] = useState(false)
  const popupWindowRef = useRef<Window | null>(null)

  const promptSuggestions = useMemo(() => {
    const c = code.toLowerCase()
    if (c.includes('empty') || c.includes('items') || c.includes('rest')) {
      return [
        'Why check inventory.kind === "empty" first?',
        'How does union narrowing work here?',
        'What happens if there are no weapons?',
        'What is the time & space complexity?',
      ]
    }
    if (c.includes('type') || c.includes('interface')) {
      return [
        'Explain the type invariants and structure',
        'How does TypeScript narrow these union types?',
        'What edge cases must be handled?',
        'How does the recursion base case work?',
      ]
    }
    return [
      'Explain the core mechanism of this code',
      'What are the edge cases to watch out for?',
      'How does this adhere to course rules?',
      'What is the time and space complexity?',
    ]
  }, [code])

  // Query installed local models on mount
  useEffect(() => {
    api
      .models()
      .then((data) => {
        if (data?.models && data.models.length > 0) {
          setAvailableModels(data.models)
        }
        if (data?.active && !activeModel && !selectedModel) {
          setSelectedModel(data.active)
        }
      })
      .catch(() => {})
  }, [activeModel, selectedModel])

  const lines = code.split('\n')
  const lineCount = Math.max(lines.length, 1)
  const resolvedHeight =
    height === 'auto'
      ? `${Math.max(140, Math.min(480, lineCount * 24 + 32))}px`
      : height

  const jumpToLine = useCallback(
    (lineNum: number) => {
      const textarea = textareaRef.current
      if (!textarea) return
      const lineList = code.split('\n')
      let charOffset = 0
      for (let i = 0; i < Math.min(lineNum - 1, lineList.length); i++) {
        charOffset += (lineList[i]?.length ?? 0) + 1
      }
      const targetLineText = lineList[lineNum - 1] ?? ''
      textarea.focus()
      textarea.setSelectionRange(charOffset, charOffset + targetLineText.length)
      setCursorLine(lineNum)
      setCursorCol(targetLineText.length + 1)
      prevCursorLineRef.current = lineNum
    },
    [code]
  )

  const updateCursorPosition = useCallback(
    (customTextOrEvent?: string | React.SyntheticEvent, customPos?: number) => {
      const textarea = textareaRef.current
      const customText = typeof customTextOrEvent === 'string' ? customTextOrEvent : undefined
      if (!textarea && customText === undefined) return
      const text = customText !== undefined ? customText : (textarea?.value ?? code)
      const pos = customPos !== undefined ? customPos : (textarea?.selectionStart ?? 0)
      const textBefore = text.slice(0, pos)
      const lineList = textBefore.split('\n')
      const currentLineNumber = lineList.length
      const currentColNumber = (lineList[lineList.length - 1]?.length ?? 0) + 1

      const prevLine = prevCursorLineRef.current
      if (prevLine !== currentLineNumber) {
        prevCursorLineRef.current = currentLineNumber
        // Line departure! Check completed line
        if (logicGuardEnabled && cleanRefCode && !readOnly) {
          const warning = checkLineLogic(text, cleanRefCode, prevLine, language)
          if (warning) {
            setActiveLogicWarning(warning)
            onLogicWarningChange?.(warning)
          } else if (activeLogicWarning && activeLogicWarning.lineNumber === prevLine) {
            setActiveLogicWarning(null)
            onLogicWarningChange?.(null)
          }
        }
      }

      setCursorLine(currentLineNumber)
      setCursorCol(currentColNumber)
      if (onCursorChange) {
        onCursorChange(currentLineNumber, currentColNumber)
      }
    },
    [
      code,
      onCursorChange,
      logicGuardEnabled,
      cleanRefCode,
      readOnly,
      language,
      activeLogicWarning,
      onLogicWarningChange,
    ]
  )

  // Track text selection in textarea and position floating pill
  const handleSelectOrMouseUp = useCallback(
    (e?: React.MouseEvent | React.SyntheticEvent) => {
      updateCursorPosition()
      const textarea = textareaRef.current
      if (!textarea) return
      const start = textarea.selectionStart ?? 0
      const end = textarea.selectionEnd ?? 0
      if (start !== end) {
        const text = textarea.value
        const slice = text.slice(Math.min(start, end), Math.max(start, end))
        if (slice.trim().length > 0) {
          setSelectedText(slice)
          if (editorContainerRef.current) {
            const containerRect = editorContainerRef.current.getBoundingClientRect()
            if (e && 'clientX' in e && (e as React.MouseEvent).clientX) {
              const mouseEvent = e as React.MouseEvent
              const relativeX = Math.max(
                80,
                Math.min(containerRect.width - 80, mouseEvent.clientX - containerRect.left)
              )
              const relativeY = Math.max(
                32,
                Math.min(containerRect.height - 35, mouseEvent.clientY - containerRect.top - 10)
              )
              setFloatingPillPos({ top: relativeY, left: relativeX })
            } else if (!floatingPillPos) {
              setFloatingPillPos({ top: 36, left: Math.min(containerRect.width - 80, 200) })
            }
          }
          return
        }
      }
      setSelectedText('')
      setFloatingPillPos(null)
    },
    [floatingPillPos, updateCursorPosition]
  )

  const triggerDocSearch = useCallback(
    async (codeToSearch?: string, modelOverride?: string) => {
      const targetModel = modelOverride || activeModel || selectedModel || undefined

      let text = (codeToSearch ?? selectedText).trim()
      if (!text && textareaRef.current) {
        const start = textareaRef.current.selectionStart ?? 0
        const end = textareaRef.current.selectionEnd ?? 0
        if (start !== end) {
          text = code.slice(Math.min(start, end), Math.max(start, end)).trim()
        }
      }
      // If still empty, fall back to current line
      if (!text) {
        const lineList = code.split('\n')
        text = (lineList[cursorLine - 1] ?? '').trim()
      }
      if (!text) {
        setDocSearchError('Please select or position cursor on code to search documentation.')
        return
      }

      setIsSearchingDocs(true)
      setDocSearchError(null)
      setDocAddStatus('idle')
      setDocAddError(null)
      try {
        const activeCardId = cardId ?? lexiconCtx?.activeDeckContext?.cardId ?? null
        const res = await api.explainCodeSelection({
          selected_code: text,
          full_code: code,
          language,
          context,
          mode: 'docs',
          model: targetModel,
          deck_id: deckId,
          card_id: activeCardId,
          user_code: userCode ?? code,
          user_test_code: userTestCode,
          execution_summary: executionSummary,
          revealed,
        })
        setDocSearchResult({ ...res, selectedSnippet: text })
        if (res.available_models && res.available_models.length > 0) {
          setAvailableModels(res.available_models)
        }
        if (res.model_used && !activeModel && !selectedModel) {
          setSelectedModel(res.model_used)
        }
      } catch (err: any) {
        setDocSearchError(
          err?.message ||
            `Failed to search deck documentation on ${targetModel || 'selected model'}.`
        )
      } finally {
        setIsSearchingDocs(false)
      }
    },
    [
      activeModel,
      cardId,
      code,
      context,
      cursorLine,
      deckId,
      executionSummary,
      language,
      lexiconCtx,
      revealed,
      selectedModel,
      selectedText,
      userCode,
      userTestCode,
    ]
  )

  const handleCopyDocResult = () => {
    if (docSearchResult?.explanation) {
      void navigator.clipboard.writeText(docSearchResult.explanation)
      setCopiedDocResult(true)
      setTimeout(() => setCopiedDocResult(false), 2000)
    }
  }

  const handleAskQuestion = useCallback(
    async (overrideQuestion?: string) => {
      const q = (overrideQuestion ?? qaInput).trim()
      if (!q || isAskingQuestion) return

      const targetModel = activeModel || selectedModel || undefined
      const userMessage: DeckDocMessage = { role: 'user', content: q }
      const updatedHistory = [...qaHistory, userMessage]
      setQaHistory(updatedHistory)
      setQaInput('')
      setIsAskingQuestion(true)
      setQaError(null)

      try {
        const snippet = docSearchResult?.selectedSnippet || activeQaSnippet || selectedText || ''
        const activeCardId = cardId ?? lexiconCtx?.activeDeckContext?.cardId ?? null
        const res = await api.askDeckQuestion({
          question: q,
          selected_code: snippet,
          full_code: code,
          language,
          context,
          deck_id: deckId,
          card_id: activeCardId,
          user_code: userCode ?? code,
          user_test_code: userTestCode,
          execution_summary: executionSummary,
          revealed,
          model: targetModel,
          history: updatedHistory.slice(0, -1),
        })

        const extractedGlosses =
          res.extracted_glosses && res.extracted_glosses.length > 0
            ? res.extracted_glosses
            : extractTermDefinitionsFromQA({
                question: q,
                answer: res.answer,
                selectedCode: snippet,
                docCitation: res.doc_citation,
                language,
              })

        if (extractedGlosses.length > 0 && lexiconCtx) {
          lexiconCtx.populateCardGlosses(extractedGlosses, res.updated_card_glosses)
        }

        const assistantMessage: DeckDocMessage = {
          role: 'assistant',
          content: res.answer,
          citation: res.doc_citation,
          extracted_terms:
            extractedGlosses.length > 0 ? extractedGlosses.map((g) => g.term) : undefined,
        }
        setQaHistory([...updatedHistory, assistantMessage])

        if (res.available_models && res.available_models.length > 0) {
          setAvailableModels(res.available_models)
        }
        if (res.model_used && !activeModel && !selectedModel) {
          setSelectedModel(res.model_used)
        }
      } catch (err: any) {
        setQaError(
          err?.message ||
            `Failed to get answer from ${targetModel || 'selected model'}.`
        )
      } finally {
        setIsAskingQuestion(false)
        setTimeout(() => {
          qaThreadEndRef.current?.scrollIntoView({ behavior: 'smooth' })
        }, 50)
      }
    },
    [
      activeModel,
      activeQaSnippet,
      cardId,
      code,
      context,
      deckId,
      docSearchResult?.selectedSnippet,
      executionSummary,
      isAskingQuestion,
      language,
      lexiconCtx,
      qaHistory,
      qaInput,
      revealed,
      selectedModel,
      selectedText,
      setQaHistory,
      userCode,
      userTestCode,
    ]
  )

  const handleTriggerAskLlm = useCallback(
    (codeToAsk?: string) => {
      let text = (codeToAsk ?? selectedText).trim()
      if (!text && textareaRef.current) {
        const start = textareaRef.current.selectionStart ?? 0
        const end = textareaRef.current.selectionEnd ?? 0
        if (start !== end) {
          text = code.slice(Math.min(start, end), Math.max(start, end)).trim()
        }
      }
      if (!text) {
        const lineList = code.split('\n')
        text = (lineList[cursorLine - 1] ?? '').trim()
      }
      if (text) {
        setActiveQaSnippet(text)
      }
      setIsQaOpen(true)
      if (isPoppedOut && popupWindowRef.current && !popupWindowRef.current.closed) {
        popupWindowRef.current.focus()
      }
      setTimeout(() => {
        qaInputRef.current?.focus()
      }, 50)
    },
    [code, cursorLine, isPoppedOut, selectedText]
  )

  const saveGlossToActiveCard = useCallback(
    async (gloss: LexiconGlossItem) => {
      if (!lexiconCtx) return
      const cardId = lexiconCtx.activeDeckContext?.cardId
      if (cardId && !lexiconCtx.hasMarginListener) {
        const updated = await api.addCardLexiconGloss(cardId, gloss)
        lexiconCtx.populateCardGlosses([gloss], updated.lexicon_glosses)
      } else {
        lexiconCtx.populateCardGlosses([gloss])
      }
    },
    [lexiconCtx]
  )

  const handleDefineSelection = useCallback(
    (codeToDefine?: string) => {
      if (!lexiconCtx) return
      let text = (codeToDefine ?? selectedText).trim()
      if (!text && textareaRef.current) {
        const start = textareaRef.current.selectionStart ?? 0
        const end = textareaRef.current.selectionEnd ?? 0
        if (start !== end) {
          text = code.slice(Math.min(start, end), Math.max(start, end)).trim()
        }
      }
      if (!text || text.length > 80 || text.includes('\n')) return

      const lineList = code.split('\n')
      const startLine = Math.max(0, cursorLine - 3)
      const endLine = Math.min(lineList.length, cursorLine + 2)
      const snippetCtx = lineList.slice(startLine, endLine).join('\n').trim()
      const fullCtx = [context || '', snippetCtx ? `Code context:\n${snippetCtx}` : '']
        .filter(Boolean)
        .join('\n\n')

      setSelectedText('')
      setFloatingPillPos(null)
      lexiconCtx.openLexicon(text, fullCtx || text, null, lexiconCtx.activeDeckContext)
    },
    [code, context, cursorLine, lexiconCtx, selectedText]
  )

  const handleDockBack = useCallback(() => {
    if (popupWindowRef.current && !popupWindowRef.current.closed) {
      popupWindowRef.current.close()
    }
    popupWindowRef.current = null
    setIsPoppedOut(false)
  }, [])

  const handlePopOut = useCallback(() => {
    setIsQaOpen(true)

    if (popupWindowRef.current && !popupWindowRef.current.closed) {
      popupWindowRef.current.focus()
      setIsPoppedOut(true)
      return
    }

    const popup = window.open(
      '',
      'ArsMemoriaeAssistantWindow',
      'width=940,height=780,left=150,top=100,resizable=yes,scrollbars=yes'
    )
    if (!popup) {
      alert('Popup was blocked by your browser. Please allow popups for Ars-Memoriae to use the secondary monitor window.')
      return
    }

    popup.document.open()
    popup.document.write('<!DOCTYPE html><html><head></head><body></body></html>')
    popup.document.close()
    popup.document.title = 'Ars Memoriae · Local LLM & Docs'
    popup.document.head.innerHTML = ''

    // Copy application stylesheets and styles
    Array.from(document.querySelectorAll('link[rel="stylesheet"], style')).forEach((node) => {
      popup.document.head.appendChild(node.cloneNode(true))
    })

    // Add layout baseline styles
    const baseStyle = popup.document.createElement('style')
    baseStyle.textContent = `
      html, body {
        height: 100%;
        margin: 0;
        padding: 0;
        background-color: #0b1411;
        color: #d1fae5;
        font-family: ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
        overflow: hidden;
      }
      #ars-popout-root {
        height: 100%;
        display: flex;
        flex-direction: column;
      }
    `
    popup.document.head.appendChild(baseStyle)

    popup.document.body.className = 'bg-[#0b1411] text-emerald-100 m-0 p-0 font-sans h-screen flex flex-col select-auto'
    popup.document.body.style.backgroundColor = '#0b1411'
    popup.document.body.style.color = '#d1fae5'

    const container = popup.document.createElement('div')
    container.id = 'ars-popout-root'
    container.className = 'flex flex-col flex-1 h-screen overflow-hidden'
    popup.document.body.appendChild(container)

    popup.addEventListener('beforeunload', () => {
      setIsPoppedOut(false)
      popupWindowRef.current = null
    })

    // Enable Escape or Alt+W to dock back from inside the popup window
    popup.document.addEventListener('keydown', (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        e.preventDefault()
        handleDockBack()
      } else if (e.altKey && (e.key === 'w' || e.key === 'W')) {
        e.preventDefault()
        handleDockBack()
      }
    })

    popupWindowRef.current = popup
    setIsPoppedOut(true)
  }, [handleDockBack])

  // Clean up popup window on unmount or main window unload
  useEffect(() => {
    const handleUnload = () => {
      if (popupWindowRef.current && !popupWindowRef.current.closed) {
        popupWindowRef.current.close()
      }
    }
    window.addEventListener('beforeunload', handleUnload)
    return () => {
      window.removeEventListener('beforeunload', handleUnload)
      if (popupWindowRef.current && !popupWindowRef.current.closed) {
        popupWindowRef.current.close()
      }
    }
  }, [])

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

  const { renderedCode, highlightedHtml } = useMemo(() => {
    if (hintOnly && hintOnlyLine && hintOnlyLine > 0) {
      const lines = code.split('\n')
      const targetIdx = hintOnlyLine - 1

      const htmlParts: string[] = []
      const maskedLines: string[] = []

      lines.forEach((line, idx) => {
        if (idx === targetIdx) {
          // This is the active hint line!
          const highlightedLine = highlightLeetCode(line)
          htmlParts.push(
            `<span style="background-color: rgba(245, 158, 11, 0.22); color: #fef08a; box-shadow: -4px 0 0 rgba(245, 158, 11, 0.22), -7px 0 0 #f59e0b; display: inline-block; vertical-align: top; min-height: 24px; min-width: 100%; border-radius: 2px;" title="💡 Hint for line ${hintOnlyLine}">${highlightedLine}</span>`
          )
          maskedLines.push(line)
        } else {
          // Indentation whitespace preserved, rest masked
          const indentMatch = line.match(/^(\s*)/)
          const indent = indentMatch ? indentMatch[1] : ''
          const nonWs = line.slice(indent.length)
          if (!nonWs) {
            htmlParts.push('')
            maskedLines.push('')
          } else {
            const maskedCharCount = Math.min(Math.max(nonWs.length, 8), 32)
            const maskedText = '•'.repeat(maskedCharCount)
            htmlParts.push(
              `${escapeHtml(indent)}<span style="opacity: 0.22; color: #94a3b8; user-select: none;">${maskedText}</span>`
            )
            maskedLines.push(indent + maskedText)
          }
        }
      })

      return {
        renderedCode: maskedLines.join('\n'),
        highlightedHtml: htmlParts.join('\n'),
      }
    }

    if (diffSegments && diffSegments.length > 0) {
      let html = ''
      for (const seg of diffSegments) {
        html += renderDiffSegment(seg.text, seg.type)
      }
      return { renderedCode: code, highlightedHtml: html }
    }
    if (activeLogicWarning && activeLogicWarning.lineNumber > 0) {
      const lines = code.split('\n')
      const targetIdx = activeLogicWarning.lineNumber - 1
      const htmlParts: string[] = []
      lines.forEach((line, idx) => {
        const highlighted = highlightLeetCode(line)
        if (idx === targetIdx) {
          htmlParts.push(
            `<span style="background-color: rgba(244, 63, 94, 0.16); box-shadow: inset 0 -2px 0 rgba(244, 63, 94, 0.7); display: inline-block; vertical-align: top; min-height: 24px; min-width: 100%; border-radius: 2px;" title="⚠️ ${escapeHtml(activeLogicWarning.message)}">${highlighted}</span>`
          )
        } else {
          htmlParts.push(highlighted)
        }
      })
      return { renderedCode: code, highlightedHtml: htmlParts.join('\n') }
    }

    if (targetLineNumbers && targetLineNumbers.size > 0) {
      const { r, g, b } = hexToRgb(targetHighlightColor || DEFAULT_TARGET_HIGHLIGHT_COLOR)
      const lines = code.split('\n')
      const htmlParts: string[] = []
      lines.forEach((line, idx) => {
        const lineNum = idx + 1
        const isTarget = targetLineNumbers.has(lineNum)
        const highlighted = highlightLeetCode(line)
        if (isTarget) {
          htmlParts.push(
            `<span style="background-color: rgba(${r}, ${g}, ${b}, 0.16); box-shadow: -4px 0 0 rgba(${r}, ${g}, ${b}, 0.16), -7px 0 0 rgb(${r}, ${g}, ${b}); display: inline-block; vertical-align: top; min-height: 24px; min-width: 100%; border-radius: 2px;" title="Expected solution code (to produce in Solution)">${highlighted}</span>`
          )
        } else if (focusTargetCode) {
          htmlParts.push(
            `<span style="opacity: 0.45; filter: contrast(80%);">${highlighted}</span>`
          )
        } else {
          htmlParts.push(highlighted)
        }
      })
      return { renderedCode: code, highlightedHtml: htmlParts.join('\n') }
    }

    return { renderedCode: code, highlightedHtml: highlightLeetCode(code) }
  }, [code, diffSegments, hintOnly, hintOnlyLine, activeLogicWarning, targetLineNumbers, focusTargetCode, targetHighlightColor])

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

  useEffect(() => {
    handleScroll()
  }, [code, highlightedHtml, resolvedHeight, handleScroll])

  useEffect(() => {
    const el = textareaRef.current || editorContainerRef.current
    if (!el || typeof ResizeObserver === 'undefined') return
    const ro = new ResizeObserver(() => {
      handleScroll()
    })
    ro.observe(el)
    return () => ro.disconnect()
  }, [handleScroll])

  // Handle Tab, Shift+Tab, Enter (auto-indent), auto-closing brackets, and shortcuts
  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    // Escape to dismiss doc search tray, QA panel, or line hint
    if (e.key === 'Escape') {
      if (docSearchResult || isSearchingDocs || docSearchError || isQaOpen) {
        e.preventDefault()
        e.stopPropagation()
        setDocSearchResult(null)
        setDocSearchError(null)
        setDocAddStatus('idle')
        setDocAddError(null)
        setIsSearchingDocs(false)
        setIsQaOpen(false)
        setActiveQaSnippet('')
        if (!onSharedQaHistoryChange) {
          setLocalQaHistory([])
        }
        setDismissedQaPrompts({})
        setQaInput('')
        setQaError(null)
        return
      }
      if (activeLineHint || lineHintLoading) {
        e.preventDefault()
        e.stopPropagation()
        onDismissLineHint?.()
        return
      }
    }

    // Alt + D or Alt + E: Search Deck Documentation for selection
    if (e.altKey && (e.key === 'd' || e.key === 'D' || e.key === 'e' || e.key === 'E')) {
      e.preventDefault()
      e.stopPropagation()
      void triggerDocSearch()
      return
    }

    // Alt + Q: Directly Ask Local LLM about selection (using docs + pre-training)
    if (e.altKey && (e.key === 'q' || e.key === 'Q')) {
      e.preventDefault()
      e.stopPropagation()
      handleTriggerAskLlm()
      return
    }

    // Alt + L: Define highlighted token/snippet via Concordance & AI Lexicon
    if (e.altKey && (e.key === 'l' || e.key === 'L') && lexiconCtx) {
      e.preventDefault()
      e.stopPropagation()
      handleDefineSelection()
      return
    }

    // Alt + W: Toggle separate window / pop-out for second monitor
    if (e.altKey && (e.key === 'w' || e.key === 'W')) {
      e.preventDefault()
      e.stopPropagation()
      if (isPoppedOut) {
        handleDockBack()
      } else {
        handlePopOut()
      }
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
          const newPos = Math.max(lineStart, selectionStart - 4)
          onChange(newValue)
          setTimeout(() => {
            textarea.selectionStart = newPos
            textarea.selectionEnd = newPos
            updateCursorPosition(newValue, newPos)
          }, 0)
        }
      } else {
        const newValue = value.slice(0, selectionStart) + tabSpaces + value.slice(selectionEnd)
        const newPos = selectionStart + 4
        onChange(newValue)
        setTimeout(() => {
          textarea.selectionStart = textarea.selectionEnd = newPos
          updateCursorPosition(newValue, newPos)
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
      const newPos = selectionStart + insertText.length
      onChange(newValue)
      setTimeout(() => {
        textarea.selectionStart = textarea.selectionEnd = newPos
        updateCursorPosition(newValue, newPos)
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
        const newStart = selectionStart + 1
        const newEnd = selectionEnd + 1
        onChange(newValue)
        setTimeout(() => {
          textarea.selectionStart = newStart
          textarea.selectionEnd = newEnd
          updateCursorPosition(newValue, newStart)
        }, 0)
        return
      }

      if (e.key === '(' || e.key === '[' || e.key === '{') {
        e.preventDefault()
        const newValue =
          value.slice(0, selectionStart) + e.key + closeChar + value.slice(selectionEnd)
        const newPos = selectionStart + 1
        onChange(newValue)
        setTimeout(() => {
          textarea.selectionStart = textarea.selectionEnd = newPos
          updateCursorPosition(newValue, newPos)
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
        const newPos = selectionStart - 1
        onChange(newValue)
        setTimeout(() => {
          textarea.selectionStart = textarea.selectionEnd = newPos
          updateCursorPosition(newValue, newPos)
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

  const langObj = SUPPORTED_LANGUAGES.find((l) => l.id === language)
  const currentLangLabel = langObj ? langObj.label : language ? (language.charAt(0).toUpperCase() + language.slice(1)) : 'Code'

  const activeCardIdForLexicon = lexiconCtx?.activeDeckContext?.cardId
  useEffect(() => {
    setDocAddStatus('idle')
    setDocAddError(null)
    setDismissedQaPrompts({})
  }, [activeCardIdForLexicon])

  const docSnippetTerm = (docSearchResult?.selectedSnippet || '').trim()
  const docHasSubstantiveDefinition = Boolean(
    docSearchResult &&
      docSnippetTerm.length >= 1 &&
      docSnippetTerm.length <= 80 &&
      !docSearchResult.explanation?.includes('No documentation attached to this deck') &&
      (docSearchResult.occams_razor ||
        docSearchResult.explanation ||
        docSearchResult.verbatim_passage ||
        docSearchResult.doc_citation)
  )
  const isDocSnippetInCard =
    docAddStatus === 'added' ||
    isTermInGlosses(lexiconCtx?.activeDeckContext?.existingGlosses, docSnippetTerm)

  const handleAddDocResultToCard = async () => {
    if (!docSearchResult || !docSnippetTerm) return
    setDocAddStatus('saving')
    setDocAddError(null)
    const cleanDef = (
      docSearchResult.occams_razor ||
      docSearchResult.socratic_insight ||
      docSearchResult.explanation ||
      ''
    )
      .replace(/\*\*→[^*]+\*\*/g, '')
      .replace(/\s+/g, ' ')
      .trim()
      .slice(0, 420)
    const ctxParts = [
      docSearchResult.doc_citation ? `Cited: ${docSearchResult.doc_citation}` : '',
      docSearchResult.socratic_insight && docSearchResult.occams_razor
        ? docSearchResult.socratic_insight
        : '',
    ].filter(Boolean)
    try {
      await saveGlossToActiveCard({
        term: docSnippetTerm,
        definition: cleanDef || docSnippetTerm,
        domain: language || 'Code',
        context_explanation: ctxParts.join(' — ') || undefined,
        example: docSearchResult.verbatim_passage?.slice(0, 240) || undefined,
        source: docSearchResult.doc_citation
          ? `Deck Docs (${docSearchResult.doc_citation})`
          : 'Deck Docs (Local LLM)',
        pinned_at: new Date().toISOString(),
      })
      setDocAddStatus('added')
    } catch (err) {
      setDocAddStatus('idle')
      setDocAddError(err instanceof Error ? err.message : 'Failed to save definition')
    }
  }

  const getFallbackQaCandidate = (tIdx: number) => {
    const prevTurn = qaHistory[tIdx - 1]
    const prevQ = prevTurn?.role === 'user' ? prevTurn.content : ''
    const raw = (activeQaSnippet || selectedText || prevQ || 'Concept').trim()
    return {
      prevQ,
      term: raw.length > 48 ? raw.slice(0, 48).trim() : raw,
    }
  }

  const handleAddQaTurnToCard = async (tIdx: number, turn: DeckDocMessage) => {
    if (!lexiconCtx) return
    setSavingQaPromptIdx(tIdx)
    try {
      const { prevQ, term: fallbackTerm } = getFallbackQaCandidate(tIdx)
      const extracted = extractTermDefinitionsFromQA({
        question: prevQ,
        answer: turn.content,
        selectedCode: activeQaSnippet || selectedText,
        docCitation: turn.citation,
        language,
      })
      if (extracted.length > 0) {
        for (const item of extracted) {
          await saveGlossToActiveCard(item)
        }
        setQaHistory((prev) =>
          prev.map((m, i) =>
            i === tIdx ? { ...m, extracted_terms: extracted.map((g) => g.term) } : m,
          ),
        )
      } else {
        await saveGlossToActiveCard({
          term: fallbackTerm,
          definition: turn.content.replace(/\s+/g, ' ').slice(0, 420),
          domain: language || 'Code',
          context_explanation: turn.citation ? `Cited: ${turn.citation}` : undefined,
          source: 'Ask Local LLM',
          pinned_at: new Date().toISOString(),
        })
        setQaHistory((prev) =>
          prev.map((m, i) => (i === tIdx ? { ...m, extracted_terms: [fallbackTerm] } : m)),
        )
      }
    } finally {
      setSavingQaPromptIdx(null)
    }
  }

  const renderDrawerContent = (inPopup = false) => {
    const activeSnippet = docSearchResult?.selectedSnippet || activeQaSnippet
    const activeModelDisplay = getModelDisplayInfo(
      selectedModel || activeModel || docSearchResult?.model_used || 'Qwen 2.5 Coder',
    )

    return (
      <div
        className={`flex flex-col min-h-0 overflow-hidden ${
          inPopup ? 'flex-1 h-full select-text bg-[#0b1411]' : 'min-w-0 flex-1'
        }`}
      >
        {/* Pinned Full-Width Drawer Header */}
        <div className="shrink-0 flex items-center justify-between gap-2 px-3 py-2 border-b border-emerald-500/20 bg-[#08100d]">
          <div className="flex items-center gap-2 min-w-0 flex-1 overflow-x-auto no-scrollbar">
            <span className="flex items-center gap-1.5 font-semibold text-xs tracking-wide whitespace-nowrap shrink-0">
              {docSearchResult ? (
                <>
                  <span className="text-emerald-400">📄</span>
                  <span className="text-emerald-200 font-bold">Deck Docs</span>
                  {docSearchResult?.doc_citation && (
                    <span className="px-1.5 py-0.5 rounded bg-emerald-950 text-emerald-300 font-mono text-[10px] font-semibold border border-emerald-500/40">
                      {docSearchResult.doc_citation}
                    </span>
                  )}
                </>
              ) : (
                <>
                  <span className="text-sky-400">💬</span>
                  <span className="text-sky-200 font-bold">Ask Local LLM</span>
                  <span className="hidden sm:inline px-1.5 py-0.5 rounded bg-sky-950/90 text-sky-300 font-sans text-[10px] font-semibold border border-sky-500/35">
                    Docs + Pre-training
                  </span>
                </>
              )}
              {inPopup && (
                <span className="px-1.5 py-0.5 rounded bg-sky-900/60 text-sky-200 font-mono text-[10px] border border-sky-500/30">
                  External Window
                </span>
              )}
            </span>

            {(availableModels.length > 0 || selectedModel || activeModel) && (
              <div className="flex items-center gap-1 shrink-0">
                <select
                  value={selectedModel || activeModel || docSearchResult?.model_used || availableModels[0] || ''}
                  onChange={(e) => {
                    const newModel = e.target.value
                    setSelectedModel(newModel)
                    onActiveModelChange?.(newModel)
                    if (docSearchResult?.selectedSnippet) {
                      void triggerDocSearch(docSearchResult.selectedSnippet, newModel)
                    }
                  }}
                  title="Select Local LLM / Documentation model"
                  className="h-6 rounded bg-[#0c3124] px-2 text-[10px] font-mono text-emerald-200 border border-emerald-500/30 focus:outline-none cursor-pointer"
                >
                  {Array.from(
                    new Set([
                      ...(activeModel ? [activeModel] : []),
                      ...(selectedModel ? [selectedModel] : []),
                      ...availableModels,
                    ]),
                  ).map((m) => (
                    <option key={m} value={m} className="bg-[#09221a] text-slate-200">
                      {getModelDisplayInfo(m).label}
                    </option>
                  ))}
                </select>
              </div>
            )}
          </div>

          {/* Header Action Controls */}
          <div className="flex items-center gap-1 shrink-0">
            {!docSearchResult && !isSearchingDocs && (activeQaSnippet || selectedText) && (
              <button
                type="button"
                onClick={() => void triggerDocSearch(activeQaSnippet || selectedText)}
                title="Search attached deck documentation for this snippet (Alt+D)"
                className="h-6 rounded px-2 text-[11px] font-medium text-emerald-300 hover:text-emerald-100 hover:bg-emerald-500/20 transition cursor-pointer flex items-center gap-1 whitespace-nowrap"
              >
                <span>📄</span>
                <span className="hidden sm:inline">Search Docs</span>
              </button>
            )}
            {docSearchResult && !isSearchingDocs && (
              <>
                <button
                  type="button"
                  onClick={handleCopyDocResult}
                  title="Copy document findings"
                  className="h-6 rounded px-2 text-[11px] font-medium text-emerald-300 hover:text-emerald-100 hover:bg-emerald-500/20 transition cursor-pointer whitespace-nowrap"
                >
                  {copiedDocResult ? 'Copied' : 'Copy'}
                </button>
                <button
                  type="button"
                  onClick={() => void triggerDocSearch(docSearchResult.selectedSnippet)}
                  title="Re-search documentation"
                  className="h-6 rounded px-2 text-[11px] font-medium text-emerald-300 hover:text-emerald-100 hover:bg-emerald-500/20 transition cursor-pointer whitespace-nowrap"
                >
                  Re-search
                </button>
              </>
            )}
            {qaHistory.length > 0 && (
              <button
                type="button"
                onClick={() => {
                  setQaHistory([])
                  setDismissedQaPrompts({})
                }}
                title="Clear conversation thread for this card"
                className="h-6 rounded px-2 text-[10px] font-medium text-emerald-400/75 hover:text-emerald-200 hover:bg-emerald-500/15 transition cursor-pointer whitespace-nowrap"
              >
                Clear Thread
              </button>
            )}

            {!inPopup ? (
              <button
                type="button"
                onClick={handlePopOut}
                title="Pop out to separate window for second monitor (Alt+W)"
                className="h-6 rounded px-2 text-[11px] font-medium text-sky-300 hover:text-sky-100 hover:bg-sky-500/20 transition cursor-pointer flex items-center gap-1 border border-sky-500/30 whitespace-nowrap"
              >
                <span>⧉</span>
                <span className="hidden sm:inline">Pop Out</span>
              </button>
            ) : (
              <button
                type="button"
                onClick={handleDockBack}
                title="Dock back to main editor window (Alt+W)"
                className="h-6 rounded px-2 text-[11px] font-medium text-amber-300 hover:text-amber-100 hover:bg-amber-500/20 transition cursor-pointer flex items-center gap-1 border border-amber-500/30 whitespace-nowrap"
              >
                <span>⤓</span>
                <span>Dock Back</span>
              </button>
            )}

            <button
              type="button"
              onClick={() => {
                if (inPopup) {
                  handleDockBack()
                }
                setDocSearchResult(null)
                setDocSearchError(null)
                setDocAddStatus('idle')
                setDocAddError(null)
                setIsSearchingDocs(false)
                setIsQaOpen(false)
                setActiveQaSnippet('')
                if (!onSharedQaHistoryChange) {
                  setLocalQaHistory([])
                }
                setDismissedQaPrompts({})
                setQaInput('')
                setQaError(null)
              }}
              title="Dismiss drawer (Escape)"
              className="h-6 w-6 rounded flex items-center justify-center text-slate-400 hover:text-slate-200 hover:bg-white/10 transition cursor-pointer text-sm leading-none"
            >
              &times;
            </button>
          </div>
        </div>

        {/* Optional Selected Snippet Focus Strip */}
        {activeSnippet && (
          <div className="shrink-0 px-3 py-1 bg-black/45 border-b border-emerald-500/15 flex items-center gap-2 text-[10px]">
            <span className="text-emerald-400/75 uppercase tracking-wider font-semibold shrink-0">Focus:</span>
            <code className="font-mono text-emerald-200/90 truncate" title={activeSnippet}>
              {activeSnippet.replace(/\s+/g, ' ').slice(0, 140)}
              {activeSnippet.length > 140 ? '…' : ''}
            </code>
          </div>
        )}

        {/* Single Scrollable Drawer Content Area */}
        <div className="flex-1 min-h-0 overflow-y-auto px-3 py-2.5 space-y-2.5 font-sans">
          {isSearchingDocs ? (
            <div className="flex items-center gap-2 text-emerald-300/85 text-xs py-2">
              <span className="inline-block w-3.5 h-3.5 rounded-full border-2 border-emerald-400 border-t-transparent animate-spin shrink-0" />
              <span>
                Searching deck documentation for selected code using {activeModelDisplay.label}…
              </span>
            </div>
          ) : docSearchError ? (
            <div className="p-2.5 rounded-lg bg-rose-950/40 border border-rose-500/40 text-rose-300 text-xs flex items-center justify-between gap-2">
              <span>{docSearchError}</span>
              <button
                type="button"
                onClick={() => void triggerDocSearch()}
                className="underline font-semibold shrink-0 hover:text-rose-100 cursor-pointer"
              >
                Retry
              </button>
            </div>
          ) : (
            <>
              {!docSearchResult && isQaOpen && qaHistory.length === 0 && (
                <div className="p-2.5 rounded-lg bg-sky-950/30 border border-sky-500/25 text-sky-200 text-xs flex items-start gap-2">
                  <span className="text-base select-none leading-none mt-0.5">🤖</span>
                  <div className="min-w-0">
                    <p className="font-medium text-sky-100">Ask Local LLM Directly</p>
                    <p className="text-[11px] text-sky-300/80 leading-relaxed">
                      Grounded in the card prompt, your live code, unit tests, execution output, attached course docs, and pre-trained programming knowledge.
                    </p>
                  </div>
                </div>
              )}

              {docSearchResult?.explanation && renderDocExplanation(docSearchResult.explanation)}

              {lexiconCtx?.activeDeckContext?.cardId &&
                docHasSubstantiveDefinition &&
                (isDocSnippetInCard || docAddStatus !== 'dismissed') && (
                  <AddToDefinitionsPrompt
                    term={docSnippetTerm}
                    alreadyAdded={isDocSnippetInCard}
                    saving={docAddStatus === 'saving'}
                    error={docAddError}
                    compact={true}
                    onConfirm={() => void handleAddDocResultToCard()}
                    onDismiss={() => setDocAddStatus('dismissed')}
                  />
                )}

              {docSearchResult?.doc_matches && docSearchResult.doc_matches.length > 0 && (
                <div className="pt-2 border-t border-emerald-500/20">
                  <button
                    type="button"
                    onClick={() => setShowDocMatches(!showDocMatches)}
                    className="flex items-center gap-1.5 text-[11px] font-medium text-emerald-300/80 hover:text-emerald-200 transition cursor-pointer py-0.5"
                  >
                    <span className="text-[9px]">{showDocMatches ? '▼' : '▶'}</span>
                    <span>
                      {showDocMatches ? 'Hide' : 'Show'} Matched Course Excerpt
                      {docSearchResult.doc_matches.length > 1 ? 's' : ''} ({docSearchResult.doc_matches.length})
                    </span>
                  </button>
                  {showDocMatches && (
                    <div className="mt-2 space-y-2">
                      {docSearchResult.doc_matches.map((m, mIdx) => (
                        <div
                          key={m.extract_id || mIdx}
                          className="p-2 rounded bg-black/60 border border-emerald-500/20 text-slate-300 text-[11px] font-mono leading-relaxed"
                        >
                          <div className="flex items-center justify-between text-emerald-400 font-semibold mb-1 text-[10px]">
                            <span>{m.source_title}</span>
                            <span className="bg-emerald-950 px-1.5 py-0.2 rounded border border-emerald-500/30">
                              {m.locator || 'General'}
                            </span>
                          </div>
                          <div className="text-slate-300 whitespace-pre-wrap font-mono text-[11px] line-clamp-4 hover:line-clamp-none transition">
                            {m.content}
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )}

              {qaHistory.length > 0 && (
                <div className="space-y-2.5 pt-1">
                  <div className="flex items-center justify-between text-[10px] text-emerald-400/75 font-semibold uppercase tracking-wider">
                    <span>
                      💬 {docSearchResult ? 'Follow-up Discussion' : 'Discussion'} ·{' '}
                      {isAntigravityModel(selectedModel || docSearchResult?.model_used) ? 'Antigravity' : 'Local'} ·{' '}
                      {activeModelDisplay.short}
                    </span>
                  </div>
                  {qaHistory.map((turn, tIdx) => {
                    const isUser = turn.role === 'user'
                    const fallbackCandidate = !isUser ? getFallbackQaCandidate(tIdx) : null
                    return (
                      <div
                        key={tIdx}
                        className={`rounded-lg p-2.5 shadow-sm text-xs ${
                          isUser
                            ? 'bg-black/60 border border-emerald-500/30 text-emerald-100 ml-4'
                            : 'bg-[#061811] border border-emerald-500/40 text-slate-100 mr-2'
                        }`}
                      >
                        <div className="flex items-center justify-between text-[10px] font-semibold mb-1">
                          <span className={isUser ? 'text-emerald-300' : 'text-emerald-400'}>
                            {isUser
                              ? '👤 You'
                              : `🤖 ${getModelDisplayInfo(selectedModel || docSearchResult?.model_used || 'Local LLM').label}`}
                          </span>
                          {turn.citation && !isUser ? (
                            <span className="px-1.5 py-0.2 rounded bg-black/60 text-emerald-300 font-mono text-[9px] border border-emerald-500/30">
                              📄 {turn.citation}
                            </span>
                          ) : !isUser ? (
                            <span className="px-1.5 py-0.2 rounded bg-sky-950/60 text-sky-300 font-sans text-[9px] border border-sky-500/30">
                              🧠 Pre-training
                            </span>
                          ) : null}
                        </div>
                        <div>
                          {isUser ? (
                            <p className="text-emerald-100/90 whitespace-pre-wrap font-sans">{turn.content}</p>
                          ) : (
                            <>
                              {renderFormattedMarkdown(turn.content)}
                              {turn.extracted_terms && turn.extracted_terms.length > 0 ? (
                                <div className="mt-2 pt-1.5 border-t border-emerald-500/20 flex items-center gap-1.5 flex-wrap text-[10px] text-emerald-300">
                                  <span className="font-semibold text-emerald-400">✓ Added to Card Lexicon:</span>
                                  {turn.extracted_terms.map((t, i) => (
                                    <code
                                      key={i}
                                      className="px-1 py-0.2 rounded bg-emerald-950/70 border border-emerald-500/30 font-mono text-emerald-200"
                                    >
                                      {t}
                                    </code>
                                  ))}
                                </div>
                              ) : lexiconCtx?.activeDeckContext?.cardId &&
                                fallbackCandidate &&
                                !dismissedQaPrompts[tIdx] ? (
                                <div className="mt-2 pt-1.5 border-t border-emerald-500/15">
                                  <AddToDefinitionsPrompt
                                    term={fallbackCandidate.term}
                                    saving={savingQaPromptIdx === tIdx}
                                    compact={true}
                                    onConfirm={() => void handleAddQaTurnToCard(tIdx, turn)}
                                    onDismiss={() =>
                                      setDismissedQaPrompts((prev) => ({ ...prev, [tIdx]: true }))
                                    }
                                  />
                                </div>
                              ) : lexiconCtx ? (
                                <div className="mt-2 pt-1.5 border-t border-emerald-500/15 flex justify-end">
                                  <button
                                    type="button"
                                    onClick={() => void handleAddQaTurnToCard(tIdx, turn)}
                                    className="text-[10px] text-sky-300/80 hover:text-sky-100 underline cursor-pointer transition"
                                    title="Extract or pin these definitions to the card's Concordance & Lexicon sidebar"
                                  >
                                    📌 Pin to Card Lexicon
                                  </button>
                                </div>
                              ) : null}
                            </>
                          )}
                        </div>
                      </div>
                    )
                  })}
                  <div ref={qaThreadEndRef} />
                </div>
              )}

              {isAskingQuestion && (
                <div className="flex items-center gap-2 text-emerald-300/80 text-xs py-1.5 px-2.5 rounded bg-emerald-950/40 border border-emerald-500/25">
                  <span className="inline-block w-3 h-3 rounded-full border-2 border-emerald-400 border-t-transparent animate-spin shrink-0" />
                  <span>Asking {activeModelDisplay.label}…</span>
                </div>
              )}

              {qaError && (
                <div className="p-2 rounded bg-rose-950/40 border border-rose-500/40 text-rose-300 text-xs flex items-center justify-between gap-2">
                  <span>{qaError}</span>
                  <button
                    type="button"
                    onClick={() => void handleAskQuestion()}
                    className="underline font-semibold shrink-0 hover:text-rose-100 cursor-pointer"
                  >
                    Retry
                  </button>
                </div>
              )}
            </>
          )}
        </div>

        {/* Pinned Bottom Input Form */}
        {!isSearchingDocs && !docSearchError && (
          <div className="shrink-0 border-t border-emerald-500/20 bg-[#08100d] px-3 py-2 space-y-1.5">
            {qaHistory.length === 0 && !isAskingQuestion && (
              <div className="flex items-center flex-wrap gap-1.5">
                <span className="text-[10px] text-emerald-400/70 font-medium mr-0.5">Quick:</span>
                {promptSuggestions.map((prompt) => (
                  <button
                    key={prompt}
                    type="button"
                    onClick={() => void handleAskQuestion(prompt)}
                    className="rounded-full bg-black/60 hover:bg-emerald-950/80 border border-emerald-500/30 hover:border-emerald-400 px-2 py-0.5 text-[10px] text-emerald-300 hover:text-emerald-100 transition cursor-pointer"
                  >
                    {prompt}
                  </button>
                ))}
              </div>
            )}

            <form
              onSubmit={(e) => {
                e.preventDefault()
                void handleAskQuestion()
              }}
              className="flex items-center gap-2"
            >
              <input
                ref={qaInputRef}
                type="text"
                value={qaInput}
                onChange={(e) => setQaInput(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Escape') {
                    e.stopPropagation()
                    ;(e.target as HTMLElement).blur()
                  }
                }}
                placeholder="Ask a question about this card, your code, or docs..."
                disabled={isAskingQuestion}
                className="flex-1 min-w-0 rounded-lg bg-black/70 border border-emerald-500/35 px-3 py-1.5 text-xs text-slate-100 placeholder-emerald-400/40 focus:outline-none focus:border-emerald-400 focus:ring-1 focus:ring-emerald-400/50 transition font-sans"
              />
              <button
                type="submit"
                disabled={isAskingQuestion || !qaInput.trim()}
                className="rounded-lg bg-emerald-600 hover:bg-emerald-500 disabled:opacity-40 disabled:cursor-not-allowed px-3 py-1.5 text-xs font-semibold text-white shadow transition flex items-center gap-1.5 cursor-pointer shrink-0"
              >
                {isAskingQuestion ? (
                  <>
                    <span className="inline-block w-3 h-3 rounded-full border-2 border-white border-t-transparent animate-spin" />
                    <span>Asking…</span>
                  </>
                ) : (
                  <>
                    <span>Ask</span>
                    <span className="text-[10px] opacity-75">↵</span>
                  </>
                )}
              </button>
            </form>
          </div>
        )}
      </div>
    )
  }

  return (
    <div
      ref={editorContainerRef}
      className={`relative flex flex-col min-w-0 ${
        fillHeight ? 'h-full flex-1 min-h-0' : ''
      } ${
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
                  <span className="hidden sm:inline">Reset</span>
                </button>
              )}
              <button
                onClick={copyCode}
                title="Copy code"
                className="flex items-center gap-1 rounded px-2 py-1 text-[#8a8a8a] hover:bg-[#333333] hover:text-[#eff1f6] transition text-xs"
              >
                <span className="hidden sm:inline">Copy</span>
              </button>
            </div>
          </div>

          {/* Sub-Header: Language Selector, Explain Selection, Line Hint, Grade & Auto Indicator */}
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
                <span className="text-xs font-medium text-[#eff1f6]">{currentLangLabel}</span>
              )}

              <span className="text-xs text-[#8a8a8a] font-mono select-none">• Auto</span>
            </div>

            <div className="flex items-center gap-1.5 shrink-0">
              {/* Search Deck Docs Button */}
              <button
                type="button"
                onClick={() => void triggerDocSearch()}
                disabled={isSearchingDocs}
                className={`flex items-center gap-1 rounded px-2.5 py-1 text-xs font-medium transition cursor-pointer shrink-0 whitespace-nowrap ${
                  isSearchingDocs
                    ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/40 animate-pulse'
                    : selectedText.trim()
                    ? 'bg-emerald-600/30 text-emerald-200 border border-emerald-500/50 hover:bg-emerald-600/40 shadow-sm ring-1 ring-emerald-500/30'
                    : 'bg-[#182822] hover:bg-[#1e332b] text-emerald-300 border border-emerald-500/30 hover:text-emerald-200'
                }`}
                title="Search and ground selected code against attached deck documentation (Alt+D)"
              >
                <span className="text-emerald-400">📄</span>
                <span>{isSearchingDocs ? 'Searching Docs…' : selectedText.trim() ? 'Search Docs' : 'Deck Docs'}</span>
                <span className="text-[10px] text-emerald-400/60 font-mono hidden md:inline">(Alt+D)</span>
              </button>

              {/* Ask Local LLM Button */}
              <button
                type="button"
                onClick={() => handleTriggerAskLlm()}
                disabled={isAskingQuestion}
                className={`flex items-center gap-1 rounded px-2.5 py-1 text-xs font-medium transition cursor-pointer shrink-0 whitespace-nowrap ${
                  isAskingQuestion
                    ? 'bg-sky-500/20 text-sky-300 border border-sky-500/40 animate-pulse'
                    : isQaOpen
                    ? 'bg-sky-600/30 text-sky-200 border border-sky-500/50 hover:bg-sky-600/40 shadow-sm ring-1 ring-sky-500/30'
                    : selectedText.trim()
                    ? 'bg-sky-950 hover:bg-sky-900 text-sky-300 border border-sky-500/40 hover:text-sky-200 shadow-sm'
                    : 'bg-[#102433] hover:bg-[#163045] text-sky-300 border border-sky-500/30 hover:text-sky-200'
                }`}
                title="Directly ask local LLM a question about selected code using docs and pre-training (Alt+Q)"
              >
                <span className="text-sky-400">💬</span>
                <span>{isAskingQuestion ? 'Asking…' : 'Ask LLM'}</span>
                <span className="text-[10px] text-sky-400/60 font-mono hidden md:inline">(Alt+Q)</span>
              </button>

              {onRequestLineHint && !readOnly && (
                <button
                  type="button"
                  onClick={() => triggerLineHint()}
                  disabled={lineHintLoading}
                  className={`flex items-center gap-1 rounded px-2.5 py-1 text-xs font-medium transition cursor-pointer shrink-0 whitespace-nowrap ${
                    lineHintLoading
                      ? 'bg-amber-500/20 text-amber-300 border border-amber-500/40 animate-pulse'
                      : activeLineHint
                      ? 'bg-amber-500/25 text-amber-200 border border-amber-500/50 hover:bg-amber-500/35'
                      : 'bg-[#282828] hover:bg-[#333333] text-amber-300/90 border border-amber-500/30 hover:text-amber-200'
                  }`}
                  title={`Request Socratic Hint for line ${cursorLine} (Alt+H)`}
                >
                  <span>{lineHintLoading ? 'Thinking…' : 'Hint'}</span>
                  <span className="text-[10px] text-amber-400/60 font-mono hidden md:inline">(Alt+H)</span>
                </button>
              )}
              {cleanRefCode && onLogicGuardToggle && !readOnly && (
                <button
                  type="button"
                  onClick={() => onLogicGuardToggle(!logicGuardEnabled)}
                  className={`flex items-center gap-1 rounded px-2.5 py-1 text-xs font-medium transition cursor-pointer shrink-0 whitespace-nowrap ${
                    logicGuardEnabled
                      ? 'bg-rose-500/20 text-rose-300 border border-rose-500/40 hover:bg-rose-500/30'
                      : 'bg-[#282828] hover:bg-[#333333] text-slate-400 hover:text-slate-200 border border-white/10'
                  }`}
                  title={
                    logicGuardEnabled
                      ? 'Logic Guard is ON: Warns if a flawed code line is written (Click to disable)'
                      : 'Logic Guard is OFF: Click to enable real-time logic flaw detection'
                  }
                >
                  <span>{logicGuardEnabled ? '🛡️ Guard: ON' : '🛡️ Guard: OFF'}</span>
                </button>
              )}

              {onGradeSolution && !readOnly && (
                <button
                  type="button"
                  onClick={onGradeSolution}
                  disabled={grading || submitting || !code.trim()}
                  className={`flex items-center gap-1 rounded px-2.5 py-1 text-xs font-semibold transition cursor-pointer shrink-0 whitespace-nowrap ${
                    grading || submitting
                      ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/40 animate-pulse'
                      : 'bg-emerald-600/25 hover:bg-emerald-600/40 text-emerald-200 border border-emerald-500/50 shadow-sm'
                  }`}
                  title="Grade your solution with local Qwen 2.5 Coder 7B (Alt+G)"
                >
                  <span>{grading || submitting ? 'Grading…' : 'Grade'}</span>
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

      {/* Real-Time Logic Flaw Warning Banner */}
      {activeLogicWarning && (
        <div className="flex items-center justify-between gap-3 bg-gradient-to-r from-rose-950/90 via-[#260e14] to-rose-950/80 border-b border-rose-500/50 px-3.5 py-2 text-xs text-rose-200 animate-in fade-in slide-in-from-top-1 shadow-md shrink-0">
          <div className="flex items-center gap-2.5 min-w-0">
            <span className="text-base select-none shrink-0 text-rose-400">⚠️</span>
            <div className="min-w-0 flex items-center gap-2 flex-wrap">
              <span className="font-bold text-rose-300 whitespace-nowrap">
                Logic Flaw on Line {activeLogicWarning.lineNumber}:
              </span>
              <span className="text-rose-100">{activeLogicWarning.message}</span>
              {activeLogicWarning.suggestedFix && (
                <span className="text-rose-300/80 italic text-[11px]">
                  ({activeLogicWarning.suggestedFix})
                </span>
              )}
            </div>
          </div>
          <div className="flex items-center gap-2 shrink-0">
            <button
              type="button"
              onClick={() => jumpToLine(activeLogicWarning.lineNumber)}
              className="rounded bg-rose-600/30 hover:bg-rose-600/50 text-rose-200 border border-rose-400/50 px-2.5 py-1 text-xs font-semibold transition cursor-pointer flex items-center gap-1 shadow-sm"
              title={`Jump cursor back to line ${activeLogicWarning.lineNumber} to correct mistake`}
            >
              <span>↩ Go back & correct (Line {activeLogicWarning.lineNumber})</span>
            </button>
            <button
              type="button"
              onClick={() => {
                setActiveLogicWarning(null)
                onLogicWarningChange?.(null)
              }}
              className="rounded text-rose-400 hover:text-white hover:bg-rose-900/40 p-1 transition cursor-pointer text-sm"
              title="Dismiss warning"
            >
              ✕
            </button>
          </div>
        </div>
      )}

      {/* Editor Body with LeetCode Colors and Line Numbers */}
      <div
        className={`relative flex font-mono text-sm bg-[#1a1a1a] ${
          fillHeight ? 'flex-1 min-h-[140px]' : ''
        }`}
        style={fillHeight ? undefined : { height: resolvedHeight }}
      >
        {/* Line Numbers Gutter */}
        <div
          ref={lineNumbersRef}
          aria-hidden="true"
          className="select-none border-r border-[#2d2d2d] bg-[#1a1a1a] px-1.5 pt-3 pb-12 text-right font-mono text-xs text-[#858585] overflow-hidden leading-6"
          style={{ width: onRequestLineHint && !readOnly ? '56px' : '48px' }}
        >
          {Array.from({ length: lineCount }, (_, i) => {
            const lineNum = i + 1
            const isCurrent = lineNum === cursorLine
            const hasActiveHint = hintLineNumber === lineNum
            const isHintOnlyTarget = hintOnly && hintOnlyLine === lineNum
            const isLogicFlawed = activeLogicWarning?.lineNumber === lineNum
            const isTargetLine = Boolean(targetLineNumbers && targetLineNumbers.has(lineNum))
            const targetRgb = isTargetLine ? hexToRgb(targetHighlightColor || DEFAULT_TARGET_HIGHLIGHT_COLOR) : null
            return (
              <div
                key={lineNum}
                onClick={() => {
                  if (isLogicFlawed) {
                    jumpToLine(lineNum)
                  } else if (hintOnly && onHintOnlyLineChange) {
                    onHintOnlyLineChange(lineNum)
                  } else if (isTargetLine) {
                    jumpToLine(lineNum)
                  }
                }}
                style={
                  isTargetLine && targetRgb && !isLogicFlawed && !isHintOnlyTarget
                    ? {
                        backgroundColor: `rgba(${targetRgb.r}, ${targetRgb.g}, ${targetRgb.b}, 0.22)`,
                        color: `rgb(${Math.min(255, targetRgb.r + 70)}, ${Math.min(255, targetRgb.g + 70)}, ${Math.min(255, targetRgb.b + 70)})`,
                        borderRight: `2px solid rgb(${targetRgb.r}, ${targetRgb.g}, ${targetRgb.b})`,
                      }
                    : undefined
                }
                className={`group flex items-center justify-end gap-1 px-1 rounded transition-colors ${
                  isLogicFlawed
                    ? 'bg-rose-600/30 text-rose-200 font-bold border-r-2 border-rose-500 animate-pulse cursor-pointer'
                    : isHintOnlyTarget
                    ? 'bg-amber-500/30 text-amber-200 font-bold border-r-2 border-amber-400'
                    : hasActiveHint
                    ? 'bg-amber-500/20 text-amber-300 font-bold'
                    : isTargetLine
                    ? 'font-bold cursor-pointer'
                    : isCurrent
                    ? 'text-[#eff1f6] bg-[#2a2a2a]/60'
                    : hintOnly
                    ? 'text-slate-600 hover:text-amber-300 hover:bg-[#2a2a2a]/40 cursor-pointer'
                    : 'hover:text-[#ccc]'
                }`}
                title={
                  isLogicFlawed
                    ? `⚠️ Logic flaw on line ${lineNum}: ${activeLogicWarning.message} (Click to jump back)`
                    : hintOnly
                    ? isHintOnlyTarget
                      ? `💡 Active Hint (Line ${lineNum})`
                      : `Click to view hint for line ${lineNum}`
                    : isTargetLine
                    ? `Expected code line ${lineNum} (Click to jump)`
                    : undefined
                }
              >
                {isTargetLine && !isLogicFlawed && !isHintOnlyTarget && (
                  <span
                    className="text-[9px] mr-0.5 select-none font-bold"
                    style={{ color: `rgb(${targetRgb!.r}, ${targetRgb!.g}, ${targetRgb!.b})` }}
                  >
                    ✦
                  </span>
                )}
                {isLogicFlawed && (
                  <span className="text-[10px] text-rose-400 select-none">⚠️</span>
                )}
                {hintOnly && isHintOnlyTarget && !isLogicFlawed && (
                  <span className="text-[10px] text-amber-400 select-none">💡</span>
                )}
                {onRequestLineHint && !readOnly && !hintOnly && !isLogicFlawed && (
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
                    ?
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
            className="pointer-events-none absolute inset-0 m-0 pt-3 pl-3 pr-12 pb-12 font-mono text-[13px] leading-6 overflow-hidden whitespace-pre font-normal text-[#eff1f6]"
            style={{
              fontFamily: 'Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace',
              tabSize: 4,
              fontVariantLigatures: 'none',
              letterSpacing: '0px',
              borderWidth: 0,
            }}
          />

          {/* Floating Action Pill on Selection: Search Docs + Ask LLM + Define */}
          {floatingPillPos && selectedText.trim().length > 0 && !isSearchingDocs && (
            <div
              style={{
                position: 'absolute',
                top: floatingPillPos.top,
                left: floatingPillPos.left,
                zIndex: 35,
                transform: 'translate(-50%, -100%)',
              }}
              className="animate-in fade-in zoom-in-95 duration-150 pointer-events-auto select-none flex flex-wrap justify-center max-w-[95%] items-center gap-1.5"
            >
              {/* Option 1: Search Attached Deck Docs */}
              <button
                type="button"
                onMouseDown={(e) => {
                  // Prevent mousedown from collapsing the textarea selection
                  e.preventDefault()
                }}
                onClick={(e) => {
                  e.preventDefault()
                  e.stopPropagation()
                  void triggerDocSearch(selectedText)
                }}
                className="flex items-center gap-1.5 rounded-full bg-[#09221a]/95 hover:bg-[#0e3328] text-emerald-200 border border-emerald-400/60 px-3 py-1 text-xs font-semibold shadow-2xl transition cursor-pointer ring-2 ring-emerald-500/25 hover:scale-105 backdrop-blur-md"
                title="Search attached deck documentation for this selected code (Alt+D)"
              >
                <span className="text-emerald-400 font-bold">📄</span>
                <span>Search Docs</span>
                <kbd className="px-1 py-0.2 rounded bg-black/60 text-[10px] font-mono text-emerald-300 border border-emerald-500/30">Alt+D</kbd>
              </button>

              {/* Option 2: Directly Ask Local LLM (Docs + Pre-training) */}
              <button
                type="button"
                onMouseDown={(e) => {
                  // Prevent mousedown from collapsing the textarea selection
                  e.preventDefault()
                }}
                onClick={(e) => {
                  e.preventDefault()
                  e.stopPropagation()
                  handleTriggerAskLlm(selectedText)
                }}
                className="flex items-center gap-1.5 rounded-full bg-[#0c1f2e]/95 hover:bg-[#122e44] text-sky-200 border border-sky-400/60 px-3 py-1 text-xs font-semibold shadow-2xl transition cursor-pointer ring-2 ring-sky-500/25 hover:scale-105 backdrop-blur-md"
                title="Directly ask local LLM a question about this code using docs and pre-training (Alt+Q)"
              >
                <span className="text-sky-400 font-bold">💬</span>
                <span>Ask LLM</span>
                <kbd className="px-1 py-0.2 rounded bg-black/60 text-[10px] font-mono text-sky-300 border border-sky-500/30">Alt+Q</kbd>
              </button>

              {/* Option 3: Define Selected Token / Term via AI Lexicon */}
              {lexiconCtx &&
                selectedText.trim().length <= 80 &&
                !selectedText.includes('\n') && (
                  <button
                    type="button"
                    onMouseDown={(e) => {
                      e.preventDefault()
                    }}
                    onClick={(e) => {
                      e.preventDefault()
                      e.stopPropagation()
                      handleDefineSelection(selectedText)
                    }}
                    className="flex items-center gap-1.5 rounded-full bg-[#1a1333]/95 hover:bg-[#271d4b] text-indigo-200 border border-indigo-400/60 px-3 py-1 text-xs font-semibold shadow-2xl transition cursor-pointer ring-2 ring-indigo-500/25 hover:scale-105 backdrop-blur-md"
                    title="Define highlighted code/term using the LLM Lexicon (Alt+L)"
                  >
                    <span className="text-indigo-300 font-bold">📖</span>
                    <span>Define</span>
                    <kbd className="px-1 py-0.2 rounded bg-black/60 text-[10px] font-mono text-indigo-300 border border-indigo-500/30">Alt+L</kbd>
                  </button>
                )}
            </div>
          )}

          {/* Textarea Input Overlay with Translucent Selection Highlight (No solid blue blur-out) */}
          <textarea
            ref={textareaRef}
            value={readOnly && hintOnly ? renderedCode : code}
            onChange={(e) => {
              const val = e.target.value
              const pos = e.target.selectionStart ?? 0
              onChange(val)
              updateCursorPosition(val, pos)
            }}
            onKeyUp={handleSelectOrMouseUp}
            onMouseUp={handleSelectOrMouseUp}
            onClick={() => updateCursorPosition()}
            onSelect={handleSelectOrMouseUp}
            onKeyDown={handleKeyDown}
            onScroll={handleScroll}
            readOnly={readOnly}
            spellCheck={false}
            autoCapitalize="off"
            autoComplete="off"
            autoCorrect="off"
            className="code-editor-textarea absolute inset-0 m-0 w-full h-full resize-none bg-transparent p-3 font-mono font-normal text-[13px] leading-6 text-transparent caret-white focus:outline-none whitespace-pre overflow-auto selection:bg-sky-500/35 selection:text-transparent"
            style={{
              fontFamily: 'Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace',
              tabSize: 4,
              fontVariantLigatures: 'none',
              letterSpacing: '0px',
              borderWidth: 0,
            }}
            placeholder={placeholder}
          />
        </div>
      </div>

      {/* If popped out, render into separate window portal for secondary monitor */}
      {isPoppedOut && popupWindowRef.current && (isSearchingDocs || docSearchResult || docSearchError || isQaOpen) && (
        createPortal(
          renderDrawerContent(true),
          popupWindowRef.current.document.getElementById('ars-popout-root') || popupWindowRef.current.document.body
        )
      )}

      {/* Main window docked banner when popped out */}
      {isPoppedOut && (isSearchingDocs || docSearchResult || docSearchError || isQaOpen) && (
        <div className="border-t border-sky-500/30 bg-[#07161f] px-4 py-2.5 text-xs text-sky-200 flex items-center justify-between shadow-lg animate-in fade-in">
          <div className="flex items-center gap-2 min-w-0">
            <span className="text-base select-none">⧉</span>
            <span className="font-semibold text-sky-100 whitespace-nowrap">Local LLM & Docs active in separate window</span>
            {(docSearchResult?.selectedSnippet || activeQaSnippet) && (
              <span className="font-mono text-[10px] text-sky-300 bg-black/60 px-2 py-0.5 rounded truncate max-w-xs border border-sky-500/25">
                {(docSearchResult?.selectedSnippet || activeQaSnippet).replace(/\s+/g, ' ').slice(0, 40)}…
              </span>
            )}
          </div>
          <div className="flex items-center gap-2 shrink-0">
            <button
              type="button"
              onClick={() => popupWindowRef.current?.focus()}
              className="rounded bg-sky-900/60 hover:bg-sky-800 text-sky-200 border border-sky-500/40 px-2.5 py-1 text-xs font-medium transition cursor-pointer"
            >
              Focus Window ↗
            </button>
            <button
              type="button"
              onClick={handleDockBack}
              className="rounded bg-black/50 hover:bg-black/70 text-slate-300 hover:text-white border border-white/10 px-2.5 py-1 text-xs font-medium transition cursor-pointer"
            >
              Dock Back ↩
            </button>
          </div>
        </div>
      )}

      {/* Inline Deck Documentation Search & Local LLM Q&A Callout Tray (when NOT popped out) */}
      {!isPoppedOut && (isSearchingDocs || docSearchResult || docSearchError || isQaOpen) && (
        <div
          className={`border-t border-emerald-500/30 bg-[#0b1411] text-xs text-emerald-100 shadow-2xl animate-in fade-in duration-200 flex flex-col min-h-0 overflow-hidden shrink-0 ${
            fillHeight ? 'max-h-[48%]' : 'max-h-[420px]'
          }`}
        >
          {renderDrawerContent(false)}
        </div>
      )}


      {/* Inline Socratic Line Hint Callout Tray */}
      {(lineHintLoading || activeLineHint) && (
        <div
          className={`border-t px-4 py-3 text-xs shadow-inner ${
            activeLineHint?.error
              ? 'border-rose-500/40 bg-rose-950/30 text-rose-200'
              : 'border-amber-500/30 bg-gradient-to-r from-[#201c13] via-[#1a1711] to-[#1c1812] text-amber-100'
          }`}
        >
          <div className="flex items-start justify-between gap-3">
            <div className="flex items-start gap-2.5 min-w-0 flex-1">
              <div className="space-y-1.5 min-w-0 flex-1">
                <div className="flex items-center flex-wrap gap-2">
                  <span
                    className={`font-semibold text-xs tracking-wide ${
                      activeLineHint?.error ? 'text-rose-300' : 'text-amber-300'
                    }`}
                  >
                    {activeLineHint?.error
                      ? `Socratic Hint Failed · Line ${hintLineNumber ?? cursorLine}`
                      : `Socratic Hint · Line ${hintLineNumber ?? cursorLine}`}
                  </span>
                  {hintTargetConcept && !activeLineHint?.error && (
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
                ) : activeLineHint?.error ? (
                  <p className="text-xs text-rose-200 leading-relaxed font-sans whitespace-pre-line">
                    {activeLineHint.error}
                  </p>
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
                  className={`rounded px-2 py-1 text-[11px] font-medium transition cursor-pointer flex items-center gap-1 ${
                    activeLineHint?.error
                      ? 'text-rose-200 hover:text-white hover:bg-rose-500/20'
                      : 'text-amber-300 hover:text-amber-100 hover:bg-amber-500/20'
                  }`}
                >
                  <span className="hidden sm:inline">
                    {activeLineHint?.error ? 'Retry' : 'Another Hint'}
                  </span>
                </button>
              )}
              {onDismissLineHint && (
                <button
                  type="button"
                  onClick={onDismissLineHint}
                  title="Dismiss hint (Escape)"
                  className="rounded p-1 text-slate-400 hover:text-slate-200 hover:bg-white/10 transition cursor-pointer text-xs"
                >
                  &times;
                </button>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Footer Info */}
      {!hideFooter && (
        <div
          className={`flex items-center justify-between border-t border-[#282828] bg-[#1e1e1e] px-3 text-[11px] text-[#8a8a8a] font-mono min-w-0 gap-2 overflow-hidden shrink-0 ${
            compactFooter ? 'h-7' : 'h-8'
          }`}
        >
          <div className="flex items-center gap-2 shrink-0 min-w-0">
            <span className="text-[#eff1f6] font-semibold whitespace-nowrap">
              Ln {cursorLine}, Col {cursorCol}
            </span>
            <span className="text-[#666666] hidden xl:inline whitespace-nowrap">
              • {lineCount}L / {code.length}C
            </span>
            {diffStats && (
              <div className="flex items-center gap-1.5 ml-1 font-mono text-[10px]">
                <span className="flex items-center gap-1 font-semibold text-emerald-300 bg-emerald-950/70 border border-emerald-500/40 px-1.5 py-0.5 rounded leading-none whitespace-nowrap">
                  <span className="inline-block h-1.5 w-1.5 rounded-full bg-emerald-400" />
                  Recalled {diffStats.matchedCount}/{diffStats.refWordCount} ({diffStats.recallPercent}%)
                </span>
                {diffStats.missingCount > 0 && (
                  <span className="flex items-center gap-1 font-semibold text-amber-300 bg-amber-950/70 border border-amber-500/40 px-1.5 py-0.5 rounded leading-none whitespace-nowrap">
                    <span className="inline-block h-1.5 w-1.5 rounded-full bg-amber-400" />
                    Missing {diffStats.missingCount}
                  </span>
                )}
              </div>
            )}
          </div>
          <div className="flex items-center gap-1.5 text-[10px] text-[#8a8a8a] shrink-0 overflow-hidden">
            {!compactFooter && onRequestLineHint && !readOnly && (
              <span className="text-amber-400/90 shrink-0 hidden md:inline whitespace-nowrap">
                <kbd className="rounded bg-[#282828] px-1 py-0.5 text-amber-300 border border-amber-500/30">Alt+H</kbd> Hint
              </span>
            )}
            {!compactFooter && onGradeSolution && !readOnly && (
              <span className="text-emerald-400/90 shrink-0 hidden md:inline whitespace-nowrap">
                <kbd className="rounded bg-[#282828] px-1 py-0.5 text-emerald-300 border border-emerald-500/30">Alt+G</kbd> Grade
              </span>
            )}
            {/* Search Deck Docs footer button */}
            <button
              type="button"
              onClick={() => void triggerDocSearch()}
              className={`cursor-pointer transition flex items-center gap-1 shrink-0 h-5 px-1.5 rounded border whitespace-nowrap ${
                selectedText.trim()
                  ? 'text-emerald-300 font-semibold bg-emerald-500/15 border-emerald-500/40'
                  : 'text-emerald-400/90 hover:text-emerald-200 border-transparent hover:bg-emerald-500/10'
              }`}
              title="Search attached deck documentation for selected code (Alt+D)"
            >
              <kbd className="rounded bg-[#282828] px-1 py-0.2 text-emerald-300 border border-emerald-500/30 leading-tight">Alt+D</kbd>
              <span>{selectedText.trim() ? 'Search Docs' : 'Docs'}</span>
            </button>
            {/* Ask Local LLM footer button */}
            <button
              type="button"
              onClick={() => handleTriggerAskLlm()}
              className={`cursor-pointer transition flex items-center gap-1 shrink-0 h-5 px-1.5 rounded border whitespace-nowrap ${
                isQaOpen || selectedText.trim()
                  ? 'text-sky-300 font-semibold bg-sky-500/15 border-sky-500/40'
                  : 'text-sky-400/90 hover:text-sky-200 border-transparent hover:bg-sky-500/10'
              }`}
              title="Directly ask local LLM a question about code using docs and pre-training (Alt+Q)"
            >
              <kbd className="rounded bg-[#282828] px-1 py-0.2 text-sky-300 border border-sky-500/30 leading-tight">Alt+Q</kbd>
              <span>Ask LLM</span>
            </button>
            {/* Pop Out / Dock separate window button */}
            <button
              type="button"
              onClick={isPoppedOut ? handleDockBack : handlePopOut}
              className={`cursor-pointer transition flex items-center gap-1 shrink-0 h-5 px-1.5 rounded border whitespace-nowrap ${
                isPoppedOut
                  ? 'text-sky-300 font-semibold bg-sky-500/15 border-sky-500/40'
                  : 'text-[#8a8a8a] hover:text-sky-200 border-transparent hover:bg-white/5'
              }`}
              title={isPoppedOut ? 'Dock assistant window back to main editor (Alt+W)' : 'Pop out assistant to separate window for 2nd monitor (Alt+W)'}
            >
              <kbd className="rounded bg-[#282828] px-1 py-0.2 text-slate-300 border border-slate-700 leading-tight">Alt+W</kbd>
              <span>{isPoppedOut ? 'Dock' : 'Pop Out'}</span>
            </button>
            <span className="shrink-0 whitespace-nowrap hidden sm:inline">
              <kbd className="rounded bg-[#282828] px-1 py-0.2 text-[#eff1f6]">Ctrl+↵</kbd> Run
            </span>
            {!compactFooter && (
              <span className="shrink-0 hidden xl:inline whitespace-nowrap">
                <kbd className="rounded bg-[#282828] px-1 py-0.2 text-[#eff1f6]">Ctrl+⇧+↵</kbd> Submit
              </span>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
