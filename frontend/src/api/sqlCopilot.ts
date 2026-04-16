import { requestJson } from './http'
import { getApiBase } from '../lib/config'
import type {
  AdminCommandRequest,
  AdminCommandResponse,
  AdminUsersResponse,
  ConfigResponse,
  ConfigUpdateRequest,
  ChatHistoryResponse,
  ChatRequest,
  ChatResponse,
  ConnectRequest,
  ConnectionStatus,
  SelectDatabasesRequest,
  SessionCreate,
  SessionRename,
  SessionResponse,
  TableSchema,
  UseDatabaseRequest,
  PinnedMetric,
  PlotlyChartConfig
} from '../types/api'

export const api = {
  root: () => requestJson<Record<string, unknown>>('/'),

  dbHealth: () => requestJson<{ status: string; message?: string }>('/db/health'),

  dbSchema: () => requestJson<TableSchema[]>('/db/schema'),

  connectionStatus: () => requestJson<ConnectionStatus>('/connection/status'),

  connect: (body: ConnectRequest) =>
    requestJson<{ message: string; databases: string[]; current_db: string }>(
      '/connection/connect',
      { method: 'POST', body: JSON.stringify(body) },
    ),

  useDb: (body: UseDatabaseRequest) =>
    requestJson<{ message: string; current_db: string }>('/connection/use_db', {
      method: 'POST',
      body: JSON.stringify(body),
    }),

  listDatabases: () => requestJson<string[]>('/connection/list'),

  disconnect: () =>
    requestJson<{ message: string }>('/connection/disconnect', { method: 'POST' }),

  selectDatabases: (body: SelectDatabasesRequest) =>
    requestJson<{ message: string; active_databases: string[]; mode: string }>(
      '/connection/select_databases',
      { method: 'POST', body: JSON.stringify(body) },
    ),

  activeDatabases: () => requestJson<string[]>('/connection/active_databases'),

  sessionsList: () => requestJson<SessionResponse[]>('/sessions'),

  sessionCreate: (body: SessionCreate) =>
    requestJson<SessionResponse>('/sessions', {
      method: 'POST',
      body: JSON.stringify(body),
    }),

  sessionGet: (id: string) => requestJson<SessionResponse>(`/sessions/${encodeURIComponent(id)}`),

  sessionRename: (id: string, body: SessionRename) =>
    requestJson<SessionResponse>(`/sessions/${encodeURIComponent(id)}`, {
      method: 'PATCH',
      body: JSON.stringify(body),
    }),

  sessionDelete: (id: string) =>
    requestJson<{ message: string; session_id: string }>(
      `/sessions/${encodeURIComponent(id)}`,
      { method: 'DELETE' },
    ),

  sessionRestore: (id: string) =>
    requestJson<{
      session_id: string
      restored_databases: string[]
      unavailable_databases: string[]
      message: string
    }>(`/sessions/${encodeURIComponent(id)}/restore`, { method: 'POST' }),

  sessionUpdateDatabases: (id: string, body: SelectDatabasesRequest) =>
    requestJson<SessionResponse>(`/sessions/${encodeURIComponent(id)}/databases`, {
      method: 'PUT',
      body: JSON.stringify(body),
    }),

  chatAsk: (body: ChatRequest) =>
    requestJson<ChatResponse>('/chat/ask', {
      method: 'POST',
      body: JSON.stringify(body),
    }),

  chatAskStream: async (body: ChatRequest, onChunk: (data: any) => void): Promise<void> => {
    const url = `${getApiBase()}/chat/ask`
    const response = await fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    })

    if (!response.ok) {
      throw new Error('Lỗi khi gọi API chat stream')
    }

    const reader = response.body?.getReader()
    if (!reader) throw new Error('ReadableStream not supported')

    const decoder = new TextDecoder()
    let buffer = ''

    while (true) {
      const { done, value } = await reader.read()
      if (done) break

      buffer += decoder.decode(value, { stream: true })
      const lines = buffer.split('\n\n')
      buffer = lines.pop() || ''

      for (const line of lines) {
        if (line.startsWith('data: ')) {
          try {
            const data = JSON.parse(line.slice(6))
            onChunk(data)
          } catch (e) {
            console.error('Lỗi parse SSE chunk:', e)
          }
        }
      }
    }
  },

  chatClearMemory: (sessionId: string) =>
    requestJson<{ message: string; session_id: string; is_success: boolean }>(
      `/chat/session/${encodeURIComponent(sessionId)}`,
      { method: 'DELETE' },
    ),

  chatHistory: (sessionId: string) =>
    requestJson<ChatHistoryResponse>(`/chat/history/${encodeURIComponent(sessionId)}`),

  adminCommand: (body: AdminCommandRequest) =>
    requestJson<AdminCommandResponse>('/admin/command', {
      method: 'POST',
      body: JSON.stringify(body),
    }),

  adminUsers: () => requestJson<AdminUsersResponse>('/admin/users'),
  getConfig: () => requestJson<ConfigResponse>('/admin/config'),
  updateConfig: (body: ConfigUpdateRequest) =>
    requestJson<{ status: string; message: string }>('/admin/config', {
      method: 'POST',
      body: JSON.stringify(body),
    }),

  dashboardPin: (title: string, chart_config: PlotlyChartConfig, raw_data?: Record<string, unknown>[]) =>
    requestJson<{ is_success: boolean; message: string }>('/dashboard/pin', {
      method: 'POST',
      body: JSON.stringify({ title, chart_config, raw_data }),
    }),

  dashboardMetrics: () => requestJson<PinnedMetric[]>('/dashboard/metrics'),

  dashboardUnpin: (id: number) =>
    requestJson<{ is_success: boolean }>(`/dashboard/metrics/${id}`, { method: 'DELETE' }),
}

/** Ping backend không ném nếu lỗi mạng — cho splash / settings. */
export async function probeBackend(): Promise<boolean> {
  try {
    await api.root()
    return true
  } catch {
    return false
  }
}
