import { describe, expect, it } from 'vitest'
import type { RunCodeResponse } from '../api/types'
import { summarizeBlitz } from '../hooks/useBlitzSprint'
import {
  buildCompletedTestCode,
  formatExecutionSummary,
  formatInterval,
  formatLatencyNote,
} from '../pages/review/helpers'

describe('formatExecutionSummary', () => {
  const failing: RunCodeResponse = {
    status: 'Wrong Answer',
    passed_count: 1,
    total_count: 2,
    runtime_ms: 12,
    results: [
      { test_index: 1, passed: true, input: { a: 1 }, expected: 1, actual: 1, stdout: '', runtime_ms: 5 },
      { test_index: 2, passed: false, input: { a: 2 }, expected: 4, actual: 5, stdout: '', runtime_ms: 5 },
    ],
  } as RunCodeResponse

  it('is null without a run', () => {
    expect(formatExecutionSummary(null)).toBeNull()
  })

  it("reports a failing test under the backend's own 1-based number", () => {
    // The runner numbers tests from 1. This text is what the Socratic guide
    // reads; it used to add 1 again and point the model at the wrong test.
    const summary = formatExecutionSummary(failing)!
    expect(summary).toContain('Tests Passed: 1/2')
    expect(summary).toContain('Test #2:')
    expect(summary).not.toContain('Test #3:')
  })
})

describe('formatInterval', () => {
  it('picks a readable unit', () => {
    const minutes = formatInterval(10 / (24 * 60))
    const days = formatInterval(3)
    expect(minutes).toMatch(/min/)
    expect(days).toMatch(/3/)
    expect(days).toMatch(/d/)
  })
})

describe('formatLatencyNote', () => {
  it('normalises the server phrasing to minutes and seconds', () => {
    expect(formatLatencyNote('answered in 75s')).toBe('answered in 1m 15s')
    expect(formatLatencyNote('answered in 3m')).toBe('answered in 3m 0s')
    expect(formatLatencyNote('answered in under a second')).toBe('answered in 0m 0s')
  })

  it('passes anything else through', () => {
    expect(formatLatencyNote('something new')).toBe('something new')
    expect(formatLatencyNote(null)).toBeNull()
    expect(formatLatencyNote(undefined)).toBeUndefined()
  })
})

describe('buildCompletedTestCode', () => {
  it('is empty for a prose card', () => {
    expect(
      buildCompletedTestCode({ id: '1', kind: 'card', front: 'Define osmosis.', back: 'Water moves.' } as never),
    ).toBe('')
  })

  it('writes one assertion per test case for a TypeScript card', () => {
    const code = buildCompletedTestCode({
      id: '1',
      kind: 'card',
      front: 'Write sum',
      back: 'function sum(nums: number[]): number { return 0 }',
      starter_code: 'function sum(nums: number[]): number {\n}',
      test_cases: [
        { input: { nums: [1, 2] }, expected: 3 },
        { input: { nums: [] }, expected: 0 },
      ],
    } as never)
    expect(code).toContain('sum([1,2])')
    expect(code).toContain('sum([])')
    expect(code.match(/checkExpect/g)).toHaveLength(2)
    // No course-specific header in generated code.
    expect(code).not.toMatch(/CPSC/)
  })
})

describe('summarizeBlitz', () => {
  it('computes pace, latency and automaticity', () => {
    const stats = summarizeBlitz({
      answered: 4,
      correct: 3,
      latenciesMs: [1000, 2000, 3000, 6000],
      durationSec: 60,
      automaticityThresholdMs: 3000,
    })
    expect(stats).toEqual({ total: 4, correct: 3, avgLatencySec: 3, cpm: 4, automaticityRate: 75 })
  })

  it('does not divide by zero on an empty sprint', () => {
    const stats = summarizeBlitz({
      answered: 0,
      correct: 0,
      latenciesMs: [],
      durationSec: 30,
      automaticityThresholdMs: 3000,
    })
    expect(stats.avgLatencySec).toBe(0)
    expect(stats.cpm).toBe(0)
    expect(stats.automaticityRate).toBe(100)
  })
})
