import crypto from 'node:crypto'
import fs from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import type {
  CardRecord,
  CodeProblemRecord,
  CodeSubmissionRecord,
  ConceptEdgeRecord,
  DeckDocumentRecord,
  DeckRecord,
  ExtractRecord,
  ImportRecordItem,
  NoteTypeRecord,
  QueueConfigRecord,
  RecentLexiconRecord,
  ReviewLogRecord,
  SisterPairRecord,
  SourceRecord,
  StudySessionRecord,
  TreeNodeRecord,
  UserRecord,
} from './types.ts'
import { computeRetrievability, jaccardSimilarity } from './grading.ts'
import { loadAllSocraticGuides } from './socraticGuideParser.ts'
import { buildSeedCardFields } from './socraticLessonService.ts'

const SERVER_DIR = path.dirname(fileURLToPath(import.meta.url))
const ROOT_DIR = path.resolve(SERVER_DIR, '..')

export function newId(prefix = ''): string {
  const raw = crypto.randomUUID()
  return prefix ? `${prefix}_${raw}` : raw
}

export function hashPassword(password: string): string {
  return crypto.createHash('sha256').update(`ars-salt:${password}`).digest('hex')
}

interface RawCatalogEntry {
  slug: string
  title: string
  kind?: 'fundamental' | 'problem'
  track?: string | null
  difficulty?: 'Easy' | 'Medium' | 'Hard'
  category?: string
  tags?: string[]
  description?: string
  examples?: Array<{ input: string; output: string; explanation?: string }>
  constraints?: string[]
  starter_codes?: Record<string, string>
  solutions?: Record<string, string>
  editorial?: string | null
  test_cases?: Array<{ input: unknown; expected: unknown }>
  hints?: string[]
}

function loadJsonFile<T>(filePath: string, fallback: T): T {
  try {
    if (!fs.existsSync(filePath)) return fallback
    return JSON.parse(fs.readFileSync(filePath, 'utf-8')) as T
  } catch {
    return fallback
  }
}

export interface GuttagLexiconEntry {
  term: string
  definition?: string
  chapter?: string
  example?: string
  domain?: string
}

export class MemoryStore {
  users = new Map<string, UserRecord>()
  tokens = new Map<string, { userId: string; tokenVersion: number; scope: 'full' | 'review' }>()
  decks = new Map<string, DeckRecord>()
  noteTypes = new Map<string, NoteTypeRecord>()
  cards = new Map<string, CardRecord>()
  reviewLogs: ReviewLogRecord[] = []
  nextLogId = 1
  treeNodes = new Map<string, TreeNodeRecord>()
  sources = new Map<string, SourceRecord>()
  extracts = new Map<string, ExtractRecord>()
  sessions = new Map<string, StudySessionRecord>()
  queueConfigs = new Map<string, QueueConfigRecord>()
  sisterPairs = new Map<string, SisterPairRecord>()
  conceptEdges = new Map<string, ConceptEdgeRecord>()
  codeProblems = new Map<string, CodeProblemRecord>()
  codeSubmissions: CodeSubmissionRecord[] = []
  imports: ImportRecordItem[] = []
  deckDocuments = new Map<string, DeckDocumentRecord>()
  recentLexicon: RecentLexiconRecord[] = []
  mediaFiles = new Map<string, { buffer: Buffer; contentType: string; filename: string }>()
  guttagLexicon = new Map<string, GuttagLexiconEntry>()

  constructor() {
    this.loadStaticCatalogs()
    // Pre-seed a ready-to-use demo account so either sign-in or registration works immediately
    this.createUser('demo@arsmemoriae.app', 'password123')
  }

  private loadStaticCatalogs() {
    const problemsPath = path.join(SERVER_DIR, 'data', 'problems_catalog.json')
    const fundamentalsPath = path.join(SERVER_DIR, 'data', 'fundamentals_catalog.json')
    const now = new Date().toISOString()

    const problems = loadJsonFile<RawCatalogEntry[]>(problemsPath, [])
    for (const item of problems) {
      const id = `prob_${item.slug}`
      this.codeProblems.set(id, {
        id,
        kind: 'problem',
        track: item.track ?? null,
        title: item.title,
        slug: item.slug,
        difficulty: item.difficulty ?? 'Medium',
        category: item.category ?? 'Algorithms',
        tags: item.tags ?? [],
        description: item.description ?? '',
        examples: item.examples ?? [],
        constraints: item.constraints ?? [],
        starter_codes: item.starter_codes ?? { python: 'class Solution:\n    pass' },
        solutions: item.solutions ?? {},
        editorial: item.editorial ?? null,
        test_cases: item.test_cases ?? [],
        hints: item.hints ?? [],
        created_at: now,
      })
    }

    const fundamentals = loadJsonFile<RawCatalogEntry[]>(fundamentalsPath, [])
    for (const item of fundamentals) {
      const id = `fund_${item.slug}`
      this.codeProblems.set(id, {
        id,
        kind: 'fundamental',
        track: item.track ?? 'track_0_python_basics',
        title: item.title,
        slug: item.slug,
        difficulty: item.difficulty ?? 'Easy',
        category: item.category ?? 'Python Basics',
        tags: item.tags ?? [],
        description: item.description ?? '',
        examples: item.examples ?? [],
        constraints: item.constraints ?? [],
        starter_codes: item.starter_codes ?? { python: 'def solve():\n    pass' },
        solutions: item.solutions ?? {},
        editorial: item.editorial ?? null,
        test_cases: item.test_cases ?? [],
        hints: item.hints ?? [],
        created_at: now,
      })
    }

    const lexiconPath = path.join(ROOT_DIR, 'frontend', 'public', 'data', 'guttag_lexicon.json')
    const rawLex = loadJsonFile<Record<string, GuttagLexiconEntry> | GuttagLexiconEntry[]>(lexiconPath, [])
    if (Array.isArray(rawLex)) {
      for (const entry of rawLex) {
        if (entry?.term) this.guttagLexicon.set(entry.term.toLowerCase(), entry)
      }
    } else if (rawLex && typeof rawLex === 'object') {
      for (const [k, v] of Object.entries(rawLex)) {
        if (typeof v === 'string') {
          this.guttagLexicon.set(k.toLowerCase(), { term: k, definition: v, domain: 'Computer Science' })
        } else if (v && typeof v === 'object') {
          this.guttagLexicon.set(k.toLowerCase(), { ...v, term: v.term || k })
        }
      }
    }
  }

