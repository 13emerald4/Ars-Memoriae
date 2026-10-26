export type Grade = 'again' | 'hard' | 'good' | 'easy'

export interface Card {
  id: string
  note_id: string
  deck_id: string
  deck_name?: string
  template_slot: string
  state: 'new' | 'learning' | 'review' | 'relearning'
  due: string | null
  stability: number | null
  difficulty: number | null
  priority: number
  lapse_count: number
  front: string
  back: string
  documentation?: string | null
  thematic_nature?: string | null
}

export interface Extract {
  id: string
  source_id: string
  title: string
  content: string
  position: number
  locator?: string | null
  priority?: number | null
}

export interface QueueItem {
  kind: 'card' | 'extract'
  card?: Card
  extract?: Extract
  stream?: string
  priority?: number
  counts?: {
    due_cards: number
    new_cards: number
    ir_extracts: number
    total_remaining: number
  }
}

export interface SubmitAnswerResponse {
  suggested_grade: Grade
  confidence: number
  reasoning: string
  reference_answer: string
  needs_confirmation: boolean
  heuristic_overlap: number
  latency_note?: string | null
  model_used?: string | null
}

export interface ConfirmReviewResponse {
  next_due: string
  new_stability: number
  new_difficulty: number
  state: string
  interval_days: number
  lapse_count: number
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

export interface OfflineReviewItem {
  card_id: string
  final_grade: Grade
  typed_answer?: string
  latency_ms?: number
  confidence?: number
  reviewed_at: string
}

export interface PairingConfig {
  server_url: string
  token: string
  email?: string
}
