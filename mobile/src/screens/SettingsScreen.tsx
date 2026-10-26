import React, { useCallback, useEffect, useState } from 'react'
import {
  Alert,
  ScrollView,
  StyleSheet,
  Text,
  TouchableOpacity,
  View,
} from 'react-native'
import { mobileApi } from '../services/api'
import { storage } from '../services/storage'
import { mobileSync, type SyncConnectionState } from '../services/sync'
import type { PairingConfig, SyncStatus } from '../types'

interface SettingsScreenProps {
  onOpenPairing: () => void
}

export function SettingsScreen({ onOpenPairing }: SettingsScreenProps) {
  const [config, setConfig] = useState<PairingConfig | null>(null)
  const [syncStatus, setSyncStatus] = useState<SyncStatus | null>(null)
  const [connectionState, setConnectionState] = useState<SyncConnectionState>('disconnected')
  const [checking, setChecking] = useState(false)

  const loadData = useCallback(async () => {
    const cfg = await storage.getPairingConfig()
    setConfig(cfg)
    if (cfg) {
      try {
        setChecking(true)
        const s = await mobileApi.fetchSyncStatus()
        setSyncStatus(s)
      } catch {
        setSyncStatus(null)
      } finally {
        setChecking(false)
      }
    }
  }, [])

  useEffect(() => {
    void loadData()
    const unsub = mobileSync.subscribeState(setConnectionState)
    return unsub
  }, [loadData])

  const handleDisconnect = () => {
    Alert.alert(
      'Unpair Mobile Device',
      'Are you sure you want to disconnect from this Ars Memoriae desktop host?',
      [
        { text: 'Cancel', style: 'cancel' },
        {
          text: 'Unpair',
          style: 'destructive',
          onPress: async () => {
            mobileSync.stop()
            await storage.clearPairingConfig()
            await loadData()
          },
        },
      ],
    )
  }

  return (
    <ScrollView style={styles.container} contentContainerStyle={styles.content}>
      <Text style={styles.pageTitle}>Mobile Settings</Text>

      {/* Host Connection Panel */}
      <View style={styles.section}>
        <Text style={styles.sectionHeader}>DESKTOP HOST CONNECTION</Text>

        {config ? (
          <View style={styles.card}>
            <View style={styles.row}>
              <Text style={styles.rowLabel}>Host URL</Text>
              <Text style={styles.rowValue}>{config.server_url}</Text>
            </View>

            <View style={styles.row}>
              <Text style={styles.rowLabel}>Auth Token</Text>
              <Text style={styles.rowValue}>
                {config.token.slice(0, 12)}...{config.token.slice(-6)}
              </Text>
            </View>

            <View style={styles.row}>
              <Text style={styles.rowLabel}>Real-Time WebSocket</Text>
              <View style={styles.statusBadge}>
                <View
                  style={[
                    styles.statusDot,
                    connectionState === 'connected' && styles.statusDotGreen,
                    connectionState === 'connecting' && styles.statusDotYellow,
                    connectionState === 'disconnected' && styles.statusDotRed,
                  ]}
                />
                <Text style={styles.statusBadgeText}>
                  {connectionState.toUpperCase()}
                </Text>
              </View>
            </View>

            {syncStatus && (
              <View style={styles.row}>
                <Text style={styles.rowLabel}>Connected Devices</Text>
                <Text style={styles.rowValue}>
                  {syncStatus.active_connections} active on host
                </Text>
              </View>
            )}

            <View style={styles.actionRow}>
              <TouchableOpacity style={styles.pairButton} onPress={onOpenPairing}>
                <Text style={styles.pairButtonText}>Change Host / QR</Text>
              </TouchableOpacity>

              <TouchableOpacity style={styles.unpairButton} onPress={handleDisconnect}>
                <Text style={styles.unpairButtonText}>Unpair</Text>
              </TouchableOpacity>
            </View>
          </View>
        ) : (
          <View style={styles.card}>
            <Text style={styles.notPairedTitle}>Not Paired to Desktop</Text>
            <Text style={styles.notPairedDesc}>
              Pair with your desktop Ars Memoriae instance to stream flashcards and sync progress in real time.
            </Text>
            <TouchableOpacity style={styles.connectButton} onPress={onOpenPairing}>
              <Text style={styles.connectButtonText}>Pair with Desktop (QR / IP)</Text>
            </TouchableOpacity>
          </View>
        )}
      </View>

      {/* Synchronization Engine Info */}
      <View style={styles.section}>
        <Text style={styles.sectionHeader}>SYNCHRONIZATION ARCHITECTURE</Text>
        <View style={styles.card}>
          <Text style={styles.infoPoint}>
            • <Text style={styles.bold}>FastAPI WebSocket Hub</Text>: Broadcasts card reviews, queue updates, and deck changes over LAN with sub-second latency.
          </Text>
          <Text style={styles.infoPoint}>
            • <Text style={styles.bold}>Offline-First Ledger</Text>: Reviews conducted on cellular or offline are cached locally in SQLite and flushed automatically upon reconnection.
          </Text>
          <Text style={styles.infoPoint}>
            • <Text style={styles.bold}>Deterministic FSRS</Text>: Identical spaced repetition interval scheduling guaranteed across mobile and desktop.
          </Text>
        </View>
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
  pageTitle: {
    fontSize: 24,
    fontWeight: '800',
    color: '#f8fafc',
    marginBottom: 20,
  },
  section: {
    marginBottom: 24,
  },
  sectionHeader: {
    color: '#94a3b8',
    fontSize: 11,
    fontWeight: '800',
    letterSpacing: 1,
    marginBottom: 10,
  },
  card: {
    backgroundColor: '#1e293b',
    borderRadius: 14,
    padding: 16,
    borderWidth: 1,
    borderColor: '#334155',
  },
  row: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingVertical: 10,
    borderBottomWidth: 1,
    borderBottomColor: '#334155',
  },
  rowLabel: {
    color: '#94a3b8',
    fontSize: 13,
  },
  rowValue: {
    color: '#f8fafc',
    fontSize: 13,
    fontWeight: '600',
    fontFamily: 'monospace',
  },
  statusBadge: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
  },
  statusDot: {
    width: 8,
    height: 8,
    borderRadius: 4,
  },
  statusDotGreen: { backgroundColor: '#34d399' },
  statusDotYellow: { backgroundColor: '#f59e0b' },
  statusDotRed: { backgroundColor: '#ef4444' },
  statusBadgeText: {
    color: '#f8fafc',
    fontSize: 11,
    fontWeight: '700',
  },
  actionRow: {
    flexDirection: 'row',
    gap: 12,
    marginTop: 16,
  },
  pairButton: {
    flex: 1,
    backgroundColor: '#0284c7',
    paddingVertical: 12,
    borderRadius: 10,
    alignItems: 'center',
  },
  pairButtonText: {
    color: '#ffffff',
    fontWeight: '700',
    fontSize: 13,
  },
  unpairButton: {
    backgroundColor: '#334155',
    paddingVertical: 12,
    paddingHorizontal: 16,
    borderRadius: 10,
    alignItems: 'center',
  },
  unpairButtonText: {
    color: '#fca5a5',
    fontWeight: '700',
    fontSize: 13,
  },
  notPairedTitle: {
    color: '#f8fafc',
    fontSize: 17,
    fontWeight: '700',
    marginBottom: 6,
  },
  notPairedDesc: {
    color: '#94a3b8',
    fontSize: 13,
    lineHeight: 18,
    marginBottom: 16,
  },
  connectButton: {
    backgroundColor: '#38bdf8',
    borderRadius: 10,
    paddingVertical: 12,
    alignItems: 'center',
  },
  connectButtonText: {
    color: '#0f172a',
    fontWeight: '800',
    fontSize: 14,
  },
  infoPoint: {
    color: '#cbd5e1',
    fontSize: 13,
    lineHeight: 20,
    marginBottom: 10,
  },
  bold: {
    fontWeight: '700',
    color: '#f8fafc',
  },
})
