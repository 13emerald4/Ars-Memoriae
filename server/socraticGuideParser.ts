import fs from 'node:fs'
import path from 'node:path'

export interface ParsedTerm {
  term: string
  definition: string
}

export interface ParsedDocLink {
  label: string
  url: string
}

export interface ParsedReadingSection {
  question: string
  body: string
}

export interface ParsedReadingBlock {
  chapterTitle: string
  coreIdea: string
  sections: ParsedReadingSection[]
}

export interface ParsedChapter {
  partNumber: number
  chapterNumber: number
  label: string
  title: string
  coreIdea: string
  rule: string | null
  ponder: string | null
}

export interface ParsedDeck {
  partNumber: number
  partTitle: string
  name: string
  declaredCardCount: number
  coreIdea: string
  summary: string
  readMoreLinks: ParsedDocLink[]
}

export interface ParsedCardGuide {
  id: string
  partNumber: number
  partTitle: string
  sourceFile: string
  deckName: string
  chapterNumbers: number[]
  cardNumber: number
  title: string
  metaRaw: string
  kind: 'write' | 'fix' | 'types' | 'predict' | 'compile' | 'concept'
  language: 'javascript' | 'typescript'
  slug: string
  difficulty: 'Easy' | 'Medium' | 'Hard' | null
  docLinks: ParsedDocLink[]
  terms: ParsedTerm[]
  prompt: string
  starterCode: string | null
  snippetCode: string | null
  solve: string | null
  invariants: string | null
  memory: string | null
  types: string | null
  failure: string | null
  tests: string | null
  trap: string | null
  solutionCode: string | null
  solutionOutput: string | null
  why: string | null
  readings: ParsedReadingBlock[]
}

export interface ParsedPartGuide {
  partNumber: number
  partTitle: string
  sourceFile: string
  chapters: ParsedChapter[]
  decks: ParsedDeck[]
  cards: ParsedCardGuide[]
}

export interface ParsedCourseGuide {
  parts: ParsedPartGuide[]
  chaptersByNumber: Map<number, ParsedChapter>
  decksByName: Map<string, ParsedDeck>
  cards: ParsedCardGuide[]
}

export const COURSE_GUIDE_FILES: Array<{
  partNumber: number
  partTitle: string
  filename: string
}> = [
  {
    partNumber: 1,
    partTitle: 'Part 1 · JavaScript Fundamentals',
    filename: 'part1-javascript-fundamentals_e024f2e2.tex',
  },
  {
    partNumber: 2,
    partTitle: 'Part 2 · TypeScript Core',
    filename: 'part2-typescript-core_28a0975f.tex',
  },
  {
    partNumber: 3,
    partTitle: 'Part 3 · Intermediate TypeScript',
    filename: 'part3-intermediate-typescript_ce400778.tex',
  },
  {
    partNumber: 4,
    partTitle: 'Part 4 · Hands-On Labs',
    filename: 'part4-hands-on-labs_cad936a4.tex',
  },
]

/** Read a balanced {...} group starting at openBraceIdx (where str[openBraceIdx] === '{'). */
function readBraceGroup(str: string, openBraceIdx: number): { content: string; endIdx: number } | null {
  if (str[openBraceIdx] !== '{') return null
  let depth = 0
  let i = openBraceIdx
  while (i < str.length) {
    const ch = str[i]
    if (ch === '\\' && i + 1 < str.length) {
      // Skip escaped brace \{ or \} or \\ so they don't affect nesting depth
      const next = str[i + 1]
      if (next === '{' || next === '}' || next === '\\') {
        i += 2
        continue
      }
    }
    if (ch === '{') {
      depth++
    } else if (ch === '}') {
      depth--
      if (depth === 0) {
        return { content: str.slice(openBraceIdx + 1, i), endIdx: i + 1 }
      }
    }
    i++
  }
  return null
}

/** Read a balanced [...] group starting at openBracketIdx. */
function readBracketGroup(str: string, openBracketIdx: number): { content: string; endIdx: number } | null {
  if (str[openBracketIdx] !== '[') return null
  let depth = 0
  let braceDepth = 0
  let i = openBracketIdx
  while (i < str.length) {
    const ch = str[i]
    if (ch === '\\' && i + 1 < str.length) {
      i += 2
      continue
    }
    if (ch === '{') braceDepth++
    else if (ch === '}') braceDepth = Math.max(0, braceDepth - 1)
    else if (braceDepth === 0) {
      if (ch === '[') depth++
      else if (ch === ']') {
        depth--
        if (depth === 0) {
          return { content: str.slice(openBracketIdx + 1, i), endIdx: i + 1 }
        }
      }
    }
    i++
  }
  return null
}

