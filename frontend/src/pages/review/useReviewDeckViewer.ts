import { useCallback, useState } from 'react'
import type { Deck, QueueItem } from '../../api/types'
import { runViewTransition } from '../../utils/viewTransition'

export interface UseReviewDeckViewerParams {
  item: QueueItem | null
  deckParam: string | null
  persistDeckId: string | null
  allDecks: Deck[]
}

/**
 * Coordinates the All Cards Viewer modal lifecycle inside Review,
 * keeping manual "← Back to All Cards" navigation available without
 * auto-interrupting review progression when a card is completed.
 */
export function useReviewDeckViewer({
  item,
  deckParam,
  persistDeckId,
  allDecks,
}: UseReviewDeckViewerParams) {
  const [deckViewerOpen, setDeckViewerOpen] = useState(false)

  // Tracks whether the user entered this study session from the All Cards Viewer
  // so the manual "← Back to All Cards" button stays visible in the header.
  const [openedFromDeckViewer, setOpenedFromDeckViewer] = useState<boolean>(() => {
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

  const openDeckViewer = useCallback(() => {
    const resolvedDeckId =
      (item?.kind === 'card' ? item.deck_or_source_id : null) ||
      deckParam ||
      persistDeckId ||
      lastStudiedDeckId ||
      allDecks.find((d) => d.card_count > 0)?.id ||
      null
    runViewTransition(() => {
      if (item?.kind === 'card') {
        setLastStudiedCardId(item.id)
      }
      if (resolvedDeckId) {
        setLastStudiedDeckId(resolvedDeckId)
      }
      setDeckViewerOpen(true)
    })
  }, [item, deckParam, persistDeckId, lastStudiedDeckId, allDecks])

  const closeDeckViewer = useCallback(() => {
    runViewTransition(() => {
      setDeckViewerOpen(false)
      setLastStudiedCardId(null)
      setLastStudiedDeckId(null)
    })
  }, [])

  const toggleDeckViewer = useCallback(() => {
    runViewTransition(() => {
      setDeckViewerOpen((prev) => !prev)
    })
  }, [])

  const markStudiedFromViewer = useCallback(
    (selectedCard: QueueItem) => {
      runViewTransition(() => {
        setLastStudiedCardId(selectedCard.id)
        setLastStudiedDeckId(selectedCard.deck_or_source_id || deckParam || persistDeckId || null)
        setOpenedFromDeckViewer(true)
        setDeckViewerOpen(false)
      })
    },
    [deckParam, persistDeckId],
  )

  return {
    deckViewerOpen,
    setDeckViewerOpen,
    openedFromDeckViewer,
    lastStudiedCardId,
    lastStudiedDeckId,
    openDeckViewer,
    closeDeckViewer,
    toggleDeckViewer,
    markStudiedFromViewer,
  }
}
