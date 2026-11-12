/**
 * Utilities for detecting expected solution lines (differentiating code the student
 * is expected to produce from boilerplate starter code) and handling RGB highlight colors.
 */

export const DEFAULT_TARGET_HIGHLIGHT_COLOR = '#10b981'

export const PRESET_HIGHLIGHT_COLORS = [
  { name: 'Emerald', hex: '#10b981' },
  { name: 'Cyan', hex: '#06b6d4' },
  { name: 'Blue', hex: '#3b82f6' },
  { name: 'Purple', hex: '#a855f7' },
  { name: 'Rose', hex: '#f43f5e' },
  { name: 'Amber', hex: '#f59e0b' },
] as const

export function hexToRgb(hex: string): { r: number; g: number; b: number } {
  let clean = hex.replace(/^#/, '').trim()
  if (clean.length === 3) {
    clean = clean
      .split('')
      .map((c) => c + c)
      .join('')
  }
  const num = parseInt(clean, 16)
  if (isNaN(num) || clean.length !== 6) {
    return { r: 16, g: 185, b: 129 }
  }
  return {
    r: (num >> 16) & 255,
    g: (num >> 8) & 255,
    b: num & 255,
  }
}

export function rgbToHex(r: number, g: number, b: number): string {
  const clamp = (v: number) => Math.max(0, Math.min(255, Math.round(v)))
  return (
    '#' +
    [clamp(r), clamp(g), clamp(b)]
      .map((x) => x.toString(16).padStart(2, '0'))
      .join('')
  )
}

/**
 * Computes 1-based line numbers in `refCode` that were added or modified
 * relative to `starterCode` (i.e. the code the student is expected to write).
 */
export function computeExpectedLines(
  starterCode?: string | null,
  refCode?: string | null
): Set<number> {
  const expectedLineNumbers = new Set<number>()
  if (!refCode || !refCode.trim()) {
    return expectedLineNumbers
  }

  const normalizedRef = refCode.replace(/\r\n/g, '\n')
  const refLines = normalizedRef.split('\n')

  // If no starter code is provided, all non-empty lines are target lines
  if (!starterCode || !starterCode.trim()) {
    refLines.forEach((line, idx) => {
      if (line.trim().length > 0) {
        expectedLineNumbers.add(idx + 1)
      }
    })
    return expectedLineNumbers
  }

  const normalizedStarter = starterCode.replace(/\r\n/g, '\n')
  const starterLines = normalizedStarter.split('\n')

  const m = starterLines.length
  const n = refLines.length

  // Fast prefix match
  let prefix = 0
  while (prefix < m && prefix < n && starterLines[prefix] === refLines[prefix]) {
    prefix++
  }

  // Fast suffix match
  let suffix = 0
  while (
    suffix < m - prefix &&
    suffix < n - prefix &&
    starterLines[m - 1 - suffix] === refLines[n - 1 - suffix]
  ) {
    suffix++
  }

  const sMid = starterLines.slice(prefix, m - suffix)
  const rMid = refLines.slice(prefix, n - suffix)

  if (sMid.length === 0) {
    // Pure additions in refCode
    for (let i = 0; i < rMid.length; i++) {
      expectedLineNumbers.add(prefix + i + 1)
    }
    return expectedLineNumbers
  }

  if (rMid.length === 0) {
    // Pure deletions from starterCode (no added lines in ref)
    return expectedLineNumbers
  }

  // DP LCS on middle divergent section
  const dp = Array.from({ length: sMid.length + 1 }, () => new Int32Array(rMid.length + 1))
  for (let i = 1; i <= sMid.length; i++) {
    for (let j = 1; j <= rMid.length; j++) {
      if (sMid[i - 1] === rMid[j - 1]) {
        dp[i][j] = dp[i - 1][j - 1] + 1
      } else {
        dp[i][j] = Math.max(dp[i - 1][j], dp[i][j - 1])
      }
    }
  }

  let i = sMid.length
  let j = rMid.length
  while (i > 0 || j > 0) {
    if (i > 0 && j > 0 && sMid[i - 1] === rMid[j - 1]) {
      i--
      j--
    } else if (j > 0 && (i === 0 || dp[i][j - 1] >= dp[i - 1][j])) {
      expectedLineNumbers.add(prefix + j)
      j--
    } else {
      i--
    }
  }

  return expectedLineNumbers
}

/** Returns the first (lowest) 1-based target line number, or null if none */
export function getFirstTargetLine(targetLines: Set<number>): number | null {
  if (targetLines.size === 0) return null
  let min = Infinity
  for (const l of targetLines) {
    if (l < min) min = l
  }
  return min === Infinity ? null : min
}

/** Formats a compact summary like "Ln 86-88 (3 lines)" or "3 lines" */
export function formatTargetLineSummary(targetLines: Set<number>): string {
  if (targetLines.size === 0) return ''
  const sorted = Array.from(targetLines).sort((a, b) => a - b)
  if (sorted.length === 1) {
    return `Ln ${sorted[0]}`
  }
  const min = sorted[0]
  const max = sorted[sorted.length - 1]
  if (max - min + 1 === sorted.length) {
    return `Ln ${min}–${max} (${sorted.length} lines)`
  }
  return `${sorted.length} lines`
}

/**
 * Returns the 1-based line number of the first incomplete/divergent line
 * between the user's solution code and the clean reference code.
 */
export function findIncompleteLineNumber(
  solutionCode: string,
  refCode: string
): number {
  if (!refCode) return 1
  const refLines = refCode.split('\n')
  const solLines = solutionCode.split('\n')

  if (!solutionCode.trim()) {
    const firstNonEmpty = refLines.findIndex((l) => l.trim().length > 0)
    return firstNonEmpty !== -1 ? firstNonEmpty + 1 : 1
  }

  let firstIncomplete = 1
  let found = false
  const maxScan = Math.min(solLines.length, refLines.length)

  for (let i = 0; i < maxScan; i++) {
    const s = solLines[i]
    const r = refLines[i]

    if (s === r) {
      continue
    }

    firstIncomplete = i + 1
    found = true
    break
  }

  if (!found) {
    if (solLines.length < refLines.length) {
      firstIncomplete = solLines.length + 1
    } else {
      firstIncomplete = Math.min(solLines.length, refLines.length)
    }
  }

  return Math.max(1, Math.min(firstIncomplete, refLines.length))
}
