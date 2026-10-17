import type { QueueItem, SubmitAnswerResponse, RunCodeResponse } from '../api/types'

export interface LearningSummaryData {
  item: QueueItem
  answer: string
  testCode?: string
  result: SubmitAnswerResponse | null
  codeLanguage?: string
  codeRunResult?: RunCodeResponse | null
}

const GRADE_BAND_LABELS: Record<string, string> = {
  again: 'Again (0–39%)',
  hard: 'Hard (40–69%)',
  good: 'Good (70–89%)',
  easy: 'Easy (90–100%)',
}

/**
 * Builds a clean, comprehensive Markdown summary of the reviewed item,
 * including question prompt, submitted answer, LLM diagnostics, reference answer,
 * and test case results.
 */
export function buildLearningSummaryMarkdown(data: LearningSummaryData): string {
  const { item, answer, result, codeLanguage = 'typescript', codeRunResult } = data

  const title = item.title || item.front || 'Untitled Problem'
  const isCode = Boolean(item.starter_code || item.test_cases?.length || codeRunResult || item.time_complexity)

  const lines: string[] = []

  // Title & Metadata
  lines.push(`# 📚 Review: ${title}`)
  const metaParts: string[] = []
  if (item.deck_name) metaParts.push(`**Deck:** \`${item.deck_name}\``)
  if (item.difficulty) metaParts.push(`**Difficulty:** ${item.difficulty.toUpperCase()}`)
  if (item.category) metaParts.push(`**Category:** ${item.category}`)
  if (metaParts.length > 0) {
    lines.push(metaParts.join(' • '))
  }
  lines.push('')
  lines.push('---')
  lines.push('')

  // 1. Problem / Question Prompt
  lines.push('## ❓ Question')
  if (item.front) {
    lines.push(item.front.trim())
  } else if (item.extract_content) {
    lines.push(item.extract_content.trim())
  }
  lines.push('')

  if (item.time_complexity || item.space_complexity || (item.edge_cases && item.edge_cases.length > 0)) {
    lines.push('### 🎯 Constraints')
    if (item.time_complexity) lines.push(`- **Time Complexity:** \`${item.time_complexity}\``)
    if (item.space_complexity) lines.push(`- **Space Complexity:** \`${item.space_complexity}\``)
    if (item.edge_cases && item.edge_cases.length > 0) {
      lines.push(`- **Edge Cases:** ${item.edge_cases.join(', ')}`)
    }
    lines.push('')
  }

  lines.push('---')
  lines.push('')

  // 2. Student Submitted Answer
  const submittedSectionTitle = isCode
    ? `## 💻 Submitted Answer (${codeLanguage})`
    : '## ✍️ Submitted Answer'
  lines.push(submittedSectionTitle)

  if (answer.trim()) {
    if (isCode) {
      lines.push('```' + codeLanguage)
      lines.push(answer.trim())
      lines.push('```')
    } else {
      lines.push(answer.trim())
    }
  } else {
    lines.push('*(No answer submitted)*')
  }
  lines.push('')

  // 2b. Student Authored Unit Tests (if provided)
  if (data.testCode && data.testCode.trim()) {
    lines.push(`## 🧪 Unit Tests (${codeLanguage})`)
    lines.push('```' + codeLanguage)
    lines.push(data.testCode.trim())
    lines.push('```')
    lines.push('')
  }

  // 3. Test Sandbox Results (if applicable)
  if (codeRunResult) {
    lines.push('## 🧪 Test Results')
    if (codeRunResult.student_tests && codeRunResult.student_tests.length > 0) {
      lines.push(
        `- **Unit Tests:** ${codeRunResult.student_passed_count ?? 0}/${codeRunResult.student_total_count ?? 0} passed`
      )
      for (const st of codeRunResult.student_tests) {
        lines.push(`  - ${st.passed ? '✓' : '✗'} ${st.test_name}${st.error ? ` (${st.error})` : ''}`)
      }
    }
    if (codeRunResult.results && codeRunResult.results.length > 0) {
      lines.push(
        `- **Test Suite:** ${codeRunResult.passed_count}/${codeRunResult.total_count} passed`
      )
    }
    lines.push(`- **Runtime:** ${codeRunResult.runtime_ms} ms`)
    if (codeRunResult.error) {
      lines.push(`- **Error:** \`${codeRunResult.error}\``)
    }
    lines.push('')
  }

  // 4. LLM Grader Assessment & Diagnostics
  if (result) {
    lines.push('---')
    lines.push('')
    lines.push('## 🤖 Grader Assessment')

    if (result.degraded_to_manual) {
      lines.push(`> ⚠️ **Manual Grading**: Automated evaluation was unavailable (${result.degraded_reason || 'Manual'}).`)
    } else {
      const gradeLabel = GRADE_BAND_LABELS[result.suggested_grade] || result.suggested_grade
      lines.push(`- **Grade:** ${gradeLabel}`)
      if (result.score !== null && result.score !== undefined) {
        lines.push(`- **Score:** ${Math.round(result.score)}%`)
      }
      lines.push(`- **Confidence:** ${Math.round(result.confidence * 100)}%`)
      if (result.model_used) {
        lines.push(`- **Model:** \`${result.model_used}\``)
      }
      lines.push('')

      if (result.reasoning) {
        lines.push('### 📝 Reasoning')
        lines.push(result.reasoning.trim())
        lines.push('')
      }

      const missed = result.missed_points || []
      const overlooked = result.overlooked_phrases || []
      const combinedOverlooked = Array.from(new Set([...missed, ...overlooked])).filter(Boolean)

      if (combinedOverlooked.length > 0) {
        lines.push('### ⚠️ Overlooked Points')
        for (const pt of combinedOverlooked) {
          lines.push(`- ${pt}`)
        }
        lines.push('')
      }

      if (result.matched_points && result.matched_points.length > 0) {
        lines.push('### ✅ Matched Points')
        for (const pt of result.matched_points) {
          lines.push(`- ${pt}`)
        }
        lines.push('')
      }

      if (result.improvements && result.improvements.length > 0) {
        lines.push('### 💡 Improvements')
        for (const imp of result.improvements) {
          lines.push(`- ${imp}`)
        }
        lines.push('')
      }
    }
  }

  // 5. Reference Solution
  const refSolution = result?.reference_answer || item.back
  if (refSolution && refSolution.trim()) {
    lines.push('---')
    lines.push('')
    lines.push('## 💡 Reference')
    if (isCode) {
      lines.push('```' + codeLanguage)
      lines.push(refSolution.trim())
      lines.push('```')
    } else {
      lines.push(refSolution.trim())
    }
    lines.push('')
  }

  return lines.join('\n')
}

/**
 * Copies the formatted learning summary Markdown to the user's system clipboard.
 * Supports modern Clipboard API with fallback for non-standard environments.
 */
export async function copyLearningSummaryToClipboard(data: LearningSummaryData): Promise<boolean> {
  const markdown = buildLearningSummaryMarkdown(data)

  if (typeof navigator !== 'undefined' && navigator.clipboard && navigator.clipboard.writeText) {
    try {
      await navigator.clipboard.writeText(markdown)
      return true
    } catch {
      // Fallback below
    }
  }

  // Fallback for document.execCommand
  try {
    const textArea = document.createElement('textarea')
    textArea.value = markdown
    textArea.style.position = 'fixed'
    textArea.style.left = '-999999px'
    textArea.style.top = '-999999px'
    document.body.appendChild(textArea)
    textArea.focus()
    textArea.select()
    const successful = document.execCommand('copy')
    document.body.removeChild(textArea)
    return successful
  } catch (err) {
    console.error('Failed to copy learning summary to clipboard', err)
    return false
  }
}
