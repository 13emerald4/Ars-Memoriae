import React, { useState } from 'react'
import {
  ActivityIndicator,
  Modal,
  StyleSheet,
  Text,
  TextInput,
  TouchableOpacity,
  View,
} from 'react-native'
import { storage } from '../services/storage'
import { mobileSync } from '../services/sync'

interface PairingModalProps {
  visible: boolean
  onClose: () => void
  onPaired: () => void
}

export function PairingModal({ visible, onClose, onPaired }: PairingModalProps) {
  const [serverUrl, setServerUrl] = useState('http://192.168.1.')
  const [token, setToken] = useState('')
  const [qrJson, setQrJson] = useState('')
  const [loading, setLoading] = useState(false)
  const [errorMessage, setErrorMessage] = useState<string | null>(null)

  const handleQuickPasteJson = (text: string) => {
    setQrJson(text)
    try {
      const parsed = JSON.parse(text)
      if (parsed.server_url) setServerUrl(parsed.server_url)
      if (parsed.token) setToken(parsed.token)
      setErrorMessage(null)
    } catch {
      // not valid JSON yet
    }
  }

  const handlePair = async () => {
    setErrorMessage(null)
    const cleanUrl = serverUrl.trim().replace(/\/+$/, '')
    const cleanToken = token.trim()

    if (!cleanUrl || !cleanToken) {
      setErrorMessage('Please provide both the Server URL and Auth Token.')
      return
    }

    setLoading(true)
    try {
      // Validate endpoint and token
      const res = await fetch(`${cleanUrl}/api/sync/status`, {
        headers: { Authorization: `Bearer ${cleanToken}` },
      })
      if (!res.ok) {
        throw new Error(`Server returned ${res.status}: ${res.statusText}`)
      }
      await storage.savePairingConfig({ server_url: cleanUrl, token: cleanToken })
      await mobileSync.start()
      onPaired()
      onClose()
    } catch (err: any) {
      setErrorMessage(err.message || 'Failed to connect to host. Check your IP and Wi-Fi connection.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <Modal visible={visible} animationType="slide" transparent>
      <View style={styles.overlay}>
        <View style={styles.modalContent}>
          <Text style={styles.title}>Pair with Desktop</Text>
          <Text style={styles.subtitle}>
            Enter your desktop connection details or paste the QR data from Settings &gt; Mobile Companion.
          </Text>

          {errorMessage && (
            <View style={styles.errorBox}>
              <Text style={styles.errorText}>{errorMessage}</Text>
            </View>
          )}

          <View style={styles.inputGroup}>
            <Text style={styles.label}>PASTE QR CODE DATA (QUICK-FILL)</Text>
            <TextInput
              style={styles.input}
              placeholder='Paste {"server_url":"...","token":"..."}'
              placeholderTextColor="#64748b"
              value={qrJson}
              onChangeText={handleQuickPasteJson}
            />
          </View>

          <View style={styles.inputGroup}>
            <Text style={styles.label}>HOST SERVER URL</Text>
            <TextInput
              style={styles.input}
              placeholder="http://192.168.1.50:8000"
              placeholderTextColor="#64748b"
              value={serverUrl}
              onChangeText={setServerUrl}
              autoCapitalize="none"
              autoCorrect={false}
            />
          </View>

          <View style={styles.inputGroup}>
            <Text style={styles.label}>BEARER AUTH TOKEN</Text>
            <TextInput
              style={styles.input}
              placeholder="eyJhbGciOi..."
              placeholderTextColor="#64748b"
              value={token}
              onChangeText={setToken}
              autoCapitalize="none"
              autoCorrect={false}
              secureTextEntry
            />
          </View>

          <View style={styles.buttonRow}>
            <TouchableOpacity style={styles.cancelButton} onPress={onClose} disabled={loading}>
              <Text style={styles.cancelButtonText}>Cancel</Text>
            </TouchableOpacity>

            <TouchableOpacity style={styles.connectButton} onPress={handlePair} disabled={loading}>
              {loading ? (
                <ActivityIndicator color="#0f172a" size="small" />
              ) : (
                <Text style={styles.connectButtonText}>Connect &amp; Sync</Text>
              )}
            </TouchableOpacity>
          </View>
        </View>
      </View>
    </Modal>
  )
}

const styles = StyleSheet.create({
  overlay: {
    flex: 1,
    backgroundColor: 'rgba(0,0,0,0.75)',
    justifyContent: 'center',
    padding: 20,
  },
  modalContent: {
    backgroundColor: '#1e293b',
    borderRadius: 16,
    padding: 24,
    borderWidth: 1,
    borderColor: '#334155',
  },
  title: {
    fontSize: 20,
    fontWeight: '800',
    color: '#f8fafc',
    marginBottom: 6,
  },
  subtitle: {
    fontSize: 13,
    color: '#94a3b8',
    marginBottom: 20,
    lineHeight: 18,
  },
  errorBox: {
    backgroundColor: '#450a0a',
    borderColor: '#ef4444',
    borderWidth: 1,
    borderRadius: 8,
    padding: 10,
    marginBottom: 16,
  },
  errorText: {
    color: '#fca5a5',
    fontSize: 12,
  },
  inputGroup: {
    marginBottom: 16,
  },
  label: {
    fontSize: 10,
    fontWeight: '800',
    color: '#94a3b8',
    letterSpacing: 0.8,
    marginBottom: 6,
  },
  input: {
    backgroundColor: '#0f172a',
    borderColor: '#334155',
    borderWidth: 1,
    borderRadius: 10,
    color: '#f8fafc',
    padding: 12,
    fontSize: 14,
  },
  buttonRow: {
    flexDirection: 'row',
    justifyContent: 'flex-end',
    gap: 12,
    marginTop: 10,
  },
  cancelButton: {
    paddingVertical: 12,
    paddingHorizontal: 18,
    borderRadius: 10,
  },
  cancelButtonText: {
    color: '#94a3b8',
    fontWeight: '700',
    fontSize: 14,
  },
  connectButton: {
    backgroundColor: '#38bdf8',
    paddingVertical: 12,
    paddingHorizontal: 22,
    borderRadius: 10,
    alignItems: 'center',
  },
  connectButtonText: {
    color: '#0f172a',
    fontWeight: '800',
    fontSize: 14,
  },
})