/** Replace every occurrence of a LaTeX macro with N brace arguments (and optional leading [...] arg). */
function replaceMacro(
  input: string,
  macroName: string,
  argCount: number,
  replacer: (args: string[], optArg: string | null) => string,
  hasOptionalBracket = false,
): string {
  const token = `\\${macroName}`
  let result = ''
  let pos = 0

  while (pos < input.length) {
    const idx = input.indexOf(token, pos)
    if (idx === -1) {
      result += input.slice(pos)
      break
    }
    const afterToken = idx + token.length
    // Ensure macro name boundary (next char is not ASCII letter)
    if (afterToken < input.length && /[a-zA-Z]/.test(input[afterToken])) {
      result += input.slice(pos, afterToken)
      pos = afterToken
      continue
    }

    let cursor = afterToken
    while (cursor < input.length && (input[cursor] === ' ' || input[cursor] === '\t')) cursor++

    let optArg: string | null = null
    if (hasOptionalBracket && input[cursor] === '[') {
      const opt = readBracketGroup(input, cursor)
      if (opt) {
        optArg = opt.content
        cursor = opt.endIdx
        while (cursor < input.length && (input[cursor] === ' ' || input[cursor] === '\t')) cursor++
      }
    }

    const args: string[] = []
    let matchedAll = true
    for (let a = 0; a < argCount; a++) {
      while (cursor < input.length && (input[cursor] === ' ' || input[cursor] === '\t')) cursor++
      const grp = readBraceGroup(input, cursor)
      if (!grp) {
        matchedAll = false
        break
      }
      args.push(grp.content)
      cursor = grp.endIdx
    }

    if (!matchedAll) {
      result += input.slice(pos, afterToken)
      pos = afterToken
      continue
    }

    result += input.slice(pos, idx) + replacer(args, optArg)
    pos = cursor
  }

  return result
}

/** Extract all calls to a macro with N brace args (and optional [...] arg). */
function extractMacroCalls(
  input: string,
  macroName: string,
  argCount: number,
  hasOptionalBracket = false,
): Array<{ index: number; endIndex: number; args: string[]; optArg: string | null }> {
  const token = `\\${macroName}`
  const calls: Array<{ index: number; endIndex: number; args: string[]; optArg: string | null }> = []
  let pos = 0

  while (pos < input.length) {
    const idx = input.indexOf(token, pos)
    if (idx === -1) break
    const afterToken = idx + token.length
    if (afterToken < input.length && /[a-zA-Z]/.test(input[afterToken])) {
      pos = afterToken
      continue
    }
    let cursor = afterToken
    while (cursor < input.length && (input[cursor] === ' ' || input[cursor] === '\t')) cursor++

    let optArg: string | null = null
    if (hasOptionalBracket && input[cursor] === '[') {
      const opt = readBracketGroup(input, cursor)
      if (opt) {
        optArg = opt.content
        cursor = opt.endIdx
      }
    }

    const args: string[] = []
    let ok = true
    for (let a = 0; a < argCount; a++) {
      while (cursor < input.length && (input[cursor] === ' ' || input[cursor] === '\t')) cursor++
      const grp = readBraceGroup(input, cursor)
      if (!grp) {
        ok = false
        break
      }
      args.push(grp.content)
      cursor = grp.endIdx
    }

    if (ok) {
      calls.push({ index: idx, endIndex: cursor, args, optArg })
      pos = cursor
    } else {
      pos = afterToken
    }
  }
  return calls
}

