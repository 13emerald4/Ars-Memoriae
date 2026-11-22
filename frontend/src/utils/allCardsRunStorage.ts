import { storage } from './storage'
const STORAGE_PREFIX = 'memorization.allCardsRunProgress.'

export interface AllCardsRunProgress {
  deckId: string
  deckName: string
  index: number // 0-based
  total: number
  cardId?: string
  updatedAt: number
  order?: 'curriculum' | 'difficulty'
}

// Initial session seed for current active run (SPAN321_Exam1_P1_Highest at Card 6 of 20)
const SEED_SESSIONS: Record<string, AllCardsRunProgress> = {
  '5ec8c266-b541-4a3e-bce1-1bd0f0f148ff': {
    deckId: '5ec8c266-b541-4a3e-bce1-1bd0f0f148ff',
    deckName: 'SPAN321_Exam1_P1_Highest',
    index: 5, // 0-based index for Card 6
    total: 20,
    cardId: '4308e4e0-1826-4b06-aa0a-d3653eec6695',
    updatedAt: Date.now(),
    order: 'curriculum',
  },
}

export function getAllCardsRunProgress(deckId: string, order?: string): AllCardsRunProgress | null {
  if (!deckId) return null
  try {
    const key = order ? `${STORAGE_PREFIX}${deckId}_${order}` : `${STORAGE_PREFIX}${deckId}`
    let raw = storage.get(key)
    if (!raw && order) {
      // Fallback to legacy un-suffixed key if matching
      raw = storage.get(STORAGE_PREFIX + deckId)
    }
    if (raw) {
      const parsed = JSON.parse(raw) as AllCardsRunProgress
      if (typeof parsed?.index === 'number') {
        return parsed
      }
    }
    // Check seed fallback
    if (SEED_SESSIONS[deckId]) {
      const seed = SEED_SESSIONS[deckId]
      storage.set(key, JSON.stringify(seed))
      return seed
    }
    return null
  } catch (err) {
    console.error('Failed to get All Cards Run progress from localStorage:', err)
    return SEED_SESSIONS[deckId] || null
  }
}

export function saveAllCardsRunProgress(progress: AllCardsRunProgress): void {
  if (!progress.deckId) return
  try {
    const key = progress.order ? `${STORAGE_PREFIX}${progress.deckId}_${progress.order}` : `${STORAGE_PREFIX}${progress.deckId}`
    storage.set(key, JSON.stringify(progress))
    // Also set legacy un-suffixed key for backwards compatibility
    storage.set(STORAGE_PREFIX + progress.deckId, JSON.stringify(progress))
    if (typeof window !== 'undefined') {
      window.dispatchEvent(
        new CustomEvent('allCardsRunProgressChanged', { detail: progress })
      )
    }
  } catch (err) {
    console.error('Failed to save All Cards Run progress to localStorage:', err)
  }
}

export function clearAllCardsRunProgress(deckId: string, order?: string): void {
  if (!deckId) return
  try {
    if (order) {
      storage.remove(`${STORAGE_PREFIX}${deckId}_${order}`)
    }
    storage.remove(STORAGE_PREFIX + deckId)
    // Also remove from in-memory seed so it doesn't resurrect once completed or explicitly restarted
    delete SEED_SESSIONS[deckId]
    if (typeof window !== 'undefined') {
      window.dispatchEvent(
        new CustomEvent('allCardsRunProgressChanged', { detail: { deckId, index: 0, cleared: true } })
      )
    }
  } catch (err) {
    console.error('Failed to clear All Cards Run progress from localStorage:', err)
  }
}