  publicUser(u: UserRecord) {
    return {
      id: u.id,
      email: u.email,
      desired_retention: u.desired_retention,
      grading_model: u.grading_model,
      queue_time_budget_minutes: u.queue_time_budget_minutes,
      leech_remediation_opt_in: u.leech_remediation_opt_in,
      daily_new_limit: u.daily_new_limit,
      daily_review_limit: u.daily_review_limit,
      backlog_spread_days: u.backlog_spread_days,
      leech_threshold: u.leech_threshold,
      llm_grading_consent: u.llm_grading_consent,
      fsrs_optimized_at: u.fsrs_optimized_at,
      grading_bias: u.grading_bias,
      automaticity_threshold_ms: u.automaticity_threshold_ms,
      target_event_date: u.target_event_date,
      target_event_title: u.target_event_title,
      peak_retention_target: u.peak_retention_target,
      show_pre_leetcode: u.show_pre_leetcode,
      show_code_lab: u.show_code_lab,
      show_thematic_context: u.show_thematic_context,
      tutorial_completed: u.tutorial_completed,
      timezone: u.timezone,
      enable_schema_checkpoints: u.enable_schema_checkpoints,
      enable_prompt_mutation: u.enable_prompt_mutation,
      enable_prediction_mode: u.enable_prediction_mode,
      can_use_antigravity: u.can_use_antigravity,
    }
  }

  issueToken(user: UserRecord, scope: 'full' | 'review' = 'full'): string {
    const token = crypto.randomBytes(24).toString('hex')
    this.tokens.set(token, { userId: user.id, tokenVersion: user.token_version, scope })
    return token
  }

  getUserByToken(token: string | undefined): UserRecord | null {
    if (!token) return null
    const rec = this.tokens.get(token)
    if (!rec) return null
    const user = this.users.get(rec.userId)
    if (!user || user.token_version !== rec.tokenVersion) return null
    return user
  }

  findUserByEmail(email: string): UserRecord | undefined {
    const norm = email.trim().toLowerCase()
    for (const u of this.users.values()) {
      if (u.email === norm) return u
    }
    return undefined
  }

  createUser(email: string, password: string): UserRecord {
    const id = newId('usr')
    const user: UserRecord = {
      id,
      email: email.trim().toLowerCase(),
      password_hash: hashPassword(password),
      token_version: 1,
      desired_retention: 0.9,
      grading_model: 'qwen2.5-coder:7b',
      queue_time_budget_minutes: 25,
      leech_remediation_opt_in: true,
      daily_new_limit: 20,
      daily_review_limit: 120,
      backlog_spread_days: 7,
      leech_threshold: 8,
      llm_grading_consent: true,
      fsrs_optimized_at: null,
      grading_bias: 0,
      automaticity_threshold_ms: 8000,
      target_event_date: null,
      target_event_title: null,
      peak_retention_target: 0.95,
      show_pre_leetcode: true,
      show_code_lab: true,
      show_thematic_context: true,
      tutorial_completed: false,
      timezone: null,
      enable_schema_checkpoints: true,
      enable_prompt_mutation: false,
      enable_prediction_mode: false,
      can_use_antigravity: false,
    }
    this.users.set(id, user)
    this.queueConfigs.set(id, {
      review_weight: 0.6,
      new_weight: 0.25,
      ir_weight: 0.15,
      seconds_per_review: 30,
      seconds_per_ir_extract: 90,
    })
    this.seedUserWorkspace(user)
    return user
  }

