import { mobileApi } from './api'
import { storage } from './storage'
import type { SyncEvent } from '../types'

export type SyncConnectionState = 'connecting' | 'connected' | 'disconnected'

type SyncListener = (event: SyncEvent) => void
type StateListener = (state: SyncConnectionState) => void

class MobileSyncService {
  private ws: WebSocket | null = null
  private pingInterval: any = null
  private reconnectTimer: any = null
  private connectionState: SyncConnectionState = 'disconnected'
  private syncListeners: Set<SyncListener> = new Set()
  private stateListeners: Set<StateListener> = new Set()
  private isDisposed = false

  public getState(): SyncConnectionState {
    return this.connectionState
  }

  public subscribe(listener: SyncListener): () => void {
    this.syncListeners.add(listener)
    return () => this.syncListeners.delete(listener)
  }

  public subscribeState(listener: StateListener): () => void {
    this.stateListeners.add(listener)
    listener(this.connectionState)
    return () => this.stateListeners.delete(listener)
  }

  private setState(state: SyncConnectionState) {
    if (this.connectionState !== state) {
      this.connectionState = state
      this.stateListeners.forEach((fn) => fn(state))
    }
  }

  public async start(): Promise<void> {
    this.isDisposed = false
    await this.connect()
  }

  public stop(): void {
    this.isDisposed = true
    if (this.pingInterval) clearInterval(this.pingInterval)
    if (this.reconnectTimer) clearTimeout(this.reconnectTimer)
    if (this.ws) {
      try {
        this.ws.close()
      } catch {}
      this.ws = null
    }
    this.setState('disconnected')
  }

  private async connect(): Promise<void> {
    if (this.isDisposed) return

    const config = await storage.getPairingConfig()
    if (!config) {
      this.setState('disconnected')
      return
    }

    this.setState('connecting')

    try {
      const wsUrl = config.server_url.replace(/^http/, 'ws') + `/api/sync/ws?token=${encodeURIComponent(config.token)}`
      this.ws = new WebSocket(wsUrl)

      this.ws.onopen = () => {
        this.setState('connected')
        // Automatically flush any reviews recorded while offline
        void this.flushOfflineQueue()

        this.pingInterval = setInterval(() => {
          if (this.ws && this.ws.readyState === WebSocket.OPEN) {
            this.ws.send(JSON.stringify({ type: 'PING' }))
          }
        }, 20000)
      }

      this.ws.onmessage = (event) => {
        try {
          const parsed = JSON.parse(event.data) as SyncEvent
          this.syncListeners.forEach((fn) => fn(parsed))
        } catch (err) {
          console.debug('[Sync] Failed parsing event', err)
        }
      }

      this.ws.onclose = () => {
        if (this.pingInterval) clearInterval(this.pingInterval)
        this.setState('disconnected')
        if (!this.isDisposed) {
          this.reconnectTimer = setTimeout(() => void this.connect(), 3500)
        }
      }

      this.ws.onerror = () => {
        if (this.ws) {
          try {
            this.ws.close()
          } catch {}
        }
      }
    } catch {
      this.setState('disconnected')
      if (!this.isDisposed) {
        this.reconnectTimer = setTimeout(() => void this.connect(), 5000)
      }
    }
  }

  public async flushOfflineQueue(): Promise<number> {
    const queue = await storage.getOfflineQueue()
    if (!queue.length) return 0

    try {
      const res = await mobileApi.batchSync(queue)
      await storage.clearOfflineQueue()
      return res.synced_count
    } catch (err) {
      console.debug('[Sync] Offline queue flush deferred', err)
      return 0
    }
  }
}

export const mobileSync = new MobileSyncService()
