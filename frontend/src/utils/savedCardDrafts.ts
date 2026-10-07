import type { QueueItem } from '../api/types'

const STORAGE_KEY = 'memorization.savedCardDrafts'

export interface SavedCardDraft {
  cardId: string
  deckId: string | null
  deckName: string | null
  title: string
  frontSnippet: string
  answer: string
  testCode: string
  codeLanguage: string
  savedAt: number
  isCodeCard: boolean
  card: QueueItem
}

export function getSavedDrafts(): Record<string, SavedCardDraft> {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (!raw) return {}
    return JSON.parse(raw) as Record<string, SavedCardDraft>
  } catch (err) {
    console.error('Failed to parse savedCardDrafts from localStorage:', err)
    return {}
  }
}

export function saveDraft(draft: SavedCardDraft): void {
  try {
    const drafts = getSavedDrafts()
    drafts[draft.cardId] = draft
    localStorage.setItem(STORAGE_KEY, JSON.stringify(drafts))
    if (typeof window !== 'undefined') {
      window.dispatchEvent(new CustomEvent('savedCardDraftsChanged'))
    }
  } catch (err) {
    console.error('Failed to save card draft to localStorage:', err)
  }
}

export function removeDraft(cardId: string): void {
  try {
    const drafts = getSavedDrafts()
    if (drafts[cardId]) {
      delete drafts[cardId]
      localStorage.setItem(STORAGE_KEY, JSON.stringify(drafts))
      if (typeof window !== 'undefined') {
        window.dispatchEvent(new CustomEvent('savedCardDraftsChanged'))
      }
    }
  } catch (err) {
    console.error('Failed to remove card draft from localStorage:', err)
  }
}

export function clearAllDrafts(): void {
  try {
    localStorage.removeItem(STORAGE_KEY)
    if (typeof window !== 'undefined') {
      window.dispatchEvent(new CustomEvent('savedCardDraftsChanged'))
    }
  } catch (err) {
    console.error('Failed to clear card drafts from localStorage:', err)
  }
}

export function getDraftForCard(cardId: string): SavedCardDraft | null {
  const drafts = getSavedDrafts()
  return drafts[cardId] || null
}

export function getSavedDraftsCount(): number {
  return Object.keys(getSavedDrafts()).length
}