  private seedUserWorkspace(user: UserRecord) {
    const uid = user.id
    const now = new Date()
    const isoNow = now.toISOString()

    // Note types
    const ntBasic: NoteTypeRecord = {
      id: newId('nt'),
      user_id: uid,
      name: 'Basic (Active Recall)',
      template_kind: 'basic',
      fields: { front: 'Question', back: 'Reference Answer' },
      grading_profile: 'conceptual',
    }
    const ntCloze: NoteTypeRecord = {
      id: newId('nt'),
      user_id: uid,
      name: 'Cloze Deletion',
      template_kind: 'cloze',
      fields: { text: 'Cloze Text' },
      grading_profile: 'exact_term',
    }
    const ntCode: NoteTypeRecord = {
      id: newId('nt'),
      user_id: uid,
      name: 'Code Execution Card',
      template_kind: 'code',
      fields: { front: 'Prompt', back: 'Reference Solution', starter_code: 'Starter Code' },
      grading_profile: 'code',
    }
    for (const nt of [ntBasic, ntCloze, ntCode]) this.noteTypes.set(nt.id, nt)

    // Root topic node
    const topicCsId = newId('node')
    const topicCogId = newId('node')
    this.treeNodes.set(topicCsId, {
      id: topicCsId,
      user_id: uid,
      parent_id: null,
      kind: 'topic',
      title: 'Computer Science & Systems',
      position: 0,
      collapsed: false,
      priority: 80,
      priority_inherited: false,
      deck_id: null,
      source_id: null,
      extract_id: null,
      requires_node_id: null,
      mastery_threshold: 0.8,
    })
    this.treeNodes.set(topicCogId, {
      id: topicCogId,
      user_id: uid,
      parent_id: null,
      kind: 'topic',
      title: 'Memory & Learning Science',
      position: 1,
      collapsed: false,
      priority: 75,
      priority_inherited: false,
      deck_id: null,
      source_id: null,
      extract_id: null,
      requires_node_id: null,
      mastery_threshold: 0.8,
    })

    // Decks
    const deckAlgoId = newId('deck')
    const deckTsId = newId('deck')
    const deckMemoryId = newId('deck')

    const decksToAdd: DeckRecord[] = [
      {
        id: deckAlgoId,
        user_id: uid,
        name: 'Algorithms & Complexity',
        parent_id: null,
        desired_retention_override: null,
        default_priority: 80,
        position: 0,
        target_event_date: null,
        target_event_title: null,
        documentation: 'Core algorithmic invariants, amortized analysis, and graph traversal patterns.',
        thematic_nature: 'Computer Science / Algorithms',
        source_documents: [],
        created_at: isoNow,
      },
      {
        id: deckTsId,
        user_id: uid,
        name: 'TypeScript & Interactive Code Cards',
        parent_id: deckAlgoId,
        desired_retention_override: null,
        default_priority: 78,
        position: 1,
        target_event_date: null,
        target_event_title: null,
        documentation: 'Executable TypeScript recall cards with automated unit test verification.',
        thematic_nature: 'Software Engineering / TypeScript',
        source_documents: [],
        created_at: isoNow,
      },
      {
        id: deckMemoryId,
        user_id: uid,
        name: 'FSRS & Cognitive Science',
        parent_id: null,
        desired_retention_override: null,
        default_priority: 75,
        position: 2,
        target_event_date: null,
        target_event_title: null,
        documentation: 'Spaced repetition theory, retrieval practice, desirable difficulty, and interference.',
        thematic_nature: 'Cognitive Science',
        source_documents: [],
        created_at: isoNow,
      },
    ]

    for (const d of decksToAdd) this.decks.set(d.id, d)

    const deckNodeAlgo = newId('node')
    const deckNodeTs = newId('node')
    const deckNodeMem = newId('node')
    this.treeNodes.set(deckNodeAlgo, {
      id: deckNodeAlgo,
      user_id: uid,
      parent_id: topicCsId,
      kind: 'deck',
      title: 'Algorithms & Complexity',
      position: 0,
      collapsed: false,
      priority: 80,
      priority_inherited: true,
      deck_id: deckAlgoId,
      source_id: null,
      extract_id: null,
      requires_node_id: null,
      mastery_threshold: 0.8,
    })
    this.treeNodes.set(deckNodeTs, {
      id: deckNodeTs,
      user_id: uid,
      parent_id: deckNodeAlgo,
      kind: 'deck',
      title: 'TypeScript & Interactive Code Cards',
      position: 0,
      collapsed: false,
      priority: 78,
      priority_inherited: false,
      deck_id: deckTsId,
      source_id: null,
      extract_id: null,
      requires_node_id: null,
      mastery_threshold: 0.8,
    })
    this.treeNodes.set(deckNodeMem, {
      id: deckNodeMem,
      user_id: uid,
      parent_id: topicCogId,
      kind: 'deck',
      title: 'FSRS & Cognitive Science',
      position: 0,
      collapsed: false,
      priority: 75,
      priority_inherited: true,
      deck_id: deckMemoryId,
      source_id: null,
      extract_id: null,
      requires_node_id: null,
      mastery_threshold: 0.8,
    })

    // Seed Incremental Reading Source + Extracts
    const srcId = newId('src')
    const srcText = [
      'Active recall forces the brain to reconstruct a memory trace from retrieval cues rather than passively recognizing an answer on the back of a flashcard. Every successful retrieval strengthens the synaptic pathway and slows future forgetting.',
      'In the Free Spaced Repetition Scheduler (FSRS), every memory item is modeled with three variables: Stability (S, the interval in days at which retrievability drops to 90%), Difficulty (D, inherent item complexity), and Retrievability (R, instantaneous recall probability).',
      'Interference occurs when two memories share overlapping retrieval cues but map to distinct targets. Separating confusable sister pairs in time and practicing explicit contrast drills dramatically reduces retrieval confusion.',
    ].join('\n\n')
    this.sources.set(srcId, {
      id: srcId,
      user_id: uid,
      title: 'Foundations of Active Recall & FSRS Scheduling',
      url: null,
      raw_text: srcText,
      priority: 72,
      status: 'active',
      created_at: isoNow,
      for_reading: true,
    })

    const ext1Id = newId('ext')
    const ext2Id = newId('ext')
    this.extracts.set(ext1Id, {
      id: ext1Id,
      user_id: uid,
      source_id: srcId,
      content:
        'Active recall forces the brain to reconstruct a memory trace from retrieval cues rather than passively recognizing an answer on the back of a flashcard. Every successful retrieval strengthens the synaptic pathway and slows future forgetting.',
      priority: 72,
      position: 0,
      locator: '§1 Active Recall',
      next_shown_at: isoNow,
      status: 'active',
    })
    this.extracts.set(ext2Id, {
      id: ext2Id,
      user_id: uid,
      source_id: srcId,
      content:
        'In the Free Spaced Repetition Scheduler (FSRS), every memory item is modeled with three variables: Stability (S, the interval in days at which retrievability drops to 90%), Difficulty (D, inherent item complexity), and Retrievability (R, instantaneous recall probability).',
      priority: 70,
      position: 1,
      locator: '§2 Three-Component Memory Model',
      next_shown_at: isoNow,
      status: 'active',
    })

    const srcNodeId = newId('node')
    this.treeNodes.set(srcNodeId, {
      id: srcNodeId,
      user_id: uid,
      parent_id: topicCogId,
      kind: 'source',
      title: 'Foundations of Active Recall & FSRS Scheduling',
      position: 1,
      collapsed: false,
      priority: 72,
      priority_inherited: false,
      deck_id: null,
      source_id: srcId,
      extract_id: null,
      requires_node_id: null,
      mastery_threshold: 0.8,
    })

    // Seed cards
    const pastDue = new Date(Date.now() - 3600_000).toISOString()
    const seededCards: Array<Partial<CardRecord> & { deck_id: string; front: string; back: string }> = [
      {
        deck_id: deckMemoryId,
        front: 'What are the three core variables in the FSRS (Three-Component) memory model, and what does Stability (S) measure?',
        back: 'Stability (S), Difficulty (D), and Retrievability (R). Stability measures the interval in days for recall probability (retrievability) to decay from 100% down to 90%.',
        template_kind: 'basic',
        grading_profile: 'conceptual',
        state: 'review',
        due: pastDue,
        stability: 4.5,
        difficulty: 4.8,
        priority: 85,
        tags: ['fsrs', 'memory-model'],
        review_count: 2,
        last_grade: 'good',
        references: [
          {
            quote: 'Stability (S, the interval in days at which retrievability drops to 90%), Difficulty (D, inherent item complexity), and Retrievability (R, instantaneous recall probability).',
            quote_verified: true,
            locator: '§2 Three-Component Memory Model',
            source_title: 'Foundations of Active Recall & FSRS Scheduling',
            extract_id: ext2Id,
            passage: this.extracts.get(ext2Id)!.content,
          },
        ],
      },
      {
        deck_id: deckMemoryId,
        front: 'Why does typing an answer before revealing the reference outperform passive flip-cards?',
        back: 'Typing enforces active retrieval from memory cues rather than passive recognition, eliminating the illusion of competence and strengthening synaptic memory traces.',
        template_kind: 'basic',
        grading_profile: 'conceptual',
        state: 'new',
        due: null,
        stability: null,
        difficulty: null,
        priority: 82,
        tags: ['active-recall', 'testing-effect'],
        references: [
          {
            quote: 'Active recall forces the brain to reconstruct a memory trace from retrieval cues rather than passively recognizing an answer on the back of a flashcard.',
            quote_verified: true,
            locator: '§1 Active Recall',
            source_title: 'Foundations of Active Recall & FSRS Scheduling',
            extract_id: ext1Id,
            passage: this.extracts.get(ext1Id)!.content,
          },
        ],
      },
      {
        deck_id: deckAlgoId,
        front: 'Why is the amortized time complexity of appending to a dynamically resized array (doubling capacity) O(1) instead of O(n)?',
        back: 'Although a resize copies n elements in O(n) time, doubling capacity ensures resizes happen only at powers of 2, so the total copy work over n appends is bounded by 2n, giving O(1) amortized cost per append.',
        template_kind: 'basic',
        grading_profile: 'conceptual',
        state: 'review',
        due: pastDue,
        stability: 6.2,
        difficulty: 5.1,
        priority: 80,
        tags: ['algorithms', 'amortized-analysis'],
        review_count: 3,
        last_grade: 'good',
      },
      {
        deck_id: deckAlgoId,
        front: 'What is the key invariant that distinguishes Breadth-First Search (BFS) from Depth-First Search (DFS) on an unweighted graph?',
        back: 'BFS uses a FIFO queue and explores vertices in non-decreasing order of edge distance from the source, guaranteeing shortest paths in unweighted graphs; DFS uses a LIFO stack or recursion to explore as deep as possible before backtracking.',
        template_kind: 'basic',
        grading_profile: 'conceptual',
        state: 'new',
        due: null,
        stability: null,
        difficulty: null,
        priority: 79,
        tags: ['graphs', 'bfs', 'dfs'],
      },
      {
        deck_id: deckTsId,
        title: 'Two Sum (TypeScript)',
        front: 'Implement `twoSum(nums: number[], target: number): number[]` in TypeScript returning the indices of the two numbers that sum to `target` in O(n) time.',
        back: '```ts\nfunction twoSum(nums: number[], target: number): number[] {\n  const seen = new Map<number, number>();\n  for (let i = 0; i < nums.length; i++) {\n    const comp = target - nums[i];\n    if (seen.has(comp)) return [seen.get(comp)!, i];\n    seen.set(nums[i], i);\n  }\n  return [];\n}\n```',
        template_kind: 'code',
        grading_profile: 'code',
        state: 'new',
        due: null,
        stability: null,
        difficulty: null,
        priority: 84,
        tags: ['typescript', 'hash-map', 'code'],
        starter_code: 'function twoSum(nums: number[], target: number): number[] {\n  // Return [i, j] such that nums[i] + nums[j] === target\n  return [];\n}\n',
        starter_tests: "test('finds pair summing to 9', () => {\n  assertEquals([0, 1], twoSum([2, 7, 11, 15], 9));\n});\ntest('finds pair summing to 6', () => {\n  assertEquals([1, 2], twoSum([3, 2, 4], 6));\n});\n",
        test_cases: [
          { input: { nums: [2, 7, 11, 15], target: 9 }, expected: [0, 1] },
          { input: { nums: [3, 2, 4], target: 6 }, expected: [1, 2] },
        ],
        time_complexity: 'O(n)',
        space_complexity: 'O(n)',
        edge_cases: ['Negative numbers', 'Duplicate values that sum to target'],
        difficulty_label: 'Easy',
        category: 'Arrays & Hashing',
      },
    ]

    const createdCardIds: string[] = []
    seededCards.forEach((sc, idx) => {
      const cid = newId('card')
      const nid = newId('note')
      createdCardIds.push(cid)
      this.cards.set(cid, {
        id: cid,
        user_id: uid,
        note_id: nid,
        deck_id: sc.deck_id,
        template_slot: 'front_back',
        template_kind: sc.template_kind ?? 'basic',
        grading_profile: sc.grading_profile ?? 'conceptual',
        state: sc.state ?? 'new',
        due: sc.due ?? null,
        stability: sc.stability ?? null,
        difficulty: sc.difficulty ?? null,
        priority: sc.priority ?? 70,
        lapse_count: 0,
        leech_flag: false,
        suspended: false,
        tags: sc.tags ?? [],
        front: sc.front,
        back: sc.back,
        image: null,
        back_image: null,
        occlusion: null,
        references: sc.references ?? [],
        starter_code: sc.starter_code ?? null,
        starter_tests: sc.starter_tests ?? null,
        test_cases: sc.test_cases ?? [],
        time_complexity: sc.time_complexity ?? null,
        space_complexity: sc.space_complexity ?? null,
        edge_cases: sc.edge_cases ?? [],
        title: sc.title ?? null,
        difficulty_label: sc.difficulty_label ?? null,
        category: sc.category ?? null,
        documentation: null,
        thematic_nature: null,
        source_documents: [],
        lexicon_glosses: [],
        position: idx,
        memory_note: null,
        active_weaknesses: [],
        weakness_history: [],
        failure_reminder: null,
        last_grade: sc.last_grade ?? null,
        review_count: sc.review_count ?? 0,
        is_schema_checkpoint: idx === 0,
        spatial_x: 120 + idx * 140,
        spatial_y: 100 + (idx % 2) * 110,
        spatial_locus: idx === 0 ? 'Entrance Hall' : null,
        mnemonic_vignette: null,
        created_at: isoNow,
      })
    })

    // Seed two concept graph edges
    if (createdCardIds.length >= 4) {
      const e1 = newId('edge')
      this.conceptEdges.set(e1, {
        id: e1,
        user_id: uid,
        source_card_id: createdCardIds[0],
        target_card_id: createdCardIds[1],
        relationship_type: 'supports',
        weight: 0.85,
        created_at: isoNow,
      })
      const e2 = newId('edge')
      this.conceptEdges.set(e2, {
        id: e2,
        user_id: uid,
        source_card_id: createdCardIds[2],
        target_card_id: createdCardIds[3],
        relationship_type: 'relates_to',
        weight: 0.7,
        created_at: isoNow,
      })
    }

    // Seed a couple of historical review logs for Stats heatmap / analytics
    const yesterday = new Date(Date.now() - 86_400_000).toISOString()
    if (createdCardIds.length >= 3) {
      this.reviewLogs.push(
        {
          id: this.nextLogId++,
          user_id: uid,
          card_id: createdCardIds[0],
          reviewed_at: yesterday,
          final_grade: 'good',
          typed_answer: 'Stability, Difficulty, and Retrievability; Stability is days until 90% recall.',
          latency_ms: 6200,
          llm_grade: 'good',
          llm_reasoning: 'Matched all three FSRS variables accurately.',
          llm_confidence: 0.88,
          overridden: false,
          user_confidence: 4,
          is_blitz: false,
          weaknesses: [],
          improvements: [],
          stability_before: 2.0,
          stability_after: 4.5,
          retrievability_before: 0.89,
          client_review_id: null,
        },
        {
          id: this.nextLogId++,
          user_id: uid,
          card_id: createdCardIds[2],
          reviewed_at: yesterday,
          final_grade: 'good',
          typed_answer: 'Doubling capacity spreads O(n) copy cost across n appends for O(1) amortized.',
          latency_ms: 7400,
          llm_grade: 'good',
          llm_reasoning: 'Clear explanation of geometric growth amortization.',
          llm_confidence: 0.86,
          overridden: false,
          user_confidence: 4,
          is_blitz: false,
          weaknesses: [],
          improvements: [],
          stability_before: 3.1,
          stability_after: 6.2,
          retrievability_before: 0.88,
          client_review_id: null,
        },
      )
    }

    // Seed the 4-part JavaScript & TypeScript: Zero to Mastery course (105 cards, 27 chapters)
    // parsed directly from the uploaded Socratic study guides.
    this.seedJsTsSocraticCourse(uid, isoNow, topicCsId)
  }

