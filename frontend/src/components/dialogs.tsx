import { useEffect, useId, useRef, useState, type ReactNode } from 'react'
import { useDialogA11y } from '../hooks/useDialogA11y'

/** In-app replacements for `window.confirm`, `window.prompt` and
 *  `window.alert`.
 *
 *  The native ones block the page, cannot be styled, say nothing about what
 *  is being destroyed beyond one line, and are suppressed outright by some
 *  browsers after the first. These are promise-based so a call site reads the
 *  same:
 *
 *      if (!(await dialogs.confirm({ title: 'Delete deck?', danger: true }))) return
 *
 *  `<DialogHost />` (mounted once, in App) renders whatever is asked for. */

export interface ConfirmOptions {
  title: string
  message?: ReactNode
  confirmLabel?: string
  cancelLabel?: string
  /** Styles the confirm button as destructive and focuses Cancel by default. */
  danger?: boolean
  /** For irreversible bulk actions: the user must type this exact text. */
  requireText?: string
}

export interface PromptOptions {
  title: string
  label?: string
  defaultValue?: string
  placeholder?: string
  confirmLabel?: string
}

type ToastKind = 'info' | 'success' | 'error'

interface Toast {
  id: number
  message: string
  kind: ToastKind
}

type Pending =
  | { kind: 'confirm'; options: ConfirmOptions; resolve: (ok: boolean) => void }
  | { kind: 'prompt'; options: PromptOptions; resolve: (value: string | null) => void }

interface Store {
  queue: Pending[]
  toasts: Toast[]
}

let store: Store = { queue: [], toasts: [] }
const listeners = new Set<() => void>()
let hostMounted = false
let nextToastId = 1

function update(next: Store) {
  store = next
  listeners.forEach((fn) => fn())
}

export const dialogs = {
  confirm(options: ConfirmOptions | string): Promise<boolean> {
    const opts = typeof options === 'string' ? { title: options } : options
    if (!hostMounted) {
      return Promise.resolve(window.confirm(opts.title))
    }
    return new Promise<boolean>((resolve) => {
      update({ ...store, queue: [...store.queue, { kind: 'confirm', options: opts, resolve }] })
    })
  },

  /** Resolves to the trimmed text, or null if cancelled or left empty. */
  prompt(options: PromptOptions | string, defaultValue?: string): Promise<string | null> {
    const opts = typeof options === 'string' ? { title: options, defaultValue } : options
    if (!hostMounted) {
      const value = window.prompt(opts.title, opts.defaultValue ?? '')
      return Promise.resolve(value && value.trim() ? value.trim() : null)
    }
    return new Promise<string | null>((resolve) => {
      update({ ...store, queue: [...store.queue, { kind: 'prompt', options: opts, resolve }] })
    })
  },

  /** A short message that does not need an answer. */
  notify(message: string, kind: ToastKind = 'info'): void {
    if (!hostMounted) {
      console.warn(message)
      return
    }
    const toast: Toast = { id: nextToastId++, message, kind }
    update({ ...store, toasts: [...store.toasts, toast].slice(-4) })
    window.setTimeout(
      () => update({ ...store, toasts: store.toasts.filter((t) => t.id !== toast.id) }),
      kind === 'error' ? 8000 : 4500,
    )
  },

  error(err: unknown, fallback = 'Something went wrong.'): void {
    const message = err instanceof Error && err.message ? err.message : fallback
    dialogs.notify(message, 'error')
  },
}

function settle(pending: Pending, value: boolean | string | null) {
  update({ ...store, queue: store.queue.filter((p) => p !== pending) })
  if (pending.kind === 'confirm') pending.resolve(Boolean(value))
  else pending.resolve(typeof value === 'string' && value.trim() ? value.trim() : null)
}

const TOAST_STYLE: Record<ToastKind, string> = {
  info: 'border-sky-500/50 bg-[#0d1726] text-sky-100',
  success: 'border-emerald-500/50 bg-[#0c1a17] text-emerald-100',
  error: 'border-rose-500/50 bg-[#1f0f14] text-rose-100',
}

