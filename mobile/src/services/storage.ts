import AsyncStorage from '@react-native-async-storage/async-storage'
import type { OfflineReviewItem, PairingConfig } from '../types'

const KEY_SERVER_URL = '@ars_memoriae:server_url'
const KEY_AUTH_TOKEN = '@ars_memoriae:auth_token'
const KEY_USER_EMAIL = '@ars_memoriae:user_email'
const KEY_OFFLINE_QUEUE = '@ars_memoriae:offline_queue'

// In-memory fallback if native async storage fails
const memoryStore = new Map<string, string>()

async function getItem(key: string): Promise<string | null> {
  try {
    return await AsyncStorage.getItem(key)
  } catch {
    return memoryStore.get(key) ?? null
  }
}

async function setItem(key: string, value: string): Promise<void> {
  try {
    await AsyncStorage.setItem(key, value)
  } catch {
    memoryStore.set(key, value)
  }
}

async function removeItem(key: string): Promise<void> {
  try {
    await AsyncStorage.removeItem(key)
  } catch {
    memoryStore.delete(key)
  }
}

export const storage = {
  async getPairingConfig(): Promise<PairingConfig | null> {
    const server_url = await getItem(KEY_SERVER_URL)
    const token = await getItem(KEY_AUTH_TOKEN)
    const email = await getItem(KEY_USER_EMAIL)
    if (!server_url || !token) return null
    return { server_url, token, email: email ?? undefined }
  },

  async savePairingConfig(config: PairingConfig): Promise<void> {
    await setItem(KEY_SERVER_URL, config.server_url.replace(/\/+$/, ''))
    await setItem(KEY_AUTH_TOKEN, config.token)
    if (config.email) await setItem(KEY_USER_EMAIL, config.email)
  },

  async clearPairingConfig(): Promise<void> {
    await removeItem(KEY_SERVER_URL)
    await removeItem(KEY_AUTH_TOKEN)
    await removeItem(KEY_USER_EMAIL)
  },

  async getOfflineQueue(): Promise<OfflineReviewItem[]> {
    const raw = await getItem(KEY_OFFLINE_QUEUE)
    if (!raw) return []
    try {
      return JSON.parse(raw) as OfflineReviewItem[]
    } catch {
      return []
    }
  },

  async enqueueOfflineReview(item: OfflineReviewItem): Promise<void> {
    const queue = await this.getOfflineQueue()
    queue.push(item)
    await setItem(KEY_OFFLINE_QUEUE, JSON.stringify(queue))
  },

  async clearOfflineQueue(): Promise<void> {
    await removeItem(KEY_OFFLINE_QUEUE)
  },
}
