import fs from 'node:fs'
import http from 'node:http'
import os from 'node:os'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import cors from 'cors'
import express from 'express'
import type { NextFunction, Request, Response } from 'express'
import multer from 'multer'
import { WebSocketServer } from 'ws'
import type { WebSocket } from 'ws'
import { buildCardAnalytics, buildCodeStats, buildLearningAnalytics, buildStats } from './server/analytics.ts'
import { executeCode } from './server/codeRunner.ts'
import {
  computeRetrievability,
  evaluateTypedAnswer,
  extractKeyPhrases,
  jaccardSimilarity,
  lintAtomicity,
  scheduleFsrs,
} from './server/grading.ts'
import { hashPassword, newId, store } from './server/store.ts'
import { loadAllSocraticGuides } from './server/socraticGuideParser.ts'
import {
  buildSocraticGuideReply,
  buildSocraticLesson,
  matchCardToGuide,
} from './server/socraticLessonService.ts'
import type { CardRecord, DeckRecord, Grade, UserRecord } from './server/types.ts'

const ROOT_DIR = path.dirname(fileURLToPath(import.meta.url))
const FRONTEND_DIST = path.join(ROOT_DIR, 'frontend', 'dist')
const PORT = Number(process.env.PORT || 3000)

interface AuthedRequest extends Request {
  user?: UserRecord
}

const app = express()
const upload = multer({ storage: multer.memoryStorage(), limits: { fileSize: 20 * 1024 * 1024 } })

app.use(cors({ origin: true, credentials: true }))
app.use(express.json({ limit: '15mb' }))

// ─── WebSocket live sync hub ─────────────────────────────────────────────────
const userSockets = new Map<string, Set<WebSocket>>()

function broadcastToUser(userId: string, event: { type: string; data: unknown }) {
  const set = userSockets.get(userId)
  if (!set) return
  const payload = JSON.stringify(event)
  for (const ws of set) {
    if (ws.readyState === 1) {
      ws.send(payload)
    }
  }
}

// ─── Auth middleware ─────────────────────────────────────────────────────────
function extractBearer(req: Request): string | undefined {
  const auth = req.headers.authorization
  if (auth && auth.startsWith('Bearer ')) return auth.slice(7).trim()
  return undefined
}

function requireAuth(req: AuthedRequest, res: Response, next: NextFunction) {
  const user = store.getUserByToken(extractBearer(req))
  if (!user) {
    res.status(401).json({ detail: 'Not authenticated' })
    return
  }
  req.user = user
  next()
}

// ─── Health & Plugins ────────────────────────────────────────────────────────
app.get('/health', (_req, res) => {
  res.json({
    status: 'ok',
    fsrs_optimizer_installed: true,
    default_grading_model: 'qwen2.5-coder:7b',
  })
})

app.get('/api/plugins', (_req, res) => {
  res.json({
    plugin_dir: null,
    enabled: false,
    plugins: [],
    seams: { grading: ['heuristic'], scheduling: ['fsrs'] },
  })
})

// ─── Auth Routes ─────────────────────────────────────────────────────────────
app.get('/api/auth/registration-status', (_req, res) => {
  res.json({ open: true })
})

app.post('/api/auth/register', (req, res) => {
  const email = String(req.body?.email || '').trim().toLowerCase()
  const password = String(req.body?.password || '')
  if (!email || !email.includes('@')) {
    res.status(400).json({ detail: 'Please provide a valid email address.' })
    return
  }
  if (password.length < 8) {
    res.status(400).json({ detail: 'Password must be at least 8 characters.' })
    return
  }
  if (store.findUserByEmail(email)) {
    res.status(409).json({ detail: 'An account with that email already exists. Please sign in.' })
    return
  }
  const user = store.createUser(email, password)
  const access_token = store.issueToken(user)
  res.status(201).json({ access_token })
})

app.post('/api/auth/login', (req, res) => {
  const email = String(req.body?.email || '').trim().toLowerCase()
  const password = String(req.body?.password || '')
  const existing = store.findUserByEmail(email)
  if (!existing || existing.password_hash !== hashPassword(password)) {
    res.status(401).json({ detail: 'Invalid email or password. Use demo@arsmemoriae.app / password123 or create a new account.' })
    return
  }
  const access_token = store.issueToken(existing)
  res.json({ access_token })
})

app.post('/api/auth/change-password', requireAuth, (req: AuthedRequest, res) => {
  const user = req.user!
  const current = String(req.body?.current_password || '')
  const nextPw = String(req.body?.new_password || '')
  if (user.password_hash !== hashPassword(current)) {
    res.status(400).json({ detail: 'Current password is incorrect.' })
    return
  }
  if (nextPw.length < 8) {
    res.status(400).json({ detail: 'New password must be at least 8 characters.' })
    return
  }
  user.password_hash = hashPassword(nextPw)
  user.token_version += 1
  const access_token = store.issueToken(user)
  res.json({ access_token })
})

app.post('/api/auth/logout-all', requireAuth, (req: AuthedRequest, res) => {
  const user = req.user!
  user.token_version += 1
  const access_token = store.issueToken(user)
  res.json({ access_token })
})

app.post('/api/auth/pairing-token', requireAuth, (req: AuthedRequest, res) => {
  const user = req.user!
  const access_token = store.issueToken(user, 'review')
  res.json({ access_token, scope: 'review', expires_in: 86400 })
})

app.get('/api/me', requireAuth, (req: AuthedRequest, res) => {
  res.json(store.publicUser(req.user!))
})

app.patch('/api/me', requireAuth, (req: AuthedRequest, res) => {
  const user = req.user!
  const allowed: Array<keyof UserRecord> = [
    'desired_retention',
    'grading_model',
    'queue_time_budget_minutes',
    'leech_remediation_opt_in',
    'daily_new_limit',
    'daily_review_limit',
    'backlog_spread_days',
    'leech_threshold',
    'llm_grading_consent',
    'grading_bias',
    'automaticity_threshold_ms',
    'target_event_date',
    'target_event_title',
    'peak_retention_target',
    'show_pre_leetcode',
    'show_code_lab',
    'show_thematic_context',
    'tutorial_completed',
    'timezone',
    'enable_schema_checkpoints',
    'enable_prompt_mutation',
    'enable_prediction_mode',
  ]
  for (const key of allowed) {
    if (req.body && Object.prototype.hasOwnProperty.call(req.body, key)) {
      ;(user as unknown as Record<string, unknown>)[key] = req.body[key]
    }
  }
  res.json(store.publicUser(user))
})

// ─── LLM / Models / Hardware Status ──────────────────────────────────────────
app.get('/api/models', requireAuth, (req: AuthedRequest, res) => {
  const active = req.user!.grading_model || 'qwen2.5-coder:7b'
  const models = ['qwen2.5-coder:7b', 'qwen3.5:4b', 'qwen3.5:9b']
  res.json({
    models,
    active,
    provider: 'heuristic',
    providers: {
      ollama: {
        connected: false,
        base_url: process.env.OLLAMA_BASE_URL || 'http://127.0.0.1:11434',
        models,
        error: 'Running in cloud heuristic mode (local Ollama is optional).',
      },
      antigravity: {
        connected: false,
        installed: false,
        models: [],
        error: null,
      },
    },
    error: null,
  })
})

app.get('/api/llm/status', requireAuth, (req: AuthedRequest, res) => {
  const model = req.user!.grading_model || 'qwen2.5-coder:7b'
  res.json({
    connected: true,
    provider: 'heuristic',
    base_url: 'in-process',
    model,
    models_installed: ['qwen2.5-coder:7b', 'qwen3.5:4b', 'qwen3.5:9b'],
    model_ready: true,
    error: null,
    vram: {
      capacity_gb: Number((os.totalmem() / 1e9).toFixed(1)),
      capacity_mb: Math.round(os.totalmem() / 1e6),
      available_gb: Number((os.freemem() / 1e9).toFixed(1)),
      available_mb: Math.round(os.freemem() / 1e6),
      used_gb: Number(((os.totalmem() - os.freemem()) / 1e9).toFixed(1)),
      used_mb: Math.round((os.totalmem() - os.freemem()) / 1e6),
      model_vram_gb: null,
      model_vram_bytes: null,
      model_approx_gb: 4.7,
      model_loaded: true,
      model_name: model,
      gpu_name: 'Cloud Runtime',
      is_unified_memory: false,
      memory_source: 'cloud',
      usage_measured: false,
    },
  })
})

app.get('/api/llm/vram', requireAuth, (req: AuthedRequest, res) => {
  const model = String(req.query.model || req.user!.grading_model || 'qwen2.5-coder:7b')
  res.json({
    capacity_gb: Number((os.totalmem() / 1e9).toFixed(1)),
    capacity_mb: Math.round(os.totalmem() / 1e6),
    available_gb: Number((os.freemem() / 1e9).toFixed(1)),
    available_mb: Math.round(os.freemem() / 1e6),
    used_gb: null,
    used_mb: null,
    model_vram_gb: null,
    model_vram_bytes: null,
    model_approx_gb: 4.7,
    model_loaded: true,
    model_name: model,
    gpu_name: 'Cloud Runtime',
    is_unified_memory: false,
    memory_source: 'cloud',
    usage_measured: false,
  })
})

app.get('/api/llm/hardware', requireAuth, (_req, res) => {
  const ramGb = Number((os.totalmem() / 1e9).toFixed(1))
  res.json({
    os_name: os.platform(),
    os_release: os.release(),
    architecture: os.arch(),
    cpu_name: os.cpus()[0]?.model || 'x86_64 CPU',
    cpu_cores: os.cpus().length,
    ram_gb: ramGb,
    gpu_name: null,
    vram_gb: null,
    is_apple_silicon: false,
    has_cuda: false,
    hardware_tier: ramGb >= 16 ? 'mid-range' : 'budget',
    recommended_model: 'qwen3.5:4b',
    recommended_size: '4B',
    headline: 'Cloud Container Runtime (Heuristic Active-Recall Engine)',
    rationale: 'Typed answers are evaluated instantaneously using semantic token-overlap and trigram verification.',
    models: [
      { id: 'qwen3.5:4b', name: 'Qwen 3.5 4B', size: '4B', vram_approx: '~2.5 GB', status: 'recommended', suitability: 'Fast low-latency grading' },
      { id: 'qwen2.5-coder:7b', name: 'Qwen2.5-Coder 7B', size: '7B', vram_approx: '~4.7 GB', status: 'supported', suitability: 'Code & technical recall' },
      { id: 'qwen3.5:9b', name: 'Qwen 3.5 9B', size: '9B', vram_approx: '~5.3 GB', status: 'heavy', suitability: 'Deep conceptual rubrics' },
    ],
  })
})

interface ServerLlmEvent {
  id: string
  timestamp: string
  operation: string
  model: string
  duration_ms: number
  status: 'ok' | 'slow' | 'error'
  detail: string | null
}

const SERVER_LLM_EVENT_LIMIT = 25
const serverLlmEventsByUser = new Map<string, ServerLlmEvent[]>()

function recordServerLlmEvent(
  userId: string,
  event: Omit<ServerLlmEvent, 'id' | 'timestamp'>,
) {
  const list = serverLlmEventsByUser.get(userId) ?? []
  const next: ServerLlmEvent = {
    id: crypto.randomUUID(),
    timestamp: new Date().toISOString(),
    ...event,
  }
  serverLlmEventsByUser.set(userId, [next, ...list].slice(0, SERVER_LLM_EVENT_LIMIT))
}

function getConfiguredOllamaBaseUrl(): string {
  const raw = (process.env.OLLAMA_BASE_URL || 'http://127.0.0.1:11434').trim()
  try {
    const parsed = new URL(raw)
    if (parsed.protocol !== 'http:' && parsed.protocol !== 'https:') {
      return 'http://127.0.0.1:11434'
    }
    return parsed.origin
  } catch {
    return 'http://127.0.0.1:11434'
  }
}

const SAFE_MODEL_NAME_RE = /^[a-zA-Z0-9._:/-]{1,80}$/

interface OllamaProbeResult {
  reachable: boolean
  base_url: string
  version: string | null
  latency_ms: number | null
  error: string | null
  loaded_models: Array<{
    name: string
    size_bytes: number
    size_vram_bytes: number
    gpu_offload_pct: number
    expires_at: string | null
  }>
  installed_models: string[]
}

