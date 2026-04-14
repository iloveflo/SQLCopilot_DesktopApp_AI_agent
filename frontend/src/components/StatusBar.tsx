import type { ConnectionStatus } from '../types/api'

type Props = {
  status: ConnectionStatus | null
  dbHealth: 'ok' | 'error' | 'unknown'
  apiBase: string
}

export function StatusBar({ status, dbHealth }: Omit<Props, 'apiBase'>) {
  const connected = status?.is_connected ?? false
  return (
    <footer className="status-bar">
      <span className="status-pill" data-state={connected ? 'on' : 'off'}>
        {connected ? '● Đã kết nối' : '○ Chưa kết nối'}
      </span>
      {connected ? (
        <>
          <span className="status-sep">|</span>
          <span title="MySQL server">{status?.server ?? '—'}</span>
          <span className="status-sep">|</span>
          <span title="User">{status?.current_user ?? '—'}</span>
          <span className="status-sep">|</span>
          <span title="DB đang phân tích">{(status?.active_databases ?? []).join(', ') || '—'}</span>
          <span className="status-sep">|</span>
          <span className="status-pill" data-state={dbHealth === 'ok' ? 'on' : 'warn'}>
            DB ping: {dbHealth === 'ok' ? 'OK' : dbHealth === 'error' ? 'Lỗi' : '…'}
          </span>
          {status?.is_admin ? (
            <>
              <span className="status-sep">|</span>
              <span className="admin-badge">Admin Profile</span>
            </>
          ) : null}
        </>
      ) : null}
      <span className="status-spacer" />
      <span className="status-api" style={{ opacity: 0.8, fontWeight: 500 }}>
        <span style={{ color: connected ? '#22c55e' : '#ef4444', marginRight: '6px' }}>●</span>
        SQLCopilot Engine: {connected ? 'Online' : 'Offline'}
      </span>
    </footer>
  )
}