  private seedJsTsSocraticCourse(uid: string, isoNow: string, parentTopicNodeId: string) {
    const course = loadAllSocraticGuides(path.join(ROOT_DIR, 'public/assets/aistudio'))
    if (course.cards.length === 0) return

    const courseRootDeckId = newId('deck')
    this.decks.set(courseRootDeckId, {
      id: courseRootDeckId,
      user_id: uid,
      name: 'JavaScript & TypeScript: Zero to Mastery',
      parent_id: null,
      desired_retention_override: null,
      default_priority: 85,
      position: 0,
      target_event_date: null,
      target_event_title: null,
      documentation:
        'Four-part Socratic course (27 chapters, 105 cards) covering JavaScript fundamentals, TypeScript core, intermediate type narrowing & generics, and hands-on labs.',
      thematic_nature: 'JavaScript & TypeScript Curriculum',
      source_documents: course.parts.map((p) => ({
        title: p.partTitle,
        filename: p.sourceFile,
      })),
      created_at: isoNow,
    })

    const courseRootNodeId = newId('node')
    this.treeNodes.set(courseRootNodeId, {
      id: courseRootNodeId,
      user_id: uid,
      parent_id: parentTopicNodeId,
      kind: 'deck',
      title: 'JavaScript & TypeScript: Zero to Mastery',
      position: 0,
      collapsed: false,
      priority: 85,
      priority_inherited: false,
      deck_id: courseRootDeckId,
      source_id: null,
      extract_id: null,
      requires_node_id: null,
      mastery_threshold: 0.8,
    })

    const deckIdByName = new Map<string, string>()

    course.parts.forEach((part, partIdx) => {
      const partDeckId = newId('deck')
      this.decks.set(partDeckId, {
        id: partDeckId,
        user_id: uid,
        name: part.partTitle,
        parent_id: courseRootDeckId,
        desired_retention_override: null,
        default_priority: 84 - partIdx,
        position: partIdx,
        target_event_date: null,
        target_event_title: null,
        documentation: `${part.partTitle} — ${part.chapters.length} chapters, ${part.cards.length} Socratic recall cards.`,
        thematic_nature: part.partTitle,
        source_documents: [{ title: part.partTitle, filename: part.sourceFile }],
        created_at: isoNow,
      })

      const partNodeId = newId('node')
      this.treeNodes.set(partNodeId, {
        id: partNodeId,
        user_id: uid,
        parent_id: courseRootNodeId,
        kind: 'deck',
        title: part.partTitle,
        position: partIdx,
        collapsed: partIdx > 0,
        priority: 84 - partIdx,
        priority_inherited: true,
        deck_id: partDeckId,
        source_id: null,
        extract_id: null,
        requires_node_id: null,
        mastery_threshold: 0.8,
      })

      part.decks.forEach((pDeck, deckIdx) => {
        const subDeckId = newId('deck')
        deckIdByName.set(pDeck.name, subDeckId)

        const deckDocParts: string[] = []
        if (pDeck.coreIdea) deckDocParts.push(`**Core idea:** ${pDeck.coreIdea}`)
        if (pDeck.summary) deckDocParts.push(pDeck.summary)
        if (pDeck.readMoreLinks.length > 0) {
          deckDocParts.push(
            `Read more: ${pDeck.readMoreLinks.map((l) => `[${l.label}](${l.url})`).join(' · ')}`,
          )
        }

        this.decks.set(subDeckId, {
          id: subDeckId,
          user_id: uid,
          name: pDeck.name,
          parent_id: partDeckId,
          desired_retention_override: null,
          default_priority: 84 - partIdx,
          position: deckIdx,
          target_event_date: null,
          target_event_title: null,
          documentation: deckDocParts.join('\n\n') || null,
          thematic_nature: `${part.partTitle} · ${pDeck.name}`,
          source_documents: pDeck.readMoreLinks.map((l) => ({ title: l.label, url: l.url })),
          created_at: isoNow,
        })

        const subNodeId = newId('node')
        this.treeNodes.set(subNodeId, {
          id: subNodeId,
          user_id: uid,
          parent_id: partNodeId,
          kind: 'deck',
          title: pDeck.name,
          position: deckIdx,
          collapsed: false,
          priority: 84 - partIdx,
          priority_inherited: true,
          deck_id: subDeckId,
          source_id: null,
          extract_id: null,
          requires_node_id: null,
          mastery_threshold: 0.8,
        })
      })

      // Track per-deck card ordering so cards always review in study-guide sequence
      const positionByDeck = new Map<string, number>()

      for (const guideCard of part.cards) {
        const targetDeckId = deckIdByName.get(guideCard.deckName) ?? partDeckId
        const pos = positionByDeck.get(targetDeckId) ?? 0
        positionByDeck.set(targetDeckId, pos + 1)

        const primaryChapterNum = guideCard.chapterNumbers[0]
        const chapter = primaryChapterNum ? course.chaptersByNumber.get(primaryChapterNum) : undefined
        const fields = buildSeedCardFields(guideCard, chapter)

        const cid = newId('card')
        const nid = newId('note')
        this.cards.set(cid, {
          id: cid,
          user_id: uid,
          note_id: nid,
          deck_id: targetDeckId,
          template_slot: 'front_back',
          template_kind: fields.template_kind,
          grading_profile: fields.grading_profile,
          state: 'new',
          due: null,
          stability: null,
          difficulty: null,
          priority: 82,
          lapse_count: 0,
          leech_flag: false,
          suspended: false,
          tags: fields.tags,
          front: fields.front,
          back: fields.back,
          image: null,
          back_image: null,
          occlusion: null,
          references: fields.references,
          starter_code: fields.starter_code,
          starter_tests: null,
          test_cases: [],
          time_complexity: null,
          space_complexity: null,
          edge_cases: fields.edge_cases,
          title: fields.title,
          difficulty_label: fields.difficulty_label,
          category: fields.category,
          documentation: fields.documentation,
          thematic_nature: fields.thematic_nature,
          source_documents: guideCard.docLinks.map((d) => ({ title: d.label, url: d.url })),
          lexicon_glosses: fields.lexicon_glosses,
          position: pos,
          memory_note: null,
          active_weaknesses: [],
          weakness_history: [],
          failure_reminder: null,
          last_grade: null,
          review_count: 0,
          is_schema_checkpoint: pos === 0,
          spatial_x: 120 + (pos % 6) * 140,
          spatial_y: 120 + Math.floor(pos / 6) * 110,
          spatial_locus: null,
          mnemonic_vignette: null,
          created_at: isoNow,
        })
      }
    })
  }

