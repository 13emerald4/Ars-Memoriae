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

/** Where a card's answer comes from in an uploaded document. */
export interface CardReference {
  quote: string
  /** False when the model's quote couldn't be found in the source — a
   *  hallucinated citation, which the UI must not present as real. */
  quote_verified: boolean
  locator: string | null
  source_title: string | null
  extract_id: string | null
  passage: string | null
}

/** Learn & Practice: what to teach before a card's question. */
export interface Lesson {
  /** False when the card has no citations to teach from. */
  available: boolean
  reason: string | null
  body: string
  key_points: string[]
  /** False when `body` is the cited passage verbatim rather than a written
   *  lesson — the UI must label that honestly. */
  generated: boolean
  model_used: string | null
  cached: boolean
  citations: CardReference[]
}

export interface SocraticTurn {
  role: 'guide' | 'student'
  text: string
}

export interface SocraticResponse {
  message: string
  on_track: boolean
  degraded: boolean
  degraded_reason: string | null
  model_used: string | null
  vram_constrained?: boolean
  failed_model?: string | null
  fallback_model?: string | null
  available_fallback_models?: string[]
}

export interface SocraticLineHintRequest {
  code: string
  line_number: number
  language?: string
  test_code?: string | null
  execution_summary?: string | null
  model?: string
  allow_smaller_model?: boolean
}

export interface SocraticLineHintResponse {
  hint: string
  target_concept?: string | null
  line_number: number
  current_line_text: string
  degraded: boolean
  degraded_reason?: string | null
  error?: string | null
}

