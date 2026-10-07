import type {
  AcceptDeckResponse,
  AtomicityLintResult,
  Bank,
  Card,
  CitedCard,
  CodeProblemOut,
  CodeProblemSummary,
  CodeProgressionStats,
  CodeSubmissionOut,
  ConfirmReviewResponse,
  Deck,
  DeckStats,
  DecomposeCardResponse,
  DocumentUpload,
  EventReadiness,
  Extract,
  GenerateCardsResponse,
  GenerateDeckResponse,
  Grade,
  ImportResult,
  JsonImportNote,
  JsonImportRequest,
  JsonImportResult,
  LearningAnalytics,
  Lesson,
  LexiconEntry,
  NoteType,
  QueueConfig,
  QueueItem,
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
  TreeNode,
  User,
  WeaknessHintResponse,
} from './types'

// When VITE_API_BASE_URL is not provided, use relative path '' so requests route through current origin / proxy
const BASE = import.meta.env.VITE_API_BASE_URL ?? ''
const TOKEN_KEY = 'memorization.token'

export const token = {
  get: () => localStorage.getItem(TOKEN_KEY),
  set: (t: string) => localStorage.setItem(TOKEN_KEY, t),
  clear: () => localStorage.removeItem(TOKEN_KEY),
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

  if (resp.status === 401) {
    token.clear()
    throw new ApiError(401, 'Session expired — please sign in again.')
  }
  if (resp.status === 204) return null as T
  if (!resp.ok) {
    let detail = `${resp.status} ${resp.statusText}`
    try {
      const body = await resp.json()
      if (typeof body.detail === 'string') detail = body.detail
      else if (Array.isArray(body.detail)) detail = body.detail.map((d: any) => d.msg).join('; ')
    } catch {
      /* keep the status line */
    }
    throw new ApiError(resp.status, detail)
  }
  const text = await resp.text()
  return (text ? JSON.parse(text) : null) as T
}

const post = <T,>(path: string, body?: unknown) =>
  request<T>(path, { method: 'POST', body: body === undefined ? undefined : JSON.stringify(body) })
const patch = <T,>(path: string, body: unknown) =>
  request<T>(path, { method: 'PATCH', body: JSON.stringify(body) })

export const api = {
  // ── auth ────────────────────────────────────────────────────────────────
  register: (email: string, password: string) =>
    post<{ access_token: string }>('/api/auth/register', { email, password }),
  login: (email: string, password: string) =>
    post<{ access_token: string }>('/api/auth/login', { email, password }),
  me: () => request<User>('/api/me'),
  updateMe: (body: Partial<User>) => patch<User>('/api/me', body),

  // ── keys (§4.2 BYOK) ────────────────────────────────────────────────────
  storeKey: (api_key: string) =>
    post<{ stored: boolean; masked: string; available_models: string[]; warning: string | null }>(
      '/api/keys',
      { api_key },
    ),
  deleteKey: () => request<{ stored: boolean }>('/api/keys', { method: 'DELETE' }),
  models: () => request<{ models: string[]; active?: string; error?: string }>('/api/models'),
  llmStatus: () =>
    request<{
      connected: boolean
      provider: string
      base_url: string
      model: string
      models_installed: string[]
      model_ready: boolean
      error?: string | null
    }>('/api/llm/status'),

  // ── queue (§9) ──────────────────────────────────────────────────────────
  // `branch` scopes the session to one knowledge-tree subtree.
  nextItem: (branch?: string | null) =>
    request<QueueItem | null>(`/api/queue/next${branch ? `?branch=${branch}` : ''}`),
  session: (branch?: string | null) =>
    request<SessionSummary>(`/api/queue/session${branch ? `?branch=${branch}` : ''}`),
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
  guide: (cardId: string, history: SocraticTurn[], message: string) =>
    post<SocraticResponse>(`/api/review/${cardId}/guide`, { history, message }),
  weaknessHint: (cardId: string) =>
    post<WeaknessHintResponse>(`/api/review/${cardId}/weakness-hint`, {}),
  socraticLineHint: (cardId: string, body: SocraticLineHintRequest) =>
    post<SocraticLineHintResponse>(`/api/review/${cardId}/line-hint`, body),
  submitAnswer: (cardId: string, typed_answer: string, latency_ms: number, test_code?: string) =>
    post<SubmitAnswerResponse>(`/api/review/${cardId}/answer`, { typed_answer, latency_ms, test_code }),
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
  ) =>
    post<ConfirmReviewResponse>(`/api/review/${cardId}/confirm`, {
      final_grade,
      overridden,
      typed_answer,
      latency_ms,
      confidence,
      is_blitz: Boolean(is_blitz),
    }),

  // ── decks / notes / cards ───────────────────────────────────────────────
  decks: () => request<Deck[]>('/api/decks'),
  deckStats: (id: string) => request<DeckStats>(`/api/decks/${id}/stats`),
  deckPersistItems: (deckId: string) => request<QueueItem[]>(`/api/decks/${deckId}/persist-items`),
  createDeck: (body: { name: string; default_priority?: number; parent_id?: string | null }) =>
    post<Deck>('/api/decks', body),
  updateDeck: (id: string, body: Record<string, unknown>) => patch<Deck>(`/api/decks/${id}`, body),
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
  acceptDeck: (sourceId: string, deck: string, cards: CitedCard[]) =>
    post<AcceptDeckResponse>(`/api/documents/${sourceId}/accept-deck`, { deck, cards }),

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
  moveNode: (id: string, parent_id: string | null) =>
    post<{ id: string; parent_id: string | null }>(`/api/tree/nodes/${id}/move`, { parent_id }),
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
  importApkg: (file: File) => {
    const form = new FormData()
    form.append('file', file)
    return request<ImportResult>('/api/import/apkg', { method: 'POST', body: form })
  },
  importHistory: () => request<ImportResult[]>('/api/import/history'),
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
    body: { code: string; language?: string; deck_id?: string },
  ) => post<SubmitCodeResponse>(`/api/code/problems/${idOrSlug}/submit`, body),
  socraticCodeHint: (
    idOrSlug: string,
    body: { code: string; language?: string; hint_type?: string },
  ) => post<SocraticCodeResponse>(`/api/code/problems/${idOrSlug}/socratic`, body),
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
  lookupLexicon: (term: string, context?: string | null, cardId?: string | null) =>
    post<LexiconEntry>('/api/lexicon/lookup', { term, context, card_id: cardId }),
  getRecentLexicon: () => request<RecentLexiconItem[]>('/api/lexicon/recent'),
}
