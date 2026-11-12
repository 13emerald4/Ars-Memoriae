import { useCallback, useEffect, useState, type ReactNode } from 'react'
import { QRCodeSVG } from 'qrcode.react'
import { api } from '../api/client'
import { dialogs } from '../components/dialogs'
import type {
  EventReadiness,
  HardwareProfile,
  LlmEngineStatusResponse,
  QueueConfig,
  SyncStatus,
  User,
} from '../api/types'
import {
  ALLOWED_QWEN_CODER_MODELS,
  ANTIGRAVITY_MODELS,
  getModelDisplayInfo,
  isAntigravityModel,
} from '../api/types'
import { ErrorNote, Section, Spinner } from '../components/ui'
import { useAuth } from '../hooks/useAuth'
import { FullscreenButton, useFullscreen } from '../components/FullscreenContext'



import { useTheme, THEME_REGISTRY, FONT_SIZES, type CognitiveTheme, type FontSize } from '../components/ThemeContext'
import InteractiveTutorialModal from '../components/InteractiveTutorialModal'
import { storage } from '../utils/storage'

export default function Settings() {
  const { user, refresh, signOut } = useAuth()
  const [queueCfg, setQueueCfg] = useState<QueueConfig | null>(null)
  const [error, setError] = useState<unknown>(null)
  const [showTutorial, setShowTutorial] = useState(false)
  const [tutorialMode, setTutorialMode] = useState<'prompt' | 'tour'>('tour')
  const [tutorialType, setTutorialType] = useState<'extensive' | 'brief'>('extensive')

  const load = useCallback(async () => {
    try {
      setQueueCfg(await api.queueConfig())
    } catch (err) {
      setError(err)
    }
  }, [])

  useEffect(() => {
    void load()
  }, [load])

  if (!user || !queueCfg) return <Spinner />

  // One list drives both the jump bar and the page, so they cannot drift.
  // Everyday settings come first; the hardware and model panel, which most
  // people set once, no longer opens the page.
  const sections: { id: string; label: string; content: ReactNode }[] = [
    { id: 'scheduling', label: 'Scheduling', content: <SchedulingPanel user={user} onChange={refresh} /> },
    { id: 'queue', label: 'Queue', content: <QueuePanel cfg={queueCfg} onChange={load} /> },
    { id: 'ai', label: 'AI engine', content: <QwenCoderPanel user={user} onChange={refresh} /> },
    { id: 'memory', label: 'Memory methods', content: <MemoryChampionPanel user={user} onChange={refresh} /> },
    { id: 'neuro', label: 'Neuroscience', content: <NeurosciencePanel user={user} onChange={refresh} /> },
    { id: 'theme', label: 'Theme', content: <CognitiveThemePanel /> },
    { id: 'typography', label: 'Text size', content: <TypographyPanel /> },
    { id: 'focus', label: 'Focus', content: <DisplayFocusPanel /> },
    {
      id: 'tutorial',
      label: 'Tutorial',
      content: (
        <TutorialPanel
          user={user}
          onLaunchTutorial={(mode, type) => {
            setTutorialMode(mode)
            setTutorialType(type)
            setShowTutorial(true)
          }}
          onChange={refresh}
        />
      ),
    },
    { id: 'modules', label: 'Modules', content: <NavigationModulesPanel user={user} onChange={refresh} /> },
    { id: 'mobile', label: 'Mobile', content: <MobileCompanionPanel user={user} /> },
    { id: 'data', label: 'Data', content: <DataPanel /> },
    { id: 'feedback', label: 'Feedback', content: <FeatureRequestPanel /> },
    { id: 'account', label: 'Account', content: <AccountPanel user={user} onSignOut={signOut} /> },
  ]

  return (
    <div className="space-y-6">
      <nav
        aria-label="Settings sections"
        className="sticky top-12 z-10 -mx-1 flex gap-1.5 overflow-x-auto no-scrollbar rounded-xl border border-ink-line bg-ink/95 px-2 py-2 backdrop-blur"
      >
        {sections.map((section) => (
          <a
            key={section.id}
            href={`#settings-${section.id}`}
            className="chip shrink-0 whitespace-nowrap hover:border-sky-500/50 hover:text-sky-200"
          >
            {section.label}
          </a>
        ))}
      </nav>

      <ErrorNote error={error} />

      {sections.map((section) => (
        <div key={section.id} id={`settings-${section.id}`} className="scroll-mt-28">
          {section.content}
        </div>
      ))}

      <InteractiveTutorialModal
        isOpen={showTutorial}
        onClose={() => setShowTutorial(false)}
        initialMode={tutorialMode}
        initialType={tutorialType}
      />
    </div>
  )
}

/** Sign-out, password and session control. A password change or "sign out
 *  everywhere" revokes every token issued so far (other browsers, paired
 *  phones); this tab is handed a fresh one so it stays signed in. */
function AccountPanel({ user, onSignOut }: { user: User; onSignOut: () => void }) {
  const { adoptToken } = useAuth()
  const [current, setCurrent] = useState('')
  const [next, setNext] = useState('')
  const [repeat, setRepeat] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<unknown>(null)

  const mismatch = repeat.length > 0 && next !== repeat
  const canSubmit = current.length > 0 && next.length >= 8 && next === repeat && !busy

  async function changePassword(e: React.FormEvent) {
    e.preventDefault()
    if (!canSubmit) return
    setBusy(true)
    setError(null)
    try {
      const { access_token } = await api.changePassword(current, next)
      adoptToken(access_token)
      setCurrent('')
      setNext('')
      setRepeat('')
      dialogs.notify('Password changed. Other devices have been signed out.', 'success')
    } catch (err) {
      setError(err)
    } finally {
      setBusy(false)
    }
  }

  async function signOutEverywhere() {
    const ok = await dialogs.confirm({
      title: 'Sign out everywhere else?',
      message:
        'Every other browser and every paired phone is signed out and has to sign in or pair again. This tab stays signed in.',
      confirmLabel: 'Sign out other devices',
      danger: true,
    })
    if (!ok) return
    try {
      const { access_token } = await api.logoutEverywhere()
      adoptToken(access_token)
      dialogs.notify('All other sessions were signed out.', 'success')
    } catch (err) {
      dialogs.error(err, 'Could not sign out other sessions.')
    }
  }

  return (
    <Section title="Account" description={user.email}>
      <div className="grid gap-6 md:grid-cols-2">
        <form onSubmit={changePassword} className="space-y-3">
          <h3 className="text-xs font-semibold uppercase tracking-wide text-slate-400">Change password</h3>
          {/* Lets password managers attach the new password to the right account. */}
          <input type="text" autoComplete="username" value={user.email} readOnly hidden />
          <Field label="Current password">
            <input
              type="password"
              className="input"
              autoComplete="current-password"
              value={current}
              onChange={(e) => setCurrent(e.target.value)}
            />
          </Field>
          <Field label="New password" hint="At least 8 characters.">
            <input
              type="password"
              className="input"
              autoComplete="new-password"
              minLength={8}
              value={next}
              onChange={(e) => setNext(e.target.value)}
            />
          </Field>
          <Field label="Repeat new password" hint={mismatch ? 'The two entries do not match.' : undefined}>
            <input
              type="password"
              className="input"
              autoComplete="new-password"
              aria-invalid={mismatch}
              value={repeat}
              onChange={(e) => setRepeat(e.target.value)}
            />
          </Field>
          <ErrorNote error={error} />
          <button type="submit" className="btn btn-primary" disabled={!canSubmit}>
            {busy ? 'Saving…' : 'Change password'}
          </button>
        </form>

        <div className="space-y-3">
          <h3 className="text-xs font-semibold uppercase tracking-wide text-slate-400">Sessions</h3>
          <p className="text-xs leading-relaxed text-slate-400">
            Signing out here only affects this browser. If a phone was paired or a session left open
            somewhere you no longer trust, sign out everywhere else.
          </p>
          <div className="flex flex-wrap gap-2">
            <button type="button" className="btn" onClick={() => void signOutEverywhere()}>
              Sign out everywhere else
            </button>
            <button type="button" className="btn btn-danger" onClick={onSignOut}>
              Sign out
            </button>
          </div>
        </div>
      </div>
    </Section>
  )
}

