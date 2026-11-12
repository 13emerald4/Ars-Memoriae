import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { storage } from '../utils/storage'

/** A localStorage whose every method throws, as in private browsing with
 *  storage blocked, or when the quota is exhausted. */
function brokenStorage(): Storage {
  const fail = () => {
    throw new DOMException('denied', 'SecurityError')
  }
  return { getItem: fail, setItem: fail, removeItem: fail, clear: fail, key: fail, length: 0 }
}

function memoryStorage(): Storage {
  const data = new Map<string, string>()
  return {
    getItem: (k) => (data.has(k) ? data.get(k)! : null),
    setItem: (k, v) => void data.set(k, String(v)),
    removeItem: (k) => void data.delete(k),
    clear: () => data.clear(),
    key: (i) => [...data.keys()][i] ?? null,
    get length() {
      return data.size
    },
  }
}

describe('storage', () => {
  beforeEach(() => {
    vi.stubGlobal('window', { localStorage: memoryStorage() })
  })
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('round-trips values', () => {
    storage.set('k', 'v')
    expect(storage.get('k')).toBe('v')
    storage.remove('k')
    expect(storage.get('k')).toBeNull()
  })

  it('never throws when storage is unavailable', () => {
    vi.stubGlobal('window', { localStorage: brokenStorage() })
    expect(storage.get('k')).toBeNull()
    expect(() => storage.set('k', 'v')).not.toThrow()
    expect(() => storage.remove('k')).not.toThrow()
    expect(storage.getJson('k', { a: 1 })).toEqual({ a: 1 })
  })

  it('never throws when reading the storage object itself is denied', () => {
    const denied = {}
    Object.defineProperty(denied, 'localStorage', {
      get() {
        throw new DOMException('denied', 'SecurityError')
      },
    })
    vi.stubGlobal('window', denied)
    expect(storage.get('k')).toBeNull()
    expect(() => storage.set('k', 'v')).not.toThrow()
  })

  it('only returns stored values the caller expects', () => {
    storage.set('layout', 'split')
    expect(storage.getOneOf('layout', ['split', 'classic'] as const, 'classic')).toBe('split')
    // A value written by an older release, or by hand.
    storage.set('layout', 'sideways')
    expect(storage.getOneOf('layout', ['split', 'classic'] as const, 'classic')).toBe('classic')
    expect(storage.getOneOf('missing', ['split', 'classic'] as const, 'split')).toBe('split')
  })

  it('falls back on corrupt JSON', () => {
    storage.set('drafts', '{not json')
    expect(storage.getJson('drafts', [])).toEqual([])
    storage.setJson('drafts', [{ id: 1 }])
    expect(storage.getJson<{ id: number }[]>('drafts', [])).toEqual([{ id: 1 }])
  })
})
