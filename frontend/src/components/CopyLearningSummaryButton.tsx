import { useState, useCallback } from 'react'
import type { QueueItem, SubmitAnswerResponse, RunCodeResponse } from '../api/types'
import { copyLearningSummaryToClipboard } from '../utils/learningSummaryExport'

export interface CopyLearningSummaryButtonProps {
  item: QueueItem
  answer: string
  testCode?: string
  result: SubmitAnswerResponse | null
  codeLanguage?: string
  codeRunResult?: RunCodeResponse | null
  variant?: 'prominent' | 'compact'
  className?: string
}

export function CopyLearningSummaryButton({
  item,
  answer,
  testCode,
  result,
  codeLanguage = 'typescript',
  codeRunResult,
  variant = 'prominent',
  className = '',
}: CopyLearningSummaryButtonProps) {
  const [copied, setCopied] = useState(false)

  const handleCopy = useCallback(async () => {
    const success = await copyLearningSummaryToClipboard({
      item,
      answer,
      testCode,
      result,
      codeLanguage,
      codeRunResult,
    })
    if (success) {
      setCopied(true)
      setTimeout(() => setCopied(false), 2500)
    }
  }, [item, answer, testCode, result, codeLanguage, codeRunResult])

  if (variant === 'compact') {
    return (
      <button
        onClick={() => void handleCopy()}
        type="button"
        title="Copy summary (Ctrl+Shift+C)"
        className={`flex items-center gap-1.5 rounded border px-2.5 py-1 text-xs font-medium transition ${
          copied
            ? 'border-emerald-500/50 bg-emerald-500/15 text-emerald-300'
            : 'border-sky-500/30 bg-sky-500/10 text-sky-200 hover:bg-sky-500/20 hover:border-sky-500/50'
        } ${className}`}
      >
        <span>{copied ? '✓' : '📋'}</span>
        <span>{copied ? 'Copied' : 'Copy'}</span>
      </button>
    )
  }

  return (
    <button
      onClick={() => void handleCopy()}
      type="button"
      title="Copy summary (Ctrl+Shift+C)"
      className={`flex items-center justify-center gap-2 rounded-lg border px-3.5 py-2 text-xs font-medium shadow-sm transition ${
        copied
          ? 'border-emerald-500/60 bg-emerald-500/15 text-emerald-200 ring-1 ring-emerald-500/30'
          : 'border-sky-500/30 bg-sky-500/10 text-sky-200 hover:bg-sky-500/20 hover:border-sky-500/50 hover:text-white'
      } ${className}`}
    >
      <span className="text-sm">{copied ? '✓' : '📋'}</span>
      <span>{copied ? 'Copied' : 'Copy Summary'}</span>
      <span className="ml-1 rounded border border-current/25 px-1 py-0.2 font-mono text-[10px] opacity-75">
        Ctrl+Shift+C
      </span>
    </button>
  )
}