function QwenCoderPanel({ user, onChange }: { user: User; onChange: () => Promise<void> }) {
  const [status, setStatus] = useState<LlmEngineStatusResponse | null>(null)
  const [hardware, setHardware] = useState<HardwareProfile | null>(null)
  const [checking, setChecking] = useState(false)
  const [error, setError] = useState<unknown>(null)

  const checkStatus = useCallback(async () => {
    setChecking(true)
    setError(null)
    try {
      const [s, h] = await Promise.all([
        api.llmStatus(),
        api.hardwareSpecs().catch(() => null),
      ])
      setStatus(s)
      if (h) setHardware(h)
    } catch (err) {
      setError(err)
    } finally {
      setChecking(false)
    }
  }, [])

  useEffect(() => {
    void checkStatus()
  }, [checkStatus])

  const canUseAntigravity = Boolean(user.can_use_antigravity)
  const isAgy = canUseAntigravity && isAntigravityModel(user.grading_model)
  const activeModelId = isAgy
    ? user.grading_model
    : (isAntigravityModel(user.grading_model) ? undefined : user.grading_model) ||
      hardware?.recommended_model ||
      'qwen2.5-coder:7b'
  const activeInfo = getModelDisplayInfo(activeModelId)
  const agyInfo = canUseAntigravity ? status?.providers?.antigravity : undefined
  const agyAvailableModels = agyInfo?.models ?? []

  const activateModel = async (modelId: string) => {
    await api.updateMe({ grading_model: modelId })
    await onChange()
    void checkStatus()
  }

  return (
    <Section
      title={canUseAntigravity ? 'AI Grading & Assistant Engine' : 'Local AI Engine'}
      description={
        canUseAntigravity
          ? 'Grade answers, drive Socratic hints, look up lexicon terms, and generate cards via your Antigravity Subscription (no API key) or local Ollama.'
          : 'Runs on this computer through Ollama, using one of the approved models listed below. Private, with zero cloud costs.'
      }
    >
      <div className="space-y-4">
        {/* Hardware Inspection & Recommendation Card */}
        {hardware && (
          <div className="rounded-xl border border-sky-500/30 bg-sky-950/20 p-4 space-y-3">
            <div className="flex flex-wrap items-center justify-between gap-2 border-b border-sky-500/20 pb-2.5">
              <div className="flex items-center gap-2.5">
                <div>
                  <h3 className="text-xs font-bold text-sky-200 uppercase tracking-wider">
                    Local Hardware Inspection
                  </h3>
                  <p className="text-[0.6875rem] text-slate-300">
                    {hardware.os_name} · {hardware.ram_gb.toFixed(1)} GB RAM
                    {hardware.gpu_name ? ` · ${hardware.gpu_name}${hardware.vram_gb ? ` (${hardware.vram_gb.toFixed(1)} GB VRAM)` : ''}` : ' · Integrated / CPU'}
                  </p>
                </div>
              </div>
              <span className="chip text-[0.625rem] uppercase font-bold border-sky-500/40 text-sky-300 bg-sky-500/10">
                {hardware.hardware_tier} tier
              </span>
            </div>

            <div className="space-y-1">
              <div className="flex items-center gap-2 text-xs font-bold text-emerald-300">
                <span>{hardware.headline}</span>
              </div>
              <p className="text-[0.6875rem] text-slate-300 leading-relaxed">
                {hardware.rationale}
              </p>
            </div>

            {!isAgy && user.grading_model !== hardware.recommended_model && (
              <div className="pt-2 flex flex-wrap items-center justify-between gap-3 text-xs border-t border-sky-500/10">
                <span className="text-[0.6875rem] text-slate-400">
                  Active model (<code className="font-mono text-slate-300">{user.grading_model || 'none'}</code>) differs from hardware-tailored recommendation.
                </span>
                <button
                  type="button"
                  onClick={() => void activateModel(hardware.recommended_model)}
                  className="btn btn-primary text-xs py-1 px-3 whitespace-nowrap cursor-pointer"
                >
                  Switch to Recommended ({hardware.recommended_size.toUpperCase()})
                </button>
              </div>
            )}
          </div>
        )}

        {/* Connection status card */}
        <div className="rounded-xl border border-ink-line bg-ink/60 p-4">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div className="flex items-center gap-3">
              <span
                className={`flex h-3 w-3 rounded-full ${
                  status?.connected && status?.model_ready
                    ? 'bg-emerald-400 ring-4 ring-emerald-500/20 animate-pulse'
                    : status?.connected
                    ? 'bg-amber-400 ring-4 ring-amber-500/20'
                    : 'bg-rose-500 ring-4 ring-rose-500/20'
                }`}
              />
              <div>
                <h3 className="text-sm font-semibold text-slate-100 flex items-center gap-2 flex-wrap">
                  <span>{activeInfo.label}</span>
                  <span className="chip text-[0.625rem] px-1.5 py-0.2 border-emerald-500/40 text-emerald-300 bg-emerald-500/10">
                    Active Grader
                  </span>
                  {canUseAntigravity && (
                    <span className="chip text-[0.5625rem] px-1.5 py-0.2 border-indigo-500/40 text-indigo-300 bg-indigo-500/10">
                      {isAgy ? 'Antigravity Subscription' : 'Local Ollama'}
                    </span>
                  )}
                  {!isAgy && hardware && user.grading_model === hardware.recommended_model && (
                    <span className="chip text-[0.5625rem] px-1 py-0.2 border-sky-500/40 text-sky-300 bg-sky-500/10">
                      Hardware Matched
                    </span>
                  )}
                </h3>
                <p className="text-xs text-slate-400 mt-0.5">
                  Engine: <code className="font-mono text-slate-300">{status?.base_url || (isAgy ? 'Antigravity Subscription (agy CLI)' : 'http://localhost:11434')}</code>
                </p>
              </div>
            </div>

            <div className="flex min-w-0 max-w-full flex-wrap items-center gap-2">
              <select aria-label="Active grading model"
                value={activeModelId}
                onChange={(e) => void activateModel(e.target.value)}
                className="select min-w-0 max-w-full truncate text-xs py-1 px-2.5 bg-slate-900 border border-slate-700 text-slate-200 font-mono rounded cursor-pointer"
                title="Select active grading & assistant model"
              >
                {canUseAntigravity && (
                  <optgroup label="Antigravity Subscription (No API Key)">
                    {ANTIGRAVITY_MODELS.map((opt) => (
                      <option key={opt.id} value={opt.id}>
                        {opt.name} — {opt.tier}
                      </option>
                    ))}
                    {agyAvailableModels
                      .filter((m) => !ANTIGRAVITY_MODELS.some((c) => c.id === m))
                      .map((m) => (
                        <option key={m} value={m}>
                          {getModelDisplayInfo(m).label}
                        </option>
                      ))}
                  </optgroup>
                )}
                <optgroup label="Local Ollama Models">
                  {ALLOWED_QWEN_CODER_MODELS.map((opt) => (
                    <option key={opt.id} value={opt.id}>
                      {opt.name} {opt.archetype}
                    </option>
                  ))}
                </optgroup>
              </select>

              <button
                className="btn text-xs py-1.5 px-3"
                disabled={checking}
                onClick={() => void checkStatus()}
              >
                {checking ? 'Testing…' : '↻ Test'}
              </button>
            </div>
          </div>

          {/* Status Diagnostic Callout */}
          {status && (
            <div className="mt-4 pt-3 border-t border-ink-line text-xs">
              {status.connected && status.model_ready ? (
                <div className="flex items-center gap-2 text-emerald-300">
                  <svg className="w-3.5 h-3.5 shrink-0" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3">
                    <polyline points="20 6 9 17 4 12" />
                  </svg>
                  <span>
                    {isAgy ? (
                      <>Antigravity Subscription (<code className="font-mono">agy</code> CLI) is signed in and <strong>{activeInfo.label}</strong> is ready across all grading and tutor tools (no API key required).</>
                    ) : (
                      <>Ollama is online and <strong>{user.grading_model || 'model'}</strong> is ready to grade solutions.</>
                    )}
                  </span>
                </div>
              ) : isAgy ? (
                <div className="space-y-2">
                  <p className="text-rose-300 font-medium">
                    Antigravity CLI needs setup or sign-in: {status.error || 'Unable to verify `agy models`.'}
                  </p>
                  <p className="text-slate-400">
                    Run <code className="font-mono text-slate-200">agy</code> once in your terminal and complete sign-in with your Antigravity subscription, then click Retry.
                  </p>
                </div>
              ) : status.connected ? (
                <div className="space-y-2">
                  <p className="text-amber-300 font-medium">
                    Notice: Ollama is running, but model <strong>{user.grading_model || hardware?.recommended_model || 'qwen2.5-coder:7b'}</strong> was not detected in your local library.
                  </p>
                  <p className="text-slate-400">
                    Run this command in your PowerShell / Terminal to download it:
                  </p>
                  <pre className="rounded bg-black/40 p-2 font-mono text-amber-200 text-xs select-all">
                    ollama pull {user.grading_model || hardware?.recommended_model || 'qwen2.5-coder:7b'}
                  </pre>
                </div>
              ) : (
                <div className="space-y-2">
                  <p className="text-rose-300 font-medium">
                    Could not connect to Ollama at <code className="font-mono">{status.base_url}</code>.
                  </p>
                  <p className="text-slate-400">
                    Start Ollama (<code className="font-mono text-sky-200">ollama serve</code>)
                    {canUseAntigravity ? (
                      <> or select an <strong>Antigravity Subscription</strong> model below to grade without Ollama.</>
                    ) : (
                      '.'
                    )}
                  </p>
                </div>
              )}
            </div>
          )}

          {/* Live VRAM Telemetry & Memory Capacity Monitor (local Ollama only) */}
          {!isAgy && status?.vram && (
            <div className="mt-4 pt-3 border-t border-ink-line space-y-3">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <div className="flex items-center gap-2">
                  <span className="text-xs font-semibold text-slate-200 flex items-center gap-1.5">
                    <svg aria-hidden="true" className="w-3.5 h-3.5 text-sky-400" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                      <rect x="2" y="3" width="20" height="14" rx="2" ry="2" />
                      <line x1="8" y1="21" x2="16" y2="21" />
                      <line x1="12" y1="17" x2="12" y2="21" />
                    </svg>
                    <span>
                      {status.vram.memory_source === 'system-ram'
                        ? 'Memory (no dedicated GPU detected)'
                        : 'GPU memory'}
                    </span>
                  </span>
                  <span className="text-[0.625rem] text-slate-400 font-mono">
                    {status.vram.gpu_name}
                  </span>
                </div>
                {status.vram.model_loaded ? (
                  <span className="chip text-[0.625rem] uppercase font-bold border-emerald-500/40 text-emerald-300 bg-emerald-500/10 flex items-center gap-1">
                    <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
                    Model Resident in VRAM
                  </span>
                ) : (
                  <span className="chip text-[0.625rem] uppercase font-bold border-amber-500/40 text-amber-300 bg-amber-500/10">
                    Standby (Loads on demand)
                  </span>
                )}
              </div>

              {/* Three Stat Cards */}
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-2.5">
                {/* 1. Computer Capacity */}
                <div className="rounded-lg border border-slate-800 bg-slate-900/60 p-3 space-y-1">
                  <span className="text-[0.625rem] uppercase font-bold text-slate-400 tracking-wider">
                    {status.vram.memory_source === 'system-ram'
                      ? 'System RAM'
                      : status.vram.memory_source === 'apple-unified'
                        ? 'Unified memory'
                        : 'GPU memory (VRAM)'}
                  </span>
                  <div className="flex items-baseline gap-1.5">
                    <span className="text-lg font-bold font-mono text-slate-100">
                      {status.vram.capacity_gb != null ? `${status.vram.capacity_gb.toFixed(1)} GB` : 'N/A'}
                    </span>
                    <span className="text-[0.625rem] text-slate-400 font-mono">
                      ({status.vram.capacity_mb != null ? `${Math.round(status.vram.capacity_mb)} MB` : ''})
                    </span>
                  </div>
                  <p className="text-[0.625rem] text-slate-400">
                    {status.vram.memory_source === 'system-ram'
                      ? 'No dedicated GPU found: models run on the CPU from system memory'
                      : status.vram.memory_source === 'apple-unified'
                        ? 'Shared between the system and the GPU'
                        : 'Total memory on the graphics card'}
                  </p>
                </div>

                {/* 2. Model Occupied VRAM */}
                <div className="rounded-lg border border-sky-500/30 bg-sky-950/30 p-3 space-y-1">
                  <span className="text-[0.625rem] uppercase font-bold text-sky-300 tracking-wider">
                    Model Occupied VRAM
                  </span>
                  <div className="flex items-baseline gap-1.5">
                    <span className="text-lg font-bold font-mono text-sky-200">
                      {status.vram.model_loaded && status.vram.model_vram_gb != null && status.vram.model_vram_gb > 0
                        ? `${status.vram.model_vram_gb.toFixed(2)} GB`
                        : `~${status.vram.model_approx_gb?.toFixed(1) || '0.0'} GB`}
                    </span>
                    <span className="text-[0.625rem] font-mono text-sky-400">
                      {status.vram.model_loaded ? 'Active in GPU' : 'Standby footprint'}
                    </span>
                  </div>
                  <p className="text-[0.625rem] text-slate-400">
                    {status.vram.model_loaded
                      ? `Exact VRAM occupied by ${status.vram.model_name || user.grading_model || 'active model'}`
                      : `Expected footprint when ${status.vram.model_name || user.grading_model || 'active model'} generates`}
                  </p>
                </div>

                {/* 3. Available VRAM */}
                <div className="rounded-lg border border-emerald-500/30 bg-emerald-950/20 p-3 space-y-1">
                  <span className="text-[0.625rem] uppercase font-bold text-emerald-300 tracking-wider">
                    Available now
                  </span>
                  {status.vram.usage_measured === false ? (
                    <>
                      {/* The server has no way to read live usage here. It used to
                          report half of capacity as "used" and half as "free",
                          which looked like a measurement and was not one. */}
                      <div className="text-lg font-bold font-mono text-slate-300">Unknown</div>
                      <p className="text-[0.625rem] text-slate-400">
                        Live usage cannot be read on this hardware
                      </p>
                    </>
                  ) : (
                    <>
                      <div className="flex items-baseline gap-1.5">
                        <span className="text-lg font-bold font-mono text-emerald-200">
                          {status.vram.available_gb != null ? `${status.vram.available_gb.toFixed(2)} GB` : 'N/A'}
                        </span>
                        <span className="text-[0.625rem] text-slate-400 font-mono">
                          ({status.vram.available_mb != null ? `${Math.round(status.vram.available_mb)} MB` : ''})
                        </span>
                      </div>
                      <p className="text-[0.625rem] text-slate-400">Free right now</p>
                    </>
                  )}
                </div>
              </div>

              {/* Segmented Capacity Bar */}
              {status.vram.capacity_gb && status.vram.capacity_gb > 0 && (
                <div className="space-y-1 pt-1">
                  <div className="h-2.5 w-full bg-slate-800 rounded-full overflow-hidden flex">
                    {/* Model Occupied */}
                    <div
                      className="bg-sky-400 transition-all duration-300"
                      style={{
                        width: `${Math.min(
                          100,
                          (((status.vram.model_loaded ? status.vram.model_vram_gb || 0 : 0) /
                            status.vram.capacity_gb) *
                            100)
                        )}%`,
                      }}
                      title={`Model VRAM: ${(status.vram.model_vram_gb || 0).toFixed(2)} GB`}
                    />
                    {/* Other Used */}
                    <div
                      className="bg-slate-600 transition-all duration-300"
                      style={{
                        width: `${Math.min(
                          100,
                          (Math.max(
                            0,
                            (status.vram.usage_measured === false ? 0 : status.vram.used_gb || 0) -
                              (status.vram.model_loaded ? status.vram.model_vram_gb || 0 : 0)
                          ) /
                            status.vram.capacity_gb) *
                            100
                        )}%`,
                      }}
                      title="Other system usage"
                    />
                  </div>
                  <div className="flex items-center justify-between text-[0.625rem] text-slate-400 font-mono">
                    <span>0 GB</span>
                    <span>
                      {status.vram.usage_measured === false
                        ? status.vram.model_loaded
                          ? `Model: ${status.vram.model_vram_gb?.toFixed(2)} GB · other usage not measurable`
                          : 'Usage not measurable on this hardware'
                        : status.vram.model_loaded
                          ? `Model: ${status.vram.model_vram_gb?.toFixed(2)} GB · System: ${status.vram.used_gb?.toFixed(2)} GB`
                          : `Used: ${status.vram.used_gb?.toFixed(2)} GB · Free: ${status.vram.available_gb?.toFixed(2)} GB`}
                    </span>
                    <span>Capacity: {status.vram.capacity_gb.toFixed(1)} GB</span>
                  </div>
                </div>
              )}
            </div>
          )}

          {/* Supported Local Quantized Models — 3 Approved Archetypes */}
          <div className="mt-4 pt-3 border-t border-ink-line space-y-2.5">
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold text-slate-300">
                Approved Model Archetypes:
              </span>
              <span className="text-[0.625rem] text-slate-400">
                Select only among these 3 models
              </span>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-3.5">
              {ALLOWED_QWEN_CODER_MODELS.map((opt) => {
                const isInstalled = status?.models_installed?.some(
                  (im) => im.toLowerCase() === opt.id.toLowerCase() || im.toLowerCase().startsWith(opt.id.toLowerCase())
                )
                const isActive = (user.grading_model || 'qwen2.5-coder:7b') === opt.id
                const isRecommended = hardware?.recommended_size.toLowerCase() === opt.size.toLowerCase()
                return (
                  <div
                    key={opt.id}
                    className={`rounded-xl border p-3.5 space-y-2 transition text-xs flex flex-col justify-between ${
                      isActive
                        ? 'border-sky-500/70 bg-sky-950/40 ring-1 ring-sky-500/30'
                        : isRecommended
                        ? 'border-emerald-500/40 bg-emerald-950/20'
                        : isInstalled
                        ? 'border-slate-800 bg-slate-900/50'
                        : 'border-slate-800/60 bg-slate-900/20 text-slate-400'
                    }`}
                  >
                    <div className="space-y-1.5">
                      <div className="flex items-start justify-between gap-1.5">
                        <div>
                          <h4 className="font-bold text-sm text-slate-100">{opt.name}</h4>
                          <p className="text-[0.6875rem] font-semibold italic text-sky-300 tracking-tight">
                            {opt.archetype}
                          </p>
                        </div>
                        <span className="chip text-[0.625rem] font-mono shrink-0 px-1.5 py-0.5 border-slate-700 bg-slate-800/80 text-slate-300">
                          {opt.vramApprox}
                        </span>
                      </div>

                      {isRecommended && (
                        <div className="text-[0.625rem] font-bold text-emerald-300 flex items-center gap-1">
                          <span className="w-1.5 h-1.5 rounded-full bg-emerald-400" />
                          <span>Recommended for your hardware</span>
                        </div>
                      )}

                      <p className="text-[0.6875rem] text-slate-400 leading-relaxed">{opt.desc}</p>
                    </div>

                    <div className="pt-2.5 border-t border-slate-800/80 flex items-center justify-between text-[0.6875rem]">
                      {isInstalled ? (
                        <div className="flex items-center gap-2">
                          <span className="text-emerald-400 flex items-center gap-1 font-medium">
                            <svg className="w-3 h-3" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3">
                              <polyline points="20 6 9 17 4 12" />
                            </svg>
                            <span>Installed</span>
                          </span>
                          {!isActive && (
                            <button
                              type="button"
                              onClick={async () => {
                                await api.updateMe({ grading_model: opt.id })
                                await onChange()
                                void checkStatus()
                              }}
                              className="text-[0.6875rem] font-medium text-sky-400 hover:text-sky-300 underline cursor-pointer"
                            >
                              Activate
                            </button>
                          )}
                        </div>
                      ) : (
                        <button
                          type="button"
                          onClick={() => void navigator.clipboard.writeText(`ollama pull ${opt.id}`)}
                          className="text-[0.625rem] text-sky-400 hover:text-sky-200 underline font-mono cursor-pointer"
                          title={`Copy: ollama pull ${opt.id}`}
                        >
                          Copy pull command
                        </button>
                      )}
                      {isActive && (
                        <span className="chip text-[0.625rem] font-bold border-sky-500/50 text-sky-300 bg-sky-500/10">
                          Active
                        </span>
                      )}
                    </div>
                  </div>
                )
              })}
            </div>
          </div>

          {canUseAntigravity && (
            <div className="mt-4 pt-3 border-t border-ink-line space-y-2.5">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <div className="flex items-center gap-2">
                  <span className="text-xs font-semibold text-slate-200">
                    Antigravity Subscription Models (No API Key)
                  </span>
                  <span
                    className={`chip text-[0.625rem] font-semibold ${
                      agyInfo?.connected
                        ? 'border-emerald-500/40 text-emerald-300 bg-emerald-500/10'
                        : agyInfo?.installed
                        ? 'border-amber-500/40 text-amber-300 bg-amber-500/10'
                        : 'border-slate-700 text-slate-400 bg-slate-900/60'
                    }`}
                  >
                    {agyInfo?.connected
                      ? 'agy CLI Ready'
                      : agyInfo?.installed
                      ? 'Sign in with agy'
                      : 'agy CLI Not Detected'}
                  </span>
                </div>
                <span className="text-[0.625rem] text-slate-400">
                  Runs via <code className="font-mono text-slate-300">agy -p</code> using your Antigravity plan quota
                </span>
              </div>

              {agyInfo?.error && !agyInfo.connected && (
                <p className="text-[0.6875rem] text-amber-300/90 bg-amber-950/30 border border-amber-500/30 rounded-lg px-3 py-2">
                  {agyInfo.error}
                </p>
              )}

              <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                {ANTIGRAVITY_MODELS.map((opt) => {
                  const isActive = (user.grading_model || '').toLowerCase() === opt.id.toLowerCase()
                  const isDiscovered =
                    agyAvailableModels.length === 0 || agyAvailableModels.includes(opt.id)
                  return (
                    <div
                      key={opt.id}
                      className={`rounded-xl border p-3.5 space-y-2 transition text-xs flex flex-col justify-between ${
                        isActive
                          ? 'border-indigo-400/70 bg-indigo-950/40 ring-1 ring-indigo-500/30'
                          : isDiscovered
                          ? 'border-slate-800 bg-slate-900/50'
                          : 'border-slate-800/60 bg-slate-900/20 text-slate-400'
                      }`}
                    >
                      <div className="space-y-1.5">
                        <div className="flex items-start justify-between gap-1.5">
                          <div>
                            <h4 className="font-bold text-sm text-slate-100">{opt.name}</h4>
                            <p className="text-[0.6875rem] font-semibold italic text-indigo-300 tracking-tight">
                              {opt.tier}
                            </p>
                          </div>
                          <span className="chip text-[0.625rem] font-mono shrink-0 px-1.5 py-0.5 border-indigo-500/30 bg-indigo-950/50 text-indigo-200">
                            Subscription
                          </span>
                        </div>
                        <p className="text-[0.6875rem] text-slate-400 leading-relaxed">{opt.desc}</p>
                      </div>

                      <div className="pt-2.5 border-t border-slate-800/80 flex items-center justify-between text-[0.6875rem]">
                        <span
                          className={`font-medium ${
                            agyInfo?.connected ? 'text-emerald-400' : 'text-slate-400'
                          }`}
                        >
                          {agyInfo?.connected ? 'Available' : 'Requires agy sign-in'}
                        </span>
                        {isActive ? (
                          <span className="chip text-[0.625rem] font-bold border-indigo-400/50 text-indigo-200 bg-indigo-500/15">
                            Active
                          </span>
                        ) : (
                          <button
                            type="button"
                            onClick={() => void activateModel(opt.id)}
                            className="text-[0.6875rem] font-medium text-indigo-300 hover:text-indigo-200 underline cursor-pointer"
                          >
                            Activate
                          </button>
                        )}
                      </div>
                    </div>
                  )
                })}
              </div>
            </div>
          )}
        </div>

        {/* Feature Toggles */}
        <div className="space-y-3 rounded-lg border border-ink-line bg-ink/40 p-4">
          <label className="flex cursor-pointer items-start gap-3">
            <input
              type="checkbox"
              checked={user.llm_grading_consent}
              className="mt-1"
              onChange={async (e) => {
                await api.updateMe({ llm_grading_consent: e.target.checked })
                await onChange()
              }}
            />
            <span className="text-sm">
              <span className="font-medium text-slate-200">Enable AI solution grading &amp; tutoring</span>
              <span className="mt-0.5 block text-xs text-slate-400">
                Powers answer grading, Socratic line hints, Lexicon lookups, Lessons, Leech remediation, Code Lab, and Card Generation using {canUseAntigravity ? 'your active Antigravity Subscription or local Ollama model' : 'your local Ollama model'}.
              </span>
            </span>
          </label>

          <label className="flex cursor-pointer items-start gap-3">
            <input
              type="checkbox"
              checked={user.leech_remediation_opt_in}
              className="mt-1"
              onChange={async (e) => {
                await api.updateMe({ leech_remediation_opt_in: e.target.checked })
                await onChange()
              }}
            />
            <span className="text-sm">
              <span className="font-medium text-slate-200">Automatic Leech card remediation diagnosis</span>
              <span className="mt-0.5 block text-xs text-slate-400">
                When you repeatedly struggle with a card, your active grader analyzes errors and proposes clearer reformulated cards.
              </span>
            </span>
          </label>
        </div>

        <ErrorNote error={error} />
      </div>
    </Section>
  )
}

