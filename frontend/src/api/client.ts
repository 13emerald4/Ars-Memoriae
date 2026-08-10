import type {
  Card,
  ConfirmReviewResponse,
  Deck,
  Extract,
  GenerateCardsResponse,
  Grade,
  ImportResult,
  NoteType,
  QueueConfig,
  QueueItem,
  SessionSummary,
  SisterPair,
  Source,
  Stats,
  SubmitAnswerResponse,
  SuggestedCard,
  User,
} from './types'

const BASE = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000'
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
  models: () => request<{ models: string[]; error?: string }>('/api/models'),

  // ── queue (§9) ──────────────────────────────────────────────────────────
  nextItem: () => request<QueueItem | null>('/api/queue/next'),
  session: () => request<SessionSummary>('/api/queue/session'),
  queueConfig: () => request<QueueConfig>('/api/queue-config'),
  updateQueueConfig: (body: Partial<QueueConfig>) => patch<QueueConfig>('/api/queue-config', body),

  // ── review (§7.1) ───────────────────────────────────────────────────────
  submitAnswer: (cardId: string, typed_answer: string, latency_ms: number) =>
    post<SubmitAnswerResponse>(`/api/review/${cardId}/answer`, { typed_answer, latency_ms }),
  confirmReview: (
    cardId: string,
    final_grade: Grade,
    overridden: boolean,
    typed_answer?: string,
    latency_ms?: number,
  ) =>
    post<ConfirmReviewResponse>(`/api/review/${cardId}/confirm`, {
      final_grade,
      overridden,
      typed_answer,
      latency_ms,
    }),

  // ── decks / notes / cards ───────────────────────────────────────────────
  decks: () => request<Deck[]>('/api/decks'),
  createDeck: (body: { name: string; default_priority?: number; parent_id?: string | null }) =>
    post<Deck>('/api/decks', body),
  updateDeck: (id: string, body: Record<string, unknown>) => patch<Deck>(`/api/decks/${id}`, body),
  deleteDeck: (id: string) => request<void>(`/api/decks/${id}`, { method: 'DELETE' }),
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
  setPriority: (target: 'deck' | 'card' | 'source' | 'extract', id: string, priority: number) =>
    patch<{ priority: number }>('/api/priority', { target, id, priority }),

  // ── incremental reading (§8) ────────────────────────────────────────────
  sources: () => request<Source[]>('/api/sources'),
  createSource: (body: { title?: string; raw_text?: string; url?: string; priority?: number }) =>
    post<Source>('/api/sources', body),
  deleteSource: (id: string) => request<void>(`/api/sources/${id}`, { method: 'DELETE' }),
  extractsOf: (sourceId: string) => request<Extract[]>(`/api/sources/${sourceId}/extracts`),
  extract: (id: string) => request<Extract>(`/api/extracts/${id}`),
  splitExtract: (id: string, body: { text?: string; start?: number; end?: number; priority?: number }) =>
    post<Extract>(`/api/extracts/${id}/split`, body),
  scheduleExtract: (id: string, body: { days?: number; status?: string; priority?: number }) =>
    post<Extract>(`/api/extracts/${id}/schedule`, body),
  generateCards: (id: string, body: { text?: string; max_cards?: number }) =>
    post<GenerateCardsResponse>(`/api/extracts/${id}/generate-cards`, body),
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
  stats: () => request<Stats>('/api/stats'),
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
}
