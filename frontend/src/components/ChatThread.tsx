import { useRef, useEffect, useState } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import type { ChatMessage, SubReport } from '../types/api'
import { DataTable } from './DataTable'
import { ChartPlot } from './ChartPlot'
import { api } from '../api/sqlCopilot'

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
  onPinMetric?: (config: unknown, data: unknown) => void
}

/**
 * Component con xử lý việc hiển trợ và tải dữ liệu bảng (Lazy Loading)
 */
function AssistantMessage({ 
  msg, 
  onPinMetric 
}: { 
  msg: ChatMessage, 
  onPinMetric?: (config: unknown, data: unknown) => void 
}) {
  const [lazyData, setLazyData] = useState<{
    raw_data?: any[],
    multi_results?: SubReport[],
    chart_config?: any,
    loading: boolean
  }>({
    raw_data: msg.raw_data || undefined,
    multi_results: msg.multi_results || undefined,
    chart_config: msg.chart_config || undefined,
    loading: false
  });

  useEffect(() => {
    // Nếu tin nhắn có result_id nhưng chưa có dữ liệu bảng -> Tải từ "Kho lưu trữ"
    if (msg.result_id && !lazyData.raw_data && !lazyData.multi_results && !lazyData.loading) {
      setLazyData(prev => ({ ...prev, loading: true }));
      api.chatFetchResult(msg.result_id)
        .then(res => {
          if (res.success && res.data) {
            setLazyData({
              raw_data: res.data.raw_data,
              multi_results: res.data.multi_results,
              chart_config: res.data.chart_config,
              loading: false
            });
          }
        })
        .catch(err => {
          console.error("Lazy loading failed:", err);
          setLazyData(prev => ({ ...prev, loading: false }));
        });
    }
  }, [msg.result_id]);

  return (
    <>
      <div className="chat-message-content assistant">
        <div className="markdown-content">
          <ReactMarkdown remarkPlugins={[remarkGfm]}>
            {msg.content}
          </ReactMarkdown>
        </div>
      </div>
      
      {lazyData.loading && (
        <div className="lazy-loading-placeholder">
          <span className="spinner-inline"></span> Đang tải dữ liệu từ kho lưu trữ...
        </div>
      )}

      {/* Hiển thị kết quả đơn lẻ */}
      {!lazyData.multi_results && (
        <>
          {msg.sql_query ? (
            <pre className="sql-block">
              <code>{msg.sql_query}</code>
            </pre>
          ) : null}
          {lazyData.raw_data && lazyData.raw_data.length > 0 ? (
            <DataTable rows={lazyData.raw_data} />
          ) : null}
          {lazyData.chart_config ? (
            <ChartPlot config={lazyData.chart_config} rawData={lazyData.raw_data} onPin={onPinMetric} />
          ) : null}
        </>
      )}

      {/* HIỂN THỊ ĐA BÁO CÁO */}
      {lazyData.multi_results && lazyData.multi_results.length > 0 && (
        <div className="multi-reports-container">
          {lazyData.multi_results.filter(r => r.sql_query || r.raw_data || r.chart_config).map((report, idx) => (
            <div key={idx} className="report-segment">
              {idx > 0 && <hr className="reports-divider" />}
              {report.title && <h4 className="report-title">{report.title}</h4>}
              {report.sql_query && (
                <details className="sql-details">
                  <summary>Chi tiết truy vấn</summary>
                  <pre className="sql-block mini">
                    <code>{report.sql_query}</code>
                  </pre>
                </details>
              )}
              {report.success ? (
                <>
                  {report.raw_data && report.raw_data.length > 0 && (
                    <DataTable rows={report.raw_data} />
                  )}
                  {report.chart_config && (
                    <ChartPlot 
                      config={report.chart_config} 
                      rawData={report.raw_data} 
                      onPin={onPinMetric} 
                    />
                  )}
                </>
              ) : (
                <div className="error-text">❌ Lỗi: {report.error}</div>
              )}
            </div>
          ))}
        </div>
      )}
    </>
  );
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
  onPinMetric,
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
            {m.role === 'user' ? (
              <div className="chat-message-content user">{m.content}</div>
            ) : (
              <AssistantMessage msg={m} onPinMetric={onPinMetric} />
            )}
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
          placeholder={
            isApiKeySet === false 
              ? 'Vui lòng nạp API Key trước khi sử dụng...' 
              : busy 
                ? 'AI đang suy nghĩ, vui lòng đợi giây lát...' 
                : pendingApproval 
                  ? 'Hoàn tất duyệt kế hoạch ở trên…' 
                  : 'Hỏi bằng tiếng Việt…'
          }
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
