import { useState } from 'react'
import { api } from '../api/client'

export interface CodeSocraticTutorProps {
  problemTitle: string
  problemSlug: string
  code: string
  language?: string
}

export function CodeSocraticTutor({
  problemTitle,
  problemSlug,
  code,
  language = 'python',
}: CodeSocraticTutorProps) {
  const [messages, setMessages] = useState<Array<{ sender: 'user' | 'tutor'; text: string }>>([
    {
      sender: 'tutor',
      text: `Hello! I'm your Socratic Algorithm Coach for **${problemTitle}**. Ask me for a conceptual hint, edge-case analysis, or complexity feedback without spoiling the full solution.`,
    },
  ])
  const [loading, setLoading] = useState(false)

  const sendHintRequest = async (hintType: string, label: string) => {
    setMessages((prev) => [...prev, { sender: 'user', text: label }])
    setLoading(true)
    try {
      const resp = await api.socraticCodeHint(problemSlug, {
        code,
        language,
        hint_type: hintType,
      })
      setMessages((prev) => [...prev, { sender: 'tutor', text: resp.hint }])
    } catch (err: any) {
      setMessages((prev) => [
        ...prev,
        {
          sender: 'tutor',
          text: `⚠️ Socratic AI unavailable (${err?.message || 'Check that Ollama is running'}).`,
        },
      ])
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="flex flex-col rounded-xl border border-sky-500/30 bg-sky-950/20 p-4 space-y-4 shadow-xl">
      <div className="flex items-center justify-between border-b border-sky-500/20 pb-2">
        <div className="flex items-center gap-2">
          <span className="text-base">🤖</span>
          <h4 className="text-xs font-bold uppercase tracking-wider text-sky-300">
            Socratic AI Code Tutor
          </h4>
        </div>
        <span className="text-[10px] text-sky-400 font-mono">Zero Spoilers</span>
      </div>

      {/* Quick Action Prompt Chips */}
      <div className="grid grid-cols-2 gap-2 text-xs">
        <button
          onClick={() =>
            sendHintRequest('conceptual', '💡 Conceptual hint')
          }
          disabled={loading}
          className="rounded-lg border border-sky-500/30 bg-sky-900/30 p-2 text-left text-sky-200 hover:bg-sky-800/40 hover:border-sky-400 transition"
        >
          💡 <strong>Conceptual Hint</strong>
        </button>

        <button
          onClick={() =>
            sendHintRequest('edge_case', '🔍 Edge cases')
          }
          disabled={loading}
          className="rounded-lg border border-sky-500/30 bg-sky-900/30 p-2 text-left text-sky-200 hover:bg-sky-800/40 hover:border-sky-400 transition"
        >
          🔍 <strong>Edge Cases</strong>
        </button>

        <button
          onClick={() =>
            sendHintRequest('complexity', '⚡ Optimize complexity')
          }
          disabled={loading}
          className="rounded-lg border border-sky-500/30 bg-sky-900/30 p-2 text-left text-sky-200 hover:bg-sky-800/40 hover:border-sky-400 transition"
        >
          ⚡ <strong>Optimize Complexity</strong>
        </button>

        <button
          onClick={() =>
            sendHintRequest('debug', '🐛 Explain bug')
          }
          disabled={loading}
          className="rounded-lg border border-sky-500/30 bg-sky-900/30 p-2 text-left text-sky-200 hover:bg-sky-800/40 hover:border-sky-400 transition"
        >
          🐛 <strong>Explain Bug</strong>
        </button>
      </div>

      {/* Message Stream */}
      <div className="space-y-3 max-h-[300px] overflow-y-auto pr-1">
        {messages.map((m, idx) => (
          <div
            key={idx}
            className={`rounded-lg p-3 text-xs leading-relaxed ${
              m.sender === 'user'
                ? 'bg-sky-500/20 text-sky-100 border border-sky-500/40 ml-4 font-semibold'
                : 'bg-[#0d1117]/80 text-slate-300 border border-ink-line/60 mr-4 whitespace-pre-wrap'
            }`}
          >
            {m.text}
          </div>
        ))}

        {loading && (
          <div className="flex items-center gap-2 text-xs text-sky-400 italic p-2">
            <span className="h-3 w-3 rounded-full border-2 border-sky-400 border-t-transparent animate-spin" />
            Socratic tutor is thinking…
          </div>
        )}
      </div>
    </div>
  )
}
