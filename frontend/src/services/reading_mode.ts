/**
 * Reading modes for the Guttag lesson pane.
 *
 * Every lesson editorial is written to the same five-section template:
 *
 *   § 1  Theoretical Foundations      — the core idea
 *   § 2  Textbook Reading             — Guttag's argument, reconstructed
 *   § 3  Canonical Code Walkthrough   — the worked example
 *   § 4  Common Pitfalls & Invariants — the edge cases
 *   § 5  Bridging to LeetCode Mastery — where it shows up in practice
 *
 * A mode selects which of those sections to show, so each higher mode is a
 * strict superset of the one below it. There is a single source of truth for
 * the content — no per-mode copies to keep in sync, and any lesson added later
 * gets all three modes for free.
 */

export type ReadingMode = 'concise' | 'normal' | 'robust'

/** Sections shown per mode. Each list is a superset of the previous one. */
const MODE_SECTIONS: Record<ReadingMode, number[]> = {
  // Concept + where it's used: enough to attempt the exercise.
  concise: [1, 5],
  // Adds the worked code walkthrough.
  normal: [1, 3, 5],
  // Everything, including the textbook grounding and the pitfalls.
  robust: [1, 2, 3, 4, 5],
}

export const READING_MODES: {
  id: ReadingMode
  label: string
  hint: string
}[] = [
  { id: 'concise', label: 'Concise', hint: 'Core idea + LeetCode transfer' },
  { id: 'normal', label: 'Normal', hint: 'Adds the worked code walkthrough' },
  { id: 'robust', label: 'Robust', hint: 'Adds textbook reading + pitfalls' },
]

export const TOTAL_SECTIONS = MODE_SECTIONS.robust.length

const SECTION_HEADING = /^###\s*§\s*(\d+)\./

interface ParsedSection {
  num: number
  text: string
}

/** Drop a trailing horizontal rule so re-joining doesn't double it up. */
function stripTrailingRule(block: string): string {
  return block.replace(/\n+---\s*$/, '').trimEnd()
}

function parseSections(markdown: string): {
  preamble: string
  sections: ParsedSection[]
} {
  const preamble: string[] = []
  const collected: { num: number; lines: string[] }[] = []
  let current: { num: number; lines: string[] } | null = null

  for (const line of markdown.split('\n')) {
    const match = SECTION_HEADING.exec(line)
    if (match) {
      current = { num: Number(match[1]), lines: [line] }
      collected.push(current)
    } else if (current) {
      current.lines.push(line)
    } else {
      preamble.push(line)
    }
  }

  return {
    preamble: preamble.join('\n'),
    sections: collected.map((s) => ({ num: s.num, text: s.lines.join('\n') })),
  }
}

/**
 * Returns the editorial trimmed to the sections the mode calls for.
 * Falls back to the full text whenever the expected structure isn't found,
 * so an unconventional lesson degrades to "show everything" rather than blank.
 */
export function filterEditorialByMode(markdown: string, mode: ReadingMode): string {
  if (!markdown) return markdown
  if (mode === 'robust') return markdown

  const keep = new Set(MODE_SECTIONS[mode])
  const { preamble, sections } = parseSections(markdown)
  const kept = sections.filter((s) => keep.has(s.num))
  if (kept.length === 0) return markdown

  const blocks = [stripTrailingRule(preamble), ...kept.map((s) => stripTrailingRule(s.text))]
  return blocks.filter(Boolean).join('\n\n---\n\n') + '\n'
}

/** How many sections this mode shows for this lesson, and how many exist. */
export function sectionCount(
  markdown: string,
  mode: ReadingMode
): { shown: number; total: number } {
  const { sections } = parseSections(markdown)
  const total = sections.length || TOTAL_SECTIONS
  if (mode === 'robust') return { shown: total, total }
  const keep = new Set(MODE_SECTIONS[mode])
  return { shown: sections.filter((s) => keep.has(s.num)).length, total }
}

/** Rough reading-time label. Prose reads at roughly 200 wpm. */
export function estimateReadMinutes(markdown: string): string {
  const words = markdown.trim().split(/\s+/).filter(Boolean).length
  const minutes = words / 200
  if (minutes < 1.5) return '~1 min'
  if (minutes < 2.5) return '~2 min'
  const low = Math.max(2, Math.floor(minutes))
  return `~${low}–${low + 2} min`
}
