import test from 'node:test'
import assert from 'node:assert/strict'
import { getErrorMessage, isAbortError } from './errors'

test('getErrorMessage extracts messages from Error, string, and error-like objects', () => {
  assert.equal(getErrorMessage(new Error('Network failed'), 'Fallback'), 'Network failed')
  assert.equal(getErrorMessage('  Invalid token  ', 'Fallback'), 'Invalid token')
  assert.equal(getErrorMessage({ message: 'Conflict' }, 'Fallback'), 'Conflict')
  assert.equal(getErrorMessage(null, 'Fallback'), 'Fallback')
  assert.equal(getErrorMessage(new Error(''), 'Fallback'), 'Fallback')
})

test('isAbortError detects AbortError instances cleanly', () => {
  const err = new Error('aborted')
  err.name = 'AbortError'
  assert.equal(isAbortError(err), true)
  assert.equal(isAbortError(new Error('other')), false)
  assert.equal(isAbortError('AbortError'), false)
})
