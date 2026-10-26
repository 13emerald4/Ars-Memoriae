import React, { useEffect, useState } from 'react'
import {
  SafeAreaView,
  StatusBar,
  StyleSheet,
  Text,
  TouchableOpacity,
  View,
} from 'react-native'
import { PairingModal } from './src/components/PairingModal'
import { DashboardScreen } from './src/screens/DashboardScreen'
import { ReviewScreen } from './src/screens/ReviewScreen'
import { SettingsScreen } from './src/screens/SettingsScreen'
import { storage } from './src/services/storage'
import { mobileSync, type SyncConnectionState } from './src/services/sync'

type Tab = 'dashboard' | 'review' | 'settings'

export default function App() {
  const [activeTab, setActiveTab] = useState<Tab>('dashboard')
  const [pairingModalOpen, setPairingModalOpen] = useState(false)
  const [connectionState, setConnectionState] = useState<SyncConnectionState>('disconnected')

  useEffect(() => {
    // Check if device is paired on startup
    void (async () => {
      const config = await storage.getPairingConfig()
      if (config) {
        await mobileSync.start()
      } else {
        // Prompt pairing modal if not yet configured
        setPairingModalOpen(true)
      }
    })()

    const unsubState = mobileSync.subscribeState(setConnectionState)
    return () => {
      unsubState()
      mobileSync.stop()
    }
  }, [])

  return (
    <SafeAreaView style={styles.safeArea}>
      <StatusBar barStyle="light-content" backgroundColor="#0f172a" />

      {/* Top Bar */}
      <View style={styles.topBar}>
        <Text style={styles.brandTitle}>Ars Memoriae</Text>
        <TouchableOpacity
          style={styles.connectionBadge}
          onPress={() => setPairingModalOpen(true)}
        >
          <View
            style={[
              styles.connectionDot,
              connectionState === 'connected' && styles.dotGreen,
              connectionState === 'connecting' && styles.dotYellow,
              connectionState === 'disconnected' && styles.dotRed,
            ]}
          />
          <Text style={styles.connectionText}>
            {connectionState === 'connected'
              ? 'LIVE SYNC'
              : connectionState === 'connecting'
                ? 'CONNECTING'
                : 'OFFLINE'}
          </Text>
        </TouchableOpacity>
      </View>

      {/* Main Tab View */}
      <View style={styles.tabContent}>
        {activeTab === 'dashboard' && (
          <DashboardScreen
            onStartReview={() => setActiveTab('review')}
            onOpenPairing={() => setPairingModalOpen(true)}
          />
        )}
        {activeTab === 'review' && (
          <ReviewScreen onOpenPairing={() => setPairingModalOpen(true)} />
        )}
        {activeTab === 'settings' && (
          <SettingsScreen onOpenPairing={() => setPairingModalOpen(true)} />
        )}
      </View>

      {/* Bottom Navigation Bar */}
      <View style={styles.bottomNav}>
        <TouchableOpacity
          style={[styles.navTab, activeTab === 'dashboard' && styles.navTabActive]}
          onPress={() => setActiveTab('dashboard')}
        >
          <Text style={[styles.navIcon, activeTab === 'dashboard' && styles.navTextActive]}>
            📊
          </Text>
          <Text style={[styles.navLabel, activeTab === 'dashboard' && styles.navTextActive]}>
            Overview
          </Text>
        </TouchableOpacity>

        <TouchableOpacity
          style={[styles.navTab, activeTab === 'review' && styles.navTabActive]}
          onPress={() => setActiveTab('review')}
        >
          <Text style={[styles.navIcon, activeTab === 'review' && styles.navTextActive]}>
            🧠
          </Text>
          <Text style={[styles.navLabel, activeTab === 'review' && styles.navTextActive]}>
            Study
          </Text>
        </TouchableOpacity>

        <TouchableOpacity
          style={[styles.navTab, activeTab === 'settings' && styles.navTabActive]}
          onPress={() => setActiveTab('settings')}
        >
          <Text style={[styles.navIcon, activeTab === 'settings' && styles.navTextActive]}>
            ⚙️
          </Text>
          <Text style={[styles.navLabel, activeTab === 'settings' && styles.navTextActive]}>
            Settings
          </Text>
        </TouchableOpacity>
      </View>

      {/* 1-Click QR Pairing Modal */}
      <PairingModal
        visible={pairingModalOpen}
        onClose={() => setPairingModalOpen(false)}
        onPaired={() => {
          setActiveTab('dashboard')
        }}
      />
    </SafeAreaView>
  )
}

const styles = StyleSheet.create({
  safeArea: {
    flex: 1,
    backgroundColor: '#0f172a',
  },
  topBar: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingHorizontal: 16,
    paddingVertical: 12,
    borderBottomWidth: 1,
    borderBottomColor: '#1e293b',
    backgroundColor: '#0f172a',
  },
  brandTitle: {
    color: '#f8fafc',
    fontSize: 18,
    fontWeight: '800',
    letterSpacing: 0.5,
  },
  connectionBadge: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
    backgroundColor: '#1e293b',
    paddingVertical: 5,
    paddingHorizontal: 10,
    borderRadius: 20,
    borderWidth: 1,
    borderColor: '#334155',
  },
  connectionDot: {
    width: 7,
    height: 7,
    borderRadius: 4,
  },
  dotGreen: { backgroundColor: '#34d399' },
  dotYellow: { backgroundColor: '#f59e0b' },
  dotRed: { backgroundColor: '#ef4444' },
  connectionText: {
    color: '#cbd5e1',
    fontSize: 10,
    fontWeight: '800',
    letterSpacing: 0.5,
  },
  tabContent: {
    flex: 1,
  },
  bottomNav: {
    flexDirection: 'row',
    height: 60,
    borderTopWidth: 1,
    borderTopColor: '#1e293b',
    backgroundColor: '#090d16',
    justifyContent: 'space-around',
    alignItems: 'center',
  },
  navTab: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    paddingVertical: 6,
  },
  navTabActive: {
    borderTopWidth: 2,
    borderTopColor: '#38bdf8',
  },
  navIcon: {
    fontSize: 18,
    marginBottom: 2,
  },
  navLabel: {
    color: '#64748b',
    fontSize: 11,
    fontWeight: '700',
  },
  navTextActive: {
    color: '#38bdf8',
  },
})
