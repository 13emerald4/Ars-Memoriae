import React, { useCallback, useEffect, useState } from 'react'
import {
  ActivityIndicator,
  RefreshControl,
  ScrollView,
  StyleSheet,
  Text,
  TouchableOpacity,
  View,
} from 'react-native'
import { ReviewCard } from '../components/ReviewCard'
import { mobileApi } from '../services/api'
import { storage } from '../services/storage'
import { mobileSync } from '../services/sync'
import type { Grade, QueueItem } from '../types'

interface ReviewScreenProps {
  onOpenPairing: () => void
}

export function ReviewScreen({ onOpenPairing }: ReviewScreenProps) {
  const [queueItem, setQueueItem] = useState<QueueItem | null>(null)
  const [loading, setLoading] = useState(true)
  const [refreshing, setRefreshing] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const loadNext = useCallback(async () => {
    setError(null)
    const config = await storage.getPairingConfig()
    if (!config) {
      setLoading(false)
      return
    }

    try {
      const item = await mobileApi.fetchNextQueueItem()
      setQueueItem(item)
    } catch (err: any) {
      setError(err.message || 'Failed to fetch next card.')
    } finally {
      setLoading(false)
      setRefreshing(false)
    }
  }, [])

  useEffect(() => {
    void loadNext()

    // Listen for real-time events that change queue state (e.g. from desktop actions)
    const unsubscribe = mobileSync.subscribe((event) => {
      if (event.type === 'QUEUE_INVALIDATED' || event.type === 'CARD_REVIEWED') {
        // Queue state changed remotely
      }
    })

    return unsubscribe
  }, [loadNext])

  const handleConfirm = async (grade: Grade, typedAnswer: string, latencyMs: number) => {
    if (!queueItem?.card) return
    const cardId = queueItem.card.id

    try {
      // Attempt online confirmation
      await mobileApi.confirmReview(cardId, grade, typedAnswer, latencyMs)
    } catch {
      // Network drop: save review in offline queue for auto-sync later
      await storage.enqueueOfflineReview({
        card_id: cardId,
        final_grade: grade,
        typed_answer: typedAnswer,
        latency_ms: latencyMs,
        reviewed_at: new Date().toISOString(),
      })
    }

    // Immediately load the next card
    await loadNext()
  }

  const handleRefresh = () => {
    setRefreshing(true)
    void loadNext()
  }

  if (loading) {
    return (
      <View style={styles.centerContainer}>
        <ActivityIndicator color="#38bdf8" size="large" />
        <Text style={styles.loadingText}>Loading Priority Queue...</Text>
      </View>
    )
  }

  return (
    <ScrollView
      style={styles.container}
      contentContainerStyle={styles.content}
      refreshControl={<RefreshControl refreshing={refreshing} onRefresh={handleRefresh} tintColor="#38bdf8" />}
    >
      {error && (
        <View style={styles.errorBox}>
          <Text style={styles.errorText}>{error}</Text>
          <TouchableOpacity style={styles.pairLink} onPress={onOpenPairing}>
            <Text style={styles.pairLinkText}>Check Pairing &gt;</Text>
          </TouchableOpacity>
        </View>
      )}

      {queueItem?.card ? (
        <ReviewCard
          card={queueItem.card}
          onConfirm={handleConfirm}
          onSubmitAnswer={(cid, ans, lat) => mobileApi.submitAnswer(cid, ans, lat)}
        />
      ) : queueItem?.extract ? (
        <View style={styles.extractContainer}>
          <Text style={styles.extractBadge}>INCREMENTAL READING</Text>
          <Text style={styles.extractTitle}>{queueItem.extract.title}</Text>
          <Text style={styles.extractContent}>{queueItem.extract.content}</Text>
          <TouchableOpacity style={styles.nextButton} onPress={loadNext}>
            <Text style={styles.nextButtonText}>Next Item →</Text>
          </TouchableOpacity>
        </View>
      ) : (
        <View style={styles.emptyContainer}>
          <Text style={styles.emptyIcon}>🎉</Text>
          <Text style={styles.emptyTitle}>Queue Cleared!</Text>
          <Text style={styles.emptySubtitle}>
            You've completed all due reviews and met your target budget for now.
          </Text>
          <TouchableOpacity style={styles.refreshButton} onPress={handleRefresh}>
            <Text style={styles.refreshButtonText}>Refresh Queue</Text>
          </TouchableOpacity>
        </View>
      )}
    </ScrollView>
  )
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#0f172a',
  },
  content: {
    padding: 16,
    flexGrow: 1,
  },
  centerContainer: {
    flex: 1,
    backgroundColor: '#0f172a',
    justifyContent: 'center',
    alignItems: 'center',
    padding: 20,
  },
  loadingText: {
    marginTop: 12,
    color: '#94a3b8',
    fontSize: 14,
  },
  errorBox: {
    backgroundColor: '#450a0a',
    borderColor: '#ef4444',
    borderWidth: 1,
    borderRadius: 12,
    padding: 14,
    marginBottom: 16,
  },
  errorText: {
    color: '#fca5a5',
    fontSize: 13,
    marginBottom: 6,
  },
  pairLink: {
    alignSelf: 'flex-start',
  },
  pairLinkText: {
    color: '#38bdf8',
    fontWeight: '700',
    fontSize: 12,
  },
  extractContainer: {
    backgroundColor: '#1e293b',
    borderRadius: 16,
    padding: 20,
    borderWidth: 1,
    borderColor: '#334155',
  },
  extractBadge: {
    color: '#a855f7',
    fontSize: 11,
    fontWeight: '800',
    letterSpacing: 1,
    marginBottom: 8,
  },
  extractTitle: {
    fontSize: 18,
    fontWeight: '700',
    color: '#f8fafc',
    marginBottom: 14,
  },
  extractContent: {
    fontSize: 15,
    lineHeight: 24,
    color: '#cbd5e1',
    marginBottom: 20,
  },
  nextButton: {
    backgroundColor: '#a855f7',
    borderRadius: 10,
    paddingVertical: 12,
    alignItems: 'center',
  },
  nextButtonText: {
    color: '#ffffff',
    fontWeight: '700',
    fontSize: 14,
  },
  emptyContainer: {
    alignItems: 'center',
    justifyContent: 'center',
    paddingVertical: 60,
  },
  emptyIcon: {
    fontSize: 48,
    marginBottom: 16,
  },
  emptyTitle: {
    fontSize: 22,
    fontWeight: '800',
    color: '#f8fafc',
    marginBottom: 8,
  },
  emptySubtitle: {
    fontSize: 14,
    color: '#94a3b8',
    textAlign: 'center',
    maxWidth: 280,
    lineHeight: 20,
    marginBottom: 24,
  },
  refreshButton: {
    backgroundColor: '#1e293b',
    borderColor: '#38bdf8',
    borderWidth: 1,
    borderRadius: 12,
    paddingVertical: 12,
    paddingHorizontal: 24,
  },
  refreshButtonText: {
    color: '#38bdf8',
    fontWeight: '700',
    fontSize: 14,
  },
})
