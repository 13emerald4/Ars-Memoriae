/**
 * Pure Persist Mode queue helpers ensuring chronological card progression
 * (e.g., starting at card #3 advances to #4 → #5 → ... → #N → #1 → #2)
 * while keeping non-Easy cards in rotation until mastered.
 */

export interface OrderedCardRef {
  id: string
  position?: number | null
}

/**
 * Sorts cards into canonical chronological deck order:
 * explicit ascending `position` first, preserving original order as tie-breaker.
 */
export function sortCardsChronologically<T extends OrderedCardRef>(cards: readonly T[]): T[] {
  return cards
    .map((card, index) => ({ card, index }))
    .sort((a, b) => {
      const aPos = a.card.position
      const bPos = b.card.position
      if (aPos != null && bPos != null && aPos !== bPos) {
        return aPos - bPos
      }
      if (aPos != null && bPos == null) return -1
      if (aPos == null && bPos != null) return 1
      return a.index - b.index
    })
    .map((entry) => entry.card)
}

/**
 * Builds a chronological Persist Mode queue starting at `startCardId` (if present),
 * continuing forward through the end of the deck and wrapping around to the start.
 * Cards in `graspedIds` are excluded, except `startCardId` when explicitly chosen.
 */
export function buildChronologicalPersistQueue(
  orderedCards: readonly OrderedCardRef[],
  startCardId?: string | null,
  graspedIds?: ReadonlySet<string>,
): string[] {
  if (orderedCards.length === 0) return []

  const startIndex = startCardId
    ? orderedCards.findIndex((c) => c.id === startCardId)
    : 0
  const pivot = startIndex >= 0 ? startIndex : 0

  const rotated = [
    ...orderedCards.slice(pivot),
    ...orderedCards.slice(0, pivot),
  ]

  return rotated
    .filter((card) => {
      if (startCardId && card.id === startCardId) return true
      return !graspedIds?.has(card.id)
    })
    .map((card) => card.id)
}

/**
 * Advances the Persist Mode queue after a card is rated:
 * - `easy`: card is grasped and removed from the pending rotation.
 * - `again` | `hard` | `good`: card moves to the back of the rotation so the
 *   next chronological pending card is shown immediately.
 */
export function advancePersistQueue(
  pendingQueue: readonly string[],
  cardId: string,
  grade: 'again' | 'hard' | 'good' | 'easy',
): string[] {
  const rest = pendingQueue.filter((id) => id !== cardId)
  if (grade === 'easy') {
    return rest
  }
  return [...rest, cardId]
}