  getUserDecks(userId: string): DeckRecord[] {
    return Array.from(this.decks.values())
      .filter((d) => d.user_id === userId)
      .sort((a, b) => a.position - b.position || a.name.localeCompare(b.name))
  }

  getUserCards(userId: string): CardRecord[] {
    return Array.from(this.cards.values())
      .filter((c) => c.user_id === userId)
      .sort((a, b) => a.position - b.position || a.created_at.localeCompare(b.created_at))
  }

  getDescendantDeckIds(userId: string, rootDeckId: string): Set<string> {
    const all = this.getUserDecks(userId)
    const set = new Set<string>([rootDeckId])
    let added = true
    while (added) {
      added = false
      for (const d of all) {
        if (d.parent_id && set.has(d.parent_id) && !set.has(d.id)) {
          set.add(d.id)
          added = true
        }
      }
    }
    return set
  }

  isCardDue(card: CardRecord, nowMs = Date.now()): boolean {
    if (card.suspended) return false
    if (card.state === 'new') return false
    if (!card.due) return true
    return new Date(card.due).getTime() <= nowMs
  }

  serializeCard(card: CardRecord) {
    const deck = this.decks.get(card.deck_id)
    return {
      id: card.id,
      note_id: card.note_id,
      deck_id: card.deck_id,
      deck_name: deck?.name ?? null,
      template_slot: card.template_slot,
      state: card.state,
      due: card.due,
      stability: card.stability,
      difficulty: card.difficulty,
      priority: card.priority,
      lapse_count: card.lapse_count,
      leech_flag: card.leech_flag,
      suspended: card.suspended,
      tags: card.tags,
      front: card.front,
      back: card.back,
      image: card.image,
      back_image: card.back_image,
      occlusion: card.occlusion,
      documentation: card.documentation,
      thematic_nature: card.thematic_nature,
      source_documents: card.source_documents,
      lexicon_glosses: card.lexicon_glosses,
      position: card.position,
      is_schema_checkpoint: card.is_schema_checkpoint,
      spatial_x: card.spatial_x,
      spatial_y: card.spatial_y,
      spatial_locus: card.spatial_locus,
      mnemonic_vignette: card.mnemonic_vignette,
    }
  }

