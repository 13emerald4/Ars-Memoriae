import test from 'node:test'
import assert from 'node:assert/strict'
import { runViewTransition, shouldUseViewTransition } from './viewTransition'

test('shouldUseViewTransition returns false when reduced motion is enabled', () => {
  const fakeDoc = { startViewTransition: (cb: () => void) => cb() }
  assert.equal(shouldUseViewTransition(fakeDoc, true), false)
  assert.equal(shouldUseViewTransition(fakeDoc, false), true)
})

test('shouldUseViewTransition returns false when API is missing', () => {
  assert.equal(shouldUseViewTransition({}, false), false)
  assert.equal(shouldUseViewTransition(null, false), false)
})

test('runViewTransition invokes startViewTransition when available', () => {
  let calledStart = 0
  let updated = 0
  const fakeDoc = {
    startViewTransition: (cb: () => void) => {
      calledStart += 1
      cb()
    },
  }
  const used = runViewTransition(() => {
    updated += 1
  }, { doc: fakeDoc, prefersReducedMotion: false })

  assert.equal(used, true)
  assert.equal(calledStart, 1)
  assert.equal(updated, 1)
})

test('runViewTransition falls back cleanly when reduced motion or unsupported', () => {
  let updated = 0
  const used = runViewTransition(() => {
    updated += 1
  }, { doc: {}, prefersReducedMotion: false })

  assert.equal(used, false)
  assert.equal(updated, 1)
})
