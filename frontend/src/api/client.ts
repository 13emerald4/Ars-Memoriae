import type {
  AcceptDeckResponse,
  AtomicityLintResult,
  Bank,
  Card,
  CardAnalytics,
  CitedCard,
  CodeProblemOut,
  CodeProblemSummary,
  CodeProgressionStats,
  CodeSubmissionOut,
  ConfirmReviewResponse,
  Deck,
  DeckDocumentOut,
  AskDeckQuestionRequest,
  AskDeckQuestionResponse,
  DeckDocumentsListResponse,
  DeckStats,
  DecomposeCardResponse,
  DocumentUpload,
  EventReadiness,
  ExplainCodeSelectionRequest,
  ExplainCodeSelectionResponse,
  Extract,
  GenerateCardsResponse,
  GenerateDeckResponse,
  Grade,
  HardwareProfile,
  ImportRecord,
  JsonImportNote,
  JsonImportRequest,
  JsonImportResult,
  LearningAnalytics,
  Lesson,
  LexiconEntry,
  LexiconGlossItem,
  LlmEngineStatusResponse,
  LlmProvidersBreakdown,
  NoteType,
  QueueConfig,
  QueueItem,
  QueryDeckDocsRequest,
  QueryDeckDocsResponse,
  RecentLexiconItem,
  RunCodeResponse,
  SequentialClozeResponse,
  SessionSummary,
  SisterPair,
  SocraticCodeResponse,
  SocraticLineHintRequest,
  SocraticLineHintResponse,
  SocraticResponse,
  SocraticTurn,
  Source,
  Stats,
  StudySession,
  SubmitAnswerResponse,
  SubmitCodeResponse,
  SuggestedCard,
  SyncEvent,
  SyncStatus,
  TreeNode,
  User,
  VramMetrics,
  WeaknessHintResponse,
  CardNeuroPropsUpdate,
  ConceptEdge,
  ConceptGraph,
  ContrastDrillResponse,
  GenerateMnemonicResponse,
  MutatePromptResponse,
  PretestPredictionResponse,
  SpreadingActivationResponse,
} from './types'
import { storage } from '../utils/storage'

// Where the API lives. Empty means "this origin": in production FastAPI serves
// the built app itself, and in development Vite proxies /api and /media to it.
// Only set VITE_API_BASE_URL to reach a backend on a different origin.
const BASE = import.meta.env.PROD ? '' : (import.meta.env.VITE_API_BASE_URL ?? '')
export const API_BASE = BASE
const TOKEN_KEY = 'memorization.token'

/** Turns a server path such as `/media/<user>/<file>.png` into something an
 *  <img> can load. Absolute URLs pass through untouched. Every place that
 *  renders uploaded media must go through this: a hard-coded host only works
 *  on the machine the server runs on. */
export function mediaUrl(path: string): string {
  return path.startsWith('/') ? `${BASE}${path}` : path
}

/** Fired when the server rejects the stored token. AuthProvider listens and
 *  drops back to the sign-in screen; without it the shell stayed up with every
 *  request failing until a manual reload. */
export const UNAUTHORIZED_EVENT = 'ars:unauthorized'

export const token = {
  get: () => storage.get(TOKEN_KEY),
  set: (t: string) => storage.set(TOKEN_KEY, t),
  clear: () => storage.remove(TOKEN_KEY),
}

export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message)
  }
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers)
  const t = token.get()
  if (t) headers.set('Authorization', `Bearer ${t}`)
  if (init.body && !(init.body instanceof FormData)) {
    headers.set('Content-Type', 'application/json')
  }

  const resp = await fetch(`${BASE}${path}`, { ...init, headers })

  // A 401 on a request that carried a token means the session is over. A 401
  // without one is just a failed sign-in, and should say what the server said.
  if (resp.status === 401 && t) {
    token.clear()
    window.dispatchEvent(new Event(UNAUTHORIZED_EVENT))
    throw new ApiError(401, 'Session expired. Please sign in again.')
  }
  if (resp.status === 204) return null as T
  if (!resp.ok) {
    let detail = `${resp.status} ${resp.statusText}`
    try {
      const body = await resp.json()
      if (typeof body.detail === 'string') detail = body.detail
      else if (Array.isArray(body.detail)) {
        detail = body.detail
          .map((d: { msg?: string }) => d.msg ?? '')
          .filter(Boolean)
          .join('; ')
      }
    } catch {
      /* keep the status line */
    }
    throw new ApiError(resp.status, detail)
  }
  const text = await resp.text()
  return (text ? JSON.parse(text) : null) as T
}

