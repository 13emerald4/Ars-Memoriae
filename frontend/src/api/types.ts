/** Mirrors backend/app/schemas — §7.1 is the contract Review.tsx depends on. */

export type Grade = 'again' | 'hard' | 'good' | 'easy'
export const GRADES: Grade[] = ['again', 'hard', 'good', 'easy']

export interface OcclusionShape {
  id: string
  x: number
  y: number
  w: number
  h: number
  label?: string
}

export interface OcclusionPayload {
  image: string
  shapes: OcclusionShape[]
  target: string
  header?: string
}

export interface SisterPair {
  id: string
  kind: 'interference' | 'duplicate' | 'convergent'
  status: string
  front_similarity: number
  back_similarity: number
  note_a_id: string
  note_b_id: string
  front_a: string
  back_a: string
  front_b: string
  back_b: string
}

export interface QueueItem {
  kind: 'card' | 'extract'
  id: string
  deck_or_source_id: string
  front: string | null
  extract_content: string | null
  priority: number
  effective_priority: number
  deck_name: string | null
  source_title: string | null
  state: string | null
  template_kind: string | null
  grading_profile: string | null
  note_id: string | null
  occlusion: OcclusionPayload | null
}

export interface SessionSummary {
  counts: Record<string, number>
  caps: Record<string, number>
  budget_seconds: number
  notes: string[]
  items: QueueItem[]
}

export interface SubmitAnswerResponse {
  suggested_grade: Grade
  confidence: number
  matched_points: string[]
  missed_points: string[]
  reasoning: string
  degraded_to_manual: boolean
  reference_answer: string
  needs_confirmation: boolean
  heuristic_overlap: number | null
  model_used: string | null
  cached: boolean
  degraded_reason: string | null
}

export interface ConfirmReviewResponse {
  next_due: string
  new_stability: number
  new_difficulty: number
  state: string
  interval_days: number
  lapse_count: number
  leech_flagged: boolean
}

export interface User {
  id: string
  email: string
  desired_retention: number
  grading_model: string
  queue_time_budget_minutes: number
  leech_remediation_opt_in: boolean
  daily_new_limit: number
  daily_review_limit: number
  backlog_spread_days: number
  leech_threshold: number
  llm_grading_consent: boolean
  has_api_key: boolean
  api_key_masked: string | null
  fsrs_optimized_at: string | null
  grading_bias: number
}

export interface Deck {
  id: string
  name: string
  parent_id: string | null
  desired_retention_override: number | null
  default_priority: number
  card_count: number
  due_count: number
  new_count: number
}

export interface NoteType {
  id: string
  name: string
  template_kind: string
  fields: Record<string, unknown>
  grading_profile: string
}

export interface Card {
  id: string
  note_id: string
  deck_id: string
  deck_name: string | null
  template_slot: string
  state: string
  due: string | null
  stability: number | null
  difficulty: number | null
  priority: number
  lapse_count: number
  leech_flag: boolean
  suspended: boolean
  tags: string[]
  front: string
  back: string
  occlusion: OcclusionPayload | null
}

export interface Source {
  id: string
  title: string
  url: string | null
  priority: number
  status: string
  created_at: string
  extract_count: number
  active_extract_count: number
}

export interface Extract {
  id: string
  source_id: string
  source_title: string | null
  content: string
  priority: number
  position: number
  next_shown_at: string | null
  status: string
}

export interface SuggestedCard {
  kind: string
  front: string
  back: string
  cloze_text: string | null
}

export interface GenerateCardsResponse {
  suggestions: SuggestedCard[]
  degraded: boolean
  reason: string | null
}

export interface Leech {
  card_id: string
  front: string
  back: string
  lapse_count: number
  deck_name: string | null
  suggestion_id: string | null
  suggestion_kind: string | null
  suggestion_rationale: string | null
  suggested_cards: { front?: string; back?: string }[]
}

export interface Stats {
  heatmap: Record<string, number>
  forecast: Record<string, number>
  retention: Record<string, number>
  totals: Record<string, number>
  grading: Record<string, number>
  ir_throughput: Record<string, number>
  leeches: Leech[]
}

export interface ImportResult {
  id: string
  filename: string
  notes_mapped: number
  cards_mapped: number
  review_logs_mapped: number
  media_copied: number
  decks_created: number
  warnings: string[]
  fsrs_optimized: boolean
}

export interface QueueConfig {
  review_weight: number
  new_weight: number
  ir_weight: number
  seconds_per_review: number
  seconds_per_ir_extract: number
}
