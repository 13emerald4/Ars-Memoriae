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
  deck_documentation?: string | null
  deck_thematic_nature?: string | null
  deck_source_documents?: Array<Record<string, any>>
  card_documentation?: string | null
  card_thematic_nature?: string | null
  card_source_documents?: Array<Record<string, any>>
  lexicon_glosses?: LexiconGlossItem[]
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
  occlusion: OcclusionPayload | null
  documentation?: string | null
  thematic_nature?: string | null
  source_documents?: Array<Record<string, any>>
  lexicon_glosses?: LexiconGlossItem[]
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
  kind?: 'basic' | 'cloze'
  front?: string
  back?: string
  cloze_text?: string
  tags?: string[]
  priority?: number
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

export interface QwenCoderModelOption {
  id: string
  name: string
  size: '7B' | '3B' | '1.5B'
  vramApprox: string
  badge: string
  desc: string
}

export const ALLOWED_QWEN_CODER_MODELS: QwenCoderModelOption[] = [
  {
    id: 'qwen2.5-coder:7b',
    name: 'Qwen 2.5 Coder 7B',
    size: '7B',
    vramApprox: '~4.7 GB',
    badge: 'Recommended',
    desc: 'High precision code & logic grader',
  },
  {
    id: 'qwen2.5-coder:3b',
    name: 'Qwen 2.5 Coder 3B',
    size: '3B',
    vramApprox: '~1.9 GB',
    badge: 'Balanced',
    desc: 'Balanced reasoning for moderate VRAM',
  },
  {
    id: 'qwen2.5-coder:1.5b',
    name: 'Qwen 2.5 Coder 1.5B',
    size: '1.5B',
    vramApprox: '~986 MB',
    badge: 'Fast / Low VRAM',
    desc: 'Ultra lightweight & instant response',
  },
]

export function isAllowedQwenCoderModel(modelName: string): boolean {
  if (!modelName) return false
  const m = modelName.toLowerCase().trim()
  if (!m.includes('qwen2.5-coder')) return false
  if (m.includes('embed') || m.includes('rerank')) return false
  return /(?:^|[:\-_])(7b|3b|1\.5b)(?:[:\-_]|$)/i.test(m)
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