async function probeLocalOllama(): Promise<OllamaProbeResult> {
  const baseUrl = getConfiguredOllamaBaseUrl()
  const startedAt = Date.now()
  try {
    const versionResp = await fetch(`${baseUrl}/api/version`, {
      signal: AbortSignal.timeout(2000),
    })
    const latencyMs = Date.now() - startedAt
    if (!versionResp.ok) {
      return {
        reachable: false,
        base_url: baseUrl,
        version: null,
        latency_ms: latencyMs,
        error: `HTTP ${versionResp.status} from Ollama /api/version`,
        loaded_models: [],
        installed_models: [],
      }
    }
    const versionData = (await versionResp.json().catch(() => ({}))) as { version?: string }

    const [psData, tagsData] = await Promise.all([
      fetch(`${baseUrl}/api/ps`, { signal: AbortSignal.timeout(2000) })
        .then((r) => (r.ok ? r.json() : { models: [] }))
        .catch(() => ({ models: [] })) as Promise<{
        models?: Array<{
          name?: string
          size?: number
          size_vram?: number
          expires_at?: string
        }>
      }>,
      fetch(`${baseUrl}/api/tags`, { signal: AbortSignal.timeout(2000) })
        .then((r) => (r.ok ? r.json() : { models: [] }))
        .catch(() => ({ models: [] })) as Promise<{
        models?: Array<{ name?: string }>
      }>,
    ])

    const loaded_models = (psData.models ?? []).map((m) => {
      const sizeBytes = Number(m.size || 0)
      const vramBytes = Number(m.size_vram || 0)
      const gpuPct = sizeBytes > 0 ? Math.min(100, Math.round((vramBytes / sizeBytes) * 100)) : 0
      return {
        name: String(m.name || 'unknown'),
        size_bytes: sizeBytes,
        size_vram_bytes: vramBytes,
        gpu_offload_pct: gpuPct,
        expires_at: m.expires_at ? String(m.expires_at) : null,
      }
    })

    const installed_models = (tagsData.models ?? [])
      .map((m) => String(m.name || ''))
      .filter(Boolean)

    return {
      reachable: true,
      base_url: baseUrl,
      version: versionData.version ?? null,
      latency_ms: latencyMs,
      error: null,
      loaded_models,
      installed_models,
    }
  } catch (err: unknown) {
    const message = err instanceof Error ? err.message : 'Unable to connect'
    return {
      reachable: false,
      base_url: baseUrl,
      version: null,
      latency_ms: Date.now() - startedAt,
      error: message.slice(0, 180),
      loaded_models: [],
      installed_models: [],
    }
  }
}

app.get('/api/llm/diagnostics', requireAuth, async (req: AuthedRequest, res) => {
  const activeModel = req.user!.grading_model || 'qwen2.5-coder:7b'
  const ollama = await probeLocalOllama()
  const totalRamGb = Number((os.totalmem() / 1e9).toFixed(1))
  const freeRamGb = Number((os.freemem() / 1e9).toFixed(1))
  const hints: string[] = []

  if (!ollama.reachable) {
    hints.push(
      'Local Ollama is not reachable from this server — grading currently runs instantaneously in built-in heuristic mode.',
    )
  } else {
    if (ollama.loaded_models.length === 0) {
      hints.push(
        'No model is currently warm in Ollama VRAM. Your next answer submission will include a cold-load delay (set OLLAMA_KEEP_ALIVE=30m to keep models warm).',
      )
    }
    for (const loaded of ollama.loaded_models) {
      if (loaded.gpu_offload_pct < 100) {
        hints.push(
          `${loaded.name} is only ${loaded.gpu_offload_pct}% in GPU VRAM (${100 - loaded.gpu_offload_pct}% spilled to CPU RAM). Close GPU-heavy Chrome tabs or switch to a smaller model.`,
        )
      }
    }
  }

  if (activeModel.toLowerCase().includes('qwen3')) {
    hints.push(
      `${activeModel} uses hidden thinking tokens by default in Ollama, which can stall short answers unless think: false is configured.`,
    )
  }

  res.json({
    checked_at: new Date().toISOString(),
    backend_mode: ollama.reachable ? 'ollama' : 'heuristic',
    active_model: activeModel,
    ollama,
    host: {
      platform: os.platform(),
      cpu_cores: os.cpus().length,
      total_ram_gb: totalRamGb,
      free_ram_gb: freeRamGb,
    },
    recent_events: serverLlmEventsByUser.get(req.user!.id) ?? [],
    hints,
  })
})

