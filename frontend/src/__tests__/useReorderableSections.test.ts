import { describe, it, expect } from 'vitest'
import { reconcileOrder } from '../hooks/useReorderableSections'

describe('reconcileOrder', () => {
  const defaultOrder = ['lesson', 'question', 'solution_preview'] as const

  it('returns defaultOrder if stored is null or non-array', () => {
    expect(reconcileOrder(null, defaultOrder)).toEqual(['lesson', 'question', 'solution_preview'])
    expect(reconcileOrder('invalid', defaultOrder)).toEqual(['lesson', 'question', 'solution_preview'])
    expect(reconcileOrder(123, defaultOrder)).toEqual(['lesson', 'question', 'solution_preview'])
  })

  it('preserves valid stored ordering', () => {
    const stored = ['question', 'solution_preview', 'lesson']
    expect(reconcileOrder(stored, defaultOrder)).toEqual(['question', 'solution_preview', 'lesson'])
  })

  it('appends missing items if stored array is missing an item', () => {
    const stored = ['solution_preview', 'question']
    expect(reconcileOrder(stored, defaultOrder)).toEqual(['solution_preview', 'question', 'lesson'])
  })

  it('filters out unknown or obsolete item IDs while keeping valid ones', () => {
    const stored = ['question', 'obsolete_section', 'lesson']
    expect(reconcileOrder(stored, defaultOrder)).toEqual(['question', 'lesson', 'solution_preview'])
  })

  it('removes duplicates in stored array', () => {
    const stored = ['question', 'question', 'lesson']
    expect(reconcileOrder(stored, defaultOrder)).toEqual(['question', 'lesson', 'solution_preview'])
  })
})
