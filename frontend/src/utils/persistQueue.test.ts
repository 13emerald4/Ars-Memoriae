import test from 'node:test'
import assert from 'node:assert/strict'
import {
  advancePersistQueue,
  buildChronologicalPersistQueue,
  sortCardsChronologically,
} from './persistQueue'

test('sortCardsChronologically orders by position ascending and preserves tie order', () => {
  const cards = [
    { id: 'c3', position: 3 },
    { id: 'c1', position: 1 },
    { id: 'c-unpos-a', position: null },
    { id: 'c2', position: 2 },
    { id: 'c-unpos-b', position: undefined },
  ]
  const sorted = sortCardsChronologically(cards)
  assert.deepEqual(
    sorted.map((c) => c.id),
    ['c1', 'c2', 'c3', 'c-unpos-a', 'c-unpos-b'],
  )
})

test('buildChronologicalPersistQueue starts at chosen card and proceeds chronologically with wrap-around', () => {
  const cards = [{ id: '1' }, { id: '2' }, { id: '3' }, { id: '4' }, { id: '5' }]
  assert.deepEqual(buildChronologicalPersistQueue(cards, '3'), ['3', '4', '5', '1', '2'])
  assert.deepEqual(buildChronologicalPersistQueue(cards, '1'), ['1', '2', '3', '4', '5'])
  assert.deepEqual(buildChronologicalPersistQueue(cards, '5'), ['5', '1', '2', '3', '4'])
})

test('buildChronologicalPersistQueue skips already grasped cards except explicitly selected start card', () => {
  const cards = [{ id: '1' }, { id: '2' }, { id: '3' }, { id: '4' }, { id: '5' }]
  const grasped = new Set(['1', '3'])
  // Starting at 2 skips 3 (grasped) and 1 (grasped), yielding 2 -> 4 -> 5
  assert.deepEqual(buildChronologicalPersistQueue(cards, '2', grasped), ['2', '4', '5'])
  // Explicitly jumping back to grasped card 3 keeps 3 at head and skips 1
  assert.deepEqual(buildChronologicalPersistQueue(cards, '3', grasped), ['3', '4', '5', '2'])
})

test('advancePersistQueue continues to next chronological card on both Easy and non-Easy grades', () => {
  // User starts at card 1 in a 4-card deck: [1, 2, 3, 4]
  const initial = ['1', '2', '3', '4']

  // Rating card 1 as Hard -> moves to back, next card is 2
  const afterHard = advancePersistQueue(initial, '1', 'hard')
  assert.deepEqual(afterHard, ['2', '3', '4', '1'])

  // Rating card 2 as Easy -> removed from rotation, next card is 3
  const afterEasy = advancePersistQueue(afterHard, '2', 'easy')
  assert.deepEqual(afterEasy, ['3', '4', '1'])

  // Rating card 3 as Good -> moves to back, next card is 4
  const afterGood = advancePersistQueue(afterEasy, '3', 'good')
  assert.deepEqual(afterGood, ['4', '1', '3'])

  // Rating card 4 as Easy -> removed, cycles back to ungrasped card 1
  const afterCard4 = advancePersistQueue(afterGood, '4', 'easy')
  assert.deepEqual(afterCard4, ['1', '3'])
})