  serializeQueueCard(card: CardRecord) {
    const deck = this.decks.get(card.deck_id)
    const r = computeRetrievability(card)
    return {
      kind: 'card' as const,
      id: card.id,
      deck_or_source_id: card.deck_id,
      front: card.front,
      back: card.back,
      extract_content: null,
      priority: card.priority,
      effective_priority: card.priority,
      deck_name: deck?.name ?? null,
      source_title: null,
      state: card.state,
      template_kind: card.template_kind,
      grading_profile: card.grading_profile,
      note_id: card.note_id,
      occlusion: card.occlusion,
      image: card.image,
      back_image: card.back_image,
      references: card.references,
      starter_code: card.starter_code,
      starter_tests: card.starter_tests,
      test_cases: card.test_cases,
      time_complexity: card.time_complexity,
      space_complexity: card.space_complexity,
      edge_cases: card.edge_cases,
      title: card.title,
      difficulty: card.difficulty_label,
      category: card.category,
      active_weaknesses: card.active_weaknesses,
      weakness_history: card.weakness_history,
      failure_reminder: card.failure_reminder,
      deck_documentation: deck?.documentation ?? null,
      deck_thematic_nature: deck?.thematic_nature ?? null,
      deck_source_documents: deck?.source_documents ?? [],
      card_documentation: card.documentation,
      card_thematic_nature: card.thematic_nature,
      card_source_documents: card.source_documents,
      lexicon_glosses: card.lexicon_glosses,
      position: card.position,
      stability: card.stability,
      retrievability: r,
      fsrs_difficulty: card.difficulty,
      last_grade: card.last_grade,
      review_count: card.review_count,
      lapses: card.lapse_count,
      is_schema_checkpoint: card.is_schema_checkpoint,
      spatial_x: card.spatial_x,
      spatial_y: card.spatial_y,
      spatial_locus: card.spatial_locus,
      mnemonic_vignette: card.mnemonic_vignette,
    }
  }

