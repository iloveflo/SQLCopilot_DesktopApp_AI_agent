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
  isApiKeySet?: boolean | null
  onOpenAdminPanel?: () => void
  onSend: (query: string) => void
  onApprovePlan: (planFeedback: string) => void
  onCancelApproval: () => void
  onPin?: (chartConfig: any, rawData: any) => Promise<void>
}

export function ChatThread({
  messages,
  pendingApproval,
  busy,
  thinkingStep,
  isApiKeySet,
  onOpenAdminPanel,
  onSend,
  onApprovePlan,
  onCancelApproval,
  onPin,
}: Props) {
  const [draft, setDraft] = useState('')
  const [feedback, setFeedback] = useState('')
  const [showInstructions, setShowInstructions] = useState(false)

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

  // Hook sự kiện Drill-down từ biểu đồ
  useEffect(() => {
    const handleDrilldown = (e: Event) => {
      const customEvent = e as CustomEvent;
      const { label, value } = customEvent.detail;
      onSend(`Cho tôi xem chi tiết dữ liệu của phần: ${label} (Giá trị: ${value})`);
    };

    window.addEventListener('app:drilldown', handleDrilldown);
    return () => {
      window.removeEventListener('app:drilldown', handleDrilldown);
    };
  }, [onSend]);

  const [pinningIndex, setPinningIndex] = useState<number | null>(null);
  
  return (
    <section className="chat-thread">
      <div className="chat-messages">
        {isApiKeySet === false && messages.length === 0 ? (
          <div className="api-key-onboarding" style={{ margin: '2rem auto', textAlign: 'center', maxWidth: 500, padding: '1rem' }}>
            <h3 style={{ color: '#ffcc00', marginBottom: '1rem' }}>⚠️ Hiện tại chưa cấu hình API key</h3>
            {!showInstructions ? (
              <button type="button" className="btn secondary" style={{ fontSize: '1.1rem', padding: '0.5rem 1rem' }} onClick={() => setShowInstructions(true)}>
                Hướng dẫn lấy API key
              </button>
            ) : (
              <div className="instructions-pane bubble assistant" style={{ textAlign: 'left', marginTop: '1rem' }}>
                <h4 style={{ marginBottom: '1rem' }}>Cách lấy và nạp API Key Google Gemini:</h4>
                <ol style={{ paddingLeft: '1.5rem', lineHeight: '1.6', fontSize: '0.95rem' }}>
                  <li>Truy cập trang <a href="https://aistudio.google.com/app/apikey" target="_blank" rel="noreferrer" style={{ color: '#4da3ff' }}>Google AI Studio</a> và đăng nhập bằng tài khoản Google.</li>
                  <li>Nhấp vào nút <strong>Create API key</strong> và Copy đoạn mã dài vừa tạo.</li>
                  <li>Nhấp vào nút bấm bên dưới để mở giao diện quản trị của ứng dụng.</li>
                  <li>Dán mã vừa copy vào ô <strong>Google Gemini API Key</strong> và ấn Lưu.</li>
                </ol>
                <div style={{ marginTop: '1.5rem', textAlign: 'center' }}>
                  <button type="button" className="btn primary" onClick={onOpenAdminPanel}>
                    Mở Cấu hình App ngay
                  </button>
                </div>
              </div>
            )}
          </div>
        ) : null}

        {messages.map((m, i) => (
          <article key={i} className={`bubble ${m.role === 'user' ? 'user' : 'assistant'}`}>
            <div className="bubble-content">{m.content}</div>
            {m.sql_query ? (
              <pre className="sql-block">
                <code>{m.sql_query}</code>
              </pre>
            ) : null}
            {m.raw_data && m.raw_data.length > 0 ? <DataTable rows={m.raw_data} /> : null}
            {m.chart_config ? (
              <div style={{ position: 'relative', marginTop: '1rem' }}>
                {onPin && (
                   <button 
                     onClick={async () => {
                       setPinningIndex(i);
                       await onPin(m.chart_config, m.raw_data);
                       setPinningIndex(null);
                     }}
                     className="btn secondary" 
                     style={{ position: 'absolute', top: -30, right: 0, zIndex: 10, fontSize: '0.8rem', padding: '4px 8px' }}
                     disabled={pinningIndex === i}
                   >
                     {pinningIndex === i ? '⏳ Đang ghim...' : '📌 Ghim lên Dashboard'}
                   </button>
                )}
                <ChartPlot config={m.chart_config} />
              </div>
            ) : null}
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
          placeholder={isApiKeySet === false ? 'Vui lòng nạp API Key trước khi sử dụng...' : (pendingApproval ? 'Hoàn tất duyệt kế hoạch ở trên…' : 'Hỏi bằng tiếng Việt…')}
          disabled={busy || !!pendingApproval || isApiKeySet === false}
          minLength={2}
        />
        <button
          type="submit"
          className="btn primary"
          disabled={busy || !!pendingApproval || draft.trim().length < 2 || isApiKeySet === false}
        >
          Gửi
        </button>
      </form>
    </section>
  )
}
