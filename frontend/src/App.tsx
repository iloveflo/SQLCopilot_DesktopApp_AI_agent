import { useCallback, useEffect, useState } from 'react'
import { api } from './api/sqlCopilot'
import { ApiError } from './api/http'
import type { ChatMessage, ChatResponse, ConnectionStatus, SessionResponse, TableSchema } from './types/api'
import { ConnectionModal } from './components/ConnectionModal'
import { SessionSidebar } from './components/SessionSidebar'
import { ChatThread } from './components/ChatThread'
import { SchemaSidebar } from './components/SchemaSidebar'
import { StatusBar } from './components/StatusBar'
import { AdminPanel } from './components/AdminPanel'
import { DatabasePickerModal } from './components/DatabasePickerModal'
import { DashboardView } from './components/DashboardView'
import { ToastContainer, ToastMessage, ToastType } from './components/Toast'
import './App.css'

type PendingApproval = { query: string; plan: string }

function chatResponseToMessage(res: ChatResponse): ChatMessage {
  return {
    role: 'assistant',
    content: res.answer,
    sql_query: res.sql_query ?? undefined,
    raw_data: res.raw_data ?? undefined,
    chart_config: res.chart_config ?? undefined,
  }
}

export default function App() {
  const [status, setStatus] = useState<ConnectionStatus | null>(null)
  const [dbHealth, setDbHealth] = useState<'ok' | 'error' | 'unknown'>('unknown')
  const [sessions, setSessions] = useState<SessionResponse[]>([])
  const [activeSessionId, setActiveSessionId] = useState<string | null>(null)
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [schema, setSchema] = useState<TableSchema[] | null>(null)
  const [schemaLoading, setSchemaLoading] = useState(false)
  const [showConnect, setShowConnect] = useState(false)
  const [showDbPick, setShowDbPick] = useState(false)
  const [showAdmin, setShowAdmin] = useState(false)
  const [showDashboard, setShowDashboard] = useState(false)
  const [dashboardVersion, setDashboardVersion] = useState(0)
  const [toasts, setToasts] = useState<ToastMessage[]>([])
  const [pendingApproval, setPendingApproval] = useState<PendingApproval | null>(null)
  const [chatBusy, setChatBusy] = useState(false)
  const [banner, setBanner] = useState<string | null>(null)
  const [thinkingStep, setThinkingStep] = useState<string | null>(null)
  const [connectNonce, setConnectNonce] = useState(0)
  const [isApiKeySet, setIsApiKeySet] = useState<boolean | null>(null)
  const [adminDefaultTab, setAdminDefaultTab] = useState<'users' | 'command' | 'config'>('users')

  const [leftWidth, setLeftWidth] = useState(240)
  const [rightWidth, setRightWidth] = useState(350)
  const [isResizingLeft, setIsResizingLeft] = useState(false)
  const [isResizingRight, setIsResizingRight] = useState(false)

  const bumpConnect = useCallback(() => setConnectNonce((n) => n + 1), [])

  // Logic kéo thả
  useEffect(() => {
    const handleMouseMove = (e: MouseEvent) => {
      if (isResizingLeft) {
        const newWidth = e.clientX
        if (newWidth > 150 && newWidth < 500) {
          setLeftWidth(newWidth)
        }
      } else if (isResizingRight) {
        const newWidth = window.innerWidth - e.clientX
        if (newWidth > 150 && newWidth < 500) {
          setRightWidth(newWidth)
        }
      }
    }

    const handleMouseUp = () => {
      setIsResizingLeft(false)
      setIsResizingRight(false)
      document.body.style.cursor = 'default'
    }

    if (isResizingLeft || isResizingRight) {
      window.addEventListener('mousemove', handleMouseMove)
      window.addEventListener('mouseup', handleMouseUp)
      document.body.style.cursor = 'col-resize'
    }

    return () => {
      window.removeEventListener('mousemove', handleMouseMove)
      window.removeEventListener('mouseup', handleMouseUp)
    }
  }, [isResizingLeft, isResizingRight])

  const refreshStatus = useCallback(async () => {
    try {
      const s = await api.connectionStatus()
      setStatus(s)
      return s
    } catch {
      setStatus(null)
      return null
    }
  }, [])

  const refreshDbHealth = useCallback(async () => {
    try {
      await api.dbHealth()
      setDbHealth('ok')
    } catch {
      setDbHealth('error')
    }
  }, [])

  const refreshSessions = useCallback(async () => {
    try {
      const list = await api.sessionsList()
      setSessions(list)
      return list
    } catch {
      setSessions([])
      return []
    }
  }, [])

  const loadSchema = useCallback(async () => {
    setSchemaLoading(true)
    try {
      const t = await api.dbSchema()
      setSchema(t)
    } catch {
      setSchema(null)
    } finally {
      setSchemaLoading(false)
    }
  }, [])

  const selectSession = useCallback(async (id: string) => {
    setBanner(null)
    setPendingApproval(null)
    setActiveSessionId(id)
    try {
      await api.sessionRestore(id)
      await refreshStatus()
      const hist = await api.chatHistory(id)
      setMessages(hist.messages)
    } catch (e) {
      setBanner(e instanceof ApiError ? e.message : 'Không tải được session')
    }
  }, [refreshStatus])


  useEffect(() => {
    void refreshStatus()
  }, [refreshStatus])

  useEffect(() => {
    if (!status?.is_connected) {
      setDbHealth('unknown')
      return
    }
    void refreshDbHealth()
    const t = window.setInterval(() => void refreshDbHealth(), 30_000)
    return () => window.clearInterval(t)
  }, [status?.is_connected, refreshDbHealth])

  useEffect(() => {
    if (!status?.is_connected) {
      setSessions([])
      setActiveSessionId(null)
      setMessages([])
      setSchema(null)
      setPendingApproval(null)
      setIsApiKeySet(null)
      return
    }

    let cancelled = false
    void (async () => {
      const st = await api.connectionStatus()
      if (cancelled) return
      setStatus(st)

      // Fetch config to check API key status
      try {
        const cfg = await api.getConfig()
        if (!cancelled) setIsApiKeySet(cfg.is_key_set)
      } catch {
        /* ignore */
      }

      const dbs = st.active_databases?.length ? st.active_databases : undefined
      const list = await refreshSessions()
      if (cancelled) return
      if (list.length === 0) {
        try {
          const s = await api.sessionCreate({ databases: dbs })
          if (cancelled) return
          setSessions([s])
          await selectSession(s.session_id)
        } catch (e) {
          if (!cancelled) {
            setBanner(e instanceof ApiError ? e.message : 'Không tạo được session')
          }
        }
      } else {
        await selectSession(list[0].session_id)
      }
    })()
    return () => {
      cancelled = true
    }
  }, [status?.is_connected, connectNonce, refreshSessions, selectSession])

  const handleNewSession = async () => {
    if (!status?.is_connected) return
    setBanner(null)
    setPendingApproval(null)
    try {
      const s = await api.sessionCreate({
        databases: status.active_databases?.length ? status.active_databases : undefined,
      })
      await refreshSessions()
      await selectSession(s.session_id)
    } catch (e) {
      setBanner(e instanceof ApiError ? e.message : 'Không tạo session')
    }
  }

  const handleRenameSession = async (id: string, name: string) => {
    try {
      await api.sessionRename(id, { name })
      await refreshSessions()
    } catch (e) {
      setBanner(e instanceof ApiError ? e.message : 'Đổi tên thất bại')
    }
  }

  const handleDeleteSession = async (id: string) => {
    try {
      await api.sessionDelete(id)
      const list = await refreshSessions()
      if (activeSessionId === id) {
        if (list[0]) {
          await selectSession(list[0].session_id)
        } else if (status?.is_connected) {
          const s = await api.sessionCreate({
            databases: status.active_databases?.length ? status.active_databases : undefined,
          })
          setSessions([s])
          await selectSession(s.session_id)
        }
      }
    } catch (e) {
      setBanner(e instanceof ApiError ? e.message : 'Xóa thất bại')
    }
  }

  const handleSend = async (query: string) => {
    if (!activeSessionId) {
      setBanner('Chưa có session.')
      return
    }
    setChatBusy(true)
    setBanner(null)
    setThinkingStep('Bắt đầu xử lý...')
    setMessages((m) => [...m, { role: 'user', content: query }])

    try {
      let finalRes: any = null

      await api.chatAskStream(
        {
          query,
          session_id: activeSessionId,
          is_approved: false,
        },
        (chunk) => {
          if (chunk.node) {
            const stepLabels: Record<string, string> = {
              reader: '🔍 Đang phân tích cấu trúc Database...',
              planner: '📝 Đang lập kế hoạch truy vấn...',
              sql_coder: '💻 Đang tạo mã SQL...',
              db_executor: '⚙️ Đang thực thi câu lệnh trên DB...',
              interpreter: '📊 Đang tổng hợp và giải thích kết quả...',
            }
            setThinkingStep(stepLabels[chunk.node] || `Đang chạy: ${chunk.node}`)

            if (chunk.data) {
              finalRes = { ...finalRes, ...chunk.data }
              
              // Cập nhật UI ngay lập tức khi có dữ liệu quan trọng (SQL hoặc Answer hoặc Data)
              if (chunk.data.sql_query || chunk.data.raw_data || chunk.data.answer || chunk.data.plan) {
                const msg = chatResponseToMessage({
                  ...finalRes,
                  is_success: true,
                  needs_approval: finalRes.needs_approval,
                  plan: finalRes.plan
                });
                
                setMessages((prev) => {
                  const last = prev[prev.length - 1];
                  if (last && last.role === 'assistant') {
                    // Cập nhật tin nhắn assistant cuối cùng
                    return [...prev.slice(0, -1), msg];
                  } else {
                    // Thêm tin nhắn assistant mới
                    return [...prev, msg];
                  }
                });
              }

              if (chunk.data.answer || chunk.data.plan) {
                setThinkingStep(null);
              }
            }
          }
        },
      )

      if (finalRes && (finalRes.answer || finalRes.plan)) {
        if (finalRes.needs_approval && finalRes.plan) {
          setPendingApproval({ query, plan: finalRes.plan })
        }
      }
      await refreshSessions()
    } catch (e) {
      setMessages((m) => [
        ...m,
        {
          role: 'assistant',
          content: e instanceof Error ? `Lỗi hệ thống: ${e.message}. Nếu Backend bị khởi động lại, vui lòng nhấp "Kết nối lại" ở góc trên bên phải.` : 'Lỗi mạng hoặc mất kết nối Server. Vui lòng thử Kết nối lại.',
        },
      ])
    } finally {
      setChatBusy(false)
      setThinkingStep(null)
    }
  }

  const addToast = (message: string, type: ToastType = 'info') => {
    const id = Math.random().toString(36).substring(2, 9)
    setToasts((prev) => [...prev, { id, message, type }])
  }

  const removeToast = (id: string) => {
    setToasts((prev) => prev.filter((t) => t.id !== id))
  }

  const handlePinMetric = async (chartConfig: unknown, _rawData?: unknown) => {
    try {
      const title = (chartConfig as any)?.layout?.title || 'Biểu đồ từ Chat'
      await api.dashboardPin({
        title: typeof title === 'object' ? title.text : title,
        chart_config: chartConfig,
        raw_data: null // Tối ưu hiệu năng: Không gửi dữ liệu thô dư thừa
      })
      addToast('Đã ghim biểu đồ vào Dashboard!', 'success')
      // Tự động yêu cầu Dashboard làm mới dữ liệu
      setDashboardVersion(v => v + 1)
    } catch (e) {
      addToast('Lỗi ghim biểu đồ: ' + (e instanceof Error ? e.message : 'Unknown error'), 'error')
    }
  }

  const handleApprovePlan = async (planFeedback: string) => {
    if (!pendingApproval || !activeSessionId) return
    setChatBusy(true)
    setBanner(null)
    setThinkingStep('Đang gửi phản hồi kế hoạch...')
    try {
      let finalRes: any = null

      await api.chatAskStream(
        {
          query: pendingApproval.query,
          session_id: activeSessionId,
          is_approved: true,
          plan_feedback: planFeedback || null,
        },
        (chunk) => {
          if (chunk.node) {
            const stepLabels: Record<string, string> = {
              sql_coder: '💻 Đang tạo mã SQL...',
              db_executor: '⚙️ Đang thực thi câu lệnh trên DB...',
              interpreter: '📊 Đang tổng hợp kết quả...',
            }
            setThinkingStep(stepLabels[chunk.node] || `Đang chạy: ${chunk.node}`)

            if (chunk.data) {
              finalRes = { ...finalRes, ...chunk.data }

              if (chunk.data.sql_query || chunk.data.raw_data || chunk.data.answer) {
                const msg = chatResponseToMessage({
                  ...finalRes,
                  is_success: true
                });
                
                setMessages((prev) => {
                  const last = prev[prev.length - 1];
                  if (last && last.role === 'assistant') {
                    return [...prev.slice(0, -1), msg];
                  } else {
                    return [...prev, msg];
                  }
                });
              }

              if (chunk.data.answer) {
                setThinkingStep(null);
              }
            }
          }
        },
      )

      setPendingApproval(null)
      await refreshSessions()
    } catch (e) {
      setMessages((m) => [
        ...m,
        {
          role: 'assistant',
          content: e instanceof Error ? `Lỗi khi duyệt: ${e.message}. Nếu Backend bị restart, vui lòng Kết nối lại.` : 'Lỗi mạng hoặc mất kết nối. Vui lòng Kết nối lại.',
        },
      ])
    } finally {
      setChatBusy(false)
      setThinkingStep(null)
    }
  }

  const handleDisconnect = async () => {
    try {
      await api.disconnect()
    } catch {
      /* ignore */
    }
    await refreshStatus()
  }

  const connected = status?.is_connected ?? false

  return (
    <div className="app-shell">
      <header className="app-toolbar">
        <h1 className="app-title">SQL Copilot</h1>
        <div className="toolbar-actions">
          {!connected ? (
            <button type="button" className="btn primary" onClick={() => setShowConnect(true)}>
              Kết nối
            </button>
          ) : (
            <>
              <button type="button" className="btn secondary" onClick={() => setShowDbPick(true)}>
                Chọn DB
              </button>
              <button type="button" className="btn secondary" onClick={() => void loadSchema()}>
                Tải lược đồ
              </button>
              <button type="button" className="btn secondary" onClick={() => setShowDashboard(true)}>
                📊 Dashboard
              </button>
              {status?.is_admin ? (
                <button type="button" className="btn secondary" onClick={() => {
                  setAdminDefaultTab('users')
                  setShowAdmin(true)
                }}>
                  Quản trị
                </button>
              ) : null}
              <button type="button" className="btn secondary" onClick={() => setShowConnect(true)}>
                Kết nối lại
              </button>
              <button type="button" className="btn danger" onClick={() => void handleDisconnect()}>
                Ngắt
              </button>
            </>
          )}
        </div>
      </header>

      {banner ? (
        <div className="banner error" role="alert">
          {banner}
          <button type="button" className="btn link" onClick={() => setBanner(null)}>
            Đóng
          </button>
        </div>
      ) : null}

      <main
        className="app-main"
        style={{
          gridTemplateColumns: `${leftWidth}px 4px 1fr 4px ${rightWidth}px`,
        }}
      >
        <SessionSidebar
          sessions={sessions}
          activeId={activeSessionId}
          onSelect={(id) => void selectSession(id)}
          onNew={() => void handleNewSession()}
          onRename={handleRenameSession}
          onDelete={(id) => void handleDeleteSession(id)}
          disabled={!connected}
        />
        <div
          className={`resizer left-resizer ${isResizingLeft ? 'dragging' : ''}`}
          onMouseDown={() => setIsResizingLeft(true)}
        />
        <ChatThread
          messages={messages}
          pendingApproval={pendingApproval}
          busy={chatBusy}
          thinkingStep={thinkingStep}
          isApiKeySet={isApiKeySet}
          onOpenAdminPanel={() => {
            setAdminDefaultTab('config')
            setShowAdmin(true)
          }}
          onSend={(q) => void handleSend(q)}
          onApprovePlan={(fb) => void handleApprovePlan(fb)}
          onCancelApproval={() => setPendingApproval(null)}
          onPinMetric={handlePinMetric}
        />
        <div
          className={`resizer right-resizer ${isResizingRight ? 'dragging' : ''}`}
          onMouseDown={() => setIsResizingRight(true)}
        />
        <SchemaSidebar tables={schema} loading={schemaLoading} onRefresh={() => void loadSchema()} />
      </main>

      <StatusBar status={status} dbHealth={dbHealth} />

      <ConnectionModal
        open={showConnect}
        onClose={() => setShowConnect(false)}
        onConnected={() => {
          void refreshStatus().then(() => {
            bumpConnect()
            void loadSchema()
          })
        }}
      />

      <DashboardView 
        isOpen={showDashboard} 
        onClose={() => setShowDashboard(false)} 
        version={dashboardVersion}
      />

      <ToastContainer toasts={toasts} onRemove={removeToast} />

      <DatabasePickerModal
        open={showDbPick}
        onClose={() => setShowDbPick(false)}
        sessionId={activeSessionId}
        currentSelection={status?.active_databases ?? []}
        onApplied={() => {
          void refreshStatus()
          void refreshSessions()
          void loadSchema()
        }}
      />

      {showAdmin ? <AdminPanel onClose={() => setShowAdmin(false)} defaultTab={adminDefaultTab} onConfigSaved={() => setIsApiKeySet(true)} /> : null}
    </div>
  )
}
