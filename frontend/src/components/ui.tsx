import { useState, type ReactNode } from 'react'
import { CodeEditor } from './CodeEditor'

export function Spinner({ label }: { label?: string }) {
  return (
    <div className="flex items-center gap-3 text-sm text-slate-500">
      <span className="h-4 w-4 animate-spin rounded-full border-2 border-slate-700 border-t-sky-400" />
      {label ?? 'Loading…'}
    </div>
  )
}

export function ErrorNote({ error }: { error: unknown }) {
  if (!error) return null
  const message = error instanceof Error ? error.message : String(error)
  return (
    <div className="rounded-lg border border-rose-500/40 bg-rose-500/10 px-4 py-3 text-sm text-rose-200">
      {message}
    </div>
  )
}

export function Empty({ title, children }: { title: string; children?: ReactNode }) {
  return (
    <div className="rounded-xl border border-dashed border-ink-line px-6 py-12 text-center">
      <p className="text-slate-300">{title}</p>
      {children && <div className="mt-3 text-sm text-slate-500">{children}</div>}
    </div>
  )
}

export function Section({
  title,
  description,
  children,
  actions,
}: {
  title: string
  description?: string
  children: ReactNode
  actions?: ReactNode
}) {
  return (
    <section className="card">
      <div className="mb-4 flex items-start justify-between gap-4">
        <div>
          <h2 className="text-sm font-semibold text-slate-200">{title}</h2>
          {description && <p className="mt-1 text-xs text-slate-500">{description}</p>}
        </div>
        {actions}
      </div>
      {children}
    </section>
  )
}

const FENCE_LANG_ALIASES: Record<string, string> = {
  ts: 'typescript',
  tsx: 'typescript',
  typescript: 'typescript',
  js: 'javascript',
  jsx: 'javascript',
  javascript: 'javascript',
  py: 'python',
  python: 'python',
  java: 'java',
  cpp: 'cpp',
  'c++': 'cpp',
  c: 'c',
  go: 'go',
  rust: 'rust',
  rs: 'rust',
  sql: 'sql',
}

function normalizeFenceLanguage(raw?: string, fallback?: string): string {
  const key = (raw || '').trim().toLowerCase()
  if (key && FENCE_LANG_ALIASES[key]) return FENCE_LANG_ALIASES[key]
  if (key) return key
  const fb = (fallback || '').trim().toLowerCase()
  return (fb && FENCE_LANG_ALIASES[fb]) || fb || 'typescript'
}

function QuestionCodeIdeBlock({
  code,
  language,
  deckId,
  fullContext,
  compact,
}: {
  code: string
  language: string
  deckId?: string | null
  fullContext?: string
  compact?: boolean
}) {
  const [copied, setCopied] = useState(false)
  const cleanCode = code.replace(/\n+$/, '')
  const linesCount = Math.max(cleanCode.split('\n').length, 1)
  const maxPx = compact ? 220 : 440
  const heightPx = `${Math.min(maxPx, Math.max(54, linesCount * 24 + 28))}px`

  const firstLine = cleanCode.split('\n')[0]?.trim() || ''
  const titleLabel =
    firstLine.startsWith('//') && firstLine.length <= 64
      ? firstLine.replace(/^\/\/\s*-*\s*/, '').replace(/\s*-*$/, '') || 'Question Code'
      : 'Question Code'

  return (
    <div
      className="my-2.5 rounded-xl border border-[#2d333b] bg-[#1a1a1a] shadow-lg overflow-hidden"
      onClick={(e) => e.stopPropagation()}
    >
      <div className="flex items-center justify-between gap-2 border-b border-[#2b3038] bg-[#20242c] px-3 py-1.5 text-xs">
        <div className="flex items-center gap-2 min-w-0">
          <span className="text-[#2cbb5d] font-bold font-mono select-none">&lt;/&gt;</span>
          <span className="rounded bg-[#282e38] border border-[#3a414d] px-1.5 py-0.5 font-mono text-[10px] font-semibold uppercase tracking-wide text-sky-300 shrink-0">
            {language}
          </span>
          <span className="text-[11px] font-medium text-slate-300 truncate">{titleLabel}</span>
          {!compact && (
            <span className="hidden md:inline text-[10px] text-slate-500 ml-1">
              · Highlight code to Define / Ask LLM
            </span>
          )}
        </div>
        <button
          type="button"
          onClick={(e) => {
            e.stopPropagation()
            void navigator.clipboard.writeText(cleanCode)
            setCopied(true)
            setTimeout(() => setCopied(false), 1800)
          }}
          className="rounded px-2 py-0.5 text-[11px] font-medium text-slate-300 hover:bg-[#2d333d] hover:text-white transition cursor-pointer shrink-0"
          title="Copy code snippet"
        >
          {copied ? 'Copied ✓' : 'Copy'}
        </button>
      </div>
      <CodeEditor
        code={cleanCode}
        onChange={() => {}}
        language={language}
        readOnly={true}
        hideHeader={true}
        hideFooter={true}
        borderless={true}
        height={heightPx}
        deckId={deckId}
        context={fullContext}
        placeholder=""
      />
    </div>
  )
}