const post = <T,>(path: string, body?: unknown, init: RequestInit = {}) =>
  request<T>(path, { method: 'POST', body: body === undefined ? undefined : JSON.stringify(body), ...init })
const patch = <T,>(path: string, body: unknown) =>
  request<T>(path, { method: 'PATCH', body: JSON.stringify(body) })

export const api = {
  // ── auth ────────────────────────────────────────────────────────────────
  register: (email: string, password: string) =>
    post<{ access_token: string }>('/api/auth/register', { email, password }),
  login: (email: string, password: string) =>
    post<{ access_token: string }>('/api/auth/login', { email, password }),
  registrationStatus: () => request<{ open: boolean }>('/api/auth/registration-status'),
  changePassword: (current_password: string, new_password: string) =>
    post<{ access_token: string }>('/api/auth/change-password', { current_password, new_password }),
  // Revokes every token for the account and returns a fresh one for this tab.
  logoutEverywhere: () => post<{ access_token: string }>('/api/auth/logout-all'),
  // A review-only token for the mobile app's pairing QR (never this tab's own).
  pairingToken: () =>
    post<{ access_token: string; scope: string; expires_in: number }>('/api/auth/pairing-token'),
  me: () => request<User>('/api/me'),
  updateMe: (body: Partial<User>) => patch<User>('/api/me', body),

  // ── AI grading engines (Antigravity CLI & local Ollama) ───────────────────
  models: () =>
    request<{
      models: string[]
      active?: string
      provider?: string
      providers?: LlmProvidersBreakdown
      error?: string | null
    }>('/api/models'),
  llmStatus: () => request<LlmEngineStatusResponse>('/api/llm/status'),
  vramStatus: (model?: string) =>
    request<VramMetrics>(`/api/llm/vram${model ? `?model=${encodeURIComponent(model)}` : ''}`),
  hardwareSpecs: () => request<HardwareProfile>('/api/llm/hardware'),

  // ── queue (§9) ──────────────────────────────────────────────────────────
  // `branch` scopes the session to one knowledge-tree subtree;
  // `deck` scopes the session to a deck and all its subdecks recursively.
  nextItem: (branch?: string | null, deck?: string | null) => {
    const params = new URLSearchParams()
    if (branch) params.set('branch', branch)
    if (deck) params.set('deck', deck)
    const qs = params.toString() ? `?${params.toString()}` : ''
    return request<QueueItem | null>(`/api/queue/next${qs}`)
  },
  session: (branch?: string | null, deck?: string | null) => {
    const params = new URLSearchParams()
    if (branch) params.set('branch', branch)
    if (deck) params.set('deck', deck)
    const qs = params.toString() ? `?${params.toString()}` : ''
    return request<SessionSummary>(`/api/queue/session${qs}`)
  },
  queueConfig: () => request<QueueConfig>('/api/queue-config'),
  updateQueueConfig: (body: Partial<QueueConfig>) => patch<QueueConfig>('/api/queue-config', body),

  // ── study sessions & the Time Bank ──────────────────────────────────────
  startSession: (body: {
    planned_minutes: number
    goal_cards?: number
    focus_goal?: string | null
  }) => post<StudySession>('/api/sessions/start', body),
  finishSession: (id: string, remaining_seconds: number) =>
    post<StudySession>(`/api/sessions/${id}/finish`, { remaining_seconds }),
  reflectOnSession: (id: string, distraction: string, next_time_plan: string) =>
    post<StudySession>(`/api/sessions/${id}/reflect`, {
      distraction: distraction.trim() || undefined,
      next_time_plan: next_time_plan.trim() || undefined,
    }),
  bank: () => request<Bank>('/api/sessions/bank'),

  // ── review (§7.1) ───────────────────────────────────────────────────────
  // Learn & Practice — fetched on demand, since the mode is opt-in and each
  // lesson may cost a generation.
  lesson: (cardId: string) => request<Lesson>(`/api/review/${cardId}/lesson`),
  // Socratic AI Guide — one diagnostic question at a time, never the answer.
  // Stateless: the full turn history goes up with every message.
  guide: (
    cardId: string,
    history: SocraticTurn[],
    message: string,
    options?: {
      model?: string
      allow_smaller_model?: boolean
      user_code?: string | null
      test_code?: string | null
      execution_summary?: string | null
    },
  ) =>
    post<SocraticResponse>(`/api/review/${cardId}/guide`, {
      history,
      message,
      model: options?.model,
      allow_smaller_model: options?.allow_smaller_model ?? true,
      user_code: options?.user_code,
      test_code: options?.test_code,
      execution_summary: options?.execution_summary,
    }),
  weaknessHint: (cardId: string) =>
    post<WeaknessHintResponse>(`/api/review/${cardId}/weakness-hint`, {}),
  socraticLineHint: (cardId: string, body: SocraticLineHintRequest) =>
    post<SocraticLineHintResponse>(`/api/review/${cardId}/line-hint`, body),
  submitAnswer: (
    cardId: string,
    typed_answer: string,
    latency_ms: number,
    test_code?: string,
    options?: { model?: string; allow_smaller_model?: boolean; language?: string; signal?: AbortSignal },
  ) =>
    post<SubmitAnswerResponse>(
      `/api/review/${cardId}/answer`,
      {
        typed_answer,
        latency_ms,
        test_code,
        language: options?.language,
        model: options?.model,
        allow_smaller_model: options?.allow_smaller_model,
      },
      options?.signal ? { signal: options.signal } : {},
    ),
  runReviewCode: (
    cardId: string,
    body: { code: string; test_code?: string; custom_test_cases?: any[]; language?: string },
  ) =>
    post<RunCodeResponse>(`/api/review/${cardId}/run-code`, body),
  confirmReview: (
    cardId: string,
    final_grade: Grade,
    overridden: boolean,
    typed_answer?: string,
    latency_ms?: number,
    confidence?: number,
    is_blitz?: boolean,
    // One id per attempt at a card. Resending the same attempt (double click,
    // retry after a lost reply) is answered from the first, not recorded again.
    client_review_id?: string,
  ) =>
    post<ConfirmReviewResponse>(`/api/review/${cardId}/confirm`, {
      final_grade,
      overridden,
      typed_answer,
      latency_ms,
      confidence,
      is_blitz: Boolean(is_blitz),
      client_review_id,
    }),

  // ── decks / notes / cards ───────────────────────────────────────────────
  decks: () => request<Deck[]>('/api/decks'),
  deckStats: (id: string) => request<DeckStats>(`/api/decks/${id}/stats`),
  deckPersistItems: (deckId: string, unseenOnly?: boolean) =>
    request<QueueItem[]>(`/api/decks/${deckId}/persist-items${unseenOnly ? '?unseen_only=true' : ''}`),
  deckAllCardsRunItems: (deckId: string) => request<QueueItem[]>(`/api/decks/${deckId}/all-cards-run-items`),
  createDeck: (body: {
    name: string
    default_priority?: number
    parent_id?: string | null
    position?: number
    documentation?: string | null
    thematic_nature?: string | null
    source_documents?: Array<Record<string, any>>
  }) => post<Deck>('/api/decks', body),
  updateDeck: (id: string, body: Record<string, unknown>) => patch<Deck>(`/api/decks/${id}`, body),
  reorderDecks: (items: { id: string; parent_id?: string | null; position: number }[]) =>
    post<Deck[]>('/api/decks/reorder', { items }),
  deleteDeck: (id: string, cascade: boolean = true) =>
    request<void>(`/api/decks/${id}${cascade ? '?cascade=true' : ''}`, { method: 'DELETE' }),
  deleteAllDecks: () => request<void>('/api/decks', { method: 'DELETE' }),
  noteTypes: () => request<NoteType[]>('/api/note-types'),
  createNoteType: (body: {
    name: string
    template_kind: string
    fields?: Record<string, unknown>
    grading_profile?: string
  }) => post<NoteType>('/api/note-types', body),
  createNote: (body: {
    deck_id: string
    note_type_id?: string
    template_kind?: string
    field_values: Record<string, unknown>
    tags?: string[]
    priority?: number | null
    documentation?: string | null
    thematic_nature?: string | null
    source_documents?: Array<Record<string, any>>
  }) => post<{ id: string; cards: Card[] }>('/api/notes', body),
  deleteNote: (id: string) => request<void>(`/api/notes/${id}`, { method: 'DELETE' }),
  cards: (params: Record<string, string | number | boolean> = {}) => {
    const qs = new URLSearchParams(
      Object.entries(params).map(([k, v]) => [k, String(v)]),
    ).toString()
    return request<Card[]>(`/api/cards${qs ? `?${qs}` : ''}`)
  },
  suspendCard: (id: string, suspended: boolean) =>
    post<Card>(`/api/cards/${id}/suspend?suspended=${suspended}`),
  postponeCard: (id: string, hours: number = 4) =>
    post<{ card_id: string; due: string; postponed_hours: number }>(`/api/cards/${id}/postpone?hours=${hours}`),
  reorderCards: (items: { id: string; position: number; deck_id?: string | null }[]) =>
    post<Card[]>('/api/cards/reorder', { items }),
  cardAnalytics: (cardId: string) => request<CardAnalytics>(`/api/cards/${cardId}/analytics`),
  updateCardMemoryNote: (cardId: string, memory_note: string) =>
    patch<Card>(`/api/cards/${cardId}/memory-note`, { memory_note }),
  updateCardLexiconGlosses: (cardId: string, glosses: LexiconGlossItem[]) =>
    patch<Card>(`/api/cards/${cardId}/lexicon-glosses`, { glosses }),
  addCardLexiconGloss: (cardId: string, gloss: LexiconGlossItem) =>
    post<Card>(`/api/cards/${cardId}/lexicon-glosses`, { gloss }),
  setPriority: (target: 'deck' | 'card' | 'source' | 'extract', id: string, priority: number) =>
    patch<{ priority: number }>('/api/priority', { target, id, priority }),

  // ── documents -> cited decks ────────────────────────────────────────────
  uploadDocument: (file: File, opts: { title?: string; parent_node_id?: string } = {}) => {
    const form = new FormData()
    form.append('file', file)
    if (opts.title) form.append('title', opts.title)
    if (opts.parent_node_id) form.append('parent_node_id', opts.parent_node_id)
    return request<DocumentUpload>('/api/documents', { method: 'POST', body: form })
  },
  generateDeck: (
    sourceId: string,
    body: {
      max_cards_per_section?: number
      max_sections?: number
      start_section?: number
      model?: string
      thinking_budget?: number
    } = {},
  ) => post<GenerateDeckResponse>(`/api/documents/${sourceId}/generate-deck`, body),
  acceptDeck: (
    sourceId: string,
    deck: string,
    cards: CitedCard[],
    options?: {
      thematic_nature?: string | null
      documentation?: string | null
      source_documents?: Array<Record<string, any>>
    },
  ) =>
    post<AcceptDeckResponse>(`/api/documents/${sourceId}/accept-deck`, {
      deck,
      cards,
      ...options,
    }),

  // ── knowledge tree ──────────────────────────────────────────────────────
  tree: () => request<{ nodes: TreeNode[] }>('/api/tree'),
  deleteAllTree: () =>
    request<{ deleted: boolean; summary: Record<string, number> }>('/api/tree', {
      method: 'DELETE',
    }),
  createTopic: (body: { title: string; parent_id?: string | null; priority?: number }) =>
    post<TreeNode>('/api/tree/nodes', body),
  updateNode: (
    id: string,
    body: {
      title?: string
      priority?: number
      collapsed?: boolean
      cascade?: boolean
      // Present-but-null clears the prerequisite; absent leaves it alone.
      requires_node_id?: string | null
      mastery_threshold?: number
    },
  ) => patch<{ entities_updated: number }>(`/api/tree/nodes/${id}`, body),
  moveNode: (id: string, parent_id: string | null, position?: number) =>
    post<{ id: string; parent_id: string | null }>(`/api/tree/nodes/${id}/move`, { parent_id, position }),
  deleteNode: (id: string) =>
    request<{ children_promoted: number }>(`/api/tree/nodes/${id}`, { method: 'DELETE' }),
  branchCards: (id: string) => request<Card[]>(`/api/tree/nodes/${id}/cards`),

  // ── incremental reading (§8) ────────────────────────────────────────────
  sources: () => request<Source[]>('/api/sources'),
  createSource: (body: {
    title?: string
    raw_text?: string
    url?: string
    priority?: number
    parent_node_id?: string | null
  }) => post<Source>('/api/sources', body),
  deleteSource: (id: string) => request<void>(`/api/sources/${id}`, { method: 'DELETE' }),
  deleteExtract: (id: string) => request<void>(`/api/extracts/${id}`, { method: 'DELETE' }),
  extractsOf: (sourceId: string) => request<Extract[]>(`/api/sources/${sourceId}/extracts`),
  extract: (id: string) => request<Extract>(`/api/extracts/${id}`),
  splitExtract: (id: string, body: { text?: string; start?: number; end?: number; priority?: number }) =>
    post<Extract>(`/api/extracts/${id}/split`, body),
  scheduleExtract: (id: string, body: { days?: number; status?: string; priority?: number }) =>
    post<Extract>(`/api/extracts/${id}/schedule`, body),
  generateCards: (
    id: string,
    body: { text?: string; max_cards?: number; model?: string; thinking_budget?: number },
  ) => post<GenerateCardsResponse>(`/api/extracts/${id}/generate-cards`, body),
  acceptCards: (id: string, deck_id: string, cards: SuggestedCard[]) =>
    post<{ cards_created: number }>(`/api/extracts/${id}/accept-cards`, { deck_id, cards }),

  // ── media + interference (Phase 4) ──────────────────────────────────────
  uploadMedia: (file: File) => {
    const form = new FormData()
    form.append('file', file)
    return request<{ url: string; kind: string; bytes: number }>('/api/media', {
      method: 'POST',
      body: form,
    })
  },
  scanInterference: () =>
    post<{ notes_scanned: number; pairs_found: number; by_kind: Record<string, number> }>(
      '/api/interference/scan',
    ),
  sisterPairs: () => request<SisterPair[]>('/api/interference'),
  dismissPair: (id: string) => post<SisterPair>(`/api/interference/${id}/dismiss`),

  // ── import / export / stats (§7, §10, §11) ──────────────────────────────
  importHistory: () => request<ImportRecord[]>('/api/import/history'),
  // A bare array of notes is accepted too — the deck name then travels as a
  // query param instead of living inside the body.
  importJson: (body: JsonImportRequest | JsonImportNote[], deckForArray?: string) =>
    post<JsonImportResult>(
      `/api/import/json${Array.isArray(body) && deckForArray ? `?deck=${encodeURIComponent(deckForArray)}` : ''}`,
      body,
    ),
  stats: () => request<Stats>('/api/stats'),
  learningAnalytics: (days: number = 365) =>
    request<LearningAnalytics>(`/api/stats/learning-analytics?days=${days}`),
  dismissLeech: (cardId: string) => post<unknown>(`/api/leeches/${cardId}/dismiss`),
  suspendLeech: (cardId: string) => post<unknown>(`/api/leeches/${cardId}/suspend`),
  acceptLeech: (cardId: string) => post<{ applied: string; cards_created: number }>(
    `/api/leeches/${cardId}/accept`,
  ),
  optimize: () =>
    post<{
      optimized: boolean
      review_count: number
      min_reviews: number
      optimizer_installed: boolean
      reason: string | null
    }>('/api/optimize'),
  exportUrl: () => `${BASE}/api/export`,
  csvUrl: () => `${BASE}/api/export/review-logs.csv`,
  downloadExport: async (path: string, filename: string) => {
    const resp = await fetch(`${BASE}${path}`, {
      headers: { Authorization: `Bearer ${token.get() ?? ''}` },
    })
    if (!resp.ok) throw new ApiError(resp.status, 'Export failed')
    const blob = await resp.blob()
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = filename
    a.click()
    URL.revokeObjectURL(url)
  },

  // ── memory athlete / champion methods (§Features 4, 5, & 6) ─────────────
  lintAtomicity: (front: string, back: string, templateKind?: string) =>
    post<AtomicityLintResult>('/api/memory/lint-atomicity', {
      front,
      back,
      template_kind: templateKind || 'basic',
    }),
  createSequentialCloze: (body: {
    title: string
    steps: string[]
    window_size?: number
    deck_id?: string
  }) => post<SequentialClozeResponse>('/api/memory/sequential-cloze', body),
  decomposeCard: (front: string, back: string) =>
    post<DecomposeCardResponse>('/api/memory/decompose', { front, back }),
  eventReadiness: (deckId?: string) =>
    request<EventReadiness>(`/api/memory/event-readiness${deckId ? `?deck_id=${deckId}` : ''}`),

  // ── code practice & pre-leetcode fundamentals ───────────────────────────
  listCodeProblems: (params?: {
    kind?: string
    track?: string
    category?: string
    difficulty?: string
    search?: string
  }) => {
    const qs = new URLSearchParams()
    if (params?.kind) qs.set('kind', params.kind)
    if (params?.track) qs.set('track', params.track)
    if (params?.category) qs.set('category', params.category)
    if (params?.difficulty) qs.set('difficulty', params.difficulty)
    if (params?.search) qs.set('search', params.search)
    const qStr = qs.toString()
    return request<CodeProblemSummary[]>(`/api/code/problems${qStr ? `?${qStr}` : ''}`)
  },
  getCodeProblem: (idOrSlug: string) => request<CodeProblemOut>(`/api/code/problems/${idOrSlug}`),
  runCode: (
    idOrSlug: string,
    body: { code: string; language?: string; custom_test_cases?: any[] },
  ) => post<RunCodeResponse>(`/api/code/problems/${idOrSlug}/run`, body),
  submitCode: (
    idOrSlug: string,
    body: { code: string; language?: string },
  ) => post<SubmitCodeResponse>(`/api/code/problems/${idOrSlug}/submit`, body),
  socraticCodeHint: (
    idOrSlug: string,
    body: { code: string; language?: string; hint_type?: string; model?: string },
  ) => post<SocraticCodeResponse>(`/api/code/problems/${idOrSlug}/socratic`, body),
  explainCodeSelection: (body: ExplainCodeSelectionRequest) =>
    post<ExplainCodeSelectionResponse>('/api/code/explain-selection', body),
  askDeckQuestion: (body: AskDeckQuestionRequest) =>
    post<AskDeckQuestionResponse>('/api/code/ask-docs', body),
  uploadDeckDocument: (deckId: string, file: File, title?: string) => {
    const form = new FormData()
    form.append('file', file)
    if (title) form.append('title', title)
    return request<DeckDocumentOut>(`/api/decks/${deckId}/documents`, {
      method: 'POST',
      body: form,
    })
  },
  getDeckDocuments: (deckId: string) =>
    request<DeckDocumentsListResponse>(`/api/decks/${deckId}/documents`),
  deleteDeckDocument: (deckId: string, docId: string) =>
    request<{ status: string; doc_id: string; source_id?: string | null }>(
      `/api/decks/${deckId}/documents/${docId}`,
      { method: 'DELETE' },
    ),
  queryDeckDocs: (deckId: string, body: QueryDeckDocsRequest) =>
    post<QueryDeckDocsResponse>(`/api/decks/${deckId}/query-docs`, body),
  forgeProblem: (body: { topic: string; difficulty?: string; target_language?: string }) =>
    post<CodeProblemOut>('/api/code/problems/forge', body),
  exportProblemToCard: (idOrSlug: string, deckId: string) =>
    post<{ note_id: string; card_id?: string; message: string }>(
      `/api/code/problems/${idOrSlug}/export-card`,
      { deck_id: deckId },
    ),
  listCodeSubmissions: (problemId?: string, limit = 20) =>
    request<CodeSubmissionOut[]>(
      `/api/code/submissions?limit=${limit}${problemId ? `&problem_id=${problemId}` : ''}`,
    ),
  getCodeStats: () => request<CodeProgressionStats>('/api/code/stats'),
  lookupLexicon: (
    term: string,
    context?: string | null,
    cardId?: string | null,
    options?: { deckName?: string | null; thematicNature?: string | null },
  ) =>
    post<LexiconEntry>('/api/lexicon/lookup', {
      term,
      context,
      card_id: cardId,
      deck_name: options?.deckName,
      thematic_nature: options?.thematicNature,
    }),
  getRecentLexicon: () => request<RecentLexiconItem[]>('/api/lexicon/recent'),
  syncStatus: () => request<SyncStatus>('/api/sync/status'),
  // ── Neuroscience Enhancements ──────────────────────────────────────────────
  getConceptGraph: (deckId?: string) =>
    request<ConceptGraph>(`/api/graph${deckId ? `?deck_id=${deckId}` : ''}`),
  createConceptEdge: (body: {
    source_card_id: string
    target_card_id: string
    relationship_type?: string
    weight?: number
  }) => post<ConceptEdge>('/api/graph/edges', body),
  deleteConceptEdge: (edgeId: string) =>
    request<void>(`/api/graph/edges/${edgeId}`, { method: 'DELETE' }),
  getRelatedCards: (cardId: string, decay = 0.6, depth = 2) =>
    request<SpreadingActivationResponse>(
      `/api/graph/related/${cardId}?decay=${decay}&depth=${depth}`,
    ),
  autoLinkConceptGraph: () =>
    post<{ created_count: number; edges: ConceptEdge[] }>('/api/graph/auto-link', {}),
  updateCardNeuroProps: (cardId: string, props: CardNeuroPropsUpdate) =>
    patch<Card>(`/api/decks/cards/${cardId}/neuro-props`, props),
  autoPalace: (deckId: string) =>
    post<Card[]>(`/api/decks/${deckId}/auto-palace`, {}),
  mutatePrompt: (cardId: string, mutationType: string) =>
    post<MutatePromptResponse>(`/api/review/${cardId}/mutate-prompt`, {
      mutation_type: mutationType,
    }),
  generateMnemonic: (cardId: string) =>
    post<GenerateMnemonicResponse>(`/api/review/${cardId}/generate-mnemonic`, {}),
  submitPrediction: (cardId: string, prediction: string, confidence: number) =>
    post<PretestPredictionResponse>(`/api/review/${cardId}/predict`, {
      prediction,
      confidence,
    }),
  getContrastDrill: (pairId: string) =>
    post<ContrastDrillResponse>(`/api/interference/${pairId}/contrast-drill`, {}),
}

