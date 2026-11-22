import { useState, useCallback, useMemo } from 'react'
import { storage } from '../utils/storage'

export interface UseReorderableSectionsOptions<T extends string> {
  storageKey: string
  defaultOrder: readonly T[]
  collapsedStorageKey?: string
}

/** Sanitize and reconcile a stored order against the allowed default order */
export function reconcileOrder<T extends string>(
  stored: unknown,
  defaultOrder: readonly T[]
): T[] {
  const defaultSet = new Set(defaultOrder)
  if (!Array.isArray(stored)) {
    return [...defaultOrder]
  }
  const result: T[] = []
  const seen = new Set<T>()
  for (const item of stored) {
    if (typeof item === 'string' && defaultSet.has(item as T) && !seen.has(item as T)) {
      result.push(item as T)
      seen.add(item as T)
    }
  }
  // Append any missing items from defaultOrder to preserve all sections
  for (const item of defaultOrder) {
    if (!seen.has(item)) {
      result.push(item)
      seen.add(item)
    }
  }
  return result
}

export function useReorderableSections<T extends string>({
  storageKey,
  defaultOrder,
  collapsedStorageKey,
}: UseReorderableSectionsOptions<T>) {
  const [sections, setSections] = useState<T[]>(() => {
    const stored = storage.getJson<unknown>(storageKey, null)
    return reconcileOrder(stored, defaultOrder)
  })

  const [collapsedMap, setCollapsedMap] = useState<Record<string, boolean>>(() => {
    if (!collapsedStorageKey) return {}
    return storage.getJson<Record<string, boolean>>(collapsedStorageKey, {})
  })

  // Drag and drop state
  const [draggingId, setDraggingId] = useState<T | null>(null)
  const [dragOverId, setDragOverId] = useState<T | null>(null)
  const [dropPosition, setDropPosition] = useState<'before' | 'after' | null>(null)

  const isCustomized = useMemo(() => {
    if (sections.length !== defaultOrder.length) return true
    return sections.some((s, idx) => s !== defaultOrder[idx])
  }, [sections, defaultOrder])

  const saveOrder = useCallback(
    (newOrder: T[]) => {
      setSections(newOrder)
      storage.setJson(storageKey, newOrder)
    },
    [storageKey]
  )

  const moveSection = useCallback(
    (id: T, direction: 'up' | 'down') => {
      const idx = sections.indexOf(id)
      if (idx === -1) return
      const targetIdx = direction === 'up' ? idx - 1 : idx + 1
      if (targetIdx < 0 || targetIdx >= sections.length) return

      const updated = [...sections]
      const [item] = updated.splice(idx, 1)
      updated.splice(targetIdx, 0, item)
      saveOrder(updated)
    },
    [sections, saveOrder]
  )

  const resetOrder = useCallback(() => {
    saveOrder([...defaultOrder])
  }, [defaultOrder, saveOrder])

  const toggleCollapse = useCallback(
    (id: T) => {
      setCollapsedMap((prev) => {
        const next = { ...prev, [id]: !prev[id] }
        if (collapsedStorageKey) {
          storage.setJson(collapsedStorageKey, next)
        }
        return next
      })
    },
    [collapsedStorageKey]
  )

  const handleDragStart = useCallback((id: T, e: React.DragEvent) => {
    e.stopPropagation()
    e.dataTransfer.effectAllowed = 'move'
    e.dataTransfer.setData('text/plain', id)
    setDraggingId(id)
  }, [])

  const handleDragOver = useCallback(
    (id: T, e: React.DragEvent) => {
      e.preventDefault()
      e.stopPropagation()
      if (!draggingId || draggingId === id) {
        if (dragOverId === id) {
          setDragOverId(null)
          setDropPosition(null)
        }
        return
      }

      e.dataTransfer.dropEffect = 'move'
      const rect = e.currentTarget.getBoundingClientRect()
      const relY = (e.clientY - rect.top) / rect.height
      const pos: 'before' | 'after' = relY < 0.5 ? 'before' : 'after'

      setDragOverId(id)
      setDropPosition(pos)
    },
    [draggingId, dragOverId]
  )

  const handleDragLeave = useCallback(
    (id: T, e: React.DragEvent) => {
      e.stopPropagation()
      if (dragOverId === id) {
        setDragOverId(null)
        setDropPosition(null)
      }
    },
    [dragOverId]
  )

  const handleDrop = useCallback(
    (targetId: T, e: React.DragEvent) => {
      e.preventDefault()
      e.stopPropagation()
      const sourceId = draggingId
      const pos = dropPosition

      setDraggingId(null)
      setDragOverId(null)
      setDropPosition(null)

      if (!sourceId || sourceId === targetId || !pos) return

      const current = [...sections]
      const fromIdx = current.indexOf(sourceId)
      if (fromIdx === -1) return
      current.splice(fromIdx, 1)

      const toIdx = current.indexOf(targetId)
      if (toIdx === -1) return
      const insertIdx = pos === 'after' ? toIdx + 1 : toIdx
      current.splice(insertIdx, 0, sourceId)

      saveOrder(current)
    },
    [draggingId, dropPosition, sections, saveOrder]
  )

  const handleDragEnd = useCallback(() => {
    setDraggingId(null)
    setDragOverId(null)
    setDropPosition(null)
  }, [])

  return {
    sections,
    isCustomized,
    draggingId,
    dragOverId,
    dropPosition,
    collapsedMap,
    moveSection,
    resetOrder,
    saveOrder,
    toggleCollapse,
    handleDragStart,
    handleDragOver,
    handleDragLeave,
    handleDrop,
    handleDragEnd,
  }
}