function renderInlineMarkdown(text: string, keyPrefix: string): ReactNode[] {
  const nodes: ReactNode[] = []
  const tokenRegex = /(`[^`\n]+`|\*\*[^*\n]+\*\*|(?<=^|[\s(])_[^_\n]+_(?=$|[\s.,;:)!?]))/g
  let lastIdx = 0
  let match: RegExpExecArray | null
  let idx = 0

  while ((match = tokenRegex.exec(text)) !== null) {
    if (match.index > lastIdx) {
      nodes.push(<span key={`${keyPrefix}-t-${idx++}`}>{text.slice(lastIdx, match.index)}</span>)
    }
    const token = match[0]
    if (token.startsWith('`') && token.endsWith('`') && token.length >= 2) {
      nodes.push(
        <code
          key={`${keyPrefix}-c-${idx++}`}
          className="mx-0.5 rounded bg-slate-900/90 border border-slate-700/70 px-1.5 py-0.5 font-mono text-[0.86em] text-sky-200 break-words"
        >
          {token.slice(1, -1)}
        </code>,
      )
    } else if (token.startsWith('**') && token.endsWith('**') && token.length >= 4) {
      nodes.push(
        <strong key={`${keyPrefix}-b-${idx++}`} className="font-semibold text-white">
          {renderInlineMarkdown(token.slice(2, -2), `${keyPrefix}-bi-${idx}`)}
        </strong>,
      )
    } else if (token.startsWith('_') && token.endsWith('_') && token.length >= 2) {
      nodes.push(
        <em key={`${keyPrefix}-i-${idx++}`} className="italic text-slate-300">
          {renderInlineMarkdown(token.slice(1, -1), `${keyPrefix}-ii-${idx}`)}
        </em>,
      )
    } else {
      nodes.push(<span key={`${keyPrefix}-r-${idx++}`}>{token}</span>)
    }
    lastIdx = match.index + token.length
  }

  if (lastIdx < text.length) {
    nodes.push(<span key={`${keyPrefix}-e-${idx++}`}>{text.slice(lastIdx)}</span>)
  }
  return nodes
}

function renderMarkdownProse(chunk: string, keyPrefix: string): ReactNode {
  const mediaParts = chunk.split(/(!\[[^\]]*\]\([^)]+\)|\[audio\]\([^)]+\))/g)
  return mediaParts.map((part, mIdx) => {
    const img = part.match(/^!\[([^\]]*)\]\(([^)]+)\)$/)
    if (img) {
      const alt = img[1]
      const rawSrc = img[2]
      const src = rawSrc.startsWith('/')
        ? `${import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000'}${rawSrc}`
        : rawSrc
      return (
        <img
          key={`${keyPrefix}-img-${mIdx}`}
          src={src}
          alt={alt}
          className="my-2 max-h-72 rounded-lg border border-ink-line object-contain"
        />
      )
    }
    const audio = part.match(/^\[audio\]\(([^)]+)\)$/)
    if (audio) {
      const src = audio[1].startsWith('/')
        ? `${import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000'}${audio[1]}`
        : audio[1]
      return <audio key={`${keyPrefix}-aud-${mIdx}`} controls src={src} className="my-2 w-full" />
    }
    if (!part) return null

    const lines = part.split(/\r?\n/)
    return (
      <div key={`${keyPrefix}-p-${mIdx}`} className="space-y-1.5">
        {lines.map((line, lIdx) => {
          const trimmed = line.trim()
          if (!trimmed) {
            return <div key={lIdx} className="h-1" />
          }
          const headingMatch = line.match(/^\s*(#{1,3})\s+(.+)$/)
          if (headingMatch) {
            const level = headingMatch[1].length
            const cls =
              level === 1
                ? 'text-lg font-bold text-white pt-1'
                : level === 2
                ? 'text-base font-bold text-slate-100 pt-1'
                : 'text-sm font-bold text-sky-200 pt-0.5'
            return (
              <div key={lIdx} className={cls}>
                {renderInlineMarkdown(headingMatch[2], `${keyPrefix}-h-${mIdx}-${lIdx}`)}
              </div>
            )
          }
          const bulletMatch = line.match(/^\s*[-*•]\s+(.+)$/)
          if (bulletMatch) {
            return (
              <div key={lIdx} className="flex items-start gap-2 pl-2">
                <span className="text-sky-400 select-none mt-0.5 text-xs">•</span>
                <div className="min-w-0 flex-1">
                  {renderInlineMarkdown(bulletMatch[1], `${keyPrefix}-ul-${mIdx}-${lIdx}`)}
                </div>
              </div>
            )
          }
          const numMatch = line.match(/^\s*(\d+[.)])\s+(.+)$/)
          if (numMatch) {
            return (
              <div key={lIdx} className="flex items-start gap-2 pl-2">
                <span className="text-sky-300 font-semibold select-none shrink-0">{numMatch[1]}</span>
                <div className="min-w-0 flex-1">
                  {renderInlineMarkdown(numMatch[2], `${keyPrefix}-ol-${mIdx}-${lIdx}`)}
                </div>
              </div>
            )
          }
          return (
            <div key={lIdx} className="whitespace-pre-wrap break-words">
              {renderInlineMarkdown(line, `${keyPrefix}-ln-${mIdx}-${lIdx}`)}
            </div>
          )
        })}
      </div>
    )
  })
}

