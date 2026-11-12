import { dialogs } from '../components/dialogs'
import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { createPortal } from 'react-dom'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { api, API_BASE, newReviewAttemptId } from '../api/client'
import type {
  CardReference,
  Deck,
  DeckDocMessage,
  Grade,
  Lesson,
  PretestPredictionResponse,
  QueueItem,
  RunCodeResponse,
  SessionSummary,
  SocraticLineHintResponse,
  SocraticTurn,
  SpreadingActivationNode,
  StuckAlert,
  SubmitAnswerResponse,
  VramMetrics,
} from '../api/types'
import {
  ANTIGRAVITY_MODELS,
  GRADES,
  getModelDisplayInfo,
  isAllowedGradingModel,
  isAntigravityModel,
} from '../api/types'
import { CodeEditor } from '../components/CodeEditor'
import { CodeTestConsole } from '../components/CodeTestConsole'
import { OcclusionCard } from '../components/Occlusion'
import SessionTimer, { formatClock, REVIEW_EVENT } from '../components/SessionTimer'
import { RichText } from '../components/RichText'
import { Empty, ErrorNote, Spinner } from '../components/ui'
import { useAuth } from '../hooks/useAuth'
import { useLexicon } from '../components/LexiconContext'
import { MarginLexiconPanel } from '../components/MarginLexiconPanel'
import { useTheme } from '../components/ThemeContext'
import { FullscreenButton } from '../components/FullscreenContext'
import { DeckReviewStatsBar } from '../components/DeckReviewStatsBar'
import { CopyLearningSummaryButton } from '../components/CopyLearningSummaryButton'
import { AnswerComparison, computeTokenDiff } from '../components/AnswerComparison'
import {
  computeExpectedLines,
  getFirstTargetLine,
  formatTargetLineSummary,
  findIncompleteLineNumber,
  DEFAULT_TARGET_HIGHLIGHT_COLOR,
} from '../utils/expectedCodeUtils'
import { HighlightColorPicker } from '../components/HighlightColorPicker'
import { copyLearningSummaryToClipboard } from '../utils/learningSummaryExport'
import TiledEditorPane, { type TilePaneTab } from '../components/TiledEditorPane'
import { ResizableSplitter } from '../components/ResizableSplitter'
import { useWorkbenchLayout } from '../hooks/useWorkbenchLayout'
import DeckCardsViewer from '../components/DeckCardsViewer'
import SavedCardsDrawer from '../components/SavedCardsDrawer'
import {
  type SavedCardDraft,
  saveDraft,
  removeDraft,
  getDraftForCard,
  getSavedDraftsCount,
} from '../utils/savedCardDrafts'
import {
  getAllCardsRunProgress,
  saveAllCardsRunProgress,
  clearAllCardsRunProgress,
} from '../utils/allCardsRunStorage'
import {
  isCodeCard as checkIsCodeCard,
  looksLikeCode,
  extractCleanCode,
  detectCodeLanguage,
} from '../utils/codeUtils'
import { storage } from '../utils/storage'

const LEARN_MODE_KEY = 'memorization.learnMode'

// Mirrors the backend's SCORE_BANDS (grading_service.py) — display only; the
// server is the one source of truth for which band a score actually lands in.
const GRADE_BAND: Record<Grade, string> = {
  again: '0–39%',
  hard: '40–69%',
  good: '70–89%',
  easy: '90–100%',
}

const GRADE_STYLE: Record<Grade, string> = {
  again: 'border-rose-500/40 text-rose-300 hover:bg-rose-500/15',
  hard: 'border-amber-500/40 text-amber-300 hover:bg-amber-500/15',
  good: 'border-emerald-500/40 text-emerald-300 hover:bg-emerald-500/15',
  easy: 'border-sky-500/40 text-sky-300 hover:bg-sky-500/15',
}

function buildStarterTestCode(item: QueueItem | null): string {
  if (!item) return ''
  return item.starter_tests || ''
}

function formatExecutionSummary(res: RunCodeResponse | null): string | null {
  if (!res) return null
  const parts: string[] = [
    `Status: ${res.status}`,
    `Tests Passed: ${res.passed_count}/${res.total_count} (${res.runtime_ms}ms)`,
  ]
  if (
    res.student_total_count !== undefined &&
    res.student_total_count > 0 &&
    res.student_passed_count !== undefined
  ) {
    parts.push(`Student Unit Tests: ${res.student_passed_count}/${res.student_total_count}`)
  }
  if (res.error) {
    parts.push(`Execution Error:\n${res.error.slice(0, 1200)}`)
  }
  const failedCases = (res.results || []).filter((r) => !r.passed).slice(0, 3)
  if (failedCases.length > 0) {
    parts.push(
      'Failed Test Cases:\n' +
        failedCases
          .map(
            (r) =>
              `  - Test #${r.test_index}: input=${JSON.stringify(r.input)} expected=${JSON.stringify(
                r.expected,
              )} actual=${JSON.stringify(r.actual)}${r.error ? ` err=${r.error}` : ''}${
                r.stdout ? ` stdout=${r.stdout.slice(0, 200)}` : ''
              }`,
          )
          .join('\n'),
    )
  }
  const failedStudentTests = (res.student_tests || []).filter((st) => !st.passed).slice(0, 3)
  if (failedStudentTests.length > 0) {
    parts.push(
      'Failed Student Tests:\n' +
        failedStudentTests
          .map((st) => `  - ${st.test_name}: ${st.error || 'failed'}`)
          .join('\n'),
    )
  }
  return parts.join('\n')
}


function buildCompletedTestCode(item: QueueItem | null): string {
  if (!item) return ''
  if ((item as any).reference_tests) return (item as any).reference_tests
  if ((item as any).test_solution) return (item as any).test_solution

  const isCode = Boolean(
    item.starter_code ||
      (item.test_cases && item.test_cases.length > 0) ||
      item.starter_tests ||
      checkIsCodeCard(item) ||
      looksLikeCode(item.back)
  )
  if (!isCode) return ''

  const cases = item.test_cases || []
  if (cases.length === 0 && item.starter_tests) {
    return item.starter_tests
  }

  const codeToScan = item.starter_code || item.back || ''
  const isPython = Boolean(codeToScan.includes('def ') || codeToScan.includes('class Solution:'))

  if (isPython) {
    const fnMatch = codeToScan.match(/def\s+([a-zA-Z0-9_]+)/)
    const fnName = fnMatch ? fnMatch[1] : 'solution'

    const testMethods = cases
      .map((tc, idx) => {
        let args = ''
        if (tc.input && typeof tc.input === 'object' && !Array.isArray(tc.input)) {
          args = Object.values(tc.input)
            .map((v) => JSON.stringify(v))
            .join(', ')
        } else {
          args = JSON.stringify(tc.input)
        }
        const exp = JSON.stringify(tc.expected)
        const label = idx === 0 ? 'sample_case' : idx === 1 ? 'boundary_threshold' : `edge_case_${idx}`
        return `    def test_${label}(self):\n        self.assertEqual(${fnName}(${args}), ${exp})`
      })
      .join('\n\n')

    return `# Completed Reference Unit Tests (Python)
import unittest

class TestSolution(unittest.TestCase):
${testMethods || '    pass'}
`
  }

  // TypeScript / JavaScript
  const fnName =
    codeToScan.match(/(?:function\s+|const\s+|let\s+|var\s+)?([a-zA-Z0-9_$]+)\s*(?:=\s*(?:async\s*)?\([^)]*\)\s*=>|\()/)?.[1] ||
    codeToScan.match(/function\s+([a-zA-Z0-9_$]+)/)?.[1] ||
    'solution'
  const edgeNotes = item.edge_cases || []

  const testBlocks = cases.map((tc, idx) => {
    let args = ''
    if (tc.input && typeof tc.input === 'object' && !Array.isArray(tc.input)) {
      args = Object.values(tc.input)
        .map((v) => JSON.stringify(v))
        .join(', ')
    } else {
      args = JSON.stringify(tc.input)
    }
    const exp = JSON.stringify(tc.expected)

    let testName = `case ${idx + 1}`
    if (idx === 0) {
      testName = 'sample case'
    } else if (idx === 1) {
      testName = 'boundary threshold case'
    } else if (edgeNotes[idx - 2]) {
      testName = `edge case: ${edgeNotes[idx - 2]}`
    } else {
      testName = `test case ${idx + 1}`
    }

    return `test('${testName}', checkExpect(() => ${fnName}(${args}), ${exp}));`
  })

  return `// Completed reference unit tests
// Full suite asserting sample, boundary, and edge cases

${testBlocks.join('\n\n')}
`
}


function formatLatencyNote(note: string | null | undefined): string | null | undefined {
  if (!note) return note
  const m = note.match(/^answered in (\d+)s$/)
  if (m) {
    const s = parseInt(m[1], 10)
    const mins = Math.floor(s / 60)
    const rem = s % 60
    return `answered in ${mins}m ${rem}s`
  }
  const m2 = note.match(/^answered in (\d+)m$/)
  if (m2) {
    return `answered in ${m2[1]}m 0s`
  }
  if (note === 'answered in under a second') {
    return 'answered in 0m 0s'
  }
  return note
}

/** The unified session view (§9): one endpoint hands back cards *and* extracts,
 *  so this page routes on `kind` rather than the user picking a mode. */
export default function Review() {
  const { user, refresh } = useAuth()
  const navigate = useNavigate()
  // `?branch=<node id>` restricts the session to one knowledge-tree branch.
  const [params, setParams] = useSearchParams()
  const branch = params.get('branch')

  const [item, setItem] = useState<QueueItem | null>(null)
  const [session, setSession] = useState<SessionSummary | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<unknown>(null)

  const [answer, setAnswer] = useState('')
  const [grading, setGrading] = useState(false)
  const [result, setResult] = useState<SubmitAnswerResponse | null>(null)
  const [vramDismissed, setVramDismissed] = useState(false)
  const [revealed, setRevealed] = useState(false)
  const [skipReviewRecording, setSkipReviewRecording] = useState(false)
  const [retryAfterRating, setRetryAfterRating] = useState(false)
  const [previousCard, setPreviousCard] = useState<QueueItem | null>(null)
  const [lastOutcome, setLastOutcome] = useState<string | null>(null)
  const [confidence, setConfidence] = useState<number | null>(null)
  const [deckStatsTrigger, setDeckStatsTrigger] = useState(0)

  const canUseAntigravity = Boolean(user?.can_use_antigravity)
  const [activeModel, setActiveModel] = useState<string>(() =>
    user?.grading_model &&
    isAllowedGradingModel(user.grading_model) &&
    (canUseAntigravity || !isAntigravityModel(user.grading_model))
      ? user.grading_model
      : 'qwen2.5-coder:3b',
  )
  const [installedModels, setInstalledModels] = useState<string[]>([])
  const gradingAbortRef = useRef<AbortController | null>(null)
  // One confirm in flight at a time: a double click or key repeat would
  // otherwise schedule the card twice and log two reviews.
  const confirmingRef = useRef(false)
  const [confirming, setConfirming] = useState(false)

  useEffect(() => {
    if (
      user?.grading_model &&
      isAllowedGradingModel(user.grading_model) &&
      (canUseAntigravity || !isAntigravityModel(user.grading_model))
    ) {
      setActiveModel(user.grading_model)
    }
  }, [user?.grading_model, canUseAntigravity])

  useEffect(() => {
    api
      .llmStatus()
      .then((res) => {
        if (res?.models_installed && res.models_installed.length > 0) {
          const genModels = res.models_installed.filter(
            (m) => isAllowedGradingModel(m) && (canUseAntigravity || !isAntigravityModel(m)),
          )
          setInstalledModels(genModels)
        }
      })
      .catch(() => {})
  }, [canUseAntigravity])

  const { setCognitiveContext } = useTheme()

  // Persist Mode: Drill a deck continuously until all cards in review are rated Easy
  const deckParam = params.get('deck')
  const persistParam = params.get('persist') === '1' || params.get('persist') === 'true'
  const unseenParam =
    params.get('unseen') === '1' ||
    params.get('unseen') === 'true' ||
    params.get('unseen_only') === '1' ||
    params.get('unseen_only') === 'true'
  const [persistActive, setPersistActive] = useState<boolean>(false)
  const [persistUnseenOnly, setPersistUnseenOnly] = useState<boolean>(false)
  const [persistDeckId, setPersistDeckId] = useState<string | null>(null)
  const activeDeckRef = useRef<string | null>(null)
  const [persistDeckName, setPersistDeckName] = useState<string>('')
  const [persistCards, setPersistCards] = useState<QueueItem[]>([])
  const [persistGraspedIds, setPersistGraspedIds] = useState<Set<string>>(new Set())
  const [persistPendingQueue, setPersistPendingQueue] = useState<string[]>([])
  const [persistCardAttempts, setPersistCardAttempts] = useState<Record<string, number>>({})
  const [persistRound, setPersistRound] = useState(1)
  const [persistTotalReviews, setPersistTotalReviews] = useState(0)
  // Cards whose first rating in this persist session has been sent to FSRS.
  // Persist mode repeats a card until it is rated Easy; scheduling every one
  // of those passes told FSRS the card was recalled many times in a row and
  // pushed its next due date far out. Only the first, honest attempt is a
  // review. The repeats are drill and are not recorded.
  const persistRecordedRef = useRef<Set<string>>(new Set())
  const [persistCompleted, setPersistCompleted] = useState(false)
  const [allDecks, setAllDecks] = useState<Deck[]>([])
  const [selectedPersistDeckId, setSelectedPersistDeckId] = useState<string>('')
  const [dismissedUnseenDeckId, setDismissedUnseenDeckId] = useState<string | null>(null)

  const { setActiveDeckContext, registerDocument } = useLexicon()

  // A card's saved definitions changed. The card object lives in several
  // pieces of state (the current item, the persist and run lists, the
  // "previous card"); each gets a new object rather than having the shared one
  // edited in place, which React cannot see.
  const applyGlossesToCard = useCallback(
    (cardId: string, glosses: NonNullable<QueueItem['lexicon_glosses']>) => {
      const patch = (c: QueueItem): QueueItem =>
        c.id === cardId ? { ...c, lexicon_glosses: glosses } : c
      setItem((prev) => (prev ? patch(prev) : prev))
      setPreviousCard((prev) => (prev ? patch(prev) : prev))
      setPersistCards((prev) => (prev.some((c) => c.id === cardId) ? prev.map(patch) : prev))
      setAllCardsRunCards((prev) => (prev.some((c) => c.id === cardId) ? prev.map(patch) : prev))
    },
    [],
  )

  const currentDeckInfo = useMemo(() => {
    if (!deckParam) return null
    return allDecks.find((d) => d.id === deckParam) || null
  }, [allDecks, deckParam])

  useEffect(() => {
    if (item) {
      setActiveDeckContext({
        cardId: item.id || null,
        deckName: item.deck_name || currentDeckInfo?.name || null,
        thematicNature:
          item.card_thematic_nature ||
          item.deck_thematic_nature ||
          currentDeckInfo?.thematic_nature ||
          item.category ||
          null,
        existingGlosses: item.lexicon_glosses || [],
        onGlossesUpdated: (updated) => applyGlossesToCard(item.id, updated),
      })
    } else if (currentDeckInfo) {
      setActiveDeckContext({
        cardId: null,
        deckName: currentDeckInfo.name,
        thematicNature: currentDeckInfo.thematic_nature || null,
      })
    } else {
      setActiveDeckContext(null)
    }
    return () => {
      setActiveDeckContext(null)
    }
  }, [item, currentDeckInfo, setActiveDeckContext, applyGlossesToCard])

  // All Cards Run Mode: Review every card in deck consecutively, easiest to hardest, then FSRS takes over
  const runParam = params.get('run') === 'all' || params.get('all_cards_run') === '1'
  const [allCardsRunActive, setAllCardsRunActive] = useState<boolean>(false)
  const [allCardsRunDeckId, setAllCardsRunDeckId] = useState<string | null>(null)
  const [allCardsRunDeckName, setAllCardsRunDeckName] = useState<string>('')
  const [allCardsRunCards, setAllCardsRunCards] = useState<QueueItem[]>([])
  const [allCardsRunIndex, setAllCardsRunIndex] = useState<number>(0)
  const [allCardsRunCompleted, setAllCardsRunCompleted] = useState<boolean>(false)

  // LeetCode-Style Split IDE & Code Execution Workbench
  const [layoutMode, setLayoutMode] = useState<'split' | 'classic'>(() => {
    return (storage.get('memorization.reviewLayoutMode') as 'split' | 'classic') || 'split'
  })
  const [codeLanguage, setCodeLanguage] = useState<string>(() => {
    return storage.get('memorization.reviewCodeLanguage') || 'typescript'
  })
  const [codeRunning, setCodeRunning] = useState(false)
  const [codeRunResult, setCodeRunResult] = useState<RunCodeResponse | null>(null)
  const [testCode, setTestCode] = useState('')
  const [sharedQaHistory, setSharedQaHistory] = useState<DeckDocMessage[]>([])
  const [activeEditorTab, setActiveEditorTab] = useState<'solution' | 'tests' | 'reference' | 'ref_tests'>('solution')
  const [singleRefViewMode, setSingleRefViewMode] = useState<'ide' | 'diff' | 'hint'>(() => {
    return (storage.get('memorization.refViewMode') as 'ide' | 'diff' | 'hint') || 'ide'
  })
  const [focusTargetCode, setFocusTargetCode] = useState<boolean>(() => {
    const saved = storage.get('memorization.focusTargetCode')
    return saved !== null ? saved === 'true' : true
  })
  const handleToggleFocusTargetCode = () => {
    setFocusTargetCode((prev) => {
      const next = !prev
      storage.set('memorization.focusTargetCode', String(next))
      return next
    })
  }
  const [targetHighlightColor, setTargetHighlightColor] = useState<string>(() => {
    return storage.get('memorization.targetHighlightColor') || DEFAULT_TARGET_HIGHLIGHT_COLOR
  })
  const handleHighlightColorChange = (newColor: string) => {
    setTargetHighlightColor(newColor)
    storage.set('memorization.targetHighlightColor', newColor)
  }
  const [tiledTabs, setTiledTabs] = useState<boolean>(() => {
    return storage.get('memorization.tiledEditorTabs') === 'true'
  })
  const [tileLeftTab, setTileLeftTabState] = useState<TilePaneTab>(() => {
    const saved = storage.get('memorization.tileLeftTab') as TilePaneTab | null
    return saved || 'solution'
  })
  const [tileRightTab, setTileRightTabState] = useState<TilePaneTab>(() => {
    const saved = storage.get('memorization.tileRightTab') as TilePaneTab | null
    if (saved && saved !== 'solution') return saved
    return 'tests'
  })

  const setTileLeftTab = useCallback((tab: TilePaneTab) => {
    setTileLeftTabState(tab)
    storage.set('memorization.tileLeftTab', tab)
  }, [])

  const setTileRightTab = useCallback((tab: TilePaneTab) => {
    setTileRightTabState(tab)
    storage.set('memorization.tileRightTab', tab)
  }, [])

  const [copiedRef, setCopiedRef] = useState(false)
  const [copiedStarterTests, setCopiedStarterTests] = useState(false)
  const [copiedRefTests, setCopiedRefTests] = useState(false)

  const toggleTiledTabs = useCallback(() => {
    setTiledTabs((prev) => {
      const next = !prev
      storage.set('memorization.tiledEditorTabs', String(next))
      return next
    })
  }, [])

  const [logicGuardEnabled, setLogicGuardEnabled] = useState<boolean>(() => {
    return storage.get('ars_logic_guard_enabled') !== 'false'
  })

  const handleToggleLogicGuard = useCallback((enabled: boolean) => {
    setLogicGuardEnabled(enabled)
    storage.set('ars_logic_guard_enabled', enabled ? 'true' : 'false')
  }, [])

  const handleHideSolution = useCallback((mode: 'hint' | 'hide' = 'hide') => {
    setRevealed(false)
    setResult(null)
    if (mode === 'hint') {
      storage.set('memorization.refViewMode', 'hint')
      setSingleRefViewMode('hint')
    } else {
      storage.set('memorization.refViewMode', 'ide')
      setSingleRefViewMode('ide')
    }
    setTimeout(() => {
      inputRef.current?.focus()
    }, 50)
  }, [])

  const workbenchLayout = useWorkbenchLayout()
  const workbenchContainerRef = useRef<HTMLDivElement>(null)
  const tiledContainerRef = useRef<HTMLDivElement>(null)
  const workbenchRowRef = useRef<HTMLDivElement>(null)

  const isCurrentCodeCard = useMemo(() => {
    return Boolean(item && item.kind === 'card' && checkIsCodeCard(item))
  }, [item])

  // Separate Window IDE Popout State & Window Management
  const [isIdePoppedOut, setIsIdePoppedOut] = useState(false)
  const idePopupRef = useRef<Window | null>(null)
  const [popoutDimensions, setPopoutDimensions] = useState<{ width: number; height: number }>({
    width: typeof window !== 'undefined' ? window.innerWidth : 1200,
    height: typeof window !== 'undefined' ? window.innerHeight : 800,
  })
  const [popoutShowProblem, setPopoutShowProblem] = useState(false)
  const [popoutShowLexicon, setPopoutShowLexicon] = useState(false)
  const [workbenchMarginCollapsed, setWorkbenchMarginCollapsed] = useState(false)

  const handleDockBackIde = useCallback(() => {
    if (idePopupRef.current && !idePopupRef.current.closed) {
      idePopupRef.current.close()
    }
    idePopupRef.current = null
    setIsIdePoppedOut(false)
  }, [])

  const handlePopOutIde = useCallback(() => {
    if (layoutMode !== 'split') {
      setLayoutMode('split')
      storage.set('memorization.reviewLayoutMode', 'split')
    }

    if (idePopupRef.current && !idePopupRef.current.closed) {
      idePopupRef.current.focus()
      if ((item?.lexicon_glosses?.length ?? 0) > 0) {
        setPopoutShowLexicon(true)
      }
      setIsIdePoppedOut(true)
      return
    }

    const availW = typeof window !== 'undefined' ? window.screen?.availWidth || 1400 : 1400
    const availH = typeof window !== 'undefined' ? window.screen?.availHeight || 900 : 900
    const popup = window.open(
      '',
      'ArsMemoriaeIdeWindow',
      `width=${availW},height=${availH},left=0,top=0,resizable=yes,scrollbars=yes`
    )
    if (!popup) {
      dialogs.notify('The separate IDE window was blocked. Allow pop-ups for this site to use it.', 'error')
      return
    }

    const problemTitle = item?.title || item?.deck_name || 'Code Practice IDE'
    popup.document.open()
    popup.document.write('<!DOCTYPE html><html><head></head><body></body></html>')
    popup.document.close()
    popup.document.title = `Ars Memoriae · ${problemTitle}`
    popup.document.head.innerHTML = ''

    // Copy documentElement classes, CSS custom properties, and data-* attributes
    popup.document.documentElement.className = document.documentElement.className
    popup.document.documentElement.style.cssText = document.documentElement.style.cssText
    Array.from(document.documentElement.attributes).forEach((attr) => {
      if (attr.name.startsWith('data-')) {
        popup.document.documentElement.setAttribute(attr.name, attr.value)
      }
    })

    // Copy application stylesheets and styles
    Array.from(document.querySelectorAll('link[rel="stylesheet"], link[rel="preconnect"], style')).forEach((node) => {
      popup.document.head.appendChild(node.cloneNode(true))
    })

    // Add layout baseline styles
    const baseStyle = popup.document.createElement('style')
    baseStyle.textContent = `
      html, body {
        height: 100%;
        margin: 0;
        padding: 0;
        background-color: #121212;
        color: #eff1f6;
        font-family: ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
        overflow: hidden;
      }
      #ars-ide-popout-root {
        height: 100vh;
        width: 100vw;
        display: flex;
        flex-direction: column;
        background-color: #121212;
        overflow: hidden;
      }
    `
    popup.document.head.appendChild(baseStyle)

    popup.document.body.className = 'bg-[#121212] text-slate-100 m-0 p-0 font-sans h-screen flex flex-col select-auto overflow-hidden'
    popup.document.body.style.backgroundColor = '#121212'
    popup.document.body.style.color = '#eff1f6'

    const container = popup.document.createElement('div')
    container.id = 'ars-ide-popout-root'
    container.className = 'flex flex-col h-screen w-screen overflow-hidden'
    popup.document.body.appendChild(container)

    const updateDims = () => {
      if (!popup || popup.closed) return
      setPopoutDimensions({
        width: popup.innerWidth,
        height: popup.innerHeight,
      })
    }
    updateDims()

    popup.addEventListener('resize', updateDims)

    popup.addEventListener('beforeunload', () => {
      setIsIdePoppedOut(false)
      idePopupRef.current = null
    })

    // Enable Escape, Alt+W, Alt+P to dock back, Alt+O to toggle problem statement
    popup.document.addEventListener('keydown', (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        e.preventDefault()
        handleDockBackIde()
      } else if (e.altKey && (e.code === 'KeyW' || e.code === 'KeyP')) {
        e.preventDefault()
        handleDockBackIde()
      } else if (e.altKey && e.code === 'KeyO') {
        e.preventDefault()
        setPopoutShowProblem((prev) => !prev)
      }
    })

    idePopupRef.current = popup
    if ((item?.lexicon_glosses?.length ?? 0) > 0) {
      setPopoutShowLexicon(true)
    }
    setIsIdePoppedOut(true)
  }, [handleDockBackIde, layoutMode, item?.title, item?.deck_name, item?.lexicon_glosses?.length])

  // Clean up popup window on unmount or main window unload
  useEffect(() => {
    const handleUnload = () => {
      if (idePopupRef.current && !idePopupRef.current.closed) {
        idePopupRef.current.close()
      }
    }
    window.addEventListener('beforeunload', handleUnload)
    return () => {
      window.removeEventListener('beforeunload', handleUnload)
      if (idePopupRef.current && !idePopupRef.current.closed) {
        idePopupRef.current.close()
      }
    }
  }, [])

  // Register popout IDE window document for text highlight -> Define pill
  useEffect(() => {
    if (!isIdePoppedOut || !idePopupRef.current || idePopupRef.current.closed) {
      return
    }
    return registerDocument(idePopupRef.current.document)
  }, [isIdePoppedOut, registerDocument])

  // If card changes to a non-code card while popped out, dock back
  useEffect(() => {
    if (!isCurrentCodeCard && isIdePoppedOut) {
      handleDockBackIde()
    }
  }, [isCurrentCodeCard, isIdePoppedOut, handleDockBackIde])

  // Update popup document title when item changes
  useEffect(() => {
    if (isIdePoppedOut && idePopupRef.current && !idePopupRef.current.closed) {
      const problemTitle = item?.title || item?.deck_name || 'Code Practice IDE'
      idePopupRef.current.document.title = `Ars Memoriae · ${problemTitle}`
    }
  }, [item?.title, item?.deck_name, isIdePoppedOut])

  const handleCopyReferenceCode = useCallback(async (refCode: string) => {
    if (!refCode) return
    try {
      await navigator.clipboard.writeText(refCode)
      setCopiedRef(true)
      setTimeout(() => setCopiedRef(false), 2000)
    } catch {
      // ignore
    }
  }, [])

  const handleCopyStarterTests = useCallback(async (code: string) => {
    if (!code) return
    try {
      await navigator.clipboard.writeText(code)
      setCopiedStarterTests(true)
      setTimeout(() => setCopiedStarterTests(false), 2000)
    } catch {
      // ignore
    }
  }, [])

  const handleCopyReferenceTests = useCallback(async (code: string) => {
    if (!code) return
    try {
      await navigator.clipboard.writeText(code)
      setCopiedRefTests(true)
      setTimeout(() => setCopiedRefTests(false), 2000)
    } catch {
      // ignore
    }
  }, [])

  // Memory Athlete: Blitz Sprint Mode & Automaticity Telemetry (§Feature 4)
  const [blitzActive, setBlitzActive] = useState(false)
  const [blitzDurationSec, setBlitzDurationSec] = useState(60)
  const [blitzTimeRemainingSec, setBlitzTimeRemainingSec] = useState(60)
  const [blitzCardsAnswered, setBlitzCardsAnswered] = useState(0)
  const [blitzCorrectCount, setBlitzCorrectCount] = useState(0)
  const [blitzLatencies, setBlitzLatencies] = useState<number[]>([])
  const [blitzSummaryOpen, setBlitzSummaryOpen] = useState(false)
  const [blitzStats, setBlitzStats] = useState<{
    total: number
    correct: number
    avgLatencySec: number
    cpm: number
    automaticityRate: number
  } | null>(null)

  // Stuck-state detector: a real-time nudge, not a per-card verdict — it
  // persists across the card transition below rather than being cleared by
  // `load()`, so it survives until the user acts on or dismisses it.
  const [stuckAlert, setStuckAlert] = useState<StuckAlert | null>(null)
  const [breakUntil, setBreakUntil] = useState<number | null>(null)

  // Learn & Practice: read a lesson built from the card's citations before
  // being asked the question.
  const [learnMode, setLearnMode] = useState(
    () => storage.get(LEARN_MODE_KEY) === '1',
  )
  // Read through a ref by initCardState. As a dependency it rebuilt that
  // callback, and with it `load` and the effect that calls `load`, so flipping
  // the Learn & Practice toggle refetched the queue and wiped a half-typed
  // answer.
  const learnModeRef = useRef(learnMode)
  learnModeRef.current = learnMode
  // Identifies one attempt at the current card to the server, so a confirm
  // that is sent twice is recorded once. Renewed whenever a card is (re)shown.
  const reviewAttemptIdRef = useRef(newReviewAttemptId())
  const [lesson, setLesson] = useState<Lesson | null>(null)
  const [lessonLoading, setLessonLoading] = useState(false)
  const [taught, setTaught] = useState(false)

  // Pre-answer Related Content Primer: User option to review related source
  // content / citations before being asked and committing an answer.
  const [showPrimer, setShowPrimer] = useState(false)
  const [primerLesson, setPrimerLesson] = useState<Lesson | null>(null)
  const [primerLoading, setPrimerLoading] = useState(false)

  // Socratic AI Guide: one diagnostic question at a time, never the answer.
  // Stateless on the server — the full history rides along with each turn.
  const [guideOpen, setGuideOpen] = useState(false)
  const [guideHistory, setGuideHistory] = useState<SocraticTurn[]>([])
  const [guideInput, setGuideInput] = useState('')
  const [guideLoading, setGuideLoading] = useState(false)
  const [guideDegraded, setGuideDegraded] = useState<string | null>(null)
  // The guide signalling "you've got it" — the cue to stop hinting and commit
  // an answer, which is the only way out of the loop that earns a grade.
  const [guideOnTrack, setGuideOnTrack] = useState(false)

  // Longitudinal Weakness Memory Hint
  const [weaknessHint, setWeaknessHint] = useState<string | null>(null)
  const [weaknessHintError, setWeaknessHintError] = useState<string | null>(null)
  const [weaknessHintLoading, setWeaknessHintLoading] = useState(false)
  const [showWeaknessHint, setShowWeaknessHint] = useState(false)

  // Socratic Line-by-Line Hint in IDE (§Feature)
  const [activeLineHint, setActiveLineHint] = useState<SocraticLineHintResponse | null>(null)
  const [lineHintLoading, setLineHintLoading] = useState(false)
  const [editorCursorLine, setEditorCursorLine] = useState(1)

  // Card Failure Memory Reminder (§Feature)
  const [failureReminderEnabled, setFailureReminderEnabled] = useState<boolean>(() => {
    return storage.get('memorization.failureReminderEnabled') !== 'false'
  })
  const [dismissedReminderCardId, setDismissedReminderCardId] = useState<string | null>(null)

  const currentFailureReminder = useMemo(() => {
    if (!item || item.kind !== 'card') return null
    if (item.failure_reminder) return item.failure_reminder
    if (item.active_weaknesses && item.active_weaknesses.length > 0) {
      const w = String(item.active_weaknesses[0]).trim().replace(/\.+$/, '')
      if (item.active_weaknesses.length > 1) {
        return `Where you stumbled: ${w} (+${item.active_weaknesses.length - 1} other flaw)`
      }
      return `Where you stumbled: ${w}`
    }
    return null
  }, [item])

  const renderFailureReminder = () => {
    if (!currentFailureReminder || !failureReminderEnabled || dismissedReminderCardId === item?.id) {
      return null
    }

    return (
      <div className="rounded-xl border border-amber-500/40 bg-gradient-to-r from-amber-950/40 via-[#18130c] to-[#120f0c] p-3 text-xs text-amber-200 shadow-md flex items-start justify-between gap-3 animate-in fade-in duration-200 mb-3">
        <div className="flex items-start gap-2.5 min-w-0">
          <div className="space-y-0.5 min-w-0">
            <div className="flex items-center gap-2">
              <span className="font-bold uppercase tracking-wider text-[0.625rem] text-amber-400">
                Past Failure Memory
              </span>
              <span className="text-[0.625rem] text-amber-300/90 font-mono">
                • avoid repeating this mistake
              </span>
            </div>
            <p className="text-amber-100 leading-relaxed break-words font-medium">
              {currentFailureReminder}
            </p>
          </div>
        </div>
        <div className="flex items-center gap-1 shrink-0">
          <button
            type="button"
            onClick={() => setDismissedReminderCardId(item?.id ?? null)}
            className="text-amber-300/90 hover:text-amber-200 text-xs px-1.5 py-0.5 rounded hover:bg-amber-500/10 cursor-pointer transition font-mono"
            title="Dismiss reminder for this card"
          >
            ✕
          </button>
        </div>
      </div>
    )
  }

  // Deck Cards Quick Browser Drawer (§Feature)
  const [deckViewerOpen, setDeckViewerOpen] = useState(false)
  // Return to All Cards viewer when a single card was studied via "Study now"
  const [returnToDeckViewerOnComplete, setReturnToDeckViewerOnComplete] = useState<boolean>(() => {
    try {
      const params = new URLSearchParams(window.location.search)
      return Boolean(params.get('card') || params.get('card_id') || params.get('from_viewer'))
    } catch {
      return false
    }
  })
  const [lastStudiedCardId, setLastStudiedCardId] = useState<string | null>(() => {
    try {
      const params = new URLSearchParams(window.location.search)
      return params.get('card') || params.get('card_id') || null
    } catch {
      return null
    }
  })
  const [lastStudiedDeckId, setLastStudiedDeckId] = useState<string | null>(() => {
    try {
      const params = new URLSearchParams(window.location.search)
      return params.get('deck') || null
    } catch {
      return null
    }
  })

  // Saved for Later Shelf Drawer (§Feature)
  const [savedDrawerOpen, setSavedDrawerOpen] = useState(false)
  const [savedCount, setSavedCount] = useState(() => getSavedDraftsCount())
  const [draftRestoredNotice, setDraftRestoredNotice] = useState<string | null>(null)

  useEffect(() => {
    const handleDraftsChange = () => setSavedCount(getSavedDraftsCount())
    window.addEventListener('savedCardDraftsChanged', handleDraftsChange)
    return () => window.removeEventListener('savedCardDraftsChanged', handleDraftsChange)
  }, [])

  // ── Neuroscience Enhancements State ─────────────────────────────────────────
  const [showMnemonic, setShowMnemonic] = useState(false)
  const [mnemonicLoading, setMnemonicLoading] = useState(false)
  const [mnemonicText, setMnemonicText] = useState<string | null>(null)

  const [mutatedPrompt, setMutatedPrompt] = useState<string | null>(null)
  const [mutationType, setMutationType] = useState<string>('counterfactual')
  const [mutationLoading, setMutationLoading] = useState(false)

  const [showAssociative, setShowAssociative] = useState(false)
  const [associativeLoading, setAssociativeLoading] = useState(false)
  const [relatedNodes, setRelatedNodes] = useState<SpreadingActivationNode[]>([])

  const [showPretest, setShowPretest] = useState(false)
  const [pretestPrediction, setPretestPrediction] = useState('')
  const [pretestConfidence, setPretestConfidence] = useState(2)
  const [pretestResult, setPretestResult] = useState<PretestPredictionResponse | null>(null)
  const [pretestSubmitting, setPretestSubmitting] = useState(false)

  useEffect(() => {
    setShowMnemonic(false)
    setMnemonicText(item?.mnemonic_vignette || null)
    setMutatedPrompt(null)
    setShowAssociative(false)
    setRelatedNodes([])
    setPretestPrediction('')
    setPretestResult(null)
    if (user?.enable_prediction_mode && item?.state === 'new') {
      setShowPretest(true)
    } else {
      setShowPretest(false)
    }
  }, [item?.id, user?.enable_prediction_mode])

  const handleToggleMnemonic = async () => {
    if (showMnemonic) {
      setShowMnemonic(false)
      return
    }
    setShowMnemonic(true)
    if (!mnemonicText && item?.id) {
      setMnemonicLoading(true)
      try {
        const res = await api.generateMnemonic(item.id)
        setMnemonicText(res.mnemonic_vignette)
      } catch (err) {
        console.error('Failed to generate mnemonic:', err)
      } finally {
        setMnemonicLoading(false)
      }
    }
  }

  const handleRegenerateMnemonic = async () => {
    if (!item?.id) return
    setMnemonicLoading(true)
    try {
      const res = await api.generateMnemonic(item.id)
      setMnemonicText(res.mnemonic_vignette)
    } catch (err) {
      console.error('Failed to regenerate mnemonic:', err)
    } finally {
      setMnemonicLoading(false)
    }
  }

  const handleMutatePrompt = async (mType?: string) => {
    if (!item?.id) return
    const targetType = mType || mutationType
    setMutationLoading(true)
    try {
      const res = await api.mutatePrompt(item.id, targetType)
      setMutatedPrompt(res.mutated_prompt)
      setMutationType(targetType)
    } catch (err) {
      console.error('Failed to mutate prompt:', err)
    } finally {
      setMutationLoading(false)
    }
  }

  const handleToggleAssociative = async () => {
    if (showAssociative) {
      setShowAssociative(false)
      return
    }
    setShowAssociative(true)
    if (relatedNodes.length === 0 && item?.id) {
      setAssociativeLoading(true)
      try {
        const res = await api.getRelatedCards(item.id)
        setRelatedNodes(res.activated_nodes)
      } catch (err) {
        console.error('Failed to get related cards:', err)
      } finally {
        setAssociativeLoading(false)
      }
    }
  }

  const handleSubmitPretest = async () => {
    if (!item?.id || !pretestPrediction.trim()) return
    setPretestSubmitting(true)
    try {
      const res = await api.submitPrediction(item.id, pretestPrediction.trim(), pretestConfidence)
      setPretestResult(res)
    } catch (err) {
      console.error('Failed to submit pretest prediction:', err)
    } finally {
      setPretestSubmitting(false)
    }
  }

  useEffect(() => {
    if (!item) {
      if (session) {
        setCognitiveContext('mastery')
      } else {
        setCognitiveContext(null)
      }
      return
    }

    if (
      codeRunResult &&
      (codeRunResult.passed_count < codeRunResult.total_count ||
        codeRunResult.status === 'Runtime Error')
    ) {
      setCognitiveContext('diagnostic')
      return
    }

    if (item.state === 'new' || item.kind === 'extract' || learnMode) {
      setCognitiveContext('acquisition')
      return
    }

    if (!revealed) {
      setCognitiveContext('recall')
      return
    }

    setCognitiveContext('acquisition')
  }, [item, session, revealed, codeRunResult, learnMode, setCognitiveContext])

  async function handleRequestWeaknessHint() {
    if (!item || item.kind !== 'card') return
    setWeaknessHintLoading(true)
    setWeaknessHintError(null)
    setWeaknessHint(null)
    setShowWeaknessHint(true)
    try {
      const res = await api.weaknessHint(item.id)
      setWeaknessHint(res.hint)
    } catch (err) {
      setWeaknessHintError(err instanceof Error ? err.message : 'Past mistake hint failed')
      setError(err)
    } finally {
      setWeaknessHintLoading(false)
    }
  }

  const shownAt = useRef<number>(Date.now())
  const inputRef = useRef<HTMLTextAreaElement>(null)


  // Blitz countdown. The remaining time is derived from a fixed deadline
  // rather than decremented: the old interval was torn down and restarted on
  // every answer (its effect depended on the running tallies), losing up to a
  // second each time, so a "60s" sprint ran long.
  const blitzDeadlineRef = useRef(0)
  useEffect(() => {
    if (!blitzActive) return
    const tick = () =>
      setBlitzTimeRemainingSec(
        Math.max(0, Math.ceil((blitzDeadlineRef.current - Date.now()) / 1000)),
      )
    tick()
    const timer = setInterval(tick, 250)
    return () => clearInterval(timer)
  }, [blitzActive])

  // Sprint finished: compute the scorecard from the final tallies.
  useEffect(() => {
    if (!blitzActive || blitzTimeRemainingSec > 0) return
    setBlitzActive(false)
    const total = blitzCardsAnswered
    const avgLatency =
      blitzLatencies.length > 0
        ? blitzLatencies.reduce((a, b) => a + b, 0) / blitzLatencies.length / 1000.0
        : 0
    const autoThreshold = user?.automaticity_threshold_ms ?? 3000
    const autoCount = blitzLatencies.filter((l) => l <= autoThreshold).length
    setBlitzStats({
      total,
      correct: blitzCorrectCount,
      avgLatencySec: Math.round(avgLatency * 10) / 10,
      cpm: Math.round((total / (blitzDurationSec / 60)) * 10) / 10,
      automaticityRate: total > 0 ? Math.round((autoCount / total) * 100) : 100,
    })
    setBlitzSummaryOpen(true)
  }, [
    blitzActive,
    blitzTimeRemainingSec,
    blitzCardsAnswered,
    blitzCorrectCount,
    blitzLatencies,
    blitzDurationSec,
    user?.automaticity_threshold_ms,
  ])

  function startBlitz(durationSec: number) {
    blitzDeadlineRef.current = Date.now() + durationSec * 1000
    setBlitzDurationSec(durationSec)
    setBlitzTimeRemainingSec(durationSec)
    setBlitzCardsAnswered(0)
    setBlitzCorrectCount(0)
    setBlitzLatencies([])
    setBlitzActive(true)
    setBlitzSummaryOpen(false)
    setBlitzStats(null)
  }

  function stopBlitz() {
    setBlitzActive(false)
  }

  const initCardState = useCallback((next: QueueItem | null) => {
    const existingDraft = next ? getDraftForCard(next.id) : null
    if (existingDraft) {
      setAnswer(existingDraft.answer)
      setTestCode(existingDraft.testCode || buildStarterTestCode(next))
      if (existingDraft.codeLanguage) {
        setCodeLanguage(existingDraft.codeLanguage)
      }
      setDraftRestoredNotice(`Restored saved draft from ${new Date(existingDraft.savedAt).toLocaleTimeString()}`)
    } else {
      setDraftRestoredNotice(null)
      setAnswer(next?.starter_code || '')
      const starterTests = buildStarterTestCode(next)
      const refTests = buildCompletedTestCode(next)
      setTestCode(starterTests.trim() ? starterTests : (learnModeRef.current ? refTests : ''))
      if (next?.starter_code) {
        if (next.starter_code.includes('def ') || next.starter_code.includes('class Solution:')) {
          setCodeLanguage('python')
        } else if (
          next.starter_code.includes('function') ||
          next.starter_code.includes('interface ') ||
          next.starter_code.includes(': number') ||
          next.starter_code.includes('const ') ||
          next.starter_code.includes('let ')
        ) {
          setCodeLanguage('typescript')
        }
      }
    }
    setActiveEditorTab('solution')
    setResult(null)
    setVramDismissed(false)
    setRevealed(false)
    setSkipReviewRecording(false)
    setConfidence(null)
    setLesson(null)
    setTaught(false)
    setShowPrimer(false)
    setPrimerLesson(null)
    setPrimerLoading(false)
    setGuideOpen(false)
    setGuideHistory([])
    setGuideInput('')
    setGuideDegraded(null)
    setGuideOnTrack(false)
    setCodeRunResult(null)
    setCodeRunning(false)
    setWeaknessHint(null)
    setWeaknessHintError(null)
    setWeaknessHintLoading(false)
    setShowWeaknessHint(false)
    setActiveLineHint(null)
    setLineHintLoading(false)
    setSharedQaHistory([])
    setEditorCursorLine(1)
    setDismissedReminderCardId(null)
    shownAt.current = Date.now()
    reviewAttemptIdRef.current = newReviewAttemptId()
    setDeckStatsTrigger((prev) => prev + 1)
  }, [])

  const handleJumpToCard = useCallback(
    (selectedCard: QueueItem) => {
      setItem(selectedCard)
      initCardState(selectedCard)
      setRevealed(false)
      setSkipReviewRecording(false)
      setResult(null)
      setLastOutcome(`Switched to card: ${selectedCard.title || 'Selected card'}`)
      if (persistActive) {
        setPersistPendingQueue((prev) => [selectedCard.id, ...prev.filter((id) => id !== selectedCard.id)])
      }
      setLastStudiedCardId(selectedCard.id)
      setLastStudiedDeckId(selectedCard.deck_or_source_id || deckParam || persistDeckId || null)
      setReturnToDeckViewerOnComplete(true)
      setDeckViewerOpen(false)
    },
    [initCardState, persistActive, deckParam, persistDeckId],
  )

  const load = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const activeDeck = !persistParam && !runParam ? deckParam : null
      const [next, summary] = await Promise.all([
        api.nextItem(branch, activeDeck),
        api.session(branch, activeDeck),
      ])
      setItem(next)
      setSession(summary)
      initCardState(next)
    } catch (err) {
      setError(err)
    } finally {
      setLoading(false)
    }
  }, [branch, deckParam, persistParam, runParam, initCardState])

  const startPersistMode = useCallback(
    async (deckId: string, deckName?: string, unseenOnly: boolean = false) => {
      setLoading(true)
      setError(null)
      setPersistActive(true)
      setPersistUnseenOnly(unseenOnly)
      setPersistDeckId(deckId)
      setPersistCompleted(false)
      setPersistRound(1)
      setPersistTotalReviews(0)
      setPersistGraspedIds(new Set())
      setPersistCardAttempts({})
      persistRecordedRef.current = new Set()

      setParams((p) => {
        const next = new URLSearchParams(p)
        next.set('deck', deckId)
        next.set('persist', '1')
        if (unseenOnly) {
          next.set('unseen', '1')
        } else {
          next.delete('unseen')
        }
        return next
      })

      try {
        const cards = await api.deckPersistItems(deckId, unseenOnly)
        setPersistCards(cards)
        const dName =
          cards[0]?.deck_name ||
          deckName ||
          allDecks.find((d) => d.id === deckId)?.name ||
          'Selected Deck'
        setPersistDeckName(dName)

        if (cards.length === 0) {
          setPersistPendingQueue([])
          setItem(null)
        } else {
          // Read from the address bar: this callback does not re-create when
          // the query string changes.
          const urlParams = new URLSearchParams(window.location.search)
          const cardParam = urlParams.get('card') || urlParams.get('card_id')
          const targetCard = (cardParam && cards.find((c) => c.id === cardParam)) || cards[0]
          const queue = [targetCard.id, ...cards.filter((c) => c.id !== targetCard.id).map((c) => c.id)]
          setPersistPendingQueue(queue)
          setItem(targetCard)
          initCardState(targetCard)
        }
      } catch (err) {
        setError(err)
        setPersistActive(false)
      } finally {
        setLoading(false)
      }
    },
    [allDecks, initCardState, setParams],
  )

  const exitPersistMode = useCallback(() => {
    activeDeckRef.current = null
    setPersistActive(false)
    setPersistUnseenOnly(false)
    setPersistDeckId(null)
    setPersistCards([])
    setPersistGraspedIds(new Set())
    setPersistPendingQueue([])
    setPersistCompleted(false)
    setPersistCardAttempts({})
    setParams((p) => {
      const next = new URLSearchParams(p)
      next.delete('deck')
      next.delete('persist')
      next.delete('unseen')
      return next
    })
    void load()
  }, [load, setParams])

  const startAllCardsRun = useCallback(
    async (deckId: string, deckName?: string, forceStartIndex?: number) => {
      setLoading(true)
      setError(null)
      // Cancel persist mode if running
      setPersistActive(false)
      setAllCardsRunActive(true)
      setAllCardsRunDeckId(deckId)
      setAllCardsRunCompleted(false)

      setParams((p) => {
        const next = new URLSearchParams(p)
        next.set('deck', deckId)
        next.set('run', 'all')
        next.delete('persist')
        return next
      })

      try {
        const cards = await api.deckAllCardsRunItems(deckId)
        setAllCardsRunCards(cards)
        const dName =
          cards[0]?.deck_name ||
          deckName ||
          allDecks.find((d) => d.id === deckId)?.name ||
          'Selected Deck'
        setAllCardsRunDeckName(dName)

        if (cards.length === 0) {
          setItem(null)
          setAllCardsRunIndex(0)
        } else {
          let targetIndex = 0
          if (forceStartIndex !== undefined) {
            targetIndex = forceStartIndex
          } else {
            const saved = getAllCardsRunProgress(deckId)
            if (saved && typeof saved.index === 'number' && saved.index > 0 && saved.index < cards.length) {
              targetIndex = saved.index
            }
          }

          setAllCardsRunIndex(targetIndex)
          setItem(cards[targetIndex])
          initCardState(cards[targetIndex])
          saveAllCardsRunProgress({
            deckId,
            deckName: dName,
            index: targetIndex,
            total: cards.length,
            cardId: cards[targetIndex]?.id,
            updatedAt: Date.now(),
          })

          if (targetIndex > 0) {
            setLastOutcome(`All Cards Run resumed — Card ${targetIndex + 1} of ${cards.length} (Easiest → Hardest).`)
          } else {
            setLastOutcome(`All Cards Run started — Card 1 of ${cards.length} (Easiest → Hardest).`)
          }
        }
      } catch (err) {
        setError(err)
        setAllCardsRunActive(false)
      } finally {
        setLoading(false)
      }
    },
    [allDecks, initCardState, setParams],
  )

  const exitAllCardsRun = useCallback(() => {
    setAllCardsRunActive(false)
    setAllCardsRunDeckId(null)
    setAllCardsRunCards([])
    setAllCardsRunIndex(0)
    setAllCardsRunCompleted(false)
    setParams((p) => {
      const next = new URLSearchParams(p)
      next.delete('run')
      next.delete('all_cards_run')
      return next
    })
    void load()
  }, [load, setParams])

  const handleContinuePersisting = useCallback(() => {
    if (persistCards.length === 0) return
    setPersistGraspedIds(new Set())
    const allIds = persistCards.map((c) => c.id)
    setPersistPendingQueue(allIds)
    setPersistRound((prev) => prev + 1)
    setPersistCompleted(false)
    const first = persistCards[0]
    setItem(first)
    initCardState(first)
    setLastOutcome(
      `Round ${persistRound + 1} started — persisting until all cards are Easy again!`,
    )
  }, [initCardState, persistCards, persistRound])

  const handleRestartPersistRound = useCallback(() => {
    if (persistCards.length === 0) return
    setPersistGraspedIds(new Set())
    const allIds = persistCards.map((c) => c.id)
    setPersistPendingQueue(allIds)
    setPersistCompleted(false)
    const first = persistCards[0]
    setItem(first)
    initCardState(first)
    setLastOutcome('Persist round restarted — all cards back in rotation.')
  }, [initCardState, persistCards])

  const handleSaveForLater = useCallback(async () => {
    if (!item || item.kind !== 'card') return

    const cardTitle = item.title || (item.front ? item.front.slice(0, 80) : 'Card draft')
    const draft: SavedCardDraft = {
      cardId: item.id,
      deckId: item.deck_or_source_id || null,
      deckName: item.deck_name || persistDeckName || null,
      title: cardTitle,
      frontSnippet: item.front ? item.front.slice(0, 160) : '',
      answer,
      testCode,
      codeLanguage,
      savedAt: Date.now(),
      isCodeCard: checkIsCodeCard(item),
      card: item,
    }

    saveDraft(draft)
    setSavedCount(getSavedDraftsCount())
    setLastOutcome(`Saved "${cardTitle}" for later — draft preserved!`)

    // Postpone on backend so queue advances without repeating this card immediately
    try {
      await api.postponeCard(item.id, 4)
    } catch (err) {
      console.warn('Could not postpone card on server:', err)
    }

    // Advance session
    if (persistActive) {
      if (persistPendingQueue.length > 1) {
        const rest = persistPendingQueue.filter((id) => id !== item.id)
        const nextQueue = [...rest, item.id]
        setPersistPendingQueue(nextQueue)
        const nextCard = persistCards.find((c) => c.id === nextQueue[0]) || null
        setItem(nextCard)
        initCardState(nextCard)
      } else {
        initCardState(item)
      }
    } else {
      await load()
    }
  }, [
    item,
    persistDeckName,
    answer,
    testCode,
    codeLanguage,
    persistActive,
    persistPendingQueue,
    persistCards,
    initCardState,
    load,
  ])

  const handleResumeSavedDraft = useCallback((draft: SavedCardDraft) => {
    setItem(draft.card)
    setAnswer(draft.answer)
    setTestCode(draft.testCode)
    if (draft.codeLanguage) {
      setCodeLanguage(draft.codeLanguage)
    }
    setRevealed(false)
    setSkipReviewRecording(false)
    setResult(null)
    setDraftRestoredNotice(`Resumed draft saved at ${new Date(draft.savedAt).toLocaleTimeString()}`)
    setLastOutcome(`Resumed saved card: ${draft.title}`)
    if (persistActive) {
      setPersistPendingQueue((prev) => [draft.cardId, ...prev.filter((id) => id !== draft.cardId)])
    }
    setSavedDrawerOpen(false)
  }, [persistActive])

  function toggleLayoutMode() {
    setLayoutMode((prev) => {
      const next = prev === 'split' ? 'classic' : 'split'
      storage.set('memorization.reviewLayoutMode', next)
      return next
    })
  }

  async function handleRunReviewCode(customCases?: Array<{ input: any; expected: any }>) {
    if (!item || item.kind !== 'card') return
    setCodeRunning(true)
    try {
      const res = await api.runReviewCode(item.id, {
        code: answer,
        test_code: testCode,
        custom_test_cases: customCases,
        language: codeLanguage,
      })
      setCodeRunResult(res)
    } catch (err) {
      setCodeRunResult({
        status: 'Runtime Error',
        passed_count: 0,
        total_count: item.test_cases?.length || 0,
        runtime_ms: 0,
        error: err instanceof Error ? err.message : String(err),
        results: [],
      })
    } finally {
      setCodeRunning(false)
    }
  }

  useEffect(() => {
    api.decks().then(setAllDecks).catch(() => {})
  }, [])

  useEffect(() => {
    if (runParam && deckParam) {
      if (activeDeckRef.current !== deckParam || !allCardsRunActive || allCardsRunDeckId !== deckParam) {
        activeDeckRef.current = deckParam
        void startAllCardsRun(deckParam)
      }
    } else if (persistParam && deckParam) {
      if (
        activeDeckRef.current !== deckParam ||
        !persistActive ||
        persistDeckId !== deckParam ||
        persistUnseenOnly !== unseenParam
      ) {
        activeDeckRef.current = deckParam
        void startPersistMode(deckParam, undefined, unseenParam)
      }
    } else {
      activeDeckRef.current = null
      void load()
    }
  }, [
    deckParam,
    persistParam,
    unseenParam,
    runParam,
    load,
    startPersistMode,
    startAllCardsRun,
    persistActive,
    persistDeckId,
    persistUnseenOnly,
    allCardsRunActive,
    allCardsRunDeckId,
  ])

  const itemId = item?.id ?? null
  const itemKind = item?.kind ?? null
  useEffect(() => {
    if (itemKind === 'card' && !revealed) inputRef.current?.focus()
  }, [itemId, itemKind, revealed])

  // Learn & Practice: fetch the lesson whenever a fresh card needs one — on
  // load, and immediately if the mode is switched on mid-card (before the
  // gate below has been passed for this card).
  useEffect(() => {
    if (!learnMode || !itemId || itemKind !== 'card' || taught) return
    let cancelled = false
    setLessonLoading(true)
    api
      .lesson(itemId)
      .then((l) => {
        if (!cancelled) setLesson(l)
      })
      .catch((err) => setError(err))
      .finally(() => {
        if (!cancelled) setLessonLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [learnMode, itemId, itemKind, taught])

  function toggleLearnMode() {
    setLearnMode((prev) => {
      const next = !prev
      storage.set(LEARN_MODE_KEY, next ? '1' : '0')
      return next
    })
  }

  function continueToQuestion() {
    setTaught(true)
    // Lesson-reading time is not recall time — don't let it pollute the
    // informational latency note.
    shownAt.current = Date.now()
  }

  async function togglePrimer() {
    if (showPrimer) {
      setShowPrimer(false)
      return
    }
    setShowPrimer(true)
    if (!primerLesson && item && item.kind === 'card') {
      setPrimerLoading(true)
      try {
        const l = await api.lesson(item.id)
        setPrimerLesson(l)
      } catch {
        // Fallback gracefully if lesson generation unavailable
      } finally {
        setPrimerLoading(false)
      }
    }
  }

  const llmEnabled = Boolean(user?.llm_grading_consent)

  const handleSwitchModel = useCallback(
    async (modelName: string) => {
      setActiveModel(modelName)
      try {
        await api.updateMe({ grading_model: modelName })
        void refresh?.()
      } catch {
        // ignore
      }
    },
    [refresh],
  )

  const handleGradeWithModel = useCallback(
    async (modelName: string) => {
      setActiveModel(modelName)
      await grade(modelName)
    },
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [item, answer, testCode, activeModel, user],
  )

  async function grade(targetModel?: string, allowSmaller: boolean = false) {
    if (!item || item.kind !== 'card') return

    // Abort previous in-flight grading if still running
    if (gradingAbortRef.current) {
      gradingAbortRef.current.abort()
    }
    const abortController = new AbortController()
    gradingAbortRef.current = abortController

    const modelToUse = targetModel || activeModel || user?.grading_model
    const latency = Date.now() - shownAt.current
    setGrading(true)
    setError(null)
    setVramDismissed(false)
    try {
      const graded = await api.submitAnswer(item.id, answer, latency, testCode, {
        model: modelToUse,
        allow_smaller_model: allowSmaller,
        language: isCurrentCodeCard ? codeLanguage : undefined,
        signal: abortController.signal,
      })
      if (abortController.signal.aborted) return
      setResult(graded)
      setRevealed(true)
      // Only a model the user picked for this grade becomes their saved
      // preference. If the server fell back to a smaller one (out of memory),
      // that is reported on the result (model_used) but changes nothing: it
      // used to be written to the profile, quietly downgrading every later card.
      const actualModel = graded.model_used || modelToUse
      if (targetModel && actualModel === targetModel && targetModel !== user?.grading_model) {
        void api.updateMe({ grading_model: targetModel }).then(() => refresh?.())
      }
    } catch (err: any) {
      if (abortController.signal.aborted || err?.name === 'AbortError') {
        return
      }
      setError(err)
    } finally {
      if (!abortController.signal.aborted) {
        setGrading(false)
      }
    }
  }

  function reveal() {
    if (gradingAbortRef.current) {
      gradingAbortRef.current.abort()
    }
    setGrading(false)
    setRevealed(true)
    setResult(null)
  }

  async function askGuide(message: string) {
    if (!item || item.kind !== 'card') return
    setGuideLoading(true)
    setGuideDegraded(null)
    setError(null)
    try {
      const executionSummary = isCurrentCodeCard ? formatExecutionSummary(codeRunResult) : null
      const resp = await api.guide(item.id, guideHistory, message, {
        model: activeModel,
        allow_smaller_model: false,
        user_code: isCurrentCodeCard ? answer : undefined,
        test_code: isCurrentCodeCard ? testCode || undefined : undefined,
        execution_summary: executionSummary ?? undefined,
      })
      if (resp.degraded) {
        setGuideDegraded(resp.degraded_reason)
        return
      }
      const turns: SocraticTurn[] = [...guideHistory]
      if (message.trim()) turns.push({ role: 'student', text: message.trim() })
      turns.push({ role: 'guide', text: resp.message })
      setGuideHistory(turns)
      setGuideOnTrack(resp.on_track)
      setGuideInput('')
    } catch (err) {
      setGuideDegraded(err instanceof Error ? err.message : String(err))
      setError(err)
    } finally {
      setGuideLoading(false)
    }
  }

  function openGuide() {
    setGuideOpen(true)
    if (guideHistory.length === 0) void askGuide('')
  }

  const handleRequestLineHint = useCallback(
    async (lineNumber?: number, lineText?: string) => {
      if (!item || item.kind !== 'card') return
      const targetLine = lineNumber && lineNumber > 0 ? lineNumber : editorCursorLine
      const lines = answer.split('\n')
      const targetText = lineText !== undefined && lineText !== '' ? lineText : (lines[targetLine - 1] ?? '')
      setLineHintLoading(true)
      setError(null)
      try {
        const resp = await api.socraticLineHint(item.id, {
          code: answer,
          line_number: targetLine,
          language: codeLanguage,
          test_code: testCode || undefined,
          execution_summary: formatExecutionSummary(codeRunResult) ?? undefined,
          model: activeModel,
          allow_smaller_model: false,
        })
        setActiveLineHint(resp)
      } catch (err) {
        const errMsg = err instanceof Error ? err.message : 'Socratic line hint failed'
        setError(err)
        setActiveLineHint({
          hint: '',
          line_number: targetLine,
          current_line_text: targetText,
          degraded: false,
          error: errMsg,
        })
      } finally {
        setLineHintLoading(false)
      }
    },
    [item, answer, codeLanguage, testCode, codeRunResult, editorCursorLine, activeModel]
  )

  async function confirm(
    finalGrade: Grade,
    options?: { retryImmediately?: boolean; forceRecord?: boolean },
  ) {
    if (!item || item.kind !== 'card') return
    if (confirmingRef.current) return
    confirmingRef.current = true
    setConfirming(true)
    const overridden = Boolean(result && !result.degraded_to_manual && result.suggested_grade !== finalGrade)
    const latency = Date.now() - shownAt.current
    const currentItem = item

    // In persist mode only the first rating of a card is scheduled (see
    // persistRecordedRef); "Record review & retry" still records on request.
    const practiceOnly =
      persistActive && persistRecordedRef.current.has(currentItem.id) && !options?.forceRecord

    try {
      const outcome = practiceOnly
        ? null
        : await api.confirmReview(
            currentItem.id,
            finalGrade,
            overridden,
            answer || undefined,
            latency,
            confidence || undefined,
            blitzActive,
            reviewAttemptIdRef.current,
          )
      if (persistActive) persistRecordedRef.current.add(currentItem.id)
      // Counted only once the review is actually recorded.
      if (blitzActive) {
        setBlitzCardsAnswered((prev) => prev + 1)
        if (finalGrade === 'good' || finalGrade === 'easy') {
          setBlitzCorrectCount((prev) => prev + 1)
        }
        setBlitzLatencies((prev) => [...prev, latency])
      }
      if (outcome?.stuck_alert) setStuckAlert(outcome.stuck_alert)
      // Let the session timer refresh its progress toward the card target.
      window.dispatchEvent(new Event(REVIEW_EVENT))

      // Remove any saved draft for this completed card
      removeDraft(currentItem.id)
      setSavedCount(getSavedDraftsCount())

      if (options?.retryImmediately) {
        if (persistActive) {
          setPersistTotalReviews((prev) => prev + 1)
          setPersistCardAttempts((prev) => ({
            ...prev,
            [currentItem.id]: (prev[currentItem.id] || 0) + 1,
          }))
          if (finalGrade === 'easy') {
            setPersistGraspedIds((prev) => new Set([...prev, currentItem.id]))
          }
          setPersistPendingQueue((prev) => [currentItem.id, ...prev.filter((id) => id !== currentItem.id)])
        }
        initCardState(currentItem)
        setAnswer(currentItem.starter_code || '')
        setRevealed(false)
        setResult(null)
        setSkipReviewRecording(false)
        shownAt.current = Date.now()
        setLastOutcome(
          practiceOnly
            ? `${finalGrade.toUpperCase()} (practice pass, not scheduled) · Retrying card immediately.`
            : `${finalGrade.toUpperCase()} recorded · Retrying card immediately.`,
        )
        setDeckStatsTrigger((prev) => prev + 1)
        return
      }

      setPreviousCard(currentItem)

      if (allCardsRunActive) {
        const nextIdx = allCardsRunIndex + 1
        setAllCardsRunIndex(nextIdx)

        if (nextIdx >= allCardsRunCards.length) {
          setAllCardsRunCompleted(true)
          if (allCardsRunDeckId) {
            clearAllCardsRunProgress(allCardsRunDeckId)
          }
          setItem(null)
          setLastOutcome(
            `All Cards Run complete! All ${allCardsRunCards.length} cards in this deck reviewed consecutively from easiest to hardest. FSRS algorithm now takes over.`,
          )
        } else {
          const nextCard = allCardsRunCards[nextIdx]
          setItem(nextCard)
          initCardState(nextCard)
          if (allCardsRunDeckId) {
            saveAllCardsRunProgress({
              deckId: allCardsRunDeckId,
              deckName: allCardsRunDeckName,
              index: nextIdx,
              total: allCardsRunCards.length,
              cardId: nextCard.id,
              updatedAt: Date.now(),
            })
          }
          setLastOutcome(
            `${finalGrade} — Card ${nextIdx + 1} of ${allCardsRunCards.length} in run (Easiest → Hardest).`,
          )
        }
      } else if (persistActive) {
        setPersistTotalReviews((prev) => prev + 1)
        setPersistCardAttempts((prev) => ({
          ...prev,
          [item.id]: (prev[item.id] || 0) + 1,
        }))

        if (finalGrade === 'easy') {
          const nextGrasped = new Set(persistGraspedIds)
          nextGrasped.add(item.id)
          setPersistGraspedIds(nextGrasped)

          const nextQueue = persistPendingQueue.filter((id) => id !== item.id)
          setPersistPendingQueue(nextQueue)

          if (nextQueue.length === 0) {
            setPersistCompleted(true)
            setItem(null)
            setLastOutcome(
              persistUnseenOnly
                ? `Easy — card grasped! All ${persistCards.length} unseen cards in this deck are now rated Easy!`
                : `Easy — card grasped! All ${persistCards.length} cards in this deck are now rated Easy!`,
            )
          } else {
            const nextCard = persistCards.find((c) => c.id === nextQueue[0]) || null
            setItem(nextCard)
            initCardState(nextCard)
            setLastOutcome(`Easy — card grasped! ${nextQueue.length} remaining in rotation.`)
          }
        } else {
          // 'again', 'hard', 'good': not yet easy, keep in rotation
          if (persistPendingQueue.length > 1) {
            const rest = persistPendingQueue.filter((id) => id !== item.id)
            const nextQueue = [...rest, item.id]
            setPersistPendingQueue(nextQueue)
            const nextCard = persistCards.find((c) => c.id === nextQueue[0]) || null
            setItem(nextCard)
            initCardState(nextCard)
          } else {
            initCardState(item)
          }
          setLastOutcome(
            practiceOnly
              ? `${finalGrade} (practice pass, not scheduled) — kept in rotation until rated Easy.`
              : `${finalGrade} recorded — kept in rotation until rated Easy. Further passes are practice.`,
          )
        }
      } else {
        if (outcome) {
          setLastOutcome(
            `${finalGrade} — next in ${formatInterval(outcome.interval_days)}${
              outcome.leech_flagged ? ' · flagged as a leech' : ''
            }${outcome.automaticity_exceeded ? ' · pace notice' : ''}`,
          )
        }
        await load()
      }

      if (returnToDeckViewerOnComplete) {
        setReturnToDeckViewerOnComplete(false)
        setLastStudiedCardId(item.id)
        setLastStudiedDeckId(item.deck_or_source_id || deckParam || persistDeckId || null)
        setDeckViewerOpen(true)
        setParams((p) => {
          const next = new URLSearchParams(p)
          next.delete('card')
          next.delete('card_id')
          next.delete('from_viewer')
          return next
        }, { replace: true })
      }
    } catch (err) {
      setError(err)
    } finally {
      confirmingRef.current = false
      setConfirming(false)
    }
  }

  const advanceWithoutReview = useCallback(async () => {
    if (!item || item.kind !== 'card') return
    const currentCardId = item.id
    const currentDeckId = item.deck_or_source_id || deckParam || persistDeckId || null
    setPreviousCard(item)
    removeDraft(item.id)
    setSavedCount(getSavedDraftsCount())
    setResult(null)
    setRevealed(false)
    setSkipReviewRecording(false)
    setLastOutcome('Card skipped — no review recorded.')

    if (allCardsRunActive) {
      const nextIdx = allCardsRunIndex + 1
      setAllCardsRunIndex(nextIdx)
      if (nextIdx >= allCardsRunCards.length) {
        setAllCardsRunCompleted(true)
        if (allCardsRunDeckId) {
          clearAllCardsRunProgress(allCardsRunDeckId)
        }
        setItem(null)
        setLastOutcome(
          `All Cards Run complete! All ${allCardsRunCards.length} cards in this deck completed.`,
        )
      } else {
        const nextCard = allCardsRunCards[nextIdx]
        setItem(nextCard)
        initCardState(nextCard)
        if (allCardsRunDeckId) {
          saveAllCardsRunProgress({
            deckId: allCardsRunDeckId,
            deckName: allCardsRunDeckName,
            index: nextIdx,
            total: allCardsRunCards.length,
            cardId: nextCard.id,
            updatedAt: Date.now(),
          })
        }
        setLastOutcome(`Card ${nextIdx + 1} of ${allCardsRunCards.length} in run (Unrecorded skip).`)
      }
    } else if (persistActive) {
      if (persistPendingQueue.length > 1) {
        const rest = persistPendingQueue.filter((id) => id !== item.id)
        const nextQueue = [...rest, item.id]
        setPersistPendingQueue(nextQueue)
        const nextCard = persistCards.find((c) => c.id === nextQueue[0]) || null
        setItem(nextCard)
        initCardState(nextCard)
      } else {
        initCardState(item)
      }
    } else {
      try {
        await api.postponeCard(item.id, 1)
      } catch (err) {
        console.warn('Could not postpone skipped card:', err)
      }
      await load()
    }

    if (returnToDeckViewerOnComplete) {
      setReturnToDeckViewerOnComplete(false)
      setLastStudiedCardId(currentCardId)
      setLastStudiedDeckId(currentDeckId)
      setDeckViewerOpen(true)
      setParams((p) => {
        const next = new URLSearchParams(p)
        next.delete('card')
        next.delete('card_id')
        next.delete('from_viewer')
        return next
      }, { replace: true })
    }
  }, [
    item,
    deckParam,
    persistDeckId,
    returnToDeckViewerOnComplete,
    setParams,
    allCardsRunActive,
    allCardsRunIndex,
    allCardsRunCards,
    allCardsRunDeckId,
    allCardsRunDeckName,
    persistActive,
    persistPendingQueue,
    persistCards,
    initCardState,
    load,
  ])

  const handleSkipGrading = useCallback(() => {
    if (!skipReviewRecording) {
      setSkipReviewRecording(true)
      if (answer.trim()) {
        void grade()
      } else {
        inputRef.current?.focus()
      }
    } else {
      if (revealed) {
        void advanceWithoutReview()
      } else if (answer.trim()) {
        void grade()
      } else {
        void advanceWithoutReview()
      }
    }
  }, [skipReviewRecording, answer, revealed, grade, advanceWithoutReview])

  const handleRetryWithoutRecording = useCallback(() => {
    if (!item || item.kind !== 'card') return
    removeDraft(item.id)
    setSavedCount(getSavedDraftsCount())
    initCardState(item)
    setAnswer(item.starter_code || '')
    setRevealed(false)
    setResult(null)
    setSkipReviewRecording(false)
    shownAt.current = Date.now()
    setLastOutcome('Card reset for immediate retry (unrecorded attempt).')
  }, [item, initCardState])

  const handleRecordAndRetry = useCallback(
    (gradeOverride?: Grade) => {
      const g =
        gradeOverride ||
        (result && !result.degraded_to_manual ? result.suggested_grade : 'hard') ||
        'hard'
      void confirm(g, { retryImmediately: true, forceRecord: true })
    },
    [confirm, result],
  )

  const handleRetryPreviousCard = useCallback(() => {
    if (!previousCard) return
    setItem(previousCard)
    initCardState(previousCard)
    setRevealed(false)
    setSkipReviewRecording(false)
    setResult(null)
    setLastOutcome(`Retrying previous card: ${previousCard.title || 'Previous card'}`)
  }, [previousCard, initCardState])

  const renderRetryActionBar = () => {
    const suggestedGrade: Grade =
      (result && !result.degraded_to_manual ? result.suggested_grade : 'hard') || 'hard'

    // Collapsed by default: grading is the one decision that has to be made
    // after every card, and three retry variants beside it competed with it.
    // The shortcuts (Alt+R, Alt+Shift+R) work whether or not this is open.
    return (
      <details className="mt-3 rounded-lg border border-ink-line/70 bg-ink/40 text-xs">
        <summary className="cursor-pointer select-none rounded-lg px-3 py-1.5 text-slate-400 hover:text-slate-200">
          Retry this card
          {retryAfterRating && <span className="ml-2 text-amber-300">· auto-retry on</span>}
        </summary>
        <div className="flex flex-wrap items-center gap-2 px-3 pb-2.5 pt-1">
          {/* Option 1: Retry without recording review */}
          <button
            type="button"
            onClick={handleRetryWithoutRecording}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-slate-700 bg-slate-800/90 hover:bg-slate-700 hover:border-slate-500 text-slate-200 hover:text-white transition font-medium text-xs cursor-pointer"
            title="Clear and retry this card immediately without recording this review to spaced repetition (Alt+R)"
          >
            <span>Retry without recording</span>
            <kbd className="hidden md:inline px-1 rounded bg-black/40 text-[0.625rem] text-slate-400 font-mono">Alt+R</kbd>
          </button>

          {/* Option 2: Record review and retry */}
          <div className="inline-flex items-center rounded-lg border border-sky-500/50 bg-sky-950/70 p-0.5">
            <button
              type="button"
              onClick={() => handleRecordAndRetry()}
              disabled={confirming}
              className="inline-flex items-center gap-1.5 px-3 py-1 rounded-md bg-sky-700 hover:bg-sky-600 text-white transition font-medium text-xs cursor-pointer disabled:opacity-50"
              title={`Record this review as ${suggestedGrade.toUpperCase()} and immediately retry the card (Alt+Shift+R)`}
            >
              <span>Record review &amp; retry</span>
              <span className="text-[0.625rem] font-mono text-sky-100 bg-sky-800/90 px-1.5 rounded uppercase font-semibold">
                {suggestedGrade}
              </span>
            </button>

            {/* Quick selector to choose a different grade before retrying */}
            <select
              value=""
              aria-label="Record with a different grade and retry"
              onChange={(e) => {
                if (e.target.value) {
                  handleRecordAndRetry(e.target.value as Grade)
                }
              }}
              disabled={confirming}
              className="bg-transparent text-sky-300 hover:text-white text-xs py-1 px-1.5 cursor-pointer border-l border-sky-500/30 font-medium"
              title="Record with a specific grade and retry immediately"
            >
              <option value="" disabled className="bg-[#121622] text-slate-400">Other grade</option>
              <option value="again" className="bg-[#121622] text-rose-300">Again (1)</option>
              <option value="hard" className="bg-[#121622] text-amber-300">Hard (2)</option>
              <option value="good" className="bg-[#121622] text-emerald-300">Good (3)</option>
              <option value="easy" className="bg-[#121622] text-sky-300">Easy (4)</option>
            </select>
          </div>

          {/* Option 3: Auto-retry on rating toggle */}
          <label
            className="inline-flex items-center gap-1.5 text-[0.6875rem] text-slate-300 hover:text-white cursor-pointer select-none px-2 py-1 rounded-lg bg-slate-800/40 hover:bg-slate-800/80 border border-slate-700/60 transition"
            title="When enabled, clicking Again/Hard/Good/Easy (or pressing 1-4) records that rating and automatically starts an immediate retry"
          >
            <input
              type="checkbox"
              checked={retryAfterRating}
              onChange={(e) => setRetryAfterRating(e.target.checked)}
              className="rounded border-slate-600 bg-slate-900 text-sky-500 w-3.5 h-3.5 cursor-pointer"
            />
            <span>Auto-retry on 1–4</span>
          </label>
        </div>
      </details>
    )
  }

  // Keyboard: 1-4 grade after reveal, Space or Ctrl/Cmd+Enter submits/reveals answer.
  useEffect(() => {
    function isTypingTarget(target: EventTarget | null): boolean {
      if (!target || !(target instanceof HTMLElement)) return false
      const tagName = target.tagName.toLowerCase()
      if (tagName === 'input' || tagName === 'textarea' || tagName === 'select') return true
      if (target.isContentEditable) return true
      return Boolean(target.closest('input, textarea, select, [contenteditable="true"]'))
    }

    function onKey(e: KeyboardEvent) {
      if (!item || item.kind !== 'card') return
      // The break overlay hides the card entirely; without this, Ctrl+Enter
      // during a break would reveal or grade a card that isn't on screen.
      if (breakUntil) return
      // The lesson gate has no answer box to submit and no grade to confirm —
      // without this, Ctrl+Enter during the lesson silently reveals the
      // answer before the question is ever shown.
      if (learnMode && !taught) return

      const isTyping = isTypingTarget(e.target) || isTypingTarget(document.activeElement)
      const isEditorTyping = isTyping && document.activeElement !== inputRef.current

      // 1-4 rating shortcuts: Only allowed when NOT typing in an editor or text field, and NOT in skipReviewRecording mode
      if (revealed && e.key >= '1' && e.key <= '4' && !isTyping && !e.ctrlKey && !e.metaKey && !e.altKey) {
        if (!skipReviewRecording) {
          e.preventDefault()
          void confirm(GRADES[Number(e.key) - 1], { retryImmediately: retryAfterRating })
        }
      }
      // Alt shortcuts are matched on the physical key (e.code), not the
      // character: on macOS Option+letter types a symbol (Option+S is "ß"),
      // so comparing e.key against a letter never matched there.
      const alt = e.altKey && !e.ctrlKey && !e.metaKey
      const altKey = (code: string) => alt && e.code === code

      // Alt+R or Alt+Shift+R shortcuts to retry current card
      if (revealed && altKey('KeyR')) {
        e.preventDefault()
        if (e.shiftKey) {
          handleRecordAndRetry()
        } else {
          handleRetryWithoutRecording()
        }
      }
      // Space or Enter after reveal in skipReviewRecording mode: advance to next card without recording
      if (revealed && skipReviewRecording && (e.key === 'Enter' || e.key === ' ') && !isTyping && !isEditorTyping && !e.ctrlKey && !e.metaKey && !e.altKey) {
        e.preventDefault()
        void advanceWithoutReview()
      }
      if (revealed && e.code === 'KeyC' && (e.metaKey || e.ctrlKey) && e.shiftKey) {
        e.preventDefault()
        void copyLearningSummaryToClipboard({
          item,
          answer,
          testCode,
          result,
          codeLanguage,
          codeRunResult,
        })
      }
      // Alt+S tiles the editor; Alt+Shift+S opens the saved-cards drawer.
      // They are one or the other: the drawer shortcut used to trigger both.
      if (altKey('KeyS')) {
        e.preventDefault()
        if (e.shiftKey) {
          setSavedDrawerOpen((prev) => !prev)
        } else {
          toggleTiledTabs()
        }
      }
      if (revealed && checkIsCodeCard(item) && altKey('KeyU')) {
        e.preventDefault()
        handleHideSolution('hint')
      }
      if (altKey('KeyT')) {
        e.preventDefault()
        if (tiledTabs) {
          if (tileLeftTab === 'solution' && tileRightTab === 'tests') {
            setTileLeftTab('reference')
            setTileRightTab('solution')
          } else if (tileLeftTab === 'reference' && tileRightTab === 'solution') {
            setTileLeftTab('reference')
            setTileRightTab('tests')
          } else {
            setTileLeftTab('solution')
            setTileRightTab('tests')
          }
        } else {
          setActiveEditorTab((prev) => (prev === 'solution' ? 'tests' : prev === 'tests' ? 'reference' : prev === 'reference' ? 'ref_tests' : 'solution'))
        }
      }
      if (altKey('KeyD')) {
        e.preventDefault()
        setDeckViewerOpen((prev) => !prev)
      }
      if (altKey('KeyL')) {
        e.preventDefault()
        void handleSaveForLater()
      }
      if (altKey('KeyH')) {
        e.preventDefault()
        void handleRequestLineHint(editorCursorLine)
      }
      if (altKey('KeyG')) {
        e.preventDefault()
        void (answer.trim() ? grade() : reveal())
      }
      if (altKey('KeyP')) {
        e.preventDefault()
        if (isIdePoppedOut) {
          handleDockBackIde()
        } else if (isCurrentCodeCard) {
          handlePopOutIde()
        }
      }
      if (!revealed && (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) && !isEditorTyping) {
        e.preventDefault()
        void (llmEnabled && answer.trim() ? grade() : reveal())
      }
      // Blitz fast-action: In Blitz Mode without active typing, Spacebar reveals
      if (!revealed && blitzActive && e.key === ' ' && !isTyping && !e.ctrlKey && !e.metaKey && !e.altKey) {
        e.preventDefault()
        void reveal()
      }
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  })

  const clearBranch = () => setParams((p) => {
    const next = new URLSearchParams(p)
    next.delete('branch')
    next.delete('deck')
    return next
  })

  // Branched in a helper rather than by returning early: `loading` flips true
  // on every card advance, and an early return there would unmount the session
  // timer between cards. It has to outlive the card it was started on.
  const renderBody = () => {
    if (loading) return <Spinner label="Composing your session…" />
    if (error && !item) return <ErrorNote error={error} />

    const deckActive = Boolean(deckParam && !persistActive && !allCardsRunActive)
    const activeDeckName =
      allDecks.find((d) => d.id === deckParam)?.name || item?.deck_name || undefined

    if (allCardsRunCompleted) {
      return (
        <div className="space-y-6">
          <SessionHeader
            session={session}
            outcome={lastOutcome}
            allCardsRunActive={allCardsRunActive}
            allCardsRunDeckName={allCardsRunDeckName}
            onExitAllCardsRun={exitAllCardsRun}
            learnMode={learnMode}
            onToggleLearnMode={toggleLearnMode}
            savedCount={savedCount}
            onOpenSavedDrawer={() => setSavedDrawerOpen(true)}
          />
          <div className="rounded-3xl border border-purple-500/40 bg-gradient-to-b from-[#140b24] via-[#0d091a] to-[#0b101b] p-8 sm:p-10 text-center max-w-xl mx-auto space-y-6 shadow-2xl backdrop-blur">
            <div className="inline-flex h-20 px-4 items-center justify-center rounded-3xl bg-purple-500/15 border border-purple-500/30 shadow-inner">
              <span className="text-xs font-bold uppercase tracking-wider text-purple-300">Run Complete</span>
            </div>
            <div className="space-y-2">
              <h2 className="text-2xl font-bold text-purple-300">
                All Cards Run Complete!
              </h2>
              <p className="text-sm text-slate-300 max-w-md mx-auto leading-relaxed">
                You've successfully reviewed every card in <strong className="text-white">{allCardsRunDeckName}</strong> consecutively from easiest to hardest!
              </p>
              <p className="text-xs text-purple-200/80 max-w-md mx-auto leading-relaxed">
                All stability states, recall ratings, and review intervals have been recorded. <strong className="text-white">FSRS spaced repetition algorithm now takes over</strong> for future reviews.
              </p>
            </div>

            <div className="grid grid-cols-2 gap-3 py-3 border-y border-purple-500/20 bg-purple-950/20 rounded-xl px-4 text-xs font-mono">
              <div className="space-y-0.5">
                <span className="text-slate-400 text-[0.625rem] uppercase">Cards Reviewed</span>
                <p className="text-white font-bold text-base">{allCardsRunCards.length}</p>
              </div>
              <div className="space-y-0.5 border-l border-purple-500/20">
                <span className="text-slate-400 text-[0.625rem] uppercase">Progression</span>
                <p className="text-purple-300 font-bold text-base">Easiest → Hardest</p>
              </div>
            </div>

            <div className="space-y-3 pt-2">
              <div className="flex flex-col sm:flex-row justify-center gap-3">
                <button
                  type="button"
                  className="btn btn-primary bg-purple-600 hover:bg-purple-500 text-white font-bold flex items-center justify-center gap-2 py-2.5 px-5 shadow-lg shadow-purple-900/40 cursor-pointer"
                  onClick={exitAllCardsRun}
                >
                  
                  <span>Resume Standard FSRS Queue</span>
                </button>
                <button
                  type="button"
                  className="btn border border-ink-line hover:bg-ink-soft text-slate-300 py-2.5 px-4 cursor-pointer"
                  onClick={() => {
                    if (allCardsRunDeckId) {
                      clearAllCardsRunProgress(allCardsRunDeckId)
                      void startAllCardsRun(allCardsRunDeckId, allCardsRunDeckName, 0)
                    } else {
                      exitAllCardsRun()
                    }
                  }}
                >
                  ↻ Run Again (Easiest → Hardest)
                </button>
              </div>
            </div>
          </div>
        </div>
      )
    }

    if (allCardsRunActive && !item && allCardsRunCards.length === 0) {
      return (
        <div className="space-y-6">
          <SessionHeader
            session={session}
            allCardsRunActive={allCardsRunActive}
            allCardsRunDeckName={allCardsRunDeckName}
            onExitAllCardsRun={exitAllCardsRun}
            learnMode={learnMode}
            onToggleLearnMode={toggleLearnMode}
          />
          <Empty title={`No cards in ${allCardsRunDeckName || 'this deck'}.`}>
            <p>This deck doesn't have any cards to review yet. Add cards or import notes to this deck.</p>
            <div className="mt-4 flex justify-center gap-2">
              <button className="btn" onClick={() => navigate('/decks')}>
                Add cards
              </button>
              <button className="btn border border-ink-line" onClick={exitAllCardsRun}>
                Exit All Cards Run
              </button>
            </div>
          </Empty>
        </div>
      )
    }

    if (persistCompleted) {
      return (
        <div className="space-y-6">
          <SessionHeader
            session={session}
            outcome={lastOutcome}
            persistActive={persistActive}
            persistDeckName={persistDeckName}
            persistUnseenOnly={persistUnseenOnly}
            onExitPersist={exitPersistMode}
            persistProgress={{
              grasped: persistGraspedIds.size,
              total: persistCards.length,
              round: persistRound,
            }}
            learnMode={learnMode}
            onToggleLearnMode={toggleLearnMode}
            savedCount={savedCount}
            onOpenSavedDrawer={() => setSavedDrawerOpen(true)}
          />
          <div className="rounded-3xl border border-emerald-500/40 bg-gradient-to-b from-[#0b1b18] via-[#080d16] to-[#0b1424] p-8 sm:p-10 text-center max-w-xl mx-auto space-y-6 shadow-2xl backdrop-blur">
            <div className="inline-flex h-20 px-4 items-center justify-center rounded-3xl bg-emerald-500/15 border border-emerald-500/30 shadow-inner">
              <span className="text-xs font-bold uppercase tracking-wider text-emerald-300">Mastered</span>
            </div>
            <div className="space-y-2">
              <h2 className="text-2xl font-bold text-emerald-300">
                {persistUnseenOnly ? 'All Unseen Cards Grasped!' : 'Deck Fully Grasped!'}
              </h2>
              <p className="text-sm text-slate-300 max-w-md mx-auto leading-relaxed">
                {persistUnseenOnly
                  ? `You've successfully mastered all ${persistCards.length} previously unseen cards in ${persistDeckName} — every single card has been rated Easy!`
                  : `You've successfully mastered all ${persistCards.length} cards in ${persistDeckName} — every single card has been rated Easy!`}
              </p>
            </div>

            <div className="grid grid-cols-3 gap-3 py-3 border-y border-emerald-500/20 bg-emerald-950/20 rounded-xl px-4 text-xs font-mono">
              <div className="space-y-0.5">
                <span className="text-slate-400 text-[0.625rem] uppercase">Cards</span>
                <p className="text-white font-bold text-base">{persistCards.length}</p>
              </div>
              <div className="space-y-0.5 border-x border-emerald-500/20">
                <span className="text-slate-400 text-[0.625rem] uppercase">Total Reviews</span>
                <p className="text-emerald-300 font-bold text-base">{persistTotalReviews}</p>
              </div>
              <div className="space-y-0.5">
                <span className="text-slate-400 text-[0.625rem] uppercase">Rounds</span>
                <p className="text-white font-bold text-base">{persistRound}</p>
              </div>
            </div>

            <div className="space-y-3 pt-2">
              <p className="text-xs text-slate-400">
                Would you like to continue persisting in this deck, or return to your review queue?
              </p>
              <div className="flex flex-col sm:flex-row justify-center gap-3">
                {persistUnseenOnly && persistDeckId && (
                  <button
                    type="button"
                    className="btn btn-primary bg-sky-700 hover:bg-sky-600 text-white font-bold flex items-center justify-center gap-2 py-2.5 px-5 shadow-lg shadow-sky-900/40"
                    onClick={() => startPersistMode(persistDeckId, persistDeckName, false)}
                  >
                    <span>Persist All Cards in Deck</span>
                  </button>
                )}
                <button
                  type="button"
                  className="btn btn-primary bg-emerald-700 hover:bg-emerald-600 text-white font-bold flex items-center justify-center gap-2 py-2.5 px-5 shadow-lg shadow-emerald-900/40"
                  onClick={handleContinuePersisting}
                >
                  <span>{persistUnseenOnly ? 'Restart Unseen Drill' : 'Continue Persisting in this Deck'}</span>
                </button>
                <button
                  type="button"
                  className="btn border border-ink-line hover:bg-ink-soft text-slate-300 py-2.5 px-4"
                  onClick={exitPersistMode}
                >
                  Exit to Normal Queue
                </button>
              </div>
            </div>
          </div>
        </div>
      )
    }

    if (persistActive && !item && persistCards.length === 0) {
      return (
        <div className="space-y-6">
          <SessionHeader
            session={session}
            persistActive={persistActive}
            persistDeckName={persistDeckName}
            persistUnseenOnly={persistUnseenOnly}
            onExitPersist={exitPersistMode}
            learnMode={learnMode}
            onToggleLearnMode={toggleLearnMode}
          />
          {persistUnseenOnly ? (
            <Empty title={`No unseen cards in ${persistDeckName || 'this deck'}.`}>
              <p>All cards in this deck have already been introduced into your review rotation.</p>
              <div className="mt-4 flex justify-center gap-2">
                {persistDeckId && (
                  <button
                    className="btn btn-primary"
                    onClick={() => startPersistMode(persistDeckId, persistDeckName, false)}
                  >
                    Persist All Cards in Deck
                  </button>
                )}
                <button className="btn border border-ink-line" onClick={exitPersistMode}>
                  Exit Persist Mode
                </button>
              </div>
            </Empty>
          ) : (
            <Empty title={`No cards in ${persistDeckName || 'this deck'}.`}>
              <p>This deck doesn't have any cards to review yet. Add cards or import notes to this deck.</p>
              <div className="mt-4 flex justify-center gap-2">
                <button className="btn" onClick={() => navigate('/decks')}>
                  Add cards
                </button>
                <button className="btn border border-ink-line" onClick={exitPersistMode}>
                  Exit Persist Mode
                </button>
              </div>
            </Empty>
          )}
        </div>
      )
    }

    if (!item) {
      return (
        <div className="space-y-6">
          <SessionHeader
            session={session}
            branchActive={Boolean(branch)}
            deckActive={deckActive}
            deckName={activeDeckName}
            onClearBranch={clearBranch}
            learnMode={learnMode}
            onToggleLearnMode={toggleLearnMode}
            allDecks={allDecks}
            onStartPersist={startPersistMode}
            onStartAllCardsRun={startAllCardsRun}
          />
          <Empty
            title={
              branch
                ? 'Nothing due in this branch.'
                : deckActive
                ? `Nothing due in ${activeDeckName || 'this deck'} (or its subdecks).`
                : 'Nothing due right now.'
            }
          >
            <p>
              {branch
                ? 'This branch is caught up. Study everything, or add more under it in the Tree.'
                : deckActive
                ? 'This deck and its subdecks are caught up. Study all decks in the collection, or add more cards in Decks.'
                : 'Your queue is empty for today. Add cards, import a deck, or bring in something to read.'}
            </p>
            <div className="mt-4 flex justify-center gap-2">
              {branch || deckActive ? (
                <button className="btn btn-primary" onClick={clearBranch}>
                  Study all decks
                </button>
              ) : (
                <>
                  <button className="btn" onClick={() => navigate('/decks')}>
                    Add cards
                  </button>
                  <button className="btn" onClick={() => navigate('/read')}>
                    Add reading
                  </button>
                </>
              )}
            </div>

            {/* Persist & All Cards Run Deck Launcher */}
            <div className="mt-8 rounded-2xl border border-sky-500/30 bg-gradient-to-b from-sky-950/20 to-ink-soft/30 p-5 max-w-lg mx-auto text-left shadow-lg">
              <div className="flex items-center gap-2.5 mb-2">
                <span className="flex h-7 px-2 items-center justify-center rounded-lg bg-sky-500/20 text-sky-300 font-bold text-xs uppercase tracking-wider">
                  Modes
                </span>
                <div>
                  <h3 className="font-semibold text-slate-100 text-sm">Deck Study Modes</h3>
                  <p className="text-xs text-slate-400">
                    Drill a deck continuously via <strong className="text-emerald-300 font-semibold">Persist Review</strong> (until all Easy) or run <strong className="text-purple-300 font-semibold">All Cards Run</strong> (easiest to hardest, then FSRS takes over).
                  </p>
                </div>
              </div>

              {allDecks.length > 0 ? (
                <div className="mt-4 space-y-3">
                  <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-2">
                    <select aria-label="Deck to study"
                      className="input flex-1 text-xs py-1.5"
                      value={selectedPersistDeckId}
                      onChange={(e) => setSelectedPersistDeckId(e.target.value)}
                    >
                      <option value="">-- Choose a deck --</option>
                      {allDecks.map((d) => {
                        const viewedPct = d.stats && d.stats.total_cards > 0
                          ? Math.round(d.stats.viewed_ratio * 100)
                          : null
                        return (
                          <option key={d.id} value={d.id}>
                            {d.name} ({d.card_count} {d.card_count === 1 ? 'card' : 'cards'}{viewedPct !== null ? ` · ${viewedPct}% viewed` : ''}{d.new_count > 0 ? ` · ${d.new_count} unseen` : ''})
                          </option>
                        )
                      })}
                    </select>
                    <div className="flex items-center gap-2">
                      <button
                        type="button"
                        disabled={!selectedPersistDeckId}
                        onClick={() => selectedPersistDeckId && startPersistMode(selectedPersistDeckId, undefined, false)}
                        className="btn btn-primary text-xs whitespace-nowrap disabled:opacity-50"
                        title="Persist reviewing until every card in the deck is rated Easy"
                      >
                        Persist All
                      </button>
                      <button
                        type="button"
                        disabled={!selectedPersistDeckId || (allDecks.find((d) => d.id === selectedPersistDeckId)?.new_count ?? 0) === 0}
                        onClick={() => selectedPersistDeckId && startPersistMode(selectedPersistDeckId, undefined, true)}
                        className="btn border border-amber-500/50 bg-amber-500/20 text-amber-200 hover:bg-amber-500/30 text-xs whitespace-nowrap disabled:opacity-50"
                        title={
                          (allDecks.find((d) => d.id === selectedPersistDeckId)?.new_count ?? 0) > 0
                            ? `Persist reviewing only the ${allDecks.find((d) => d.id === selectedPersistDeckId)?.new_count} unseen cards until Easy`
                            : 'No unseen cards in this deck'
                        }
                      >
                        Persist Unseen{' '}
                        {(allDecks.find((d) => d.id === selectedPersistDeckId)?.new_count ?? 0) > 0
                          ? `(${allDecks.find((d) => d.id === selectedPersistDeckId)?.new_count})`
                          : ''}
                      </button>
                      {(() => {
                        const savedRun = selectedPersistDeckId ? getAllCardsRunProgress(selectedPersistDeckId) : null
                        const hasSaved = Boolean(savedRun && savedRun.index > 0 && savedRun.index < savedRun.total)
                        return (
                          <button
                            type="button"
                            disabled={!selectedPersistDeckId}
                            onClick={() => selectedPersistDeckId && startAllCardsRun(selectedPersistDeckId)}
                            className="btn border border-purple-500/50 bg-purple-500/20 text-purple-200 hover:bg-purple-500/30 text-xs whitespace-nowrap disabled:opacity-50"
                            title={
                              hasSaved
                                ? `Resume All Cards Run from Card ${savedRun!.index + 1}`
                                : 'Review every card consecutively from easiest to hardest, then FSRS takes over'
                            }
                          >
                            {hasSaved ? `Resume Run (${savedRun!.index + 1}/${savedRun!.total})` : 'All Cards Run'}
                          </button>
                        )
                      })()}
                    </div>
                  </div>

                  {allDecks.filter((d) => d.card_count > 0).length > 0 && (
                    <div className="flex flex-wrap items-center gap-1.5 pt-1">
                      <span className="text-[0.6875rem] text-slate-500">Quick run:</span>
                      {allDecks
                        .filter((d) => d.card_count > 0)
                        .slice(0, 4)
                        .map((d) => (
                          <button
                            key={d.id}
                            type="button"
                            onClick={() => startAllCardsRun(d.id, d.name)}
                            className="chip border-purple-500/30 hover:border-purple-400 hover:text-purple-200 text-xs transition"
                            title="Run all cards in easiest to hardest order"
                          >
                            {d.name} ({d.card_count})
                          </button>
                        ))}
                    </div>
                  )}
                </div>
              ) : (
                <p className="mt-3 text-xs text-slate-500">
                  No decks available yet. Create or import a deck to start reviewing!
                </p>
              )}
            </div>
          </Empty>
        </div>
      )
    }

    if (item.kind === 'extract') {
      return (
        <div className="space-y-6">
          <SessionHeader
            session={session}
            outcome={lastOutcome}
            branchActive={Boolean(branch)}
            deckActive={deckActive}
            deckName={activeDeckName}
            onClearBranch={clearBranch}
            learnMode={learnMode}
            onToggleLearnMode={toggleLearnMode}
            savedCount={savedCount}
            onOpenSavedDrawer={() => setSavedDrawerOpen(true)}
          />
          <ExtractCard item={item} onDone={load} />
        </div>
      )
    }

    if (learnMode && !taught) {
      return (
        <div className="space-y-6">
          <SessionHeader
            session={session}
            outcome={lastOutcome}
            branchActive={Boolean(branch)}
            deckActive={deckActive}
            deckName={activeDeckName}
            onClearBranch={clearBranch}
            learnMode={learnMode}
            onToggleLearnMode={toggleLearnMode}
            persistActive={persistActive}
            persistDeckName={persistDeckName}
            persistUnseenOnly={persistUnseenOnly}
            onExitPersist={exitPersistMode}
            onStartPersist={startPersistMode}
            allDecks={allDecks}
            savedCount={savedCount}
            onOpenSavedDrawer={() => setSavedDrawerOpen(true)}
          />
          <div className="flex flex-col xl:flex-row items-start justify-center gap-6 max-w-[1750px] mx-auto px-2 sm:px-4">
            <div className="flex-1 w-full max-w-4xl min-w-0 xl:min-w-[500px]">
              <LessonGate
                item={item}
                lesson={lesson}
                loading={lessonLoading}
                deckName={item.deck_name}
                onContinue={continueToQuestion}
                onOpenSettings={() => navigate('/settings')}
                codeLanguage={codeLanguage}
                activeModel={activeModel}
                onActiveModelChange={(m) => void handleSwitchModel(m)}
              />
            </div>
            <aside className="w-full xl:w-80 2xl:w-96 shrink-0 xl:sticky xl:top-16">
              <MarginLexiconPanel
                cardId={item.id}
                deckId={item.kind === 'card' ? item.deck_or_source_id : null}
                deckName={item.deck_name}
                thematicNature={item.card_thematic_nature || item.deck_thematic_nature}
                cardFront={item.front}
                cardBack={item.back}
                initialGlosses={item.lexicon_glosses}
                onGlossesUpdated={(updatedGlosses) => applyGlossesToCard(item.id, updatedGlosses)}
                codeLanguage={codeLanguage}
              />
            </aside>
          </div>
        </div>
      )
    }

    const isCodeCard = Boolean(
      item &&
      item.kind === 'card' &&
      checkIsCodeCard(item)
    )

    const overlookedTerms = result
      ? [
          ...(result.overlooked_phrases ?? []),
          ...result.missed_points.flatMap((mp) => {
            const quotes = mp.match(/["']([^"']{3,})["']/g)
            return quotes ? quotes.map((q) => q.slice(1, -1)) : []
          }),
        ].filter(Boolean)
      : []

    const matchedTerms = result
      ? [
          ...result.matched_points.flatMap((mp) => {
            const quotes = mp.match(/["']([^"']{3,})["']/g)
            return quotes ? quotes.map((q) => q.slice(1, -1)) : []
          }),
        ].filter(Boolean)
      : []

    const cleanRefCode = extractCleanCode(result?.reference_answer || item?.back || '')
    const starterTestsCode = buildStarterTestCode(item)
    const cleanRefTestsCode = buildCompletedTestCode(item)

    const singleRefDiff = !cleanRefCode || !answer.trim()
      ? { refSegments: null, stats: null }
      : computeTokenDiff(answer, cleanRefCode, overlookedTerms, matchedTerms, true)

    const singleTargetRefLines = computeExpectedLines(item?.starter_code, cleanRefCode)
    const firstSingleTargetRefLine = getFirstTargetLine(singleTargetRefLines)
    const executionSummaryStr = formatExecutionSummary(codeRunResult)

  const renderIdeWorkbench = (inPopout = false) => {
    const currentViewportWidth = inPopout
      ? popoutDimensions.width
      : typeof window !== 'undefined'
      ? window.innerWidth
      : 1200

    const isRightDock = workbenchLayout.consoleDockPosition === 'right' && !workbenchLayout.isStacked
    const shouldFillTiledHeight = inPopout || currentViewportWidth >= 1024

    const effectiveEditorHeight = inPopout
      ? isRightDock
        ? `${Math.max(380, popoutDimensions.height - 110)}px`
        : `${Math.max(260, Math.floor(popoutDimensions.height * (workbenchLayout.consoleCollapsed ? 0.85 : 0.58)))}px`
      : `${workbenchLayout.editorHeight}px`

    const effectiveRefHintHeight = inPopout
      ? `${Math.max(100, parseInt(effectiveEditorHeight, 10) - 33)}px`
      : `${Math.max(100, workbenchLayout.editorHeight - 33)}px`

    const workbenchContent = (
              <div
                ref={workbenchLayout.consoleDockPosition === 'right' ? workbenchRowRef : undefined}
                className={
                  isRightDock
                    ? inPopout
                      ? 'flex flex-col lg:flex-row items-stretch h-full flex-1 min-h-0 w-full min-w-0 overflow-hidden'
                      : 'flex flex-col lg:flex-row items-stretch gap-2 w-full min-w-0'
                    : inPopout
                    ? 'flex flex-col h-full flex-1 min-h-0 w-full min-w-0 overflow-hidden'
                    : 'flex flex-col gap-2 w-full min-w-0'
                }
              >
                {/* Editor Container */}
                <div
                  className={
                    isRightDock
                      ? inPopout
                        ? 'flex-1 min-w-[280px] min-w-0 h-full min-h-0 flex flex-col overflow-hidden'
                        : 'flex-1 min-w-[280px] min-w-0'
                      : inPopout
                      ? 'flex-1 min-h-[180px] w-full flex flex-col min-w-0 overflow-hidden'
                      : 'w-full'
                  }
                >
                  <div
                    className={
                      inPopout
                        ? 'bg-[#1a1a1a] h-full flex-1 min-h-0 flex flex-col overflow-hidden border-0 rounded-none'
                        : 'card p-0 overflow-hidden border border-ink-line flex flex-col'
                    }
                  >
                <div className="flex flex-wrap items-center justify-between border-b border-ink-line bg-[#1e1e1e] px-3 py-1.5 text-xs gap-1.5 shrink-0">
                  <div className="flex flex-wrap items-center gap-2">
                    {/* View mode / Tabs selector */}
                    {tiledTabs ? (
                      <div className="flex flex-wrap items-center gap-2">
                        <div className="inline-flex rounded-md bg-[#161616] p-0.5 border border-ink-line shrink-0">
                          <span
                            className="px-2 py-0.5 text-xs font-semibold rounded bg-sky-600/30 text-sky-200 border border-sky-500/50 shadow-sm flex items-center gap-1.5 cursor-default select-none shrink-0"
                            title="Tiled (Alt+S)"
                          >
                            <span>⧉</span>
                            <span>Tiled</span>
                          </span>
                          <button
                            type="button"
                            onClick={toggleTiledTabs}
                            className="px-2 py-0.5 text-xs font-medium rounded text-slate-400 hover:text-slate-200 flex items-center gap-1.5 transition cursor-pointer shrink-0"
                            title="Single tab (Alt+S)"
                          >
                            <span>⊟</span>
                            <span>Single Tab</span>
                          </button>
                        </div>

                        <div className="inline-flex items-center rounded-md bg-[#161616] p-0.5 border border-ink-line shrink-0 overflow-x-auto no-scrollbar">
                          <span className="text-[0.625rem] text-slate-500 px-1.5 font-medium uppercase tracking-wider shrink-0 select-none">Presets:</span>
                          <button
                            type="button"
                            onClick={() => {
                              setTileLeftTab('solution')
                              setTileRightTab('tests')
                            }}
                            className={`px-2 py-0.5 text-xs font-medium rounded transition flex items-center gap-1 cursor-pointer shrink-0 whitespace-nowrap ${
                              tileLeftTab === 'solution' && tileRightTab === 'tests'
                                ? 'bg-sky-600/40 text-sky-100 border border-sky-500/60 shadow-sm font-semibold'
                                : 'text-slate-400 hover:text-slate-200'
                            }`}
                            title="Classic TDD: Solution on left, Unit Tests on right"
                          >
                            <span>Sol</span>
                            <span className="text-slate-500">↔</span>
                            <span>Tests</span>
                          </button>
                          <button
                            type="button"
                            onClick={() => {
                              setTileLeftTab('reference')
                              setTileRightTab('solution')
                            }}
                            className={`px-2 py-0.5 text-xs font-medium rounded transition flex items-center gap-1 cursor-pointer shrink-0 whitespace-nowrap ${
                              tileLeftTab === 'reference' && tileRightTab === 'solution'
                                ? 'bg-sky-600/40 text-sky-100 border border-sky-500/60 shadow-sm font-semibold'
                                : 'text-slate-400 hover:text-slate-200'
                            }`}
                            title="Compare Reference Solution alongside Solution"
                          >
                            <span>Ref</span>
                            <span className="text-slate-500">↔</span>
                            <span>Sol</span>
                          </button>
                          <button
                            type="button"
                            onClick={() => {
                              setTileLeftTab('reference')
                              setTileRightTab('tests')
                            }}
                            className={`px-2 py-0.5 text-xs font-medium rounded transition flex items-center gap-1 cursor-pointer shrink-0 whitespace-nowrap ${
                              tileLeftTab === 'reference' && tileRightTab === 'tests'
                                ? 'bg-sky-600/40 text-sky-100 border border-sky-500/60 shadow-sm font-semibold'
                                : 'text-slate-400 hover:text-slate-200'
                            }`}
                            title="Compare Reference Solution alongside Unit Tests"
                          >
                            <span>Ref</span>
                            <span className="text-slate-500">↔</span>
                            <span>Tests</span>
                          </button>
                          <button
                            type="button"
                            onClick={() => {
                              setTileLeftTab('tests')
                              setTileRightTab('ref_tests')
                            }}
                            className={`px-2 py-0.5 text-xs font-medium rounded transition flex items-center gap-1 cursor-pointer shrink-0 whitespace-nowrap ${
                              tileLeftTab === 'tests' && tileRightTab === 'ref_tests'
                                ? 'bg-purple-600/40 text-purple-100 border border-purple-500/60 shadow-sm font-semibold'
                                : 'text-slate-400 hover:text-slate-200'
                            }`}
                            title="Compare Unit Tests alongside Completed Reference Tests"
                          >
                            <span>Tests</span>
                            <span className="text-slate-500">↔</span>
                            <span>Ref Tests</span>
                          </button>
                          <button
                            type="button"
                            onClick={() => {
                              const prevLeft = tileLeftTab
                              const prevRight = tileRightTab
                              setTileLeftTab(prevRight)
                              setTileRightTab(prevLeft)
                            }}
                            className="px-1.5 py-0.5 text-xs font-medium rounded text-slate-400 hover:text-slate-200 hover:bg-[#282828] transition cursor-pointer border-l border-ink-line/60 ml-0.5 shrink-0 whitespace-nowrap"
                            title="Swap Left and Right panes"
                          >
                            <span>⇄ Swap</span>
                          </button>
                        </div>
                      </div>
                    ) : (
                      <div className="inline-flex rounded-md bg-[#161616] p-0.5 border border-ink-line">
                        <button
                          type="button"
                          onClick={() => setActiveEditorTab('solution')}
                          className={`px-2.5 py-1 text-xs font-medium rounded transition flex items-center gap-1.5 cursor-pointer ${
                            activeEditorTab === 'solution'
                              ? 'bg-sky-600/30 text-sky-200 border border-sky-500/50 shadow-sm'
                              : 'text-slate-400 hover:text-slate-200'
                          }`}
                          title="Solution (Alt+T)"
                        >
                          <span>Solution</span>
                        </button>
                        <button
                          type="button"
                          onClick={() => setActiveEditorTab('tests')}
                          className={`px-2.5 py-1 text-xs font-medium rounded transition flex items-center gap-1.5 cursor-pointer ${
                            activeEditorTab === 'tests'
                              ? 'bg-indigo-600/30 text-indigo-200 border border-indigo-500/50 shadow-sm'
                              : 'text-slate-400 hover:text-slate-200'
                          }`}
                          title="Unit Tests (Alt+T)"
                        >
                          <span>Unit Tests</span>
                          {testCode.trim() && (
                            <span className="w-1.5 h-1.5 rounded-full bg-indigo-400"></span>
                          )}
                        </button>
                        <button
                          type="button"
                          onClick={() => setActiveEditorTab('reference')}
                          className={`px-2.5 py-1 text-xs font-medium rounded transition flex items-center gap-1.5 cursor-pointer ${
                            activeEditorTab === 'reference'
                              ? 'bg-emerald-600/30 text-emerald-200 border border-emerald-500/50 shadow-sm'
                              : 'text-slate-400 hover:text-slate-200'
                          }`}
                          title="Reference"
                        >
                          
                          <span>Reference</span>
                        </button>
                        {Boolean(cleanRefTestsCode.trim()) && (
                          <button
                            type="button"
                            onClick={() => setActiveEditorTab('ref_tests')}
                            className={`px-2.5 py-1 text-xs font-medium rounded transition flex items-center gap-1.5 cursor-pointer ${
                              activeEditorTab === 'ref_tests'
                                ? 'bg-purple-600/30 text-purple-200 border border-purple-500/50 shadow-sm'
                                : 'text-slate-400 hover:text-slate-200'
                            }`}
                            title="Ref Tests"
                          >
                            <span>Ref Tests</span>
                          </button>
                        )}
                        <button
                          type="button"
                          onClick={toggleTiledTabs}
                          className="px-2.5 py-1 text-xs font-medium rounded text-sky-400 hover:text-sky-200 hover:bg-sky-500/10 flex items-center gap-1.5 transition border-l border-ink-line/60 ml-0.5 cursor-pointer"
                          title="Tile side-by-side (Alt+S)"
                        >
                          <span>⧉</span>
                          <span>Tile</span>
                        </button>
                      </div>
                    )}

                    <select aria-label="Code language"
                      value={codeLanguage}
                      onChange={(e) => {
                        const nextLang = e.target.value
                        setCodeLanguage(nextLang)
                        storage.set('memorization.reviewCodeLanguage', nextLang)
                      }}
                      className="rounded border border-ink-line bg-[#282828] px-2 py-0.5 text-xs font-semibold text-slate-200 hover:border-slate-500 focus:outline-none focus:ring-1 focus:ring-sky-500 cursor-pointer shrink-0"
                    >
                      <option value="typescript">TypeScript</option>
                      <option value="javascript">JavaScript</option>
                      <option value="python">Python 3</option>
                    </select>

                    {/* Reset buttons in Single Tab Mode */}
                    {!tiledTabs && activeEditorTab === 'solution' && item.starter_code && (
                      <button
                        type="button"
                        onClick={() => setAnswer(item.starter_code || '')}
                        className="text-slate-400 hover:text-slate-200 text-[0.6875rem] underline cursor-pointer"
                        title="Reset code editor to original starter template"
                      >
                        Reset solution
                      </button>
                    )}
                    {!tiledTabs && activeEditorTab === 'tests' && (
                      <div className="flex items-center gap-2">
                        {!testCode.trim() && Boolean(cleanRefTestsCode) && (
                          <button
                            type="button"
                            onClick={() => setTestCode(cleanRefTestsCode)}
                            className="text-purple-300 hover:text-purple-200 text-[0.6875rem] underline cursor-pointer"
                            title="Load completed reference tests into unit tests editor"
                          >
                            Load reference tests
                          </button>
                        )}
                        <button
                          type="button"
                          onClick={() => setTestCode(buildStarterTestCode(item) || cleanRefTestsCode)}
                          className="text-slate-400 hover:text-slate-200 text-[0.6875rem] underline cursor-pointer"
                          title="Reset unit tests to starter assertions"
                        >
                          Reset tests
                        </button>
                      </div>
                    )}
                    {!tiledTabs && activeEditorTab === 'reference' && (
                      <div className="flex items-center gap-2">
                        {Boolean(cleanRefCode) && (revealed || singleRefViewMode === 'hint') && (
                          <div className="inline-flex rounded-md bg-[#161616] p-0.5 border border-ink-line text-[0.6875rem] shrink-0">
                            <button
                              type="button"
                              onClick={() => {
                                setSingleRefViewMode('ide')
                                storage.set('memorization.refViewMode', 'ide')
                              }}
                              className={`px-2 py-0.5 rounded transition cursor-pointer ${
                                singleRefViewMode === 'ide'
                                  ? 'bg-sky-600/30 text-sky-200 border border-sky-500/50 font-medium'
                                  : 'text-slate-400 hover:text-slate-200'
                              }`}
                              title="IDE syntax-highlighted code format"
                            >
                              IDE
                            </button>
                            {revealed && Boolean(answer.trim()) && (
                              <button
                                type="button"
                                onClick={() => {
                                  setSingleRefViewMode('diff')
                                  storage.set('memorization.refViewMode', 'diff')
                                }}
                                className={`px-2 py-0.5 rounded transition flex items-center gap-1 cursor-pointer ${
                                  singleRefViewMode === 'diff'
                                    ? 'bg-amber-600/30 text-amber-200 border border-amber-500/50 font-medium'
                                    : 'text-slate-400 hover:text-slate-200'
                                }`}
                                title="Token-by-token answer comparison diff against your Solution"
                              >
                                <span>Diff</span>
                                {singleRefDiff.stats && singleRefDiff.stats.missingCount > 0 && (
                                  <span className="inline-block w-1.5 h-1.5 rounded-full bg-amber-400" />
                                )}
                              </button>
                            )}
                            <button
                              type="button"
                              onClick={() => {
                                setSingleRefViewMode('hint')
                                storage.set('memorization.refViewMode', 'hint')
                              }}
                              className={`px-2 py-0.5 rounded transition flex items-center gap-1 cursor-pointer ${
                                singleRefViewMode === 'hint'
                                  ? 'bg-amber-500/30 text-amber-300 border border-amber-500/50 font-medium'
                                  : 'text-slate-400 hover:text-slate-200'
                              }`}
                              title="Hint-only mode: reveals only the current incomplete line"
                            >
                             <span> Hint</span>
                            </button>
                          </div>
                        )}
                        {Boolean(cleanRefCode) && singleRefViewMode === 'ide' && singleTargetRefLines.size > 0 && (
                          <div className="flex items-center gap-1.5 shrink-0 ml-1">
                            <button
                              type="button"
                              onClick={handleToggleFocusTargetCode}
                              className={`px-2 py-0.5 rounded transition flex items-center gap-1 cursor-pointer text-xs ${
                                focusTargetCode
                                  ? 'bg-emerald-600/30 text-emerald-200 border border-emerald-500/50 font-medium shadow-sm'
                                  : 'text-slate-400 hover:text-slate-200 border border-transparent'
                              }`}
                              title={
                                focusTargetCode
                                  ? 'Focus Target Code active: boilerplate starter code is dimmed. Click to show full brightness.'
                                  : 'Click to focus target code (dims boilerplate starter code)'
                              }
                            >
                             <span> Target ({formatTargetLineSummary(singleTargetRefLines)})</span>
                            </button>
                            <HighlightColorPicker
                              color={targetHighlightColor}
                              onChange={handleHighlightColorChange}
                            />
                          </div>
                        )}
                        {revealed && (
                          <button
                            type="button"
                            onClick={() => handleHideSolution('hide')}
                            className="px-2 py-0.5 rounded bg-rose-500/10 hover:bg-rose-500/20 text-rose-300 border border-rose-500/30 text-[0.6875rem] font-medium transition cursor-pointer flex items-center gap-1 shrink-0"
                            title="Hide solution and return to active practice"
                          >
                           <span> Hide</span>
                          </button>
                        )}
                        <button
                          type="button"
                          onClick={() => void handleCopyReferenceCode(cleanRefCode)}
                          disabled={!cleanRefCode}
                          className="text-slate-400 hover:text-slate-200 text-[0.6875rem] flex items-center gap-1 disabled:opacity-30 cursor-pointer"
                          title="Copy reference code to clipboard"
                        >
                          <span>{copiedRef ? 'Copied' : 'Copy ref'}</span>
                        </button>
                      </div>
                    )}
                    {!tiledTabs && activeEditorTab === 'ref_tests' && (
                      <div className="flex items-center gap-2">
                        {Boolean(cleanRefTestsCode) && (
                          <button
                            type="button"
                            onClick={() => {
                              setTestCode(cleanRefTestsCode)
                              setActiveEditorTab('tests')
                            }}
                            className="text-purple-300 hover:text-purple-200 text-[0.6875rem] underline cursor-pointer"
                            title="Load reference tests into editable Unit Tests editor"
                          >
                            Load to tests
                          </button>
                        )}
                        <button
                          type="button"
                          onClick={() => void handleCopyReferenceTests(cleanRefTestsCode)}
                          disabled={!cleanRefTestsCode}
                          className="text-slate-400 hover:text-slate-200 text-[0.6875rem] flex items-center gap-1 disabled:opacity-30 cursor-pointer"
                          title="Copy completed reference tests to clipboard"
                        >
                          <span>{copiedRefTests ? 'Copied' : 'Copy ref tests'}</span>
                        </button>
                      </div>
                    )}
                  </div>

                  <div className="flex items-center gap-3 text-xs shrink-0">
                    <div className="flex items-center gap-1 shrink-0">
                      <span className="text-slate-500 text-[0.6875rem] shrink-0">Confidence:</span>
                      {[
                        { lvl: 1, label: '1', color: 'text-rose-300' },
                        { lvl: 2, label: '2', color: 'text-amber-300' },
                        { lvl: 3, label: '3', color: 'text-sky-300' },
                        { lvl: 4, label: '4', color: 'text-emerald-300' },
                      ].map(({ lvl, label, color }) => (
                        <button
                          key={lvl}
                          type="button"
                          onClick={() => setConfidence(confidence === lvl ? null : lvl)}
                          className={`rounded px-1.5 py-0.5 text-[0.6875rem] transition cursor-pointer ${
                            confidence === lvl
                              ? `bg-white/10 ${color} font-bold ring-1 ring-inset ring-current`
                              : 'text-slate-400 hover:text-slate-200'
                          }`}
                        >
                          {label}
                        </button>
                      ))}
                    </div>
                    {/* Workbench Layout Toolbar */}
                    <div className="inline-flex items-center rounded-md bg-[#161616] p-0.5 border border-ink-line text-xs gap-0.5 shrink-0">
                      {!inPopout && (
                        <button
                          type="button"
                          onClick={workbenchLayout.toggleColumnsSwapped}
                          className={`px-1.5 py-0.5 text-[0.6875rem] font-medium rounded transition flex items-center gap-1 cursor-pointer ${
                            workbenchLayout.columnsSwapped
                              ? 'bg-sky-600/30 text-sky-200 border border-sky-500/40'
                              : 'text-slate-400 hover:text-slate-200'
                          }`}
                          title="Swap Problem and Workbench columns"
                        >
                          <span>⇄ Swap Col</span>
                        </button>
                      )}

                      <button
                        type="button"
                        onClick={() =>
                          workbenchLayout.setConsoleDockPosition(
                            workbenchLayout.consoleDockPosition === 'bottom' ? 'right' : 'bottom',
                          )
                        }
                        className={`px-1.5 py-0.5 text-[0.6875rem] font-medium rounded transition flex items-center gap-1 cursor-pointer ${
                          workbenchLayout.consoleDockPosition === 'right'
                            ? 'bg-indigo-600/30 text-indigo-200 border border-indigo-500/40'
                            : 'text-slate-400 hover:text-slate-200'
                        }`}
                        title={
                          workbenchLayout.consoleDockPosition === 'bottom'
                            ? 'Dock testcases on right (3-column layout)'
                            : 'Dock testcases at bottom'
                        }
                      >
                        <span>{workbenchLayout.consoleDockPosition === 'bottom' ? '⊞ Dock Right' : '⊟ Dock Bottom'}</span>
                      </button>

                      <button
                        type="button"
                        onClick={workbenchLayout.toggleStacked}
                        className={`px-1.5 py-0.5 text-[0.6875rem] font-medium rounded transition flex items-center gap-1 cursor-pointer ${
                          workbenchLayout.isStacked
                            ? 'bg-amber-600/30 text-amber-200 border border-amber-500/40'
                            : 'text-slate-400 hover:text-slate-200'
                        }`}
                        title={workbenchLayout.isStacked ? 'Switch to side-by-side split' : 'Switch to stacked top/bottom layout'}
                      >
                        <span>{workbenchLayout.isStacked ? '⧉ Split' : '☰ Stack'}</span>
                      </button>

                      <button
                        type="button"
                        onClick={workbenchLayout.resetLayout}
                        className="px-1.5 py-0.5 text-[0.6875rem] font-medium rounded text-slate-500 hover:text-slate-300 transition cursor-pointer"
                        title="Reset layout dimensions and positions to default"
                      >
                        <span>↺ Reset</span>
                      </button>
                    </div>

                    {revealed && (
                      <CopyLearningSummaryButton
                        item={item}
                        answer={answer}
                        testCode={testCode}
                        result={result}
                        codeLanguage={codeLanguage}
                        codeRunResult={codeRunResult}
                        variant="compact"
                      />
                    )}
                    {!inPopout && (
                      <button
                        type="button"
                        onClick={handlePopOutIde}
                        className="px-2 py-0.5 text-xs font-medium rounded bg-[#161616] hover:bg-[#222] text-sky-400 hover:text-sky-300 border border-sky-500/40 shadow-sm flex items-center gap-1 transition cursor-pointer shrink-0"
                        title="Expand IDE into a separate window for multi-monitor or full workspace (Alt+P)"
                      >
                        <span>⧉</span>
                        <span>Separate Window</span>
                      </button>
                    )}
                    {!inPopout && <FullscreenButton size="sm" showLabel={false} />}
                  </div>
                </div>

                {/* Body: Tiled Side-by-Side View vs Single Tab View */}
                {tiledTabs ? (
                  <div
                    ref={tiledContainerRef}
                    style={
                      inPopout || currentViewportWidth < 1024
                        ? undefined
                        : { height: `${Math.max(460, workbenchLayout.editorHeight + 76)}px` }
                    }
                    className={`flex flex-col lg:flex-row items-stretch bg-[#161616] relative overflow-hidden w-full divide-y lg:divide-y-0 divide-ink-line ${
                      inPopout ? 'flex-1 min-h-0' : ''
                    }`}
                  >
                    <div
                      style={
                        currentViewportWidth < 1024
                          ? undefined
                          : { width: `${workbenchLayout.tiledLeftWidthPercent}%` }
                      }
                      className="w-full lg:w-auto min-w-0 lg:min-w-[200px] shrink-0 flex flex-col min-h-0"
                    >
                      <TiledEditorPane
                        paneId="left"
                        currentTab={tileLeftTab}
                        onTabChange={setTileLeftTab}
                        answer={answer}
                        onAnswerChange={setAnswer}
                        testCode={testCode}
                        onTestCodeChange={setTestCode}
                        cleanRefCode={cleanRefCode}
                        starterTestsCode={starterTestsCode}
                        cleanRefTestsCode={cleanRefTestsCode}
                        codeLanguage={codeLanguage}
                        revealed={revealed}
                        onReveal={() => void reveal()}
                        item={item}
                        copiedRef={copiedRef}
                        onCopyRef={handleCopyReferenceCode}
                        copiedStarterTests={copiedStarterTests}
                        onCopyStarterTests={handleCopyStarterTests}
                        copiedRefTests={copiedRefTests}
                        onCopyRefTests={handleCopyReferenceTests}
                        height={effectiveEditorHeight}
                        fillHeight={shouldFillTiledHeight}
                        onRun={() => void handleRunReviewCode()}
                        onSubmit={() => void (llmEnabled && answer.trim() ? grade() : reveal())}
                        activeLineHint={activeLineHint}
                        lineHintLoading={lineHintLoading}
                        onRequestLineHint={handleRequestLineHint}
                        onDismissLineHint={() => setActiveLineHint(null)}
                        onCursorChange={(l) => {
                          if (tileLeftTab === 'solution') setEditorCursorLine(l)
                        }}
                        onGradeSolution={() => void (answer.trim() ? grade() : reveal())}
                        grading={grading}
                        learnMode={learnMode}
                        overlookedPhrases={overlookedTerms}
                        matchedPhrases={matchedTerms}
                        onHide={() => handleHideSolution('hide')}
                        logicGuardEnabled={logicGuardEnabled}
                        onLogicGuardToggle={handleToggleLogicGuard}
                        activeModel={activeModel}
                        onActiveModelChange={(m) => void handleSwitchModel(m)}
                        executionSummary={executionSummaryStr}
                        sharedQaHistory={sharedQaHistory}
                        onSharedQaHistoryChange={setSharedQaHistory}
                      />
                    </div>

                    <div className="hidden lg:flex items-stretch shrink-0">
                      <ResizableSplitter
                        direction="horizontal"
                        variant="flush"
                        onResize={(delta) => {
                          const width = tiledContainerRef.current?.getBoundingClientRect().width || (inPopout ? popoutDimensions.width : 800)
                          workbenchLayout.handleTiledResize(delta, width)
                        }}
                        onDoubleClick={workbenchLayout.resetTiledSplit}
                        collapseTooltip="Drag to resize panes (Double-click to reset 50/50)"
                      />
                    </div>

                    <div className="w-full lg:w-auto min-w-0 lg:min-w-[200px] flex-1 flex flex-col min-h-0">
                      <TiledEditorPane
                        paneId="right"
                        currentTab={tileRightTab}
                        onTabChange={setTileRightTab}
                        answer={answer}
                        onAnswerChange={setAnswer}
                        testCode={testCode}
                        onTestCodeChange={setTestCode}
                        cleanRefCode={cleanRefCode}
                        starterTestsCode={starterTestsCode}
                        cleanRefTestsCode={cleanRefTestsCode}
                        codeLanguage={codeLanguage}
                        revealed={revealed}
                        onReveal={() => void reveal()}
                        item={item}
                        copiedRef={copiedRef}
                        onCopyRef={handleCopyReferenceCode}
                        copiedStarterTests={copiedStarterTests}
                        onCopyStarterTests={handleCopyStarterTests}
                        copiedRefTests={copiedRefTests}
                        onCopyRefTests={handleCopyReferenceTests}
                        height={effectiveEditorHeight}
                        fillHeight={shouldFillTiledHeight}
                        onRun={() => void handleRunReviewCode()}
                        onSubmit={() => void (llmEnabled && answer.trim() ? grade() : reveal())}
                        activeLineHint={activeLineHint}
                        lineHintLoading={lineHintLoading}
                        onRequestLineHint={handleRequestLineHint}
                        onDismissLineHint={() => setActiveLineHint(null)}
                        onCursorChange={(l) => {
                          if (tileRightTab === 'solution') setEditorCursorLine(l)
                        }}
                        onGradeSolution={() => void (answer.trim() ? grade() : reveal())}
                        grading={grading}
                        learnMode={learnMode}
                        overlookedPhrases={overlookedTerms}
                        matchedPhrases={matchedTerms}
                        onHide={() => handleHideSolution('hide')}
                        logicGuardEnabled={logicGuardEnabled}
                        onLogicGuardToggle={handleToggleLogicGuard}
                        activeModel={activeModel}
                        onActiveModelChange={(m) => void handleSwitchModel(m)}
                        executionSummary={executionSummaryStr}
                        sharedQaHistory={sharedQaHistory}
                        onSharedQaHistoryChange={setSharedQaHistory}
                      />
                    </div>
                  </div>
                ) : (
                  /* Single Tab View */
                  activeEditorTab === 'reference' ? (
                    revealed || singleRefViewMode === 'hint' ? (
                      <div className={inPopout ? 'flex flex-col flex-1 min-h-0 overflow-hidden' : 'flex flex-col'}>
                        {singleRefViewMode === 'hint' && (
                          <div className="px-3 py-1.5 bg-amber-950/40 border-b border-amber-500/30 flex items-center justify-between text-xs text-amber-200 shrink-0">
                            <div className="flex items-center gap-2">
                             <span className="font-semibold text-amber-300"> Hint Mode:</span>
                              <span>
                                Only line {findIncompleteLineNumber(answer, cleanRefCode)} is visible
                              </span>
                            </div>
                            {revealed && (
                              <button
                                type="button"
                                onClick={() => handleHideSolution('hide')}
                                className="px-2 py-0.5 rounded bg-rose-500/20 hover:bg-rose-500/30 text-rose-300 border border-rose-500/40 font-semibold cursor-pointer"
                                title="Hide the solution and continue practicing"
                              >
                                 Unreveal & Practice
                              </button>
                            )}
                          </div>
                        )}
                        <CodeEditor
                          code={cleanRefCode}
                          onChange={() => {}}
                          language={codeLanguage}
                          readOnly={true}
                          fillHeight={inPopout}
                          height={
                            singleRefViewMode === 'hint'
                              ? effectiveRefHintHeight
                              : effectiveEditorHeight
                          }
                          placeholder="// Reference solution"
                          context={item?.front || item?.deck_name}
                          deckId={item?.kind === 'card' ? item.deck_or_source_id : null}
                          cardId={item?.id ?? null}
                          userCode={answer}
                          userTestCode={testCode}
                          executionSummary={executionSummaryStr}
                          revealed={revealed}
                          sharedQaHistory={sharedQaHistory}
                          onSharedQaHistoryChange={setSharedQaHistory}
                          activeModel={activeModel}
                          onActiveModelChange={(m) => void handleSwitchModel(m)}
                          diffSegments={singleRefViewMode === 'diff' ? singleRefDiff.refSegments : null}
                          diffStats={singleRefViewMode === 'diff' ? singleRefDiff.stats : null}
                          hintOnly={singleRefViewMode === 'hint'}
                          hintOnlyLine={findIncompleteLineNumber(answer, cleanRefCode)}
                          targetLineNumbers={singleTargetRefLines}
                          focusTargetCode={focusTargetCode}
                          targetHighlightColor={targetHighlightColor}
                          initialScrollLine={firstSingleTargetRefLine ?? undefined}
                        />
                      </div>
                    ) : (
                      <div
                        style={inPopout ? undefined : { height: effectiveEditorHeight }}
                        className={`flex flex-col items-center justify-center p-6 text-center bg-[#181818] text-slate-400 space-y-3 ${
                          inPopout ? 'flex-1 min-h-[200px]' : ''
                        }`}
                      >
                        <div className="w-12 h-12 rounded-2xl bg-sky-500/10 border border-sky-500/20 flex items-center justify-center text-sky-400 shadow-inner">
                          <svg className="w-5 h-5 text-sky-400" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><rect x="3" y="11" width="18" height="11" rx="2" ry="2"/><path d="M7 11V7a5 5 0 0 1 10 0v4"/></svg>
                        </div>
                        <div className="space-y-1">
                          <h4 className="text-sm font-semibold text-slate-200">Reference Solution</h4>
                          <p className="text-xs text-slate-400 max-w-xs leading-relaxed">
                            Hidden until revealed.
                          </p>
                        </div>
                        <div className="flex items-center gap-2 mt-2">
                          <button
                            type="button"
                            onClick={() => void reveal()}
                            className="btn btn-secondary text-xs flex items-center gap-1.5 px-3 py-1.5 cursor-pointer"
                          >
                            <span>Reveal Solution</span>
                          </button>
                          <button
                            type="button"
                            onClick={() => {
                              setSingleRefViewMode('hint')
                              storage.set('memorization.refViewMode', 'hint')
                            }}
                            className="px-3 py-1.5 rounded-lg border border-amber-500/40 bg-amber-500/10 hover:bg-amber-500/20 text-amber-300 text-xs font-medium transition cursor-pointer flex items-center gap-1.5"
                            title="Peek only the next line of code without revealing full answer"
                          >
                           <span> Line Hint</span>
                          </button>
                        </div>
                      </div>
                    )
                  ) : activeEditorTab === 'ref_tests' ? (
                    revealed || learnMode ? (
                      <CodeEditor
                        code={cleanRefTestsCode}
                        onChange={() => {}}
                        language={codeLanguage}
                        readOnly={true}
                        fillHeight={inPopout}
                        height={effectiveEditorHeight}
                        placeholder="// Completed reference test suite"
                        context={item?.front || item?.deck_name}
                        deckId={item?.kind === 'card' ? item.deck_or_source_id : null}
                        cardId={item?.id ?? null}
                        userCode={answer}
                        userTestCode={testCode}
                        executionSummary={executionSummaryStr}
                        revealed={revealed}
                        sharedQaHistory={sharedQaHistory}
                        onSharedQaHistoryChange={setSharedQaHistory}
                        activeModel={activeModel}
                        onActiveModelChange={(m) => void handleSwitchModel(m)}
                      />
                    ) : (
                      <div
                        style={inPopout ? undefined : { height: effectiveEditorHeight }}
                        className={`flex flex-col items-center justify-center p-6 text-center bg-[#181818] text-slate-400 space-y-3 ${
                          inPopout ? 'flex-1 min-h-[200px]' : ''
                        }`}
                      >
                        <div className="w-12 h-12 rounded-2xl bg-purple-500/10 border border-purple-500/20 flex items-center justify-center text-purple-400 shadow-inner">
                          <svg className="w-5 h-5 text-purple-400" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><rect x="3" y="11" width="18" height="11" rx="2" ry="2"/><path d="M7 11V7a5 5 0 0 1 10 0v4"/></svg>
                        </div>
                        <div className="space-y-1">
                          <h4 className="text-sm font-semibold text-slate-200">Reference Tests</h4>
                          <p className="text-xs text-slate-400 max-w-xs leading-relaxed">
                            Hidden until revealed.
                          </p>
                        </div>
                        <div className="flex items-center gap-2 mt-2">
                          <button
                            type="button"
                            onClick={() => void reveal()}
                            className="btn btn-secondary text-xs flex items-center gap-1.5 px-3 py-1.5 cursor-pointer"
                          >
                            <span>Reveal Tests</span>
                          </button>
                        </div>
                      </div>
                    )
                  ) : (
                    <CodeEditor
                      code={activeEditorTab === 'solution' ? answer : testCode}
                      onChange={activeEditorTab === 'solution' ? setAnswer : setTestCode}
                      language={codeLanguage}
                      fillHeight={inPopout}
                      height={effectiveEditorHeight}
                      onRun={() => void handleRunReviewCode()}
                      onSubmit={() => void (llmEnabled && answer.trim() ? grade() : reveal())}
                      activeModel={activeModel}
                      onActiveModelChange={(m) => void handleSwitchModel(m)}
                      activeLineHint={activeEditorTab === 'solution' ? activeLineHint : null}
                      lineHintLoading={activeEditorTab === 'solution' ? lineHintLoading : false}
                      onRequestLineHint={activeEditorTab === 'solution' ? handleRequestLineHint : undefined}
                      onDismissLineHint={() => setActiveLineHint(null)}
                      onCursorChange={(l) => setEditorCursorLine(l)}
                      onGradeSolution={activeEditorTab === 'solution' ? () => void (answer.trim() ? grade() : reveal()) : undefined}
                      grading={activeEditorTab === 'solution' ? grading : false}
                      context={item?.front || item?.deck_name}
                      deckId={item?.kind === 'card' ? item.deck_or_source_id : null}
                      cardId={item?.id ?? null}
                      userCode={answer}
                      userTestCode={testCode}
                      executionSummary={executionSummaryStr}
                      revealed={revealed}
                      sharedQaHistory={sharedQaHistory}
                      onSharedQaHistoryChange={setSharedQaHistory}
                    />
                  )
                )}
              </div>
            </div>

            {/* Splitter between Editor and Console */}
            {!workbenchLayout.consoleCollapsed && (
              isRightDock ? (
                <div className="hidden lg:flex items-stretch shrink-0">
                  <ResizableSplitter
                    direction="horizontal"
                    variant={inPopout ? 'flush' : 'pill'}
                    onResize={(delta) => {
                      const width = workbenchRowRef.current?.getBoundingClientRect().width || (inPopout ? popoutDimensions.width : 900)
                      workbenchLayout.handleConsoleWidthResize(delta, width)
                    }}
                    onDoubleClick={workbenchLayout.resetConsoleWidth}
                    onToggleCollapse={workbenchLayout.toggleConsoleCollapsed}
                    isCollapsed={workbenchLayout.consoleCollapsed}
                    collapseTooltip="Drag to resize Console width / Double-click to reset / Click to collapse"
                  />
                </div>
              ) : (
                <ResizableSplitter
                  direction="vertical"
                  variant={inPopout ? 'flush' : 'pill'}
                  onResize={
                    inPopout
                      ? workbenchLayout.handleConsoleHeightResize
                      : workbenchLayout.handleEditorHeightResize
                  }
                  onDoubleClick={
                    inPopout
                      ? workbenchLayout.resetConsoleHeight
                      : workbenchLayout.resetEditorHeight
                  }
                  onToggleCollapse={workbenchLayout.toggleConsoleCollapsed}
                  isCollapsed={workbenchLayout.consoleCollapsed}
                  collapseTooltip={
                    inPopout
                      ? 'Drag to resize Console height / Double-click to reset / Click to collapse'
                      : 'Drag to resize editor & console height / Double-click to reset / Click to collapse'
                  }
                />
              )
            )}

            {/* Console Section (Docked Right vs Docked Bottom) */}
            {isRightDock ? (
              workbenchLayout.consoleCollapsed ? (
                <div
                  onClick={workbenchLayout.toggleConsoleCollapsed}
                  className={
                    inPopout
                      ? 'hidden lg:flex w-10 border-l border-[#2a2d34] bg-[#161616] hover:bg-[#202020] cursor-pointer flex-col items-center py-4 text-slate-400 hover:text-white transition gap-3 select-none shrink-0'
                      : 'hidden lg:flex w-10 rounded-xl border border-ink-line bg-[#161616] hover:bg-[#202020] cursor-pointer flex-col items-center py-4 text-slate-400 hover:text-white transition gap-3 select-none shrink-0'
                  }
                  title="Expand Testcases Console (Click to expand)"
                >
                  <span className="text-xs">◀</span>
                  <span className="text-[0.6875rem] font-mono [writing-mode:vertical-rl] tracking-wider font-semibold">
                    Testcases Console
                  </span>
                  {codeRunResult && (
                    <span
                      className={`w-2 h-2 rounded-full ${
                        codeRunResult.status === 'Accepted' ? 'bg-emerald-400' : 'bg-rose-400'
                      }`}
                      title={codeRunResult.status === 'Accepted' ? 'Tests Passed' : 'Tests Failed'}
                    />
                  )}
                </div>
              ) : (
                <div
                  style={{ width: `${workbenchLayout.consoleWidthPercent}%` }}
                  className={
                    inPopout
                      ? 'w-full lg:w-auto min-w-[260px] shrink-0 h-full min-h-0 flex flex-col border-l border-[#2a2d34]'
                      : 'w-full lg:w-auto min-w-[280px] shrink-0'
                  }
                >
                  <CodeTestConsole
                    testCases={item.test_cases || []}
                    runResult={codeRunResult}
                    running={codeRunning}
                    onRun={handleRunReviewCode}
                    onSubmit={() => void (llmEnabled && answer.trim() ? grade() : reveal())}
                    submitting={grading}
                    dockPosition="right"
                    onToggleCollapse={workbenchLayout.toggleConsoleCollapsed}
                    flush={inPopout}
                  />
                </div>
              )
            ) : (
              /* Bottom Dock Console */
              workbenchLayout.consoleCollapsed ? (
                <div
                  className={
                    inPopout
                      ? 'shrink-0 flex items-center justify-between px-3.5 py-2 bg-[#16171b] border-t border-[#2a2d34] text-xs text-slate-400'
                      : 'flex items-center justify-between px-3.5 py-2 bg-[#1a1a1a] border border-ink-line rounded-xl text-xs text-slate-400'
                  }
                >
                  <div className="flex items-center gap-2.5">
                    <button
                      type="button"
                      onClick={workbenchLayout.toggleConsoleCollapsed}
                      className="flex items-center gap-1.5 text-slate-200 hover:text-white font-medium cursor-pointer"
                      title="Expand Testcases Console"
                    >
                      <span className="text-sky-400">▲</span>
                      <span className="font-semibold">Testcases Console</span>
                      <span className="text-slate-500 text-[0.6875rem]">(Collapsed)</span>
                    </button>
                    {codeRunResult && (
                      <span
                        className={`text-[0.6875rem] px-2 py-0.5 rounded font-semibold ${
                          codeRunResult.status === 'Accepted'
                            ? 'bg-emerald-500/20 text-emerald-300'
                            : 'bg-rose-500/20 text-rose-300'
                        }`}
                      >
                        {codeRunResult.status === 'Accepted' ? 'Passed' : 'Failed'} ({codeRunResult.passed_count}/
                        {codeRunResult.total_count})
                      </span>
                    )}
                  </div>
                  <div className="flex items-center gap-2">
                    <button
                      type="button"
                      onClick={() => void handleRunReviewCode()}
                      disabled={codeRunning}
                      className="btn btn-secondary text-xs py-1 px-3 cursor-pointer"
                    >
                      {codeRunning ? 'Running…' : 'Run Tests'}
                    </button>
                    <button
                      type="button"
                      onClick={workbenchLayout.toggleConsoleCollapsed}
                      className="text-xs text-sky-400 hover:text-sky-300 cursor-pointer font-medium"
                    >
                      Expand ▲
                    </button>
                  </div>
                </div>
              ) : inPopout ? (
                <div className="shrink-0 w-full border-t border-[#2a2d34]">
                  <CodeTestConsole
                    testCases={item.test_cases || []}
                    runResult={codeRunResult}
                    running={codeRunning}
                    onRun={handleRunReviewCode}
                    onSubmit={() => void (llmEnabled && answer.trim() ? grade() : reveal())}
                    submitting={grading}
                    dockPosition="bottom"
                    onToggleCollapse={workbenchLayout.toggleConsoleCollapsed}
                    flush={true}
                    heightPx={workbenchLayout.consoleHeight}
                  />
                </div>
              ) : (
                <CodeTestConsole
                  testCases={item.test_cases || []}
                  runResult={codeRunResult}
                  running={codeRunning}
                  onRun={handleRunReviewCode}
                  onSubmit={() => void (llmEnabled && answer.trim() ? grade() : reveal())}
                  submitting={grading}
                  dockPosition="bottom"
                  onToggleCollapse={workbenchLayout.toggleConsoleCollapsed}
                />
              )
            )}
          </div>
    )

    if (!inPopout) {
      return workbenchContent
    }

    return (
      <div className="flex flex-col h-screen w-screen bg-[#121212] text-slate-100 overflow-hidden select-auto font-sans">
        {/* Popout Window Top Header Bar */}
        <div className="h-11 shrink-0 flex items-center justify-between px-3.5 bg-[#18181b] border-b border-[#2a2d34] text-xs text-slate-200 select-none gap-3">
          {/* Left: Window Title & Metadata */}
          <div className="flex items-center gap-2.5 min-w-0">
            <div className="flex items-center gap-1.5 font-bold text-sky-400">
              <span className="tracking-wide">Ars Memoriae</span>
              <span className="text-slate-600">/</span>
              <span className="text-slate-300 font-medium truncate max-w-[320px]">
                {item?.title || item?.deck_name || 'Code Practice IDE'}
              </span>
            </div>
            {item?.difficulty && (
              <span
                className={`chip text-[0.625rem] py-0.5 px-2 font-semibold ${
                  item.difficulty === 'Easy'
                    ? 'border-emerald-500/40 text-emerald-300 bg-emerald-500/10'
                    : item.difficulty === 'Medium'
                    ? 'border-amber-500/40 text-amber-300 bg-amber-500/10'
                    : 'border-rose-500/40 text-rose-300 bg-rose-500/10'
                }`}
              >
                {item.difficulty}
              </span>
            )}
            <span className="chip text-[0.625rem] py-0.5 px-2 border-sky-500/40 text-sky-300 bg-sky-500/10 font-mono uppercase">
              {codeLanguage}
            </span>
            {item?.deck_name && (
              <span className="chip text-[0.625rem] py-0.5 px-2 text-slate-400 hidden sm:inline">
                {item.deck_name}
              </span>
            )}
          </div>

          {/* Right: Controls (Problem Drawer, Lexicon Margin, Fullscreen, Dock Back) */}
          <div className="flex items-center gap-2 shrink-0">
            <button
              type="button"
              onClick={() => setPopoutShowProblem((prev) => !prev)}
              className={`px-2.5 py-1 text-xs font-medium rounded transition flex items-center gap-1.5 cursor-pointer ${
                popoutShowProblem
                  ? 'bg-sky-600/30 text-sky-200 border border-sky-500/50 shadow-sm'
                  : 'bg-[#222] hover:bg-[#2a2a2a] text-slate-300 border border-slate-700'
              }`}
              title="Toggle problem statement drawer (Alt+O)"
            >
              <span>{popoutShowProblem ? 'Hide Problem' : 'Problem Statement'}</span>
            </button>

            <button
              type="button"
              onClick={() => setPopoutShowLexicon((prev) => !prev)}
              className={`px-2.5 py-1 text-xs font-medium rounded transition flex items-center gap-1.5 cursor-pointer ${
                popoutShowLexicon
                  ? 'bg-sky-600/30 text-sky-200 border border-sky-500/50 shadow-sm'
                  : 'bg-[#222] hover:bg-[#2a2a2a] text-slate-300 border border-slate-700'
              }`}
              title="Toggle Card Lexicon & Definitions margin panel"
            >
              <span>Lexicon</span>
              {(item?.lexicon_glosses?.length || 0) > 0 && (
                <span className="rounded-full bg-sky-500/30 px-1.5 py-0.2 text-[0.625rem] font-bold text-sky-200">
                  {item?.lexicon_glosses?.length}
                </span>
              )}
            </button>

            <button
              type="button"
              onClick={() => {
                if (idePopupRef.current?.document.fullscreenElement) {
                  void idePopupRef.current.document.exitFullscreen()
                } else {
                  void idePopupRef.current?.document.documentElement.requestFullscreen()
                }
              }}
              className="px-2.5 py-1 text-xs font-medium rounded bg-[#222] hover:bg-[#2a2a2a] text-slate-300 border border-slate-700 transition flex items-center gap-1 cursor-pointer"
              title="Toggle Fullscreen"
            >
              <span>⛶</span>
              <span>Fullscreen</span>
            </button>

            <button
              type="button"
              onClick={handleDockBackIde}
              className="px-2.5 py-1 text-xs font-semibold rounded bg-sky-600/40 hover:bg-sky-600/60 text-sky-100 border border-sky-500/60 shadow-sm flex items-center gap-1.5 transition cursor-pointer"
              title="Dock IDE back into main browser window (Esc / Alt+P)"
            >
              <span>⤓</span>
              <span>Dock Back</span>
              <kbd className="text-[0.625rem] bg-slate-900/60 px-1 py-0.2 rounded text-sky-200">Esc</kbd>
            </button>
          </div>
        </div>

        {/* Main Content Area: Problem Drawer + Editor & Console + Margin Lexicon */}
        <div className="flex flex-1 flex-row min-h-0 overflow-hidden relative">
          {/* Slide-over Problem Statement Drawer in Separate Window */}
          {popoutShowProblem && item && (
            <div className="w-[380px] xl:w-[420px] max-w-[42vw] shrink-0 border-r border-[#2a2d34] bg-[#16181d] p-4 overflow-y-auto space-y-4 text-xs">
              <div className="flex items-center justify-between pb-2 border-b border-ink-line">
                <h3 className="font-bold text-sm text-slate-100">Problem Description</h3>
                <button
                  type="button"
                  onClick={() => setPopoutShowProblem(false)}
                  className="text-slate-400 hover:text-slate-200 text-sm font-mono cursor-pointer"
                  title="Close problem drawer (Alt+O)"
                >
                  ✕
                </button>
              </div>
              {item.title && <h2 className="text-base font-bold text-slate-100">{item.title}</h2>}
              <RichText
                text={item.front ?? ''}
                className="text-xs leading-relaxed text-slate-200"
                codeLanguage={codeLanguage}
                deckId={item.kind === 'card' ? item.deck_or_source_id : null}
              />
              {(item.time_complexity || item.space_complexity || (item.edge_cases && item.edge_cases.length > 0)) && (
                <div className="rounded-lg border border-ink-line/70 bg-ink-soft/40 p-3 space-y-2 text-xs">
                  <p className="font-semibold text-slate-400 uppercase tracking-wider text-[0.625rem]">
                    Target Complexity &amp; Constraints:
                  </p>
                  <div className="flex flex-wrap gap-3 text-slate-300">
                    {item.time_complexity && (
                      <span>
                        <strong>Time:</strong> <code className="text-sky-300 font-mono font-bold">{item.time_complexity}</code>
                      </span>
                    )}
                    {item.space_complexity && (
                      <span>
                        <strong>Space:</strong> <code className="text-sky-300 font-mono font-bold">{item.space_complexity}</code>
                      </span>
                    )}
                  </div>
                  {item.edge_cases && item.edge_cases.length > 0 && (
                    <div className="pt-1 border-t border-ink-line/50">
                      <span className="text-slate-400 font-medium">Critical Edge Cases: </span>
                      <span className="text-amber-200/90 italic">{item.edge_cases.join(', ')}</span>
                    </div>
                  )}
                </div>
              )}
            </div>
          )}

          {/* The Workbench Body (Editor + Console) */}
          <div className="flex-1 min-w-0 min-h-0 flex flex-col overflow-hidden bg-[#121212]">
            {Boolean(error) && (
              <div className="px-3 pt-2 shrink-0">
                <ErrorNote error={error} />
              </div>
            )}
            {workbenchContent}
          </div>

          {/* Right Margin Lexicon Sidebar in Separate Window */}
          {item && (
            <aside
              className={
                popoutShowLexicon
                  ? 'w-[300px] xl:w-[320px] max-w-[36vw] shrink-0 border-l border-[#2a2d34] bg-[#111318] h-full min-h-0 flex flex-col overflow-hidden'
                  : 'hidden'
              }
            >
              <MarginLexiconPanel
                embedded={true}
                cardId={item.id}
                deckId={item.kind === 'card' ? item.deck_or_source_id : null}
                deckName={item.deck_name}
                thematicNature={item.card_thematic_nature || item.deck_thematic_nature}
                cardFront={item.front}
                cardBack={item.back}
                initialGlosses={item.lexicon_glosses}
                codeLanguage={codeLanguage}
                onLookupTriggered={() => setPopoutShowLexicon(true)}
                onGlossesUpdated={(updatedGlosses) => applyGlossesToCard(item.id, updatedGlosses)}
              />
            </aside>
          )}
        </div>
      </div>
    )
  }

    return (
      <div className="space-y-6">
        <SessionHeader
          session={session}
          outcome={lastOutcome}
          branchActive={Boolean(branch)}
          deckActive={deckActive}
          deckName={activeDeckName}
          onClearBranch={clearBranch}
          learnMode={learnMode}
          onToggleLearnMode={toggleLearnMode}
          blitzActive={blitzActive}
          onStartBlitz={startBlitz}
          persistActive={persistActive}
          persistDeckName={persistDeckName}
          persistUnseenOnly={persistUnseenOnly}
          onExitPersist={exitPersistMode}
          persistProgress={{
            grasped: persistGraspedIds.size,
            total: persistCards.length,
            round: persistRound,
          }}
          allCardsRunActive={allCardsRunActive}
          allCardsRunDeckName={allCardsRunDeckName}
          onExitAllCardsRun={exitAllCardsRun}
          allCardsRunProgress={{
            current: allCardsRunIndex + 1,
            total: allCardsRunCards.length,
          }}
          onStartAllCardsRun={startAllCardsRun}
          allDecks={allDecks}
          onStartPersist={startPersistMode}
          savedCount={savedCount}
          onOpenSavedDrawer={() => setSavedDrawerOpen(true)}
          previousCard={previousCard}
          onRetryPreviousCard={handleRetryPreviousCard}
        />

        {/* Prompt to study unseen cards if reviewing a deck with unintroduced material */}
        {deckParam &&
          !persistActive &&
          !allCardsRunActive &&
          currentDeckInfo &&
          currentDeckInfo.new_count > 0 &&
          dismissedUnseenDeckId !== deckParam && (
            <div className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-amber-500/40 bg-gradient-to-r from-amber-950/40 via-amber-900/20 to-ink-soft p-3.5 shadow-md">
              <div className="flex items-center gap-2.5">
                <span className="flex h-6 px-2 items-center justify-center rounded bg-amber-500/20 text-[0.625rem] font-bold uppercase tracking-wider text-amber-300 border border-amber-500/30">
                  Unseen Cards Available
                </span>
                <span className="text-xs text-slate-200">
                  This deck has <strong className="text-amber-300 font-mono">{currentDeckInfo.new_count}</strong> unseen {currentDeckInfo.new_count === 1 ? 'card' : 'cards'}. Would you like to study only unseen cards until you have seen all of them?
                </span>
              </div>
              <div className="flex items-center gap-2 shrink-0">
                <button
                  type="button"
                  onClick={() => startPersistMode(deckParam, currentDeckInfo.name, true)}
                  className="rounded-lg border border-amber-500/60 bg-amber-500/25 px-3 py-1 text-xs font-semibold text-amber-100 hover:bg-amber-500/40 transition shadow-xs cursor-pointer"
                >
                  Study Unseen Only ({currentDeckInfo.new_count})
                </button>
                <button
                  type="button"
                  onClick={() => setDismissedUnseenDeckId(deckParam)}
                  className="rounded-lg border border-slate-700 bg-ink-soft/80 px-2.5 py-1 text-xs text-slate-400 hover:text-slate-200 hover:bg-ink-soft transition cursor-pointer"
                  title="Dismiss notice"
                >
                  Dismiss
                </button>
              </div>
            </div>
          )}

        {blitzActive && (
          <div className="rounded-lg border border-amber-500/40 bg-amber-500/10 p-3">
            <div className="flex flex-wrap items-center justify-between gap-2 text-xs font-medium text-amber-200">
              <span className="flex items-center gap-1.5 text-sm">
                <strong>BLITZ SPRINT:</strong> {blitzTimeRemainingSec}s remaining
              </span>
              <div className="flex items-center gap-3">
                <span>{blitzCardsAnswered} cards answered</span>
                <span>
                  {blitzCardsAnswered > 0
                    ? ((blitzCardsAnswered / Math.max(1, blitzDurationSec - blitzTimeRemainingSec)) * 60).toFixed(0)
                    : 0}{' '}
                  CPM
                </span>
                <button
                  type="button"
                  className="rounded border border-amber-500/50 bg-amber-500/20 px-2 py-0.5 text-xs text-amber-100 hover:bg-amber-500/30"
                  onClick={stopBlitz}
                >
                  Stop Sprint
                </button>
              </div>
            </div>
            <div className="mt-2 h-1.5 w-full overflow-hidden rounded-full bg-amber-950/60">
              <div
                className="h-full bg-gradient-to-r from-amber-400 to-amber-200 transition-all duration-1000 ease-linear"
                style={{ width: `${Math.max(0, (blitzTimeRemainingSec / blitzDurationSec) * 100)}%` }}
              />
            </div>
          </div>
        )}

        {persistActive && (
          <div className="rounded-xl border border-sky-500/40 bg-gradient-to-r from-sky-950/40 via-indigo-950/30 to-purple-950/20 p-4 shadow-lg backdrop-blur space-y-3">
            <div className="flex flex-wrap items-center justify-between gap-2.5">
              <div className="flex items-center gap-2">
                <span className="flex h-7 px-2 items-center justify-center rounded-lg bg-sky-500/20 text-xs font-bold uppercase tracking-wider text-sky-300">
                  {persistUnseenOnly ? 'Persist · Unseen' : 'Persist'}
                </span>
                <div>
                  <div className="flex items-center gap-2">
                    <span className="font-bold text-slate-100 text-sm">
                      Persist Review Mode: {persistDeckName || item?.deck_name || 'Active Deck'}
                    </span>
                    {persistUnseenOnly && (
                      <span className="rounded bg-amber-500/20 border border-amber-500/30 px-1.5 py-0.5 text-[0.625rem] font-medium text-amber-300">
                        Unseen Cards Only
                      </span>
                    )}
                    <span className="rounded-full bg-sky-500/20 border border-sky-500/40 px-2 py-0.5 text-[0.625rem] font-mono text-sky-200">
                      Round {persistRound}
                    </span>
                  </div>
                  <p className="text-[0.6875rem] text-slate-400 mt-0.5">
                    {persistUnseenOnly
                      ? 'Drilling previously unseen cards until all are rated Easy. Other ratings (Again, Hard, Good) keep the card in rotation.'
                      : 'Drilling until all cards are rated Easy. Other ratings (Again, Hard, Good) keep the card in rotation.'}{' '}
                    Only your first rating of each card is scheduled; repeat passes are practice.
                  </p>
                </div>
              </div>

              <div className="flex items-center gap-2">
                <button
                  type="button"
                  onClick={handleRestartPersistRound}
                  className="rounded-md border border-slate-700 bg-slate-800/80 px-2.5 py-1 text-xs text-slate-300 hover:bg-slate-700 hover:text-white transition"
                  title="Reset current round progress and drill all cards again"
                >
                  Restart Round
                </button>
                <button
                  type="button"
                  onClick={exitPersistMode}
                  className="rounded-md border border-rose-500/30 bg-rose-500/10 px-2.5 py-1 text-xs text-rose-300 hover:bg-rose-500/20 transition"
                  title="Exit persist review mode and return to standard queue"
                >
                  &times; Exit Persist
                </button>
              </div>
            </div>

            {/* Live Persist Progress Bar */}
            <div className="space-y-1.5 pt-1">
              <div className="flex items-center justify-between text-xs">
                <span className="text-slate-300 flex items-center gap-2">
                  <span>{persistUnseenOnly ? 'Grasped Unseen Cards:' : 'Grasped Cards:'}</span>
                  <strong className="text-emerald-400 font-mono">
                    {persistGraspedIds.size} / {persistCards.length}
                  </strong>
                  <span className="text-slate-500 text-[0.6875rem]">
                    ({persistPendingQueue.length} pending in current cycle)
                  </span>
                </span>
                <span className="font-mono font-bold text-emerald-400">
                  {Math.round((persistGraspedIds.size / Math.max(1, persistCards.length)) * 100)}%
                </span>
              </div>
              <div className="relative h-2 w-full overflow-hidden rounded-full bg-slate-800/80">
                <div
                  className="h-full bg-gradient-to-r from-emerald-500 to-sky-400 transition-all duration-300 ease-out"
                  style={{
                    width: `${Math.min(
                      100,
                      Math.max(0, (persistGraspedIds.size / Math.max(1, persistCards.length)) * 100)
                    )}%`,
                  }}
                />
              </div>
            </div>

            {/* Re-attempt Indicator for current card */}
            {item && (persistCardAttempts[item.id] || 0) > 0 && (
              <div className="flex items-center gap-2 pt-0.5 text-xs text-amber-300/90 bg-amber-500/10 rounded-lg px-2.5 py-1 border border-amber-500/20">
                
                <span>
                  <strong>Re-attempt #{persistCardAttempts[item.id] + 1}:</strong> This card remains in the persist queue until rated <strong>Easy</strong>.
                </span>
              </div>
            )}
          </div>
        )}

        {allCardsRunActive && (
          <div className="rounded-xl border border-purple-500/40 bg-gradient-to-r from-purple-950/40 via-indigo-950/30 to-purple-950/20 p-4 shadow-lg backdrop-blur space-y-3">
            <div className="flex flex-wrap items-center justify-between gap-2.5">
              <div className="flex items-center gap-2">
                <span className="flex h-7 px-2 items-center justify-center rounded-lg bg-purple-500/20 text-xs font-bold uppercase tracking-wider text-purple-300">
                  Run
                </span>
                <div>
                  <div className="flex items-center gap-2">
                    <span className="font-bold text-slate-100 text-sm">
                      All Cards Run: {allCardsRunDeckName || item?.deck_name || 'Active Deck'}
                    </span>
                    <span className="rounded-full bg-purple-500/20 border border-purple-500/40 px-2 py-0.5 text-[0.625rem] font-mono text-purple-200">
                      Easiest → Hardest
                    </span>
                  </div>
                  <p className="text-[0.6875rem] text-slate-400 mt-0.5">
                    Reviewing every card in this deck consecutively in ascending difficulty order. Progress is automatically saved.
                  </p>
                </div>
              </div>

              <div className="flex items-center gap-2">
                {allCardsRunIndex > 0 && (
                  <button
                    type="button"
                    onClick={() => {
                      if (allCardsRunDeckId) {
                        clearAllCardsRunProgress(allCardsRunDeckId)
                        void startAllCardsRun(allCardsRunDeckId, allCardsRunDeckName, 0)
                      }
                    }}
                    className="rounded-md border border-purple-500/30 bg-purple-500/10 px-2.5 py-1 text-xs text-purple-300 hover:bg-purple-500/20 transition cursor-pointer"
                    title="Restart All Cards Run from Card 1"
                  >
                    Restart Run
                  </button>
                )}
                <button
                  type="button"
                  onClick={exitAllCardsRun}
                  className="rounded-md border border-purple-500/30 bg-purple-500/10 px-2.5 py-1 text-xs text-purple-300 hover:bg-purple-500/20 transition cursor-pointer"
                  title="Exit All Cards Run (progress is saved) and return to standard FSRS queue"
                >
                  &times; Exit Run (to FSRS)
                </button>
              </div>
            </div>

            {/* Live Run Progress Bar */}
            <div className="space-y-1.5 pt-1">
              <div className="flex items-center justify-between text-xs">
                <span className="text-slate-300 flex items-center gap-2">
                  <span>Progress:</span>
                  <strong className="text-purple-300 font-mono">
                    Card {allCardsRunIndex + 1} of {allCardsRunCards.length}
                  </strong>
                  <span className="text-slate-500 text-[0.6875rem]">
                    ({Math.max(0, allCardsRunCards.length - (allCardsRunIndex + 1))} remaining)
                  </span>
                </span>
                <span className="font-mono font-bold text-purple-300">
                  {Math.round(((allCardsRunIndex + 1) / Math.max(1, allCardsRunCards.length)) * 100)}%
                </span>
              </div>
              <div className="relative h-2 w-full overflow-hidden rounded-full bg-slate-800/80">
                <div
                  className="h-full bg-gradient-to-r from-purple-500 to-indigo-400 transition-all duration-300 ease-out"
                  style={{
                    width: `${Math.min(
                      100,
                      Math.max(0, ((allCardsRunIndex + 1) / Math.max(1, allCardsRunCards.length)) * 100)
                    )}%`,
                  }}
                />
              </div>
            </div>
          </div>
        )}

        {/* Live Deck Progress & Difficulty Distribution Stats Bar */}
        {item && item.kind === 'card' && item.deck_or_source_id && (
          <DeckReviewStatsBar
            deckId={item.deck_or_source_id}
            deckName={item.deck_name}
            lastUpdated={deckStatsTrigger}
            onStartPersist={(id, unseenOnly) => startPersistMode(id, item.deck_name || undefined, unseenOnly)}
            isPersistActive={persistActive}
            onOpenDeckViewer={() => setDeckViewerOpen(true)}
            onStartAllCardsRun={(id) => void startAllCardsRun(id, item.deck_name || undefined)}
            onExitAllCardsRun={exitAllCardsRun}
            isAllCardsRunActive={allCardsRunActive}
          />
        )}

        {draftRestoredNotice && (
          <div className="flex items-center justify-between rounded-lg border border-indigo-500/40 bg-indigo-500/10 px-3 py-2 text-xs text-indigo-200 shadow-sm animate-in fade-in duration-200">
            <div className="flex items-center gap-2">
              
              <div>
                <span className="font-semibold">{draftRestoredNotice}</span>
                <span className="text-indigo-300/80 ml-2 text-[0.6875rem]">— your work-in-progress solution and unit tests were restored.</span>
              </div>
            </div>
            <button
              type="button"
              onClick={() => setDraftRestoredNotice(null)}
              className="text-xs text-indigo-300 hover:text-white underline cursor-pointer"
            >
              dismiss
            </button>
          </div>
        )}

        {isCodeCard && layoutMode === 'split' ? (
          /* ════════════════════════════════════════════════════════════════════
             LEETCODE-STYLE SPLIT IDE WORKBENCH WITH RIGHT MARGIN LEXICON
             Left: Problem specs, primer, guide, solution, LLM rubric & grades
             Center: Editor & interactive sandbox testcase console
             Right Margin: Persistent Card Concordance & Lexicon definitions
             ════════════════════════════════════════════════════════════════════ */
          <div className="flex flex-col xl:flex-row items-start gap-4 w-full">
            <div
              ref={workbenchContainerRef}
              className={`flex-1 w-full min-w-0 transition-all ${
                workbenchLayout.isStacked
                  ? 'flex flex-col gap-4'
                  : 'flex flex-col lg:flex-row items-stretch gap-0 relative'
              }`}
            >
            {/* Left Column: Problem & Review Pane */}
            {workbenchLayout.leftCollapsed ? (
              <button
                type="button"
                className={`hidden lg:flex flex-col items-center py-4 px-2 bg-[#161a22] border border-ink-line rounded-xl cursor-pointer hover:bg-[#1c2230] hover:border-sky-500/50 transition-all select-none shrink-0 self-stretch my-0.5 mx-1 shadow-md group focus:outline-none focus-visible:ring-2 focus-visible:ring-sky-400 ${
                  workbenchLayout.columnsSwapped ? 'order-3' : 'order-1'
                }`}
                style={{ width: '42px' }}
                onClick={workbenchLayout.toggleLeftCollapsed}
                title="Click to expand Problem Description"
                aria-label="Expand Problem Description panel"
              >
                <div
                  className="w-6 h-6 rounded-full bg-sky-950 border border-sky-500/50 text-sky-300 flex items-center justify-center text-xs font-bold shadow group-hover:scale-110 transition-transform mb-3 shrink-0"
                >
                  {workbenchLayout.columnsSwapped ? '‹' : '›'}
                </div>
                <div className="flex-1 flex items-center justify-center">
                  <span
                    className="text-[0.6875rem] font-semibold text-slate-400 group-hover:text-sky-200 tracking-wider uppercase whitespace-nowrap"
                    style={{ writingMode: 'vertical-rl', transform: 'rotate(180deg)' }}
                  >
                    {revealed ? 'Assessment & Specs' : 'Problem Description'}
                  </span>
                </div>
                {revealed && (
                  <span className="w-2.5 h-2.5 rounded-full bg-emerald-400 my-1 shadow-sm ring-2 ring-emerald-500/40 animate-pulse" title="Assessment & Rubric Ready" />
                )}
                {currentFailureReminder && (
                  <span
                    className="w-5 h-5 rounded-full bg-amber-500/20 border border-amber-500/40 text-amber-300 my-1 flex items-center justify-center text-[0.625rem]"
                    title={currentFailureReminder}
                  >
                    
                  </span>
                )}
                <span className="text-[0.625rem] text-slate-500 mt-2 font-mono">
                  {item.difficulty || 'Code'}
                </span>
              </button>
            ) : (
              <div
                style={
                  workbenchLayout.isStacked ? undefined : { width: `${workbenchLayout.leftWidthPercent}%` }
                }
                className={`card space-y-4 min-w-[260px] flex-shrink-0 ${
                  workbenchLayout.columnsSwapped ? 'order-3' : 'order-1'
                } ${workbenchLayout.isStacked ? 'w-full' : 'overflow-y-auto max-h-[calc(100vh-140px)]'}`}
              >
                <div className="flex flex-wrap items-center justify-between gap-2 text-xs text-slate-500">
                  <div className="flex flex-wrap items-center gap-1.5">
                    <span className="chip">{item.deck_name}</span>
                    {(item.deck_or_source_id || deckParam) && (
                      <button
                        type="button"
                        onClick={() => setDeckViewerOpen(true)}
                        className="chip bg-sky-950/60 border-sky-500/40 text-sky-300 hover:bg-sky-900/60 hover:text-white transition cursor-pointer flex items-center gap-1 font-semibold"
                        title="Cards (Alt+D)"
                      >
                        <span>Cards</span>
                      </button>
                    )}
                    {savedCount > 0 && (
                      <button
                        type="button"
                        onClick={() => setSavedDrawerOpen(true)}
                        className="chip bg-indigo-950/60 border-indigo-500/40 text-indigo-300 hover:bg-indigo-900/60 hover:text-white transition cursor-pointer flex items-center gap-1 font-semibold"
                        title="Saved (Alt+Shift+S)"
                      >
                        <span>Saved ({savedCount})</span>
                      </button>
                    )}
                    {item.difficulty && (
                      <span
                        className={`chip font-semibold ${
                          item.difficulty === 'Easy'
                            ? 'border-emerald-500/40 text-emerald-300'
                            : item.difficulty === 'Medium'
                            ? 'border-amber-500/40 text-amber-300'
                            : 'border-rose-500/40 text-rose-300'
                        }`}
                      >
                        {item.difficulty}
                      </span>
                    )}
                    {item.category && <span className="chip text-sky-300">{item.category}</span>}
                    <span className="chip">Code Exercise</span>
                    {!revealed && (
                      <button
                        type="button"
                        onClick={togglePrimer}
                        className={`chip cursor-pointer transition-colors flex items-center gap-1.5 font-medium ${
                          showPrimer
                            ? 'border-sky-500/60 bg-sky-500/20 text-sky-200'
                            : 'border-ink-line text-slate-300 hover:text-slate-100 hover:border-slate-500'
                        }`}
                        title="Review related source passages and primer before answering"
                      >
                        <span>{showPrimer ? 'Hide Primer' : 'Primer'}</span>
                      </button>
                    )}
                    {currentFailureReminder ? (
                      <button
                        type="button"
                        onClick={() => {
                          if (dismissedReminderCardId === item.id) {
                            setDismissedReminderCardId(null)
                            setFailureReminderEnabled(true)
                          } else {
                            setFailureReminderEnabled((prev) => !prev)
                          }
                        }}
                        className={`chip cursor-pointer transition-colors flex items-center gap-1 font-medium ${
                          failureReminderEnabled && dismissedReminderCardId !== item.id
                            ? 'border-amber-500/50 bg-amber-500/20 text-amber-300 hover:bg-amber-500/30'
                            : 'border-ink-line text-slate-400 hover:text-amber-300 hover:border-amber-500/40'
                        }`}
                        title={currentFailureReminder}
                      >
                        <span>{failureReminderEnabled && dismissedReminderCardId !== item.id ? 'Prior Mistake' : 'Show Past Mistake'}</span>
                      </button>
                    ) : item.active_weaknesses && item.active_weaknesses.length > 0 ? (
                      <button
                        type="button"
                        onClick={() => {
                          if (!weaknessHint) void handleRequestWeaknessHint()
                          else setShowWeaknessHint((v) => !v)
                        }}
                        className="chip cursor-pointer border-amber-500/40 bg-amber-500/10 text-amber-300 hover:bg-amber-500/20 transition-colors font-medium"
                        title={item.active_weaknesses.join('; ')}
                      >
                        {item.active_weaknesses.length} prior {item.active_weaknesses.length === 1 ? 'mistake' : 'mistakes'}
                      </button>
                    ) : null}
                  </div>

                  <div className="flex items-center gap-2">
                    <button
                      type="button"
                      onClick={isIdePoppedOut ? handleDockBackIde : handlePopOutIde}
                      className={`chip cursor-pointer transition-colors flex items-center gap-1 font-semibold ${
                        isIdePoppedOut
                          ? 'border-sky-500/60 bg-sky-950/60 text-sky-200'
                          : 'border-sky-500/40 text-sky-300 hover:bg-sky-500/10'
                      }`}
                      title={isIdePoppedOut ? 'Dock IDE back to this window (Esc / Alt+P)' : 'Expand IDE into separate window (Alt+P)'}
                    >
                      <span>{isIdePoppedOut ? '⤓' : '⧉'}</span>
                      <span className="hidden sm:inline">{isIdePoppedOut ? 'Dock IDE' : 'Pop Out IDE'}</span>
                    </button>
                    <button
                      type="button"
                      onClick={toggleLayoutMode}
                      className="chip cursor-pointer border-ink-line text-slate-400 hover:text-slate-200 transition-colors"
                      title="Switch to single card view"
                    >
                      Classic Card
                    </button>
                    <button
                      type="button"
                      onClick={workbenchLayout.toggleLeftCollapsed}
                      className="chip cursor-pointer border-ink-line text-slate-400 hover:text-sky-300 hover:border-sky-500/40 transition-colors flex items-center gap-1"
                      title="Collapse problem description (Focus mode)"
                    >
                      <span>{workbenchLayout.columnsSwapped ? '›' : '‹'}</span>
                      <span className="hidden sm:inline">Collapse</span>
                    </button>
                    <button
                      type="button"
                      onClick={workbenchLayout.toggleColumnsSwapped}
                      className="chip cursor-pointer border-ink-line text-slate-400 hover:text-slate-200 transition-colors flex items-center gap-1"
                      title="Move problem panel to other side"
                    >
                      <span>⇄</span>
                      <span className="hidden sm:inline">Swap</span>
                    </button>
                  </div>
                </div>

              {/* Related Content Drawer / Primer */}
              {!revealed && showPrimer && (
                <PrimerDrawer
                  item={item}
                  lesson={primerLesson}
                  loading={primerLoading}
                  onReady={() => {
                    setShowPrimer(false)
                    shownAt.current = Date.now()
                  }}
                />
              )}

              {/* Prior Failure Reminder Banner */}
              {renderFailureReminder()}

              {/* Problem Title & Statement */}
              <div>
                {item.title && <h2 className="text-xl font-bold text-slate-100 mb-2">{item.title}</h2>}
                <RichText
                  text={item.front ?? ''}
                  className="text-base leading-relaxed text-slate-200"
                  codeLanguage={codeLanguage}
                  deckId={item.kind === 'card' ? item.deck_or_source_id : null}
                />
              </div>

              {/* Complexity & Constraints Box */}
              {(item.time_complexity || item.space_complexity || (item.edge_cases && item.edge_cases.length > 0)) && (
                <div className="rounded-lg border border-ink-line/70 bg-ink-soft/40 p-3 space-y-2 text-xs">
                  <p className="font-semibold text-slate-400 uppercase tracking-wider text-[0.625rem]">
                    Target Complexity &amp; Constraints:
                  </p>
                  <div className="flex flex-wrap gap-4 text-slate-300">
                    {item.time_complexity && (
                      <span>
                        <strong>Time:</strong> <code className="text-sky-300 font-mono font-bold">{item.time_complexity}</code>
                      </span>
                    )}
                    {item.space_complexity && (
                      <span>
                        <strong>Space:</strong> <code className="text-sky-300 font-mono font-bold">{item.space_complexity}</code>
                      </span>
                    )}
                  </div>
                  {item.edge_cases && item.edge_cases.length > 0 && (
                    <div className="pt-1 border-t border-ink-line/50">
                      <span className="text-slate-400 font-medium">Critical Edge Cases: </span>
                      <span className="text-amber-200/90 italic">{item.edge_cases.join(', ')}</span>
                    </div>
                  )}
                </div>
              )}

              {/* Thematic Context & Documentation */}
              {user?.show_thematic_context !== false && (
                <ThematicDocumentationCard item={item} />
              )}

              {/* Pre-reveal action & Socratic guide */}
              {!revealed && (
                <div className="space-y-3 pt-2">
                  {skipReviewRecording && (
                    <div className="rounded-lg border border-amber-500/40 bg-amber-500/10 px-3 py-2 text-xs text-amber-200 shadow-sm flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <span className="font-bold uppercase tracking-wider text-[0.6875rem] bg-amber-500/20 px-1.5 py-0.5 rounded border border-amber-500/30">
                           Skip Grading Active
                        </span>
                        <span>Type your solution and test/grade it. Your grade will not be recorded as a card review.</span>
                      </div>
                      <button
                        type="button"
                        className="text-[0.6875rem] underline text-amber-400 hover:text-amber-100 ml-2 shrink-0 cursor-pointer"
                        onClick={() => setSkipReviewRecording(false)}
                      >
                        Cancel
                      </button>
                    </div>
                  )}
                  <div className="flex flex-wrap items-center justify-between gap-2 border-t border-ink-line/60 pt-3">
                    <div className="flex items-center gap-2">
                      {llmEnabled && (
                        <DiscreteModelSelector
                          activeModel={activeModel}
                          installedModels={installedModels}
                          grading={grading}
                          hasAnswer={Boolean(answer.trim())}
                          onSelectModel={(m) => void handleSwitchModel(m)}
                          onGradeWithModel={(m) => void handleGradeWithModel(m)}
                        />
                      )}
                      {llmEnabled ? (
                        <button
                          className={`btn ${skipReviewRecording ? 'btn-secondary border-amber-500/50 text-amber-200' : 'btn-primary'}`}
                          onClick={() => void grade()}
                          disabled={grading || !answer.trim()}
                        >
                          {grading ? 'Evaluating…' : skipReviewRecording ? 'Grade for Rubric (Unrecorded)' : 'Submit for LLM Rubric'}
                        </button>
                      ) : null}
                      <button
                        type="button"
                        className={`btn ${skipReviewRecording ? 'border-amber-500/60 text-amber-300 bg-amber-500/15 font-semibold' : ''}`}
                        onClick={handleSkipGrading}
                        disabled={grading}
                        title={skipReviewRecording ? 'Advance to next card without recording review' : 'Type code and grade with LLM rubric without recording a card review'}
                      >
                        <span>{skipReviewRecording ? 'Skip card (Unrecorded)' : 'Skip grading'}</span>
                      </button>
                      <button className="btn" onClick={reveal} disabled={grading}>
                        {llmEnabled ? 'Show Reference Solution' : 'Show solution'}
                      </button>
                      <button
                        type="button"
                        onClick={() => void handleSaveForLater()}
                        className="btn border-indigo-500/40 text-indigo-300 hover:bg-indigo-500/15 flex items-center gap-1.5"
                        title="Save your drafted code and advance to next card (Alt+L)"
                      >
                        
                        <span>Save for Later</span>
                      </button>
                    </div>
                    <span className="text-xs text-slate-500 font-mono">Cmd/Ctrl + Enter</span>
                  </div>

                  {/* Longitudinal Weakness Hint Box */}
                  {showWeaknessHint && (
                    <div className="rounded-lg border border-amber-500/40 bg-amber-500/10 p-3 space-y-1.5 text-xs text-amber-200">
                      <div className="flex items-center justify-between font-semibold">
                        <span className="flex items-center gap-1.5">
                          
                          <span>Past Mistake Diagnostic Hint:</span>
                        </span>
                        <button
                          type="button"
                          className="text-[0.6875rem] underline text-amber-400 hover:text-amber-200"
                          onClick={() => setShowWeaknessHint(false)}
                        >
                          hide
                        </button>
                      </div>
                      {weaknessHintLoading ? (
                        <p className="text-amber-300/70 italic">Consulting past weakness memory…</p>
                      ) : weaknessHintError ? (
                        <p className="text-rose-300 leading-relaxed">{weaknessHintError}</p>
                      ) : weaknessHint ? (
                        <p className="text-amber-100 leading-relaxed">{weaknessHint}</p>
                      ) : null}
                    </div>
                  )}

                  <div className="flex flex-wrap items-center gap-2">
                    {llmEnabled && !guideOpen && (
                      <button className="btn text-xs" onClick={openGuide}>
                        Stuck? Ask your Socratic Guide
                      </button>
                    )}
                    {item.active_weaknesses && item.active_weaknesses.length > 0 && (
                      <button
                        type="button"
                        className="btn text-xs border-amber-500/40 text-amber-300 hover:bg-amber-500/15"
                        onClick={() => {
                          if (!weaknessHint) void handleRequestWeaknessHint()
                          else setShowWeaknessHint((v) => !v)
                        }}
                      >
                        {showWeaknessHint ? 'Hide Past Mistake Hint' : 'Past Mistake Hint'}
                      </button>
                    )}
                  </div>

                  {llmEnabled && guideOpen && (
                    <SocraticGuide
                      history={guideHistory}
                      input={guideInput}
                      onInputChange={setGuideInput}
                      loading={guideLoading}
                      degraded={guideDegraded}
                      onTrack={guideOnTrack}
                      onSend={() => void askGuide(guideInput)}
                      onClose={() => setGuideOpen(false)}
                      onCommit={() => setGuideOpen(false)}
                      onRetry={() => void askGuide(guideInput || '')}
                    />
                  )}
                </div>
              )}

              {/* Post-reveal assessment */}
              {revealed && (
                <div className="space-y-4 border-t border-ink-line pt-4">
                  <CopyLearningSummaryButton
                    item={item}
                    answer={answer}
                    testCode={testCode}
                    result={result}
                    codeLanguage={codeLanguage}
                    codeRunResult={codeRunResult}
                    variant="prominent"
                    className="w-full"
                  />
                  {!isCodeCard && (
                    <AnswerComparison
                      userAnswer={answer}
                      userTestCode={testCode}
                      referenceAnswer={result?.reference_answer || item.back || ''}
                      isCodeCard={isCodeCard}
                      codeLanguage={codeLanguage}
                      timeComplexity={item.time_complexity}
                      overlookedPhrases={overlookedTerms}
                      matchedPhrases={matchedTerms}
                    />
                  )}

                  {result?.latency_note && (
                    <p className="text-xs text-slate-600" title="Informational only — never affects the grade">
                      {formatLatencyNote(result.latency_note)}
                    </p>
                  )}

                  {result && !result.degraded_to_manual && (
                    <OverlookedAnalysisCard result={result} />
                  )}

                  <ReferenceReadings
                    references={item.references}
                    overlookedPhrases={overlookedTerms}
                    matchedPhrases={matchedTerms}
                  />

                  {result && !result.degraded_to_manual && (
                    <GradeReasoning
                      result={result}
                      installedModels={installedModels}
                      activeModel={activeModel}
                      grading={grading}
                      hasAnswer={Boolean(answer.trim())}
                      onSelectModel={(m) => void handleSwitchModel(m)}
                      onGradeWithModel={(m) => void handleGradeWithModel(m)}
                    />
                  )}

                  {result?.vram_constrained && !vramDismissed ? (
                    <VramConstraintPrompt
                      result={result}
                      loading={grading}
                      onSwitchModel={(model) => void grade(model, true)}
                      onRetry={() => void grade(result.failed_model || undefined)}
                      onGradeManually={() => setVramDismissed(true)}
                    />
                  ) : result?.degraded_to_manual && result.degraded_reason !== 'consent_not_given' ? (
                    <div className="rounded-lg border border-amber-500/40 bg-amber-500/10 px-4 py-3 text-sm text-amber-200">
                      Automatic grading was unavailable ({result.degraded_reason}). Grade it yourself — your
                      scheduling is unaffected.
                    </div>
                  ) : null}

                  {skipReviewRecording ? (
                    <div className="rounded-xl border border-amber-500/40 bg-amber-500/10 p-4 space-y-3">
                      <div className="flex items-center justify-between">
                        <span className="text-xs font-bold uppercase tracking-wider text-amber-300 flex items-center gap-1.5">
                           Unrecorded Practice Mode
                        </span>
                        <span className="chip border-amber-500/30 text-amber-300 bg-amber-500/20 text-[0.625rem]">
                          Review Not Recorded
                        </span>
                      </div>
                      <p className="text-xs text-slate-300 leading-relaxed">
                        You typed and graded your solution without recording a card review. Your review queue and spaced repetition schedule are unaffected.
                      </p>
                      <div className="flex flex-wrap items-center gap-2 pt-1">
                        <button
                          type="button"
                          className="btn btn-primary text-xs px-4 py-2 font-bold shadow-sm cursor-pointer"
                          onClick={() => void advanceWithoutReview()}
                          title="Advance to next card (Space / Enter)"
                        >
                          <span>Next Card (No review recorded) →</span>
                        </button>
                        <button
                          type="button"
                          className="btn text-xs px-3 py-2 cursor-pointer"
                          onClick={() => {
                            setRevealed(false)
                          }}
                          title="Edit your code and grade again"
                        >
                          <span>Edit &amp; Re-grade</span>
                        </button>
                        <button
                          type="button"
                          className="btn text-xs px-3 py-2 bg-amber-500/20 hover:bg-amber-500/30 text-amber-200 border border-amber-500/40 cursor-pointer"
                          onClick={handleRetryWithoutRecording}
                          title="Clear input and retry card from scratch (unrecorded)"
                        >
                         <span> Fresh Retry</span>
                        </button>
                        <button
                          type="button"
                          className="btn text-xs px-2.5 py-1 text-slate-400 hover:text-slate-200 cursor-pointer"
                          onClick={() => {
                            setSkipReviewRecording(false)
                          }}
                          title="Enable standard grade buttons to record this review"
                        >
                          <span>Record this review anyway</span>
                        </button>
                      </div>
                    </div>
                  ) : (
                    <div className="review-grade-bar">
                      <div className="mb-2 flex items-center justify-between flex-wrap gap-2">
                        <p className="label mb-0">
                          {result && !result.degraded_to_manual
                            ? result.needs_confirmation
                              ? 'Confirm or correct the grade'
                              : 'Accept the suggestion, or override'
                            : 'How well did you recall it?'}
                        </p>
                        <div className="flex items-center gap-2">
                          {isCodeCard && (
                            <>
                              <button
                                type="button"
                                onClick={() => handleHideSolution('hint')}
                                className="text-[0.6875rem] text-amber-300 hover:text-amber-100 flex items-center gap-1 cursor-pointer bg-amber-500/15 hover:bg-amber-500/25 px-2.5 py-0.5 rounded border border-amber-500/40 transition font-medium shadow-sm"
                                title="Hide full solution, enable line hints, and return to practice mode (Alt+U)"
                              >
                               <span> Use Line Hints &amp; Keep Practicing</span>
                              </button>
                              <button
                                type="button"
                                onClick={() => handleHideSolution('hide')}
                                className="text-[0.6875rem] text-slate-300 hover:text-white flex items-center gap-1 cursor-pointer bg-white/5 hover:bg-white/10 px-2 py-0.5 rounded border border-white/15 transition font-medium"
                                title="Lock reference solution and return to practice mode"
                              >
                               <span> Hide Solution</span>
                              </button>
                            </>
                          )}
                          <button
                            type="button"
                            className="text-[0.6875rem] text-slate-500 hover:text-amber-300 underline cursor-pointer"
                            onClick={() => setSkipReviewRecording(true)}
                            title="Don't record this card review"
                          >
                            Skip recording this review
                          </button>
                        </div>
                      </div>
                      <div className="flex flex-wrap gap-2">
                        {GRADES.map((g, i) => {
                          const suggested =
                            result && !result.degraded_to_manual && result.suggested_grade === g
                          return (
                            <button
                              key={g}
                              onClick={() => confirm(g, { retryImmediately: retryAfterRating })}
                              disabled={confirming}
                              className={`btn ${GRADE_STYLE[g]} ${
                                suggested ? 'ring-1 ring-inset ring-current' : ''
                              }`}
                              title={retryAfterRating ? `Record as ${g.toUpperCase()} and retry card immediately` : `Record as ${g.toUpperCase()} and advance to next card`}
                            >
                              {retryAfterRating && <span className="text-xs" aria-hidden="true">↻</span>}
                              <span className="capitalize">{g}</span>
                              <span className="text-xs opacity-50">{GRADE_BAND[g]}</span>
                              <span className="text-xs opacity-50">{i + 1}</span>
                              {suggested && <span className="text-xs opacity-70">· suggested</span>}
                              {persistActive && (
                                <span
                                  className={`text-[0.625rem] ml-1 px-1.5 py-0.5 rounded font-semibold ${
                                    g === 'easy'
                                      ? 'bg-emerald-500/30 text-emerald-200 border border-emerald-500/50'
                                      : 'bg-amber-500/20 text-amber-200 border border-amber-500/40'
                                  }`}
                                >
                                  {g === 'easy' ? 'Grasps' : 'Re-queues'}
                                </span>
                              )}
                            </button>
                          )
                        })}
                      </div>

                      {/* Immediate Retry Action Bar */}
                      {renderRetryActionBar()}
                    </div>
                  )}
                </div>
              )}
            </div>
            )}

            {/* Splitter between Problem Column & Workbench Column */}
            {!workbenchLayout.leftCollapsed && !workbenchLayout.isStacked && (
              <div className="order-2 flex items-stretch">
                <ResizableSplitter
                  direction="horizontal"
                  onResize={(delta) => {
                    const width = workbenchContainerRef.current?.getBoundingClientRect().width || 1200
                    workbenchLayout.handleMainResize(delta, width)
                  }}
                  onDoubleClick={workbenchLayout.resetMainSplit}
                  onToggleCollapse={workbenchLayout.toggleLeftCollapsed}
                  isCollapsed={workbenchLayout.leftCollapsed}
                  collapseTooltip="Drag to resize Problem panel / Double-click to reset / Click chevron to collapse"
                />
              </div>
            )}

            {/* Right Column: Code Editor & Test Console */}
            <div
              style={
                workbenchLayout.isStacked
                  ? undefined
                  : {
                      width: workbenchLayout.leftCollapsed
                        ? 'calc(100% - 48px)'
                        : `${100 - workbenchLayout.leftWidthPercent}%`,
                    }
              }
              className={`min-w-[320px] flex-1 min-w-0 ${
                workbenchLayout.columnsSwapped ? 'order-1' : 'order-3'
              } ${workbenchLayout.isStacked ? 'w-full' : ''}`}
            >
              {isIdePoppedOut ? (
                <div className="card border border-ink-line bg-[#161a22]/80 p-8 flex flex-col items-center justify-center text-center space-y-4 min-h-[460px] shadow-xl">
                  <div className="w-16 h-16 rounded-2xl bg-sky-950/80 border border-sky-500/40 text-sky-400 flex items-center justify-center text-3xl shadow-lg ring-1 ring-sky-500/30">
                    ⧉
                  </div>
                  <div className="space-y-1">
                    <h3 className="text-lg font-bold text-slate-100">IDE Popped Out in Separate Window</h3>
                    <p className="text-sm text-slate-400 max-w-md">
                      Your code editor, tests, and sandbox test runner are running in a dedicated window.
                    </p>
                  </div>
                  <div className="flex flex-wrap items-center justify-center gap-3 pt-2">
                    <button
                      type="button"
                      onClick={() => idePopupRef.current?.focus()}
                      className="btn btn-primary text-xs px-4 py-2 font-semibold shadow-sm flex items-center gap-1.5 cursor-pointer"
                      title="Bring the separate IDE window to the front"
                    >
                     <span> Bring to Front</span>
                    </button>
                    <button
                      type="button"
                      onClick={handleDockBackIde}
                      className="btn text-xs px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-600 flex items-center gap-1.5 cursor-pointer"
                      title="Dock IDE back into this window (Esc / Alt+P)"
                    >
                      <span>⤓ Dock Back Here</span>
                      <kbd className="text-[0.625rem] bg-slate-900 px-1.5 py-0.5 rounded text-slate-400">Esc</kbd>
                    </button>
                  </div>
                </div>
              ) : (
                renderIdeWorkbench(false)
              )}
            </div>
          {isIdePoppedOut &&
            idePopupRef.current &&
            createPortal(
              renderIdeWorkbench(true),
              idePopupRef.current.document.getElementById('ars-ide-popout-root') ||
                idePopupRef.current.document.body,
            )}
            </div>

            {/* Right Margin: Concordance, Lexicon & Persistent Card Memory */}
            {!isIdePoppedOut && (
              <aside
                className={`shrink-0 transition-all duration-200 xl:sticky xl:top-16 ${
                  workbenchMarginCollapsed ? 'w-full xl:w-12' : 'w-full xl:w-72 2xl:w-80'
                }`}
              >
                <MarginLexiconPanel
                  cardId={item.id}
                  deckId={item.kind === 'card' ? item.deck_or_source_id : null}
                  deckName={item.deck_name}
                  thematicNature={item.card_thematic_nature || item.deck_thematic_nature}
                  cardFront={item.front}
                  cardBack={item.back}
                  initialGlosses={item.lexicon_glosses}
                  collapsedRailOnDesktop={true}
                  onCollapseChange={setWorkbenchMarginCollapsed}
                  codeLanguage={codeLanguage}
                  onGlossesUpdated={(updatedGlosses) => applyGlossesToCard(item.id, updatedGlosses)}
                />
              </aside>
            )}
          </div>
        ) : (
          /* ════════════════════════════════════════════════════════════════════
             CLASSIC CARD VIEW WITH MARGIN CONCORDANCE & LEXICON
             ════════════════════════════════════════════════════════════════════ */
          <div className="flex flex-col xl:flex-row items-start justify-center gap-6 max-w-[1750px] mx-auto px-2 sm:px-4">
            <div className="flex-1 w-full max-w-4xl min-w-0 xl:min-w-[500px]">
              <div className={`card ${isCodeCard && tiledTabs ? 'max-w-6xl' : 'w-full'} mx-auto`}>
            <div className="mb-3 flex flex-wrap items-center justify-between gap-2 text-xs text-slate-500">
              <div className="flex flex-wrap items-center gap-2">
                <span className="chip">{item.deck_name}</span>
                {(item.deck_or_source_id || deckParam) && (
                  <button
                    type="button"
                    onClick={() => setDeckViewerOpen(true)}
                    className="chip bg-sky-950/60 border-sky-500/40 text-sky-300 hover:bg-sky-900/60 hover:text-white transition cursor-pointer flex items-center gap-1 font-semibold"
                    title="Cards (Alt+D)"
                  >
                    
                    <span>Cards</span>
                  </button>
                )}
                {savedCount > 0 && (
                  <button
                    type="button"
                    onClick={() => setSavedDrawerOpen(true)}
                    className="chip bg-indigo-950/60 border-indigo-500/40 text-indigo-300 hover:bg-indigo-900/60 hover:text-white transition cursor-pointer flex items-center gap-1 font-semibold"
                    title="Saved (Alt+Shift+S)"
                  >
                    
                    <span>Saved ({savedCount})</span>
                  </button>
                )}
                <span className="chip">{item.state}</span>
                {item.difficulty && (
                  <span
                    className={`chip font-semibold ${
                      item.difficulty === 'Easy'
                        ? 'border-emerald-500/40 text-emerald-300'
                        : item.difficulty === 'Medium'
                        ? 'border-amber-500/40 text-amber-300'
                        : 'border-rose-500/40 text-rose-300'
                    }`}
                  >
                    {item.difficulty}
                  </span>
                )}
                {item.category && <span className="chip text-sky-300">{item.category}</span>}
                {item.grading_profile && <span className="chip">{item.grading_profile}</span>}
                <span className="chip">priority {item.priority}</span>
                {isCodeCard && (
                  <>
                    <button
                      type="button"
                      onClick={toggleLayoutMode}
                      className="chip cursor-pointer border-sky-500/40 text-sky-300 hover:bg-sky-500/10 transition-colors"
                      title="Split IDE"
                    >
                      Split IDE
                    </button>
                    <button
                      type="button"
                      onClick={handlePopOutIde}
                      className="chip cursor-pointer border-sky-500/50 bg-sky-950/40 text-sky-300 hover:bg-sky-900/50 hover:text-white transition-colors flex items-center gap-1 font-semibold"
                      title="Expand IDE into a separate window (Alt+P)"
                    >
                      <span>⧉</span>
                      <span>Pop Out IDE</span>
                    </button>
                  </>
                )}
                {!revealed && (
                  <button
                    type="button"
                    onClick={togglePrimer}
                    className={`chip cursor-pointer transition-colors flex items-center gap-1.5 font-medium ${
                      showPrimer
                        ? 'border-sky-500/60 bg-sky-500/20 text-sky-200'
                        : 'border-ink-line text-slate-300 hover:text-slate-100 hover:border-slate-500'
                    }`}
                    title="Primer"
                  >
                    
                    <span>{showPrimer ? 'Hide Primer' : 'Primer'}</span>
                  </button>
                )}
                {currentFailureReminder ? (
                  <button
                    type="button"
                    onClick={() => {
                      if (dismissedReminderCardId === item.id) {
                        setDismissedReminderCardId(null)
                        setFailureReminderEnabled(true)
                      } else {
                        setFailureReminderEnabled((prev) => !prev)
                      }
                    }}
                    className={`chip cursor-pointer transition-colors flex items-center gap-1 font-medium ${
                      failureReminderEnabled && dismissedReminderCardId !== item.id
                        ? 'border-amber-500/50 bg-amber-500/20 text-amber-300 hover:bg-amber-500/30'
                        : 'border-ink-line text-slate-400 hover:text-amber-300 hover:border-amber-500/40'
                    }`}
                    title={currentFailureReminder}
                  >
                    <span>{failureReminderEnabled && dismissedReminderCardId !== item.id ? 'Prior Mistake' : 'Show Past Mistake'}</span>
                  </button>
                ) : item.active_weaknesses && item.active_weaknesses.length > 0 ? (
                  <button
                    type="button"
                    onClick={() => {
                      if (!weaknessHint) void handleRequestWeaknessHint()
                      else setShowWeaknessHint((v) => !v)
                    }}
                    className="chip cursor-pointer border-amber-500/40 bg-amber-500/10 text-amber-300 hover:bg-amber-500/20 transition-colors font-medium"
                    title={item.active_weaknesses.join('; ')}
                  >
                    {item.active_weaknesses.length} prior {item.active_weaknesses.length === 1 ? 'mistake' : 'mistakes'}
                  </button>
                ) : null}

                {/* ── Neuroscience Enhancements Badges & Controls ── */}
                {item.is_schema_checkpoint && (
                  <span
                    className="chip border-amber-500/60 bg-amber-500/15 text-amber-300 font-bold flex items-center gap-1 shadow-sm"
                    title="Neocortical Schema Checkpoint: Foundational Mental Model Anchor"
                  >
                     Schema Checkpoint
                  </span>
                )}
                {item.spatial_locus && (
                  <span
                    className="chip border-emerald-500/40 bg-emerald-950/40 text-emerald-300 font-medium flex items-center gap-1"
                    title="Memory Palace Spatial Locus"
                  >
                     {item.spatial_locus}
                  </span>
                )}
                <button
                  type="button"
                  onClick={handleToggleMnemonic}
                  className={`chip cursor-pointer transition-colors flex items-center gap-1 font-medium ${
                    showMnemonic
                      ? 'border-purple-500/60 bg-purple-500/20 text-purple-200'
                      : 'border-ink-line text-slate-300 hover:text-purple-300 hover:border-purple-500/40'
                  }`}
                  title="View or generate bizarre Memory Palace visual mnemonic (Dual-Coding / Von Restorff)"
                >
                  <span>Mnemonic</span>
                </button>
                {!revealed && (
                  <button
                    type="button"
                    onClick={() => void handleMutatePrompt()}
                    disabled={mutationLoading}
                    className={`chip cursor-pointer transition-colors flex items-center gap-1 font-medium ${
                      mutatedPrompt
                        ? 'border-cyan-500/60 bg-cyan-500/20 text-cyan-200'
                        : 'border-ink-line text-slate-300 hover:text-cyan-300 hover:border-cyan-500/40'
                    }`}
                    title="Reconsolidation: Test core invariant from an orthogonal angle"
                  >
                    <span>{mutationLoading ? 'Mutating…' : mutatedPrompt ? 'Mutated Angle' : 'Mutate Prompt'}</span>
                  </button>
                )}
                <button
                  type="button"
                  onClick={handleToggleAssociative}
                  className={`chip cursor-pointer transition-colors flex items-center gap-1 font-medium ${
                    showAssociative
                      ? 'border-indigo-500/60 bg-indigo-500/20 text-indigo-200'
                      : 'border-ink-line text-slate-300 hover:text-indigo-300 hover:border-indigo-500/40'
                  }`}
                  title="Spreading activation: explore primed semantic connections"
                >
                  <span>Associative</span>
                </button>
                {!revealed && (
                  <button
                    type="button"
                    onClick={() => setShowPretest((v) => !v)}
                    className={`chip cursor-pointer transition-colors flex items-center gap-1 font-medium ${
                      showPretest
                        ? 'border-emerald-500/60 bg-emerald-500/20 text-emerald-200'
                        : 'border-ink-line text-slate-300 hover:text-emerald-300 hover:border-emerald-500/40'
                    }`}
                    title="Pre-test hypothesis generation: guess before revealing to prime dopaminergic RPE"
                  >
                    <span>{showPretest ? 'Hide Hypothesis' : 'Hypothesize'}</span>
                  </button>
                )}
              </div>
            </div>

            {/* Related Content Drawer / Primer */}
            {!revealed && showPrimer && (
              <PrimerDrawer
                item={item}
                lesson={primerLesson}
                loading={primerLoading}
                onReady={() => {
                  setShowPrimer(false)
                  shownAt.current = Date.now()
                  inputRef.current?.focus()
                }}
              />
            )}

            {/* Prior Failure Reminder Banner */}
            {renderFailureReminder()}

            {item.title && <h2 className="text-xl font-bold text-slate-100 mb-2">{item.title}</h2>}

            {item.occlusion ? (
              <div className="space-y-3">
                {item.occlusion.header && (
                  <p className="text-lg leading-relaxed text-slate-100">{item.occlusion.header}</p>
                )}
                <OcclusionCard payload={item.occlusion} revealed={revealed} />
              </div>
            ) : (
              <RichText
                text={item.front ?? ''}
                className="text-lg leading-relaxed text-slate-100"
                codeLanguage={codeLanguage}
                deckId={item.kind === 'card' ? item.deck_or_source_id : null}
              />
            )}

            {/* ── Reconsolidation Mutated Prompt Panel ── */}
            {mutatedPrompt && (
              <div className="mt-3 rounded-xl border border-cyan-500/40 bg-gradient-to-r from-cyan-950/40 via-[#0d1820] to-[#0a1218] p-3 text-xs text-cyan-200 shadow-md animate-in fade-in">
                <div className="flex items-center justify-between gap-2 border-b border-cyan-500/20 pb-2 mb-2">
                  <div className="flex items-center gap-2">
                    <span className="font-bold uppercase tracking-wider text-[0.625rem] text-cyan-300">
                       Reconsolidation Variant ({mutationType})
                    </span>
                    <span className="text-[0.625rem] text-cyan-400/60 font-mono">
                      • testing invariant invariance
                    </span>
                  </div>
                  <div className="flex items-center gap-1.5">
                    <select aria-label="How to vary the prompt"
                      value={mutationType}
                      onChange={(e) => void handleMutatePrompt(e.target.value)}
                      className="text-[0.6875rem] bg-slate-900 border border-slate-700 text-slate-200 rounded px-1.5 py-0.5 cursor-pointer"
                    >
                      <option value="counterfactual">Counterfactual</option>
                      <option value="scenario">Scenario</option>
                      <option value="adversarial">Adversarial</option>
                      <option value="perspective">Perspective</option>
                    </select>
                    <button
                      type="button"
                      onClick={() => setMutatedPrompt(null)}
                      className="text-xs text-slate-400 hover:text-white px-1 font-mono"
                      title="Reset to original front prompt"
                    >
                      ✕
                    </button>
                  </div>
                </div>
                <p className="text-sm text-cyan-100 font-medium leading-relaxed">
                  {mutatedPrompt}
                </p>
              </div>
            )}

            {/* ── Mnemonic Palace Anchor (Von Restorff / Dual-Coding) ── */}
            {showMnemonic && (
              <div className="mt-3 rounded-xl border border-purple-500/40 bg-gradient-to-r from-purple-950/40 via-[#150d1e] to-[#0f0915] p-3.5 text-xs text-purple-200 shadow-md animate-in fade-in">
                <div className="flex items-center justify-between gap-2 border-b border-purple-500/20 pb-2 mb-2">
                  <div className="flex items-center gap-2">
                    <span className="font-bold uppercase tracking-wider text-[0.625rem] text-purple-300">
                       Memory Palace Anchor (Bizarre Visual Vignette)
                    </span>
                    {item.spatial_locus && (
                      <span className="chip text-[0.625rem] border-purple-500/30 text-purple-300 bg-purple-500/10">
                        {item.spatial_locus}
                      </span>
                    )}
                  </div>
                  <div className="flex items-center gap-2">
                    <button
                      type="button"
                      disabled={mnemonicLoading}
                      onClick={handleRegenerateMnemonic}
                      className="text-[0.6875rem] text-purple-300 hover:text-white flex items-center gap-1 bg-purple-900/40 border border-purple-500/30 px-2 py-0.5 rounded cursor-pointer transition font-medium"
                    >
                      <span>{mnemonicLoading ? 'Synthesizing…' : '↻ Re-synthesize'}</span>
                    </button>
                    <button
                      type="button"
                      onClick={() => setShowMnemonic(false)}
                      className="text-xs text-purple-400 hover:text-white font-mono"
                    >
                      ✕
                    </button>
                  </div>
                </div>
                {mnemonicLoading ? (
                  <div className="py-2 text-center text-purple-300 flex items-center justify-center gap-2">
                    <Spinner /> <span>Synthesizing bizarre sensory imagery…</span>
                  </div>
                ) : mnemonicText ? (
                  <p className="text-sm text-purple-100 italic leading-relaxed">
                    "{mnemonicText}"
                  </p>
                ) : (
                  <p className="text-xs text-purple-400">
                    No visual mnemonic generated yet. Click Re-synthesize to create an absurd memory palace scene.
                  </p>
                )}
              </div>
            )}

            {/* ── Associative Network Spreading Activation ── */}
            {showAssociative && (
              <div className="mt-3 rounded-xl border border-indigo-500/40 bg-gradient-to-r from-indigo-950/40 via-[#0e0f1e] to-[#0a0b17] p-3.5 text-xs text-indigo-200 shadow-md animate-in fade-in">
                <div className="flex items-center justify-between gap-2 border-b border-indigo-500/20 pb-2 mb-2">
                  <div className="flex items-center gap-2">
                    <span className="font-bold uppercase tracking-wider text-[0.625rem] text-indigo-300">
                       Associative Network (Spreading Activation)
                    </span>
                    <span className="text-[0.625rem] text-indigo-300/90 font-mono">
                      • primed semantic representations
                    </span>
                  </div>
                  <button
                    type="button"
                    onClick={() => setShowAssociative(false)}
                    className="text-xs text-slate-400 hover:text-white font-mono"
                  >
                    ✕
                  </button>
                </div>
                {associativeLoading ? (
                  <div className="py-2 text-center text-indigo-300 flex items-center justify-center gap-2">
                    <Spinner /> <span>Traversing associative edges…</span>
                  </div>
                ) : relatedNodes.length > 0 ? (
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 mt-2">
                    {relatedNodes.map((node) => (
                      <div
                        key={node.card_id}
                        className="p-2 rounded-lg border border-indigo-500/20 bg-indigo-950/30 space-y-1 text-xs"
                      >
                        <div className="flex items-center justify-between gap-1">
                          <span className="font-medium text-slate-200 truncate">{node.title}</span>
                          <span className="text-[0.625rem] font-mono text-indigo-300 shrink-0">
                            {Math.round(node.activation * 100)}%
                          </span>
                        </div>
                        <div className="flex items-center justify-between text-[0.625rem] text-slate-400">
                          <span>{node.deck_name}</span>
                          <span className="italic text-indigo-300/80">{node.relationship_to_source}</span>
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="text-xs text-indigo-400/80">
                    No active associative edges found for this card yet. Connect related cards in the Decks view.
                  </p>
                )}
              </div>
            )}

            {/* ── Pre-Test Prediction Hypothesis Mode ── */}
            {!revealed && showPretest && (
              <div className="mt-3 rounded-xl border border-emerald-500/40 bg-gradient-to-r from-emerald-950/40 via-[#0d1a12] to-[#09140e] p-3.5 text-xs text-emerald-200 shadow-md animate-in fade-in">
                <div className="flex items-center justify-between gap-2 border-b border-emerald-500/20 pb-2 mb-2">
                  <div className="flex items-center gap-2">
                    <span className="font-bold uppercase tracking-wider text-[0.625rem] text-emerald-300">
                       Pre-Test Hypothesis (Dopaminergic Prediction Error)
                    </span>
                  </div>
                  <button
                    type="button"
                    onClick={() => setShowPretest(false)}
                    className="text-xs text-slate-400 hover:text-white font-mono"
                  >
                    ✕
                  </button>
                </div>
                <p className="text-xs text-slate-300 mb-2">
                  Formulate a hypothesis before looking at the reference. Even incorrect predictions prime synaptic plasticity.
                </p>
                <div className="space-y-2">
                  <textarea
                    value={pretestPrediction}
                    onChange={(e) => setPretestPrediction(e.target.value)}
                    placeholder="What do you predict is the core mechanism, reason, or answer?"
                    rows={2}
                    className="w-full text-xs bg-slate-900 border border-slate-700 rounded-lg p-2 text-slate-100 placeholder-slate-500 focus:outline-none focus:border-emerald-500"
                  />
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <div className="flex items-center gap-2">
                      <span className="text-[0.6875rem] text-slate-400">Confidence:</span>
                      <div className="flex items-center gap-1">
                        {[1, 2, 3, 4].map((lvl) => (
                          <button
                            key={lvl}
                            type="button"
                            onClick={() => setPretestConfidence(lvl)}
                            className={`px-2 py-0.5 rounded text-[0.625rem] font-bold transition ${
                              pretestConfidence === lvl
                                ? 'bg-emerald-500 text-slate-950'
                                : 'bg-slate-800 text-slate-400 hover:bg-slate-700'
                            }`}
                          >
                            {lvl === 1 ? '1 Wild Guess' : lvl === 2 ? '2 Low' : lvl === 3 ? '3 Probable' : '4 Solid'}
                          </button>
                        ))}
                      </div>
                    </div>
                    <button
                      type="button"
                      disabled={pretestSubmitting || !pretestPrediction.trim()}
                      onClick={handleSubmitPretest}
                      className="btn text-xs py-1 px-3 bg-emerald-700 hover:bg-emerald-600 text-white font-semibold rounded disabled:opacity-50 cursor-pointer"
                    >
                      {pretestSubmitting ? 'Evaluating…' : 'Test Prediction'}
                    </button>
                  </div>
                </div>
                {pretestResult && (
                  <div className={`mt-3 p-2.5 rounded-lg border text-xs ${
                    pretestResult.is_accurate
                      ? 'border-emerald-500/50 bg-emerald-950/50 text-emerald-200'
                      : pretestResult.high_confidence_error
                      ? 'border-rose-500/60 bg-rose-950/50 text-rose-200'
                      : 'border-amber-500/50 bg-amber-950/50 text-amber-200'
                  }`}>
                    <div className="font-bold flex items-center gap-1.5 mb-1">
                     <span>{pretestResult.is_accurate ? ' Accurate Prediction!' : pretestResult.high_confidence_error ? ' High-Confidence Prediction Error!' : ' Divergent Intuition'}</span>
                    </div>
                    <p className="leading-relaxed">{pretestResult.feedback}</p>
                  </div>
                )}
              </div>
            )}

            {/* Complexity hints if code card in classic view */}
            {isCodeCard && (item.time_complexity || item.space_complexity || (item.edge_cases && item.edge_cases.length > 0)) && (
              <div className="mt-3 rounded-lg border border-ink-line/70 bg-ink-soft/40 p-3 space-y-1.5 text-xs">
                <div className="flex flex-wrap gap-4 text-slate-300">
                  {item.time_complexity && (
                    <span><strong>Target Time:</strong> <code className="text-sky-300 font-mono">{item.time_complexity}</code></span>
                  )}
                  {item.space_complexity && (
                    <span><strong>Target Space:</strong> <code className="text-sky-300 font-mono">{item.space_complexity}</code></span>
                  )}
                </div>
                {item.edge_cases && item.edge_cases.length > 0 && (
                  <div>
                    <span className="text-slate-400">Edge Cases: </span>
                    <span className="text-amber-200/90 italic">{item.edge_cases.join(', ')}</span>
                  </div>
                )}
              </div>
            )}

            {/* Thematic Context & Documentation */}
            {user?.show_thematic_context !== false && (
              <div className="mt-3">
                <ThematicDocumentationCard item={item} />
              </div>
            )}

            {!revealed && (
              <div className="mt-6">
                <div className="mb-2 flex flex-wrap items-center justify-between gap-2">
                  <label className="label mb-0" htmlFor="answer">
                    {llmEnabled ? 'Type your answer' : 'Type your answer (optional — grading is manual)'}
                  </label>
                  <div className="flex items-center gap-1 text-xs">
                    <span className="mr-1 text-slate-500">Confidence:</span>
                    {[
                      { lvl: 1, label: '1: Guess', color: 'border-rose-500/40 text-rose-300' },
                      { lvl: 2, label: '2: Unsure', color: 'border-amber-500/40 text-amber-300' },
                      { lvl: 3, label: '3: Likely', color: 'border-sky-500/40 text-sky-300' },
                      { lvl: 4, label: '4: Solid', color: 'border-emerald-500/40 text-emerald-300' },
                    ].map(({ lvl, label, color }) => (
                      <button
                        key={lvl}
                        type="button"
                        onClick={() => setConfidence(confidence === lvl ? null : lvl)}
                        className={`rounded border px-2 py-0.5 text-[0.6875rem] transition-all ${
                          confidence === lvl
                            ? `${color} bg-white/10 font-medium ring-1 ring-inset ring-current`
                            : 'border-ink-line text-slate-400 hover:text-slate-200'
                        }`}
                        title={`Metacognitive Judgment of Learning: ${label}`}
                      >
                        {label}
                      </button>
                    ))}
                  </div>
                </div>
                {isCodeCard ? (
                  <div className="my-2 space-y-4">
                    <div className="rounded-lg border border-ink-line overflow-hidden">
                      <div className="flex flex-wrap items-center justify-between border-b border-ink-line bg-[#1e1e1e] px-3 py-1.5 text-xs gap-2">
                        <div className="flex flex-wrap items-center gap-2">
                          {tiledTabs ? (
                            <div className="flex flex-wrap items-center gap-2">
                              <div className="inline-flex rounded-md bg-[#161616] p-0.5 border border-ink-line shrink-0">
                                <span
                                  className="px-2 py-0.5 text-xs font-semibold rounded bg-sky-600/30 text-sky-200 border border-sky-500/50 shadow-sm flex items-center gap-1.5 cursor-default select-none shrink-0"
                                  title="Tiled side-by-side workbench active (Alt+S to untile)"
                                >
                                  <span>⧉</span>
                                  <span>Tiled</span>
                                </span>
                                <button
                                  type="button"
                                  onClick={toggleTiledTabs}
                                  className="px-2 py-0.5 text-xs font-medium rounded text-slate-400 hover:text-slate-200 flex items-center gap-1.5 transition cursor-pointer shrink-0"
                                  title="Switch to single tab mode (Alt+S)"
                                >
                                  <span>⊟</span>
                                  <span>Single Tab</span>
                                </button>
                              </div>

                              <div className="inline-flex items-center rounded-md bg-[#161616] p-0.5 border border-ink-line shrink-0 overflow-x-auto no-scrollbar">
                                <span className="text-[0.625rem] text-slate-500 px-1.5 font-medium uppercase tracking-wider shrink-0 select-none">Presets:</span>
                                <button
                                  type="button"
                                  onClick={() => {
                                    setTileLeftTab('solution')
                                    setTileRightTab('tests')
                                  }}
                                  className={`px-2 py-0.5 text-xs font-medium rounded transition flex items-center gap-1 cursor-pointer shrink-0 whitespace-nowrap ${
                                    tileLeftTab === 'solution' && tileRightTab === 'tests'
                                      ? 'bg-sky-600/40 text-sky-100 border border-sky-500/60 shadow-sm font-semibold'
                                      : 'text-slate-400 hover:text-slate-200'
                                  }`}
                                  title="Classic TDD: Solution on left, Unit Tests on right"
                                >
                                  <span>Sol</span>
                                  <span className="text-slate-500">↔</span>
                                  <span>Tests</span>
                                </button>
                                <button
                                  type="button"
                                  onClick={() => {
                                    setTileLeftTab('reference')
                                    setTileRightTab('solution')
                                  }}
                                  className={`px-2 py-0.5 text-xs font-medium rounded transition flex items-center gap-1 cursor-pointer shrink-0 whitespace-nowrap ${
                                    tileLeftTab === 'reference' && tileRightTab === 'solution'
                                      ? 'bg-sky-600/40 text-sky-100 border border-sky-500/60 shadow-sm font-semibold'
                                      : 'text-slate-400 hover:text-slate-200'
                                  }`}
                                  title="Compare Reference Solution alongside Solution"
                                >
                                  <span>Ref</span>
                                  <span className="text-slate-500">↔</span>
                                  <span>Sol</span>
                                </button>
                                <button
                                  type="button"
                                  onClick={() => {
                                    setTileLeftTab('reference')
                                    setTileRightTab('tests')
                                  }}
                                  className={`px-2 py-0.5 text-xs font-medium rounded transition flex items-center gap-1 cursor-pointer shrink-0 whitespace-nowrap ${
                                    tileLeftTab === 'reference' && tileRightTab === 'tests'
                                      ? 'bg-sky-600/40 text-sky-100 border border-sky-500/60 shadow-sm font-semibold'
                                      : 'text-slate-400 hover:text-slate-200'
                                  }`}
                                  title="Compare Reference Solution alongside Unit Tests"
                                >
                                  <span>Ref</span>
                                  <span className="text-slate-500">↔</span>
                                  <span>Tests</span>
                                </button>
                                <button
                                  type="button"
                                  onClick={() => {
                                    setTileLeftTab('tests')
                                    setTileRightTab('ref_tests')
                                  }}
                                  className={`px-2 py-0.5 text-xs font-medium rounded transition flex items-center gap-1 cursor-pointer shrink-0 whitespace-nowrap ${
                                    tileLeftTab === 'tests' && tileRightTab === 'ref_tests'
                                      ? 'bg-purple-600/40 text-purple-100 border border-purple-500/60 shadow-sm font-semibold'
                                      : 'text-slate-400 hover:text-slate-200'
                                  }`}
                                  title="Compare Unit Tests alongside Completed Reference Tests"
                                >
                                  <span>Tests</span>
                                  <span className="text-slate-500">↔</span>
                                  <span>Ref Tests</span>
                                </button>
                                <button
                                  type="button"
                                  onClick={() => {
                                    const prevLeft = tileLeftTab
                                    const prevRight = tileRightTab
                                    setTileLeftTab(prevRight)
                                    setTileRightTab(prevLeft)
                                  }}
                                  className="px-1.5 py-0.5 text-xs font-medium rounded text-slate-400 hover:text-slate-200 hover:bg-[#282828] transition cursor-pointer border-l border-ink-line/60 ml-0.5 shrink-0 whitespace-nowrap"
                                  title="Swap Left and Right panes"
                                >
                                  <span>⇄ Swap</span>
                                </button>
                              </div>
                            </div>
                          ) : (
                            <div className="inline-flex rounded-md bg-[#161616] p-0.5 border border-ink-line">
                              <button
                                type="button"
                                onClick={() => setActiveEditorTab('solution')}
                                className={`px-2 py-0.5 text-xs font-medium rounded transition flex items-center gap-1.5 cursor-pointer ${
                                  activeEditorTab === 'solution'
                                    ? 'bg-sky-600/30 text-sky-200 border border-sky-500/50 shadow-sm'
                                    : 'text-slate-400 hover:text-slate-200'
                                }`}
                                title="Edit implementation logic (Alt+T to toggle)"
                              >
                                <span>Sol</span>
                                <span>Solution</span>
                              </button>
                              <button
                                type="button"
                                onClick={() => setActiveEditorTab('tests')}
                                className={`px-2 py-0.5 text-xs font-medium rounded transition flex items-center gap-1.5 cursor-pointer ${
                                  activeEditorTab === 'tests'
                                    ? 'bg-indigo-600/30 text-indigo-200 border border-indigo-500/50 shadow-sm'
                                    : 'text-slate-400 hover:text-slate-200'
                                }`}
                                title="Write unit tests with assertions (Alt+T to toggle)"
                              >
                                <span>Tests</span>
                                <span>Unit Tests</span>
                                {testCode.trim() && (
                                  <span className="w-1.5 h-1.5 rounded-full bg-indigo-400"></span>
                                )}
                              </button>
                              <button
                                type="button"
                                onClick={() => setActiveEditorTab('reference')}
                                className={`px-2 py-0.5 text-xs font-medium rounded transition flex items-center gap-1.5 cursor-pointer ${
                                  activeEditorTab === 'reference'
                                    ? 'bg-emerald-600/30 text-emerald-200 border border-emerald-500/50 shadow-sm'
                                    : 'text-slate-400 hover:text-slate-200'
                                }`}
                                title="View reference model solution"
                              >
                                
                                <span>Reference</span>
                              </button>
                              {Boolean(cleanRefTestsCode.trim()) && (
                                <button
                                  type="button"
                                  onClick={() => setActiveEditorTab('ref_tests')}
                                  className={`px-2 py-0.5 text-xs font-medium rounded transition flex items-center gap-1.5 cursor-pointer ${
                                    activeEditorTab === 'ref_tests'
                                      ? 'bg-purple-600/30 text-purple-200 border border-purple-500/50 shadow-sm'
                                      : 'text-slate-400 hover:text-slate-200'
                                  }`}
                                  title="View completed reference test suite"
                                >
                                  <span>Tests</span>
                                  <span>Ref Tests</span>
                                </button>
                              )}
                              <button
                                type="button"
                                onClick={toggleTiledTabs}
                                className="px-2 py-0.5 text-xs font-medium rounded text-sky-400 hover:text-sky-200 hover:bg-sky-500/10 flex items-center gap-1.5 transition border-l border-ink-line/60 ml-0.5 cursor-pointer"
                                title="Tile reference solution and IDE side-by-side (Alt+S)"
                              >
                                <span>⧉</span>
                                <span>Tile</span>
                              </button>
                            </div>
                          )}

                          <select aria-label="Code language"
                            value={codeLanguage}
                            onChange={(e) => {
                              const nextLang = e.target.value
                              setCodeLanguage(nextLang)
                              storage.set('memorization.reviewCodeLanguage', nextLang)
                            }}
                            className="rounded border border-ink-line bg-[#282828] px-2 py-0.5 text-xs font-semibold text-slate-200 hover:border-slate-500 focus:outline-none focus:ring-1 focus:ring-sky-500 cursor-pointer shrink-0"
                          >
                            <option value="typescript">TypeScript</option>
                            <option value="javascript">JavaScript</option>
                            <option value="python">Python 3</option>
                          </select>

                          {!tiledTabs && activeEditorTab === 'solution' && (
                            <button
                              type="button"
                              onClick={() => handleToggleLogicGuard(!logicGuardEnabled)}
                              className={`flex items-center gap-1 rounded px-2 py-0.5 text-xs font-medium transition cursor-pointer shrink-0 whitespace-nowrap ${
                                logicGuardEnabled
                                  ? 'bg-rose-500/20 text-rose-300 border border-rose-500/40 hover:bg-rose-500/30'
                                  : 'text-slate-500 hover:text-slate-300 hover:bg-white/5 border border-white/10'
                              }`}
                              title={
                                logicGuardEnabled
                                  ? 'Logic Guard is ON: Warns if a flawed code line is written (Click to disable)'
                                  : 'Logic Guard is OFF: Click to enable real-time logic flaw detection'
                              }
                            >
                             <span>{logicGuardEnabled ? ' Guard: ON' : ' Guard: OFF'}</span>
                            </button>
                          )}

                          {!tiledTabs && activeEditorTab === 'solution' && item.starter_code && (
                            <button
                              type="button"
                              onClick={() => setAnswer(item.starter_code || '')}
                              className="text-slate-400 hover:text-slate-200 text-[0.6875rem] underline cursor-pointer"
                              title="Reset code editor to original starter template"
                            >
                              Reset solution
                            </button>
                          )}
                          {!tiledTabs && activeEditorTab === 'tests' && (
                            <div className="flex items-center gap-2">
                              {!testCode.trim() && Boolean(cleanRefTestsCode) && (
                                <button
                                  type="button"
                                  onClick={() => setTestCode(cleanRefTestsCode)}
                                  className="text-purple-300 hover:text-purple-200 text-[0.6875rem] underline cursor-pointer"
                                  title="Load completed reference tests into unit tests editor"
                                >
                                  Load reference tests
                                </button>
                              )}
                              <button
                                type="button"
                                onClick={() => setTestCode(buildStarterTestCode(item) || cleanRefTestsCode)}
                                className="text-slate-400 hover:text-slate-200 text-[0.6875rem] underline cursor-pointer"
                                title="Reset unit tests to starter assertions"
                              >
                                Reset tests
                              </button>
                            </div>
                          )}
                          {!tiledTabs && activeEditorTab === 'reference' && (
                            <div className="flex items-center gap-2">
                              {Boolean(cleanRefCode) && (revealed || singleRefViewMode === 'hint') && (
                                <div className="inline-flex rounded-md bg-[#161616] p-0.5 border border-ink-line text-[0.6875rem] shrink-0">
                                  <button
                                    type="button"
                                    onClick={() => {
                                      setSingleRefViewMode('ide')
                                      storage.set('memorization.refViewMode', 'ide')
                                    }}
                                    className={`px-2 py-0.5 rounded transition cursor-pointer ${
                                      singleRefViewMode === 'ide'
                                        ? 'bg-sky-600/30 text-sky-200 border border-sky-500/50 font-medium'
                                        : 'text-slate-400 hover:text-slate-200'
                                    }`}
                                    title="IDE syntax-highlighted code format"
                                  >
                                    IDE
                                  </button>
                                  {revealed && Boolean(answer.trim()) && (
                                    <button
                                      type="button"
                                      onClick={() => {
                                        setSingleRefViewMode('diff')
                                        storage.set('memorization.refViewMode', 'diff')
                                      }}
                                      className={`px-2 py-0.5 rounded transition flex items-center gap-1 cursor-pointer ${
                                        singleRefViewMode === 'diff'
                                          ? 'bg-amber-600/30 text-amber-200 border border-amber-500/50 font-medium'
                                        : 'text-slate-400 hover:text-slate-200'
                                      }`}
                                      title="Token-by-token answer comparison diff against your Solution"
                                    >
                                      <span>Diff</span>
                                      {singleRefDiff.stats && singleRefDiff.stats.missingCount > 0 && (
                                        <span className="inline-block w-1.5 h-1.5 rounded-full bg-amber-400" />
                                      )}
                                    </button>
                                  )}
                                  <button
                                    type="button"
                                    onClick={() => {
                                      setSingleRefViewMode('hint')
                                      storage.set('memorization.refViewMode', 'hint')
                                    }}
                                    className={`px-2 py-0.5 rounded transition flex items-center gap-1 cursor-pointer ${
                                      singleRefViewMode === 'hint'
                                        ? 'bg-amber-500/30 text-amber-300 border border-amber-500/50 font-medium'
                                        : 'text-slate-400 hover:text-slate-200'
                                    }`}
                                    title="Hint-only mode: reveals only the current incomplete line"
                                  >
                                   <span> Hint</span>
                                  </button>
                                </div>
                              )}
                              {Boolean(cleanRefCode) && singleRefViewMode === 'ide' && singleTargetRefLines.size > 0 && (
                                <div className="flex items-center gap-1.5 shrink-0 ml-1">
                                  <button
                                    type="button"
                                    onClick={handleToggleFocusTargetCode}
                                    className={`px-2 py-0.5 rounded transition flex items-center gap-1 cursor-pointer text-xs ${
                                      focusTargetCode
                                        ? 'bg-emerald-600/30 text-emerald-200 border border-emerald-500/50 font-medium shadow-sm'
                                        : 'text-slate-400 hover:text-slate-200 border border-transparent'
                                    }`}
                                    title={
                                      focusTargetCode
                                        ? 'Focus Target Code active: boilerplate starter code is dimmed. Click to show full brightness.'
                                        : 'Click to focus target code (dims boilerplate starter code)'
                                    }
                                  >
                                   <span> Target ({formatTargetLineSummary(singleTargetRefLines)})</span>
                                  </button>
                                  <HighlightColorPicker
                                    color={targetHighlightColor}
                                    onChange={handleHighlightColorChange}
                                  />
                                </div>
                              )}
                              {revealed && (
                                <button
                                  type="button"
                                  onClick={() => handleHideSolution('hide')}
                                  className="px-2 py-0.5 rounded bg-rose-500/10 hover:bg-rose-500/20 text-rose-300 border border-rose-500/30 text-[0.6875rem] font-medium transition cursor-pointer flex items-center gap-1 shrink-0"
                                  title="Hide solution and return to active practice"
                                >
                                 <span> Hide</span>
                                </button>
                              )}
                              <button
                                type="button"
                                onClick={() => void handleCopyReferenceCode(cleanRefCode)}
                                disabled={!cleanRefCode}
                                className="text-slate-400 hover:text-slate-200 text-[0.6875rem] flex items-center gap-1 disabled:opacity-30 cursor-pointer"
                                title="Copy reference code to clipboard"
                              >
                                <span>{copiedRef ? 'Copied' : 'Copy ref'}</span>
                              </button>
                            </div>
                          )}
                          {!tiledTabs && activeEditorTab === 'ref_tests' && (
                            <div className="flex items-center gap-2">
                              {Boolean(cleanRefTestsCode) && (
                                <button
                                  type="button"
                                  onClick={() => {
                                    setTestCode(cleanRefTestsCode)
                                    setActiveEditorTab('tests')
                                  }}
                                  className="text-purple-300 hover:text-purple-200 text-[0.6875rem] underline cursor-pointer"
                                  title="Load reference tests into editable Unit Tests editor"
                                >
                                  Load to tests
                                </button>
                              )}
                              <button
                                type="button"
                                onClick={() => void handleCopyReferenceTests(cleanRefTestsCode)}
                                disabled={!cleanRefTestsCode}
                                className="text-slate-400 hover:text-slate-200 text-[0.6875rem] flex items-center gap-1 disabled:opacity-30 cursor-pointer"
                                title="Copy completed reference tests to clipboard"
                              >
                                <span>{copiedRefTests ? 'Copied' : 'Copy ref tests'}</span>
                              </button>
                            </div>
                          )}
                        </div>
                      </div>

                      {/* Body: Tiled Side-by-Side vs Single Tab */}
                      {tiledTabs ? (
                        <div className="grid grid-cols-1 lg:grid-cols-2 divide-y lg:divide-y-0 lg:divide-x divide-ink-line bg-[#161616]">
                          <TiledEditorPane
                            paneId="left"
                            currentTab={tileLeftTab}
                            onTabChange={setTileLeftTab}
                            answer={answer}
                            onAnswerChange={setAnswer}
                            testCode={testCode}
                            onTestCodeChange={setTestCode}
                            cleanRefCode={cleanRefCode}
                            starterTestsCode={starterTestsCode}
                            cleanRefTestsCode={cleanRefTestsCode}
                            codeLanguage={codeLanguage}
                            revealed={revealed}
                            onReveal={() => void reveal()}
                            item={item}
                            copiedRef={copiedRef}
                            onCopyRef={handleCopyReferenceCode}
                            copiedStarterTests={copiedStarterTests}
                            onCopyStarterTests={handleCopyStarterTests}
                            copiedRefTests={copiedRefTests}
                            onCopyRefTests={handleCopyReferenceTests}
                            height="340px"
                            onRun={() => void handleRunReviewCode()}
                            onSubmit={() => void (llmEnabled && answer.trim() ? grade() : reveal())}
                            activeLineHint={activeLineHint}
                            lineHintLoading={lineHintLoading}
                            onRequestLineHint={handleRequestLineHint}
                            onDismissLineHint={() => setActiveLineHint(null)}
                            onCursorChange={(l) => {
                              if (tileLeftTab === 'solution') setEditorCursorLine(l)
                            }}
                            onGradeSolution={() => void (answer.trim() ? grade() : reveal())}
                            grading={grading}
                            learnMode={learnMode}
                            overlookedPhrases={overlookedTerms}
                            matchedPhrases={matchedTerms}
                            logicGuardEnabled={logicGuardEnabled}
                            onLogicGuardToggle={handleToggleLogicGuard}
                            onHide={() => handleHideSolution('hide')}
                            activeModel={activeModel}
                            onActiveModelChange={(m) => void handleSwitchModel(m)}
                            executionSummary={executionSummaryStr}
                            sharedQaHistory={sharedQaHistory}
                            onSharedQaHistoryChange={setSharedQaHistory}
                          />
                          <TiledEditorPane
                            paneId="right"
                            currentTab={tileRightTab}
                            onTabChange={setTileRightTab}
                            answer={answer}
                            onAnswerChange={setAnswer}
                            testCode={testCode}
                            onTestCodeChange={setTestCode}
                            cleanRefCode={cleanRefCode}
                            starterTestsCode={starterTestsCode}
                            cleanRefTestsCode={cleanRefTestsCode}
                            codeLanguage={codeLanguage}
                            revealed={revealed}
                            onReveal={() => void reveal()}
                            item={item}
                            copiedRef={copiedRef}
                            onCopyRef={handleCopyReferenceCode}
                            copiedStarterTests={copiedStarterTests}
                            onCopyStarterTests={handleCopyStarterTests}
                            copiedRefTests={copiedRefTests}
                            onCopyRefTests={handleCopyReferenceTests}
                            height="340px"
                            onRun={() => void handleRunReviewCode()}
                            onSubmit={() => void (llmEnabled && answer.trim() ? grade() : reveal())}
                            activeLineHint={activeLineHint}
                            lineHintLoading={lineHintLoading}
                            onRequestLineHint={handleRequestLineHint}
                            onDismissLineHint={() => setActiveLineHint(null)}
                            onCursorChange={(l) => {
                              if (tileRightTab === 'solution') setEditorCursorLine(l)
                            }}
                            onGradeSolution={() => void (answer.trim() ? grade() : reveal())}
                            grading={grading}
                            learnMode={learnMode}
                            overlookedPhrases={overlookedTerms}
                            matchedPhrases={matchedTerms}
                            logicGuardEnabled={logicGuardEnabled}
                            onLogicGuardToggle={handleToggleLogicGuard}
                            onHide={() => handleHideSolution('hide')}
                            activeModel={activeModel}
                            onActiveModelChange={(m) => void handleSwitchModel(m)}
                            executionSummary={executionSummaryStr}
                            sharedQaHistory={sharedQaHistory}
                            onSharedQaHistoryChange={setSharedQaHistory}
                          />
                        </div>
                      ) : (
                        /* Single Tab View */
                        activeEditorTab === 'reference' ? (
                          revealed || singleRefViewMode === 'hint' ? (
                            <div className="flex flex-col">
                              {singleRefViewMode === 'hint' && (
                                <div className="px-3 py-1 bg-amber-950/40 border-b border-amber-500/30 flex items-center justify-between text-xs text-amber-200 shrink-0">
                                  <div className="flex items-center gap-2">
                                   <span className="font-semibold text-amber-300"> Hint Mode:</span>
                                    <span>
                                      Only line {findIncompleteLineNumber(answer, cleanRefCode)} is visible
                                    </span>
                                  </div>
                                  {revealed && (
                                    <button
                                      type="button"
                                      onClick={() => handleHideSolution('hide')}
                                      className="px-2 py-0.5 rounded bg-rose-500/20 hover:bg-rose-500/30 text-rose-300 border border-rose-500/40 font-semibold cursor-pointer"
                                      title="Hide the solution and continue practicing"
                                    >
                                       Unreveal & Practice
                                    </button>
                                  )}
                                </div>
                              )}
                              <CodeEditor
                                code={cleanRefCode}
                                onChange={() => {}}
                                language={codeLanguage}
                                readOnly={true}
                                height={singleRefViewMode === 'hint' ? '288px' : '320px'}
                                placeholder="// Reference solution"
                                context={item?.front || item?.deck_name}
                                deckId={item?.kind === 'card' ? item.deck_or_source_id : null}
                                cardId={item?.id ?? null}
                                userCode={answer}
                                userTestCode={testCode}
                                executionSummary={executionSummaryStr}
                                revealed={revealed}
                                sharedQaHistory={sharedQaHistory}
                                onSharedQaHistoryChange={setSharedQaHistory}
                                activeModel={activeModel}
                                onActiveModelChange={(m) => void handleSwitchModel(m)}
                                diffSegments={singleRefViewMode === 'diff' ? singleRefDiff.refSegments : null}
                                diffStats={singleRefViewMode === 'diff' ? singleRefDiff.stats : null}
                                hintOnly={singleRefViewMode === 'hint'}
                                hintOnlyLine={findIncompleteLineNumber(answer, cleanRefCode)}
                                targetLineNumbers={singleTargetRefLines}
                                focusTargetCode={focusTargetCode}
                                targetHighlightColor={targetHighlightColor}
                                initialScrollLine={firstSingleTargetRefLine ?? undefined}
                              />
                            </div>
                          ) : (
                            <div className="flex flex-col items-center justify-center p-6 text-center bg-[#181818] text-slate-400 space-y-2 h-[320px]">
                              <div className="w-10 h-10 rounded-2xl bg-sky-500/10 border border-sky-500/20 flex items-center justify-center text-sky-400 shadow-inner">
                                <svg className="w-4 h-4 text-sky-400" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><rect x="3" y="11" width="18" height="11" rx="2" ry="2"/></svg>
                              </div>
                              <div className="space-y-0.5">
                                <h4 className="text-xs font-semibold text-slate-200">Reference Solution</h4>
                                <p className="text-[0.6875rem] text-slate-400 max-w-xs leading-relaxed">
                                   Hidden until revealed.
                                </p>
                              </div>
                              <div className="flex items-center gap-2 mt-1">
                                <button
                                  type="button"
                                  onClick={() => void reveal()}
                                  className="btn btn-secondary text-xs flex items-center gap-1.5 px-3 py-1 cursor-pointer"
                                >
                                  <span>Reveal Solution</span>
                                </button>
                                <button
                                  type="button"
                                  onClick={() => {
                                    setSingleRefViewMode('hint')
                                    storage.set('memorization.refViewMode', 'hint')
                                  }}
                                  className="px-3 py-1 rounded border border-amber-500/40 bg-amber-500/10 hover:bg-amber-500/20 text-amber-300 text-xs font-medium transition cursor-pointer flex items-center gap-1"
                                  title="Peek only the next line of code without revealing full answer"
                                >
                                 <span> Line Hint</span>
                                </button>
                              </div>
                            </div>
                          )
                        ) : activeEditorTab === 'ref_tests' ? (
                          revealed || learnMode ? (
                            <CodeEditor
                              code={cleanRefTestsCode}
                              onChange={() => {}}
                              language={codeLanguage}
                              readOnly={true}
                              height="320px"
                              placeholder="// Completed reference test suite"
                              context={item?.front || item?.deck_name}
                              deckId={item?.kind === 'card' ? item.deck_or_source_id : null}
                              cardId={item?.id ?? null}
                              userCode={answer}
                              userTestCode={testCode}
                              executionSummary={executionSummaryStr}
                              revealed={revealed}
                              sharedQaHistory={sharedQaHistory}
                              onSharedQaHistoryChange={setSharedQaHistory}
                              activeModel={activeModel}
                              onActiveModelChange={(m) => void handleSwitchModel(m)}
                            />
                          ) : (
                            <div className="flex flex-col items-center justify-center p-6 text-center bg-[#181818] text-slate-400 space-y-2 h-[320px]">
                              <div className="w-10 h-10 rounded-2xl bg-purple-500/10 border border-purple-500/20 flex items-center justify-center text-purple-400 shadow-inner">
                                <svg className="w-4 h-4 text-purple-400" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><rect x="3" y="11" width="18" height="11" rx="2" ry="2"/><path d="M7 11V7a5 5 0 0 1 10 0v4"/></svg>
                              </div>
                              <div className="space-y-0.5">
                                <h4 className="text-xs font-semibold text-slate-200">Reference Tests</h4>
                                <p className="text-[0.6875rem] text-slate-400 max-w-xs leading-relaxed">
                                   Hidden until revealed.
                                </p>
                              </div>
                              <div className="flex items-center gap-2 mt-1">
                                <button
                                  type="button"
                                  onClick={() => void reveal()}
                                  className="btn btn-secondary text-xs flex items-center gap-1.5 px-3 py-1 cursor-pointer"
                                >
                                  <span>Reveal Tests</span>
                                </button>
                              </div>
                            </div>
                          )
                        ) : (
                          <CodeEditor
                            code={activeEditorTab === 'solution' ? answer : testCode}
                            onChange={activeEditorTab === 'solution' ? setAnswer : setTestCode}
                            language={codeLanguage}
                            height="320px"
                            onRun={() => void handleRunReviewCode()}
                            onSubmit={() => void (llmEnabled && answer.trim() ? grade() : reveal())}
                            activeModel={activeModel}
                            onActiveModelChange={(m) => void handleSwitchModel(m)}
                            activeLineHint={activeEditorTab === 'solution' ? activeLineHint : null}
                            lineHintLoading={activeEditorTab === 'solution' ? lineHintLoading : false}
                            onRequestLineHint={activeEditorTab === 'solution' ? handleRequestLineHint : undefined}
                            onDismissLineHint={() => setActiveLineHint(null)}
                            onCursorChange={(l) => setEditorCursorLine(l)}
                            onGradeSolution={activeEditorTab === 'solution' ? () => void (answer.trim() ? grade() : reveal()) : undefined}
                            grading={activeEditorTab === 'solution' ? grading : false}
                            context={item?.front || item?.deck_name}
                            deckId={item?.kind === 'card' ? item.deck_or_source_id : null}
                            cardId={item?.id ?? null}
                            userCode={answer}
                            userTestCode={testCode}
                            executionSummary={executionSummaryStr}
                            revealed={revealed}
                            sharedQaHistory={sharedQaHistory}
                            onSharedQaHistoryChange={setSharedQaHistory}
                            cleanRefCode={activeEditorTab === 'solution' ? cleanRefCode : undefined}
                            logicGuardEnabled={logicGuardEnabled}
                            onLogicGuardToggle={handleToggleLogicGuard}
                          />
                        )
                      )}
                    </div>
                    <CodeTestConsole
                      testCases={item.test_cases || []}
                      runResult={codeRunResult}
                      running={codeRunning}
                      onRun={handleRunReviewCode}
                      onSubmit={() => void (llmEnabled && answer.trim() ? grade() : reveal())}
                      submitting={grading}
                    />
                  </div>
                ) : (
                  <>
                    {skipReviewRecording && (
                      <div className="mb-2 flex items-center justify-between rounded-lg border border-amber-500/40 bg-amber-500/10 px-3 py-2 text-xs text-amber-200 shadow-sm animate-fadeIn">
                        <div className="flex items-center gap-2 min-w-0">
                          <span className="font-bold uppercase tracking-wider text-[0.6875rem] bg-amber-500/20 px-1.5 py-0.5 rounded border border-amber-500/30 shrink-0">
                             Skip Grading Active
                          </span>
                          <span className="truncate">
                            Type your answer and grade it below. Your grade will not be recorded as a card review.
                          </span>
                        </div>
                        <button
                          type="button"
                          className="text-[0.6875rem] underline text-amber-400 hover:text-amber-100 ml-2 shrink-0 cursor-pointer"
                          onClick={() => setSkipReviewRecording(false)}
                          title="Return to standard review mode"
                        >
                          Cancel
                        </button>
                      </div>
                    )}
                    <textarea
                      id="answer"
                      ref={inputRef}
                      className="input min-h-[7rem] resize-y"
                      value={answer}
                      onChange={(e) => setAnswer(e.target.value)}
                      placeholder="Type your answer…"
                    />
                  </>
                )}
                <div className="mt-3 flex flex-wrap items-center gap-2">
                  {llmEnabled && (
                    <DiscreteModelSelector
                      activeModel={activeModel}
                      installedModels={installedModels}
                      grading={grading}
                      hasAnswer={Boolean(answer.trim())}
                      onSelectModel={(m) => void handleSwitchModel(m)}
                      onGradeWithModel={(m) => void handleGradeWithModel(m)}
                    />
                  )}
                  {llmEnabled ? (
                    <button
                      className={`btn ${skipReviewRecording ? 'btn-secondary border-amber-500/50 text-amber-200' : 'btn-primary'}`}
                      onClick={() => void grade()}
                      disabled={grading || !answer.trim()}
                      title={skipReviewRecording ? 'Grade answer without recording a review' : 'Submit answer and prepare to record review'}
                    >
                      {grading ? 'Grading…' : skipReviewRecording ? 'Grade answer (Unrecorded)' : 'Submit answer'}
                    </button>
                  ) : null}
                  <button
                    type="button"
                    className={`btn ${skipReviewRecording ? 'border-amber-500/60 text-amber-300 bg-amber-500/15 font-semibold' : ''}`}
                    onClick={handleSkipGrading}
                    disabled={grading}
                    title={skipReviewRecording ? 'Advance to next card without recording review' : 'Type and grade an answer without recording the grade as a card review'}
                  >
                    <span>{skipReviewRecording ? 'Skip card (Unrecorded)' : 'Skip grading'}</span>
                  </button>
                  <button className="btn" onClick={reveal} disabled={grading} title="Show reference answer immediately">
                    Show answer
                  </button>
                  <button
                    type="button"
                    onClick={() => void handleSaveForLater()}
                    className="btn border-indigo-500/40 text-indigo-300 hover:bg-indigo-500/15 flex items-center gap-1.5"
                    title="Save your work and advance to next card (Alt+L)"
                  >
                    
                    <span>Save for Later</span>
                  </button>
                  {llmEnabled && !guideOpen && (
                    <button className="btn" onClick={openGuide}>
                      Stuck? Ask your Guide
                    </button>
                  )}
                  {item.active_weaknesses && item.active_weaknesses.length > 0 && (
                    <button
                      type="button"
                      className="btn border-amber-500/40 text-amber-300 hover:bg-amber-500/15"
                      onClick={() => {
                        if (!weaknessHint) void handleRequestWeaknessHint()
                        else setShowWeaknessHint((v) => !v)
                      }}
                    >
                      {showWeaknessHint ? 'Hide Past Mistake Hint' : 'Past Mistake Hint'}
                    </button>
                  )}
                  <span className="text-xs text-slate-600">Cmd/Ctrl + Enter</span>
                </div>

                {/* Longitudinal Weakness Hint Box */}
                {showWeaknessHint && (
                  <div className="mt-3 rounded-lg border border-amber-500/40 bg-amber-500/10 p-3 space-y-1.5 text-xs text-amber-200">
                    <div className="flex items-center justify-between font-semibold">
                      <span className="flex items-center gap-1.5">
                        
                        <span>Past Mistake Diagnostic Hint:</span>
                      </span>
                      <button
                        type="button"
                        className="text-[0.6875rem] underline text-amber-400 hover:text-amber-200"
                        onClick={() => setShowWeaknessHint(false)}
                      >
                        hide
                      </button>
                    </div>
                    {weaknessHintLoading ? (
                      <p className="text-amber-300/70 italic">Consulting past weakness memory…</p>
                    ) : weaknessHintError ? (
                      <p className="text-rose-300 leading-relaxed">{weaknessHintError}</p>
                    ) : weaknessHint ? (
                      <p className="text-amber-100 leading-relaxed">{weaknessHint}</p>
                    ) : null}
                  </div>
                )}
                {!llmEnabled && (
                  <p className="mt-3 text-xs text-slate-600">
                    LLM grading is off. Turn it on in{' '}
                    <button className="underline hover:text-slate-400" onClick={() => navigate('/settings')}>
                      Settings
                    </button>{' '}
                    by giving consent.
                  </p>
                )}
                {guideOpen && (
                  <SocraticGuide
                    history={guideHistory}
                    input={guideInput}
                    onInputChange={setGuideInput}
                    loading={guideLoading}
                    degraded={guideDegraded}
                    onTrack={guideOnTrack}
                    onSend={() => void askGuide(guideInput)}
                    onClose={() => setGuideOpen(false)}
                    onCommit={() => {
                      setGuideOpen(false)
                      inputRef.current?.focus()
                    }}
                    onRetry={() => void askGuide(guideInput || '')}
                  />
                )}
              </div>
            )}

            {revealed && (
              <div className="mt-6 space-y-4">
                <CopyLearningSummaryButton
                  item={item}
                  answer={answer}
                  testCode={testCode}
                  result={result}
                  codeLanguage={codeLanguage}
                  codeRunResult={codeRunResult}
                  variant="prominent"
                  className="w-full"
                />
                {!isCodeCard && (
                  <AnswerComparison
                    userAnswer={answer}
                    userTestCode={testCode}
                    referenceAnswer={result?.reference_answer || item.back || ''}
                    isCodeCard={isCodeCard}
                    codeLanguage={codeLanguage}
                    timeComplexity={item.time_complexity}
                    overlookedPhrases={overlookedTerms}
                    matchedPhrases={matchedTerms}
                  />
                )}

                {result?.latency_note && (
                  <p className="text-xs text-slate-600" title="Informational only — never affects the grade">
                    {formatLatencyNote(result.latency_note)}
                  </p>
                )}

                {result && !result.degraded_to_manual && (
                  <OverlookedAnalysisCard result={result} />
                )}

                <ReferenceReadings
                  references={item.references}
                  overlookedPhrases={overlookedTerms}
                  matchedPhrases={matchedTerms}
                />

                {result && !result.degraded_to_manual && (
                  <GradeReasoning
                    result={result}
                    installedModels={installedModels}
                    activeModel={activeModel}
                    grading={grading}
                    hasAnswer={Boolean(answer.trim())}
                    onSelectModel={(m) => void handleSwitchModel(m)}
                    onGradeWithModel={(m) => void handleGradeWithModel(m)}
                  />
                )}

                {result?.vram_constrained && !vramDismissed ? (
                  <VramConstraintPrompt
                    result={result}
                    loading={grading}
                    onSwitchModel={(model) => void grade(model, true)}
                    onRetry={() => void grade(result.failed_model || undefined)}
                    onGradeManually={() => setVramDismissed(true)}
                  />
                ) : result?.degraded_to_manual && result.degraded_reason !== 'consent_not_given' ? (
                  <div className="rounded-lg border border-amber-500/40 bg-amber-500/10 px-4 py-3 text-sm text-amber-200">
                    Automatic grading was unavailable ({result.degraded_reason}). Grade it yourself —
                    your scheduling is unaffected.
                  </div>
                ) : null}

                {skipReviewRecording ? (
                  <div className="rounded-xl border border-amber-500/40 bg-amber-500/10 p-4 space-y-3">
                    <div className="flex items-center justify-between">
                      <span className="text-xs font-bold uppercase tracking-wider text-amber-300 flex items-center gap-1.5">
                         Unrecorded Practice Mode
                      </span>
                      <span className="chip border-amber-500/30 text-amber-300 bg-amber-500/20 text-[0.625rem]">
                        Review Not Recorded
                      </span>
                    </div>
                    <p className="text-xs text-slate-300 leading-relaxed">
                      You typed and graded your answer without recording a card review. Your review queue and spaced repetition schedule are unaffected.
                    </p>
                    <div className="flex flex-wrap items-center gap-2 pt-1">
                      <button
                        type="button"
                        className="btn btn-primary text-xs px-4 py-2 font-bold shadow-sm cursor-pointer"
                        onClick={() => void advanceWithoutReview()}
                        title="Advance to next card (Space / Enter)"
                      >
                        <span>Next Card (No review recorded) →</span>
                      </button>
                      <button
                        type="button"
                        className="btn text-xs px-3 py-2 cursor-pointer"
                        onClick={() => {
                          setRevealed(false)
                        }}
                        title="Edit your answer and grade again"
                      >
                        <span>Edit &amp; Re-grade</span>
                      </button>
                      <button
                        type="button"
                        className="btn text-xs px-3 py-2 bg-amber-500/20 hover:bg-amber-500/30 text-amber-200 border border-amber-500/40 cursor-pointer"
                        onClick={handleRetryWithoutRecording}
                        title="Clear input and retry card from scratch (unrecorded)"
                      >
                       <span> Fresh Retry</span>
                      </button>
                      <button
                        type="button"
                        className="btn text-xs px-2.5 py-1 text-slate-400 hover:text-slate-200 cursor-pointer"
                        onClick={() => {
                          setSkipReviewRecording(false)
                        }}
                        title="Enable standard grade buttons to record this review"
                      >
                        <span>Record this review anyway</span>
                      </button>
                    </div>
                  </div>
                ) : (
                  <div className="review-grade-bar">
                    <div className="mb-2 flex items-center justify-between flex-wrap gap-2">
                      <p className="label mb-0">
                        {result && !result.degraded_to_manual
                          ? result.needs_confirmation
                            ? 'Confirm or correct the grade'
                            : 'Accept the suggestion, or override'
                          : 'How well did you recall it?'}
                      </p>
                      <div className="flex items-center gap-2">
                        {isCodeCard && (
                          <>
                            <button
                              type="button"
                              onClick={() => handleHideSolution('hint')}
                              className="text-[0.6875rem] text-amber-300 hover:text-amber-100 flex items-center gap-1 cursor-pointer bg-amber-500/15 hover:bg-amber-500/25 px-2.5 py-0.5 rounded border border-amber-500/40 transition font-medium shadow-sm"
                              title="Hide full solution, enable line hints, and return to practice mode (Alt+U)"
                            >
                             <span> Use Line Hints &amp; Keep Practicing</span>
                            </button>
                            <button
                              type="button"
                              onClick={() => handleHideSolution('hide')}
                              className="text-[0.6875rem] text-slate-300 hover:text-white flex items-center gap-1 cursor-pointer bg-white/5 hover:bg-white/10 px-2 py-0.5 rounded border border-white/15 transition font-medium"
                              title="Lock reference solution and return to practice mode"
                            >
                             <span> Hide Solution</span>
                            </button>
                          </>
                        )}
                        <button
                          type="button"
                          className="text-[0.6875rem] text-slate-500 hover:text-amber-300 underline cursor-pointer"
                          onClick={() => setSkipReviewRecording(true)}
                          title="Don't record this card review"
                        >
                          Skip recording this review
                        </button>
                      </div>
                    </div>
                    <div className="flex flex-wrap gap-2">
                      {GRADES.map((g, i) => {
                        const suggested =
                          result && !result.degraded_to_manual && result.suggested_grade === g
                        return (
                          <button
                            key={g}
                            onClick={() => confirm(g, { retryImmediately: retryAfterRating })}
                            disabled={confirming}
                            className={`btn ${GRADE_STYLE[g]} ${
                              suggested ? 'ring-1 ring-inset ring-current' : ''
                            }`}
                            title={retryAfterRating ? `Record as ${g.toUpperCase()} and retry card immediately` : `Record as ${g.toUpperCase()} and advance to next card`}
                          >
                            {retryAfterRating && <span className="text-xs" aria-hidden="true">↻</span>}
                            <span className="capitalize">{g}</span>
                            <span className="text-xs opacity-50">{GRADE_BAND[g]}</span>
                            <span className="text-xs opacity-50">{i + 1}</span>
                            {suggested && <span className="text-xs opacity-70">· suggested</span>}
                            {persistActive && (
                              <span
                                className={`text-[0.625rem] ml-1 px-1.5 py-0.5 rounded font-semibold ${
                                  g === 'easy'
                                    ? 'bg-emerald-500/30 text-emerald-200 border border-emerald-500/50'
                                    : 'bg-amber-500/20 text-amber-200 border border-amber-500/40'
                                }`}
                              >
                                {g === 'easy' ? 'Grasps' : 'Re-queues'}
                              </span>
                            )}
                          </button>
                        )
                      })}
                    </div>

                    {/* Immediate Retry Action Bar */}
                    {renderRetryActionBar()}
                  </div>
                )}
              </div>
            )}
              </div>
            </div>

            {/* Right Margin: Concordance, Lexicon & Persistent Card Memory */}
            <aside className="w-full xl:w-80 2xl:w-96 shrink-0 xl:sticky xl:top-16">
              <MarginLexiconPanel
                cardId={item.id}
                deckId={item.kind === 'card' ? item.deck_or_source_id : null}
                deckName={item.deck_name}
                thematicNature={item.card_thematic_nature || item.deck_thematic_nature}
                cardFront={item.front}
                cardBack={item.back}
                initialGlosses={item.lexicon_glosses}
                onGlossesUpdated={(updatedGlosses) => applyGlossesToCard(item.id, updatedGlosses)}
                codeLanguage={codeLanguage}
              />
            </aside>
          </div>
        )}

        <ErrorNote error={error} />
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <SessionTimer />
      {stuckAlert && !breakUntil && (
        <StuckBanner
          alert={stuckAlert}
          onBreak={() => {
            setBreakUntil(Date.now() + stuckAlert.suggested_break_minutes * 60_000)
            setStuckAlert(null)
          }}
          onDismiss={() => setStuckAlert(null)}
        />
      )}
      {breakUntil ? (
        <BreakOverlay until={breakUntil} onDone={() => setBreakUntil(null)} />
      ) : (
        renderBody()
      )}

      {blitzSummaryOpen && blitzStats && (
        <BlitzScorecardModal
          stats={blitzStats}
          durationSec={blitzDurationSec}
          onRestart={(sec) => startBlitz(sec)}
          onClose={() => setBlitzSummaryOpen(false)}
        />
      )}

      <DeckCardsViewer
        isOpen={deckViewerOpen}
        onClose={() => {
          setDeckViewerOpen(false)
          setLastStudiedCardId(null)
          setLastStudiedDeckId(null)
        }}
        deckId={lastStudiedDeckId || item?.deck_or_source_id || deckParam || null}
        deckName={item?.deck_name || persistDeckName || null}
        currentCardId={lastStudiedCardId || item?.id || null}
        onSelectCard={handleJumpToCard}
        codeLanguage={codeLanguage}
        allDecks={allDecks}
      />

      <SavedCardsDrawer
        isOpen={savedDrawerOpen}
        onClose={() => setSavedDrawerOpen(false)}
        onResumeCard={handleResumeSavedDraft}
        currentCardId={item?.id || null}
      />
    </div>
  )
}

/** Stuck-state detector (§ Stuck-state detector): the backend flags an
 *  accuracy slump or a latency spike on `confirm`; this is the nudge — take
 *  it as a prompt to break or work, never a silent behavior change, matching
 *  how every other automatic suggestion in this app stays a proposal. */
function StuckBanner({
  alert,
  onBreak,
  onDismiss,
}: {
  alert: StuckAlert
  onBreak: () => void
  onDismiss: () => void
}) {
  return (
    <div className="rounded-lg border border-amber-500/40 bg-amber-500/10 px-4 py-3 text-sm text-amber-200">
      <p>{alert.message}</p>
      <div className="mt-2 flex flex-wrap gap-2">
        <button className="btn px-2.5 py-1 text-xs" onClick={onBreak}>
          Take a {alert.suggested_break_minutes}-minute break
        </button>
        <button className="btn px-2.5 py-1 text-xs" onClick={onDismiss}>
          Keep going
        </button>
      </div>
    </div>
  )
}

/** Stands in for the next card until the break ends — the study clock and
 *  bank keep running underneath (SessionTimer is unaffected), only the next
 *  question is held back. */
function BreakOverlay({ until, onDone }: { until: number; onDone: () => void }) {
  const [now, setNow] = useState(() => Date.now())

  useEffect(() => {
    const id = window.setInterval(() => setNow(Date.now()), 1000)
    return () => window.clearInterval(id)
  }, [])

  useEffect(() => {
    if (now >= until) onDone()
  }, [now, until, onDone])

  return (
    <div className="card space-y-3 text-center">
      <p className="text-lg text-slate-100">Taking a break</p>
      <p className="font-mono text-3xl tabular-nums text-slate-100">
        {formatClock(Math.max(0, until - now))}
      </p>
      <button className="btn" onClick={onDone}>
        Skip break, keep going
      </button>
    </div>
  )
}

/** Socratic AI Guide: one diagnostic question at a time, never the answer.
 *  Stateless on the server — the whole transcript rides along with each
 *  turn, so there's nothing here to persist across a card change either. */
function SocraticGuide({
  history,
  input,
  onInputChange,
  loading,
  degraded,
  onTrack,
  onSend,
  onClose,
  onCommit,
  onRetry,
}: {
  history: SocraticTurn[]
  input: string
  onInputChange: (v: string) => void
  loading: boolean
  degraded: string | null
  onTrack: boolean
  onSend: () => void
  onClose: () => void
  onCommit: () => void
  onRetry?: () => void
}) {
  return (
    <div className="mt-3 space-y-2 rounded-lg border border-ink-line bg-ink p-3">
      <div className="flex items-center justify-between">
        <span className="text-xs font-medium text-slate-400">Guide</span>
        <button className="text-xs text-slate-600 underline hover:text-slate-400" onClick={onClose}>
          close
        </button>
      </div>

      {degraded ? (
        <div className="space-y-2">
          <p className="text-xs text-amber-300 leading-relaxed">
            Guide unavailable ({degraded}).
          </p>
          {onRetry && (
            <div className="pt-1">
              <button
                type="button"
                className="btn text-xs px-2.5 py-1 border-sky-500/40 text-sky-300 hover:bg-sky-500/10"
                onClick={onRetry}
                disabled={loading}
              >
                {loading ? 'Retrying…' : '↻ Retry Guide'}
              </button>
            </div>
          )}
        </div>
      ) : (
        <>
          {history.length === 0 && loading && <p className="text-xs text-slate-600">Thinking…</p>}
          <div className="space-y-2">
            {history.map((turn, i) => (
              <p
                key={i}
                className={`text-xs leading-relaxed ${
                  turn.role === 'guide' ? 'text-sky-300' : 'text-slate-300'
                }`}
              >
                <span className="font-medium">{turn.role === 'guide' ? 'Guide: ' : 'You: '}</span>
                {turn.text}
              </p>
            ))}
            {history.length > 0 && loading && <p className="text-xs text-slate-600">Thinking…</p>}
          </div>
          {onTrack && !loading && (
            <div className="flex flex-wrap items-center gap-2 rounded border border-emerald-500/40 bg-emerald-500/10 px-2 py-1.5">
              <span className="text-xs text-emerald-300">You've got it — write it down.</span>
              <button className="btn px-2 py-0.5 text-xs" onClick={onCommit}>
                Back to my answer
              </button>
            </div>
          )}
          <div className="flex gap-2 pt-1">
            <input
              className="input flex-1 py-1 text-xs"
              placeholder="Reply to the guide…"
              value={input}
              disabled={loading}
              onChange={(e) => onInputChange(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter' && !e.metaKey && !e.ctrlKey && input.trim()) {
                  e.preventDefault()
                  onSend()
                }
              }}
            />
            <button
              className="btn px-2.5 py-1 text-xs"
              disabled={loading || !input.trim()}
              onClick={onSend}
            >
              Send
            </button>
          </div>
        </>
      )}
    </div>
  )
}

/** Learn & Practice: the priming gate shown before testing a card's question.
 *
 *  Shows the user:
 *  1. The Question to be asked.
 *  2. The Verbatim Answer expected.
 *  3. (Optional) Supporting citations / lesson notes.
 *  Then prompts the user to enter the active recall / practice phase.
 */
function LessonGate({
  item,
  lesson,
  loading: _loading,
  deckName,
  onContinue,
  onOpenSettings: _onOpenSettings,
  codeLanguage = 'typescript',
  activeModel,
  onActiveModelChange,
}: {
  item: QueueItem
  lesson: Lesson | null
  loading?: boolean
  deckName: string | null
  onContinue: () => void
  onOpenSettings?: () => void
  codeLanguage?: string
  activeModel?: string | null
  onActiveModelChange?: (modelId: string) => void
}) {
  const { openLexicon } = useLexicon()
  const isCode = checkIsCodeCard(item) || looksLikeCode(item.back)
  const cleanCode = useMemo(() => (isCode ? extractCleanCode(item.back) : ''), [isCode, item.back])
  const detectedLang = useMemo(
    () => (isCode ? detectCodeLanguage(cleanCode, codeLanguage) : codeLanguage),
    [isCode, cleanCode, codeLanguage]
  )

  const refTestsCode = useMemo(() => (isCode ? buildCompletedTestCode(item) : ''), [isCode, item])
  const starterTestsCode = useMemo(() => (isCode ? buildStarterTestCode(item) : ''), [isCode, item])
  const displayTestsCode = refTestsCode.trim() ? refTestsCode : starterTestsCode
  const testCases = item.test_cases || []
  const edgeCases = item.edge_cases || []
  const hasTests = Boolean(displayTestsCode.trim() || testCases.length > 0)

  const [codeLayout, setCodeLayout] = useState<'stacked' | 'split'>(() => {
    return (storage.get('memorization.learnGateCodeLayout') as 'stacked' | 'split') || 'stacked'
  })
  const [testsTab, setTestsTab] = useState<'all' | 'code' | 'cases'>('all')
  const [showTestsSection, setShowTestsSection] = useState(true)
  const [copiedAnswer, setCopiedAnswer] = useState(false)
  const [copiedTests, setCopiedTests] = useState(false)

  const handleCopyAnswer = async () => {
    if (!cleanCode) return
    try {
      await navigator.clipboard.writeText(cleanCode)
      setCopiedAnswer(true)
      setTimeout(() => setCopiedAnswer(false), 1800)
    } catch {
      // ignore
    }
  }

  const handleCopyTests = async () => {
    const textToCopy = displayTestsCode.trim() || JSON.stringify(testCases, null, 2)
    if (!textToCopy) return
    try {
      await navigator.clipboard.writeText(textToCopy)
      setCopiedTests(true)
      setTimeout(() => setCopiedTests(false), 1800)
    } catch {
      // ignore
    }
  }

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Enter' && !e.shiftKey && !e.metaKey && !e.ctrlKey) {
        const target = e.target as HTMLElement
        if (target.tagName !== 'INPUT' && target.tagName !== 'TEXTAREA') {
          e.preventDefault()
          onContinue()
        }
      }
    }
    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [onContinue])

  const hasReferences = Boolean(item.references && item.references.length > 0)
  const thematic = item.card_thematic_nature || item.deck_thematic_nature
  const doc = item.card_documentation || item.deck_documentation

  const renderAnswerCard = () => (
    <div className="space-y-2 rounded-xl border border-emerald-500/40 bg-emerald-950/20 p-4">
      <div className="flex items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <span className="text-xs font-bold uppercase tracking-wider text-emerald-300 flex items-center gap-1.5">
            Answer · Solution
          </span>
          <span className="rounded bg-emerald-500/10 px-2 py-0.5 text-xs font-mono text-emerald-300 border border-emerald-500/30">
            {detectedLang}
          </span>
        </div>
        <div className="flex items-center gap-2">
          {cleanCode && (
            <button
              type="button"
              onClick={() => void handleCopyAnswer()}
              className="flex items-center gap-1 rounded border border-ink-line bg-[#161b24] hover:bg-[#1f2633] px-2 py-0.5 text-xs text-slate-300 hover:text-white transition cursor-pointer"
              title="Copy solution code to clipboard"
            >
              <span>{copiedAnswer ? 'Copied' : 'Copy'}</span>
            </button>
          )}
        </div>
      </div>

      <div className="rounded-lg border border-ink-line overflow-hidden shadow-sm">
        <CodeEditor
          code={cleanCode}
          onChange={() => {}}
          language={detectedLang}
          readOnly={true}
          height="auto"
          hideHeader={false}
          hideFooter={false}
          borderless={true}
          placeholder="// Expected answer solution"
          activeModel={activeModel}
          onActiveModelChange={onActiveModelChange}
        />
      </div>

      {(item.time_complexity || item.space_complexity) && (
        <div className="flex items-center gap-3 pt-1 text-xs text-emerald-400/90 font-mono">
          {item.time_complexity && <span>Time: {item.time_complexity}</span>}
          {item.space_complexity && <span>Space: {item.space_complexity}</span>}
        </div>
      )}
    </div>
  )

  const renderTestsCard = () => {
    if (!hasTests) return null

    return (
      <div className="space-y-3 rounded-xl border border-indigo-500/40 bg-indigo-950/20 p-4">
        {/* Header */}
        <div className="flex flex-wrap items-center justify-between gap-2 border-b border-indigo-500/20 pb-2.5">
          <div className="flex flex-wrap items-center gap-2">
            <span className="text-xs font-bold uppercase tracking-wider text-indigo-300 flex items-center gap-1.5">
              <span>Tests &amp; Verification</span>
            </span>
            {testCases.length > 0 && (
              <span className="rounded-full bg-indigo-500/15 border border-indigo-500/30 px-2 py-0.5 text-[0.625rem] font-mono text-indigo-200">
                {testCases.length} {testCases.length === 1 ? 'case' : 'cases'}
              </span>
            )}
            {/* View Sub-Tabs if both unit test code and test cases exist */}
            {displayTestsCode.trim() && testCases.length > 0 && (
              <div className="inline-flex rounded-md bg-[#121622] p-0.5 border border-ink-line text-[0.6875rem] ml-1">
                <button
                  type="button"
                  onClick={() => setTestsTab('all')}
                  className={`px-2 py-0.5 rounded transition cursor-pointer ${
                    testsTab === 'all'
                      ? 'bg-indigo-600/40 text-indigo-100 border border-indigo-500/50 font-semibold'
                      : 'text-slate-400 hover:text-slate-200'
                  }`}
                >
                  All
                </button>
                <button
                  type="button"
                  onClick={() => setTestsTab('code')}
                  className={`px-2 py-0.5 rounded transition cursor-pointer ${
                    testsTab === 'code'
                      ? 'bg-indigo-600/40 text-indigo-100 border border-indigo-500/50 font-semibold'
                      : 'text-slate-400 hover:text-slate-200'
                  }`}
                >
                  Unit Tests
                </button>
                <button
                  type="button"
                  onClick={() => setTestsTab('cases')}
                  className={`px-2 py-0.5 rounded transition cursor-pointer ${
                    testsTab === 'cases'
                      ? 'bg-indigo-600/40 text-indigo-100 border border-indigo-500/50 font-semibold'
                      : 'text-slate-400 hover:text-slate-200'
                  }`}
                >
                  Cases ({testCases.length})
                </button>
              </div>
            )}
          </div>

          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={() => void handleCopyTests()}
              className="flex items-center gap-1 rounded border border-ink-line bg-[#161b24] hover:bg-[#1f2633] px-2 py-0.5 text-xs text-slate-300 hover:text-white transition cursor-pointer"
              title="Copy unit tests to clipboard"
            >
              <span>{copiedTests ? 'Copied' : 'Copy Tests'}</span>
            </button>
            <button
              type="button"
              onClick={() => setShowTestsSection((prev) => !prev)}
              className="rounded border border-ink-line/60 bg-[#161b24] hover:bg-[#1f2633] px-2 py-0.5 text-xs text-slate-400 hover:text-slate-200 transition cursor-pointer"
              title={showTestsSection ? 'Collapse tests' : 'Expand tests'}
            >
              <span>{showTestsSection ? 'Hide' : 'Show'}</span>
            </button>
          </div>
        </div>

        {/* Content Body */}
        {showTestsSection && (
          <div className="space-y-4">
            {/* 1. Unit Tests Code */}
            {(testsTab === 'all' || testsTab === 'code') && displayTestsCode.trim() && (
              <div className="space-y-1.5">
                <div className="flex items-center justify-between text-xs text-slate-400">
                  <span className="font-semibold text-slate-200">Unit Test Suite</span>
                  <span className="font-mono text-[0.6875rem] text-indigo-300">{detectedLang}</span>
                </div>
                <div className="rounded-lg border border-ink-line overflow-hidden shadow-sm">
                  <CodeEditor
                    code={displayTestsCode}
                    onChange={() => {}}
                    language={detectedLang}
                    readOnly={true}
                    height="auto"
                    hideHeader={false}
                    hideFooter={false}
                    borderless={true}
                    placeholder="// Completed unit test suite"
                    activeModel={activeModel}
                    onActiveModelChange={onActiveModelChange}
                  />
                </div>
              </div>
            )}

            {/* 2. Structured Test Cases Table */}
            {(testsTab === 'all' || testsTab === 'cases') && testCases.length > 0 && (
              <div className="space-y-1.5">
                <div className="flex items-center justify-between text-xs text-slate-400">
                  <span className="font-semibold text-slate-200">Test Cases ({testCases.length})</span>
                </div>
                <div className="overflow-x-auto rounded-lg border border-ink-line/80">
                  <table className="w-full text-left text-xs">
                    <thead className="bg-[#182030] text-slate-300 font-mono text-[0.6875rem] border-b border-ink-line/80">
                      <tr>
                        <th className="px-3 py-2 w-10 text-slate-400">#</th>
                        <th className="px-3 py-2">Input</th>
                        <th className="px-3 py-2">Expected Output</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-ink-line/40 font-mono text-[0.6875rem] bg-[#10141f]">
                      {testCases.map((tc, idx) => (
                        <tr key={idx} className="hover:bg-[#161c2b] transition-colors">
                          <td className="px-3 py-2 text-slate-500 font-bold">{idx + 1}</td>
                          <td className="px-3 py-2 text-sky-200">
                            {typeof tc.input === 'object' && tc.input !== null
                              ? Object.entries(tc.input)
                                  .map(([k, v]) => `${k}: ${JSON.stringify(v)}`)
                                  .join(', ')
                              : JSON.stringify(tc.input)}
                          </td>
                          <td className="px-3 py-2 text-emerald-300 font-semibold">
                            {JSON.stringify(tc.expected)}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}

            {/* 3. Edge Cases */}
            {edgeCases.length > 0 && (
              <div className="rounded-lg bg-[#121622] border border-indigo-500/30 p-2.5 text-xs text-slate-300 space-y-1">
                <span className="font-semibold text-indigo-300 text-[0.6875rem] uppercase tracking-wider block">
                  Target Edge Cases &amp; Boundaries:
                </span>
                <ul className="list-disc list-inside space-y-0.5 text-slate-300 text-[0.6875rem]">
                  {edgeCases.map((ec, i) => (
                    <li key={i}>{ec}</li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        )}
      </div>
    )
  }

  return (
    <div className="card space-y-5">
      {/* ── Top Header Strip ── */}
      <div className="flex flex-wrap items-center justify-between gap-2 border-b border-ink-line pb-3 text-xs">
        <div className="flex flex-wrap items-center gap-2">
          {deckName && <span className="chip font-semibold text-slate-300">{deckName}</span>}
          <span className="chip border-sky-500/40 bg-sky-500/15 text-sky-200 font-semibold">
            Learn &amp; Practice
          </span>
          {thematic && (
            <span className="chip border-sky-400/30 text-sky-300">
              {thematic}
            </span>
          )}
        </div>

        <button
          type="button"
          onClick={() =>
            openLexicon(item.title || 'terminology', item.front || '', null, {
              cardId: item.id,
              deckName,
              thematicNature: thematic,
            })
          }
          className="flex items-center gap-1.5 rounded-full border border-sky-400/40 bg-sky-950/70 px-2.5 py-1 text-xs font-semibold text-sky-200 hover:bg-sky-900/80 hover:border-sky-300 transition-all shadow-sm"
          title="Lexicon lookup"
        >
          <span>Lexicon</span>
        </button>
      </div>

      {/* Step Indicator Banner */}
      <div className="rounded-lg bg-sky-500/10 border border-sky-500/25 p-3 text-xs text-sky-200 flex items-center justify-between gap-3">
        <div className="flex items-center gap-2">
          <span className="font-bold text-sky-300">Priming</span>
          <span>Review before answering.</span>
        </div>
        <kbd className="hidden sm:inline-block px-2 py-0.5 rounded bg-slate-800 text-[0.6875rem] font-mono border border-slate-700 text-sky-300">
          Enter ↵
        </kbd>
      </div>

      {/* ── 1. The Question Asked ── */}
      <div className="space-y-2 rounded-xl border border-sky-500/30 bg-sky-950/15 p-4">
        <div className="flex items-center justify-between">
          <span className="text-xs font-bold uppercase tracking-wider text-sky-300 flex items-center gap-1.5">
            Question
          </span>
          {item.category && (
            <span className="chip text-[0.625rem] text-slate-400">{item.category}</span>
          )}
        </div>

        {item.title && <h3 className="text-base font-bold text-slate-100">{item.title}</h3>}

        {item.occlusion ? (
          <div className="space-y-2">
            {item.occlusion.header && (
              <p className="text-sm font-medium text-slate-200">{item.occlusion.header}</p>
            )}
            <OcclusionCard payload={item.occlusion} revealed={false} />
          </div>
        ) : (
          <RichText
            text={item.front || item.title || 'No prompt specified'}
            className="text-sm md:text-base font-medium text-slate-100 leading-relaxed"
            codeLanguage={detectedLang}
            deckId={item.kind === 'card' ? item.deck_or_source_id : null}
          />
        )}
      </div>

      {/* ── 2. The Answer to the Question (Verbatim) & Tests ── */}
      {item.occlusion ? (
        <div className="space-y-2 rounded-xl border border-emerald-500/40 bg-emerald-950/20 p-4">
          <span className="text-xs font-bold uppercase tracking-wider text-emerald-300 flex items-center gap-1.5">
            Answer
          </span>
          <OcclusionCard payload={item.occlusion} revealed={true} />
        </div>
      ) : isCode ? (
        <div className="space-y-3">
          {/* Layout Switcher if tests exist */}
          {hasTests && (
            <div className="flex flex-wrap items-center justify-between gap-2 text-xs px-1">
              <div className="flex items-center gap-1.5">
                <span className="text-[0.6875rem] font-semibold uppercase tracking-wider text-slate-400">Layout:</span>
                <div className="inline-flex rounded-lg bg-[#141822] p-0.5 border border-ink-line/60">
                  <button
                    type="button"
                    onClick={() => {
                      setCodeLayout('stacked')
                      storage.set('memorization.learnGateCodeLayout', 'stacked')
                    }}
                    className={`px-2.5 py-0.5 rounded text-xs font-medium transition cursor-pointer flex items-center gap-1.5 ${
                      codeLayout === 'stacked'
                        ? 'bg-slate-700/70 text-white border border-slate-500/50 shadow-sm font-semibold'
                        : 'text-slate-400 hover:text-slate-200'
                    }`}
                    title="Stacked cards view"
                  >
                    <span>Stacked</span>
                  </button>
                  <button
                    type="button"
                    onClick={() => {
                      setCodeLayout('split')
                      storage.set('memorization.learnGateCodeLayout', 'split')
                    }}
                    className={`hidden sm:flex px-2.5 py-0.5 rounded text-xs font-medium transition cursor-pointer items-center gap-1.5 ${
                      codeLayout === 'split'
                        ? 'bg-sky-600/40 text-sky-100 border border-sky-500/50 shadow-sm font-semibold'
                        : 'text-slate-400 hover:text-slate-200'
                    }`}
                    title="Side-by-side solution and tests view"
                  >
                    <span>⧉ Side-by-Side</span>
                  </button>
                </div>
              </div>
              <span className="text-[0.6875rem] text-slate-400">
                Solution and tests primed before practice phase
              </span>
            </div>
          )}

          {codeLayout === 'split' && hasTests ? (
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 items-start">
              {renderAnswerCard()}
              {renderTestsCard()}
            </div>
          ) : (
            <div className="space-y-4">
              {renderAnswerCard()}
              {renderTestsCard()}
            </div>
          )}
        </div>
      ) : (
        <div className="space-y-2 rounded-xl border border-emerald-500/40 bg-emerald-950/20 p-4">
          <span className="text-xs font-bold uppercase tracking-wider text-emerald-300 flex items-center gap-1.5">
            Answer
          </span>
          <div className="rounded-lg border border-emerald-500/20 bg-slate-950/70 p-3.5">
            <RichText
              text={item.back || 'No answer specified'}
              className="text-xs md:text-sm text-emerald-100 leading-relaxed font-mono whitespace-pre-wrap"
            />
          </div>
          {(item.time_complexity || item.space_complexity) && (
            <div className="flex items-center gap-3 pt-1 text-xs text-emerald-400/90 font-mono">
              {item.time_complexity && <span>Time: {item.time_complexity}</span>}
              {item.space_complexity && <span>Space: {item.space_complexity}</span>}
            </div>
          )}
        </div>
      )}

      {/* ── 3. Supporting Context / Citations / Lesson Notes ── */}
      {(doc || hasReferences || (lesson && lesson.body)) && (
        <details className="rounded-lg border border-ink-line/80 bg-ink/40 p-3 text-xs text-slate-300 group">
          <summary className="cursor-pointer font-semibold text-slate-400 hover:text-slate-200 flex items-center gap-1.5 select-none">
            <span>References</span>
          </summary>
          <div className="mt-3 space-y-3 pt-2 border-t border-ink-line/60">
            {doc && (
              <div>
                <span className="text-slate-400 font-medium block mb-1">Documentation:</span>
                <RichText text={doc} className="text-xs leading-relaxed text-slate-300" />
              </div>
            )}
            {lesson && lesson.body && lesson.body !== item.back && (
              <div>
                <span className="text-slate-400 font-medium block mb-1">Lesson Notes:</span>
                <RichText text={lesson.body} className="text-xs leading-relaxed text-slate-300" />
              </div>
            )}
            {hasReferences && (
              <div className="flex flex-wrap items-center gap-1.5 pt-1">
                <span className="text-slate-400 text-[0.6875rem]">Citations:</span>
                {item.references.map((ref, idx) => (
                  <span key={idx} className="chip text-[0.625rem] text-slate-400" title={ref.quote || undefined}>
                    {ref.source_title ?? ref.locator ?? 'source'}
                  </span>
                ))}
              </div>
            )}
          </div>
        </details>
      )}

      {/* ── 4. Call-to-action to enter Practice Phase ── */}
      <div className="pt-2">
        <button
          type="button"
          className="btn btn-primary w-full py-3 text-sm font-bold flex items-center justify-center gap-2 shadow-lg shadow-sky-950/40 hover:scale-[1.01] active:scale-[0.99] transition-all"
          onClick={onContinue}
        >
          <span>Start Quiz</span>
          <span className="text-xs text-sky-300/80 font-normal">Enter ↵</span>
        </button>
      </div>
    </div>
  )
}

/** The reading a card came from, shown once the answer is revealed.
 *
 *  A verified quote is displayed as a quote; an unverified one was never
 *  stored, so what shows instead is the real passage — the guarantee being
 *  that anything presented in quotation marks genuinely appears in the source.
 */
function ReferenceReadings({
  references,
  overlookedPhrases = [],
  matchedPhrases = [],
}: {
  references?: CardReference[]
  overlookedPhrases?: string[]
  matchedPhrases?: string[]
}) {
  const [expanded, setExpanded] = useState<Set<number>>(new Set())
  if (!references || references.length === 0) return null

  return (
    <div className="rounded-lg border border-ink-line bg-ink p-4">
      <p className="label">
        {references.length > 1 ? 'Reference readings' : 'Reference reading'}
      </p>
      <div className="mt-2 space-y-4">
        {references.map((ref, i) => {
          const showingPassage = expanded.has(i) || !ref.quote
          return (
            <div key={i}>
              <div className="mb-1.5 flex flex-wrap items-center gap-2 text-xs">
                {ref.locator && <span className="chip text-sky-300">{ref.locator}</span>}
                {ref.source_title && <span className="chip">{ref.source_title}</span>}
              </div>

              {ref.quote && !showingPassage ? (
                <blockquote className="border-l-2 border-sky-500/40 pl-3 text-sm italic leading-6 text-slate-300">
                  “
                  <HighlightedText
                    text={ref.quote}
                    overlookedPhrases={overlookedPhrases}
                    matchedPhrases={matchedPhrases}
                    className="inline"
                  />
                  ”
                </blockquote>
              ) : (
                ref.passage && (
                  <HighlightedText
                    text={ref.passage}
                    overlookedPhrases={overlookedPhrases}
                    matchedPhrases={matchedPhrases}
                    className="max-h-64 overflow-y-auto border-l-2 border-ink-line pl-3 text-sm leading-6 text-slate-300"
                  />
                )
              )}

              <div className="mt-2 flex flex-wrap gap-3 text-xs">
                {ref.quote && ref.passage && (
                  <button
                    className="text-slate-500 underline hover:text-slate-300"
                    onClick={() =>
                      setExpanded((prev) => {
                        const next = new Set(prev)
                        next.has(i) ? next.delete(i) : next.add(i)
                        return next
                      })
                    }
                  >
                    {showingPassage ? 'Show just the quote' : 'Show the full passage'}
                  </button>
                )}
                {ref.extract_id && (
                  <a
                    className="text-slate-500 underline hover:text-slate-300"
                    href={`/read/${ref.extract_id}`}
                  >
                    Open in Read
                  </a>
                )}
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}

interface VramConstraintPromptProps {
  result: SubmitAnswerResponse
  loading: boolean
  onSwitchModel: (model: string) => void
  onRetry: () => void
  onGradeManually: () => void
}

function VramConstraintPrompt({
  result,
  loading,
  onSwitchModel,
  onRetry,
  onGradeManually,
}: VramConstraintPromptProps) {
  const defaultModel =
    result.fallback_model ||
    result.available_fallback_models?.[0] ||
    'qwen2.5-coder:1.5b'
  const [chosenModel, setChosenModel] = useState<string>(defaultModel)

  return (
    <div className="rounded-xl border border-amber-500/50 bg-amber-950/40 p-5 space-y-4 text-slate-200 shadow-xl animate-fadeIn">
      <div className="flex items-start gap-3.5">
        <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-amber-500/20 text-amber-300 border border-amber-500/30">
          <svg className="w-5 h-5 text-amber-300" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>
        </div>
        <div className="space-y-1">
          <div className="flex flex-wrap items-center gap-2">
            <h4 className="text-base font-semibold text-amber-200">
              GPU VRAM / Memory Limit Reached
            </h4>
            <span className="text-xs px-2 py-0.5 rounded bg-amber-500/20 text-amber-300 border border-amber-500/40 font-mono">
              {result.failed_model || 'Local Model'}
            </span>
          </div>
          <p className="text-xs text-slate-300 leading-relaxed">
            Your system's available GPU VRAM or host memory could not allocate space for{' '}
            <strong className="text-amber-300 font-mono">{result.failed_model || 'this model'}</strong>.
            Would you like to switch to a smaller local model, or free up more VRAM by closing apps and retry?
          </p>
        </div>
      </div>

      <div className="rounded-lg bg-black/40 border border-white/10 p-3.5 space-y-2.5">
        <div className="flex flex-wrap items-center justify-between gap-3 text-xs">
          <div className="space-y-1">
            <span className="text-slate-400 font-medium">Recommended next biggest model:</span>
            <div className="flex items-center gap-2 font-mono text-emerald-300 font-semibold text-sm">
              <span>{chosenModel}</span>
              <span className="chip text-[0.625rem] px-1.5 py-0.2 border-emerald-500/40 text-emerald-300 bg-emerald-500/10">
                {getModelInfo(chosenModel).badge || 'Smaller size'}
              </span>
            </div>
          </div>

          {result.available_fallback_models &&
            result.available_fallback_models.filter(isAllowedGradingModel).length > 1 && (
              <div className="flex items-center gap-2">
                <span className="text-xs text-slate-400">Other models:</span>
                <select aria-label="Grading model"
                  value={chosenModel}
                  onChange={(e) => setChosenModel(e.target.value)}
                  className="select text-xs py-1 px-2.5 bg-slate-900 border-slate-700 text-slate-200 font-mono rounded"
                >
                  {result.available_fallback_models.filter(isAllowedGradingModel).map((m) => (
                    <option key={m} value={m}>
                      {m}
                    </option>
                  ))}
                </select>
              </div>
            )}
        </div>
      </div>

      <div className="flex flex-wrap items-center gap-2.5 pt-1">
        <button
          type="button"
          disabled={loading}
          onClick={() => onSwitchModel(chosenModel)}
          className="btn btn-primary text-xs py-2 px-4 font-medium flex items-center gap-2 bg-emerald-700 hover:bg-emerald-600 text-white border-emerald-500 shadow-sm"
        >
          {loading ? (
            <>
              <span className="inline-block h-3.5 w-3.5 animate-spin rounded-full border-2 border-white/20 border-t-white" />
              <span>Grading with {chosenModel}…</span>
            </>
          ) : (
            <>
              <span>Switch to {chosenModel} & Grade</span>
            </>
          )}
        </button>

        <button
          type="button"
          disabled={loading}
          onClick={onRetry}
          className="btn btn-secondary text-xs py-2 px-3.5 flex items-center gap-1.5 border-slate-700 hover:bg-slate-800 text-slate-200"
          title="Retry AI model"
        >
          <span>↻ Retry {result.failed_model || 'Grading'}</span>
        </button>

        <button
          type="button"
          disabled={loading}
          onClick={onGradeManually}
          className="btn text-xs py-2 px-3 opacity-75 hover:opacity-100 text-slate-400 hover:text-slate-200 ml-auto"
        >
          <span>Grade Manually</span>
        </button>
      </div>
    </div>
  )
}

/** Model metadata formatter for Antigravity subscription and local Ollama models */
function getModelInfo(modelName: string): {
  label: string
  short: string
  archetype: string
  badge?: string
  desc?: string
  provider: 'ollama' | 'antigravity'
} {
  return getModelDisplayInfo(modelName)
}

interface DiscreteModelSelectorProps {
  activeModel: string
  installedModels: string[]
  grading: boolean
  hasAnswer: boolean
  isRevealed?: boolean
  onSelectModel: (model: string) => void
  onGradeWithModel: (model: string) => void
  className?: string
}

/** Discrete model switcher positioned adjacent to grading button.
 *  Allows switching between Antigravity Subscription models and local Ollama archetypes.
 */
function DiscreteModelSelector({
  activeModel,
  installedModels,
  grading,
  hasAnswer,
  isRevealed = false,
  onSelectModel,
  onGradeWithModel,
  className = '',
}: DiscreteModelSelectorProps) {
  const { user } = useAuth()
  const canUseAntigravity = Boolean(user?.can_use_antigravity)
  const [open, setOpen] = useState(false)
  const [vram, setVram] = useState<VramMetrics | null>(null)
  const menuRef = useRef<HTMLDivElement>(null)
  const isAgyActive = canUseAntigravity && isAntigravityModel(activeModel)

  useEffect(() => {
    if (!open) return
    if (isAgyActive) {
      setVram(null)
    } else {
      api.vramStatus(activeModel).then(setVram).catch(() => {})
    }
    const handleDown = (e: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
        setOpen(false)
      }
    }
    const handleKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') setOpen(false)
    }
    document.addEventListener('mousedown', handleDown)
    document.addEventListener('keydown', handleKey)
    return () => {
      document.removeEventListener('mousedown', handleDown)
      document.removeEventListener('keydown', handleKey)
    }
  }, [open, activeModel, isAgyActive])

  const models = useMemo<string[]>(() => {
    if (!canUseAntigravity) {
      return ['qwen3.5:9b', 'qwen2.5-coder:7b', 'qwen3.5:4b']
    }
    const agyInstalled = installedModels.filter(isAntigravityModel)
    const agyList = agyInstalled.length > 0 ? agyInstalled : ANTIGRAVITY_MODELS.map((a) => a.id)
    return [...agyList, 'qwen3.5:9b', 'qwen2.5-coder:7b', 'qwen3.5:4b']
  }, [installedModels, canUseAntigravity])

  const currentInfo = getModelInfo(activeModel)
  const isFast = currentInfo.badge?.toLowerCase().includes('fast') || currentInfo.badge?.toLowerCase().includes('speed')

  return (
    <div className={`relative inline-block ${className}`} ref={menuRef}>
      <button
        type="button"
        onClick={() => setOpen((prev) => !prev)}
        className={`group flex items-center gap-1.5 rounded-lg border px-2.5 py-1.5 text-xs font-medium transition-all ${
          open
            ? 'border-sky-500/60 bg-sky-950/50 text-sky-200 ring-2 ring-sky-500/20'
            : grading
            ? 'border-amber-500/40 bg-amber-500/10 text-amber-200 hover:border-amber-400'
            : 'border-slate-700/80 bg-slate-900/80 text-slate-300 hover:border-slate-500 hover:bg-slate-800 hover:text-white'
        }`}
        title={`Model: ${activeModel}`}
      >
        <span className="text-[0.625rem] font-mono text-slate-400 uppercase">
          {isAgyActive ? 'AGY' : isFast ? 'Fast' : 'AI'}
        </span>
        <span className="font-mono text-[0.6875rem] font-semibold tracking-tight">{currentInfo.short}</span>
        <span
          className={`text-[0.5625rem] text-slate-400 transition-transform duration-150 ${
            open ? 'rotate-180 text-sky-400' : 'group-hover:text-slate-200'
          }`}
        >
          ▾
        </span>
      </button>

      {open && (
        <div className="absolute bottom-full left-0 mb-2 w-88 rounded-xl border border-slate-700/80 bg-slate-900/95 p-3 shadow-2xl backdrop-blur-md z-50 text-xs">
          <div className="flex items-center justify-between pb-2 border-b border-slate-800">
            <div className="flex items-center gap-1.5">
              <span className="font-semibold text-slate-100">AI Grading Engine</span>
              <span className="text-[0.625rem] text-slate-400 font-mono">AGY &amp; Local</span>
            </div>
            <span className="flex items-center gap-1 text-[0.625rem] text-emerald-400 font-medium">
              <span className="h-1.5 w-1.5 rounded-full bg-emerald-400 animate-pulse" />
              {isAgyActive ? 'Subscription' : 'Quantized'}
            </span>
          </div>

          {/* Live VRAM Telemetry inside Discrete Switcher (Ollama only) */}
          {!isAgyActive && vram && (
            <div className="my-2 rounded-lg border border-slate-800 bg-slate-950/80 p-2 space-y-1.5">
              <div className="flex items-center justify-between text-[0.6875rem]">
                <span className="text-slate-300 font-semibold flex items-center gap-1">
                  <svg className="w-3 h-3 text-sky-400" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <rect x="2" y="3" width="20" height="14" rx="2" ry="2" />
                    <line x1="8" y1="21" x2="16" y2="21" />
                    <line x1="12" y1="17" x2="12" y2="21" />
                  </svg>
                  <span>VRAM Hardware Telemetry</span>
                </span>
                <span className="text-[0.625rem] font-mono text-slate-400 truncate max-w-[140px]">{vram.gpu_name}</span>
              </div>
              <div className="grid grid-cols-3 gap-1.5 text-center font-mono">
                <div className="rounded bg-slate-900/80 p-1 border border-slate-800/60">
                  <div className="text-[0.5625rem] uppercase text-slate-400">Capacity</div>
                  <div className="font-bold text-slate-100 text-[0.6875rem]">
                    {vram.capacity_gb != null ? `${vram.capacity_gb.toFixed(1)} GB` : 'N/A'}
                  </div>
                </div>
                <div className="rounded bg-sky-950/40 p-1 border border-sky-500/30">
                  <div className="text-[0.5625rem] uppercase text-sky-300">Model VRAM</div>
                  <div className="font-bold text-sky-200 text-[0.6875rem]">
                    {vram.model_loaded && vram.model_vram_gb
                      ? `${vram.model_vram_gb.toFixed(1)} GB`
                      : `~${vram.model_approx_gb || 0} GB`}
                  </div>
                </div>
                <div className="rounded bg-emerald-950/40 p-1 border border-emerald-500/30">
                  <div className="text-[0.5625rem] uppercase text-emerald-300">Available</div>
                  <div className="font-bold text-emerald-200 text-[0.6875rem]">
                    {vram.available_gb != null ? `${vram.available_gb.toFixed(1)} GB` : 'N/A'}
                  </div>
                </div>
              </div>
            </div>
          )}

          <div className="my-2 space-y-1.5 max-h-64 overflow-y-auto pr-1">
            {models.map((m) => {
              const isAgyItem = isAntigravityModel(m)
              const isCurrent = isAgyItem
                ? m.toLowerCase() === activeModel.toLowerCase()
                : m === activeModel ||
                  (!isAntigravityModel(activeModel) &&
                    Boolean(activeModel) &&
                    activeModel.toLowerCase().includes(m.split(':')[0]))
              const info = getModelInfo(m)
              const isInstalled = installedModels.some(
                (im) =>
                  im.toLowerCase() === m.toLowerCase() ||
                  (!isAgyItem && im.toLowerCase().startsWith(m.toLowerCase())),
              )
              const isSelectable = isInstalled || isAgyItem
              return (
                <div
                  key={m}
                  className={`group flex items-center justify-between rounded-lg border p-2 transition ${
                    isCurrent
                      ? 'border-sky-500/60 bg-sky-950/40 text-sky-100 ring-1 ring-sky-500/30'
                      : isSelectable
                      ? 'border-slate-800 bg-slate-900/40 hover:border-slate-700 hover:bg-slate-800/60 text-slate-300 cursor-pointer'
                      : 'border-slate-800/60 bg-slate-900/20 text-slate-500'
                  }`}
                  onClick={() => {
                    if (isSelectable) {
                      onSelectModel(m)
                      setOpen(false)
                    } else {
                      void navigator.clipboard.writeText(`ollama pull ${m}`)
                    }
                  }}
                >
                  <div className="flex-1 min-w-0 pr-2">
                    <div className="flex items-center gap-1.5">
                      <span className={`font-semibold truncate ${isSelectable ? 'text-slate-100' : 'text-slate-400'}`}>
                        {info.label}
                      </span>
                      {info.badge && (
                        <span
                          className={`text-[0.5625rem] px-1 py-0.2 rounded font-semibold border ${
                            info.provider === 'antigravity'
                              ? 'border-indigo-400/40 text-indigo-200 bg-indigo-500/15'
                              : info.badge.includes('Speed') || info.badge.includes('Fast')
                              ? 'border-emerald-500/40 text-emerald-300 bg-emerald-500/10'
                              : info.badge.includes('Technical')
                              ? 'border-indigo-500/40 text-indigo-300 bg-indigo-500/10'
                              : 'border-sky-500/40 text-sky-300 bg-sky-500/10'
                          }`}
                        >
                          {info.badge}
                        </span>
                      )}
                      {isCurrent && (
                        <span className="text-[0.625rem] text-sky-400 font-bold ml-auto shrink-0">Active</span>
                      )}
                    </div>
                    <div className="text-[0.625rem] font-medium italic text-sky-300/90 mt-0.5">
                      {info.archetype}
                    </div>
                    {info.desc && (
                      <p className="text-[0.625rem] text-slate-400 truncate mt-0.5">{info.desc}</p>
                    )}
                  </div>

                  {/* Immediate Action: Grade if selectable, or Pull prompt if local model missing */}
                  {isSelectable ? (
                    hasAnswer && (
                      <button
                        type="button"
                        className="shrink-0 rounded px-2 py-1 text-[0.6875rem] font-medium border border-slate-700 bg-slate-800 hover:border-sky-500 hover:bg-sky-600 hover:text-white text-slate-200 transition"
                        title={`Grade answer now using ${info.label}`}
                        onClick={(e) => {
                          e.stopPropagation()
                          onGradeWithModel(m)
                          setOpen(false)
                        }}
                      >
                        {grading ? '↻ Retry' : isRevealed ? '↻ Re-grade' : 'Grade'}
                      </button>
                    )
                  ) : (
                    <button
                      type="button"
                      className="shrink-0 text-[0.625rem] font-mono text-sky-400 hover:text-sky-200 underline cursor-pointer"
                      onClick={(e) => {
                        e.stopPropagation()
                        void navigator.clipboard.writeText(`ollama pull ${m}`)
                      }}
                      title={`Copy pull command: ollama pull ${m}`}
                    >
                      Pull
                    </button>
                  )}
                </div>
              )
            })}
          </div>

          <div className="pt-2 border-t border-slate-800 flex items-center justify-between text-[0.6875rem]">
            <span className="text-slate-400">
              {grading ? (
                <span className="text-amber-300 flex items-center gap-1">
                  <span className="animate-spin text-xs">↻</span> Grading in progress…
                </span>
              ) : hasAnswer ? (
                <span>Click model to switch, or button to grade</span>
              ) : (
                <span>Click model to set as active grader</span>
              )}
            </span>
            {grading && (
              <button
                type="button"
                className="text-amber-400 hover:text-amber-200 underline font-medium cursor-pointer"
                onClick={() => {
                  const alt = models.find((m) => m !== activeModel) || activeModel
                  onGradeWithModel(alt)
                  setOpen(false)
                }}
              >
                Cancel &amp; retry
              </button>
            )}
          </div>
        </div>
      )}
    </div>
  )
}

/** §4.1 step 5: show the score *and* the reasoning, so the model is auditable.
 *
 *  The score (0-100) is the actual grading feedback — correctness against key
 *  concepts and keyword match. The grade chip next to it is only the FSRS
 *  scheduling bucket that score landed in; "confidence" is a separate axis
 *  entirely (how sure the model is in its own score), so it's labelled to
 *  avoid being read as a second correctness number.
 */
function GradeReasoning({
  result,
  installedModels = [],
  activeModel,
  grading = false,
  hasAnswer = false,
  onSelectModel,
  onGradeWithModel,
}: {
  result: SubmitAnswerResponse
  installedModels?: string[]
  activeModel?: string
  grading?: boolean
  hasAnswer?: boolean
  onSelectModel?: (m: string) => void
  onGradeWithModel?: (m: string) => void
}) {
  const pct = Math.round(result.confidence * 100)
  return (
    <div className="rounded-lg border border-ink-line bg-ink p-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="flex flex-wrap items-center gap-2">
          {result.score !== null && (
            <span className={`chip text-base font-semibold ${GRADE_STYLE[result.suggested_grade]}`}>
              {Math.round(result.score)}%
            </span>
          )}
          <span className={`chip capitalize ${GRADE_STYLE[result.suggested_grade]}`}>
            {result.suggested_grade}
          </span>
          <span className="chip">model confidence {pct}%</span>
          {result.model_used && <span className="chip">{result.model_used}</span>}
          {result.cached && <span className="chip">cached</span>}
          {result.heuristic_overlap !== null && (
            <span className="chip">keyword overlap {Math.round(result.heuristic_overlap * 100)}%</span>
          )}
        </div>

        {onSelectModel && onGradeWithModel && (
          <div className="flex items-center gap-1.5">
            <span className="text-[0.6875rem] text-slate-400">Retry with:</span>
            <DiscreteModelSelector
              activeModel={activeModel || result.model_used || 'qwen2.5-coder:3b'}
              installedModels={installedModels}
              grading={grading}
              hasAnswer={hasAnswer}
              isRevealed={true}
              onSelectModel={onSelectModel}
              onGradeWithModel={onGradeWithModel}
            />
          </div>
        )}
      </div>

      {result.reasoning && <p className="mt-3 text-sm text-slate-300">{result.reasoning}</p>}

      {result.needs_confirmation && (
        <p className="mt-3 rounded border border-amber-500/30 bg-amber-500/10 px-3 py-2 text-xs text-amber-200">
          This grade disagreed with the keyword check, or the model wasn't confident — worth a
          second look before you accept it.
        </p>
      )}

      {result.automaticity_exceeded && (
        <p className="mt-3 rounded border border-amber-500/30 bg-amber-500/10 px-3 py-2 text-xs text-amber-200">
          {result.automaticity_note || 'Reaction latency exceeded target automaticity threshold.'}
        </p>
      )}
    </div>
  )
}

/** Pre-Answer Primer: collapsible related content drawer allowing the student
 *  to optionally review source quotes, citations, or lesson before committing
 *  an answer to memory.
/** Collapsible card for thematic context, deck documentation, and creation source documents. */
function ThematicDocumentationCard({ item }: { item: QueueItem }) {
  const [expanded, setExpanded] = useState(false)

  const theme = item.card_thematic_nature || item.deck_thematic_nature
  const doc = item.card_documentation || item.deck_documentation
  const sources = item.card_source_documents || item.deck_source_documents || []

  if (!theme && !doc && sources.length === 0) return null

  return (
    <div className="rounded-xl border border-sky-500/30 bg-gradient-to-r from-sky-950/20 to-ink-soft/40 p-3.5 space-y-2 text-xs backdrop-blur-xs">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="flex flex-wrap items-center gap-2">
          <span className="font-semibold text-sky-200">Thematic Context &amp; Documentation</span>
          {theme && (
            <span className="chip border-sky-400/40 text-sky-300 bg-sky-500/10 font-semibold">
              {theme}
            </span>
          )}
        </div>
        {doc && (
          <button
            type="button"
            onClick={() => setExpanded((prev) => !prev)}
            className="text-[0.6875rem] text-sky-300 hover:text-white underline cursor-pointer"
          >
            {expanded ? 'Hide Documentation' : 'View Documentation'}
          </button>
        )}
      </div>

      {sources.length > 0 && (
        <div className="flex flex-wrap items-center gap-1.5 pt-0.5">
          <span className="text-[0.6875rem] text-slate-400">Creation Documents:</span>
          {sources.map((sd: any, idx: number) => {
            let label = ''
            let quoteText = ''
            if (typeof sd === 'string') {
              try {
                const parsed = JSON.parse(sd)
                if (typeof parsed === 'object' && parsed !== null) {
                  sd = parsed
                } else {
                  label = sd
                }
              } catch {
                label = sd
              }
            }
            if (typeof sd === 'object' && sd !== null) {
              const name = sd.title || sd.name || sd.filename || 'Document'
              const locator = sd.locator ? ` (${sd.locator})` : ''
              const pages = !sd.locator && sd.pages ? ` (pp. ${sd.pages})` : ''
              label = `${name}${locator || pages}`
              quoteText = sd.quote || ''
            }
            return (
              <span
                key={idx}
                className="chip border-emerald-500/30 bg-emerald-500/10 text-emerald-300 text-[0.6875rem]"
                title={quoteText ? `Citation quote: "${quoteText}"` : undefined}
              >
                {label}
              </span>
            )
          })}
        </div>
      )}

      {expanded && doc && (
        <div className="mt-2 rounded-lg border border-ink-line/60 bg-ink/80 p-3 text-slate-300 leading-relaxed text-xs">
          <RichText text={doc} />
        </div>
      )}
    </div>
  )
}

function PrimerDrawer({
  item,
  lesson,
  loading,
  onReady,
}: {
  item: QueueItem
  lesson: Lesson | null
  loading: boolean
  onReady: () => void
}) {
  const hasReferences = Boolean(item.references && item.references.length > 0)
  const hasLessonBody = Boolean(lesson && lesson.available && lesson.body)

  return (
    <div className="mb-5 rounded-lg border border-sky-500/30 bg-sky-950/20 p-4 transition-all">
      <div className="mb-3 flex items-center justify-between gap-2 border-b border-sky-500/20 pb-2.5">
        <div className="flex items-center gap-2 text-xs font-semibold text-sky-300">
          <span>Primer</span>
          <span className="chip border-sky-500/30 text-[0.625rem] text-sky-200">Pre-review</span>
        </div>
        <button
          type="button"
          onClick={onReady}
          className="text-xs text-slate-400 underline hover:text-slate-200"
        >
          Dismiss
        </button>
      </div>

      {loading ? (
        <Spinner label="Loading primer…" />
      ) : (
        <div className="space-y-3">
          {hasLessonBody ? (
            <div className="space-y-2">
              <RichText text={lesson!.body} className="text-sm leading-relaxed text-slate-200" />
              {lesson!.key_points && lesson!.key_points.length > 0 && (
                <div className="pt-2">
                  <p className="text-xs font-medium text-sky-300">Key Points:</p>
                  <ul className="mt-1 space-y-1 text-xs text-slate-300">
                    {lesson!.key_points.map((p, i) => (
                      <li key={i}>• {p}</li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          ) : hasReferences ? (
            <div className="space-y-2">
              <p className="text-xs font-medium text-sky-300">Citations:</p>
              <div className="max-h-56 space-y-2 overflow-y-auto pr-1">
                {item.references!.map((ref, idx) => (
                  <div key={idx} className="rounded border border-sky-500/20 bg-ink/60 p-2.5 text-xs text-slate-300">
                    <div className="mb-1 flex items-center gap-2 font-mono text-[0.625rem] text-sky-300">
                      {ref.locator && <span>[{ref.locator}]</span>}
                      {ref.source_title && <span>{ref.source_title}</span>}
                    </div>
                    {ref.quote && (
                      <blockquote className="border-l-2 border-sky-400/50 pl-2 italic text-slate-200">
                        “{ref.quote}”
                      </blockquote>
                    )}
                    {ref.passage && !ref.quote && (
                      <div className="whitespace-pre-wrap">{ref.passage}</div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          ) : (
            <div className="space-y-1 text-xs text-slate-400">
              <p>
                <strong className="text-slate-300">Deck:</strong> {item.deck_name}
              </p>
              <p className="text-slate-500">
                No external citations attached. Recall key concepts and prepare your response below.
              </p>
            </div>
          )}

          <div className="flex items-center justify-end border-t border-sky-500/20 pt-3">
            <button
              type="button"
              onClick={onReady}
              className="btn btn-primary flex items-center gap-1.5 px-3 py-1 text-xs font-semibold"
            >
              <span>Answer</span>
              <span>&rarr;</span>
            </button>
          </div>
        </div>
      )}
    </div>
  )
}

/** Prominent callout card for overlooked or unconsidered content post-grading. */
function OverlookedAnalysisCard({ result }: { result: SubmitAnswerResponse }) {
  const hasMissed = result.missed_points.length > 0
  const hasOverlookedPhrases = Boolean(result.overlooked_phrases && result.overlooked_phrases.length > 0)
  const isComplete = !hasMissed && !hasOverlookedPhrases && (result.score === null || result.score >= 90)

  if (isComplete) {
    return (
      <div className="flex items-center gap-2 rounded-lg border border-emerald-500/40 bg-emerald-500/10 p-3.5 text-xs text-emerald-200">
        
        <div>
          <span className="font-semibold">Complete Recall:</span> All key concepts recalled.
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-3">
      {(hasMissed || hasOverlookedPhrases) && (
        <div className="rounded-lg border border-amber-500/40 bg-amber-500/10 p-4">
          <div className="flex items-center gap-2 text-sm font-semibold text-amber-200">
            
            <span>Overlooked</span>
          </div>
          <p className="mt-1 text-xs text-amber-300/80">
            Omitted from answer:
          </p>
          {hasMissed && (
            <ul className="mt-2.5 space-y-1.5 text-sm text-amber-100">
              {result.missed_points.map((p, i) => (
                <li key={i} className="flex items-start gap-2">
                  <span className="font-bold text-amber-400">•</span>
                  <span>{p}</span>
                </li>
              ))}
            </ul>
          )}
          {hasOverlookedPhrases && (
            <div className="mt-3 border-t border-amber-500/20 pt-2.5">
              <p className="mb-1.5 text-[0.6875rem] font-medium text-amber-300/70">
                Omitted Phrases:
              </p>
              <div className="flex flex-wrap gap-1.5">
                {result.overlooked_phrases!.map((phrase, i) => (
                  <span
                    key={i}
                    className="inline-flex items-center rounded border border-amber-500/30 bg-amber-500/20 px-2 py-0.5 text-xs font-medium text-amber-200"
                  >
                    {phrase}
                  </span>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {result.matched_points.length > 0 && (
        <div className="rounded-lg border border-emerald-500/30 bg-emerald-500/10 p-3">
          <div className="flex items-center gap-1.5 text-xs font-semibold text-emerald-200">
            <span>Recalled</span>
          </div>
          <ul className="mt-1.5 space-y-1 text-xs text-emerald-100/90">
            {result.matched_points.map((p, i) => (
              <li key={i} className="flex items-start gap-1.5">
                <svg className="w-3 h-3 text-emerald-400 shrink-0" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5"><polyline points="20 6 9 17 4 12"/></svg>
                <span>{p}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Longitudinal Weakness Memory: Improvements & Resolved Pitfalls */}
      {result.improvements && result.improvements.length > 0 && (
        <div className="rounded-lg border border-emerald-500/50 bg-emerald-500/15 p-3.5">
          <div className="flex items-center gap-2 text-xs font-semibold text-emerald-200">
            
            <span>Resolved Weakness</span>
          </div>
          <p className="mt-1 text-[0.6875rem] text-emerald-300/80">
            Resolved from previous reviews:
          </p>
          <ul className="mt-2 space-y-1 text-xs text-emerald-100">
            {result.improvements.map((imp, i) => (
              <li key={i} className="flex items-start gap-1.5">
                <svg className="w-3 h-3 text-emerald-400 shrink-0" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5"><polyline points="20 6 9 17 4 12"/></svg>
                <span>{imp}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Longitudinal Weakness Memory: Persistent Recurring Blind Spots */}
      {result.persistent_weaknesses && result.persistent_weaknesses.length > 0 && (
        <div className="rounded-lg border border-rose-500/40 bg-rose-500/15 p-3.5">
          <div className="flex items-center gap-2 text-xs font-semibold text-rose-200">
            
            <span>Recurring Weakness</span>
          </div>
          <p className="mt-1 text-[0.6875rem] text-rose-300/80">
            Flagged in prior reviews:
          </p>
          <ul className="mt-2 space-y-1 text-xs text-rose-100">
            {result.persistent_weaknesses.map((pw, i) => (
              <li key={i} className="flex items-start gap-1.5">
                <span className="text-rose-400 font-bold">•</span>
                <span>{pw}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Longitudinal Weakness Memory: Newly Logged Flaws Stored for Next Time */}
      {result.weaknesses && result.weaknesses.length > 0 && (
        <div className="rounded-lg border border-amber-500/30 bg-amber-500/10 p-3 text-xs">
          <div className="flex items-center gap-1.5 font-semibold text-amber-200">
            
            <span>Saved to Memory:</span>
          </div>
          <p className="mt-1 text-[0.6875rem] text-amber-300/70">
            Noted for future reviews:
          </p>
          <ul className="mt-1.5 space-y-1 text-xs text-amber-100">
            {result.weaknesses.map((w, i) => (
              <li key={i} className="flex items-start gap-1.5">
                <span className="text-amber-400 font-bold">•</span>
                <span>{w}</span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  )
}

interface TermHighlight {
  term: string
  type: 'overlooked' | 'matched'
}

function highlightParts(text: string, terms: TermHighlight[]) {
  if (!terms.length || !text) return [{ text, type: null }]

  // Sort terms by length descending so longer phrases match first
  const sorted = [...terms]
    .filter((t) => t.term && t.term.trim().length > 1)
    .sort((a, b) => b.term.length - a.term.length)

  if (sorted.length === 0) return [{ text, type: null }]

  const uniqueTerms: TermHighlight[] = []
  const seen = new Set<string>()
  for (const t of sorted) {
    const key = t.term.trim().toLowerCase()
    if (!seen.has(key)) {
      seen.add(key)
      uniqueTerms.push({ term: t.term.trim(), type: t.type })
    }
  }

  const escaped = uniqueTerms
    .map((t) => t.term.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'))
    .join('|')

  let regex: RegExp
  try {
    regex = new RegExp(`(${escaped})`, 'gi')
  } catch {
    return [{ text, type: null }]
  }

  const parts = text.split(regex)
  const termMap = new Map<string, 'overlooked' | 'matched'>()
  for (const t of uniqueTerms) {
    termMap.set(t.term.toLowerCase(), t.type)
  }

  return parts
    .map((part) => ({
      text: part,
      type: termMap.get(part.toLowerCase()) || null,
    }))
    .filter((p) => p.text.length > 0)
}

/** Highlights text with amber for overlooked terms and emerald for matched terms. */
function HighlightedText({
  text,
  overlookedPhrases = [],
  matchedPhrases = [],
  className = '',
}: {
  text: string
  overlookedPhrases?: string[]
  matchedPhrases?: string[]
  className?: string
}) {
  if (!text) return null

  const terms: TermHighlight[] = [
    ...overlookedPhrases.map((t) => ({ term: t, type: 'overlooked' as const })),
    ...matchedPhrases.map((t) => ({ term: t, type: 'matched' as const })),
  ]

  const mediaParts = text.split(/(!\[\]\([^)]+\)|\[audio\]\([^)]+\))/g)

  return (
    <div className={`whitespace-pre-wrap break-words ${className}`}>
      {mediaParts.map((part, i) => {
        const img = part.match(/^!\[\]\(([^)]+)\)$/)
        if (img) {
          const src = img[1].startsWith('/')
            ? `${API_BASE}${img[1]}`
            : img[1]
          return (
            <img
              key={i}
              src={src}
              alt=""
              className="my-2 max-h-72 rounded-lg border border-ink-line"
            />
          )
        }
        const audio = part.match(/^\[audio\]\(([^)]+)\)$/)
        if (audio) {
          const src = audio[1].startsWith('/')
            ? `${API_BASE}${audio[1]}`
            : audio[1]
          return <audio key={i} controls src={src} className="my-2 w-full" />
        }

        const segments = highlightParts(part, terms)
        return (
          <span key={i}>
            {segments.map((seg, j) => {
              if (seg.type === 'overlooked') {
                return (
                  <mark
                    key={j}
                    className="rounded border-b-2 border-amber-400 bg-amber-500/25 px-1 py-0.5 font-semibold text-amber-200 shadow-sm"
                    title="Overlooked"
                  >
                    {seg.text}
                  </mark>
                )
              }
              if (seg.type === 'matched') {
                return (
                  <mark
                    key={j}
                    className="rounded border-b border-emerald-500/40 bg-emerald-500/20 px-1 py-0.5 text-emerald-200"
                    title="Recalled"
                  >
                    {seg.text}
                  </mark>
                )
              }
              return <span key={j}>{seg.text}</span>
            })}
          </span>
        )
      })}
    </div>
  )
}

/** IR extracts surfaced inside the review session (§9.4). */
function ExtractCard({ item, onDone }: { item: QueueItem; onDone: () => void }) {
  const navigate = useNavigate()
  const [busy, setBusy] = useState(false)

  async function postpone(days: number) {
    setBusy(true)
    try {
      await api.scheduleExtract(item.id, { days })
      onDone()
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="card">
      <div className="mb-3 flex flex-wrap items-center gap-2">
        <span className="chip">reading</span>
        <span className="chip">{item.source_title}</span>
        <span className="chip">priority {item.priority}</span>
      </div>
      <RichText
        text={item.extract_content ?? ''}
        className="max-h-[26rem] overflow-y-auto text-[0.9375rem] leading-7 text-slate-200"
      />
      <div className="mt-5 flex flex-wrap gap-2">
        <button className="btn btn-primary" onClick={() => navigate(`/read/${item.id}`)}>
          Work on this
        </button>
        <button className="btn" disabled={busy} onClick={() => postpone(3)}>
          Later (3d)
        </button>
        <button className="btn" disabled={busy} onClick={() => postpone(14)}>
          Much later (14d)
        </button>
        <button
          className="btn"
          disabled={busy}
          onClick={async () => {
            setBusy(true)
            try {
              await api.scheduleExtract(item.id, { status: 'done' })
              onDone()
            } finally {
              setBusy(false)
            }
          }}
        >
          Done with it
        </button>
      </div>
    </div>
  )
}

function SessionHeader({
  session,
  outcome,
  branchActive,
  onClearBranch,
  deckActive,
  deckName,
  learnMode,
  onToggleLearnMode,
  blitzActive,
  onStartBlitz,
  persistActive,
  persistDeckName,
  persistUnseenOnly,
  onExitPersist,
  persistProgress,
  allCardsRunActive,
  allCardsRunDeckName,
  onExitAllCardsRun,
  allCardsRunProgress,
  onStartAllCardsRun,
  allDecks,
  onStartPersist,
  savedCount,
  onOpenSavedDrawer,
  previousCard,
  onRetryPreviousCard,
}: {
  session: SessionSummary | null
  outcome?: string | null
  branchActive?: boolean
  onClearBranch?: () => void
  deckActive?: boolean
  deckName?: string
  learnMode?: boolean
  onToggleLearnMode?: () => void
  blitzActive?: boolean
  onStartBlitz?: (sec: number) => void
  persistActive?: boolean
  persistDeckName?: string
  persistUnseenOnly?: boolean
  onExitPersist?: () => void
  persistProgress?: { grasped: number; total: number; round: number }
  allCardsRunActive?: boolean
  allCardsRunDeckName?: string
  onExitAllCardsRun?: () => void
  allCardsRunProgress?: { current: number; total: number }
  onStartAllCardsRun?: (deckId: string, deckName?: string) => void
  allDecks?: Deck[]
  onStartPersist?: (deckId: string, deckName?: string, unseenOnly?: boolean) => void
  savedCount?: number
  onOpenSavedDrawer?: () => void
  previousCard?: QueueItem | null
  onRetryPreviousCard?: () => void
}) {
  const [quickPersistUnseenOnly, setQuickPersistUnseenOnly] = useState(false)
  if (!session && !persistActive && !allCardsRunActive) return null
  const counts = session?.counts
  const caps = session?.caps
  const planned = ((counts?.review ?? 0) + (counts?.new ?? 0) + (counts?.ir ?? 0))

  const [modesOpen, setModesOpen] = useState(false)
  const decksWithCards = (allDecks ?? []).filter((d) => d.card_count > 0).length
  const hasModeLaunchers =
    (!persistActive && !allCardsRunActive && decksWithCards > 0 && Boolean(onStartPersist || onStartAllCardsRun)) ||
    Boolean(onStartBlitz && !blitzActive)

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-center gap-2 text-xs">
        {allCardsRunActive && (
          <span className="chip border-purple-500/50 bg-purple-500/15 text-purple-200 font-semibold flex items-center gap-1.5 shadow-sm">
            <span>Run: {allCardsRunDeckName || 'Current Deck'}</span>
            {allCardsRunProgress && (
              <span className="text-[0.625rem] text-purple-300/90 font-mono">
                ({allCardsRunProgress.current}/{allCardsRunProgress.total} · Easiest → Hardest)
              </span>
            )}
            {onExitAllCardsRun && (
              <button
                type="button"
                className="ml-1 text-slate-400 hover:text-white underline text-[0.6875rem] cursor-pointer"
                onClick={onExitAllCardsRun}
                title="Exit All Cards Run and return to FSRS queue"
              >
                exit
              </button>
            )}
          </span>
        )}

        {persistActive && (
          <span className="chip border-amber-500/50 bg-amber-500/15 text-amber-200 font-semibold flex items-center gap-1.5 shadow-sm">
            <span>Persist{persistUnseenOnly ? ' (Unseen)' : ''}: {persistDeckName || 'Current Deck'}</span>
            {persistProgress && (
              <span className="text-[0.625rem] text-amber-300/90 font-mono">
                ({persistProgress.grasped}/{persistProgress.total} Easy · R{persistProgress.round})
              </span>
            )}
            {onExitPersist && (
              <button
                type="button"
                className="ml-1 text-slate-400 hover:text-white underline"
                onClick={onExitPersist}
                title="Exit persist mode"
              >
                exit
              </button>
            )}
          </span>
        )}

        {branchActive && (
          <span className="chip border-sky-500/40 text-sky-300">
            branch-scoped
            {onClearBranch && (
              <button className="ml-2 underline" onClick={onClearBranch}>
                exit
              </button>
            )}
          </span>
        )}

        {deckActive && (
          <span className="chip border-sky-500/50 bg-sky-500/10 text-sky-200 flex items-center gap-1.5 shadow-sm">
            <span>Deck Tree: {deckName || 'Deck + Subdecks'}</span>
            {onClearBranch && (
              <button
                type="button"
                className="ml-1 text-slate-400 hover:text-white underline text-[0.6875rem]"
                onClick={onClearBranch}
                title="Switch to studying all decks in collection"
              >
                study all
              </button>
            )}
          </span>
        )}

        {!branchActive && !deckActive && !persistActive && !allCardsRunActive && (
          <span className="chip border-emerald-500/40 bg-emerald-500/10 text-emerald-200 font-medium">
            Collection: All Decks
          </span>
        )}

        {session && (
          <>
            <span className="chip">{counts?.review ?? 0} reviews</span>
            <span className="chip">{counts?.new ?? 0} new</span>
            <span className="chip">{counts?.ir ?? 0} reading</span>
            <span className="chip">~{Math.round(session.budget_seconds / 60)} min budget</span>
            {caps && caps.reviews_done_today > 0 && (
              <span className="chip">{caps.reviews_done_today} done today</span>
            )}
            {planned === 0 && <span className="chip">queue clear</span>}
          </>
        )}

        {/* Persist, All Cards Run and Blitz are ways to *start* a different kind
            of session, not things you need while answering a card. They sit
            behind one toggle so the row above the card stays a single line. */}
        {hasModeLaunchers && (
          <button
            type="button"
            className={`chip transition cursor-pointer ${
              modesOpen ? 'border-sky-500/50 text-sky-200' : 'hover:text-slate-200'
            }`}
            aria-expanded={modesOpen}
            aria-controls="review-study-modes"
            onClick={() => setModesOpen((open) => !open)}
            title="Persist drill, All Cards Run and Blitz sprint"
          >
            Study modes {modesOpen ? '▴' : '▾'}
          </button>
        )}

        {hasModeLaunchers && modesOpen && (
          <div
            id="review-study-modes"
            className="order-last flex basis-full flex-wrap items-center gap-x-5 gap-y-2 rounded-lg border border-ink-line bg-ink-soft/60 px-3 py-2"
          >
            {/* Quick Persist Deck Selector (when not in persist mode) */}
            {!persistActive && !allCardsRunActive && allDecks && allDecks.filter((d) => d.card_count > 0).length > 0 && onStartPersist && (
              <div className="flex items-center gap-1.5">
                <span className="text-[0.6875rem] text-amber-400 font-medium">Persist Deck:</span>
                <label className="flex items-center gap-1 text-[0.6875rem] text-slate-300 cursor-pointer select-none">
                  <input
                    type="checkbox"
                    checked={quickPersistUnseenOnly}
                    onChange={(e) => setQuickPersistUnseenOnly(e.target.checked)}
                    className="rounded border-slate-700 bg-ink-soft text-amber-500 focus:ring-0 w-3 h-3 cursor-pointer"
                  />
                  <span className="text-[0.625rem] text-amber-300/80">Unseen only</span>
                </label>
                <select
                  aria-label="Deck to drill in persist mode"
                  className="rounded border border-amber-500/30 bg-ink-soft px-2 py-0.5 text-[0.6875rem] text-amber-200 hover:border-amber-400 cursor-pointer"
                  defaultValue=""
                  onChange={(e) => {
                    if (e.target.value) {
                      const d = allDecks.find((deck) => deck.id === e.target.value)
                      onStartPersist(e.target.value, d?.name, quickPersistUnseenOnly)
                      e.target.value = ''
                    }
                  }}
                >
                  <option value="" disabled>
                    Select deck to drill…
                  </option>
                  {allDecks
                    .filter((d) => d.card_count > 0)
                    .map((d) => {
                      const viewedPct = d.stats && d.stats.total_cards > 0
                        ? Math.round(d.stats.viewed_ratio * 100)
                        : null
                      return (
                        <option key={d.id} value={d.id}>
                          {d.name} ({d.card_count} cards{viewedPct !== null ? ` · ${viewedPct}% viewed` : ''}{d.new_count > 0 ? ` · ${d.new_count} unseen` : ''})
                        </option>
                      )
                    })}
                </select>
              </div>
            )}

            {/* Quick All Cards Run Selector */}
            {!allCardsRunActive && !persistActive && allDecks && allDecks.filter((d) => d.card_count > 0).length > 0 && onStartAllCardsRun && (
              <div className="flex items-center gap-1.5">
                <span className="text-[0.6875rem] text-purple-400 font-medium">All Cards Run:</span>
                <select
                  aria-label="Deck for an All Cards Run"
                  className="rounded border border-purple-500/30 bg-ink-soft px-2 py-0.5 text-[0.6875rem] text-purple-200 hover:border-purple-400 cursor-pointer"
                  defaultValue=""
                  onChange={(e) => {
                    if (e.target.value) {
                      const d = allDecks.find((deck) => deck.id === e.target.value)
                      onStartAllCardsRun(e.target.value, d?.name)
                      e.target.value = ''
                    }
                  }}
                >
                  <option value="" disabled>
                    Select deck to run…
                  </option>
                  {allDecks
                    .filter((d) => d.card_count > 0)
                    .map((d) => {
                      const viewedPct = d.stats && d.stats.total_cards > 0
                        ? Math.round(d.stats.viewed_ratio * 100)
                        : null
                      return (
                        <option key={d.id} value={d.id}>
                          {d.name} ({d.card_count} cards{viewedPct !== null ? ` · ${viewedPct}% viewed` : ''})
                        </option>
                      )
                    })}
                </select>
              </div>
            )}

            {/* Blitz Mode Sprint Triggers */}
            {onStartBlitz && !blitzActive && (
              <div className="flex items-center gap-1">
                <span className="text-[0.6875rem] text-amber-400 font-medium">Blitz Sprint:</span>
                <button
                  className="chip hover:border-amber-500/40 hover:text-amber-300"
                  onClick={() => onStartBlitz(30)}
                  title="Start high-speed 30 second sprint"
                >
                  30s
                </button>
                <button
                  className="chip hover:border-amber-500/40 hover:text-amber-300"
                  onClick={() => onStartBlitz(60)}
                  title="Start high-speed 60 second sprint"
                >
                  60s
                </button>
                <button
                  className="chip hover:border-amber-500/40 hover:text-amber-300"
                  onClick={() => onStartBlitz(90)}
                  title="Start high-speed 90 second sprint"
                >
                  90s
                </button>
              </div>
            )}
          </div>
        )}

        {savedCount !== undefined && savedCount > 0 && onOpenSavedDrawer && (
          <button
            type="button"
            onClick={onOpenSavedDrawer}
            className="chip border-indigo-500/50 bg-indigo-500/15 text-indigo-200 hover:bg-indigo-500/25 hover:text-white transition cursor-pointer flex items-center gap-1.5 font-semibold shadow-xs"
            title="Open saved cards shelf (Alt+Shift+S)"
          >
            
            <span>Saved for Later ({savedCount})</span>
          </button>
        )}

        {onToggleLearnMode && (
          <button
            className={`chip ml-auto transition ${
              learnMode ? 'border-sky-500/40 text-sky-300' : 'hover:text-slate-300'
            }`}
            onClick={onToggleLearnMode}
            title="Read a short lesson from the card's source before each question"
          >
            Learn &amp; Practice {learnMode ? 'on' : 'off'}
          </button>
        )}
      </div>

      {outcome && (
        <div className="flex flex-wrap items-center justify-between gap-2 text-xs">
          <p className="text-slate-500">Last: {outcome}</p>
          {onRetryPreviousCard && previousCard && (
            <button
              type="button"
              onClick={onRetryPreviousCard}
              className="inline-flex items-center gap-1.5 text-[0.6875rem] text-amber-400 hover:text-amber-300 hover:underline cursor-pointer font-medium transition"
              title={`Retry previous card: "${previousCard.title || previousCard.front?.slice(0, 40)}..."`}
            >
             <span> Retry Previous Card</span>
              <span className="text-slate-500 text-[0.625rem]">
                ({previousCard.title || (previousCard.front ? previousCard.front.slice(0, 25) + '…' : 'card')})
              </span>
            </button>
          )}
        </div>
      )}

      {/* §3.1: guardrails must be visible, or a smoothed backlog looks like a bug.
          One strip for all of them: a separate bordered box per note stacked
          two or three banners between the header and the card. */}
      {session?.notes && session.notes.length > 0 && (
        <ul className="flex flex-wrap gap-x-4 gap-y-1 rounded-lg border border-sky-500/25 bg-sky-500/5 px-3 py-1.5 text-xs text-sky-200/90">
          {session.notes.map((note, i) => (
            <li key={i} className="flex items-baseline gap-1.5">
              <span aria-hidden="true" className="text-sky-400/70">
                •
              </span>
              <span>{note}</span>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}

/** Blitz Sprint Summary Scorecard Modal */
function BlitzScorecardModal({
  stats,
  durationSec,
  onRestart,
  onClose,
}: {
  stats: {
    total: number
    correct: number
    avgLatencySec: number
    cpm: number
    automaticityRate: number
  }
  durationSec: number
  onRestart: (sec: number) => void
  onClose: () => void
}) {
  const accuracy = stats.total > 0 ? Math.round((stats.correct / stats.total) * 100) : 0

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/75 p-4 backdrop-blur-sm animate-fade-in">
      <div className="w-full max-w-md rounded-xl border border-amber-500/40 bg-ink-card p-6 shadow-2xl space-y-5">
        <div className="text-center space-y-1">
          <div className="inline-flex px-3 py-1 items-center justify-center rounded-full bg-amber-500/20 text-xs font-bold uppercase tracking-wider text-amber-300 mb-1">
            Sprint Complete
          </div>
          <h2 className="text-xl font-bold text-slate-100">Sprint Complete!</h2>
          <p className="text-xs text-slate-400">{durationSec}s Memory Athlete Speed Run</p>
        </div>

        <div className="grid grid-cols-2 gap-3">
          <div className="rounded-lg border border-ink-line bg-ink/60 p-3 text-center">
            <p className="text-xs text-slate-400">Cards Answered</p>
            <p className="font-mono text-2xl font-bold text-amber-300">{stats.total}</p>
            <p className="text-[0.625rem] text-slate-500">{stats.cpm} cards / min</p>
          </div>
          <div className="rounded-lg border border-ink-line bg-ink/60 p-3 text-center">
            <p className="text-xs text-slate-400">Accuracy</p>
            <p className={`font-mono text-2xl font-bold ${accuracy >= 85 ? 'text-emerald-400' : 'text-amber-400'}`}>
              {accuracy}%
            </p>
            <p className="text-[0.625rem] text-slate-500">{stats.correct} correct</p>
          </div>
          <div className="rounded-lg border border-ink-line bg-ink/60 p-3 text-center">
            <p className="text-xs text-slate-400">Avg Reaction Time</p>
            <p className="font-mono text-2xl font-bold text-sky-300">
              {Math.floor(stats.avgLatencySec / 60)}m {Math.round(stats.avgLatencySec % 60)}s
            </p>
            <p className="text-[0.625rem] text-slate-500">per retrieval</p>
          </div>
          <div className="rounded-lg border border-ink-line bg-ink/60 p-3 text-center">
            <p className="text-xs text-slate-400">Automaticity Rate</p>
            <p className="font-mono text-2xl font-bold text-emerald-300">{stats.automaticityRate}%</p>
            <p className="text-[0.625rem] text-slate-500">reflexes &lt; 3.0s</p>
          </div>
        </div>

        <div className="flex flex-col gap-2 pt-2">
          <div className="flex items-center gap-2">
            <button
              type="button"
              className="btn btn-primary flex-1 justify-center text-xs"
              onClick={() => onRestart(durationSec)}
            >
              Retry {durationSec}s Sprint
            </button>
            <button
              type="button"
              className="btn flex-1 justify-center text-xs"
              onClick={() => onRestart(durationSec === 30 ? 60 : 30)}
            >
              Switch to {durationSec === 30 ? '60s' : '30s'}
            </button>
          </div>
          <button type="button" className="btn justify-center text-xs text-slate-400" onClick={onClose}>
            Return to Normal Review
          </button>
        </div>
      </div>
    </div>
  )
}

function formatInterval(days: number): string {
  if (days < 1 / 24) return `${Math.max(1, Math.round(days * 1440))} min`
  if (days < 1) return `${Math.round(days * 24)} h`
  if (days < 30) return `${Math.round(days)} d`
  if (days < 365) return `${(days / 30).toFixed(1)} mo`
  return `${(days / 365).toFixed(1)} y`
}
