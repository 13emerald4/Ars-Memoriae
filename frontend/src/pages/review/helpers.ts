import type { Grade, QueueItem, RunCodeResponse } from '../../api/types'
import { isCodeCard as checkIsCodeCard, looksLikeCode } from '../../utils/codeUtils'

// Mirrors the backend's SCORE_BANDS (grading_service.py) — display only; the
// server is the one source of truth for which band a score actually lands in.
export const GRADE_BAND: Record<Grade, string> = {
  again: '0–39%',
  hard: '40–69%',
  good: '70–89%',
  easy: '90–100%',
}

export const GRADE_STYLE: Record<Grade, string> = {
  again: 'border-rose-500/40 text-rose-300 hover:bg-rose-500/15',
  hard: 'border-amber-500/40 text-amber-300 hover:bg-amber-500/15',
  good: 'border-emerald-500/40 text-emerald-300 hover:bg-emerald-500/15',
  easy: 'border-sky-500/40 text-sky-300 hover:bg-sky-500/15',
}

export function buildStarterTestCode(item: QueueItem | null): string {
  if (!item) return ''
  return item.starter_tests || ''
}

export function formatExecutionSummary(res: RunCodeResponse | null): string | null {
  if (!res) return null
  const parts: string[] = [
    `Status: ${res.status}`,
    `Tests Passed: ${res.passed_count}/${res.total_count} (${res.runtime_ms}ms)`,
  ]
  if (
    res.student_total_count !== undefined &&
    res.student_total_count > 0 &&
    res.student_passed_count !== undefined
  ) {
    parts.push(`Student Unit Tests: ${res.student_passed_count}/${res.student_total_count}`)
  }
  if (res.error) {
    parts.push(`Execution Error:\n${res.error.slice(0, 1200)}`)
  }
  const failedCases = (res.results || []).filter((r) => !r.passed).slice(0, 3)
  if (failedCases.length > 0) {
    parts.push(
      'Failed Test Cases:\n' +
        failedCases
          .map(
            (r) =>
              `  - Test #${r.test_index}: input=${JSON.stringify(r.input)} expected=${JSON.stringify(
                r.expected,
              )} actual=${JSON.stringify(r.actual)}${r.error ? ` err=${r.error}` : ''}${
                r.stdout ? ` stdout=${r.stdout.slice(0, 200)}` : ''
              }`,
          )
          .join('\n'),
    )
  }
  const failedStudentTests = (res.student_tests || []).filter((st) => !st.passed).slice(0, 3)
  if (failedStudentTests.length > 0) {
    parts.push(
      'Failed Student Tests:\n' +
        failedStudentTests
          .map((st) => `  - ${st.test_name}: ${st.error || 'failed'}`)
          .join('\n'),
    )
  }
  return parts.join('\n')
}


export function buildCompletedTestCode(item: QueueItem | null): string {
  if (!item) return ''
  if ((item as any).reference_tests) return (item as any).reference_tests
  if ((item as any).test_solution) return (item as any).test_solution

  const isCode = Boolean(
    item.starter_code ||
      (item.test_cases && item.test_cases.length > 0) ||
      item.starter_tests ||
      checkIsCodeCard(item) ||
      looksLikeCode(item.back)
  )
  if (!isCode) return ''

  const cases = item.test_cases || []
  if (cases.length === 0 && item.starter_tests) {
    return item.starter_tests
  }

  const codeToScan = item.starter_code || item.back || ''
  const isPython = Boolean(codeToScan.includes('def ') || codeToScan.includes('class Solution:'))

  if (isPython) {
    const fnMatch = codeToScan.match(/def\s+([a-zA-Z0-9_]+)/)
    const fnName = fnMatch ? fnMatch[1] : 'solution'

    const testMethods = cases
      .map((tc, idx) => {
        let args = ''
        if (tc.input && typeof tc.input === 'object' && !Array.isArray(tc.input)) {
          args = Object.values(tc.input)
            .map((v) => JSON.stringify(v))
            .join(', ')
        } else {
          args = JSON.stringify(tc.input)
        }
        const exp = JSON.stringify(tc.expected)
        const label = idx === 0 ? 'sample_case' : idx === 1 ? 'boundary_threshold' : `edge_case_${idx}`
        return `    def test_${label}(self):\n        self.assertEqual(${fnName}(${args}), ${exp})`
      })
      .join('\n\n')

    return `# Completed Reference Unit Tests (Python)
import unittest

class TestSolution(unittest.TestCase):
${testMethods || '    pass'}
`
  }

  // TypeScript / JavaScript
  const fnName =
    codeToScan.match(/(?:function\s+|const\s+|let\s+|var\s+)?([a-zA-Z0-9_$]+)\s*(?:=\s*(?:async\s*)?\([^)]*\)\s*=>|\()/)?.[1] ||
    codeToScan.match(/function\s+([a-zA-Z0-9_$]+)/)?.[1] ||
    'solution'
  const edgeNotes = item.edge_cases || []

  const testBlocks = cases.map((tc, idx) => {
    let args = ''
    if (tc.input && typeof tc.input === 'object' && !Array.isArray(tc.input)) {
      args = Object.values(tc.input)
        .map((v) => JSON.stringify(v))
        .join(', ')
    } else {
      args = JSON.stringify(tc.input)
    }
    const exp = JSON.stringify(tc.expected)

    let testName = `case ${idx + 1}`
    if (idx === 0) {
      testName = 'sample case'
    } else if (idx === 1) {
      testName = 'boundary threshold case'
    } else if (edgeNotes[idx - 2]) {
      testName = `edge case: ${edgeNotes[idx - 2]}`
    } else {
      testName = `test case ${idx + 1}`
    }

    return `test('${testName}', checkExpect(() => ${fnName}(${args}), ${exp}));`
  })

  return `// Completed reference unit tests
// Full suite asserting sample, boundary, and edge cases

${testBlocks.join('\n\n')}
`
}


export function formatLatencyNote(note: string | null | undefined): string | null | undefined {
  if (!note) return note
  const m = note.match(/^answered in (\d+)s$/)
  if (m) {
    const s = parseInt(m[1], 10)
    const mins = Math.floor(s / 60)
    const rem = s % 60
    return `answered in ${mins}m ${rem}s`
  }
  const m2 = note.match(/^answered in (\d+)m$/)
  if (m2) {
    return `answered in ${m2[1]}m 0s`
  }
  if (note === 'answered in under a second') {
    return 'answered in 0m 0s'
  }
  return note
}

export function formatInterval(days: number): string {
  if (days < 1 / 24) return `${Math.max(1, Math.round(days * 1440))} min`
  if (days < 1) return `${Math.round(days * 24)} h`
  if (days < 30) return `${Math.round(days)} d`
  if (days < 365) return `${(days / 30).toFixed(1)} mo`
  return `${(days / 365).toFixed(1)} y`
}
