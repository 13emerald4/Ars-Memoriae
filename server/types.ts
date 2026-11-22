export type Grade = 'again' | 'hard' | 'good' | 'easy'

export interface UserRecord {
  id: string
  email: string
  password_hash: string
  token_version: number
  desired_retention: number
  grading_model: string
  queue_time_budget_minutes: number
  leech_remediation_opt_in: boolean
  daily_new_limit: number
  daily_review_limit: number
  backlog_spread_days: number
  leech_threshold: number
  llm_grading_consent: boolean
  fsrs_optimized_at: string | null
  grading_bias: number
  automaticity_threshold_ms: number | null
  target_event_date: string | null
  target_event_title: string | null
  peak_retention_target: number | null
  show_pre_leetcode: boolean
  show_code_lab: boolean
  show_thematic_context: boolean
  tutorial_completed: boolean
  timezone: string | null
  enable_schema_checkpoints: boolean
  enable_prompt_mutation: boolean
  enable_prediction_mode: boolean
  can_use_antigravity: boolean
}

export interface LexiconGlossItem {
  term: string
  source?: string
  definition?: string
  definitions?: string[]
  context_explanation?: string | null
  example?: string | null
  domain?: string | null
  pinned_at?: string
}

export interface CardReference {
  quote: string
  quote_verified: boolean
  locator: string | null
  source_title: string | null
  extract_id: string | null
  passage: string | null
}

export interface OcclusionPayload {
  image: string
  shapes: Array<{ id: string; x: number; y: number; w: number; h: number; label?: string }>
  target: string
  header?: string
}

export interface DeckRecord {
  id: string
  user_id: string
  name: string
  parent_id: string | null
  desired_retention_override: number | null
  default_priority: number
  position: number
  target_event_date: string | null
  target_event_title: string | null
  documentation: string | null
  thematic_nature: string | null
  source_documents: Array<Record<string, unknown>>
  created_at: string
}

export interface NoteTypeRecord {
  id: string
  user_id: string
  name: string
  template_kind: string
  fields: Record<string, unknown>
  grading_profile: string
}

export interface CardRecord {
  id: string
  user_id: string
  note_id: string
  deck_id: string
  template_slot: string
  template_kind: string
  grading_profile: string
  state: 'new' | 'learning' | 'review' | 'relearning'
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
  image: string | null
  back_image: string | null
  occlusion: OcclusionPayload | null
  references: CardReference[]
  starter_code: string | null
  starter_tests: string | null
  test_cases: Array<{ input: unknown; expected: unknown }>
  time_complexity: string | null
  space_complexity: string | null
  edge_cases: string[]
  title: string | null
  difficulty_label: string | null
  category: string | null
  documentation: string | null
  thematic_nature: string | null
  source_documents: Array<Record<string, unknown>>
  lexicon_glosses: LexiconGlossItem[]
  position: number
  memory_note: string | null
  active_weaknesses: string[]
  weakness_history: Array<Record<string, unknown>>
  failure_reminder: string | null
  last_grade: Grade | null
  review_count: number
  is_schema_checkpoint: boolean
  spatial_x: number | null
  spatial_y: number | null
  spatial_locus: string | null
  mnemonic_vignette: string | null
  created_at: string
}

export interface ReviewLogRecord {
  id: number
  user_id: string
  card_id: string
  reviewed_at: string
  final_grade: Grade
  typed_answer: string | null
  latency_ms: number | null
  llm_grade: Grade | null
  llm_reasoning: string | null
  llm_confidence: number | null
  overridden: boolean
  user_confidence: number | null
  is_blitz: boolean
  weaknesses: string[]
  improvements: string[]
  stability_before: number
  stability_after: number
  retrievability_before: number
  client_review_id: string | null
}

export interface TreeNodeRecord {
  id: string
  user_id: string
  parent_id: string | null
  kind: 'topic' | 'deck' | 'source' | 'extract'
  title: string
  position: number
  collapsed: boolean
  priority: number
  priority_inherited: boolean
  deck_id: string | null
  source_id: string | null
  extract_id: string | null
  requires_node_id: string | null
  mastery_threshold: number
}

export interface SourceRecord {
  id: string
  user_id: string
  title: string
  url: string | null
  raw_text: string
  priority: number
  status: string
  created_at: string
  for_reading: boolean
}

export interface ExtractRecord {
  id: string
  user_id: string
  source_id: string
  content: string
  priority: number
  position: number
  locator: string | null
  next_shown_at: string | null
  status: 'active' | 'scheduled' | 'done' | 'archived'
}

export interface StudySessionRecord {
  id: string
  user_id: string
  started_at: string
  ended_at: string | null
  planned_seconds: number
  active_seconds: number
  focus_goal: string | null
  goal_cards: number
  cards_reviewed: number
  banked_seconds: number
  goal_met: boolean
  distraction: string | null
  next_time_plan: string | null
}

export interface QueueConfigRecord {
  review_weight: number
  new_weight: number
  ir_weight: number
  seconds_per_review: number
  seconds_per_ir_extract: number
}

export interface SisterPairRecord {
  id: string
  user_id: string
  kind: 'interference' | 'duplicate' | 'convergent'
  status: 'active' | 'dismissed'
  front_similarity: number
  back_similarity: number
  note_a_id: string
  note_b_id: string
  front_a: string
  back_a: string
  front_b: string
  back_b: string
}

export interface ConceptEdgeRecord {
  id: string
  user_id: string
  source_card_id: string
  target_card_id: string
  relationship_type: string
  weight: number
  created_at: string
}

export interface CodeProblemRecord {
  id: string
  kind: 'fundamental' | 'problem'
  track: string | null
  title: string
  slug: string
  difficulty: 'Easy' | 'Medium' | 'Hard'
  category: string
  tags: string[]
  description: string
  examples: Array<{ input: string; output: string; explanation?: string }>
  constraints: string[]
  starter_codes: Record<string, string>
  solutions: Record<string, string>
  editorial: string | null
  test_cases: Array<{ input: unknown; expected: unknown }>
  hints: string[]
  created_at: string
}

export interface CodeSubmissionRecord {
  id: string
  user_id: string
  problem_id: string
  language: string
  code: string
  status: string
  passed_tests: number
  total_tests: number
  runtime_ms: number | null
  error: string | null
  created_at: string
}

export interface ImportRecordItem {
  id: string
  user_id: string
  filename: string
  imported_at: string
  notes_mapped: number
  cards_mapped: number
  warnings: string[]
}

export interface DeckDocumentRecord {
  id: string
  deck_id: string
  user_id: string
  source_id: string
  filename: string
  title: string
  segment_count: number
  locators: string[]
  uploaded_at: string
}

export interface RecentLexiconRecord {
  user_id: string
  term: string
  definition: string
  domain: string | null
  created_at: string
}