function MemoryChampionPanel({ user, onChange }: { user: User; onChange: () => Promise<void> }) {
  const [readiness, setReadiness] = useState<EventReadiness | null>(null)
  const [loadingReadiness, setLoadingReadiness] = useState(false)

  const save = async (patch: Partial<User>) => {
    await api.updateMe(patch)
    await onChange()
    void fetchReadiness()
  }

  const fetchReadiness = useCallback(() => {
    setLoadingReadiness(true)
    api
      .eventReadiness()
      .then(setReadiness)
      .catch(() => setReadiness(null))
      .finally(() => setLoadingReadiness(false))
  }, [])

  useEffect(() => {
    fetchReadiness()
  }, [fetchReadiness, user.target_event_date])

  const thresholdSec = ((user.automaticity_threshold_ms ?? 3000) / 1000).toFixed(1)
  const eventDateStr = user.target_event_date
    ? new Date(user.target_event_date).toISOString().slice(0, 10)
    : ''

  return (
    <Section
      title="Recall & Target Date"
      description="Reaction latency tracking and target event scheduling."
    >
      <div className="space-y-6">
        {/* Automaticity Latency Threshold (§Feature 4) */}
        <div>
          <Field
            label={`Reaction Threshold (${thresholdSec}s)`}
            hint="Target response pace. Informational only — does not affect grading."
          >
            <div className="flex items-center gap-4 mt-2">
              <input
                type="range"
                min={500}
                max={10000}
                step={250}
                defaultValue={user.automaticity_threshold_ms ?? 3000}
                className="flex-1"
                onMouseUp={(e) =>
                  save({ automaticity_threshold_ms: Number((e.target as HTMLInputElement).value) })
                }
              />
              <span className="w-16 font-mono text-sm font-semibold text-amber-300 text-right">
                {thresholdSec}s
              </span>
            </div>
          </Field>
        </div>

        {/* Event Horizon Peak Taper (§Feature 6) */}
        <div className="border-t border-ink-line pt-4 space-y-4">
          <p className="text-xs font-semibold uppercase tracking-wider text-slate-400">
            Target Event Horizon (Competition / Exam Taper)
          </p>

          <div className="grid gap-4 sm:grid-cols-3">
            <Field label="Event Title" hint="e.g. Memory Championship, USMLE, Bar Exam">
              <input
                type="text"
                className="input"
                defaultValue={user.target_event_title ?? ''}
                placeholder="Target Competition / Exam"
                onBlur={(e) => save({ target_event_title: e.target.value.trim() || null })}
              />
            </Field>

            <Field label="Target Event Date" hint="When intervals compress for peak recall">
              <input
                type="date"
                className="input"
                defaultValue={eventDateStr}
                onChange={(e) => {
                  const val = e.target.value
                  save({ target_event_date: val ? new Date(val).toISOString() : null })
                }}
              />
            </Field>

            <Field label="Peak Retention Target" hint="Target retention on event day (e.g. 0.95)">
              <input
                type="number"
                step={0.01}
                min={0.7}
                max={0.99}
                className="input"
                defaultValue={user.peak_retention_target ?? 0.95}
                onBlur={(e) => save({ peak_retention_target: Number(e.target.value) })}
              />
            </Field>
          </div>

          {/* Live Event Readiness Telemetry Card */}
          {loadingReadiness ? (
            <p className="text-xs text-slate-500 italic">Calculating event readiness telemetry…</p>
          ) : readiness?.is_active ? (
            <div className="rounded-xl border border-sky-500/30 bg-sky-950/20 p-4 space-y-3">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <div className="flex items-center gap-2">
                  <span className="inline-block h-2.5 w-2.5 rounded-full bg-emerald-400 animate-pulse" />
                  <span className="text-xs font-bold text-sky-200 uppercase tracking-wide">
                    {readiness.target_event_title || 'Active Target Event'}
                  </span>
                </div>
                <span className="chip border-sky-500/40 text-sky-300 font-semibold">
                  {readiness.status_label}
                </span>
              </div>

              <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
                <div className="rounded-lg border border-ink-line/60 bg-ink/60 p-2.5 text-center">
                  <p className="text-[0.625rem] text-slate-400">Countdown</p>
                  <p className="font-mono text-xl font-bold text-amber-300">
                    {readiness.days_remaining}d
                  </p>
                  <p className="text-[0.5625rem] text-slate-500">until event</p>
                </div>

                <div className="rounded-lg border border-ink-line/60 bg-ink/60 p-2.5 text-center">
                  <p className="text-[0.625rem] text-slate-400">Projected Retention</p>
                  <p className="font-mono text-xl font-bold text-emerald-400">
                    {Math.round(readiness.projected_retention * 100)}%
                  </p>
                  <p className="text-[0.5625rem] text-slate-500">at event horizon</p>
                </div>

                <div className="rounded-lg border border-ink-line/60 bg-ink/60 p-2.5 text-center">
                  <p className="text-[0.625rem] text-slate-400">Unstable Cards</p>
                  <p className="font-mono text-xl font-bold text-rose-300">
                    {readiness.unstable_cards_count}
                  </p>
                  <p className="text-[0.5625rem] text-slate-500">stability &lt; 7d</p>
                </div>

                <div className="rounded-lg border border-ink-line/60 bg-ink/60 p-2.5 text-center">
                  <p className="text-[0.625rem] text-slate-400">Required Pace</p>
                  <p className="font-mono text-xl font-bold text-sky-300">
                    ~{readiness.estimated_daily_reviews_needed}
                  </p>
                  <p className="text-[0.5625rem] text-slate-500">reviews / day</p>
                </div>
              </div>
            </div>
          ) : null}
        </div>
      </div>
    </Section>
  )
}

