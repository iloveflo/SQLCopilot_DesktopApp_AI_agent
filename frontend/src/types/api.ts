export type ConnectRequest = {
  host: string
  port: number
  user: string
  password: string
  database?: string
}

export type UseDatabaseRequest = { database: string }

export type SelectDatabasesRequest = { databases: string[] }

export type ConnectionStatus = {
  is_connected: boolean
  server: string | null
  current_user: string | null
  is_admin: boolean
  active_databases: string[]
  health: string | undefined
  message: string
}

export type SessionCreate = {
  name?: string | null
  databases?: string[] | null
}

export type SessionRename = { name: string }

export type SessionResponse = {
  session_id: string
  name: string
  created_at: string
  updated_at: string
  databases: string[]
  message_count: number
}

export type ChatRequest = {
  query: string
  user_id?: string
  session_id?: string | null
  is_approved?: boolean
  plan_feedback?: string | null
}

export type ChatResponse = {
  answer: string
  plan?: string | null
  needs_approval: boolean
  sql_query?: string | null
  raw_data?: Record<string, unknown>[] | null
  chart_config?: PlotlyChartConfig | null
  is_success: boolean
  error_message?: string | null
}

export type ChatMessage = {
  role: string
  content: string
  sql_query?: string | null
  raw_data?: Record<string, unknown>[] | null
  chart_config?: PlotlyChartConfig | null
}

export type ChatHistoryResponse = {
  session_id: string
  messages: ChatMessage[]
}

export type ColumnSchema = {
  name: string
  type: string
  nullable: boolean
  comment?: string | null
}

export type ForeignKeySchema = {
  constrained_columns: string[]
  referred_table: string
  referred_columns: string[]
}

export type TableSchema = {
  table_name: string
  db_name?: string | null
  columns: ColumnSchema[]
  primary_keys: string[]
  foreign_keys: ForeignKeySchema[]
}

export type AdminCommandRequest = {
  command: string
  is_approved?: boolean
  planned_sql?: string | null
}

export type AdminCommandResponse = {
  answer: string
  planned_sql?: string | null
  needs_approval: boolean
  is_success: boolean
  error_message?: string | null
}

export type AdminUserRow = { user: string; host: string; locked: boolean }

export type AdminUsersResponse = { users: AdminUserRow[]; total: number }

export type ConfigResponse = {
  google_api_key_masked: string
  is_key_set: boolean
}

export type ConfigUpdateRequest = {
  google_api_key: string
}

/** Khớp output `visualizer.generate_chart_config` → react-plotly.js */
export type PlotlyChartConfig = {
  data: Record<string, unknown>[]
  layout?: Record<string, unknown>
}

export type PinnedMetric = {
  id: number
  title: string
  chart_config: PlotlyChartConfig
  raw_data?: Record<string, unknown>[] | null
  created_at: string
}