function unescapeLatexCode(raw: string): string {
  return raw
    .replace(/\\textquotedbl\{\}|\\textquotedbl(?![a-zA-Z])/g, '"')
    .replace(/\\textquotesingle\{\}|\\textquotesingle(?![a-zA-Z])/g, "'")
    .replace(/\\textless\{\}|\\textless(?![a-zA-Z])/g, '<')
    .replace(/\\textgreater\{\}|\\textgreater(?![a-zA-Z])/g, '>')
    .replace(/\\textbackslash\{\}|\\textbackslash(?![a-zA-Z])/g, '\\')
    .replace(/\\textdegree\{\}|\\textdegree(?![a-zA-Z])/g, '°')
    .replace(/\\([&%_$#{}])/g, '$1')
    .replace(/~/g, ' ')
    .trim()
}

function mapListingLanguage(rawLang: string | undefined): string {
  const lower = (rawLang || '').trim().toLowerCase()
  if (lower.includes('typescript') || lower === 'ts') return 'typescript'
  if (lower.includes('javascript') || lower === 'js') return 'javascript'
  if (lower.includes('json')) return 'json'
  return 'text'
}

/** Convert LaTeX prose (including lstlisting code blocks, \code, \textbf, \href, math arrows) into clean Markdown. */
export function latexToMarkdown(rawTex: string): string {
  if (!rawTex) return ''
  let s = rawTex.replace(/\r\n/g, '\n')

  // Strip LaTeX full-line or trailing comments (unescaped %) outside lstlisting blocks
  const codePlaceholders: string[] = []
  s = s.replace(
    /\\begin\{lstlisting\}(?:\[([^\]]*)\])?([\s\S]*?)\\end\{lstlisting\}/g,
    (_m, opts: string | undefined, body: string) => {
      const langMatch = opts?.match(/language\s*=\s*([A-Za-z0-9_+-]+)/i)
      const lang = mapListingLanguage(langMatch?.[1])
      const cleanCode = body.replace(/^\n/, '').replace(/\n$/, '')
      const idx = codePlaceholders.length
      codePlaceholders.push(`\n\n\`\`\`${lang}\n${cleanCode}\n\`\`\`\n\n`)
      return `@@CODEBLOCK_${idx}@@`
    },
  )

  // Remove LaTeX comments (unescaped %)
  s = s.replace(/(^|[^\\])%[^\n]*/g, '$1')

  // Protect inline \code{...} content as placeholders so inner punctuation/quotes/braces stay exact
  const inlineCodePlaceholders: string[] = []
  s = replaceMacro(s, 'code', 1, ([inner]) => {
    const cleaned = unescapeLatexCode(inner)
    const idx = inlineCodePlaceholders.length
    // Use double backticks if the code snippet itself contains a backtick
    const formatted = cleaned.includes('`') ? `\`\` ${cleaned} \`\`` : `\`${cleaned}\``
    inlineCodePlaceholders.push(formatted)
    return `@@INLINECODE_${idx}@@`
  })

  // Structural / layout macros to remove completely
  s = replaceMacro(s, 'Needspace', 1, () => '')
  s = replaceMacro(s, 'vspace', 1, () => '')
  s = replaceMacro(s, 'label', 1, () => '')
  s = replaceMacro(s, 'ix', 1, () => '')
  s = replaceMacro(s, 'color', 1, () => '')
  s = s.replace(/\\phantomsection\b/g, '')
  s = s.replace(/\\nopagebreak\b/g, '')
  s = s.replace(/\\newpage\b/g, '')
  s = s.replace(/\\noindent\b/g, '')
  s = s.replace(/\\raggedright\b/g, '')
  s = s.replace(/\\hfill\b/g, ' ')
  s = s.replace(/\\enspace\b/g, ' ')
  s = s.replace(/\\smallskip\b|\\medskip\b|\\bigskip\b/g, '\n')

  // Hyperlinks & cross references
  s = replaceMacro(s, 'hyperref', 1, ([text]) => text, true)
  s = replaceMacro(s, 'href', 2, ([url, label]) => `[${label}](${url})`)
  s = replaceMacro(s, 'path', 1, ([inner]) => `\`${unescapeLatexCode(inner)}\``)

  // Terms: \term[marginDef]{id}{visibleText} -> **visibleText**
  s = replaceMacro(s, 'term', 2, ([, text]) => `**${text}**`, true)

  // Colored separators like \textcolor{black!45}{|}
  s = replaceMacro(s, 'textcolor', 2, ([, text]) => text)

  // Formatting macros (run twice for simple nesting like \textbf{... \emph{...}})
  for (let pass = 0; pass < 2; pass++) {
    s = replaceMacro(s, 'textbf', 1, ([inner]) => `**${inner.trim()}**`)
    s = replaceMacro(s, 'textit', 1, ([inner]) => {
      const t = inner.trim()
      if (/^(Prints:|tsc\s+--strict:)$/i.test(t)) return `**${t}**`
      return `*${t}*`
    })
    s = replaceMacro(s, 'emph', 1, ([inner]) => `*${inner.trim()}*`)
  }

  // Font-size / style switches inside brace groups like {\small\textit{Prints:} ...}
  s = s.replace(/\\(small|footnotesize|large|LARGE|bfseries|itshape|scshape|ttfamily)\b/g, '')

  // Math symbols & special LaTeX character macros
  s = s.replace(/\$\\rightarrow\$/g, '→')
  s = s.replace(/\$\\geq\$/g, '≥')
  s = s.replace(/\$\\leq\$/g, '≤')
  s = s.replace(/\$\\pi\$/g, 'π')
  s = s.replace(/\$\\times\$/g, '×')
  s = s.replace(/\$\\ldots\$/g, '…')
  s = s.replace(/\\rightarrow\b/g, '→')
  s = s.replace(/\\geq\b/g, '≥')
  s = s.replace(/\\leq\b/g, '≤')
  s = s.replace(/\\pi\b/g, 'π')
  s = s.replace(/\\times\b/g, '×')
  s = s.replace(/\\ldots\b/g, '…')
  s = s.replace(/\\textquotedbl\{\}|\\textquotedbl(?![a-zA-Z])/g, '"')
  s = s.replace(/\\textquotesingle\{\}|\\textquotesingle(?![a-zA-Z])/g, "'")
  s = s.replace(/\\textless\{\}|\\textless(?![a-zA-Z])/g, '<')
  s = s.replace(/\\textgreater\{\}|\\textgreater(?![a-zA-Z])/g, '>')
  s = s.replace(/\\textbackslash\{\}|\\textbackslash(?![a-zA-Z])/g, '\\')
  s = s.replace(/\\textdegree\{\}|\\textdegree(?![a-zA-Z])/g, '°')

  // Paragraph markers
  s = s.replace(/\\par\b/g, '\n\n')
  s = s.replace(/\\\\/g, '\n')

  // Escaped LaTeX punctuation
  s = s.replace(/\\([&%_$#{}])/g, '$1')

  // Typographic punctuation (preserve CLI flags like --strict)
  s = s.replace(/---/g, '—')
  s = s.replace(/(^|\s)--(?=\s|$)/g, '$1–')
  s = s.replace(/``/g, '"')
  s = s.replace(/''/g, '"')
  s = s.replace(/~/g, ' ')

  // Remove bare grouping braces left over from {\small ...}
  // Iterate to peel outer non-semantic braces while leaving code intact (code is in placeholders)
  let prev = ''
  while (prev !== s) {
    prev = s
    s = s.replace(/\{([^{}]+)\}/g, '$1')
  }

  // Clean up prose whitespace BEFORE restoring inline code & fenced blocks so spaces inside `"   "` stay intact
  s = s
    .replace(/[ \t]+\n/g, '\n')
    .replace(/\n[ \t]+/g, '\n')
    .replace(/[ \t]{2,}/g, ' ')
    .replace(/\n{3,}/g, '\n\n')

  // Restore inline code and fenced code blocks
  s = s.replace(/@@INLINECODE_(\d+)@@/g, (_m, idx) => inlineCodePlaceholders[Number(idx)] ?? '')
  s = s.replace(/@@CODEBLOCK_(\d+)@@/g, (_m, idx) => codePlaceholders[Number(idx)] ?? '')

  return s.trim()
}

function extractLstListings(rawTex: string): Array<{ language: string; code: string; fullMatch: string }> {
  const results: Array<{ language: string; code: string; fullMatch: string }> = []
  const re = /\\begin\{lstlisting\}(?:\[([^\]]*)\])?([\s\S]*?)\\end\{lstlisting\}/g
  let m: RegExpExecArray | null
  while ((m = re.exec(rawTex)) !== null) {
    const opts = m[1] || ''
    const langMatch = opts.match(/language\s*=\s*([A-Za-z0-9_+-]+)/i)
    const language = mapListingLanguage(langMatch?.[1])
    const code = m[2].replace(/^\n/, '').replace(/\n$/, '')
    results.push({ language, code, fullMatch: m[0] })
  }
  return results
}

function parseTermsFromSafemargin(cardTex: string): ParsedTerm[] {
  const calls = extractMacroCalls(cardTex, 'safemargin', 1)
  if (calls.length === 0) return []
  const body = calls[0].args[0]
  // Split on \par\smallskip or \par after removing the leading \textbf{Terms for this card}
  const stripped = body.replace(/^\s*\\textbf\{Terms for this card\}(?:\s*\\par)?(?:\s*\\smallskip)?\s*/i, '')
  const segments = stripped.split(/\\par(?:\s*\\smallskip)?/).map((seg) => seg.trim()).filter(Boolean)

  const terms: ParsedTerm[] = []
  for (const seg of segments) {
    const boldCalls = extractMacroCalls(seg, 'textbf', 1)
    if (boldCalls.length > 0 && boldCalls[0].index === 0) {
      const rawTerm = latexToMarkdown(boldCalls[0].args[0]).replace(/:\s*$/, '').trim()
      const rawDef = latexToMarkdown(seg.slice(boldCalls[0].endIndex)).replace(/^:\s*/, '').trim()
      if (rawTerm && rawDef) {
        terms.push({ term: rawTerm, definition: rawDef })
      }
    }
  }
  return terms
}

function parseCardRows(howToSolveTex: string): {
  solve: string | null
  invariants: string | null
  memory: string | null
  types: string | null
  failure: string | null
  tests: string | null
} {
  const out = {
    solve: null as string | null,
    invariants: null as string | null,
    memory: null as string | null,
    types: null as string | null,
    failure: null as string | null,
    tests: null as string | null,
  }
  const envMatch = howToSolveTex.match(/\\begin\{cardrows\}([\s\S]*?)\\end\{cardrows\}/)
  if (!envMatch) return out
  const body = envMatch[1]
  const itemRe = /\\item\[([^\]]+)\]\s*/g
  const markers: Array<{ key: string; start: number; contentStart: number }> = []
  let m: RegExpExecArray | null
  while ((m = itemRe.exec(body)) !== null) {
    markers.push({ key: m[1].trim().toLowerCase(), start: m.index, contentStart: itemRe.lastIndex })
  }
  for (let i = 0; i < markers.length; i++) {
    const cur = markers[i]
    const end = i + 1 < markers.length ? markers[i + 1].start : body.length
    const val = latexToMarkdown(body.slice(cur.contentStart, end))
    if (cur.key === 'solve') out.solve = val
    else if (cur.key === 'invariants') out.invariants = val
    else if (cur.key === 'memory') out.memory = val
    else if (cur.key === 'types') out.types = val
    else if (cur.key === 'failure') out.failure = val
    else if (cur.key === 'tests') out.tests = val
  }
  return out
}

function parseReadingsSection(readingsTex: string): ParsedReadingBlock[] {
  if (!readingsTex.trim()) return []
  const chapCalls = extractMacroCalls(readingsTex, 'readchap', 2)
  const blocks: ParsedReadingBlock[] = []

  for (let i = 0; i < chapCalls.length; i++) {
    const cur = chapCalls[i]
    const nextStart = i + 1 < chapCalls.length ? chapCalls[i + 1].index : readingsTex.length
    const slice = readingsTex.slice(cur.endIndex, nextStart)
    const chapterTitle = latexToMarkdown(cur.args[0])
    const coreIdea = latexToMarkdown(cur.args[1])

    const qCalls = extractMacroCalls(slice, 'readq', 1)
    const sections: ParsedReadingSection[] = []
    for (let j = 0; j < qCalls.length; j++) {
      const q = qCalls[j]
      const qEnd = j + 1 < qCalls.length ? qCalls[j + 1].index : slice.length
      const question = latexToMarkdown(q.args[0])
      const body = latexToMarkdown(slice.slice(q.endIndex, qEnd))
      if (question || body) {
        sections.push({ question, body })
      }
    }
    blocks.push({ chapterTitle, coreIdea, sections })
  }

  return blocks
}

function slugify(text: string): string {
  return text
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-+|-+$/g, '')
}

function parseMeta(metaRaw: string, partNumber: number, cardNumber: number, title: string): {
  kind: ParsedCardGuide['kind']
  language: 'javascript' | 'typescript'
  slug: string
  difficulty: ParsedCardGuide['difficulty']
} {
  const parts = metaRaw.split('·').map((p) => p.trim()).filter(Boolean)
  const rawKind = (parts[0] || 'concept').toLowerCase()
  const kind: ParsedCardGuide['kind'] =
    rawKind === 'write' || rawKind === 'fix' || rawKind === 'types' || rawKind === 'predict' || rawKind === 'compile'
      ? rawKind
      : 'concept'

  let language: 'javascript' | 'typescript' = partNumber === 1 ? 'javascript' : 'typescript'
  let slug = ''
  let difficulty: ParsedCardGuide['difficulty'] = null

  for (const p of parts.slice(1)) {
    const low = p.toLowerCase()
    if (low === 'javascript' || low === 'js') {
      language = 'javascript'
    } else if (low === 'typescript' || low === 'ts') {
      language = 'typescript'
    } else if (low === 'easy') {
      difficulty = 'Easy'
    } else if (low === 'medium') {
      difficulty = 'Medium'
    } else if (low === 'hard') {
      difficulty = 'Hard'
    } else if (/^(js|ts)\d+-/i.test(p)) {
      slug = p.toLowerCase()
      if (slug.startsWith('ts')) language = 'typescript'
      else if (slug.startsWith('js')) language = 'javascript'
    }
  }

  if (!slug) {
    slug = `p${partNumber}-c${cardNumber}-${slugify(title)}`
  }

  return { kind, language, slug, difficulty }
}

/** Parse one complete LaTeX Socratic study guide file. */
export function parseTexStudyGuide(
  tex: string,
  meta: { partNumber: number; partTitle: string; sourceFile: string },
): ParsedPartGuide {
  const docStart = tex.indexOf('\\begin{document}')
  const docEnd = tex.indexOf('\\end{document}')
  const body =
    docStart !== -1
      ? tex.slice(docStart + '\\begin{document}'.length, docEnd !== -1 ? docEnd : tex.length)
      : tex

  // 1. Parse Chapters (\chap{title}{coreIdea} ... \mantra{...} ... \begin{ponder}...\end{ponder})
  const chapCalls = extractMacroCalls(body, 'chap', 2)
  const chapters: ParsedChapter[] = []
  for (let i = 0; i < chapCalls.length; i++) {
    const cur = chapCalls[i]
    const nextIdx = i + 1 < chapCalls.length ? chapCalls[i + 1].index : body.indexOf('\\deckhead{', cur.endIndex)
    const endBoundary = nextIdx !== -1 ? nextIdx : body.length
    const chapSlice = body.slice(cur.endIndex, endBoundary)

    const title = latexToMarkdown(cur.args[0])
    const coreIdea = latexToMarkdown(cur.args[1])
    const numMatch = title.match(/^(\d+)\./)
    const chapterNumber = numMatch ? Number(numMatch[1]) : i + 1

    const beforeChunk = body.slice(Math.max(0, cur.index - 80), cur.index)
    const labelMatch = beforeChunk.match(/\\label\{([^}]+)\}/)
    const label = labelMatch?.[1] ?? `ch:c${String(chapterNumber).padStart(2, '0')}`

    const mantraCalls = extractMacroCalls(chapSlice, 'mantra', 1)
    const rule = mantraCalls.length > 0 ? latexToMarkdown(mantraCalls[0].args[0]) : null

    const ponderMatch = chapSlice.match(/\\begin\{ponder\}([\s\S]*?)\\end\{ponder\}/)
    const ponder = ponderMatch ? latexToMarkdown(ponderMatch[1]) : null

    chapters.push({
      partNumber: meta.partNumber,
      chapterNumber,
      label,
      title,
      coreIdea,
      rule,
      ponder,
    })
  }

  // 2. Parse Decks (\deckhead{name}{count}) and their Cards (\cardhead ... \cardend)
  const deckCalls = extractMacroCalls(body, 'deckhead', 2)
  const decks: ParsedDeck[] = []
  const cards: ParsedCardGuide[] = []

  for (let dIdx = 0; dIdx < deckCalls.length; dIdx++) {
    const dc = deckCalls[dIdx]
    const deckEnd = dIdx + 1 < deckCalls.length ? deckCalls[dIdx + 1].index : body.length
    const deckSlice = body.slice(dc.endIndex, deckEnd)

    const deckName = latexToMarkdown(dc.args[0])
    const declaredCardCount = Number(dc.args[1].trim()) || 0

    const coreMatch = deckSlice.match(/\\begin\{corebox\}([\s\S]*?)\\end\{corebox\}/)
    const deckCoreIdea = coreMatch
      ? latexToMarkdown(coreMatch[1].replace(/^\s*\\textbf\{Core idea\.?\}\s*/i, ''))
      : ''

    let deckSummary = ''
    const readMoreLinks: ParsedDocLink[] = []
    const sumStart = deckSlice.indexOf('\\begin{sumbox}')
    const sumEnd = deckSlice.indexOf('\\end{sumbox}')
    if (sumStart !== -1 && sumEnd !== -1 && sumEnd > sumStart) {
      const afterBegin = sumStart + '\\begin{sumbox}'.length
      const sumTitleGrp = readBraceGroup(deckSlice, afterBegin)
      const sumContent = sumTitleGrp ? deckSlice.slice(sumTitleGrp.endIdx, sumEnd) : deckSlice.slice(afterBegin, sumEnd)
      for (const hc of extractMacroCalls(sumContent, 'href', 2)) {
        readMoreLinks.push({
          url: unescapeLatexCode(hc.args[0]),
          label: latexToMarkdown(hc.args[1]),
        })
      }
      const withoutReadMore = sumContent.replace(/\\par\\smallskip\{\\footnotesize\s*Read more:[\s\S]*$/, '')
      deckSummary = latexToMarkdown(withoutReadMore)
    }

    decks.push({
      partNumber: meta.partNumber,
      partTitle: meta.partTitle,
      name: deckName,
      declaredCardCount,
      coreIdea: deckCoreIdea,
      summary: deckSummary,
      readMoreLinks,
    })

    // Parse all cards inside this deck slice
    const cardCalls = extractMacroCalls(deckSlice, 'cardhead', 2)
    for (let cIdx = 0; cIdx < cardCalls.length; cIdx++) {
      const cc = cardCalls[cIdx]
      const cardEndMarker = deckSlice.indexOf('\\cardend', cc.endIndex)
      const nextCardIdx = cIdx + 1 < cardCalls.length ? cardCalls[cIdx + 1].index : deckSlice.length
      const cardEnd = cardEndMarker !== -1 && cardEndMarker < nextCardIdx ? cardEndMarker : nextCardIdx
      const cardBody = deckSlice.slice(cc.endIndex, cardEnd)

      const rawHeader = latexToMarkdown(cc.args[0])
      const headerMatch = rawHeader.match(/^Card\s+(\d+)\s*[—–-]+\s*(.+)$/)
      const cardNumber = headerMatch ? Number(headerMatch[1]) : cIdx + 1
      const title = (headerMatch ? headerMatch[2] : rawHeader).trim()
      const metaRaw = latexToMarkdown(cc.args[1])
      const { kind, language, slug, difficulty } = parseMeta(metaRaw, meta.partNumber, cardNumber, title)

      const terms = parseTermsFromSafemargin(cardBody)

      // Extract Covered in chapters + doc links (in header area before \cardsub{The card})
      const firstCardSubIdx = cardBody.indexOf('\\cardsub{')
      const headerArea = firstCardSubIdx !== -1 ? cardBody.slice(0, firstCardSubIdx) : ''
      const chapterNumbers: number[] = []
      for (const hrc of extractMacroCalls(headerArea, 'hyperref', 1, true)) {
        const chMatch = (hrc.optArg || '').match(/ch:c(\d+)/i) || hrc.args[0].match(/(\d+)/)
        if (chMatch) {
          const n = Number(chMatch[1])
          if (!chapterNumbers.includes(n)) chapterNumbers.push(n)
        }
      }
      const docLinks: ParsedDocLink[] = []
      for (const hc of extractMacroCalls(headerArea, 'href', 2)) {
        docLinks.push({
          url: unescapeLatexCode(hc.args[0]),
          label: latexToMarkdown(hc.args[1]),
        })
      }

      // Split into \cardsub{...} sections
      const subCalls = extractMacroCalls(cardBody, 'cardsub', 1)
      const sectionsByName = new Map<string, string>()
      for (let sIdx = 0; sIdx < subCalls.length; sIdx++) {
        const sc = subCalls[sIdx]
        const sEnd = sIdx + 1 < subCalls.length ? subCalls[sIdx + 1].index : cardBody.length
        const secName = latexToMarkdown(sc.args[0]).toLowerCase()
        sectionsByName.set(secName, cardBody.slice(sc.endIndex, sEnd))
      }

      // Parse "The card"
      const theCardRaw = sectionsByName.get('the card') || ''
      const theCardListings = extractLstListings(theCardRaw)
      const theCardWithoutCode = theCardRaw.replace(
        /\\begin\{lstlisting\}(?:\[[^\]]*\])?[\s\S]*?\\end\{lstlisting\}/g,
        '',
      )
      let prompt = latexToMarkdown(theCardWithoutCode)
      // Remove duplicate leading bold title line (e.g. **parseCount(text)** followed by Write `parseCount(text)`...)
      const escapedTitle = title.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
      prompt = prompt
        .replace(new RegExp(`^\\*\\*${escapedTitle}\\*\\*\\s*\\n+`, 'i'), '')
        .replace(new RegExp(`^${escapedTitle}\\s*\\n+`, 'i'), '')
        .trim()

      let starterCode: string | null = null
      let snippetCode: string | null = null
      if (theCardListings.length > 0) {
        if (kind === 'write' || kind === 'fix' || kind === 'types') {
          starterCode = theCardListings[0].code
        } else {
          snippetCode = theCardListings[0].code
        }
      }

      // Parse "How to solve it" + \trap
      const howRaw = sectionsByName.get('how to solve it') || ''
      const rows = parseCardRows(howRaw)
      let trap: string | null = null
      const trapIdx = howRaw.indexOf('\\trap')
      if (trapIdx !== -1) {
        const afterTrap = howRaw.slice(trapIdx + '\\trap'.length).trim()
        // Trap runs until \par or end of section
        const trapEnd = afterTrap.indexOf('\\par')
        trap = latexToMarkdown(trapEnd !== -1 ? afterTrap.slice(0, trapEnd) : afterTrap)
      }

      // Parse "Solution"
      const solRaw = sectionsByName.get('solution') || ''
      const solListings = extractLstListings(solRaw)
      let solutionCode: string | null = null
      let solutionOutput: string | null = null
      if (solListings.length > 0) {
        if (kind === 'predict' || kind === 'compile') {
          solutionOutput = solListings[0].code
        } else {
          solutionCode = solListings[0].code
        }
      }
      let why: string | null = null
      const whyMatch = solRaw.match(/\\textbf\{Why:\}\s*([\s\S]*?)(?:\}\s*(?:\\par|$)|$)/)
      if (whyMatch) {
        why = latexToMarkdown(whyMatch[1])
      }

      // Parse "From the readings"
      const readingsRaw = sectionsByName.get('from the readings') || ''
      const readings = parseReadingsSection(readingsRaw)

      cards.push({
        id: `guide-p${meta.partNumber}-${String(cardNumber).padStart(2, '0')}-${slug}`,
        partNumber: meta.partNumber,
        partTitle: meta.partTitle,
        sourceFile: meta.sourceFile,
        deckName,
        chapterNumbers,
        cardNumber,
        title,
        metaRaw,
        kind,
        language,
        slug,
        difficulty,
        docLinks,
        terms,
        prompt,
        starterCode,
        snippetCode,
        solve: rows.solve,
        invariants: rows.invariants,
        memory: rows.memory,
        types: rows.types,
        failure: rows.failure,
        tests: rows.tests,
        trap,
        solutionCode,
        solutionOutput,
        why,
        readings,
      })
    }
  }

  return {
    partNumber: meta.partNumber,
    partTitle: meta.partTitle,
    sourceFile: meta.sourceFile,
    chapters,
    decks,
    cards,
  }
}

