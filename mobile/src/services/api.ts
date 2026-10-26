import { storage } from './storage'
import type {
  ConfirmReviewResponse,
  Grade,
  OfflineReviewItem,
  QueueItem,
  SubmitAnswerResponse,
  SyncStatus,
} from '../types'

export class MobileApiError extends Error {
  constructor(public status: number, message: string) {
    super(message)
  }
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const config = await storage.getPairingConfig()
  if (!config) {
    throw new MobileApiError(401, 'Device is not paired. Please scan the QR code in Settings.')
  }

  const url = `${config.server_url}${path}`
  const headers = new Headers(options.headers)
  headers.set('Authorization', `Bearer ${config.token}`)
  if (options.body && !(options.body instanceof FormData)) {
    headers.set('Content-Type', 'application/json')
  }

  const response = await fetch(url, { ...options, headers })

  if (response.status === 401) {
    throw new MobileApiError(401, 'Authentication token expired or rejected.')
  }
  if (!response.ok) {
    let detail = `${response.status} ${response.statusText}`
    try {
      const body = await response.json()
      if (typeof body.detail === 'string') detail = body.detail
      else if (Array.isArray(body.detail)) detail = body.detail.map((d: any) => d.msg).join('; ')
    } catch {
      // Keep status line
    }
    throw new MobileApiError(response.status, detail)
  }

  const text = await response.text()
  return (text ? JSON.parse(text) : null) as T
}

export const mobileApi = {
  async fetchNextQueueItem(branch?: string): Promise<QueueItem | null> {
    const query = branch ? `?branch=${encodeURIComponent(branch)}` : ''
    return request<QueueItem | null>(`/api/queue/next${query}`)
  },

  async submitAnswer(
    cardId: string,
    typedAnswer: string,
    latencyMs: number,
  ): Promise<SubmitAnswerResponse> {
    return request<SubmitAnswerResponse>(`/api/review/${cardId}/answer`, {
      method: 'POST',
      body: JSON.stringify({ typed_answer: typedAnswer, latency_ms: latencyMs }),
    })
  },

  async confirmReview(
    cardId: string,
    finalGrade: Grade,
    typedAnswer?: string,
    latencyMs?: number,
    overridden = false,
  ): Promise<ConfirmReviewResponse> {
    return request<ConfirmReviewResponse>(`/api/review/${cardId}/confirm`, {
      method: 'POST',
      body: JSON.stringify({
        final_grade: finalGrade,
        typed_answer: typedAnswer,
        latency_ms: latencyMs,
        overridden,
      }),
    })
  },

  async batchSync(
    reviews: OfflineReviewItem[],
  ): Promise<{ synced_count: number; failed_items: list<any> }> {
    return request<{ synced_count: number; failed_items: list<any> }>('/api/sync/batch', {
      method: 'POST',
      body: JSON.stringify({ reviews }),
    })
  },

  async fetchSyncStatus(): Promise<SyncStatus> {
    return request<SyncStatus>('/api/sync/status')
  },
}
