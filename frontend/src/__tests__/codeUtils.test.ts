import { describe, expect, it } from 'vitest'
import { mediaUrl } from '../api/client'
import { isCodeCard, looksLikeCode } from '../utils/codeUtils'

describe('looksLikeCode', () => {
  it('recognises fenced and bare code', () => {
    expect(looksLikeCode('```ts\nconst a = 1\n```')).toBe(true)
    expect(looksLikeCode('def add(a, b):\n    return a + b')).toBe(true)
    expect(looksLikeCode('const total = nums.reduce((a, b) => { return a + b })')).toBe(true)
  })

  it('leaves prose alone', () => {
    expect(looksLikeCode('The mitochondrion, through oxidative phosphorylation.')).toBe(false)
    expect(looksLikeCode('Let x be the class of all functions.')).toBe(false)
    expect(looksLikeCode('')).toBe(false)
    expect(looksLikeCode(null)).toBe(false)
  })
})

describe('isCodeCard', () => {
  it('follows starter code and test cases', () => {
    expect(isCodeCard({ starter_code: 'function f() {}' })).toBe(true)
    expect(isCodeCard({ test_cases: [{}] })).toBe(true)
    expect(isCodeCard({ back: 'Prophase, metaphase, anaphase, telophase.' })).toBe(false)
  })
})

describe('mediaUrl', () => {
  it('keeps server paths on the app origin and never bakes in a host', () => {
    // With no VITE_API_BASE_URL the API is "this origin", so a server path
    // must stay relative. It used to be prefixed with http://localhost:8000,
    // which broke every image on any device but the server itself.
    expect(mediaUrl('/media/u/abc.png')).toBe('/media/u/abc.png')
    expect(mediaUrl('/media/u/abc.png')).not.toContain('localhost')
  })

  it('passes absolute URLs through', () => {
    expect(mediaUrl('https://example.org/a.png')).toBe('https://example.org/a.png')
  })
})
