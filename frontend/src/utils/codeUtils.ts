/** Utility functions for detecting, cleaning, and formatting code in cards */

const CODE_FENCE_REGEX = /```(?:[a-zA-Z0-9_-]+)?\r?\n([\s\S]*?)\r?\n```/

export function looksLikeCode(text?: string | null): boolean {
  if (!text || typeof text !== 'string') return false
  const trimmed = text.trim()
  if (!trimmed) return false

  // Direct markdown fence
  if (trimmed.includes('```')) return true

  // Definition keywords with code punctuation
  const hasDefPattern = /(?:^|\n)\s*(?:export\s+)?(?:default\s+)?(?:async\s+)?(?:function\b|class\b|def\b|const\b|let\b|var\b|import\b|from\s+[\w.]+\s+import)/m.test(
    trimmed
  )
  if (hasDefPattern) {
    if (
      trimmed.includes('{') ||
      trimmed.includes('}') ||
      trimmed.includes('=>') ||
      trimmed.includes(';') ||
      trimmed.includes('return ') ||
      trimmed.includes('():') ||
      trimmed.includes('->') ||
      trimmed.includes('//') ||
      trimmed.includes('#')
    ) {
      return true
    }
  }

  // Arrow function with block or return
  if (/(?:\w+|\([^)]*\))\s*=>\s*[{]/.test(trimmed)) {
    return true
  }

  // Python function definition: def foo(...):
  if (/(?:^|\n)\s*def\s+\w+\s*\([^)]*\)\s*:/m.test(trimmed)) {
    return true
  }

  // Multi-line code indentation with return / control flow
  if (/(?:^|\n)\s{2,}(?:return\b|yield\b|raise\b|throw\b)/m.test(trimmed) && (trimmed.includes('{') || trimmed.includes(':'))) {
    return true
  }

  return false
}

export function isCodeCard(
  item?: {
    grading_profile?: string | null
    starter_code?: string | null
    test_cases?: unknown[] | null
    time_complexity?: string | null
    space_complexity?: string | null
    back?: string | null
  } | null
): boolean {
  if (!item) return false
  return Boolean(
    item.grading_profile === 'math_code' ||
      (item.starter_code && item.starter_code.trim()) ||
      (item.test_cases && item.test_cases.length > 0) ||
      (item.time_complexity && item.time_complexity.trim()) ||
      (item.space_complexity && item.space_complexity.trim()) ||
      looksLikeCode(item.back)
  )
}

export function extractCleanCode(raw?: string | null): string {
  if (!raw) return ''
  const trimmed = raw.trim()

  // Full-string code fence: ```lang\n<code>\n```
  const fenceMatch = trimmed.match(/^```(?:[a-zA-Z0-9_-]+)?\r?\n([\s\S]*?)\r?\n```$/)
  if (fenceMatch) {
    return fenceMatch[1].trim()
  }

  // If there's an embedded fenced block that forms the bulk of the content
  const embeddedMatch = trimmed.match(CODE_FENCE_REGEX)
  if (embeddedMatch && embeddedMatch[1].trim().length > trimmed.length * 0.4) {
    return embeddedMatch[1].trim()
  }

  return trimmed
}

export function detectCodeLanguage(
  code?: string | null,
  fallback: string = 'typescript'
): string {
  if (!code) return fallback
  const text = code.trim()

  // Markdown fence language hint
  const fenceMatch = text.match(/```([a-zA-Z0-9_-]+)/)
  if (fenceMatch) {
    const lang = fenceMatch[1].toLowerCase()
    if (lang === 'py' || lang === 'python' || lang === 'python3') return 'python'
    if (lang === 'ts' || lang === 'typescript') return 'typescript'
    if (lang === 'js' || lang === 'javascript') return 'javascript'
  }

  // Python heuristics
  if (
    /(?:^|\n)\s*def\s+\w+\s*\(/.test(text) ||
    /\b(elif|lambda|self)\b/.test(text) ||
    /(?:^|\n)\s*import\s+(?:math|collections|heapq|sys|os)\b/.test(text) ||
    /\bprint\(/.test(text)
  ) {
    return 'python'
  }

  // TypeScript heuristics
  if (
    /:\s*(?:number|string|boolean|void|any|Record<|Array<|Map<|Promise<)/.test(text) ||
    /\b(interface|type\s+\w+\s*=)/.test(text) ||
    /as\s+(?:const|string|number)/.test(text)
  ) {
    return 'typescript'
  }

  // JavaScript heuristics
  if (/\b(function|const|let|var)\b/.test(text)) {
    return fallback === 'python' ? 'typescript' : fallback
  }

  return fallback
}

export function calcEditorHeight(
  code: string,
  minH: number = 140,
  maxH: number = 460
): string {
  const lineCount = Math.max(code.split('\n').length, 1)
  return `${Math.max(minH, Math.min(maxH, lineCount * 24 + 32))}px`
}