export interface QueueItem {
  kind: 'card' | 'extract'
  id: string
  deck_or_source_id: string
  front: string | null
  back: string | null
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
  image?: string | null
  back_image?: string | null
  references: CardReference[]
  starter_code?: string | null
  starter_tests?: string | null
  test_cases?: Array<{ input: any; expected: any }>
  time_complexity?: string | null
  space_complexity?: string | null
  edge_cases?: string[]
  title?: string | null
  difficulty?: string | null
  category?: string | null
  active_weaknesses?: string[]
  weakness_history?: Array<Record<string, any>>
  failure_reminder?: string | null
  deck_documentation?: string | null
  deck_thematic_nature?: string | null
  deck_source_documents?: Array<Record<string, any>>
  card_documentation?: string | null
  card_thematic_nature?: string | null
  card_source_documents?: Array<Record<string, any>>
  lexicon_glosses?: LexiconGlossItem[]
  position?: number | null
  stability?: number | null
  retrievability?: number | null
  fsrs_difficulty?: number | null
  last_grade?: string | null
  review_count?: number
  lapses?: number
  is_schema_checkpoint?: boolean
  spatial_x?: number | null
  spatial_y?: number | null
  spatial_locus?: string | null
  mnemonic_vignette?: string | null
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

export interface CitedCard {
  kind: string
  front: string
  back: string
  cloze_text: string | null
  quote: string
  quote_verified: boolean
  locator: string | null
  extract_id: string | null
}

export interface DocumentUpload {
  source_id: string
  title: string
  segment_count: number
  locators: string[]
  node_id: string | null
}

export interface GenerateDeckResponse {
  source_id: string
  title: string
  cards: CitedCard[]
  sections_used: number
  sections_total: number
  next_section: number | null
  degraded: boolean
  reason: string | null
  warnings: string[]
}

export interface AcceptDeckResponse {
  deck_id: string
  deck_created: boolean
  notes_created: number
  cards_created: number
  references_created: number
  warnings: string[]
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
  // 0-100 correctness score — the primary grading feedback. Null in
  // manual/degraded mode, where there is no automated assessment.
  score: number | null
  confidence: number
  matched_points: string[]
  missed_points: string[]
  overlooked_phrases?: string[]
  weaknesses?: string[]
  improvements?: string[]
  persistent_weaknesses?: string[]
  reasoning: string
  degraded_to_manual: boolean
  reference_answer: string
  needs_confirmation: boolean
  heuristic_overlap: number | null
  model_used: string | null
  cached: boolean
  degraded_reason: string | null
  // Informational only — response time never factors into the grade.
  latency_note: string | null
  automaticity_exceeded?: boolean
  automaticity_threshold_ms?: number | null
  automaticity_note?: string | null
  vram_constrained?: boolean
  failed_model?: string | null
  fallback_model?: string | null
  available_fallback_models?: string[]
}

export interface WeaknessHintResponse {
  hint: string
  active_weaknesses: string[]
  has_past_weaknesses: boolean
}

export interface StuckAlert {
  reason: 'accuracy' | 'latency'
  message: string
  suggested_break_minutes: number
}

export interface ConfirmReviewResponse {
  next_due: string
  new_stability: number
  new_difficulty: number
  state: string
  interval_days: number
  lapse_count: number
  leech_flagged: boolean
  stuck_alert: StuckAlert | null
  automaticity_exceeded?: boolean
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
  fsrs_optimized_at: string | null
  grading_bias: number
  automaticity_threshold_ms?: number | null
  target_event_date?: string | null
  target_event_title?: string | null
  peak_retention_target?: number | null
  show_pre_leetcode?: boolean
  show_code_lab?: boolean
  show_thematic_context?: boolean
  tutorial_completed?: boolean
  /** IANA zone for the study-day boundary; null until first set. */
  timezone?: string | null
  enable_schema_checkpoints?: boolean
  enable_prompt_mutation?: boolean
  enable_prediction_mode?: boolean
  can_use_antigravity?: boolean
}

export interface Deck {
  id: string
  name: string
  parent_id: string | null
  desired_retention_override: number | null
  default_priority: number
  position?: number
  card_count: number
  due_count: number
  new_count: number
  total_card_count?: number
  total_due_count?: number
  total_new_count?: number
  target_event_date?: string | null
  target_event_title?: string | null
  documentation?: string | null
  thematic_nature?: string | null
  source_documents?: Array<Record<string, any>>
  stats?: DeckStats | null
}

export interface DeckStats {
  id: string
  name: string
  total_cards: number
  viewed_cards: number
  new_cards: number
  learning_cards: number
  review_cards: number
  due_cards: number
  viewed_ratio: number
  difficulty_counts: Record<string, number>
  difficulty_proportions: Record<string, number>
  rating_counts?: Record<string, number>
  rating_proportions?: Record<string, number>
  total_reviews?: number
}

export interface AtomicityIssue {
  severity: 'info' | 'warning' | 'danger'
  code: string
  message: string
  suggestion: string
}

export interface AtomicityLintResult {
  score: number
  is_atomic: boolean
  word_count_front: number
  word_count_back: number
  word_count_total: number
  issues: AtomicityIssue[]
}

export interface SequentialClozeItem {
  step_index: number
  total_steps: number
  front: string
  back: string
  target_step: string
  context_before: string[]
  context_after: string[]
}

export interface SequentialClozeResponse {
  cards: SequentialClozeItem[]
  notes_created: number
  cards_created: number
}

export interface DecomposedCardItem {
  front: string
  back: string
}

export interface DecomposeCardResponse {
  cards: DecomposedCardItem[]
}

export interface EventReadiness {
  target_event_date: string | null
  target_event_title: string | null
  days_remaining: number | null
  is_active: boolean
  projected_retention: number
  total_cards_count: number
  due_cards_count: number
  unstable_cards_count: number
  estimated_daily_reviews_needed: number
  status_label: string
}

/** A node in the knowledge tree. Counts are rolled up over the whole subtree,
 *  so a collapsed branch still says what is waiting inside it. */
export interface TreeNode {
  id: string
  parent_id: string | null
  kind: 'topic' | 'deck' | 'source' | 'extract'
  title: string
  position: number
  collapsed: boolean
  priority: number
  priority_inherited: boolean
  card_count: number
  due_count: number
  new_count: number
  extract_count: number
  deck_id: string | null
  source_id: string | null
  extract_id: string | null
  // Mastery gating — rolled up over this node's whole subtree, the same way
  // card_count is. Only topic/deck nodes participate meaningfully.
  mastery_pct: number
  locked: boolean
  requires_node_id: string | null
  requires_title: string | null
  mastery_threshold: number
  children: TreeNode[]
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
  image?: string | null
  back_image?: string | null
  occlusion: OcclusionPayload | null
  documentation?: string | null
  thematic_nature?: string | null
  source_documents?: Array<Record<string, any>>
  lexicon_glosses?: LexiconGlossItem[]
  position?: number | null
  is_schema_checkpoint?: boolean
  spatial_x?: number | null
  spatial_y?: number | null
  spatial_locus?: string | null
  mnemonic_vignette?: string | null
}

export interface CardReviewLogItem {
  id: number
  reviewed_at: string
  final_grade: string
  typed_answer?: string | null
  latency_ms?: number | null
  llm_grade?: string | null
  llm_reasoning?: string | null
  llm_confidence?: number | null
  overridden: boolean
  user_confidence?: number | null
  is_blitz: boolean
  weaknesses: string[]
  improvements: string[]
}

export interface CardNextIntervals {
  again: string
  hard: string
  good: string
  easy: string
}

export interface CardAnalytics {
  card: Card
  retrievability?: number | null
  next_intervals?: CardNextIntervals | null
  total_reviews: number
  recall_rate: number
  rating_counts: Record<string, number>
  rating_percentages: Record<string, number>
  avg_latency_ms?: number | null
  fastest_latency_ms?: number | null
  slowest_latency_ms?: number | null
  automaticity_achieved?: boolean | null
  total_overridden: number
  active_weaknesses: string[]
  weakness_history: Array<Record<string, any>>
  review_logs: CardReviewLogItem[]
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
  // False for a document uploaded to generate cards from — it never appears
  // in the Review queue as something to read.
  for_reading: boolean
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
  velocity: Record<string, number>
  leeches: Leech[]
}

export interface JsonImportNote {
  kind?: 'basic' | 'cloze' | 'code'
  card_type?: string
  front?: string
  back?: string
  cloze_text?: string
  image?: string
  back_image?: string
  tags?: string[]
  priority?: number
  quote?: string
  locator?: string
  source_title?: string
  starter_code?: string
  starter_tests?: string
  time_complexity?: string
  space_complexity?: string
}

export interface JsonImportRequest {
  deck: string
  priority?: number
  notes: JsonImportNote[]
}

export interface JsonImportResult {
  deck_id: string
  deck_created: boolean
  notes_created: number
  cards_created: number
  citations_created: number
  warnings: string[]
}

/** One row of GET /api/import/history. */
export interface ImportRecord {
  id: string
  filename: string
  imported_at: string
  notes_mapped: number
  cards_mapped: number
  warnings: string[]
}

/** One timed study block. Finishing its card target early banks the unspent
 *  time as earned free time. */
export interface StudySession {
  id: string
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

export interface Bank {
  today_seconds: number
  week_seconds: number
  total_seconds: number
  sessions_today: number
  goals_met_today: number
  current: StudySession | null
  recent: StudySession[]
}

export interface QueueConfig {
  review_weight: number
  new_weight: number
  ir_weight: number
  seconds_per_review: number
  seconds_per_ir_extract: number
}

export interface FatiguePoint {
  minute_bucket: string
  elapsed_minutes: number
  review_count: number
  accuracy: number
  avg_latency_ms: number
}

export interface SessionFatigue {
  curve: FatiguePoint[]
  optimal_focus_minutes: number
  baseline_accuracy: number
  breakpoint_accuracy: number
  recommendation: string
}

export interface ChronotypeHour {
  hour: number
  review_count: number
  accuracy: number
  avg_latency_ms: number
  avg_stability_gain: number
  efficiency_score: number
}

export interface Chronotype {
  hourly: ChronotypeHour[]
  peak_window_start: number
  peak_window_end: number
  optimal_study_time: string
  summary: string
}

export interface DiscriminatedCard {
  card_id: string
  front: string
  back: string
  deck_name: string | null
  review_count: number
  pass_rate: number
  point_biserial_r: number
  classification: 'high' | 'moderate' | 'ambiguous'
  rationale: string
}

export interface ItemDiscrimination {
  high_discrimination: DiscriminatedCard[]
  ambiguous_cards: DiscriminatedCard[]
  overall_deck_r: number
}

export interface YieldPoint {
  retrievability_bucket: string
  avg_retrievability: number
  review_count: number
  avg_stability_gain: number
  yield_ratio: number
}

export interface DesirableDifficulty {
  curve: YieldPoint[]
  optimal_retention_target: number
  summary: string
}

export interface CalibrationBucket {
  confidence_level: number
  label: string
  predicted_prob: number
  observed_accuracy: number
  review_count: number
}

export interface MetacognitiveStats {
  calibration_curve: CalibrationBucket[]
  brier_score: number
  overconfidence_index: number
  hypercorrection_retention: number
  calibration_verdict: string
}

export interface EWMAScore {
  node_id: string
  title: string
  kind: string
  ewma_pct: number
  sample_size: number
}

export interface SPRTVerdict {
  node_id: string
  title: string
  log_likelihood_ratio: number
  threshold_upper: number
  threshold_lower: number
  verdict: 'mastered' | 'unmastered' | 'testing'
  cards_evaluated: number
}

export interface LearningAnalytics {
  fatigue: SessionFatigue
  chronotype: Chronotype
  item_discrimination: ItemDiscrimination
  desirable_difficulty: DesirableDifficulty
  metacognition: MetacognitiveStats
  ewma_mastery: EWMAScore[]
  sprt_gating: SPRTVerdict[]
}

export interface CodeProblemSummary {
  id: string
  kind: 'fundamental' | 'problem'
  track: string | null
  title: string
  slug: string
  difficulty: 'Easy' | 'Medium' | 'Hard'
  category: string
  tags: string[]
  has_submission: boolean
  last_status: string | null
}

export interface CodeProblemOut {
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
  test_cases: Array<{ input: any; expected: any }>
  hints: string[]
  created_at: string
}

export interface TestCaseResult {
  test_index: number
  passed: boolean
  input: any
  expected: any
  actual: any
  stdout: string
  error: string | null
  runtime_ms: number
}

export interface StudentTestResult {
  test_name: string
  passed: boolean
  error: string | null
  runtime_ms: number
}

export interface RunCodeResponse {
  status: string
  passed_count: number
  total_count: number
  runtime_ms: number
  error: string | null
  results: TestCaseResult[]
  student_tests?: StudentTestResult[]
  student_passed_count?: number
  student_total_count?: number
}

export interface SubmitCodeResponse {
  submission_id: string
  status: string
  passed_count: number
  total_count: number
  runtime_ms: number
  error?: string | null
  results: TestCaseResult[]
  student_tests?: StudentTestResult[]
  student_passed_count?: number
  student_total_count?: number
}

export interface SocraticCodeResponse {
  hint: string
}

export interface CodeSubmissionOut {
  id: string
  problem_id: string
  language: string
  code: string
  status: string
  passed_tests: number
  total_tests: number
  runtime_ms: number | null
  created_at: string
}

export interface CodeLeech {
  problem_id: string
  slug: string
  title: string
  difficulty: string
  category: string
  lapse_count: number
  last_error: string | null
  suggestion_kind: string
  suggestion_rationale: string
}

export interface CategoryProgression {
  category: string
  total: number
  solved: number
  attempted: number
  percentage: number
}

export interface DifficultyTierProgression {
  total: number
  solved: number
  attempted: number
  percentage: number
}

export interface CodeProgressionStats {
  totals: Record<string, number>
  velocity: Record<string, number>
  retention: Record<string, number>
  heatmap: Record<string, number>
  forecast: Record<string, number>
  leeches: CodeLeech[]
  categories: CategoryProgression[]
  difficulty: Record<string, DifficultyTierProgression>
  recent_activity: CodeSubmissionOut[]
}

export interface LexiconLookupRequest {
  term: string
  context?: string | null
  card_id?: string | null
  deck_name?: string | null
  thematic_nature?: string | null
}

export interface LexiconEntry {
  term: string
  definition: string
  context_explanation?: string | null
  example?: string | null
  domain?: string | null
  related_terms: string[]
  cached: boolean
  model_used?: string | null
  created_at?: string | null
}

export interface RecentLexiconItem {
  term: string
  definition: string
  domain?: string | null
  created_at: string
}

export interface VramMetrics {
  capacity_gb: number | null
  capacity_mb: number | null
  available_gb: number | null
  available_mb: number | null
  used_gb: number | null
  used_mb: number | null
  model_vram_gb: number | null
  model_vram_bytes: number | null
  model_approx_gb: number | null
  model_loaded: boolean
  model_name: string | null
  gpu_name: string | null
  is_unified_memory: boolean
}

export interface QwenCoderModelOption {
  id: string
  name: string
  archetype: string
  size: '9B' | '7B' | '4B' | string
  vramApprox: string
  badge: string
  desc: string
}

export const ALLOWED_QWEN_CODER_MODELS: QwenCoderModelOption[] = [
  {
    id: 'qwen3.5:9b',
    name: 'Qwen 3.5 9B',
    archetype: '(The Heavy Generalist)',
    size: '9B',
    vramApprox: '~5.3 GB VRAM',
    badge: 'Heavy Generalist',
    desc: 'Dense hybrid reasoning & multimodal evaluation workhorse',
  },
  {
    id: 'qwen2.5-coder:7b',
    name: 'Qwen2.5-Coder 7B',
    archetype: '(The Technical Specialist)',
    size: '7B',
    vramApprox: '~4.7 GB VRAM',
    badge: 'Technical Specialist',
    desc: 'High-precision code syntax, logic grading & deep technical focus',
  },
  {
    id: 'qwen3.5:4b',
    name: 'Qwen 3.5 4B / Gemma 4 E4B',
    archetype: '(The Speed Demon)',
    size: '4B',
    vramApprox: '~2.5 GB VRAM',
    badge: 'Speed Demon',
    desc: 'Blistering fast token velocity & ultra-low latency inference',
  },
]

export interface AntigravityModelOption {
  id: string
  slug: string
  name: string
  tier: string
  desc: string
}

export const ANTIGRAVITY_MODEL_PREFIX = 'antigravity:'

export const ANTIGRAVITY_MODELS: AntigravityModelOption[] = [
  {
    id: 'antigravity:gemini-3.8-flash-low',
    slug: 'gemini-3.8-flash-low',
    name: 'Gemini 3.8 Flash (Low)',
    tier: 'Fast / Low Quota',
    desc: 'Fastest Antigravity response with low subscription quota cost per grade',
  },
  {
    id: 'antigravity:gemini-3.8-flash-medium',
    slug: 'gemini-3.8-flash-medium',
    name: 'Gemini 3.8 Flash (Medium)',
    tier: 'Balanced Default',
    desc: 'Balanced reasoning speed and grading accuracy via Antigravity CLI',
  },
  {
    id: 'antigravity:gemini-3.8-flash-high',
    slug: 'gemini-3.8-flash-high',
    name: 'Gemini 3.8 Flash (High)',
    tier: 'Deep Reasoning',
    desc: 'High reasoning effort for nuance, math, and technical grading',
  },
  {
    id: 'antigravity:claude-sonnet-4-6',
    slug: 'claude-sonnet-4-6',
    name: 'Claude Sonnet 4.6 (Thinking)',
    tier: 'Coding & Prose',
    desc: 'Strong code review, Socratic tutoring, and prose evaluation',
  },
  {
    id: 'antigravity:claude-opus-4-6-thinking',
    slug: 'claude-opus-4-6-thinking',
    name: 'Claude Opus 4.6 (Thinking)',
    tier: 'Max Reasoning',
    desc: 'Highest-depth reasoning for difficult proofs and complex designs',
  },
  {
    id: 'antigravity:gpt-oss-120b-medium',
    slug: 'gpt-oss-120b-medium',
    name: 'GPT-OSS 120B (Medium)',
    tier: 'Open Weights',
    desc: '120B open-weights model hosted on your Antigravity subscription',
  },
]

export const ALL_GENERATION_MODEL_OPTIONS: Array<{
  id: string
  name: string
  badge: string
  provider: 'ollama' | 'antigravity'
}> = [
  ...ANTIGRAVITY_MODELS.map((m) => ({
    id: m.id,
    name: `${m.name}`,
    badge: `Antigravity · ${m.tier}`,
    provider: 'antigravity' as const,
  })),
  ...ALLOWED_QWEN_CODER_MODELS.map((m) => ({
    id: m.id,
    name: `${m.name} ${m.archetype}`,
    badge: m.badge,
    provider: 'ollama' as const,
  })),
]

export function isAllowedQwenCoderModel(modelName: string): boolean {
  if (!modelName) return false
  const m = modelName.toLowerCase().trim()
  if (m.includes('embed') || m.includes('rerank')) return false
  if (m.includes('qwen3.5') || m.includes('qwen-3.5')) {
    return /(?:^|[:\-_])(9b|4b)(?:[:\-_]|$)/i.test(m)
  }
  if (m.includes('gemma')) {
    return /(?:^|[:\-_])(e4b|4b|2b|gemma4|gemma3|gemma2)(?:[:\-_]|$)/i.test(m)
  }
  if (m.includes('qwen2.5-coder')) {
    return /(?:^|[:\-_])(7b|3b|1\.5b)(?:[:\-_]|$)/i.test(m)
  }
  return false
}

export function isAntigravityModel(modelName?: string | null): boolean {
  if (!modelName) return false
  const m = modelName.toLowerCase().trim()
  if (!m.startsWith(ANTIGRAVITY_MODEL_PREFIX)) return false
  const slug = m.slice(ANTIGRAVITY_MODEL_PREFIX.length)
  return /^(?:gemini|claude|gpt-oss)-[a-z0-9._-]{1,64}$/i.test(slug)
}

export function isAllowedGradingModel(modelName?: string | null): boolean {
  if (!modelName) return false
  return isAllowedQwenCoderModel(modelName) || isAntigravityModel(modelName)
}

export function getModelDisplayInfo(modelName: string): {
  label: string
  short: string
  archetype: string
  badge?: string
  desc?: string
  provider: 'ollama' | 'antigravity'
} {
  if (isAntigravityModel(modelName)) {
    const cleanId = modelName.toLowerCase().trim()
    const match = ANTIGRAVITY_MODELS.find((a) => a.id === cleanId)
    if (match) {
      return {
        label: match.name,
        short: match.name.replace(' (Medium)', ' (Med)').replace(' (Thinking)', ''),
        archetype: `(Antigravity · ${match.tier})`,
        badge: 'Subscription',
        desc: match.desc,
        provider: 'antigravity',
      }
    }
    const slug = cleanId.slice(ANTIGRAVITY_MODEL_PREFIX.length)
    return {
      label: `Antigravity (${slug})`,
      short: slug,
      archetype: '(Antigravity Subscription)',
      badge: 'Subscription',
      desc: 'Runs via local agy CLI on your Antigravity subscription',
      provider: 'antigravity',
    }
  }
  const m = (modelName || '').toLowerCase()
  if (m.includes('9b')) {
    return {
      label: 'Qwen 3.5 9B',
      short: 'Qwen 3.5 9B',
      archetype: '(The Heavy Generalist)',
      badge: 'Heavy Generalist',
      desc: 'Dense hybrid reasoning & multimodal evaluation (~5.3 GB VRAM)',
      provider: 'ollama',
    }
  }
  if (m.includes('7b')) {
    return {
      label: 'Qwen2.5-Coder 7B',
      short: 'Qwen2.5-Coder 7B',
      archetype: '(The Technical Specialist)',
      badge: 'Technical Specialist',
      desc: 'High precision code & logic grader (~4.7 GB VRAM)',
      provider: 'ollama',
    }
  }
  if (m.includes('4b') || m.includes('e4b') || m.includes('gemma') || m.includes('3b') || m.includes('1.5b')) {
    return {
      label: 'Qwen 3.5 4B / Gemma 4 E4B',
      short: 'Qwen 3.5 4B / Gemma',
      archetype: '(The Speed Demon)',
      badge: 'Speed Demon',
      desc: 'Ultra lightweight & instant response (~2.5 GB VRAM)',
      provider: 'ollama',
    }
  }
  const clean = (modelName || '').replace(/:latest$/, '')
  return {
    label: clean,
    short: clean.split(':')[0] || clean,
    archetype: '',
    desc: 'Local Ollama quantized model',
    provider: 'ollama',
  }
}

export interface LlmProvidersBreakdown {
  ollama?: {
    connected: boolean
    base_url: string
    models: string[]
    error?: string | null
  }
  antigravity?: {
    connected: boolean
    installed: boolean
    cli_path?: string | null
    models: string[]
    catalog?: Array<{ id: string; slug: string; name: string; tier: string }>
    error?: string | null
  }
}

export interface LlmEngineStatusResponse {
  connected: boolean
  provider: string
  base_url: string
  model: string
  models_installed: string[]
  model_ready: boolean
  error?: string | null
  vram?: VramMetrics | null
  providers?: LlmProvidersBreakdown
}

export interface HardwareModelOption {
  id: string
  name: string
  size: string
  vram_approx: string
  status: 'recommended' | 'supported' | 'heavy' | 'too_large'
  suitability: string
}

export interface HardwareProfile {
  os_name: string
  os_release: string
  architecture: string
  cpu_name: string
  cpu_cores: number
  ram_gb: number
  gpu_name: string | null
  vram_gb: number | null
  is_apple_silicon: boolean
  has_cuda: boolean
  hardware_tier: 'budget' | 'mid-range' | 'high-end'
  recommended_model: string
  recommended_size: string
  headline: string
  rationale: string
  models: HardwareModelOption[]
}

export interface SyncStatus {
  lan_ip: string
  port: number
  pairing_url: string
  active_connections: number
  user_connections: number
  server_time: string
}

export interface SyncEvent<T = any> {
  type: 'CONNECTED' | 'PONG' | 'CARD_REVIEWED' | 'QUEUE_INVALIDATED' | 'DECK_MUTATED' | 'SESSION_TICK'
  data: T
}

export interface ExplainCodeSelectionRequest {
  selected_code: string
  full_code?: string | null
  language?: string
  context?: string | null
  mode?: 'occams_razor' | 'socratic' | 'both' | 'docs'
  model?: string | null
  deck_id?: string | null
  card_id?: string | null
  doc_id?: string | null
  user_code?: string | null
  user_test_code?: string | null
  execution_summary?: string | null
  revealed?: boolean
}

export interface ExplainCodeSelectionResponse {
  explanation: string
  occams_razor?: string | null
  socratic_insight?: string | null
  doc_citation?: string | null
  verbatim_passage?: string | null
  doc_matches?: Array<{
    extract_id: string
    source_id: string
    source_title: string
    locator: string
    content: string
    score: number
  }>
  model_used: string
  available_models: string[]
}

export interface DeckDocumentOut {
  id: string
  source_id: string
  filename: string
  title: string
  segment_count: number
  locators: string[]
  uploaded_at?: string | null
}

export interface DeckDocumentsListResponse {
  deck_id: string
  documents: DeckDocumentOut[]
}

export interface QueryDeckDocsRequest {
  query: string
  full_code?: string | null
  language?: string
  doc_id?: string | null
  model?: string | null
}

export interface QueryDeckDocsResponse {
  found_info: string
  doc_citation?: string | null
  verbatim_passage?: string | null
  explanation?: string | null
  key_takeaway?: string | null
  citations: Array<{
    extract_id: string
    source_id: string
    source_title: string
    locator: string
    content: string
    score: number
  }>
  model_used: string
  available_models: string[]
}

export interface DeckDocMessage {
  role: 'user' | 'assistant'
  content: string
  citation?: string | null
  extracted_terms?: string[]
}

export interface AskDeckQuestionRequest {
  question: string
  selected_code?: string | null
  full_code?: string | null
  language?: string
  context?: string | null
  deck_id?: string | null
  card_id?: string | null
  doc_id?: string | null
  user_code?: string | null
  user_test_code?: string | null
  execution_summary?: string | null
  revealed?: boolean
  model?: string | null
  history?: DeckDocMessage[]
}

export interface AskDeckQuestionResponse {
  answer: string
  doc_citation?: string | null
  citations?: Array<{
    extract_id: string
    source_id: string
    source_title: string
    locator: string
    content: string
    score: number
  }>
  model_used: string
  available_models?: string[]
  extracted_glosses?: LexiconGlossItem[]
  updated_card_glosses?: LexiconGlossItem[] | null
}


// ── Neuroscience Enhancements (§Neuroscience) ─────────────────────────────────

export interface ConceptEdge {
  id: string
  source_card_id: string
  target_card_id: string
  relationship_type: string
  weight: number
  created_at: string
}

export interface GraphNode {
  id: string
  card_id: string
  title: string
  deck_id: string
  deck_name: string
  state: string
  is_schema_checkpoint: boolean
  spatial_x: number | null
  spatial_y: number | null
  spatial_locus: string | null
  activation: number
}

export interface GraphEdge {
  id: string
  source: string
  target: string
  relationship_type: string
  weight: number
}

export interface ConceptGraph {
  nodes: GraphNode[]
  edges: GraphEdge[]
  total_nodes: number
  total_edges: number
}

export interface SpreadingActivationNode {
  card_id: string
  title: string
  deck_name: string
  activation: number
  path_depth: number
  relationship_to_source?: string | null
}

export interface SpreadingActivationResponse {
  source_card_id: string
  source_title: string
  activated_nodes: SpreadingActivationNode[]
}

export interface MutatePromptResponse {
  card_id: string
  original_front: string
  mutated_prompt: string
  mutation_type: string
  model_used: string | null
}

export interface GenerateMnemonicResponse {
  card_id: string
  mnemonic_vignette: string
  model_used: string | null
}

export interface PretestPredictionResponse {
  card_id: string
  prediction: string
  reference_answer: string
  confidence: number
  is_accurate: boolean
  feedback: string
  high_confidence_error: boolean
}

export interface ContrastDrillResponse {
  pair_id: string
  concept_a_title: string
  concept_b_title: string
  front_a: string
  back_a: string
  front_b: string
  back_b: string
  discriminative_challenge: string
  key_distinction: string
  divergent_conditions: Array<{ condition: string; choice_a: string; choice_b: string }>
}

export interface CardNeuroPropsUpdate {
  is_schema_checkpoint?: boolean | null
  spatial_x?: number | null
  spatial_y?: number | null
  spatial_locus?: string | null
  mnemonic_vignette?: string | null
}