export function DialogHost() {
  const [, force] = useState(0)

  useEffect(() => {
    hostMounted = true
    const listener = () => force((n) => n + 1)
    listeners.add(listener)
    return () => {
      listeners.delete(listener)
      hostMounted = listeners.size > 0
    }
  }, [])

  const current = store.queue[0]

  return (
    <>
      {current && <DialogPanel key={store.queue.length + current.options.title} pending={current} />}
      <div
        className="pointer-events-none fixed bottom-4 right-4 z-[120] flex w-[min(24rem,calc(100vw-2rem))] flex-col gap-2"
        role="status"
        aria-live="polite"
      >
        {store.toasts.map((t) => (
          <div
            key={t.id}
            role={t.kind === 'error' ? 'alert' : undefined}
            className={`pointer-events-auto flex items-start justify-between gap-3 rounded-lg border px-3.5 py-2.5 text-sm shadow-2xl animate-in fade-in ${TOAST_STYLE[t.kind]}`}
          >
            <span className="min-w-0 break-words">{t.message}</span>
            <button
              type="button"
              aria-label="Dismiss message"
              className="shrink-0 rounded px-1 text-base leading-none opacity-70 hover:opacity-100"
              onClick={() => update({ ...store, toasts: store.toasts.filter((x) => x.id !== t.id) })}
            >
              &times;
            </button>
          </div>
        ))}
      </div>
    </>
  )
}

function DialogPanel({ pending }: { pending: Pending }) {
  const panelRef = useRef<HTMLDivElement>(null)
  const titleId = useId()
  const bodyId = useId()
  const isPrompt = pending.kind === 'prompt'
  const confirmOptions = pending.kind === 'confirm' ? pending.options : null
  const promptOptions = pending.kind === 'prompt' ? pending.options : null
  const [text, setText] = useState(promptOptions?.defaultValue ?? '')

  const cancel = () => settle(pending, isPrompt ? null : false)
  useDialogA11y(panelRef, cancel)

  const requireText = confirmOptions?.requireText
  const canConfirm = isPrompt ? text.trim().length > 0 : !requireText || text.trim() === requireText
  const accept = () => {
    if (!canConfirm) return
    settle(pending, isPrompt ? text : true)
  }
  const danger = Boolean(confirmOptions?.danger)
  const hasInput = isPrompt || Boolean(requireText)

  return (
    <div
      className="fixed inset-0 z-[110] flex items-center justify-center bg-black/70 p-4 backdrop-blur-sm"
      onMouseDown={(e) => {
        if (e.target === e.currentTarget) cancel()
      }}
    >
      <div
        ref={panelRef}
        role={danger ? 'alertdialog' : 'dialog'}
        aria-modal="true"
        aria-labelledby={titleId}
        aria-describedby={bodyId}
        tabIndex={-1}
        className="w-full max-w-md rounded-2xl border border-ink-line bg-ink-soft p-5 shadow-2xl outline-none animate-in fade-in zoom-in-95"
      >
        <h2 id={titleId} className="text-base font-semibold text-slate-100">
          {pending.options.title}
        </h2>
        <form
          className="mt-3 space-y-4"
          onSubmit={(e) => {
            e.preventDefault()
            accept()
          }}
        >
          <div id={bodyId} className="space-y-3 text-sm leading-relaxed text-slate-300">
            {confirmOptions?.message && <div>{confirmOptions.message}</div>}
            {requireText && (
              <label className="block">
                <span className="mb-1.5 block text-xs text-slate-400">
                  Type <strong className="font-mono text-rose-200">{requireText}</strong> to confirm.
                </span>
                <input
                  data-autofocus
                  className="input"
                  value={text}
                  onChange={(e) => setText(e.target.value)}
                  autoComplete="off"
                  spellCheck={false}
                />
              </label>
            )}
            {promptOptions && (
              <label className="block">
                {promptOptions.label && (
                  <span className="mb-1.5 block text-xs text-slate-400">{promptOptions.label}</span>
                )}
                <input
                  data-autofocus
                  className="input"
                  value={text}
                  placeholder={promptOptions.placeholder}
                  onChange={(e) => setText(e.target.value)}
                  onFocus={(e) => e.currentTarget.select()}
                  aria-label={promptOptions.label ? undefined : promptOptions.title}
                />
              </label>
            )}
          </div>
          <div className="flex flex-wrap justify-end gap-2">
            <button
              type="button"
              className="btn"
              onClick={cancel}
              // For a destructive action, the safe choice gets the focus.
              {...(danger && !hasInput ? { 'data-autofocus': true } : {})}
            >
              {confirmOptions?.cancelLabel ?? 'Cancel'}
            </button>
            <button
              type="submit"
              className={`btn ${danger ? 'btn-danger' : 'btn-primary'}`}
              disabled={!canConfirm}
              {...(!danger && !hasInput ? { 'data-autofocus': true } : {})}
            >
              {(isPrompt ? promptOptions?.confirmLabel : confirmOptions?.confirmLabel) ??
                (danger ? 'Delete' : 'OK')}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