function SchedulingPanel({ user, onChange }: { user: User; onChange: () => Promise<void> }) {
  const [optimizeMsg, setOptimizeMsg] = useState<string | null>(null)

  const save = async (patch: Partial<User>) => {
    await api.updateMe(patch)
    await onChange()
  }

  return (
    <Section
      title="Scheduling & load"
      description="FSRS targets a retention rate rather than a fixed interval table. The caps below are what stop a missed week from turning into an 800-card wall."
    >
      <div className="grid gap-4 sm:grid-cols-2">
        <Field label="Desired retention" hint="0.90 = you want to recall 90% of due cards.">
          <input
            type="number"
            step={0.01}
            min={0.7}
            max={0.99}
            className="input"
            defaultValue={user.desired_retention}
            onBlur={(e) => save({ desired_retention: Number(e.target.value) })}
          />
        </Field>
        <Field label="Session budget (minutes)" hint="The queue fills this, rather than dumping a list.">
          <input
            type="number"
            min={1}
            max={600}
            className="input"
            defaultValue={user.queue_time_budget_minutes}
            onBlur={(e) => save({ queue_time_budget_minutes: Number(e.target.value) })}
          />
        </Field>
        <Field label="New cards / day">
          <input
            type="number"
            min={0}
            className="input"
            defaultValue={user.daily_new_limit}
            onBlur={(e) => save({ daily_new_limit: Number(e.target.value) })}
          />
        </Field>
        <Field label="Max reviews / day">
          <input
            type="number"
            min={0}
            className="input"
            defaultValue={user.daily_review_limit}
            onBlur={(e) => save({ daily_review_limit: Number(e.target.value) })}
          />
        </Field>
        <Field label="Spread a backlog over (days)" hint="Missed days get smoothed across this window.">
          <input
            type="number"
            min={1}
            max={60}
            className="input"
            defaultValue={user.backlog_spread_days}
            onBlur={(e) => save({ backlog_spread_days: Number(e.target.value) })}
          />
        </Field>
        <Field label="Leech threshold (lapses)">
          <input
            type="number"
            min={2}
            max={100}
            className="input"
            defaultValue={user.leech_threshold}
            onBlur={(e) => save({ leech_threshold: Number(e.target.value) })}
          />
        </Field>
        <Field label="Time zone" hint="Daily limits and streaks reset at 4 am here. IANA name, e.g. America/Vancouver.">
          <input
            type="text"
            className="input"
            defaultValue={user.timezone ?? ''}
            onBlur={(e) => {
              const zone = e.target.value.trim()
              if (zone && zone !== user.timezone) void save({ timezone: zone })
            }}
          />
        </Field>
      </div>

      <div className="mt-5 border-t border-ink-line pt-4">
        <p className="text-xs text-slate-500">
          FSRS parameters:{' '}
          {user.fsrs_optimized_at
            ? `personalized ${new Date(user.fsrs_optimized_at).toLocaleDateString()}`
            : 'using defaults until you have enough review history'}
        </p>
        <button
          className="btn mt-2"
          onClick={async () => {
            const r = await api.optimize()
            setOptimizeMsg(
              r.optimized
                ? 'Parameters refit from your review history.'
                : (r.reason ?? 'Not enough history yet.'),
            )
            await onChange()
          }}
        >
          Refit parameters now
        </button>
        {optimizeMsg && <p className="mt-2 text-xs text-slate-400">{optimizeMsg}</p>}
      </div>
    </Section>
  )
}

function QueuePanel({ cfg, onChange }: { cfg: QueueConfig; onChange: () => Promise<void> }) {
  const save = async (patch: Partial<QueueConfig>) => {
    await api.updateQueueConfig(patch)
    await onChange()
  }
  const total = cfg.review_weight + cfg.new_weight + cfg.ir_weight || 1

  return (
    <Section
      title="Queue mix"
      description="How the session budget is split between due reviews, new cards, and reading. Ship-with-conservative-defaults; tune from real use."
    >
      <div className="space-y-4">
        {(
          [
            ['review_weight', 'Due reviews'],
            ['new_weight', 'New cards'],
            ['ir_weight', 'Reading'],
          ] as const
        ).map(([key, label]) => (
          <label key={key} className="flex items-center gap-4 text-sm">
            <span className="w-28 text-slate-400">{label}</span>
            <input
              type="range"
              min={0}
              max={1}
              step={0.05}
              defaultValue={cfg[key]}
              className="flex-1"
              onMouseUp={(e) => save({ [key]: Number((e.target as HTMLInputElement).value) })}
            />
            <span className="w-12 text-right text-xs tabular-nums text-slate-500">
              {Math.round((cfg[key] / total) * 100)}%
            </span>
          </label>
        ))}

        <div className="grid gap-4 border-t border-ink-line pt-4 sm:grid-cols-2">
          <Field label="Seconds per review" hint="Auto-refined from your real timings after 30 reviews.">
            <input
              type="number"
              min={1}
              className="input"
              defaultValue={cfg.seconds_per_review}
              onBlur={(e) => save({ seconds_per_review: Number(e.target.value) })}
            />
          </Field>
          <Field label="Seconds per extract">
            <input
              type="number"
              min={1}
              className="input"
              defaultValue={cfg.seconds_per_ir_extract}
              onBlur={(e) => save({ seconds_per_ir_extract: Number(e.target.value) })}
            />
          </Field>
        </div>
      </div>
    </Section>
  )
}

function MobileCompanionPanel({ user }: { user: User }) {
  const [status, setStatus] = useState<SyncStatus | null>(null)
  const [copied, setCopied] = useState(false)
  const [error, setError] = useState<unknown>(null)

  const loadStatus = useCallback(async () => {
    try {
      const s = await api.syncStatus()
      setStatus(s)
    } catch (err) {
      setError(err)
    }
  }, [])

  useEffect(() => {
    void loadStatus()
    const interval = setInterval(loadStatus, 8000)
    return () => clearInterval(interval)
  }, [loadStatus])

  // The QR carries a token made for the phone: scoped to reviewing, unable to
  // run code on this computer, and revoked by "sign out everywhere". It used
  // to carry this browser's own session token, which made a photo of the
  // screen a full login. Minted only when asked for, shown only until hidden.
  const [pairingToken, setPairingToken] = useState<string | null>(null)
  const [minting, setMinting] = useState(false)

  const showPairingCode = async () => {
    setMinting(true)
    setError(null)
    try {
      const { access_token } = await api.pairingToken()
      setPairingToken(access_token)
    } catch (err) {
      setError(err)
    } finally {
      setMinting(false)
    }
  }

  const pairingData =
    status && pairingToken
      ? JSON.stringify({
          server_url: status.pairing_url,
          token: pairingToken,
          email: user.email,
        })
      : ''

  const copyUrl = () => {
    if (status?.pairing_url) {
      void navigator.clipboard.writeText(status.pairing_url)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    }
  }

  return (
    <Section
      title="Mobile Companion & Real-Time Sync"
      description="Connect your iPhone or Android app to review cards on the go with real-time bidirectional synchronization."
    >
      <ErrorNote error={error} />
      <div className="flex flex-col gap-6 md:flex-row md:items-center">
        {pairingData ? (
          <div className="flex flex-col items-center gap-2 rounded-xl border border-ink-line/80 bg-white p-4 shadow-sm">
            <QRCodeSVG value={pairingData} size={170} level="M" title="Pairing code for the mobile app" />
            <span className="text-[0.6875rem] font-semibold tracking-wide text-slate-700">
              Scan with Mobile App
            </span>
            <button
              type="button"
              className="text-[0.6875rem] font-medium text-slate-600 underline hover:text-slate-900"
              onClick={() => setPairingToken(null)}
            >
              Hide code
            </button>
          </div>
        ) : (
          <div className="flex h-44 w-44 shrink-0 flex-col items-center justify-center gap-2 rounded-xl border border-ink-line/60 bg-ink/40 p-3 text-center">
            {status ? (
              <>
                <button
                  type="button"
                  className="btn btn-primary text-xs"
                  disabled={minting}
                  onClick={() => void showPairingCode()}
                >
                  {minting ? 'Preparing…' : 'Show pairing code'}
                </button>
                <span className="text-[0.6875rem] leading-snug text-slate-400">
                  Anyone who scans it can review your cards. Show it only to your own phone.
                </span>
              </>
            ) : (
              <Spinner />
            )}
          </div>
        )}

        <div className="flex-1 space-y-4">
          <div className="flex items-center gap-2">
            <span
              className={`inline-block h-3 w-3 rounded-full ${
                status && status.user_connections > 0
                  ? 'bg-emerald-400 animate-pulse'
                  : 'bg-slate-500'
              }`}
            />
            <span className="text-sm font-medium text-slate-200">
              {status && status.user_connections > 0
                ? `${status.user_connections} Mobile Device(s) Connected in Real Time`
                : 'Ready for Connection'}
            </span>
          </div>

          <div className="space-y-1">
            <label
              htmlFor="pairing-url"
              className="text-xs font-semibold uppercase tracking-wider text-slate-400"
            >
              Local Network Address (Wi-Fi)
            </label>
            <div className="flex flex-wrap items-center gap-2">
              <input
                id="pairing-url"
                type="text"
                readOnly
                value={status?.pairing_url || 'Detecting local IP...'}
                className="input min-w-0 flex-1 font-mono text-sm sm:max-w-sm"
              />
              <button
                type="button"
                className="btn btn-secondary whitespace-nowrap text-xs"
                onClick={copyUrl}
              >
                {copied ? '✓ Copied' : 'Copy URL'}
              </button>
            </div>
            <p className="text-[0.6875rem] text-slate-500">
              Your phone must be connected to the same Wi-Fi network as this computer, or connected via VPN / Tailscale.
            </p>
          </div>

          <div className="rounded-lg border border-sky-900/30 bg-sky-950/20 p-3 text-xs text-sky-300">
            <p className="font-semibold text-sky-200">How to Pair:</p>
            <ol className="mt-1 list-decimal space-y-1 pl-4 text-sky-300/90">
              <li>Open the Ars Memoriae mobile app on iOS or Android.</li>
              <li>Tap <strong>Scan QR</strong> and aim your phone's camera at the QR code.</li>
              <li>Your device authenticates and begins streaming cards and syncing reviews!</li>
            </ol>
            <p className="mt-2 text-sky-300/80">
              A paired phone can review but cannot run code on this computer. To unpair every
              device, use <strong>Sign out everywhere else</strong> under Account.
            </p>
          </div>
        </div>
      </div>
    </Section>
  )
}