  serializeQueueExtract(ext: ExtractRecord) {
    const src = this.sources.get(ext.source_id)
    return {
      kind: 'extract' as const,
      id: ext.id,
      deck_or_source_id: ext.source_id,
      front: null,
      back: null,
      extract_content: ext.content,
      priority: ext.priority,
      effective_priority: ext.priority,
      deck_name: null,
      source_title: src?.title ?? null,
      state: ext.status,
      template_kind: null,
      grading_profile: null,
      note_id: null,
      occlusion: null,
      references: [],
    }
  }

  computeDeckStats(userId: string, deckId: string) {
    const deck = this.decks.get(deckId)
    const ids = this.getDescendantDeckIds(userId, deckId)
    const cards = this.getUserCards(userId).filter((c) => ids.has(c.deck_id) && !c.suspended)
    const nowMs = Date.now()
    const total = cards.length
    const newCards = cards.filter((c) => c.state === 'new').length
    const learningCards = cards.filter((c) => c.state === 'learning' || c.state === 'relearning').length
    const reviewCards = cards.filter((c) => c.state === 'review').length
    const dueCards = cards.filter((c) => this.isCardDue(c, nowMs)).length
    const viewedCards = total - newCards

    const cardIds = new Set(cards.map((c) => c.id))
    const logs = this.reviewLogs.filter((l) => l.user_id === userId && cardIds.has(l.card_id))
    const ratingCounts: Record<string, number> = { again: 0, hard: 0, good: 0, easy: 0 }
    for (const l of logs) ratingCounts[l.final_grade] = (ratingCounts[l.final_grade] ?? 0) + 1
    const totalReviews = logs.length
    const ratingProportions: Record<string, number> = {}
    for (const k of ['again', 'hard', 'good', 'easy']) {
      ratingProportions[k] = totalReviews > 0 ? Number((ratingCounts[k] / totalReviews).toFixed(3)) : 0
    }

    const diffCounts: Record<string, number> = { easy: 0, medium: 0, hard: 0 }
    for (const c of cards) {
      const d = c.difficulty ?? 5
      if (d <= 3.5) diffCounts.easy++
      else if (d <= 6.5) diffCounts.medium++
      else diffCounts.hard++
    }
    const diffProps: Record<string, number> = {}
    for (const k of ['easy', 'medium', 'hard']) {
      diffProps[k] = total > 0 ? Number((diffCounts[k] / total).toFixed(3)) : 0
    }

    return {
      id: deckId,
      name: deck?.name ?? '',
      total_cards: total,
      viewed_cards: viewedCards,
      new_cards: newCards,
      learning_cards: learningCards,
      review_cards: reviewCards,
      due_cards: dueCards,
      viewed_ratio: total > 0 ? Number((viewedCards / total).toFixed(3)) : 0,
      difficulty_counts: diffCounts,
      difficulty_proportions: diffProps,
      rating_counts: ratingCounts,
      rating_proportions: ratingProportions,
      total_reviews: totalReviews,
    }
  }

  serializeDeck(userId: string, deck: DeckRecord) {
    const ownCards = this.getUserCards(userId).filter((c) => c.deck_id === deck.id && !c.suspended)
    const allIds = this.getDescendantDeckIds(userId, deck.id)
    const allCards = this.getUserCards(userId).filter((c) => allIds.has(c.deck_id) && !c.suspended)
    const nowMs = Date.now()
    return {
      id: deck.id,
      name: deck.name,
      parent_id: deck.parent_id,
      desired_retention_override: deck.desired_retention_override,
      default_priority: deck.default_priority,
      position: deck.position,
      card_count: ownCards.length,
      due_count: ownCards.filter((c) => this.isCardDue(c, nowMs)).length,
      new_count: ownCards.filter((c) => c.state === 'new').length,
      total_card_count: allCards.length,
      total_due_count: allCards.filter((c) => this.isCardDue(c, nowMs)).length,
      total_new_count: allCards.filter((c) => c.state === 'new').length,
      target_event_date: deck.target_event_date,
      target_event_title: deck.target_event_title,
      documentation: deck.documentation,
      thematic_nature: deck.thematic_nature,
      source_documents: deck.source_documents,
      stats: this.computeDeckStats(userId, deck.id),
    }
  }

  getBranchDeckAndSourceIds(userId: string, branchNodeId: string): { deckIds: Set<string>; sourceIds: Set<string> } {
    const allNodes = Array.from(this.treeNodes.values()).filter((n) => n.user_id === userId)
    const nodeIds = new Set<string>([branchNodeId])
    let added = true
    while (added) {
      added = false
      for (const n of allNodes) {
        if (n.parent_id && nodeIds.has(n.parent_id) && !nodeIds.has(n.id)) {
          nodeIds.add(n.id)
          added = true
        }
      }
    }
    const deckIds = new Set<string>()
    const sourceIds = new Set<string>()
    for (const nid of nodeIds) {
      const n = this.treeNodes.get(nid)
      if (!n) continue
      if (n.deck_id) {
        for (const did of this.getDescendantDeckIds(userId, n.deck_id)) deckIds.add(did)
      }
      if (n.source_id) sourceIds.add(n.source_id)
    }
    return { deckIds, sourceIds }
  }

  buildQueueSession(userId: string, branch?: string | null, deck?: string | null) {
    const user = this.users.get(userId)!
    const cfg = this.queueConfigs.get(userId) ?? {
      review_weight: 0.6,
      new_weight: 0.25,
      ir_weight: 0.15,
      seconds_per_review: 30,
      seconds_per_ir_extract: 90,
    }
    let cards = this.getUserCards(userId).filter((c) => !c.suspended)
    let extracts = Array.from(this.extracts.values()).filter(
      (e) =>
        e.user_id === userId &&
        e.status === 'active' &&
        (this.sources.get(e.source_id)?.for_reading ?? true) &&
        (!e.next_shown_at || new Date(e.next_shown_at).getTime() <= Date.now()),
    )

    if (deck) {
      const deckIds = this.getDescendantDeckIds(userId, deck)
      cards = cards.filter((c) => deckIds.has(c.deck_id))
      extracts = []
    } else if (branch) {
      const { deckIds, sourceIds } = this.getBranchDeckAndSourceIds(userId, branch)
      cards = cards.filter((c) => deckIds.has(c.deck_id))
      extracts = extracts.filter((e) => sourceIds.has(e.source_id))
    }

    const nowMs = Date.now()
    const dueCards = cards
      .filter((c) => this.isCardDue(c, nowMs))
      .sort((a, b) => b.priority - a.priority || (a.due ?? '').localeCompare(b.due ?? ''))
      .slice(0, user.daily_review_limit)

    const newCards = cards
      .filter((c) => c.state === 'new')
      .sort((a, b) => b.priority - a.priority || a.position - b.position)
      .slice(0, user.daily_new_limit)

    const sortedExtracts = extracts.sort((a, b) => b.priority - a.priority).slice(0, 10)

    const items = [
      ...dueCards.map((c) => this.serializeQueueCard(c)),
      ...newCards.map((c) => this.serializeQueueCard(c)),
      ...sortedExtracts.map((e) => this.serializeQueueExtract(e)),
    ]

    return {
      counts: {
        due: dueCards.length,
        new: newCards.length,
        extracts: sortedExtracts.length,
        total: items.length,
      },
      caps: {
        daily_new_limit: user.daily_new_limit,
        daily_review_limit: user.daily_review_limit,
      },
      budget_seconds: user.queue_time_budget_minutes * 60,
      notes: items.length === 0 ? ['Queue complete! Add cards or explore Code Lab.'] : [],
      items,
    }
  }

