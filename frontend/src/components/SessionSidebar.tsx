import { useState } from 'react'
import type { SessionResponse } from '../types/api'
import { RenameModal } from './RenameModal'
import { ConfirmModal } from './ConfirmModal'

type Props = {
  sessions: SessionResponse[]
  activeId: string | null
  onSelect: (id: string) => void
  onNew: () => void
  onRename: (id: string, name: string) => void
  onDelete: (id: string) => void
  disabled?: boolean
}

export function SessionSidebar({
  sessions,
  activeId,
  onSelect,
  onNew,
  onRename,
  onDelete,
  disabled,
}: Props) {
  const [renamingSession, setRenamingSession] = useState<{ id: string; name: string } | null>(null)
  const [deletingId, setDeletingId] = useState<string | null>(null)

  return (
    <aside className="sidebar sessions-sidebar">
      <div className="sidebar-header">
        <span>Đoạn chat</span>
        <button type="button" className="btn small primary" onClick={onNew} disabled={disabled}>
          + Mới
        </button>
      </div>
      <ul className="session-list">
        {sessions.map((s) => (
          <li key={s.session_id}>
            <button
              type="button"
              className={`session-item ${activeId === s.session_id ? 'active' : ''}`}
              onClick={() => onSelect(s.session_id)}
              disabled={disabled}
            >
              <span className="session-name">{s.name}</span>
              <span className="session-meta">
                {s.message_count} tin · {s.databases.length ? s.databases.join(', ') : '—'}
              </span>
            </button>
            <div className="session-actions">
              <button
                type="button"
                className="btn link"
                onClick={() => setRenamingSession({ id: s.session_id, name: s.name })}
                disabled={disabled}
              >
                Đổi tên
              </button>
              <button
                type="button"
                className="btn link danger"
                onClick={() => setDeletingId(s.session_id)}
                disabled={disabled}
              >
                Xóa
              </button>
            </div>
          </li>
        ))}
      </ul>

      {/* Modern Modals */}
      <RenameModal
        open={!!renamingSession}
        initialName={renamingSession?.name || ''}
        onClose={() => setRenamingSession(null)}
        onSave={(newName) => renamingSession && onRename(renamingSession.id, newName)}
      />

      <ConfirmModal
        open={!!deletingId}
        title="Xóa đoạn chat?"
        message="Hành động này sẽ xóa vĩnh viễn dữ liệu lịch sử và metadata của đoạn chat này. Bạn có chắc chắn không?"
        confirmText="Xác nhận xóa"
        onClose={() => setDeletingId(null)}
        onConfirm={() => deletingId && onDelete(deletingId)}
      />
    </aside>
  )
}