function DataPanel() {
  const [busy, setBusy] = useState(false)
  return (
    <Section
      title="Your data"
      description="Full-fidelity export, on demand, hosted or self-hosted. No lock-in mechanism exists here."
    >
      <div className="flex flex-wrap gap-2">
        <button
          className="btn"
          disabled={busy}
          onClick={async () => {
            setBusy(true)
            try {
              await api.downloadExport('/api/export', 'memorization-export.json')
            } finally {
              setBusy(false)
            }
          }}
        >
          Download full export (JSON)
        </button>
        <button
          className="btn"
          disabled={busy}
          onClick={async () => {
            setBusy(true)
            try {
              await api.downloadExport('/api/export/review-logs.csv', 'review-logs.csv')
            } finally {
              setBusy(false)
            }
          }}
        >
          Download review logs (CSV)
        </button>
      </div>
      <p className="mt-3 text-xs text-slate-600">
        The export contains decks, notes, cards with live FSRS state, every review log, and your
        reading sources.
      </p>
    </Section>
  )
}

function Field({
  label,
  hint,
  children,
}: {
  label: string
  hint?: string
  children: React.ReactNode
}) {
  // A <label> wrapping its control: clicking the caption focuses the field,
  // and a screen reader announces the caption with it. As a <p> beside the
  // control, most fields on this page had no name at all.
  return (
    <label className="block">
      <span className="label">{label}</span>
      {children}
      {hint && <span className="mt-1 block text-xs text-slate-600">{hint}</span>}
    </label>
  )
}

function TypographyPanel() {
  const { fontSize, setFontSize } = useTheme()

  const sizeLabels: Record<FontSize, { label: string; tag: string }> = {
    10: { label: '10px', tag: 'Tiny / Dense' },
    12: { label: '12px', tag: 'Compact' },
    14: { label: '14px', tag: 'Medium' },
    16: { label: '16px', tag: 'Default' },
    18: { label: '18px', tag: 'Large' },
    20: { label: '20px', tag: 'Extra Large' },
  }

  return (
    <Section
      title="Typography"
      description="Base font size (10px to 20px)."
    >
      <div className="space-y-4">
        {/* Font size pill selector */}
        <div className="flex flex-wrap items-center gap-2.5">
          {FONT_SIZES.map((size) => {
            const isSelected = fontSize === size
            const meta = sizeLabels[size]
            return (
              <button
                key={size}
                type="button"
                onClick={() => setFontSize(size)}
                className={`flex flex-col items-center justify-center rounded-xl border px-3.5 py-2.5 transition cursor-pointer min-w-[5.25rem] ${
                  isSelected
                    ? 'border-sky-500 bg-sky-950/50 text-sky-200 ring-2 ring-sky-500/50 shadow-md'
                    : 'border-ink-line bg-ink/70 text-slate-300 hover:border-slate-600 hover:bg-ink'
                }`}
              >
                <span className="font-bold font-mono text-sm">
                  {meta.label}
                </span>
                <span className={`text-[0.625rem] mt-0.5 ${isSelected ? 'text-sky-300 font-semibold' : 'text-slate-500'}`}>
                  {meta.tag}
                </span>
              </button>
            )
          })}

          {fontSize !== 16 && (
            <button
              type="button"
              onClick={() => setFontSize(16)}
              className="btn text-xs py-2 px-3 text-slate-400 hover:text-slate-200"
              title="Reset font size to 16px default"
            >
              Reset (16px)
            </button>
          )}
        </div>

        {/* Live Typography Preview Box */}
        <div className="rounded-xl border border-ink-line bg-ink-soft/50 p-4 space-y-2">
          <div className="flex items-center justify-between text-xs text-slate-400 border-b border-ink-line/50 pb-2">
            <span className="font-semibold uppercase tracking-wider text-[0.6875rem] text-slate-300">
              Preview ({fontSize}px)
            </span>
            <span className="font-mono text-sky-400 text-[0.6875rem]">font-family: 'Verdana', sans-serif</span>
          </div>

          <div className="space-y-1.5 pt-1">
            <h3 className="font-bold text-slate-100" style={{ fontSize: `${fontSize * 1.15}px` }}>
              Active Recall & FSRS Scheduling
            </h3>
            <p className="text-slate-300 leading-relaxed" style={{ fontSize: `${fontSize}px` }}>
              Every function has a contract. Type your answer to verify understanding with local AI reasoning and similarity checking.
            </p>
            <div className="pt-1">
              <code className="font-mono bg-ink px-2 py-0.5 rounded border border-ink-line text-emerald-300 text-xs inline-block">
                def memory_consolidation(stability: float, difficulty: float) -&gt; float:
              </code>
            </div>
          </div>
        </div>
      </div>
    </Section>
  )
}

function DisplayFocusPanel() {
  const { isZenMode, toggleZenMode } = useFullscreen()

  return (
    <Section
      title="Display & Fullscreen"
      description="Distraction-free study and shortcuts."
    >
      <div className="flex flex-wrap items-center gap-4">
        <FullscreenButton />
        <button
          type="button"
          onClick={toggleZenMode}
          className={`btn ${isZenMode ? 'btn-primary' : 'btn-secondary'}`}
        >
          {isZenMode ? 'Zen Mode (Active)' : 'Zen Mode'}
        </button>
      </div>

      <div className="mt-4 rounded-xl border border-ink-line/60 bg-ink-soft/40 p-3.5 space-y-2 text-xs">
        <p className="font-semibold text-slate-300">Keyboard Shortcuts:</p>
        <ul className="space-y-1.5 text-slate-400">
          <li className="flex items-center gap-2">
            <kbd className="rounded bg-slate-800 px-1.5 py-0.5 text-sky-300 font-mono text-[0.6875rem] border border-slate-700">
              F
            </kbd>
            <span>Toggle fullscreen mode</span>
          </li>
          <li className="flex items-center gap-2">
            <kbd className="rounded bg-slate-800 px-1.5 py-0.5 text-sky-300 font-mono text-[0.6875rem] border border-slate-700">
              Ctrl+Shift+F
            </kbd>
            <span>Universal fullscreen toggle</span>
          </li>
          <li className="flex items-center gap-2">
            <kbd className="rounded bg-slate-800 px-1.5 py-0.5 text-sky-300 font-mono text-[0.6875rem] border border-slate-700">
              Esc
            </kbd>
            <span>Exit fullscreen or Zen mode</span>
          </li>
        </ul>
      </div>
    </Section>
  )
}

