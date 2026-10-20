const STORAGE_PREFIX = 'memorization.allCardsRunProgress.'

export interface AllCardsRunProgress {
  deckId: string
  deckName: string
  index: number // 0-based
  total: number
  cardId?: string
  updatedAt: number
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
  },
}

export function getAllCardsRunProgress(deckId: string): AllCardsRunProgress | null {
  if (!deckId) return null
  try {
    const key = STORAGE_PREFIX + deckId
    const raw = typeof localStorage !== 'undefined' ? localStorage.getItem(key) : null
    if (raw) {
      const parsed = JSON.parse(raw) as AllCardsRunProgress
      if (typeof parsed?.index === 'number') {
        return parsed
      }
    }
    // Check seed fallback
    if (SEED_SESSIONS[deckId]) {
      const seed = SEED_SESSIONS[deckId]
      if (typeof localStorage !== 'undefined') {
        localStorage.setItem(key, JSON.stringify(seed))
      }
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
    const key = STORAGE_PREFIX + progress.deckId
    if (typeof localStorage !== 'undefined') {
      localStorage.setItem(key, JSON.stringify(progress))
    }
    if (typeof window !== 'undefined') {
      window.dispatchEvent(
        new CustomEvent('allCardsRunProgressChanged', { detail: progress })
      )
    }
  } catch (err) {
    console.error('Failed to save All Cards Run progress to localStorage:', err)
  }
}

export function clearAllCardsRunProgress(deckId: string): void {
  if (!deckId) return
  try {
    const key = STORAGE_PREFIX + deckId
    if (typeof localStorage !== 'undefined') {
      localStorage.removeItem(key)
    }
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
