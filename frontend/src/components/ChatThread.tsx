import { useRef, useEffect, useState } from 'react'
import type { ChatMessage } from '../types/api'
import { DataTable } from './DataTable'
import { ChartPlot } from './ChartPlot'

type PendingApproval = { query: string; plan: string }

type Props = {
  messages: ChatMessage[]
  pendingApproval: PendingApproval | null
  busy: boolean
  thinkingStep?: string | null
  onSend: (query: string) => void
  onApprovePlan: (planFeedback: string) => void
  onCancelApproval: () => void
}

export function ChatThread({
  messages,
  pendingApproval,
  busy,
  thinkingStep,
  onSend,
  onApprovePlan,
  onCancelApproval,
}: Props) {
  const [draft, setDraft] = useState('')
  const [feedback, setFeedback] = useState('')
  const endRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, pendingApproval, busy])

  const submit = (e: React.FormEvent) => {
    e.preventDefault()
    const q = draft.trim()
    if (q.length < 2 || busy || pendingApproval) return
    setDraft('')
    onSend(q)
  }

  return (
    <section className="chat-thread">
      <div className="chat-messages">
        {messages.map((m, i) => (
          <article key={i} className={`bubble ${m.role === 'user' ? 'user' : 'assistant'}`}>
            <div className="bubble-content">{m.content}</div>
            {m.sql_query ? (
              <pre className="sql-block">
                <code>{m.sql_query}</code>
              </pre>
            ) : null}
            {m.raw_data && m.raw_data.length > 0 ? <DataTable rows={m.raw_data} /> : null}
            {m.chart_config ? <ChartPlot config={m.chart_config} /> : null}
          </article>
        ))}
        {pendingApproval ? (
          <article className="bubble assistant approval-card">
            <p className="approval-label">Chờ duyệt kế hoạch</p>
            <div className="bubble-content plan-text">{pendingApproval.plan}</div>
            <label className="feedback-label">
              Góp ý / chỉnh sửa (tùy chọn)
              <textarea
                value={feedback}
                onChange={(e) => setFeedback(e.target.value)}
                rows={3}
                disabled={busy}
              />
            </label>
            <div className="approval-actions">
              <button type="button" className="btn secondary" onClick={onCancelApproval} disabled={busy}>
                Hủy
              </button>
              <button
                type="button"
                className="btn primary"
                disabled={busy}
                onClick={() => {
                  onApprovePlan(feedback.trim())
                  setFeedback('')
                }}
              >
                Duyệt &amp; chạy
              </button>
            </div>
          </article>
        ) : null}
        {thinkingStep ? (
          <article className="bubble assistant thinking-bubble">
            <div className="bubble-content thinking-text">{thinkingStep}</div>
          </article>
        ) : null}
        <div ref={endRef} />
      </div>
      <form className="chat-composer" onSubmit={submit}>
        <input
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          placeholder={pendingApproval ? 'Hoàn tất duyệt kế hoạch ở trên…' : 'Hỏi bằng tiếng Việt…'}
          disabled={busy || !!pendingApproval}
          minLength={2}
        />
        <button
          type="submit"
          className="btn primary"
          disabled={busy || !!pendingApproval || draft.trim().length < 2}
        >
          Gửi
        </button>
      </form>
    </section>
  )
}
