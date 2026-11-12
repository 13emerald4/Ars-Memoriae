import { useCallback, useEffect, useRef, useState } from 'react'
import type { Grade } from '../api/types'

export interface BlitzStats {
  total: number
  correct: number
  avgLatencySec: number
  /** Cards per minute over the sprint. */
  cpm: number
  /** Share of answers given within the automaticity threshold, 0-100. */
  automaticityRate: number
}

/** Blitz Sprint: a fixed-length burst of rapid reviews with a scorecard at the
 *  end (Memory Athlete, Feature 4).
 *
 *  The clock is derived from a wall-clock deadline rather than decremented.
 *  An interval that subtracts one per tick drifts whenever it is restarted,
 *  and the old one restarted on every answer because its effect depended on
 *  the running tallies: a "60s" sprint ran long. */
export function useBlitzSprint(automaticityThresholdMs: number) {
  const [blitzActive, setBlitzActive] = useState(false)
  const [blitzDurationSec, setBlitzDurationSec] = useState(60)
  const [blitzTimeRemainingSec, setBlitzTimeRemainingSec] = useState(60)
  const [blitzCardsAnswered, setBlitzCardsAnswered] = useState(0)
  const [blitzCorrectCount, setBlitzCorrectCount] = useState(0)
  const [blitzLatencies, setBlitzLatencies] = useState<number[]>([])
  const [blitzSummaryOpen, setBlitzSummaryOpen] = useState(false)
  const [blitzStats, setBlitzStats] = useState<BlitzStats | null>(null)
  const deadlineRef = useRef(0)

  useEffect(() => {
    if (!blitzActive) return
    const tick = () =>
      setBlitzTimeRemainingSec(Math.max(0, Math.ceil((deadlineRef.current - Date.now()) / 1000)))
    tick()
    const timer = setInterval(tick, 250)
    return () => clearInterval(timer)
  }, [blitzActive])

  // Time is up: turn the final tallies into the scorecard.
  useEffect(() => {
    if (!blitzActive || blitzTimeRemainingSec > 0) return
    setBlitzActive(false)
    setBlitzStats(
      summarizeBlitz({
        answered: blitzCardsAnswered,
        correct: blitzCorrectCount,
        latenciesMs: blitzLatencies,
        durationSec: blitzDurationSec,
        automaticityThresholdMs,
      }),
    )
    setBlitzSummaryOpen(true)
  }, [
    blitzActive,
    blitzTimeRemainingSec,
    blitzCardsAnswered,
    blitzCorrectCount,
    blitzLatencies,
    blitzDurationSec,
    automaticityThresholdMs,
  ])

  const startBlitz = useCallback((durationSec: number) => {
    deadlineRef.current = Date.now() + durationSec * 1000
    setBlitzDurationSec(durationSec)
    setBlitzTimeRemainingSec(durationSec)
    setBlitzCardsAnswered(0)
    setBlitzCorrectCount(0)
    setBlitzLatencies([])
    setBlitzActive(true)
    setBlitzSummaryOpen(false)
    setBlitzStats(null)
  }, [])

  const stopBlitz = useCallback(() => setBlitzActive(false), [])

  /** Count one answered card toward the running sprint. */
  const recordBlitzAnswer = useCallback((grade: Grade, latencyMs: number) => {
    setBlitzCardsAnswered((n) => n + 1)
    if (grade === 'good' || grade === 'easy') setBlitzCorrectCount((n) => n + 1)
    setBlitzLatencies((all) => [...all, latencyMs])
  }, [])

  const closeBlitzSummary = useCallback(() => setBlitzSummaryOpen(false), [])

  return {
    blitzActive,
    blitzDurationSec,
    blitzTimeRemainingSec,
    blitzCardsAnswered,
    blitzSummaryOpen,
    blitzStats,
    startBlitz,
    stopBlitz,
    recordBlitzAnswer,
    closeBlitzSummary,
  }
}

/** Pure scorecard maths, separate from the hook so it can be tested. */
export function summarizeBlitz(input: {
  answered: number
  correct: number
  latenciesMs: number[]
  durationSec: number
  automaticityThresholdMs: number
}): BlitzStats {
  const { answered, correct, latenciesMs, durationSec, automaticityThresholdMs } = input
  const avgLatencyMs =
    latenciesMs.length > 0 ? latenciesMs.reduce((a, b) => a + b, 0) / latenciesMs.length : 0
  const automatic = latenciesMs.filter((ms) => ms <= automaticityThresholdMs).length
  return {
    total: answered,
    correct,
    avgLatencySec: Math.round(avgLatencyMs / 100) / 10,
    cpm: durationSec > 0 ? Math.round((answered / (durationSec / 60)) * 10) / 10 : 0,
    automaticityRate: answered > 0 ? Math.round((automatic / answered) * 100) : 100,
  }
}