/** Renders markdown prose, inline code chips, media, and fenced code blocks inside read-only IDEs. */
export function RichText({
  text,
  className = '',
  codeLanguage,
  deckId,
  compactCode = false,
}: {
  text: string
  className?: string
  codeLanguage?: string
  deckId?: string | null
  compactCode?: boolean
}) {
  if (!text) return null

  const segments: Array<{ type: 'prose'; content: string } | { type: 'code'; lang: string; content: string }> = []
  const fenceRegex = /```([a-zA-Z0-9_+#.-]*)[ \t]*\r?\n([\s\S]*?)(?:\r?\n?```|$)/g
  let lastIndex = 0
  let match: RegExpExecArray | null

  while ((match = fenceRegex.exec(text)) !== null) {
    if (match.index > lastIndex) {
      const proseBefore = text.slice(lastIndex, match.index).trim()
      if (proseBefore) {
        segments.push({ type: 'prose', content: proseBefore })
      }
    }
    const lang = normalizeFenceLanguage(match[1], codeLanguage)
    segments.push({ type: 'code', lang, content: match[2] })
    lastIndex = match.index + match[0].length
  }

  if (lastIndex < text.length) {
    const trailing = text.slice(lastIndex).trim()
    if (trailing) {
      segments.push({ type: 'prose', content: trailing })
    }
  }

  if (segments.length === 0) {
    segments.push({ type: 'prose', content: text })
  }

  return (
    <div className={`min-w-0 space-y-2 break-words ${className}`}>
      {segments.map((seg, idx) =>
        seg.type === 'code' ? (
          <QuestionCodeIdeBlock
            key={`ide-${idx}`}
            code={seg.content}
            language={seg.lang}
            deckId={deckId}
            fullContext={text}
            compact={compactCode}
          />
        ) : (
          <div key={`prose-${idx}`}>{renderMarkdownProse(seg.content, `seg-${idx}`)}</div>
        ),
      )}
    </div>
  )
}

export function PriorityBar({ value }: { value: number }) {
  return (
    <span className="inline-flex items-center gap-2" title={`Priority ${value}/100`}>
      <span className="h-1.5 w-16 overflow-hidden rounded-full bg-ink-line">
        <span
          className="block h-full rounded-full bg-sky-400/70"
          style={{ width: `${Math.max(2, value)}%` }}
        />
      </span>
      <span className="text-xs tabular-nums text-slate-500">{value}</span>
    </span>
  )
}

export function Modal({
  title,
  onClose,
  children,
}: {
  title: string
  onClose: () => void
  children: ReactNode
}) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4 backdrop-blur-sm">
      <div className="w-full max-w-lg rounded-2xl border border-ink-line bg-[#0d1117] p-6 shadow-2xl space-y-4">
        <div className="flex items-center justify-between border-b border-ink-line/80 pb-3">
          <h3 className="text-base font-bold text-slate-100">{title}</h3>
          <button
            onClick={onClose}
            className="rounded-lg p-1 text-slate-400 hover:bg-ink-soft hover:text-slate-200 transition text-lg leading-none"
            title="Close"
          >
            &times;
          </button>
        </div>
        <div>{children}</div>
      </div>
    </div>
  )
}
