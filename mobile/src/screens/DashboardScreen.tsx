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
import { mobileApi } from '../services/api'
import { storage } from '../services/storage'
import { mobileSync, type SyncConnectionState } from '../services/sync'
import type { QueueItem } from '../types'

interface DashboardScreenProps {
  onStartReview: () => void
  onOpenPairing: () => void
}

export function DashboardScreen({ onStartReview, onOpenPairing }: DashboardScreenProps) {
  const [queueItem, setQueueItem] = useState<QueueItem | null>(null)
  const [offlineCount, setOfflineCount] = useState(0)
  const [connectionState, setConnectionState] = useState<SyncConnectionState>('disconnected')
  const [loading, setLoading] = useState(true)
  const [syncingOffline, setSyncingOffline] = useState(false)
  const [refreshing, setRefreshing] = useState(false)

  const loadData = useCallback(async () => {
    try {
      const [item, offline] = await Promise.all([
        mobileApi.fetchNextQueueItem().catch(() => null),
        storage.getOfflineQueue(),
      ])
      setQueueItem(item)
      setOfflineCount(offline.length)
    } finally {
      setLoading(false)
      setRefreshing(false)
    }
  }, [])

  useEffect(() => {
    void loadData()
    const unsubState = mobileSync.subscribeState(setConnectionState)
    const unsubSync = mobileSync.subscribe((event) => {
      if (event.type === 'CARD_REVIEWED' || event.type === 'QUEUE_INVALIDATED') {
        void loadData()
      }
    })

    return () => {
      unsubState()
      unsubSync()
    }
  }, [loadData])

  const handleFlushOffline = async () => {
    setSyncingOffline(true)
    try {
      await mobileSync.flushOfflineQueue()
      await loadData()
    } finally {
      setSyncingOffline(false)
    }
  }

  const counts = queueItem?.counts || {
    due_cards: 0,
    new_cards: 0,
    ir_extracts: 0,
    total_remaining: 0,
  }

  return (
    <ScrollView
      style={styles.container}
      contentContainerStyle={styles.content}
      refreshControl={<RefreshControl refreshing={refreshing} onRefresh={() => { setRefreshing(true); void loadData() }} tintColor="#38bdf8" />}
    >
      {/* Header Banner */}
      <View style={styles.header}>
        <Text style={styles.title}>Ars Memoriae</Text>
        <TouchableOpacity style={styles.statusPill} onPress={onOpenPairing}>
          <View
            style={[
              styles.statusDot,
              connectionState === 'connected' && styles.statusConnected,
              connectionState === 'connecting' && styles.statusConnecting,
              connectionState === 'disconnected' && styles.statusDisconnected,
            ]}
          />
          <Text style={styles.statusText}>
            {connectionState === 'connected'
              ? 'Real-Time Sync Active'
              : connectionState === 'connecting'
                ? 'Connecting to Host...'
                : 'Offline / Disconnected'}
          </Text>
        </TouchableOpacity>
      </View>

      {/* Offline Pending Reviews Alert */}
      {offlineCount > 0 && (
        <View style={styles.offlineBox}>
          <View style={styles.offlineTextCol}>
            <Text style={styles.offlineTitle}>Offline Reviews Queued</Text>
            <Text style={styles.offlineDesc}>
              {offlineCount} review(s) completed while offline.
            </Text>
          </View>
          <TouchableOpacity
            style={styles.syncNowButton}
            onPress={handleFlushOffline}
            disabled={syncingOffline || connectionState !== 'connected'}
          >
            {syncingOffline ? (
              <ActivityIndicator color="#0f172a" size="small" />
            ) : (
              <Text style={styles.syncNowButtonText}>Sync Now</Text>
            )}
          </TouchableOpacity>
        </View>
      )}

      {/* Main Review CTA Card */}
      <View style={styles.ctaCard}>
        <Text style={styles.ctaLabel}>ACTIVE RECALL WORKBENCH</Text>
        <Text style={styles.ctaTitle}>Daily Memory Priority Queue</Text>
        <Text style={styles.ctaDesc}>
          Ranked by FSRS memory stability and retrieval decay to fit your study budget.
        </Text>
        <TouchableOpacity style={styles.ctaButton} onPress={onStartReview}>
          <Text style={styles.ctaButtonText}>Start Today's Reviews →</Text>
        </TouchableOpacity>
      </View>

      {/* Queue Breakdown Grid */}
      <Text style={styles.sectionTitle}>Queue Composition</Text>
      <View style={styles.grid}>
        <View style={styles.gridCard}>
          <Text style={styles.gridNumber}>{counts.due_cards}</Text>
          <Text style={styles.gridLabel}>Due Cards</Text>
          <Text style={styles.gridSub}>FSRS recall reviews</Text>
        </View>

        <View style={styles.gridCard}>
          <Text style={[styles.gridNumber, { color: '#38bdf8' }]}>{counts.new_cards}</Text>
          <Text style={styles.gridLabel}>New Cards</Text>
          <Text style={styles.gridSub}>Fresh concepts</Text>
        </View>

        <View style={styles.gridCard}>
          <Text style={[styles.gridNumber, { color: '#a855f7' }]}>{counts.ir_extracts}</Text>
          <Text style={styles.gridLabel}>Extracts</Text>
          <Text style={styles.gridSub}>Incremental reading</Text>
        </View>

        <View style={styles.gridCard}>
          <Text style={[styles.gridNumber, { color: '#10b981' }]}>{counts.total_remaining}</Text>
          <Text style={styles.gridLabel}>Total Active</Text>
          <Text style={styles.gridSub}>Session pool</Text>
        </View>
      </View>

      {/* Real-Time Sync Feature Note */}
      <View style={styles.infoBox}>
        <Text style={styles.infoTitle}>⚡ Bi-directional Sync</Text>
        <Text style={styles.infoText}>
          Every typed recall response and grade confirmed on your phone reflects instantly on your desktop
          workspace without refreshing.
        </Text>
      </View>
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
    paddingBottom: 40,
  },
  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 20,
  },
  title: {
    fontSize: 22,
    fontWeight: '800',
    color: '#f8fafc',
  },
  statusPill: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#1e293b',
    borderColor: '#334155',
    borderWidth: 1,
    paddingVertical: 6,
    paddingHorizontal: 10,
    borderRadius: 20,
    gap: 6,
  },
  statusDot: {
    width: 8,
    height: 8,
    borderRadius: 4,
  },
  statusConnected: {
    backgroundColor: '#34d399',
  },
  statusConnecting: {
    backgroundColor: '#f59e0b',
  },
  statusDisconnected: {
    backgroundColor: '#94a3b8',
  },
  statusText: {
    color: '#cbd5e1',
    fontSize: 11,
    fontWeight: '600',
  },
  offlineBox: {
    backgroundColor: '#451a03',
    borderColor: '#f59e0b',
    borderWidth: 1,
    borderRadius: 14,
    padding: 14,
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 16,
  },
  offlineTextCol: {
    flex: 1,
  },
  offlineTitle: {
    color: '#fef3c7',
    fontWeight: '700',
    fontSize: 14,
  },
  offlineDesc: {
    color: '#fde68a',
    fontSize: 12,
    marginTop: 2,
  },
  syncNowButton: {
    backgroundColor: '#f59e0b',
    paddingVertical: 8,
    paddingHorizontal: 14,
    borderRadius: 8,
  },
  syncNowButtonText: {
    color: '#0f172a',
    fontWeight: '800',
    fontSize: 12,
  },
  ctaCard: {
    backgroundColor: '#1e293b',
    borderColor: '#0284c7',
    borderWidth: 1,
    borderRadius: 16,
    padding: 20,
    marginBottom: 24,
  },
  ctaLabel: {
    color: '#38bdf8',
    fontSize: 10,
    fontWeight: '800',
    letterSpacing: 1,
    marginBottom: 6,
  },
  ctaTitle: {
    color: '#f8fafc',
    fontSize: 19,
    fontWeight: '700',
    marginBottom: 6,
  },
  ctaDesc: {
    color: '#94a3b8',
    fontSize: 13,
    lineHeight: 18,
    marginBottom: 16,
  },
  ctaButton: {
    backgroundColor: '#38bdf8',
    borderRadius: 10,
    paddingVertical: 14,
    alignItems: 'center',
  },
  ctaButtonText: {
    color: '#0f172a',
    fontWeight: '800',
    fontSize: 15,
  },
  sectionTitle: {
    color: '#94a3b8',
    fontSize: 12,
    fontWeight: '800',
    letterSpacing: 0.8,
    textTransform: 'uppercase',
    marginBottom: 12,
  },
  grid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 12,
    marginBottom: 20,
  },
  gridCard: {
    width: '48%',
    backgroundColor: '#1e293b',
    borderRadius: 14,
    padding: 14,
    borderWidth: 1,
    borderColor: '#334155',
  },
  gridNumber: {
    color: '#f8fafc',
    fontSize: 24,
    fontWeight: '800',
    marginBottom: 4,
  },
  gridLabel: {
    color: '#cbd5e1',
    fontSize: 13,
    fontWeight: '700',
  },
  gridSub: {
    color: '#64748b',
    fontSize: 11,
    marginTop: 2,
  },
  infoBox: {
    backgroundColor: '#0c1527',
    borderRadius: 12,
    borderWidth: 1,
    borderColor: '#1e3a8a',
    padding: 14,
  },
  infoTitle: {
    color: '#60a5fa',
    fontSize: 13,
    fontWeight: '700',
    marginBottom: 4,
  },
  infoText: {
    color: '#94a3b8',
    fontSize: 12,
    lineHeight: 18,
  },
})
