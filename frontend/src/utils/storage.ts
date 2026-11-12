/** localStorage that cannot throw.
 *
 *  Reading or writing storage raises in private browsing modes, when the
 *  quota is full and when site data is blocked. Much of this app reads a
 *  preference inside a `useState` initialiser, where an exception takes the
 *  whole page down. A preference that cannot be read is just "not set". */

function backend(): Storage | null {
  try {
    return typeof window === 'undefined' ? null : window.localStorage
  } catch {
    return null
  }
}

export const storage = {
  get(key: string): string | null {
    try {
      return backend()?.getItem(key) ?? null
    } catch {
      return null
    }
  },

  set(key: string, value: string): void {
    try {
      backend()?.setItem(key, value)
    } catch {
      /* quota exceeded or storage disabled: the setting lasts for this visit only */
    }
  },

  remove(key: string): void {
    try {
      backend()?.removeItem(key)
    } catch {
      /* nothing to remove if storage is unavailable */
    }
  },

  /** A stored value, but only if it is one of the values the caller expects.
   *  Storage outlives releases; an old or hand-edited value must not be cast
   *  straight into a union type. */
  getOneOf<T extends string>(key: string, allowed: readonly T[], fallback: T): T {
    const value = this.get(key)
    return value !== null && (allowed as readonly string[]).includes(value) ? (value as T) : fallback
  },

  getJson<T>(key: string, fallback: T): T {
    const raw = this.get(key)
    if (raw === null) return fallback
    try {
      return JSON.parse(raw) as T
    } catch {
      return fallback
    }
  },

  setJson(key: string, value: unknown): void {
    try {
      this.set(key, JSON.stringify(value))
    } catch {
      /* unserialisable value: skip rather than throw */
    }
  },
}