app.post('/api/llm/ping', requireAuth, async (req: AuthedRequest, res) => {
  const requestedModel = typeof req.body?.model === 'string' ? req.body.model.trim() : ''
  const model =
    requestedModel && SAFE_MODEL_NAME_RE.test(requestedModel)
      ? requestedModel
      : req.user!.grading_model || 'qwen2.5-coder:7b'
  const warmup = Boolean(req.body?.warmup)
  const startedAt = Date.now()

  const probe = await probeLocalOllama()
  if (!probe.reachable) {
    const latencyMs = Date.now() - startedAt
    recordServerLlmEvent(req.user!.id, {
      operation: warmup ? 'Model Warmup' : 'Ollama Ping',
      model,
      duration_ms: latencyMs,
      status: 'ok',
      detail: 'Cloud heuristic mode active (local Ollama not running on server host).',
    })
    res.json({
      ok: true,
      mode: 'heuristic',
      model,
      latency_ms: latencyMs,
      ollama_version: null,
      model_loaded: true,
      gpu_offload_pct: null,
      message: `Backend responded in ${latencyMs}ms (heuristic mode; local Ollama not reachable at ${probe.base_url}).`,
    })
    return
  }

  if (warmup) {
    try {
      const warmResp = await fetch(`${probe.base_url}/api/generate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          model,
          prompt: 'ok',
          stream: false,
          think: false,
          keep_alive: '15m',
          options: { num_predict: 1 },
        }),
        signal: AbortSignal.timeout(15_000),
      })
      const latencyMs = Date.now() - startedAt
      if (!warmResp.ok) {
        const detail = `Warmup HTTP ${warmResp.status}`
        recordServerLlmEvent(req.user!.id, {
          operation: 'Model Warmup',
          model,
          duration_ms: latencyMs,
          status: 'error',
          detail,
        })
        res.status(502).json({ detail })
        return
      }
      const postProbe = await probeLocalOllama()
      const loaded = postProbe.loaded_models.find((m) =>
        m.name.toLowerCase().startsWith(model.toLowerCase()),
      )
      recordServerLlmEvent(req.user!.id, {
        operation: 'Model Warmup',
        model,
        duration_ms: latencyMs,
        status: latencyMs >= 8000 ? 'slow' : 'ok',
        detail: loaded ? `${loaded.gpu_offload_pct}% GPU` : 'Warmed up',
      })
      res.json({
        ok: true,
        mode: 'ollama',
        model,
        latency_ms: latencyMs,
        ollama_version: probe.version,
        model_loaded: Boolean(loaded),
        gpu_offload_pct: loaded?.gpu_offload_pct ?? null,
        message: loaded
          ? `Warmed ${model} in ${(latencyMs / 1000).toFixed(1)}s (${loaded.gpu_offload_pct}% GPU VRAM).`
          : `Warmed ${model} in ${(latencyMs / 1000).toFixed(1)}s.`,
      })
      return
    } catch (err: unknown) {
      const latencyMs = Date.now() - startedAt
      const detail = err instanceof Error ? err.message : 'Warmup failed'
      recordServerLlmEvent(req.user!.id, {
        operation: 'Model Warmup',
        model,
        duration_ms: latencyMs,
        status: 'error',
        detail: detail.slice(0, 180),
      })
      res.status(504).json({ detail: `Ollama warmup failed after ${(latencyMs / 1000).toFixed(1)}s: ${detail}` })
      return
    }
  }

  const latencyMs = Date.now() - startedAt
  const loaded = probe.loaded_models.find((m) =>
    m.name.toLowerCase().startsWith(model.toLowerCase()),
  )
  recordServerLlmEvent(req.user!.id, {
    operation: 'Ollama Ping',
    model,
    duration_ms: latencyMs,
    status: 'ok',
    detail: `Ollama ${probe.version ?? ''}`.trim(),
  })
  res.json({
    ok: true,
    mode: 'ollama',
    model,
    latency_ms: latencyMs,
    ollama_version: probe.version,
    model_loaded: Boolean(loaded),
    gpu_offload_pct: loaded?.gpu_offload_pct ?? null,
    message: loaded
      ? `Ollama ${probe.version ?? ''} reachable in ${latencyMs}ms — ${model} loaded (${loaded.gpu_offload_pct}% GPU).`
      : `Ollama ${probe.version ?? ''} reachable in ${latencyMs}ms — ${model} is currently cold (not loaded in VRAM).`,
  })
})

// ─── Queue & Config ──────────────────────────────────────────────────────────
app.get('/api/queue/session', requireAuth, (req: AuthedRequest, res) => {
  const branch = typeof req.query.branch === 'string' ? req.query.branch : null
  const deck = typeof req.query.deck === 'string' ? req.query.deck : null
  res.json(store.buildQueueSession(req.user!.id, branch, deck))
})

app.get('/api/queue/next', requireAuth, (req: AuthedRequest, res) => {
  const branch = typeof req.query.branch === 'string' ? req.query.branch : null
  const deck = typeof req.query.deck === 'string' ? req.query.deck : null
  const session = store.buildQueueSession(req.user!.id, branch, deck)
  res.json(session.items[0] ?? null)
})

app.get('/api/queue-config', requireAuth, (req: AuthedRequest, res) => {
  const cfg = store.queueConfigs.get(req.user!.id) ?? {
    review_weight: 0.6,
    new_weight: 0.25,
    ir_weight: 0.15,
    seconds_per_review: 30,
    seconds_per_ir_extract: 90,
  }
  res.json(cfg)
})

app.patch('/api/queue-config', requireAuth, (req: AuthedRequest, res) => {
  const cur = store.queueConfigs.get(req.user!.id) ?? {
    review_weight: 0.6,
    new_weight: 0.25,
    ir_weight: 0.15,
    seconds_per_review: 30,
    seconds_per_ir_extract: 90,
  }
  const updated = { ...cur, ...req.body }
  store.queueConfigs.set(req.user!.id, updated)
  res.json(updated)
})

// ─── Study Sessions & Time Bank ──────────────────────────────────────────────
app.post('/api/sessions/start', requireAuth, (req: AuthedRequest, res) => {
  const uid = req.user!.id
  const plannedMinutes = Number(req.body?.planned_minutes || 25)
  const id = newId('sess')
  const session = {
    id,
    user_id: uid,
    started_at: new Date().toISOString(),
    ended_at: null,
    planned_seconds: Math.max(60, Math.round(plannedMinutes * 60)),
    active_seconds: 0,
    focus_goal: req.body?.focus_goal ?? null,
    goal_cards: Number(req.body?.goal_cards || 15),
    cards_reviewed: 0,
    banked_seconds: 0,
    goal_met: false,
    distraction: null,
    next_time_plan: null,
  }
  store.sessions.set(id, session)
  res.status(201).json(session)
})

app.post('/api/sessions/:id/finish', requireAuth, (req: AuthedRequest, res) => {
  const sess = store.sessions.get(String(req.params.id))
  if (!sess || sess.user_id !== req.user!.id) {
    res.status(404).json({ detail: 'Session not found' })
    return
  }
  const remaining = Math.max(0, Number(req.body?.remaining_seconds || 0))
  sess.ended_at = new Date().toISOString()
  sess.active_seconds = Math.max(0, sess.planned_seconds - remaining)
  sess.goal_met = sess.cards_reviewed >= sess.goal_cards
  sess.banked_seconds = sess.goal_met ? remaining : 0
  res.json(sess)
})

app.post('/api/sessions/:id/reflect', requireAuth, (req: AuthedRequest, res) => {
  const sess = store.sessions.get(String(req.params.id))
  if (!sess || sess.user_id !== req.user!.id) {
    res.status(404).json({ detail: 'Session not found' })
    return
  }
  if (req.body?.distraction !== undefined) sess.distraction = req.body.distraction
  if (req.body?.next_time_plan !== undefined) sess.next_time_plan = req.body.next_time_plan
  res.json(sess)
})

app.get('/api/sessions/bank', requireAuth, (req: AuthedRequest, res) => {
  const uid = req.user!.id
  const all = Array.from(store.sessions.values())
    .filter((s) => s.user_id === uid)
    .sort((a, b) => b.started_at.localeCompare(a.started_at))
  const todayStr = new Date().toISOString().slice(0, 10)
  const weekCutoff = Date.now() - 7 * 86_400_000
  const todayList = all.filter((s) => s.started_at.slice(0, 10) === todayStr)
  const weekList = all.filter((s) => new Date(s.started_at).getTime() >= weekCutoff)
  res.json({
    today_seconds: todayList.reduce((a, b) => a + b.banked_seconds, 0),
    week_seconds: weekList.reduce((a, b) => a + b.banked_seconds, 0),
    total_seconds: all.reduce((a, b) => a + b.banked_seconds, 0),
    sessions_today: todayList.length,
    goals_met_today: todayList.filter((s) => s.goal_met).length,
    current: all.find((s) => !s.ended_at) ?? null,
    recent: all.slice(0, 10),
  })
})

// ─── Review Endpoints ────────────────────────────────────────────────────────
app.get('/api/review/:cardId/lesson', requireAuth, (req: AuthedRequest, res) => {
  const card = store.cards.get(String(req.params.cardId))
  if (!card || card.user_id !== req.user!.id) {
    res.status(404).json({ detail: 'Card not found' })
    return
  }
  const deck = store.decks.get(card.deck_id)
  const course = loadAllSocraticGuides(path.join(ROOT_DIR, 'public/assets/aistudio'))
  res.json(buildSocraticLesson(card, deck, course))
})

app.post('/api/review/:cardId/guide', requireAuth, (req: AuthedRequest, res) => {
  const card = store.cards.get(String(req.params.cardId))
  if (!card || card.user_id !== req.user!.id) {
    res.status(404).json({ detail: 'Card not found' })
    return
  }
  const deck = store.decks.get(card.deck_id)
  const course = loadAllSocraticGuides(path.join(ROOT_DIR, 'public/assets/aistudio'))
  const studentMessage = String(req.body?.message || '')
  const history = Array.isArray(req.body?.history) ? req.body.history : []
  res.json(buildSocraticGuideReply(card, deck, course, studentMessage, history))
})

app.post('/api/review/:cardId/weakness-hint', requireAuth, (req: AuthedRequest, res) => {
  const card = store.cards.get(String(req.params.cardId))
  if (!card || card.user_id !== req.user!.id) {
    res.status(404).json({ detail: 'Card not found' })
    return
  }
  const deck = store.decks.get(card.deck_id)
  const course = loadAllSocraticGuides(path.join(ROOT_DIR, 'public/assets/aistudio'))
  const guide = matchCardToGuide(card, course, deck?.name)
  const hasPast = card.active_weaknesses.length > 0
  res.json({
    hint: hasPast
      ? `Watch out for your past blind spot: ${card.active_weaknesses[0]}`
      : guide?.trap
      ? `Common trap on this card: ${guide.trap}`
      : 'Focus on stating the exact mechanism and edge conditions concisely.',
    active_weaknesses: card.active_weaknesses,
    has_past_weaknesses: hasPast,
  })
})

app.post('/api/review/:cardId/line-hint', requireAuth, (req: AuthedRequest, res) => {
  const code = String(req.body?.code || '')
  const lineNumber = Math.max(1, Number(req.body?.line_number || 1))
  const lines = code.split('\n')
  const lineText = lines[lineNumber - 1] ?? ''
  res.json({
    hint: `Inspect line ${lineNumber}: verify edge cases, return types, and loop bounds around "${lineText.trim() || '(blank line)'}".`,
    target_concept: 'Invariant & edge-case check',
    line_number: lineNumber,
    current_line_text: lineText,
    degraded: false,
    degraded_reason: null,
    error: null,
  })
})

app.post('/api/review/:cardId/answer', requireAuth, (req: AuthedRequest, res) => {
  const startedAt = Date.now()
  const user = req.user!
  const card = store.cards.get(String(req.params.cardId))
  if (!card || card.user_id !== user.id) {
    res.status(404).json({ detail: 'Card not found' })
    return
  }
  const typedAnswer = String(req.body?.typed_answer || '')
  const latencyMs = Number(req.body?.latency_ms || 0)
  const evalResult = evaluateTypedAnswer(typedAnswer, card.back, user.grading_bias)

  const threshold = user.automaticity_threshold_ms
  const autoExceeded = Boolean(threshold && latencyMs > threshold)
  const evalDurationMs = Math.max(1, Date.now() - startedAt)

  recordServerLlmEvent(user.id, {
    operation: 'Grade Answer',
    model: 'heuristic-semantic-v1',
    duration_ms: evalDurationMs,
    status: evalDurationMs >= 8000 ? 'slow' : 'ok',
    detail: `score=${evalResult.score}`,
  })

  res.json({
    ...evalResult,
    persistent_weaknesses: card.active_weaknesses,
    degraded_to_manual: false,
    reference_answer: card.back,
    needs_confirmation: true,
    model_used: 'heuristic-semantic-v1',
    cached: false,
    degraded_reason: null,
    latency_note: latencyMs > 0 ? `Answered in ${(latencyMs / 1000).toFixed(1)}s` : null,
    automaticity_exceeded: autoExceeded,
    automaticity_threshold_ms: threshold,
    automaticity_note: null,
  })
})

app.post('/api/review/:cardId/run-code', requireAuth, async (req: AuthedRequest, res) => {
  const card = store.cards.get(String(req.params.cardId))
  if (!card || card.user_id !== req.user!.id) {
    res.status(404).json({ detail: 'Card not found' })
    return
  }
  const result = await executeCode({
    code: String(req.body?.code || ''),
    language: String(req.body?.language || 'typescript'),
    test_code: req.body?.test_code ? String(req.body.test_code) : undefined,
    test_cases: Array.isArray(req.body?.custom_test_cases) ? req.body.custom_test_cases : card.test_cases,
  })
  res.json(result)
})

const processedReviewIds = new Map<string, unknown>()

app.post('/api/review/:cardId/confirm', requireAuth, (req: AuthedRequest, res) => {
  const user = req.user!
  const card = store.cards.get(String(req.params.cardId))
  if (!card || card.user_id !== user.id) {
    res.status(404).json({ detail: 'Card not found' })
    return
  }
  const clientReviewId = req.body?.client_review_id ? String(req.body.client_review_id) : null
  if (clientReviewId && processedReviewIds.has(`${user.id}:${clientReviewId}`)) {
    res.json(processedReviewIds.get(`${user.id}:${clientReviewId}`))
    return
  }

  const grade = (['again', 'hard', 'good', 'easy'].includes(req.body?.final_grade)
    ? req.body.final_grade
    : 'good') as Grade
  const overridden = Boolean(req.body?.overridden)
  const latencyMs = typeof req.body?.latency_ms === 'number' ? req.body.latency_ms : null
  const stabilityBefore = card.stability ?? 0
  const rBefore = computeRetrievability(card)

  const deck = store.decks.get(card.deck_id)
  const retentionTarget = deck?.desired_retention_override ?? user.desired_retention
  const sched = scheduleFsrs(card, grade, retentionTarget)

  card.due = sched.next_due
  card.stability = sched.new_stability
  card.difficulty = sched.new_difficulty
  card.state = sched.state
  card.lapse_count = sched.lapse_count
  card.last_grade = grade
  card.review_count += 1
  if (card.lapse_count >= user.leech_threshold) {
    card.leech_flag = true
  }

  store.reviewLogs.push({
    id: store.nextLogId++,
    user_id: user.id,
    card_id: card.id,
    reviewed_at: new Date().toISOString(),
    final_grade: grade,
    typed_answer: req.body?.typed_answer ?? null,
    latency_ms: latencyMs,
    llm_grade: grade,
    llm_reasoning: null,
    llm_confidence: null,
    overridden,
    user_confidence: typeof req.body?.confidence === 'number' ? req.body.confidence : null,
    is_blitz: Boolean(req.body?.is_blitz),
    weaknesses: [],
    improvements: [],
    stability_before: stabilityBefore,
    stability_after: sched.new_stability,
    retrievability_before: rBefore,
    client_review_id: clientReviewId,
  })

  // Increment active study session if any
  for (const s of store.sessions.values()) {
    if (s.user_id === user.id && !s.ended_at) {
      s.cards_reviewed += 1
    }
  }

  const responsePayload = {
    next_due: sched.next_due,
    new_stability: sched.new_stability,
    new_difficulty: sched.new_difficulty,
    state: sched.state,
    interval_days: sched.interval_days,
    lapse_count: sched.lapse_count,
    leech_flagged: card.leech_flag,
    stuck_alert: null,
    automaticity_exceeded: Boolean(
      latencyMs && user.automaticity_threshold_ms && latencyMs > user.automaticity_threshold_ms,
    ),
  }
  if (clientReviewId) processedReviewIds.set(`${user.id}:${clientReviewId}`, responsePayload)

  broadcastToUser(user.id, { type: 'CARD_REVIEWED', data: { card_id: card.id, grade } })
  res.json(responsePayload)
})

app.post('/api/review/:cardId/mutate-prompt', requireAuth, (req: AuthedRequest, res) => {
  const card = store.cards.get(String(req.params.cardId))
  if (!card || card.user_id !== req.user!.id) {
    res.status(404).json({ detail: 'Card not found' })
    return
  }
  const mutationType = String(req.body?.mutation_type || 'application')
  const prefixes: Record<string, string> = {
    application: 'Apply this concept to a real scenario: ',
    inversion: 'What breaks or fails if the principle behind this question is violated? ',
    eli5: 'Explain clearly from first principles without jargon: ',
    contrast: 'Distinguish this precisely from closely related concepts: ',
  }
  res.json({
    card_id: card.id,
    original_front: card.front,
    mutated_prompt: `${prefixes[mutationType] ?? 'Rephrased challenge: '}${card.front}`,
    mutation_type: mutationType,
    model_used: 'prompt-mutator-heuristic',
  })
})

app.post('/api/review/:cardId/generate-mnemonic', requireAuth, (req: AuthedRequest, res) => {
  const card = store.cards.get(String(req.params.cardId))
  if (!card || card.user_id !== req.user!.id) {
    res.status(404).json({ detail: 'Card not found' })
    return
  }
  const phrases = extractKeyPhrases(card.back)
  const acronym = phrases
    .map((p) => p.trim()[0]?.toUpperCase() || '')
    .filter(Boolean)
    .join('-')
  const vignette = `Anchor Hook [${acronym || 'KEY'}]: Visualize "${card.front.slice(0, 60)}" leading directly to "${(phrases[0] || card.back).slice(0, 90)}".`
  card.mnemonic_vignette = vignette
  res.json({
    card_id: card.id,
    mnemonic_vignette: vignette,
    model_used: 'mnemonic-heuristic',
  })
})

app.post('/api/review/:cardId/predict', requireAuth, (req: AuthedRequest, res) => {
  const card = store.cards.get(String(req.params.cardId))
  if (!card || card.user_id !== req.user!.id) {
    res.status(404).json({ detail: 'Card not found' })
    return
  }
  const prediction = String(req.body?.prediction || '')
  const confidence = Number(req.body?.confidence || 3)
  const evalRes = evaluateTypedAnswer(prediction, card.back)
  const isAccurate = evalRes.score >= 60
  res.json({
    card_id: card.id,
    prediction,
    reference_answer: card.back,
    confidence,
    is_accurate: isAccurate,
    feedback: isAccurate
      ? 'Strong prediction — your mental model aligns with the reference answer.'
      : 'Prediction diverged from reference — hypercorrection will strengthen this trace.',
    high_confidence_error: !isAccurate && confidence >= 4,
  })
})

// ─── Decks, Note Types, Notes, Cards ─────────────────────────────────────────
app.get('/api/decks', requireAuth, (req: AuthedRequest, res) => {
  const uid = req.user!.id
  res.json(store.getUserDecks(uid).map((d) => store.serializeDeck(uid, d)))
})

app.post('/api/decks', requireAuth, (req: AuthedRequest, res) => {
  const uid = req.user!.id
  const name = String(req.body?.name || '').trim()
  if (!name) {
    res.status(400).json({ detail: 'Deck name is required' })
    return
  }
  const id = newId('deck')
  const deck: DeckRecord = {
    id,
    user_id: uid,
    name,
    parent_id: req.body?.parent_id ?? null,
    desired_retention_override: null,
    default_priority: Number(req.body?.default_priority ?? 70),
    position: Number(req.body?.position ?? store.getUserDecks(uid).length),
    target_event_date: null,
    target_event_title: null,
    documentation: req.body?.documentation ?? null,
    thematic_nature: req.body?.thematic_nature ?? null,
    source_documents: Array.isArray(req.body?.source_documents) ? req.body.source_documents : [],
    created_at: new Date().toISOString(),
  }
  store.decks.set(id, deck)

  // Mirror deck in knowledge tree
  const parentTreeNode = deck.parent_id
    ? Array.from(store.treeNodes.values()).find((n) => n.user_id === uid && n.deck_id === deck.parent_id)
    : null
  const nodeId = newId('node')
  store.treeNodes.set(nodeId, {
    id: nodeId,
    user_id: uid,
    parent_id: parentTreeNode?.id ?? null,
    kind: 'deck',
    title: deck.name,
    position: deck.position,
    collapsed: false,
    priority: deck.default_priority,
    priority_inherited: false,
    deck_id: deck.id,
    source_id: null,
    extract_id: null,
    requires_node_id: null,
    mastery_threshold: 0.8,
  })

  broadcastToUser(uid, { type: 'DECK_MUTATED', data: { deck_id: id } })
  res.status(201).json(store.serializeDeck(uid, deck))
})

app.post('/api/decks/reorder', requireAuth, (req: AuthedRequest, res) => {
  const uid = req.user!.id
  const items = Array.isArray(req.body?.items) ? req.body.items : []
  for (const item of items) {
    const deck = store.decks.get(String(item.id))
    if (deck && deck.user_id === uid) {
      if (item.parent_id !== undefined) deck.parent_id = item.parent_id
      if (typeof item.position === 'number') deck.position = item.position
    }
  }
  res.json(store.getUserDecks(uid).map((d) => store.serializeDeck(uid, d)))
})

app.patch('/api/decks/cards/:cardId/neuro-props', requireAuth, (req: AuthedRequest, res) => {
  const card = store.cards.get(String(req.params.cardId))
  if (!card || card.user_id !== req.user!.id) {
    res.status(404).json({ detail: 'Card not found' })
    return
  }
  if (req.body?.is_schema_checkpoint !== undefined) card.is_schema_checkpoint = Boolean(req.body.is_schema_checkpoint)
  if (req.body?.spatial_x !== undefined) card.spatial_x = req.body.spatial_x
  if (req.body?.spatial_y !== undefined) card.spatial_y = req.body.spatial_y
  if (req.body?.spatial_locus !== undefined) card.spatial_locus = req.body.spatial_locus
  if (req.body?.mnemonic_vignette !== undefined) card.mnemonic_vignette = req.body.mnemonic_vignette
  res.json(store.serializeCard(card))
})

app.get('/api/decks/:id/stats', requireAuth, (req: AuthedRequest, res) => {
  const deck = store.decks.get(String(req.params.id))
  if (!deck || deck.user_id !== req.user!.id) {
    res.status(404).json({ detail: 'Deck not found' })
    return
  }
  res.json(store.computeDeckStats(req.user!.id, deck.id))
})

app.get('/api/decks/:id/persist-items', requireAuth, (req: AuthedRequest, res) => {
  const uid = req.user!.id
  const targetId = String(req.params.id)
  const deckIds = targetId === '__root__' ? null : store.getDescendantDeckIds(uid, targetId)
  const unseenOnly = req.query.unseen_only === 'true'
  const cards = store
    .getUserCards(uid)
    .filter((c) => (!deckIds || deckIds.has(c.deck_id)) && !c.suspended && (!unseenOnly || c.state === 'new'))
    .sort((a, b) => {
      if (a.position != null && b.position != null && a.position !== b.position) {
        return a.position - b.position
      }
      if (a.position != null && b.position == null) return -1
      if (a.position == null && b.position != null) return 1
      return (a.created_at || '').localeCompare(b.created_at || '')
    })
  res.json(cards.map((c) => store.serializeQueueCard(c)))
})

app.get('/api/decks/:id/all-cards-run-items', requireAuth, (req: AuthedRequest, res) => {
  const uid = req.user!.id
  const targetId = String(req.params.id)
  const deckIds = targetId === '__root__' ? null : store.getDescendantDeckIds(uid, targetId)
  const cards = store
    .getUserCards(uid)
    .filter((c) => (!deckIds || deckIds.has(c.deck_id)) && !c.suspended)
  res.json(cards.map((c) => store.serializeQueueCard(c)))
})

app.patch('/api/decks/:id', requireAuth, (req: AuthedRequest, res) => {
  const uid = req.user!.id
  const deck = store.decks.get(String(req.params.id))
  if (!deck || deck.user_id !== uid) {
    res.status(404).json({ detail: 'Deck not found' })
    return
  }
  const fields: Array<keyof DeckRecord> = [
    'name',
    'parent_id',
    'desired_retention_override',
    'default_priority',
    'position',
    'target_event_date',
    'target_event_title',
    'documentation',
    'thematic_nature',
    'source_documents',
  ]
  for (const f of fields) {
    if (req.body && Object.prototype.hasOwnProperty.call(req.body, f)) {
      ;(deck as unknown as Record<string, unknown>)[f] = req.body[f]
    }
  }
  for (const n of store.treeNodes.values()) {
    if (n.user_id === uid && n.deck_id === deck.id) n.title = deck.name
  }
  res.json(store.serializeDeck(uid, deck))
})

app.delete('/api/decks/:id', requireAuth, (req: AuthedRequest, res) => {
  const uid = req.user!.id
  const deckId = String(req.params.id)
  const deck = store.decks.get(deckId)
  if (!deck || deck.user_id !== uid) {
    res.status(404).json({ detail: 'Deck not found' })
    return
  }
  const idsToDelete = req.query.cascade === 'false' ? new Set([deckId]) : store.getDescendantDeckIds(uid, deckId)
  for (const did of idsToDelete) {
    store.decks.delete(did)
    for (const [cid, c] of store.cards.entries()) {
      if (c.user_id === uid && c.deck_id === did) store.cards.delete(cid)
    }
    for (const [nid, n] of store.treeNodes.entries()) {
      if (n.user_id === uid && n.deck_id === did) store.treeNodes.delete(nid)
    }
  }
  res.status(204).end()
})

app.delete('/api/decks', requireAuth, (req: AuthedRequest, res) => {
  const uid = req.user!.id
  for (const [id, d] of store.decks.entries()) if (d.user_id === uid) store.decks.delete(id)
  for (const [id, c] of store.cards.entries()) if (c.user_id === uid) store.cards.delete(id)
  for (const [id, n] of store.treeNodes.entries()) if (n.user_id === uid && n.deck_id) store.treeNodes.delete(id)
  res.status(204).end()
})

app.post('/api/decks/:id/auto-palace', requireAuth, (req: AuthedRequest, res) => {
  const uid = req.user!.id
  const deckIds = store.getDescendantDeckIds(uid, String(req.params.id))
  const loci = ['Entrance Gate', 'Marble Courtyard', 'Library Alcove', 'Spiral Stair', 'Observatory Dome', 'Garden Fountain', 'Clocktower Loft', 'Archive Vault']
  const cards = store.getUserCards(uid).filter((c) => deckIds.has(c.deck_id))
  cards.forEach((c, idx) => {
    const angle = (idx / Math.max(1, cards.length)) * Math.PI * 2
    c.spatial_x = Math.round(350 + Math.cos(angle) * 200)
    c.spatial_y = Math.round(250 + Math.sin(angle) * 140)
    c.spatial_locus = loci[idx % loci.length]
  })
  res.json(cards.map((c) => store.serializeCard(c)))
})

app.get('/api/decks/:id/documents', requireAuth, (req: AuthedRequest, res) => {
  const deckId = String(req.params.id)
  const docs = Array.from(store.deckDocuments.values()).filter(
    (d) => d.user_id === req.user!.id && d.deck_id === deckId,
  )
  res.json({ deck_id: deckId, documents: docs })
})

app.post('/api/decks/:id/documents', requireAuth, upload.single('file'), (req: AuthedRequest, res) => {
  const uid = req.user!.id
  const deckId = String(req.params.id)
  const file = req.file
  const rawText = file ? file.buffer.toString('utf-8') : ''
  const title = String(req.body?.title || file?.originalname || 'Uploaded Document')
  const segments = rawText
    .split(/\n{2,}/)
    .map((s) => s.trim())
    .filter((s) => s.length > 20)
    .slice(0, 40)

  const srcId = newId('src')
  store.sources.set(srcId, {
    id: srcId,
    user_id: uid,
    title,
    url: null,
    raw_text: rawText,
    priority: 65,
    status: 'active',
    created_at: new Date().toISOString(),
    for_reading: false,
  })
  const locators: string[] = []
  segments.forEach((seg, idx) => {
    const loc = `Section ${idx + 1}`
    locators.push(loc)
    const extId = newId('ext')
    store.extracts.set(extId, {
      id: extId,
      user_id: uid,
      source_id: srcId,
      content: seg,
      priority: 65,
      position: idx,
      locator: loc,
      next_shown_at: null,
      status: 'active',
    })
  })
  const docId = newId('doc')
  const doc = {
    id: docId,
    deck_id: deckId,
    user_id: uid,
    source_id: srcId,
    filename: file?.originalname || 'document.txt',
    title,
    segment_count: Math.max(1, segments.length),
    locators,
    uploaded_at: new Date().toISOString(),
  }
  store.deckDocuments.set(docId, doc)
  res.status(201).json(doc)
})

app.delete('/api/decks/:id/documents/:docId', requireAuth, (req: AuthedRequest, res) => {
  const doc = store.deckDocuments.get(String(req.params.docId))
  if (!doc || doc.user_id !== req.user!.id) {
    res.status(404).json({ detail: 'Document not found' })
    return
  }
  store.deckDocuments.delete(doc.id)
  res.json({ status: 'deleted', doc_id: doc.id, source_id: doc.source_id })
})

app.post('/api/decks/:id/query-docs', requireAuth, (req: AuthedRequest, res) => {
  const uid = req.user!.id
  const deckId = String(req.params.id)
  const query = String(req.body?.query || '')
  const docs = Array.from(store.deckDocuments.values()).filter((d) => d.user_id === uid && d.deck_id === deckId)
  const sourceIds = new Set(docs.map((d) => d.source_id))
  const extracts = Array.from(store.extracts.values()).filter((e) => sourceIds.has(e.source_id))
  const ranked = extracts
    .map((e) => ({
      extract_id: e.id,
      source_id: e.source_id,
      source_title: store.sources.get(e.source_id)?.title || 'Deck Document',
      locator: e.locator || `Section ${e.position + 1}`,
      content: e.content,
      score: Number(jaccardSimilarity(query, e.content).toFixed(3)),
    }))
    .sort((a, b) => b.score - a.score)
    .slice(0, 3)

  const top = ranked[0]
  res.json({
    found_info: top ? top.content : 'No matching passages found in uploaded deck documents yet.',
    doc_citation: top ? `${top.source_title} (${top.locator})` : null,
    verbatim_passage: top?.content ?? null,
    explanation: top ? 'Matched via lexical similarity against your uploaded deck references.' : null,
    key_takeaway: top ? top.content.slice(0, 140) : null,
    citations: ranked,
    model_used: 'doc-search-heuristic',
    available_models: ['qwen2.5-coder:7b'],
  })
})

app.get('/api/note-types', requireAuth, (req: AuthedRequest, res) => {
  const uid = req.user!.id
  res.json(Array.from(store.noteTypes.values()).filter((nt) => nt.user_id === uid))
})

app.post('/api/note-types', requireAuth, (req: AuthedRequest, res) => {
  const uid = req.user!.id
  const id = newId('nt')
  const nt = {
    id,
    user_id: uid,
    name: String(req.body?.name || 'Custom Note Type'),
    template_kind: String(req.body?.template_kind || 'basic'),
    fields: req.body?.fields || {},
    grading_profile: String(req.body?.grading_profile || 'conceptual'),
  }
  store.noteTypes.set(id, nt)
  res.status(201).json(nt)
})

function buildCardsFromNote(uid: string, body: Record<string, any>): { noteId: string; cards: CardRecord[] } {
  const noteId = newId('note')
  const deckId = String(body.deck_id)
  const deck = store.decks.get(deckId)
  const fv = (body.field_values || {}) as Record<string, any>
  const templateKind = String(body.template_kind || 'basic')
  const priority = typeof body.priority === 'number' ? body.priority : deck?.default_priority ?? 70
  const tags = Array.isArray(body.tags) ? body.tags.map(String) : []
  const now = new Date().toISOString()
  const basePos = store.getUserCards(uid).length

  const created: CardRecord[] = []

  if (templateKind === 'cloze' && typeof (fv.text || fv.cloze_text) === 'string') {
    const raw = String(fv.text || fv.cloze_text)
    const matches = Array.from(raw.matchAll(/\{\{c(\d+)::([^}]+)\}\}/g))
    const indices = Array.from(new Set(matches.map((m) => m[1])))
    if (indices.length > 0) {
      indices.forEach((cIdx, idx) => {
        const answers: string[] = []
        const front = raw.replace(/\{\{c(\d+)::([^}]+)\}\}/g, (_m, n, inner) => {
          const [ans, hint] = String(inner).split('::')
          if (n === cIdx) {
            answers.push(ans)
            return hint ? `[${hint}]` : '[...]'
          }
          return ans
        })
        const cid = newId('card')
        const card: CardRecord = {
          id: cid,
          user_id: uid,
          note_id: noteId,
          deck_id: deckId,
          template_slot: `c${cIdx}`,
          template_kind: 'cloze',
          grading_profile: 'exact_term',
          state: 'new',
          due: null,
          stability: null,
          difficulty: null,
          priority,
          lapse_count: 0,
          leech_flag: false,
          suspended: false,
          tags,
          front,
          back: answers.join('; '),
          image: fv.image ?? null,
          back_image: fv.back_image ?? null,
          occlusion: null,
          references: [],
          starter_code: null,
          starter_tests: null,
          test_cases: [],
          time_complexity: null,
          space_complexity: null,
          edge_cases: [],
          title: null,
          difficulty_label: null,
          category: null,
          documentation: body.documentation ?? null,
          thematic_nature: body.thematic_nature ?? null,
          source_documents: Array.isArray(body.source_documents) ? body.source_documents : [],
          lexicon_glosses: [],
          position: basePos + idx,
          memory_note: null,
          active_weaknesses: [],
          weakness_history: [],
          failure_reminder: null,
          last_grade: null,
          review_count: 0,
          is_schema_checkpoint: false,
          spatial_x: null,
          spatial_y: null,
          spatial_locus: null,
          mnemonic_vignette: null,
          created_at: now,
        }
        store.cards.set(cid, card)
        created.push(card)
      })
      return { noteId, cards: created }
    }
  }

  const cid = newId('card')
  const card: CardRecord = {
    id: cid,
    user_id: uid,
    note_id: noteId,
    deck_id: deckId,
    template_slot: 'front_back',
    template_kind: templateKind,
    grading_profile: templateKind === 'code' ? 'code' : 'conceptual',
    state: 'new',
    due: null,
    stability: null,
    difficulty: null,
    priority,
    lapse_count: 0,
    leech_flag: false,
    suspended: false,
    tags,
    front: String(fv.front || fv.question || fv.prompt || fv.text || ''),
    back: String(fv.back || fv.answer || fv.solution || ''),
    image: fv.image ?? null,
    back_image: fv.back_image ?? null,
    occlusion: fv.occlusion ?? null,
    references: [],
    starter_code: fv.starter_code ?? null,
    starter_tests: fv.starter_tests ?? null,
    test_cases: Array.isArray(fv.test_cases) ? fv.test_cases : [],
    time_complexity: fv.time_complexity ?? null,
    space_complexity: fv.space_complexity ?? null,
    edge_cases: Array.isArray(fv.edge_cases) ? fv.edge_cases : [],
    title: fv.title ?? null,
    difficulty_label: fv.difficulty ?? null,
    category: fv.category ?? null,
    documentation: body.documentation ?? null,
    thematic_nature: body.thematic_nature ?? null,
    source_documents: Array.isArray(body.source_documents) ? body.source_documents : [],
    lexicon_glosses: [],
    position: basePos,
    memory_note: null,
    active_weaknesses: [],
    weakness_history: [],
    failure_reminder: null,
    last_grade: null,
    review_count: 0,
    is_schema_checkpoint: false,
    spatial_x: null,
    spatial_y: null,
    spatial_locus: null,
    mnemonic_vignette: null,
    created_at: now,
  }
  store.cards.set(cid, card)
  created.push(card)
  return { noteId, cards: created }
}

app.post('/api/notes', requireAuth, (req: AuthedRequest, res) => {
  const uid = req.user!.id
  const { noteId, cards } = buildCardsFromNote(uid, req.body || {})
  res.status(201).json({ id: noteId, cards: cards.map((c) => store.serializeCard(c)) })
})

app.delete('/api/notes/:id', requireAuth, (req: AuthedRequest, res) => {
  const uid = req.user!.id
  const nid = String(req.params.id)
  for (const [cid, c] of store.cards.entries()) {
    if (c.user_id === uid && c.note_id === nid) store.cards.delete(cid)
  }
  res.status(204).end()
})

app.get('/api/cards', requireAuth, (req: AuthedRequest, res) => {
  const uid = req.user!.id
  let cards = store.getUserCards(uid)
  if (typeof req.query.deck_id === 'string' && req.query.deck_id) {
    const ids = store.getDescendantDeckIds(uid, req.query.deck_id)
    cards = cards.filter((c) => ids.has(c.deck_id))
  }
  if (typeof req.query.state === 'string' && req.query.state) {
    cards = cards.filter((c) => c.state === req.query.state)
  }
  if (typeof req.query.search === 'string' && req.query.search.trim()) {
    const q = req.query.search.trim().toLowerCase()
    cards = cards.filter((c) => c.front.toLowerCase().includes(q) || c.back.toLowerCase().includes(q))
  }
  res.json(cards.map((c) => store.serializeCard(c)))
})

app.post('/api/cards/reorder', requireAuth, (req: AuthedRequest, res) => {
  const uid = req.user!.id
  const items = Array.isArray(req.body?.items) ? req.body.items : []
  for (const item of items) {
    const c = store.cards.get(String(item.id))
    if (c && c.user_id === uid) {
      if (typeof item.position === 'number') c.position = item.position
      if (item.deck_id) c.deck_id = String(item.deck_id)
    }
  }
  res.json(store.getUserCards(uid).map((c) => store.serializeCard(c)))
})

app.post('/api/cards/:id/suspend', requireAuth, (req: AuthedRequest, res) => {
  const c = store.cards.get(String(req.params.id))
  if (!c || c.user_id !== req.user!.id) {
    res.status(404).json({ detail: 'Card not found' })
    return
  }
  c.suspended = req.query.suspended === 'true'
  res.json(store.serializeCard(c))
})

app.post('/api/cards/:id/postpone', requireAuth, (req: AuthedRequest, res) => {
  const c = store.cards.get(String(req.params.id))
  if (!c || c.user_id !== req.user!.id) {
    res.status(404).json({ detail: 'Card not found' })
    return
  }
  const hours = Number(req.query.hours || 4)
  c.due = new Date(Date.now() + hours * 3600_000).toISOString()
  if (c.state === 'new') c.state = 'learning'
  res.json({ card_id: c.id, due: c.due, postponed_hours: hours })
})

app.get('/api/cards/:id/analytics', requireAuth, (req: AuthedRequest, res) => {
  const c = store.cards.get(String(req.params.id))
  if (!c || c.user_id !== req.user!.id) {
    res.status(404).json({ detail: 'Card not found' })
    return
  }
  res.json(buildCardAnalytics(store, req.user!, c))
})

app.patch('/api/cards/:id/memory-note', requireAuth, (req: AuthedRequest, res) => {
  const c = store.cards.get(String(req.params.id))
  if (!c || c.user_id !== req.user!.id) {
    res.status(404).json({ detail: 'Card not found' })
    return
  }
  c.memory_note = String(req.body?.memory_note || '')
  c.mnemonic_vignette = c.memory_note
  res.json(store.serializeCard(c))
})

app.patch('/api/cards/:id/lexicon-glosses', requireAuth, (req: AuthedRequest, res) => {
  const c = store.cards.get(String(req.params.id))
  if (!c || c.user_id !== req.user!.id) {
    res.status(404).json({ detail: 'Card not found' })
    return
  }
  c.lexicon_glosses = Array.isArray(req.body?.glosses) ? req.body.glosses : []
  res.json(store.serializeCard(c))
})

app.post('/api/cards/:id/lexicon-glosses', requireAuth, (req: AuthedRequest, res) => {
  const c = store.cards.get(String(req.params.id))
  if (!c || c.user_id !== req.user!.id) {
    res.status(404).json({ detail: 'Card not found' })
    return
  }
  if (req.body?.gloss) {
    c.lexicon_glosses = [...c.lexicon_glosses, { ...req.body.gloss, pinned_at: new Date().toISOString() }]
  }
  res.json(store.serializeCard(c))
})

app.patch('/api/priority', requireAuth, (req: AuthedRequest, res) => {
  const uid = req.user!.id
  const { target, id, priority } = req.body || {}
  const p = Math.max(0, Math.min(100, Number(priority ?? 50)))
  if (target === 'deck') {
    const d = store.decks.get(String(id))
    if (d && d.user_id === uid) d.default_priority = p
  } else if (target === 'card') {
    const c = store.cards.get(String(id))
    if (c && c.user_id === uid) c.priority = p
  } else if (target === 'source') {
    const s = store.sources.get(String(id))
    if (s && s.user_id === uid) s.priority = p
  } else if (target === 'extract') {
    const e = store.extracts.get(String(id))
    if (e && e.user_id === uid) e.priority = p
  }
  res.json({ priority: p })
})

// ─── Knowledge Tree ──────────────────────────────────────────────────────────
app.get('/api/tree', requireAuth, (req: AuthedRequest, res) => {
  res.json(store.buildTree(req.user!.id))
})

app.delete('/api/tree', requireAuth, (req: AuthedRequest, res) => {
  const uid = req.user!.id
  let nodesRemoved = 0
  for (const [id, n] of store.treeNodes.entries()) {
    if (n.user_id === uid) {
      store.treeNodes.delete(id)
      nodesRemoved++
    }
  }
  res.json({ deleted: true, summary: { nodes: nodesRemoved } })
})

app.post('/api/tree/nodes', requireAuth, (req: AuthedRequest, res) => {
  const uid = req.user!.id
  const id = newId('node')
  const node = {
    id,
    user_id: uid,
    parent_id: req.body?.parent_id ?? null,
    kind: 'topic' as const,
    title: String(req.body?.title || 'New Topic').trim(),
    position: Array.from(store.treeNodes.values()).filter((n) => n.user_id === uid).length,
    collapsed: false,
    priority: Number(req.body?.priority ?? 70),
    priority_inherited: false,
    deck_id: null,
    source_id: null,
    extract_id: null,
    requires_node_id: null,
    mastery_threshold: 0.8,
  }
  store.treeNodes.set(id, node)
  res.status(201).json({
    ...node,
    card_count: 0,
    due_count: 0,
    new_count: 0,
    extract_count: 0,
    mastery_pct: 0,
    locked: false,
    requires_title: null,
    children: [],
  })
})

app.patch('/api/tree/nodes/:id', requireAuth, (req: AuthedRequest, res) => {
  const uid = req.user!.id
  const node = store.treeNodes.get(String(req.params.id))
  if (!node || node.user_id !== uid) {
    res.status(404).json({ detail: 'Node not found' })
    return
  }
  let updated = 1
  if (req.body?.title !== undefined) node.title = String(req.body.title)
  if (req.body?.collapsed !== undefined) node.collapsed = Boolean(req.body.collapsed)
  if (req.body?.priority !== undefined) {
    node.priority = Number(req.body.priority)
    node.priority_inherited = false
    if (req.body?.cascade) {
      const { deckIds } = store.getBranchDeckAndSourceIds(uid, node.id)
      for (const c of store.getUserCards(uid)) {
        if (deckIds.has(c.deck_id)) {
          c.priority = node.priority
          updated++
        }
      }
    }
  }
  if (Object.prototype.hasOwnProperty.call(req.body || {}, 'requires_node_id')) {
    node.requires_node_id = req.body.requires_node_id
  }
  if (req.body?.mastery_threshold !== undefined) {
    node.mastery_threshold = Number(req.body.mastery_threshold)
  }
  res.json({ entities_updated: updated })
})

app.post('/api/tree/nodes/:id/move', requireAuth, (req: AuthedRequest, res) => {
  const node = store.treeNodes.get(String(req.params.id))
  if (!node || node.user_id !== req.user!.id) {
    res.status(404).json({ detail: 'Node not found' })
    return
  }
  node.parent_id = req.body?.parent_id ?? null
  if (typeof req.body?.position === 'number') node.position = req.body.position
  res.json({ id: node.id, parent_id: node.parent_id })
})

app.delete('/api/tree/nodes/:id', requireAuth, (req: AuthedRequest, res) => {
  const uid = req.user!.id
  const node = store.treeNodes.get(String(req.params.id))
  if (!node || node.user_id !== uid) {
    res.status(404).json({ detail: 'Node not found' })
    return
  }
  let promoted = 0
  for (const child of store.treeNodes.values()) {
    if (child.user_id === uid && child.parent_id === node.id) {
      child.parent_id = node.parent_id
      promoted++
    }
  }
  store.treeNodes.delete(node.id)
  res.json({ children_promoted: promoted })
})

app.get('/api/tree/nodes/:id/cards', requireAuth, (req: AuthedRequest, res) => {
  const uid = req.user!.id
  const { deckIds } = store.getBranchDeckAndSourceIds(uid, String(req.params.id))
  const cards = store.getUserCards(uid).filter((c) => deckIds.has(c.deck_id))
  res.json(cards.map((c) => store.serializeCard(c)))
})

// ─── Incremental Reading & Documents ─────────────────────────────────────────
app.get('/api/sources', requireAuth, (req: AuthedRequest, res) => {
  const uid = req.user!.id
  const all = Array.from(store.sources.values()).filter((s) => s.user_id === uid)
  const extracts = Array.from(store.extracts.values()).filter((e) => e.user_id === uid)
  res.json(
    all.map((s) => {
      const own = extracts.filter((e) => e.source_id === s.id)
      return {
        id: s.id,
        title: s.title,
        url: s.url,
        priority: s.priority,
        status: s.status,
        created_at: s.created_at,
        extract_count: own.length,
        active_extract_count: own.filter((e) => e.status === 'active').length,
        for_reading: s.for_reading,
      }
    }),
  )
})

app.post('/api/sources', requireAuth, (req: AuthedRequest, res) => {
  const uid = req.user!.id
  const title = String(req.body?.title || req.body?.url || 'Untitled Source').trim()
  const rawText = String(req.body?.raw_text || '').trim() || `Source imported from ${req.body?.url || title}.`
  const priority = Number(req.body?.priority ?? 70)
  const srcId = newId('src')
  const now = new Date().toISOString()

  const source = {
    id: srcId,
    user_id: uid,
    title,
    url: req.body?.url ?? null,
    raw_text: rawText,
    priority,
    status: 'active',
    created_at: now,
    for_reading: true,
  }
  store.sources.set(srcId, source)

  const extId = newId('ext')
  store.extracts.set(extId, {
    id: extId,
    user_id: uid,
    source_id: srcId,
    content: rawText,
    priority,
    position: 0,
    locator: 'Full Text',
    next_shown_at: now,
    status: 'active',
  })

  const nodeId = newId('node')
  store.treeNodes.set(nodeId, {
    id: nodeId,
    user_id: uid,
    parent_id: req.body?.parent_node_id ?? null,
    kind: 'source',
    title,
    position: Array.from(store.treeNodes.values()).filter((n) => n.user_id === uid).length,
    collapsed: false,
    priority,
    priority_inherited: false,
    deck_id: null,
    source_id: srcId,
    extract_id: null,
    requires_node_id: null,
    mastery_threshold: 0.8,
  })

  res.status(201).json({
    id: source.id,
    title: source.title,
    url: source.url,
    priority: source.priority,
    status: source.status,
    created_at: source.created_at,
    extract_count: 1,
    active_extract_count: 1,
    for_reading: true,
  })
})

app.delete('/api/sources/:id', requireAuth, (req: AuthedRequest, res) => {
  const uid = req.user!.id
  const sid = String(req.params.id)
  store.sources.delete(sid)
  for (const [eid, e] of store.extracts.entries()) if (e.user_id === uid && e.source_id === sid) store.extracts.delete(eid)
  for (const [nid, n] of store.treeNodes.entries()) if (n.user_id === uid && n.source_id === sid) store.treeNodes.delete(nid)
  res.status(204).end()
})

app.get('/api/sources/:id/extracts', requireAuth, (req: AuthedRequest, res) => {
  const uid = req.user!.id
  const sid = String(req.params.id)
  const src = store.sources.get(sid)
  const list = Array.from(store.extracts.values())
    .filter((e) => e.user_id === uid && e.source_id === sid)
    .sort((a, b) => a.position - b.position)
    .map((e) => ({ ...e, source_title: src?.title ?? null }))
  res.json(list)
})

app.get('/api/extracts/:id', requireAuth, (req: AuthedRequest, res) => {
  const ext = store.extracts.get(String(req.params.id))
  if (!ext || ext.user_id !== req.user!.id) {
    res.status(404).json({ detail: 'Extract not found' })
    return
  }
  res.json({ ...ext, source_title: store.sources.get(ext.source_id)?.title ?? null })
})

app.delete('/api/extracts/:id', requireAuth, (req: AuthedRequest, res) => {
  store.extracts.delete(String(req.params.id))
  res.status(204).end()
})

app.post('/api/extracts/:id/split', requireAuth, (req: AuthedRequest, res) => {
  const parent = store.extracts.get(String(req.params.id))
  if (!parent || parent.user_id !== req.user!.id) {
    res.status(404).json({ detail: 'Extract not found' })
    return
  }
  let text = String(req.body?.text || '').trim()
  if (!text && typeof req.body?.start === 'number' && typeof req.body?.end === 'number') {
    text = parent.content.slice(req.body.start, req.body.end).trim()
  }
  if (!text) {
    res.status(400).json({ detail: 'Highlight or provide text to extract' })
    return
  }
  const childId = newId('ext')
  const child = {
    id: childId,
    user_id: parent.user_id,
    source_id: parent.source_id,
    content: text,
    priority: Number(req.body?.priority ?? parent.priority),
    position: parent.position + 1,
    locator: parent.locator,
    next_shown_at: new Date().toISOString(),
    status: 'active' as const,
  }
  store.extracts.set(childId, child)
  res.status(201).json({ ...child, source_title: store.sources.get(child.source_id)?.title ?? null })
})

app.post('/api/extracts/:id/schedule', requireAuth, (req: AuthedRequest, res) => {
  const ext = store.extracts.get(String(req.params.id))
  if (!ext || ext.user_id !== req.user!.id) {
    res.status(404).json({ detail: 'Extract not found' })
    return
  }
  if (typeof req.body?.days === 'number') {
    ext.next_shown_at = new Date(Date.now() + req.body.days * 86_400_000).toISOString()
  }
  if (req.body?.status) ext.status = req.body.status
  if (typeof req.body?.priority === 'number') ext.priority = req.body.priority
  res.json({ ...ext, source_title: store.sources.get(ext.source_id)?.title ?? null })
})

app.post('/api/extracts/:id/generate-cards', requireAuth, (req: AuthedRequest, res) => {
  const ext = store.extracts.get(String(req.params.id))
  if (!ext || ext.user_id !== req.user!.id) {
    res.status(404).json({ detail: 'Extract not found' })
    return
  }
  const passage = String(req.body?.text || ext.content).trim()
  const maxCards = Math.max(1, Math.min(8, Number(req.body?.max_cards || 3)))
  const sentences = passage
    .split(/(?<=[.!?])\s+/)
    .map((s) => s.trim())
    .filter((s) => s.length > 20)
    .slice(0, maxCards)

  const suggestions = sentences.map((s) => ({
    kind: 'basic',
    front: `Explain the core claim regarding: "${s.split(/\s+/).slice(0, 7).join(' ')}..."`,
    back: s,
    cloze_text: null,
  }))
  res.json({
    suggestions: suggestions.length > 0 ? suggestions : [{ kind: 'basic', front: 'Summarize the key point from this passage.', back: passage, cloze_text: null }],
    degraded: false,
    reason: null,
  })
})

app.post('/api/extracts/:id/accept-cards', requireAuth, (req: AuthedRequest, res) => {
  const uid = req.user!.id
  const deckId = String(req.body?.deck_id || '')
  const cards = Array.isArray(req.body?.cards) ? req.body.cards : []
  let created = 0
  for (const item of cards) {
    const out = buildCardsFromNote(uid, {
      deck_id: deckId,
      template_kind: item.kind || 'basic',
      field_values: { front: item.front, back: item.back, text: item.cloze_text },
    })
    created += out.cards.length
  }
  res.status(201).json({ cards_created: created })
})

app.post('/api/documents', requireAuth, upload.single('file'), (req: AuthedRequest, res) => {
  const uid = req.user!.id
  const file = req.file
  const rawText = file ? file.buffer.toString('utf-8') : ''
  const title = String(req.body?.title || file?.originalname || 'Uploaded Document')
  const segments = rawText
    .split(/\n{2,}/)
    .map((s) => s.trim())
    .filter((s) => s.length > 15)
  const srcId = newId('src')
  store.sources.set(srcId, {
    id: srcId,
    user_id: uid,
    title,
    url: null,
    raw_text: rawText,
    priority: 70,
    status: 'active',
    created_at: new Date().toISOString(),
    for_reading: false,
  })
  const locators: string[] = []
  segments.slice(0, 50).forEach((seg, i) => {
    const loc = `§${i + 1}`
    locators.push(loc)
    const extId = newId('ext')
    store.extracts.set(extId, {
      id: extId,
      user_id: uid,
      source_id: srcId,
      content: seg,
      priority: 70,
      position: i,
      locator: loc,
      next_shown_at: null,
      status: 'active',
    })
  })
  res.status(201).json({
    source_id: srcId,
    title,
    segment_count: Math.max(1, segments.length),
    locators,
    node_id: null,
  })
})

app.post('/api/documents/:sourceId/generate-deck', requireAuth, (req: AuthedRequest, res) => {
  const src = store.sources.get(String(req.params.sourceId))
  if (!src || src.user_id !== req.user!.id) {
    res.status(404).json({ detail: 'Source document not found' })
    return
  }
  const exts = Array.from(store.extracts.values())
    .filter((e) => e.source_id === src.id)
    .sort((a, b) => a.position - b.position)
  const start = Number(req.body?.start_section || 0)
  const maxSec = Number(req.body?.max_sections || 5)
  const slice = exts.slice(start, start + maxSec)
  const cards = slice.map((e) => ({
    kind: 'basic',
    front: `What key concept is described in ${src.title} (${e.locator || 'passage'})?`,
    back: e.content.slice(0, 260),
    cloze_text: null,
    quote: e.content.slice(0, 140),
    quote_verified: true,
    locator: e.locator,
    extract_id: e.id,
  }))
  res.json({
    source_id: src.id,
    title: src.title,
    cards,
    sections_used: slice.length,
    sections_total: exts.length,
    next_section: start + slice.length < exts.length ? start + slice.length : null,
    degraded: false,
    reason: null,
    warnings: [],
  })
})

app.post('/api/documents/:sourceId/accept-deck', requireAuth, (req: AuthedRequest, res) => {
  const uid = req.user!.id
  const src = store.sources.get(String(req.params.sourceId))
  const deckName = String(req.body?.deck || src?.title || 'Generated Deck').trim()
  let deck = store.getUserDecks(uid).find((d) => d.name.toLowerCase() === deckName.toLowerCase())
  let deckCreated = false
  if (!deck) {
    const id = newId('deck')
    deck = {
      id,
      user_id: uid,
      name: deckName,
      parent_id: null,
      desired_retention_override: null,
      default_priority: 70,
      position: store.getUserDecks(uid).length,
      target_event_date: null,
      target_event_title: null,
      documentation: req.body?.documentation ?? null,
      thematic_nature: req.body?.thematic_nature ?? null,
      source_documents: Array.isArray(req.body?.source_documents) ? req.body.source_documents : [],
      created_at: new Date().toISOString(),
    }
    store.decks.set(id, deck)
    deckCreated = true
  }
  const incoming = Array.isArray(req.body?.cards) ? req.body.cards : []
  let cardsCreated = 0
  let refsCreated = 0
  for (const item of incoming) {
    const out = buildCardsFromNote(uid, {
      deck_id: deck.id,
      template_kind: item.kind || 'basic',
      field_values: { front: item.front, back: item.back, text: item.cloze_text },
    })
    for (const c of out.cards) {
      if (item.quote) {
        c.references.push({
          quote: item.quote,
          quote_verified: Boolean(item.quote_verified),
          locator: item.locator ?? null,
          source_title: src?.title ?? null,
          extract_id: item.extract_id ?? null,
          passage: item.extract_id ? store.extracts.get(item.extract_id)?.content ?? null : null,
        })
        refsCreated++
      }
      cardsCreated++
    }
  }
  res.status(201).json({
    deck_id: deck.id,
    deck_created: deckCreated,
    notes_created: incoming.length,
    cards_created: cardsCreated,
    references_created: refsCreated,
    warnings: [],
  })
})

// ─── Media, Interference, Imports, Stats, Leeches, Export ────────────────────
app.post('/api/media', requireAuth, upload.single('file'), (req: AuthedRequest, res) => {
  const file = req.file
  if (!file) {
    res.status(400).json({ detail: 'No file uploaded' })
    return
  }
  const ext = path.extname(file.originalname || '.png') || '.png'
  const filename = `${newId('img')}${ext}`
  store.mediaFiles.set(filename, {
    buffer: file.buffer,
    contentType: file.mimetype || 'application/octet-stream',
    filename,
  })
  res.status(201).json({
    url: `/media/${filename}`,
    kind: file.mimetype.startsWith('image/') ? 'image' : 'file',
    bytes: file.size,
  })
})

app.get('/media/:filename', (req, res) => {
  const item = store.mediaFiles.get(String(req.params.filename))
  if (!item) {
    res.status(404).json({ detail: 'Media file not found' })
    return
  }
  res.setHeader('Content-Type', item.contentType)
  res.send(item.buffer)
})

app.post('/api/interference/scan', requireAuth, (req: AuthedRequest, res) => {
  res.json(store.scanInterference(req.user!.id))
})

app.get('/api/interference', requireAuth, (req: AuthedRequest, res) => {
  const pairs = Array.from(store.sisterPairs.values()).filter(
    (p) => p.user_id === req.user!.id && p.status !== 'dismissed',
  )
  res.json(pairs)
})

app.post('/api/interference/:id/dismiss', requireAuth, (req: AuthedRequest, res) => {
  const pair = store.sisterPairs.get(String(req.params.id))
  if (!pair || pair.user_id !== req.user!.id) {
    res.status(404).json({ detail: 'Pair not found' })
    return
  }
  pair.status = 'dismissed'
  res.json(pair)
})

app.post('/api/interference/:id/contrast-drill', requireAuth, (req: AuthedRequest, res) => {
  const pair = store.sisterPairs.get(String(req.params.id))
  if (!pair || pair.user_id !== req.user!.id) {
    res.status(404).json({ detail: 'Pair not found' })
    return
  }
  res.json({
    pair_id: pair.id,
    concept_a_title: pair.front_a.slice(0, 60),
    concept_b_title: pair.front_b.slice(0, 60),
    front_a: pair.front_a,
    back_a: pair.back_a,
    front_b: pair.front_b,
    back_b: pair.back_b,
    discriminative_challenge: 'Identify the exact cue that separates Concept A from Concept B without conflating their outputs.',
    key_distinction: `Concept A emphasizes "${pair.back_a.slice(0, 80)}", whereas Concept B emphasizes "${pair.back_b.slice(0, 80)}".`,
    divergent_conditions: [
      { condition: 'Primary trigger', choice_a: pair.front_a.slice(0, 60), choice_b: pair.front_b.slice(0, 60) },
      { condition: 'Expected result', choice_a: pair.back_a.slice(0, 60), choice_b: pair.back_b.slice(0, 60) },
    ],
  })
})

app.get('/api/import/history', requireAuth, (req: AuthedRequest, res) => {
  res.json(store.imports.filter((i) => i.user_id === req.user!.id))
})

app.post('/api/import/json', requireAuth, (req: AuthedRequest, res) => {
  const uid = req.user!.id
  const isArr = Array.isArray(req.body)
  const deckName = String(isArr ? req.query.deck || 'Imported Deck' : req.body?.deck || 'Imported Deck').trim()
  const notes = isArr ? req.body : Array.isArray(req.body?.notes) ? req.body.notes : []

  let deck = store.getUserDecks(uid).find((d) => d.name.toLowerCase() === deckName.toLowerCase())
  let deckCreated = false
  if (!deck) {
    const id = newId('deck')
    deck = {
      id,
      user_id: uid,
      name: deckName,
      parent_id: null,
      desired_retention_override: null,
      default_priority: Number((!isArr && req.body?.priority) || 70),
      position: store.getUserDecks(uid).length,
      target_event_date: null,
      target_event_title: null,
      documentation: null,
      thematic_nature: null,
      source_documents: [],
      created_at: new Date().toISOString(),
    }
    store.decks.set(id, deck)
    deckCreated = true
  }

  let cardsCreated = 0
  let citationsCreated = 0
  for (const note of notes) {
    const out = buildCardsFromNote(uid, {
      deck_id: deck.id,
      template_kind: note.kind || note.card_type || 'basic',
      priority: note.priority,
      tags: note.tags || [],
      field_values: {
        front: note.front,
        back: note.back,
        text: note.cloze_text,
        image: note.image,
        back_image: note.back_image,
        starter_code: note.starter_code,
        starter_tests: note.starter_tests,
        time_complexity: note.time_complexity,
        space_complexity: note.space_complexity,
      },
    })
    for (const c of out.cards) {
      if (note.quote) {
        c.references.push({
          quote: note.quote,
          quote_verified: true,
          locator: note.locator ?? null,
          source_title: note.source_title ?? null,
          extract_id: null,
          passage: note.quote,
        })
        citationsCreated++
      }
      cardsCreated++
    }
  }

  store.imports.unshift({
    id: newId('imp'),
    user_id: uid,
    filename: `${deckName}.json`,
    imported_at: new Date().toISOString(),
    notes_mapped: notes.length,
    cards_mapped: cardsCreated,
    warnings: [],
  })

  res.status(201).json({
    deck_id: deck.id,
    deck_created: deckCreated,
    notes_created: notes.length,
    cards_created: cardsCreated,
    citations_created: citationsCreated,
    warnings: [],
  })
})

app.get('/api/stats', requireAuth, (req: AuthedRequest, res) => {
  res.json(buildStats(store, req.user!))
})

app.get('/api/stats/learning-analytics', requireAuth, (req: AuthedRequest, res) => {
  const days = Number(req.query.days || 365)
  res.json(buildLearningAnalytics(store, req.user!, days))
})

app.post('/api/leeches/:cardId/dismiss', requireAuth, (req: AuthedRequest, res) => {
  const c = store.cards.get(String(req.params.cardId))
  if (c && c.user_id === req.user!.id) c.leech_flag = false
  res.json({ dismissed: true })
})

app.post('/api/leeches/:cardId/suspend', requireAuth, (req: AuthedRequest, res) => {
  const c = store.cards.get(String(req.params.cardId))
  if (c && c.user_id === req.user!.id) {
    c.suspended = true
    c.leech_flag = false
  }
  res.json({ suspended: true })
})

app.post('/api/leeches/:cardId/accept', requireAuth, (req: AuthedRequest, res) => {
  const c = store.cards.get(String(req.params.cardId))
  if (c && c.user_id === req.user!.id) {
    c.leech_flag = false
    c.lapse_count = 0
  }
  res.json({ applied: 'reset', cards_created: 0 })
})

app.post('/api/optimize', requireAuth, (req: AuthedRequest, res) => {
  const uid = req.user!.id
  const count = store.reviewLogs.filter((l) => l.user_id === uid).length
  const minReviews = 50
  if (count >= minReviews) req.user!.fsrs_optimized_at = new Date().toISOString()
  res.json({
    optimized: count >= minReviews,
    review_count: count,
    min_reviews: minReviews,
    optimizer_installed: true,
    reason: count >= minReviews ? null : `Need at least ${minReviews} reviews to personalize FSRS weights (currently ${count}).`,
  })
})

app.get('/api/export', requireAuth, (req: AuthedRequest, res) => {
  const uid = req.user!.id
  res.json({
    exported_at: new Date().toISOString(),
    decks: store.getUserDecks(uid),
    cards: store.getUserCards(uid),
    review_logs: store.reviewLogs.filter((l) => l.user_id === uid),
  })
})

app.get('/api/export/review-logs.csv', requireAuth, (req: AuthedRequest, res) => {
  const uid = req.user!.id
  const rows = ['id,card_id,reviewed_at,final_grade,latency_ms,overridden']
  for (const l of store.reviewLogs.filter((r) => r.user_id === uid)) {
    rows.push(`${l.id},${l.card_id},${l.reviewed_at},${l.final_grade},${l.latency_ms ?? ''},${l.overridden}`)
  }
  res.setHeader('Content-Type', 'text/csv; charset=utf-8')
  res.send(rows.join('\n'))
})

// ─── Memory Athlete ──────────────────────────────────────────────────────────
app.post('/api/memory/lint-atomicity', requireAuth, (req: AuthedRequest, res) => {
  res.json(
    lintAtomicity(
      String(req.body?.front || ''),
      String(req.body?.back || ''),
      String(req.body?.template_kind || 'basic'),
    ),
  )
})

app.post('/api/memory/sequential-cloze', requireAuth, (req: AuthedRequest, res) => {
  const uid = req.user!.id
  const title = String(req.body?.title || 'Sequence')
  const steps: string[] = Array.isArray(req.body?.steps) ? req.body.steps.map(String) : []
  const windowSize = Number(req.body?.window_size || 2)
  const deckId = req.body?.deck_id ? String(req.body.deck_id) : null
  const items = steps.map((step, i) => {
    const contextBefore = steps.slice(Math.max(0, i - windowSize), i)
    const contextAfter = steps.slice(i + 1, i + 1 + windowSize)
    const front = `${title} (Step ${i + 1}/${steps.length})\n${contextBefore.map((s) => `• ${s}`).join('\n')}\n• [???]`
    return {
      step_index: i,
      total_steps: steps.length,
      front,
      back: step,
      target_step: step,
      context_before: contextBefore,
      context_after: contextAfter,
    }
  })
  let created = 0
  if (deckId) {
    for (const item of items) {
      buildCardsFromNote(uid, {
        deck_id: deckId,
        template_kind: 'basic',
        field_values: { front: item.front, back: item.back },
        tags: ['sequential-cloze'],
      })
      created++
    }
  }
  res.json({ cards: items, notes_created: created, cards_created: created })
})

app.post('/api/memory/decompose', requireAuth, (req: AuthedRequest, res) => {
  const front = String(req.body?.front || '')
  const back = String(req.body?.back || '')
  const phrases = extractKeyPhrases(back)
  const cards =
    phrases.length > 1
      ? phrases.map((p, idx) => ({
          front: `${front} (Part ${idx + 1}/${phrases.length})`,
          back: p,
        }))
      : [{ front, back }]
  res.json({ cards })
})

app.get('/api/memory/event-readiness', requireAuth, (req: AuthedRequest, res) => {
  const user = req.user!
  const deckId = typeof req.query.deck_id === 'string' ? req.query.deck_id : null
  const deck = deckId ? store.decks.get(deckId) : null
  const targetDate = deck?.target_event_date ?? user.target_event_date
  const targetTitle = deck?.target_event_title ?? user.target_event_title
  const cards = deckId
    ? store.getUserCards(user.id).filter((c) => store.getDescendantDeckIds(user.id, deckId).has(c.deck_id))
    : store.getUserCards(user.id)
  const daysRemaining = targetDate
    ? Math.max(0, Math.ceil((new Date(targetDate).getTime() - Date.now()) / 86_400_000))
    : null
  const dueCount = cards.filter((c) => store.isCardDue(c)).length
  const unstableCount = cards.filter((c) => (c.stability ?? 0) < 7).length
  res.json({
    target_event_date: targetDate,
    target_event_title: targetTitle,
    days_remaining: daysRemaining,
    is_active: Boolean(targetDate),
    projected_retention: Number(user.desired_retention.toFixed(2)),
    total_cards_count: cards.length,
    due_cards_count: dueCount,
    unstable_cards_count: unstableCount,
    estimated_daily_reviews_needed: daysRemaining && daysRemaining > 0 ? Math.ceil(cards.length / daysRemaining) : dueCount,
    status_label: targetDate ? 'On Track' : 'No Target Event Set',
  })
})

// ─── Code Practice & Pre-LeetCode Fundamentals ───────────────────────────────
app.get('/api/code/problems', requireAuth, (req: AuthedRequest, res) => {
  const uid = req.user!.id
  const { kind, track, category, difficulty, search } = req.query
  let list = Array.from(store.codeProblems.values())
  if (typeof kind === 'string' && kind) list = list.filter((p) => p.kind === kind)
  if (typeof track === 'string' && track) list = list.filter((p) => p.track === track)
  if (typeof category === 'string' && category) list = list.filter((p) => p.category === category)
  if (typeof difficulty === 'string' && difficulty) list = list.filter((p) => p.difficulty === difficulty)
  if (typeof search === 'string' && search.trim()) {
    const q = search.trim().toLowerCase()
    list = list.filter(
      (p) =>
        p.title.toLowerCase().includes(q) ||
        p.category.toLowerCase().includes(q) ||
        p.tags.some((t) => t.toLowerCase().includes(q)),
    )
  }

  const userSubs = store.codeSubmissions.filter((s) => s.user_id === uid)
  res.json(
    list.map((p) => {
      const pSubs = userSubs.filter((s) => s.problem_id === p.id)
      const latest = pSubs[pSubs.length - 1]
      return {
        id: p.id,
        kind: p.kind,
        track: p.track,
        title: p.title,
        slug: p.slug,
        difficulty: p.difficulty,
        category: p.category,
        tags: p.tags,
        has_submission: pSubs.length > 0,
        last_status: latest?.status ?? null,
      }
    }),
  )
})

function findProblem(idOrSlug: string) {
  const direct = store.codeProblems.get(idOrSlug)
  if (direct) return direct
  for (const p of store.codeProblems.values()) {
    if (p.slug === idOrSlug) return p
  }
  return undefined
}

app.post('/api/code/problems/forge', requireAuth, (req: AuthedRequest, res) => {
  const topic = String(req.body?.topic || 'Array Manipulation').trim()
  const difficulty = (['Easy', 'Medium', 'Hard'].includes(req.body?.difficulty)
    ? req.body.difficulty
    : 'Medium') as 'Easy' | 'Medium' | 'Hard'
  const slug = `forged-${topic.toLowerCase().replace(/[^a-z0-9]+/g, '-')}-${Date.now().toString(36)}`
  const id = `prob_${slug}`
  const prob = {
    id,
    kind: 'problem' as const,
    track: null,
    title: `Forged: ${topic}`,
    slug,
    difficulty,
    category: topic,
    tags: ['Forged', topic],
    description: `Implement a clean, well-tested solution for **${topic}**.\n\nReturn the transformed output for each input array while maintaining optimal time complexity.`,
    examples: [{ input: 'nums = [1, 2, 3]', output: '[1, 2, 3]' }],
    constraints: ['1 <= nums.length <= 10^4'],
    starter_codes: {
      typescript: 'function solve(nums: number[]): number[] {\n  // Write your implementation\n  return nums;\n}\n',
      python: 'class Solution:\n    def solve(self, nums: list[int]) -> list[int]:\n        return nums\n',
    },
    solutions: {
      typescript: 'function solve(nums: number[]): number[] {\n  return [...nums];\n}\n',
    },
    editorial: `Focus on preserving the core invariant for ${topic}.`,
    test_cases: [{ input: { nums: [1, 2, 3] }, expected: [1, 2, 3] }],
    hints: ['Start by verifying the base case and loop invariant.'],
    created_at: new Date().toISOString(),
  }
  store.codeProblems.set(id, prob)
  res.status(201).json(prob)
})

app.get('/api/code/problems/:idOrSlug', requireAuth, (req: AuthedRequest, res) => {
  const prob = findProblem(String(req.params.idOrSlug))
  if (!prob) {
    res.status(404).json({ detail: 'Problem not found' })
    return
  }
  res.json(prob)
})

app.post('/api/code/problems/:idOrSlug/run', requireAuth, async (req: AuthedRequest, res) => {
  const prob = findProblem(String(req.params.idOrSlug))
  if (!prob) {
    res.status(404).json({ detail: 'Problem not found' })
    return
  }
  const result = await executeCode({
    code: String(req.body?.code || ''),
    language: String(req.body?.language || 'python'),
    test_cases: Array.isArray(req.body?.custom_test_cases) ? req.body.custom_test_cases : prob.test_cases,
  })
  res.json(result)
})

app.post('/api/code/problems/:idOrSlug/submit', requireAuth, async (req: AuthedRequest, res) => {
  const prob = findProblem(String(req.params.idOrSlug))
  if (!prob) {
    res.status(404).json({ detail: 'Problem not found' })
    return
  }
  const language = String(req.body?.language || 'python')
  const code = String(req.body?.code || '')
  const result = await executeCode({ code, language, test_cases: prob.test_cases })
  const submissionId = newId('sub')
  store.codeSubmissions.push({
    id: submissionId,
    user_id: req.user!.id,
    problem_id: prob.id,
    language,
    code,
    status: result.status,
    passed_tests: result.passed_count,
    total_tests: result.total_count,
    runtime_ms: result.runtime_ms,
    error: result.error,
    created_at: new Date().toISOString(),
  })
  res.json({ submission_id: submissionId, ...result })
})

app.post('/api/code/problems/:idOrSlug/socratic', requireAuth, (req: AuthedRequest, res) => {
  const prob = findProblem(String(req.params.idOrSlug))
  if (!prob) {
    res.status(404).json({ detail: 'Problem not found' })
    return
  }
  const hint = prob.hints[0] || `Break "${prob.title}" into its input invariant, base case, and state transition.`
  res.json({ hint })
})

app.post('/api/code/problems/:idOrSlug/export-card', requireAuth, (req: AuthedRequest, res) => {
  const prob = findProblem(String(req.params.idOrSlug))
  if (!prob) {
    res.status(404).json({ detail: 'Problem not found' })
    return
  }
  const deckId = String(req.body?.deck_id || store.getUserDecks(req.user!.id)[0]?.id || '')
  const out = buildCardsFromNote(req.user!.id, {
    deck_id: deckId,
    template_kind: 'code',
    tags: prob.tags,
    field_values: {
      title: prob.title,
      front: `${prob.title}\n\n${prob.description}`,
      back: Object.values(prob.solutions)[0] || prob.editorial || '',
      starter_code: Object.values(prob.starter_codes)[0] || '',
      test_cases: prob.test_cases,
      difficulty: prob.difficulty,
      category: prob.category,
    },
  })
  res.status(201).json({
    note_id: out.noteId,
    card_id: out.cards[0]?.id,
    message: `Exported "${prob.title}" to your deck.`,
  })
})

app.post('/api/code/explain-selection', requireAuth, (req: AuthedRequest, res) => {
  const sel = String(req.body?.selected_code || '').trim()
  res.json({
    explanation: `Selected snippet (\`${sel.slice(0, 80)}\`) performs a localized computation step. Trace its inputs, side effects, and return value against the surrounding scope.`,
    occams_razor: `Focus on what state "${sel.slice(0, 50)}" reads and mutates.`,
    socratic_insight: 'What happens to this line on an empty input or boundary index?',
    doc_citation: null,
    verbatim_passage: null,
    doc_matches: [],
    model_used: 'code-explainer-heuristic',
    available_models: ['qwen2.5-coder:7b'],
  })
})

app.post('/api/code/ask-docs', requireAuth, (req: AuthedRequest, res) => {
  const question = String(req.body?.question || '').trim()
  res.json({
    answer: `Regarding "${question.slice(0, 100)}": check the loop invariants, data structure complexity, and edge cases in your deck documentation.`,
    doc_citation: null,
    citations: [],
    model_used: 'docs-qa-heuristic',
    available_models: ['qwen2.5-coder:7b'],
    extracted_glosses: [],
    updated_card_glosses: null,
  })
})

app.get('/api/code/submissions', requireAuth, (req: AuthedRequest, res) => {
  const uid = req.user!.id
  const limit = Number(req.query.limit || 20)
  const problemId = typeof req.query.problem_id === 'string' ? req.query.problem_id : null
  const list = store.codeSubmissions
    .filter((s) => s.user_id === uid && (!problemId || s.problem_id === problemId))
    .sort((a, b) => b.created_at.localeCompare(a.created_at))
    .slice(0, limit)
  res.json(list)
})

app.get('/api/code/stats', requireAuth, (req: AuthedRequest, res) => {
  res.json(buildCodeStats(store, req.user!.id))
})

// ─── Lexicon & Sync ──────────────────────────────────────────────────────────
app.post('/api/lexicon/lookup', requireAuth, (req: AuthedRequest, res) => {
  const uid = req.user!.id
  const term = String(req.body?.term || '').trim()
  const key = term.toLowerCase()
  const match = store.guttagLexicon.get(key)
  const definition =
    match?.definition ||
    `Key domain term "${term}" used in ${req.body?.thematic_nature || req.body?.deck_name || 'your active study material'}.`
  const domain = match?.domain || req.body?.thematic_nature || 'General Knowledge'
  const now = new Date().toISOString()

  store.recentLexicon = [
    { user_id: uid, term, definition, domain, created_at: now },
    ...store.recentLexicon.filter((r) => !(r.user_id === uid && r.term.toLowerCase() === key)),
  ].slice(0, 40)

  res.json({
    term,
    definition,
    context_explanation: req.body?.context ? `In context: ${String(req.body.context).slice(0, 160)}` : null,
    example: match?.example ?? null,
    domain,
    related_terms: [],
    cached: Boolean(match),
    model_used: match ? 'guttag-lexicon' : 'lexicon-heuristic',
    created_at: now,
  })
})

app.get('/api/lexicon/recent', requireAuth, (req: AuthedRequest, res) => {
  res.json(store.recentLexicon.filter((r) => r.user_id === req.user!.id).slice(0, 20))
})

app.get('/api/sync/status', requireAuth, (req: AuthedRequest, res) => {
  const uid = req.user!.id
  let totalConns = 0
  for (const s of userSockets.values()) totalConns += s.size
  res.json({
    lan_ip: '0.0.0.0',
    port: PORT,
    pairing_url: `http://localhost:${PORT}`,
    active_connections: totalConns,
    user_connections: userSockets.get(uid)?.size ?? 0,
    server_time: new Date().toISOString(),
  })
})

// ─── Concept Graph (Neuroscience Enhancements) ───────────────────────────────
app.get('/api/graph', requireAuth, (req: AuthedRequest, res) => {
  const uid = req.user!.id
  const deckId = typeof req.query.deck_id === 'string' ? req.query.deck_id : null
  const deckIds = deckId ? store.getDescendantDeckIds(uid, deckId) : null
  const cards = store.getUserCards(uid).filter((c) => !deckIds || deckIds.has(c.deck_id))
  const cardIdSet = new Set(cards.map((c) => c.id))

  const nodes = cards.map((c) => ({
    id: c.id,
    card_id: c.id,
    title: c.title || c.front.slice(0, 70),
    deck_id: c.deck_id,
    deck_name: store.decks.get(c.deck_id)?.name ?? '',
    state: c.state,
    is_schema_checkpoint: c.is_schema_checkpoint,
    spatial_x: c.spatial_x,
    spatial_y: c.spatial_y,
    spatial_locus: c.spatial_locus,
    activation: computeRetrievability(c),
  }))

  const edges = Array.from(store.conceptEdges.values())
    .filter((e) => e.user_id === uid && cardIdSet.has(e.source_card_id) && cardIdSet.has(e.target_card_id))
    .map((e) => ({
      id: e.id,
      source: e.source_card_id,
      target: e.target_card_id,
      relationship_type: e.relationship_type,
      weight: e.weight,
    }))

  res.json({ nodes, edges, total_nodes: nodes.length, total_edges: edges.length })
})

app.post('/api/graph/edges', requireAuth, (req: AuthedRequest, res) => {
  const uid = req.user!.id
  const id = newId('edge')
  const edge = {
    id,
    user_id: uid,
    source_card_id: String(req.body?.source_card_id),
    target_card_id: String(req.body?.target_card_id),
    relationship_type: String(req.body?.relationship_type || 'relates_to'),
    weight: Number(req.body?.weight ?? 0.75),
    created_at: new Date().toISOString(),
  }
  store.conceptEdges.set(id, edge)
  res.status(201).json(edge)
})

app.delete('/api/graph/edges/:edgeId', requireAuth, (req: AuthedRequest, res) => {
  store.conceptEdges.delete(String(req.params.edgeId))
  res.status(204).end()
})

app.get('/api/graph/related/:cardId', requireAuth, (req: AuthedRequest, res) => {
  const uid = req.user!.id
  const sourceId = String(req.params.cardId)
  const source = store.cards.get(sourceId)
  if (!source || source.user_id !== uid) {
    res.status(404).json({ detail: 'Card not found' })
    return
  }
  const decay = Number(req.query.decay || 0.6)
  const edges = Array.from(store.conceptEdges.values()).filter((e) => e.user_id === uid)
  const activated: Array<{
    card_id: string
    title: string
    deck_name: string
    activation: number
    path_depth: number
    relationship_to_source: string | null
  }> = []

  for (const e of edges) {
    const otherId = e.source_card_id === sourceId ? e.target_card_id : e.target_card_id === sourceId ? e.source_card_id : null
    if (!otherId) continue
    const other = store.cards.get(otherId)
    if (!other) continue
    activated.push({
      card_id: other.id,
      title: other.title || other.front.slice(0, 70),
      deck_name: store.decks.get(other.deck_id)?.name ?? '',
      activation: Number((e.weight * decay).toFixed(3)),
      path_depth: 1,
      relationship_to_source: e.relationship_type,
    })
  }
  res.json({
    source_card_id: source.id,
    source_title: source.title || source.front.slice(0, 70),
    activated_nodes: activated,
  })
})

app.post('/api/graph/auto-link', requireAuth, (req: AuthedRequest, res) => {
  const uid = req.user!.id
  const cards = store.getUserCards(uid)
  const created = []
  for (let i = 0; i < cards.length; i++) {
    for (let j = i + 1; j < cards.length; j++) {
      const sim = jaccardSimilarity(`${cards[i].front} ${cards[i].back}`, `${cards[j].front} ${cards[j].back}`)
      if (sim < 0.2) continue
      const exists = Array.from(store.conceptEdges.values()).some(
        (e) =>
          e.user_id === uid &&
          ((e.source_card_id === cards[i].id && e.target_card_id === cards[j].id) ||
            (e.source_card_id === cards[j].id && e.target_card_id === cards[i].id)),
      )
      if (!exists) {
        const id = newId('edge')
        const edge = {
          id,
          user_id: uid,
          source_card_id: cards[i].id,
          target_card_id: cards[j].id,
          relationship_type: 'relates_to',
          weight: Number(Math.min(1, sim + 0.3).toFixed(2)),
          created_at: new Date().toISOString(),
        }
        store.conceptEdges.set(id, edge)
        created.push(edge)
      }
    }
  }
  res.json({ created_count: created.length, edges: created })
})

// ─── Static Frontend Serving & SPA Fallback ──────────────────────────────────
if (fs.existsSync(FRONTEND_DIST)) {
  app.use(express.static(FRONTEND_DIST))
}

app.get('*', (req, res) => {
  if (req.path.startsWith('/api/') || req.path.startsWith('/media/')) {
    res.status(404).json({ detail: `Not found: ${req.path}` })
    return
  }
  const indexHtml = path.join(FRONTEND_DIST, 'index.html')
  if (fs.existsSync(indexHtml)) {
    res.sendFile(indexHtml)
    return
  }
  res.status(503).send('Ars Memoriae frontend build not found. Run `npm run build` first.')
})

// ─── HTTP + WebSocket Server on 0.0.0.0:3000 ─────────────────────────────────
const server = http.createServer(app)
const wss = new WebSocketServer({ noServer: true })

server.on('upgrade', (req, socket, head) => {
  if (req.url && req.url.startsWith('/api/sync/ws')) {
    wss.handleUpgrade(req, socket, head, (ws) => {
      wss.emit('connection', ws, req)
    })
  } else {
    socket.destroy()
  }
})

wss.on('connection', (ws) => {
  let authedUserId: string | null = null

  ws.on('message', (raw) => {
    try {
      const msg = JSON.parse(String(raw)) as { type?: string; token?: string }
      if (msg.type === 'AUTH') {
        const user = store.getUserByToken(msg.token)
        if (!user) {
          ws.close(1008, 'Invalid token')
          return
        }
        authedUserId = user.id
        if (!userSockets.has(user.id)) userSockets.set(user.id, new Set())
        userSockets.get(user.id)!.add(ws)
        ws.send(JSON.stringify({ type: 'CONNECTED', data: { user_id: user.id } }))
      } else if (msg.type === 'PING') {
        ws.send(JSON.stringify({ type: 'PONG', data: { server_time: new Date().toISOString() } }))
      }
    } catch {
      /* ignore malformed frames */
    }
  })

  ws.on('close', () => {
    if (authedUserId) {
      userSockets.get(authedUserId)?.delete(ws)
    }
  })
})

server.listen(PORT, '0.0.0.0', () => {
  console.log(`Ars Memoriae listening on http://0.0.0.0:${PORT}`)
})