  buildTree(userId: string) {
    const allNodes = Array.from(this.treeNodes.values()).filter((n) => n.user_id === userId)
    const byParent = new Map<string | null, TreeNodeRecord[]>()
    for (const n of allNodes) {
      const key = n.parent_id ?? null
      if (!byParent.has(key)) byParent.set(key, [])
      byParent.get(key)!.push(n)
    }
    for (const list of byParent.values()) {
      list.sort((a, b) => a.position - b.position || a.title.localeCompare(b.title))
    }

    const allCards = this.getUserCards(userId).filter((c) => !c.suspended)
    const allExtracts = Array.from(this.extracts.values()).filter(
      (e) => e.user_id === userId && e.status === 'active',
    )
    const nowMs = Date.now()

    interface BuiltNode {
      id: string
      parent_id: string | null
      kind: TreeNodeRecord['kind']
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
      mastery_pct: number
      locked: boolean
      requires_node_id: string | null
      requires_title: string | null
      mastery_threshold: number
      children: BuiltNode[]
    }

    const masteryMap = new Map<string, number>()

    const buildRec = (rec: TreeNodeRecord): BuiltNode => {
      const children = (byParent.get(rec.id) ?? []).map(buildRec)
      let cardCount = 0
      let dueCount = 0
      let newCount = 0
      let extractCount = 0
      let masteredCards = 0

      if (rec.deck_id) {
        const own = allCards.filter((c) => c.deck_id === rec.deck_id)
        cardCount += own.length
        dueCount += own.filter((c) => this.isCardDue(c, nowMs)).length
        newCount += own.filter((c) => c.state === 'new').length
        masteredCards += own.filter((c) => c.state === 'review' && (c.stability ?? 0) >= 3).length
      }
      if (rec.source_id) {
        extractCount += allExtracts.filter((e) => e.source_id === rec.source_id).length
      }

      for (const ch of children) {
        cardCount += ch.card_count
        dueCount += ch.due_count
        newCount += ch.new_count
        extractCount += ch.extract_count
        masteredCards += Math.round((ch.mastery_pct / 100) * ch.card_count)
      }

      const masteryPct = cardCount > 0 ? Math.round((masteredCards / cardCount) * 100) : 0
      masteryMap.set(rec.id, masteryPct)

      return {
        id: rec.id,
        parent_id: rec.parent_id,
        kind: rec.kind,
        title: rec.title,
        position: rec.position,
        collapsed: rec.collapsed,
        priority: rec.priority,
        priority_inherited: rec.priority_inherited,
        card_count: cardCount,
        due_count: dueCount,
        new_count: newCount,
        extract_count: extractCount,
        deck_id: rec.deck_id,
        source_id: rec.source_id,
        extract_id: rec.extract_id,
        mastery_pct: masteryPct,
        locked: false,
        requires_node_id: rec.requires_node_id,
        requires_title: rec.requires_node_id ? this.treeNodes.get(rec.requires_node_id)?.title ?? null : null,
        mastery_threshold: rec.mastery_threshold,
        children,
      }
    }

    const roots = (byParent.get(null) ?? []).map(buildRec)

    const applyLocks = (node: BuiltNode) => {
      if (node.requires_node_id) {
        const reqMastery = masteryMap.get(node.requires_node_id) ?? 0
        node.locked = reqMastery < node.mastery_threshold * 100
      }
      for (const ch of node.children) applyLocks(ch)
    }
    for (const r of roots) applyLocks(r)

    return { nodes: roots }
  }

  scanInterference(userId: string) {
    const cards = this.getUserCards(userId).filter((c) => !c.suspended)
    let pairsFound = 0
    const byKind: Record<string, number> = { interference: 0, duplicate: 0, convergent: 0 }

    for (let i = 0; i < cards.length; i++) {
      for (let j = i + 1; j < cards.length; j++) {
        const a = cards[i]
        const b = cards[j]
        const fSim = jaccardSimilarity(a.front, b.front)
        const bSim = jaccardSimilarity(a.back, b.back)
        let kind: SisterPairRecord['kind'] | null = null
        if (fSim >= 0.6 && bSim >= 0.6) kind = 'duplicate'
        else if (fSim >= 0.35 && bSim < 0.5) kind = 'interference'
        else if (bSim >= 0.45 && fSim < 0.4) kind = 'convergent'
        if (!kind) continue

        const exists = Array.from(this.sisterPairs.values()).some(
          (p) =>
            p.user_id === userId &&
            ((p.note_a_id === a.note_id && p.note_b_id === b.note_id) ||
              (p.note_a_id === b.note_id && p.note_b_id === a.note_id)),
        )
        if (!exists) {
          const id = newId('pair')
          this.sisterPairs.set(id, {
            id,
            user_id: userId,
            kind,
            status: 'active',
            front_similarity: Number(fSim.toFixed(2)),
            back_similarity: Number(bSim.toFixed(2)),
            note_a_id: a.note_id,
            note_b_id: b.note_id,
            front_a: a.front,
            back_a: a.back,
            front_b: b.front,
            back_b: b.back,
          })
          pairsFound++
          byKind[kind] = (byKind[kind] ?? 0) + 1
        }
      }
    }

    return { notes_scanned: cards.length, pairs_found: pairsFound, by_kind: byKind }
  }
}

export const store = new MemoryStore()