function TutorialPanel({
  user,
  onLaunchTutorial,
  onChange,
}: {
  user: User
  onLaunchTutorial: (mode: 'prompt' | 'tour', type: 'extensive' | 'brief') => void
  onChange: () => Promise<void>
}) {
  const [resetting, setResetting] = useState(false)
  const [error, setError] = useState<unknown>(null)

  const toggleCompletion = async () => {
    setResetting(true)
    setError(null)
    try {
      const nextStatus = !user.tutorial_completed
      await api.updateMe({ tutorial_completed: nextStatus })
      if (!nextStatus) {
        storage.remove('tutorial_prompt_dismissed')
        storage.remove('prompt_new_user_tutorial')
      }
      await onChange()
    } catch (err) {
      setError(err)
    } finally {
      setResetting(false)
    }
  }

  return (
    <Section
      title="Tutorial"
      description="Guided onboarding and core concepts."
    >
      <div className="space-y-4">
        {/* Status Header Bar */}
        <div className="rounded-xl border border-ink-line bg-ink/70 p-4 flex flex-wrap items-center justify-between gap-3">
          <div className="flex items-center gap-3">
            <div>
              <div className="flex items-center gap-2">
                <span className="text-xs font-bold text-slate-100">Tutorial Status</span>
                {user.tutorial_completed ? (
                  <span className="chip border-emerald-500/40 text-emerald-300 bg-emerald-500/10 font-semibold text-[0.625rem]">
                    Completed
                  </span>
                ) : (
                  <span className="chip border-amber-500/40 text-amber-300 bg-amber-500/10 font-semibold text-[0.625rem]">
                    Incomplete
                  </span>
                )}
              </div>
              <p className="text-[0.6875rem] text-slate-400 mt-0.5">
                {user.tutorial_completed
                  ? 'Tour completed. You can replay either mode below.'
                  : 'Tutorial not yet completed.'}
              </p>
            </div>
          </div>

          <button
            type="button"
            disabled={resetting}
            onClick={() => void toggleCompletion()}
            className="btn text-xs py-1.5 px-3 text-slate-300 hover:text-slate-100"
            title="Toggle tutorial completion status"
          >
            {resetting ? 'Updating…' : user.tutorial_completed ? 'Reset' : 'Mark Done'}
          </button>
        </div>

        {/* Tutorial Mode Selection Cards */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3.5">
          {/* Card A: Brief High-Level Tour */}
          <div className="rounded-xl border border-ink-line bg-ink-soft/50 p-4 flex flex-col justify-between space-y-3 hover:border-sky-500/60 transition">
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2 text-sky-300 font-bold text-xs">
                  <span>Brief Overview</span>
                </div>
                <span className="chip text-[0.625rem] py-0.5 border-sky-500/40 text-sky-300 bg-sky-500/10 font-semibold">
                  1 min
                </span>
              </div>
              <p className="text-[0.6875rem] text-slate-400 leading-relaxed">
                A rapid 3-slide overview of the core principles: Active Recall, Knowledge Trees, and the Priority Queue.
              </p>
              <ul className="text-[0.625rem] text-slate-500 space-y-1 pt-1">
                <li className="flex items-center gap-1.5">
                  <svg className="w-3 h-3 text-sky-400 shrink-0" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                    <polyline points="20 6 9 17 4 12" />
                  </svg>
                  <span>Slide 1: Active Recall & Token Similarity</span>
                </li>
                <li className="flex items-center gap-1.5">
                  <svg className="w-3 h-3 text-sky-400 shrink-0" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                    <polyline points="20 6 9 17 4 12" />
                  </svg>
                  <span>Slide 2: Knowledge Trees</span>
                </li>
                <li className="flex items-center gap-1.5">
                  <svg className="w-3 h-3 text-sky-400 shrink-0" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                    <polyline points="20 6 9 17 4 12" />
                  </svg>
                  <span>Slide 3: Priority Queue</span>
                </li>
              </ul>
            </div>

            <button
              type="button"
              onClick={() => onLaunchTutorial('tour', 'brief')}
              className="btn btn-primary w-full py-2 text-xs font-semibold"
            >
              Start Brief (1 min) →
            </button>
          </div>

          {/* Card B: Extensive Deep-Dive Interactive Tutorial */}
          <div className="rounded-xl border border-emerald-500/30 bg-emerald-950/10 p-4 flex flex-col justify-between space-y-3 hover:border-emerald-500/60 transition">
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2 text-emerald-300 font-bold text-xs">
                  <span>Full Tutorial</span>
                </div>
                <span className="chip text-[0.625rem] py-0.5 border-emerald-500/40 text-emerald-300 bg-emerald-500/10 font-semibold">
                  Recommended · 4 min
                </span>
              </div>
              <p className="text-[0.6875rem] text-slate-400 leading-relaxed">
                Interactive simulation: test-drive the FSRS retention slider, AI grading, and knowledge trees.
              </p>
              <ul className="text-[0.625rem] text-slate-500 space-y-1 pt-1">
                <li className="flex items-center gap-1.5">
                  <svg className="w-3 h-3 text-emerald-400 shrink-0" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                    <polyline points="20 6 9 17 4 12" />
                  </svg>
                  <span>Steps 0–1: FSRS Retention & AI Grader</span>
                </li>
                <li className="flex items-center gap-1.5">
                  <svg className="w-3 h-3 text-emerald-400 shrink-0" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                    <polyline points="20 6 9 17 4 12" />
                  </svg>
                  <span>Steps 2–3: Knowledge Tree & Time Bank</span>
                </li>
                <li className="flex items-center gap-1.5">
                  <svg className="w-3 h-3 text-emerald-400 shrink-0" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                    <polyline points="20 6 9 17 4 12" />
                  </svg>
                  <span>Steps 4–5: Reading & Code Lab</span>
                </li>
              </ul>
            </div>

            <button
              type="button"
              onClick={() => onLaunchTutorial('tour', 'extensive')}
              className="btn btn-primary w-full py-2 text-xs font-semibold bg-emerald-700 hover:bg-emerald-600 border-emerald-500/50 text-white"
            >
              Start Full Tutorial (4 min) →
            </button>
          </div>
        </div>

        {/* Footer Actions */}
        <div className="flex flex-wrap items-center justify-between gap-2 pt-1 text-xs">
          <button
            type="button"
            onClick={() => onLaunchTutorial('prompt', 'extensive')}
            className="text-slate-400 hover:text-sky-300 text-xs transition cursor-pointer flex items-center gap-1.5"
          >
            <span>Open Welcome Modal</span>
          </button>

          <a
            href="/tutorial"
            className="text-slate-400 hover:text-sky-300 text-xs transition flex items-center gap-1"
          >
            <span>Milestone Checklist (/tutorial)</span>
            <span>→</span>
          </a>
        </div>

        <ErrorNote error={error} />
      </div>
    </Section>
  )
}

function NavigationModulesPanel({ user, onChange }: { user: User; onChange: () => Promise<void> }) {
  const [savingPreLeetCode, setSavingPreLeetCode] = useState(false)
  const [savingCodeLab, setSavingCodeLab] = useState(false)
  const [savingThematicContext, setSavingThematicContext] = useState(false)
  const [error, setError] = useState<unknown>(null)

  const togglePreLeetCode = async () => {
    setSavingPreLeetCode(true)
    setError(null)
    try {
      await api.updateMe({ show_pre_leetcode: !user.show_pre_leetcode })
      await onChange()
    } catch (err) {
      setError(err)
    } finally {
      setSavingPreLeetCode(false)
    }
  }

  const toggleCodeLab = async () => {
    setSavingCodeLab(true)
    setError(null)
    try {
      await api.updateMe({ show_code_lab: !user.show_code_lab })
      await onChange()
    } catch (err) {
      setError(err)
    } finally {
      setSavingCodeLab(false)
    }
  }

  const toggleThematicContext = async () => {
    setSavingThematicContext(true)
    setError(null)
    try {
      await api.updateMe({ show_thematic_context: user.show_thematic_context === false ? true : false })
      await onChange()
    } catch (err) {
      setError(err)
    } finally {
      setSavingThematicContext(false)
    }
  }

  return (
    <Section
      title="Navigation & Modules"
      description="Toggle module visibility in the navigation bar."
    >
      <ErrorNote error={error} />
      <div className="space-y-3">
        {/* Pre-LeetCode */}
        <div className="flex items-center justify-between gap-4 rounded-xl border border-ink-line/60 bg-ink-soft/40 p-4">
          <div className="space-y-0.5">
            <div className="flex items-center gap-2">
              <span className="font-semibold text-sm text-slate-200">Pre-LeetCode</span>
              <span
                className={`rounded px-1.5 py-0.5 text-[0.625rem] font-semibold ${
                  user.show_pre_leetcode
                    ? 'bg-emerald-500/15 text-emerald-300 border border-emerald-500/30'
                    : 'bg-slate-700/50 text-slate-400 border border-slate-600/30'
                }`}
              >
                {user.show_pre_leetcode ? 'Visible' : 'Hidden'}
              </span>
            </div>
            <p className="text-xs text-slate-400">
              Python fundamentals, Socratic tutoring, and code execution sandbox.
            </p>
          </div>
          <button
            type="button"
            role="switch"
            aria-checked={Boolean(user.show_pre_leetcode)}
            aria-label="Toggle Pre-LeetCode visibility"
            disabled={savingPreLeetCode}
            onClick={togglePreLeetCode}
            className={`relative inline-flex h-6 w-11 shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out focus:outline-none focus:ring-2 focus:ring-sky-500 focus:ring-offset-2 focus:ring-offset-slate-900 disabled:opacity-50 ${
              user.show_pre_leetcode ? 'bg-sky-500' : 'bg-slate-700'
            }`}
          >
            <span
              aria-hidden="true"
              className={`pointer-events-none inline-block h-5 w-5 transform rounded-full bg-white shadow ring-0 transition duration-200 ease-in-out ${
                user.show_pre_leetcode ? 'translate-x-5' : 'translate-x-0'
              }`}
            />
          </button>
        </div>

        {/* Code Lab */}
        <div className="flex items-center justify-between gap-4 rounded-xl border border-ink-line/60 bg-ink-soft/40 p-4">
          <div className="space-y-0.5">
            <div className="flex items-center gap-2">
              <span className="font-semibold text-sm text-slate-200">Code Lab</span>
              <span
                className={`rounded px-1.5 py-0.5 text-[0.625rem] font-semibold ${
                  user.show_code_lab
                    ? 'bg-emerald-500/15 text-emerald-300 border border-emerald-500/30'
                    : 'bg-slate-700/50 text-slate-400 border border-slate-600/30'
                }`}
              >
                {user.show_code_lab ? 'Visible' : 'Hidden'}
              </span>
            </div>
            <p className="text-xs text-slate-400">
              Targeted coding practice problems, automated test suites, and drills.
            </p>
          </div>
          <button
            type="button"
            role="switch"
            aria-checked={Boolean(user.show_code_lab)}
            aria-label="Toggle Code Lab visibility"
            disabled={savingCodeLab}
            onClick={toggleCodeLab}
            className={`relative inline-flex h-6 w-11 shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out focus:outline-none focus:ring-2 focus:ring-sky-500 focus:ring-offset-2 focus:ring-offset-slate-900 disabled:opacity-50 ${
              user.show_code_lab ? 'bg-sky-500' : 'bg-slate-700'
            }`}
          >
            <span
              aria-hidden="true"
              className={`pointer-events-none inline-block h-5 w-5 transform rounded-full bg-white shadow ring-0 transition duration-200 ease-in-out ${
                user.show_code_lab ? 'translate-x-5' : 'translate-x-0'
              }`}
            />
          </button>
        </div>

        {/* Thematic Context & Documentation */}
        <div className="flex items-center justify-between gap-4 rounded-xl border border-ink-line/60 bg-ink-soft/40 p-4">
          <div className="space-y-0.5">
            <div className="flex items-center gap-2">
              <span className="font-semibold text-sm text-slate-200">Thematic Context</span>
              <span
                className={`rounded px-1.5 py-0.5 text-[0.625rem] font-semibold ${
                  user.show_thematic_context !== false
                    ? 'bg-emerald-500/15 text-emerald-300 border border-emerald-500/30'
                    : 'bg-slate-700/50 text-slate-400 border border-slate-600/30'
                }`}
              >
                {user.show_thematic_context !== false ? 'Visible' : 'Hidden'}
              </span>
            </div>
            <p className="text-xs text-slate-400">
              Display deck documentation, source documents, and theme during reviews.
            </p>
          </div>
          <button
            type="button"
            role="switch"
            aria-checked={user.show_thematic_context !== false}
            aria-label="Toggle Thematic Context visibility"
            disabled={savingThematicContext}
            onClick={toggleThematicContext}
            className={`relative inline-flex h-6 w-11 shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out focus:outline-none focus:ring-2 focus:ring-sky-500 focus:ring-offset-2 focus:ring-offset-slate-900 disabled:opacity-50 ${
              user.show_thematic_context !== false ? 'bg-sky-500' : 'bg-slate-700'
            }`}
          >
            <span
              aria-hidden="true"
              className={`pointer-events-none inline-block h-5 w-5 transform rounded-full bg-white shadow ring-0 transition duration-200 ease-in-out ${
                user.show_thematic_context !== false ? 'translate-x-5' : 'translate-x-0'
              }`}
            />
          </button>
        </div>
      </div>
    </Section>
  )
}

function NeurosciencePanel({ user, onChange }: { user: User; onChange: () => Promise<void> }) {
  const [savingSchema, setSavingSchema] = useState(false)
  const [savingMutation, setSavingMutation] = useState(false)
  const [savingPrediction, setSavingPrediction] = useState(false)
  const [error, setError] = useState<unknown>(null)

  const toggleSchemaCheckpoints = async () => {
    setSavingSchema(true)
    setError(null)
    try {
      await api.updateMe({
        enable_schema_checkpoints: user.enable_schema_checkpoints === false ? true : false,
      })
      await onChange()
    } catch (err) {
      setError(err)
    } finally {
      setSavingSchema(false)
    }
  }

  const togglePromptMutation = async () => {
    setSavingMutation(true)
    setError(null)
    try {
      await api.updateMe({ enable_prompt_mutation: !user.enable_prompt_mutation })
      await onChange()
    } catch (err) {
      setError(err)
    } finally {
      setSavingMutation(false)
    }
  }

  const togglePredictionMode = async () => {
    setSavingPrediction(true)
    setError(null)
    try {
      await api.updateMe({ enable_prediction_mode: !user.enable_prediction_mode })
      await onChange()
    } catch (err) {
      setError(err)
    } finally {
      setSavingPrediction(false)
    }
  }

  return (
    <Section
      title="Neuroscience & Cognitive Optimization"
      description="Biologically grounded memory mechanisms: Neocortical Schema Scaffolding, Engram Reconsolidation, and Prediction Error."
    >
      <div className="space-y-4">
        {/* Schema Checkpoints Toggle */}
        <div className="flex items-center justify-between gap-4 rounded-xl border border-ink-line/60 bg-ink-soft/40 p-4">
          <div className="space-y-0.5">
            <div className="flex items-center gap-2">
              <span className="font-semibold text-sm text-slate-200">
                Schema Checkpoints (mPFC Scaffolding)
              </span>
              <span
                className={`rounded px-1.5 py-0.5 text-[0.625rem] font-semibold ${
                  user.enable_schema_checkpoints !== false
                    ? 'bg-emerald-500/15 text-emerald-300 border border-emerald-500/30'
                    : 'bg-slate-700/50 text-slate-400 border border-slate-600/30'
                }`}
              >
                {user.enable_schema_checkpoints !== false ? 'Enabled' : 'Disabled'}
              </span>
            </div>
            <p className="text-xs text-slate-400">
              Prioritizes foundational mental model cards before detailed leaf items appear in the queue. Rooted in medial prefrontal cortex schema assimilation (Tse et al., van Kesteren et al.).
            </p>
          </div>
          <button
            type="button"
            role="switch"
            aria-checked={user.enable_schema_checkpoints !== false}
            aria-label="Toggle Schema Checkpoints"
            disabled={savingSchema}
            onClick={toggleSchemaCheckpoints}
            className={`relative inline-flex h-6 w-11 shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out focus:outline-none focus:ring-2 focus:ring-sky-500 focus:ring-offset-2 focus:ring-offset-slate-900 disabled:opacity-50 ${
              user.enable_schema_checkpoints !== false ? 'bg-sky-500' : 'bg-slate-700'
            }`}
          >
            <span
              aria-hidden="true"
              className={`pointer-events-none inline-block h-5 w-5 transform rounded-full bg-white shadow ring-0 transition duration-200 ease-in-out ${
                user.enable_schema_checkpoints !== false ? 'translate-x-5' : 'translate-x-0'
              }`}
            />
          </button>
        </div>

        {/* Prompt Mutation (Reconsolidation Variant Cueing) */}
        <div className="flex items-center justify-between gap-4 rounded-xl border border-ink-line/60 bg-ink-soft/40 p-4">
          <div className="space-y-0.5">
            <div className="flex items-center gap-2">
              <span className="font-semibold text-sm text-slate-200">
                Reconsolidation Variant Cueing
              </span>
              <span
                className={`rounded px-1.5 py-0.5 text-[0.625rem] font-semibold ${
                  user.enable_prompt_mutation
                    ? 'bg-emerald-500/15 text-emerald-300 border border-emerald-500/30'
                    : 'bg-slate-700/50 text-slate-400 border border-slate-600/30'
                }`}
              >
                {user.enable_prompt_mutation ? 'Enabled' : 'Disabled'}
              </span>
            </div>
            <p className="text-xs text-slate-400">
              Enables dynamic orthogonal prompt mutation (counterfactual, adversarial, scenario) during the post-retrieval labile window to prevent superficial wording-overfitting.
            </p>
          </div>
          <button
            type="button"
            role="switch"
            aria-checked={Boolean(user.enable_prompt_mutation)}
            aria-label="Toggle Prompt Mutation"
            disabled={savingMutation}
            onClick={togglePromptMutation}
            className={`relative inline-flex h-6 w-11 shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out focus:outline-none focus:ring-2 focus:ring-sky-500 focus:ring-offset-2 focus:ring-offset-slate-900 disabled:opacity-50 ${
              user.enable_prompt_mutation ? 'bg-sky-500' : 'bg-slate-700'
            }`}
          >
            <span
              aria-hidden="true"
              className={`pointer-events-none inline-block h-5 w-5 transform rounded-full bg-white shadow ring-0 transition duration-200 ease-in-out ${
                user.enable_prompt_mutation ? 'translate-x-5' : 'translate-x-0'
              }`}
            />
          </button>
        </div>

        {/* Pre-Test Hypothesis Mode (Prediction Error / RPE) */}
        <div className="flex items-center justify-between gap-4 rounded-xl border border-ink-line/60 bg-ink-soft/40 p-4">
          <div className="space-y-0.5">
            <div className="flex items-center gap-2">
              <span className="font-semibold text-sm text-slate-200">
                Pre-Test Prediction Mode (Dopaminergic RPE)
              </span>
              <span
                className={`rounded px-1.5 py-0.5 text-[0.625rem] font-semibold ${
                  user.enable_prediction_mode
                    ? 'bg-emerald-500/15 text-emerald-300 border border-emerald-500/30'
                    : 'bg-slate-700/50 text-slate-400 border border-slate-600/30'
                }`}
              >
                {user.enable_prediction_mode ? 'Enabled' : 'Disabled'}
              </span>
            </div>
            <p className="text-xs text-slate-400">
              Requires a blind hypothesis before learning new cards or extracts. Refuted high-confidence guesses trigger dopaminergic plasticity and accelerate long-term retention.
            </p>
          </div>
          <button
            type="button"
            role="switch"
            aria-checked={Boolean(user.enable_prediction_mode)}
            aria-label="Toggle Pre-Test Prediction Mode"
            disabled={savingPrediction}
            onClick={togglePredictionMode}
            className={`relative inline-flex h-6 w-11 shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out focus:outline-none focus:ring-2 focus:ring-sky-500 focus:ring-offset-2 focus:ring-offset-slate-900 disabled:opacity-50 ${
              user.enable_prediction_mode ? 'bg-sky-500' : 'bg-slate-700'
            }`}
          >
            <span
              aria-hidden="true"
              className={`pointer-events-none inline-block h-5 w-5 transform rounded-full bg-white shadow ring-0 transition duration-200 ease-in-out ${
                user.enable_prediction_mode ? 'translate-x-5' : 'translate-x-0'
              }`}
            />
          </button>
        </div>

        <ErrorNote error={error} />
      </div>
    </Section>
  )
}

function CognitiveThemePanel() {
  const {
    themeMode,
    setThemeMode,
    fixedTheme,
    setFixedTheme,
    activeThemeMeta,
    setCognitiveContext,
    enableNightAutoShift,
    setEnableNightAutoShift,
    enableOledBlack,
    setEnableOledBlack,
    enableGreyscaleFriendly,
    setEnableGreyscaleFriendly,
    simulateGreyscale,
    setSimulateGreyscale,
  } = useTheme()

  return (
    <Section
      title="Themes"
      description="Adaptive color harmonies or fixed palette."
    >
      <div className="space-y-6">
        {/* Mode Selector Cards */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {/* Option A: Dynamic Context-Adaptive */}
          <div
            onClick={() => setThemeMode('dynamic')}
            className={`rounded-2xl border p-4 cursor-pointer transition-all relative ${
              themeMode === 'dynamic'
                ? 'border-sky-500 bg-sky-950/20 shadow-lg ring-1 ring-sky-500/50'
                : 'border-ink-line bg-ink/60 hover:border-slate-600 hover:bg-ink'
            }`}
          >
            <div className="flex items-center justify-between mb-2">
              <div className="flex items-center gap-2">
                <span className="font-bold text-slate-100 text-sm">Dynamic Context-Adaptive</span>
              </div>
              <span className="rounded-full bg-emerald-500/20 border border-emerald-500/40 px-2 py-0.5 text-[0.625rem] font-semibold text-emerald-300">
                Recommended
              </span>
            </div>
            <p className="text-xs text-slate-400 mb-3 leading-relaxed">
              The interface smoothly shifts its color harmony to match your real-time cognitive task:
              calming Azure/Emerald for new learning, high-alert Indigo/Amber for recall questions,
              diagnostic Cyan/Coral when tests fail, and obsidian for code flow.
            </p>
            {themeMode === 'dynamic' && (
              <div className="rounded-xl border border-sky-500/30 bg-sky-950/40 p-2.5 text-xs space-y-2">
                <div className="flex items-center justify-between">
                  <span className="text-slate-400">Current Active State:</span>
                  <span className="font-semibold text-sky-200 flex items-center gap-1.5">
                    <span>{activeThemeMeta.label}</span>
                  </span>
                </div>
                <div className="pt-2 border-t border-sky-500/20">
                  <label className="flex items-center gap-2 text-slate-300 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={enableNightAutoShift}
                      onChange={(e) => setEnableNightAutoShift(e.target.checked)}
                      className="rounded border-slate-700 bg-slate-900 text-sky-500 focus:ring-sky-500 cursor-pointer"
                    />
                    <span className="text-[0.6875rem]">
                      Automatically shift to <strong>Circadian Candlelight</strong> after 8:00 PM
                    </span>
                  </label>
                </div>
                <div className="pt-2 border-t border-sky-500/20">
                  <label className="flex items-center gap-2 text-slate-300 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={enableOledBlack}
                      onChange={(e) => setEnableOledBlack(e.target.checked)}
                      className="rounded border-slate-700 bg-slate-900 text-sky-500 focus:ring-sky-500 cursor-pointer"
                    />
                    <span className="text-[0.6875rem]">
                      <strong>OLED Pure Black Canvas</strong>: Keep adaptive accents but force pure pitch black (<code>#000000</code>) background
                    </span>
                  </label>
                </div>
              </div>
            )}
          </div>

          {/* Option B: Fixed Palette Lock */}
          <div
            onClick={() => setThemeMode('fixed')}
            className={`rounded-2xl border p-4 cursor-pointer transition-all relative ${
              themeMode === 'fixed'
                ? 'border-sky-500 bg-sky-950/20 shadow-lg ring-1 ring-sky-500/50'
                : 'border-ink-line bg-ink/60 hover:border-slate-600 hover:bg-ink'
            }`}
          >
            <div className="flex items-center justify-between mb-2">
              <div className="flex items-center gap-2">
                <span className="font-bold text-slate-100 text-sm">Fixed Palette Lock</span>
              </div>
              <span className="rounded-full bg-slate-800 border border-slate-700 px-2 py-0.5 text-[0.625rem] font-semibold text-slate-400">
                User Choice
              </span>
            </div>
            <p className="text-xs text-slate-400 mb-3 leading-relaxed">
              Lock in one uniform color scheme across the entire application. Your chosen substrate and
              accent pairing stays consistent across Flashcards, Code Lab, Reading, and Tree views.
            </p>
            {themeMode === 'fixed' && (
              <div className="rounded-xl border border-sky-500/30 bg-sky-950/40 p-2.5 text-xs space-y-2">
                <div className="flex items-center justify-between">
                  <span className="text-slate-400">Locked Palette:</span>
                  <span className="font-semibold text-sky-200 flex items-center gap-1.5">
                    <span>{activeThemeMeta.label}</span>
                  </span>
                </div>
                <div className="pt-2 border-t border-sky-500/20">
                  <label className="flex items-center gap-2 text-slate-300 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={enableOledBlack}
                      onChange={(e) => setEnableOledBlack(e.target.checked)}
                      className="rounded border-slate-700 bg-slate-900 text-sky-500 focus:ring-sky-500 cursor-pointer"
                    />
                    <span className="text-[0.6875rem]">
                      <strong>OLED Pure Black Canvas</strong>: Force pure pitch black (<code>#000000</code>) background
                    </span>
                  </label>
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Greyscale & High-Contrast Accessibility Mode Panel */}
        <div className="rounded-2xl border border-ink-line bg-ink/60 p-4 transition-all">
          <div className="flex flex-wrap items-center justify-between gap-3 mb-3">
            <div className="flex items-center gap-2.5">
              <div>
                <h3 className="text-sm font-bold text-slate-100 flex items-center gap-2">
                  <span>Greyscale &amp; High-Contrast Mode</span>
                  {enableGreyscaleFriendly && (
                    <span className="rounded-full bg-white/20 border border-white/40 px-2 py-0.5 text-[0.625rem] font-semibold text-white">
                      Active
                    </span>
                  )}
                </h3>
                <p className="text-xs text-slate-400">
                  Enhanced visibility for monochrome displays, Windows/macOS greyscale filters, e-ink monitors, and high-contrast accessibility.
                </p>
              </div>
            </div>

            <button
              type="button"
              role="switch"
              aria-checked={enableGreyscaleFriendly}
              onClick={() => setEnableGreyscaleFriendly(!enableGreyscaleFriendly)}
              className={`w-11 h-6 rounded-full transition-colors relative cursor-pointer ${
                enableGreyscaleFriendly ? 'bg-white' : 'bg-slate-700'
              }`}
              title="Toggle Greyscale & High-Contrast UI Mode"
            >
              <span
                className={`w-5 h-5 rounded-full absolute top-0.5 transition-transform ${
                  enableGreyscaleFriendly ? 'left-5.5 bg-black' : 'left-0.5 bg-white'
                }`}
              />
            </button>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 pt-3 border-t border-ink-line/50 text-xs">
            <div className="space-y-1.5 text-slate-300">
              <p className="font-semibold text-slate-200">How Greyscale Mode enhances visibility:</p>
              <ul className="space-y-1 text-slate-400 text-[0.6875rem] list-disc list-inside">
                <li>
                  <strong className="text-slate-200">Token Diffs:</strong> Solid underline (—) and <span className="font-bold">✓</span> for recalled tokens vs. dashed underline (- -) and <span className="font-bold">✗</span> for missing/unmatched tokens.
                </li>
                <li>
                  <strong className="text-slate-200">Borders:</strong> Elevated high-contrast outlines on cards, panes, code viewports, and dialogs.
                </li>
                <li>
                  <strong className="text-slate-200">Active States:</strong> High-luminance solid indicators for selected tabs, grading buttons, and toggles.
                </li>
                <li>
                  <strong className="text-slate-200">Typography:</strong> Boosted text luminance on secondary and muted descriptions to eliminate blur.
                </li>
              </ul>
            </div>

            <div className="rounded-xl border border-ink-line bg-ink-soft/60 p-3 space-y-2.5">
              <div className="flex items-center justify-between">
                <span className="text-[0.6875rem] font-medium text-slate-300">Simulate Greyscale View</span>
                <button
                  type="button"
                  onClick={() => setSimulateGreyscale(!simulateGreyscale)}
                  className={`px-2.5 py-1 rounded text-xs font-semibold transition cursor-pointer ${
                    simulateGreyscale
                      ? 'bg-white text-black border border-white'
                      : 'bg-slate-800 text-slate-300 border border-slate-700 hover:text-white'
                  }`}
                  title="Apply 100% monochrome CSS filter in browser to preview"
                >
                  {simulateGreyscale ? 'Simulating (ON)' : 'Preview (OFF)'}
                </button>
              </div>
              <p className="text-[0.625rem] text-slate-400 leading-relaxed">
                Turns on an in-browser 100% monochrome filter so you can verify contrast and pattern legibility even when your OS color filter is turned off.
              </p>

              {/* Live Mini Preview */}
              <div className="pt-2 border-t border-ink-line/50">
                <span className="text-[0.625rem] uppercase font-bold text-slate-400 block mb-1.5">Live Token Diff Preview:</span>
                <div className="p-2 rounded bg-ink border border-ink-line text-xs font-mono flex flex-wrap gap-2 items-center">
                  <mark className="rounded px-1.5 py-0.5 text-xs font-medium" title="Recalled">
                    Recalled Term
                  </mark>
                  <mark className="rounded px-1.5 py-0.5 text-xs font-normal" title="Missing">
                    Missing Term
                  </mark>
                  <span className="text-slate-400 text-xs">Punctuation &amp; context</span>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Palettes Grid */}
        <div>
          <div className="flex items-center justify-between mb-3">
            <h3 className="text-xs font-bold text-slate-300 uppercase tracking-wider">
              {themeMode === 'fixed' ? 'Choose Your Fixed Palette:' : 'Interactive Cognitive State Previews:'}
            </h3>
            {themeMode === 'dynamic' && (
              <span className="text-[0.6875rem] text-slate-500 italic">
                (Click any state to preview its color scheme)
              </span>
            )}
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
            {(Object.keys(THEME_REGISTRY) as CognitiveTheme[]).map((themeKey) => {
              const meta = THEME_REGISTRY[themeKey]
              const isSelected =
                themeMode === 'fixed' ? fixedTheme === themeKey : activeThemeMeta.id === themeKey

              return (
                <div
                  key={themeKey}
                  onClick={() => {
                    if (themeMode === 'dynamic') {
                      setCognitiveContext(themeKey === 'classic' ? null : themeKey)
                    } else {
                      setFixedTheme(themeKey)
                    }
                  }}
                  className={`rounded-xl border p-3.5 transition-all cursor-pointer flex flex-col justify-between ${
                    isSelected
                      ? 'border-sky-500/70 bg-sky-950/30 shadow-md ring-1 ring-sky-500/40'
                      : 'border-ink-line/80 bg-ink-soft/40 hover:border-slate-600 hover:bg-ink-soft'
                  }`}
                >
                  <div>
                    <div className="flex items-center justify-between mb-2">
                      <div className="flex items-center gap-2">
                        <span className="font-semibold text-slate-200 text-xs">{meta.label}</span>
                      </div>
                      <div className="flex items-center gap-1.5 shrink-0">
                        <span
                          className="w-3.5 h-3.5 rounded-full border border-white/30 shadow-sm"
                          style={{ backgroundColor: meta.primaryColor }}
                          title={`Primary Accent: ${meta.primaryColor}`}
                        />
                        <span
                          className="w-3.5 h-3.5 rounded-full border border-white/30 shadow-sm"
                          style={{ backgroundColor: meta.secondaryColor }}
                          title={`Secondary Accent: ${meta.secondaryColor}`}
                        />
                      </div>
                    </div>
                    <p className="text-[0.6875rem] font-mono text-slate-400 mb-2">{meta.subtitle}</p>
                    <p className="text-[0.6875rem] text-slate-300 leading-snug mb-2 font-medium">
                      <span className="text-slate-400">{meta.bestFor}</span>
                    </p>
                    <p className="text-[0.625rem] text-slate-500 leading-normal italic">
                      {meta.psychology}
                    </p>
                  </div>

                  <div className="mt-3 pt-2 border-t border-ink-line/50 flex items-center justify-between text-[0.6875rem]">
                    <span className="text-slate-500 font-mono text-[0.625rem]">
                      {meta.primaryColor} / {meta.secondaryColor}
                    </span>
                    <button
                      type="button"
                      className={`px-2 py-0.5 rounded text-[0.625rem] font-semibold transition cursor-pointer ${
                        isSelected
                          ? 'bg-sky-500/30 text-sky-200 border border-sky-500/50'
                          : 'bg-slate-800 text-slate-400 hover:text-slate-200'
                      }`}
                    >
                      {isSelected ? 'Active' : themeMode === 'fixed' ? 'Select' : 'Preview'}
                    </button>
                  </div>
                </div>
              )
            })}
          </div>
        </div>
      </div>
    </Section>
  )
}

function FeatureRequestPanel() {
  const [title, setTitle] = useState('')
  const [category, setCategory] = useState('Feature Request')
  const [description, setDescription] = useState('')
  const [includeSystemInfo, setIncludeSystemInfo] = useState(true)
  const [copied, setCopied] = useState(false)
  const [history, setHistory] = useState<
    Array<{ id: string; title: string; category: string; description: string; date: string }>
  >(() => {
    try {
      const saved = storage.get('memorization.featureRequests')
      return saved ? JSON.parse(saved) : []
    } catch {
      return []
    }
  })

  const getSystemInfo = () => {
    const ua = navigator.userAgent
    const platform = navigator.platform || 'Unknown OS'
    const screenRes = typeof window !== 'undefined' ? `${window.screen.width}x${window.screen.height}` : 'unknown'
    return `\n\n---\n**Environment Details:**\n- **OS / Platform**: ${platform}\n- **Browser / User Agent**: ${ua}\n- **Screen Resolution**: ${screenRes}\n- **App Version**: Ars Memoriae v0.1.0`
  }

  const formatPayload = () => {
    let body = `### Description\n${description.trim() || '_No description provided._'}`
    if (includeSystemInfo) {
      body += getSystemInfo()
    }
    return body
  }

  const saveToHistory = () => {
    if (!title.trim()) return
    const entry = {
      id: Date.now().toString(),
      title: title.trim(),
      category,
      description: description.trim(),
      date: new Date().toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' }),
    }
    const updated = [entry, ...history.filter((h) => h.title !== title.trim()).slice(0, 9)]
    setHistory(updated)
    try {
      storage.set('memorization.featureRequests', JSON.stringify(updated))
    } catch {
      // ignore
    }
  }

  const handleGitHubSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (!title.trim()) return

    const issueTitle = `[${category}] ${title.trim()}`
    const issueBody = formatPayload()
    const url = `https://github.com/13emerald4/Ars-Memoriae/issues/new?title=${encodeURIComponent(
      issueTitle,
    )}&body=${encodeURIComponent(issueBody)}`

    saveToHistory()
    window.open(url, '_blank', 'noopener,noreferrer')
  }

  const handleCopy = () => {
    if (!title.trim() && !description.trim()) return
    const formatted = `[Feature Request: ${category}] ${title.trim()}\n\n${formatPayload()}`
    void navigator.clipboard.writeText(formatted)
    setCopied(true)
    setTimeout(() => setCopied(false), 2200)
    saveToHistory()
  }

  const handleClearHistory = () => {
    setHistory([])
    try {
      storage.remove('memorization.featureRequests')
    } catch {
      // ignore
    }
  }

  return (
    <Section
      title="Feature Requests & Feedback"
      description="Have an idea for a feature, adjustment, or improvement? Submit it directly to the developer."
    >
      <form onSubmit={handleGitHubSubmit} className="space-y-4">
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
          <div className="sm:col-span-2 space-y-1">
            <label className="text-xs font-semibold text-slate-300">Request Title</label>
            <input
              type="text"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="e.g. Vim keybindings in editor, dark contrast slider, audio cues..."
              className="w-full rounded-lg border border-ink-line bg-[#1c1c1c] px-3 py-2 text-xs text-slate-200 placeholder:text-slate-600 focus:border-sky-500 focus:outline-none focus:ring-1 focus:ring-sky-500"
              required
            />
          </div>
          <div className="space-y-1">
            <label className="text-xs font-semibold text-slate-300">Category</label>
            <select aria-label="Feedback category"
              value={category}
              onChange={(e) => setCategory(e.target.value)}
              className="w-full rounded-lg border border-ink-line bg-[#1c1c1c] px-3 py-2 text-xs text-slate-200 focus:border-sky-500 focus:outline-none focus:ring-1 focus:ring-sky-500 cursor-pointer"
            >
              <option value="Feature Request">Feature Request</option>
              <option value="UI & Visual Ergonomics">UI & Visual Ergonomics</option>
              <option value="Active Recall & Review">Active Recall & Review</option>
              <option value="Code Practice & Execution">Code Practice & Execution</option>
              <option value="FSRS & Scheduling">FSRS & Scheduling</option>
              <option value="Performance & Hardware">Performance & Hardware</option>
              <option value="Bug Report / Issue">Bug Report / Issue</option>
              <option value="Other">Other</option>
            </select>
          </div>
        </div>

        <div className="space-y-1">
          <label className="text-xs font-semibold text-slate-300">Details & Rationale</label>
          <textarea
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            rows={4}
            placeholder="Describe what feature you would like to see, why it is useful, or how you envision it working..."
            className="w-full rounded-lg border border-ink-line bg-[#1c1c1c] p-3 text-xs text-slate-200 placeholder:text-slate-600 focus:border-sky-500 focus:outline-none focus:ring-1 focus:ring-sky-500 font-sans leading-relaxed"
          />
        </div>

        <div className="flex flex-wrap items-center justify-between gap-3 pt-1">
          <label className="flex items-center gap-2 text-xs text-slate-400 cursor-pointer select-none">
            <input
              type="checkbox"
              checked={includeSystemInfo}
              onChange={(e) => setIncludeSystemInfo(e.target.checked)}
              className="rounded border-ink-line bg-[#1c1c1c] text-sky-500 focus:ring-sky-500 cursor-pointer"
            />
            <span>Include client platform details (OS, browser, resolution)</span>
          </label>

          <div className="flex flex-wrap items-center gap-2">
            <button
              type="button"
              onClick={handleCopy}
              disabled={!title.trim() && !description.trim()}
              className="btn btn-secondary text-xs px-3 py-1.5 flex items-center gap-1.5 disabled:opacity-40 cursor-pointer"
              title="Copy formatted request to paste in Discord, email, or messaging"
            >
              {copied ? (
                <>
                  <span className="text-emerald-400">✓</span>
                  <span className="text-emerald-300 font-medium">Copied to Clipboard!</span>
                </>
              ) : (
                <>
                  <span>Copy Formatted Request</span>
                </>
              )}
            </button>

            <button
              type="submit"
              disabled={!title.trim()}
              className="btn btn-primary text-xs px-4 py-1.5 flex items-center gap-1.5 font-semibold disabled:opacity-40 shadow-md cursor-pointer"
              title="Open GitHub Issues pre-filled with this feature request"
            >
              <span>Submit on GitHub Issues</span>
              <span className="text-xs">↗</span>
            </button>
          </div>
        </div>

        {/* Local History */}
        {history.length > 0 && (
          <div className="mt-4 pt-4 border-t border-ink-line/60 space-y-2">
            <div className="flex items-center justify-between text-xs">
              <span className="font-semibold text-slate-400 uppercase tracking-wider text-[0.625rem]">
                Your Recent Requests ({history.length})
              </span>
              <button
                type="button"
                onClick={handleClearHistory}
                className="text-[0.6875rem] text-slate-500 hover:text-slate-300 transition cursor-pointer"
              >
                Clear History
              </button>
            </div>
            <div className="space-y-1.5 max-h-44 overflow-y-auto pr-1">
              {history.map((h) => (
                <div
                  key={h.id}
                  className="rounded-lg border border-ink-line/50 bg-[#161616] p-2.5 flex items-center justify-between text-xs gap-3"
                >
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center gap-2 mb-0.5">
                      <span className="chip text-[0.625rem] py-0 px-1.5 border-sky-500/30 text-sky-300 font-mono">
                        {h.category}
                      </span>
                      <span className="text-slate-500 text-[0.625rem]">{h.date}</span>
                    </div>
                    <p className="text-slate-200 font-medium truncate text-xs">{h.title}</p>
                  </div>
                  <button
                    type="button"
                    onClick={() => {
                      setTitle(h.title)
                      setCategory(h.category)
                      setDescription(h.description)
                    }}
                    className="text-slate-400 hover:text-slate-200 text-[0.6875rem] underline shrink-0 cursor-pointer"
                    title="Reload into form"
                  >
                    Load
                  </button>
                </div>
              ))}
            </div>
          </div>
        )}
      </form>
    </Section>
  )
}