/** Fresh id for one attempt at a card (see `confirmReview`). */
export function newReviewAttemptId(): string {
  if (typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function') {
    return crypto.randomUUID().replace(/-/g, '')
  }
  // randomUUID needs a secure context; plain http on a LAN address is not one.
  return `${Date.now().toString(36)}${Math.random().toString(36).slice(2, 14)}`.padEnd(16, '0')
}

const WS_POLICY_VIOLATION = 1008
const WS_RETRY_MIN_MS = 2_000
const WS_RETRY_MAX_MS = 60_000

export function createSyncSocket(onMessage: (event: SyncEvent) => void): () => void {
  if (!token.get()) return () => {}

  let ws: WebSocket | null = null
  let pingInterval: ReturnType<typeof setInterval> | null = null
  let reconnectTimeout: ReturnType<typeof setTimeout> | null = null
  let retryDelay = WS_RETRY_MIN_MS
  let disposed = false

  function connect() {
    if (disposed) return
    // Read at connect time: the token can be replaced while the page is open
    // (password change, "sign out everywhere").
    const current = token.get()
    if (!current) return
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const wsBase = BASE ? BASE.replace(/^http/, 'ws') : `${protocol}//${window.location.host}`
    const socket = new WebSocket(`${wsBase}/api/sync/ws`)
    ws = socket

    socket.onopen = () => {
      // The token goes in the first frame, not the URL: URLs are written to
      // server and proxy access logs.
      socket.send(JSON.stringify({ type: 'AUTH', token: current }))
      pingInterval = setInterval(() => {
        if (socket.readyState === WebSocket.OPEN) {
          socket.send(JSON.stringify({ type: 'PING' }))
        }
      }, 25000)
    }

    socket.onmessage = (e) => {
      try {
        const parsed = JSON.parse(e.data) as SyncEvent
        if (parsed.type === 'CONNECTED') retryDelay = WS_RETRY_MIN_MS
        onMessage(parsed)
      } catch (err) {
        console.debug('Failed to parse WS sync event', err)
      }
    }

    socket.onclose = (e) => {
      if (pingInterval) clearInterval(pingInterval)
      pingInterval = null
      if (disposed) return
      // The server refused the token. Retrying with the same one can only be
      // refused again; a new sign-in creates a new socket.
      if (e.code === WS_POLICY_VIOLATION) return
      reconnectTimeout = setTimeout(connect, retryDelay)
      retryDelay = Math.min(WS_RETRY_MAX_MS, retryDelay * 2)
    }

    socket.onerror = () => {
      socket.close()
    }
  }

  connect()

  return () => {
    disposed = true
    if (pingInterval) clearInterval(pingInterval)
    if (reconnectTimeout) clearTimeout(reconnectTimeout)
    if (ws) ws.close()
  }
}