let cachedCourseGuide: ParsedCourseGuide | null = null

export function loadAllSocraticGuides(
  assetsDir = path.resolve(process.cwd(), 'public/assets/aistudio'),
): ParsedCourseGuide {
  if (cachedCourseGuide && assetsDir === path.resolve(process.cwd(), 'public/assets/aistudio')) {
    return cachedCourseGuide
  }

  const parts: ParsedPartGuide[] = []
  const chaptersByNumber = new Map<number, ParsedChapter>()
  const decksByName = new Map<string, ParsedDeck>()
  const allCards: ParsedCardGuide[] = []

  for (const spec of COURSE_GUIDE_FILES) {
    const filePath = path.join(assetsDir, spec.filename)
    if (!fs.existsSync(filePath)) continue
    const tex = fs.readFileSync(filePath, 'utf8')
    const parsed = parseTexStudyGuide(tex, {
      partNumber: spec.partNumber,
      partTitle: spec.partTitle,
      sourceFile: spec.filename,
    })
    parts.push(parsed)
    for (const ch of parsed.chapters) chaptersByNumber.set(ch.chapterNumber, ch)
    for (const dk of parsed.decks) decksByName.set(dk.name, dk)
    allCards.push(...parsed.cards)
  }

  const course: ParsedCourseGuide = {
    parts,
    chaptersByNumber,
    decksByName,
    cards: allCards,
  }

  if (assetsDir === path.resolve(process.cwd(), 'public/assets/aistudio')) {
    cachedCourseGuide = course
  }
  return course
}
