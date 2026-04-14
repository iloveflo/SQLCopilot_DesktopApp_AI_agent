import { useState } from 'react'
import { api } from '../api/sqlCopilot'
import { ApiError } from '../api/http'
import type { AdminUserRow } from '../types/api'

type Props = { onClose: () => void }

export function AdminPanel({ onClose }: Props) {
  const [tab, setTab] = useState<'users' | 'command' | 'config'>('users')
  const [users, setUsers] = useState<AdminUserRow[] | null>(null)
  const [usersErr, setUsersErr] = useState<string | null>(null)
  const [loadingUsers, setLoadingUsers] = useState(false)

  const [apiKey, setApiKey] = useState('')
  const [maskedKey, setMaskedKey] = useState('')
  const [saveLoading, setSaveLoading] = useState(false)
  const [saveMsg, setSaveMsg] = useState<{ type: 'ok' | 'err'; text: string } | null>(null)

  const [cmd, setCmd] = useState('')
  const [plannedSql, setPlannedSql] = useState<string | null>(null)
  const [cmdAnswer, setCmdAnswer] = useState<string | null>(null)
  const [cmdBusy, setCmdBusy] = useState(false)

  const loadConfig = async () => {
    try {
      const cfg = await api.getConfig()
      setMaskedKey(cfg.google_api_key_masked)
    } catch {
      /* ignore */
    }
  }

  const handleSaveConfig = async () => {
    if (!apiKey.trim()) return
    setSaveLoading(true)
    setSaveMsg(null)
    try {
      await api.updateConfig({ google_api_key: apiKey.trim() })
      setSaveMsg({ type: 'ok', text: 'Đã lưu cấu hình thành công!' })
      setApiKey('')
      await loadConfig()
    } catch (e) {
      setSaveMsg({ type: 'err', text: e instanceof ApiError ? e.message : 'Lỗi khi lưu' })
    } finally {
      setSaveLoading(false)
    }
  }

  const loadUsers = async () => {
    setLoadingUsers(true)
    setUsersErr(null)
    try {
      const r = await api.adminUsers()
      setUsers(r.users)
    } catch (e) {
      setUsersErr(e instanceof ApiError ? e.message : 'Lỗi tải danh sách')
      setUsers(null)
    } finally {
      setLoadingUsers(false)
    }
  }

  const runCommandPreview = async () => {
    if (!cmd.trim()) return
    setCmdBusy(true)
    setCmdAnswer(null)
    setPlannedSql(null)
    try {
      const r = await api.adminCommand({ command: cmd.trim(), is_approved: false })
      setCmdAnswer(r.answer)
      setPlannedSql(r.planned_sql ?? null)
    } catch (e) {
      setCmdAnswer(e instanceof ApiError ? e.message : 'Lỗi')
    } finally {
      setCmdBusy(false)
    }
  }

  const runCommandExecute = async () => {
    if (!plannedSql?.trim()) return
    setCmdBusy(true)
    try {
      const r = await api.adminCommand({
        command: cmd.trim(),
        is_approved: true,
        planned_sql: plannedSql,
      })
      setCmdAnswer(r.answer)
      if (r.is_success) setPlannedSql(null)
    } catch (e) {
      setCmdAnswer(e instanceof ApiError ? e.message : 'Lỗi')
    } finally {
      setCmdBusy(false)
    }
  }

  return (
    <div className="modal-backdrop" role="presentation">
      <div
        className="modal panel admin-modal"
        role="dialog"
        aria-labelledby="adm-title"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="modal-head">
          <h2 id="adm-title">Quản trị Hệ thống</h2>
          <button type="button" className="btn icon" onClick={onClose} aria-label="Đóng">
            ×
          </button>
        </div>
        <div className="tabs">
          <button
            type="button"
            className={tab === 'users' ? 'active' : ''}
            onClick={() => setTab('users')}
          >
            Users
          </button>
          <button
            type="button"
            className={tab === 'command' ? 'active' : ''}
            onClick={() => setTab('command')}
          >
            Lệnh (HITL)
          </button>
          <button
            type="button"
            className={tab === 'config' ? 'active' : ''}
            onClick={() => {
              setTab('config')
              void loadConfig()
            }}
          >
            Cấu hình
          </button>
        </div>
        {tab === 'users' ? (
          <div className="admin-users">
            <button
              type="button"
              className="btn secondary"
              onClick={() => void loadUsers()}
              disabled={loadingUsers}
            >
              {loadingUsers ? 'Đang tải…' : 'Tải danh sách'}
            </button>
            {usersErr ? <p className="form-error">{usersErr}</p> : null}
            {users ? (
              <table className="users-table">
                <thead>
                  <tr>
                    <th>User</th>
                    <th>Host</th>
                    <th>Khóa</th>
                  </tr>
                </thead>
                <tbody>
                  {users.map((u, i) => (
                    <tr key={`${u.user}@${u.host}-${i}`}>
                      <td>{u.user}</td>
                      <td>{u.host}</td>
                      <td>{u.locked ? 'Có' : 'Không'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            ) : null}
          </div>
        ) : tab === 'command' ? (
          <div className="admin-command">
            <label>
              Lệnh tiếng Việt
              <textarea
                value={cmd}
                onChange={(e) => setCmd(e.target.value)}
                rows={3}
                disabled={cmdBusy}
              />
            </label>
            <div className="modal-actions">
              <button
                type="button"
                className="btn secondary"
                onClick={() => void runCommandPreview()}
                disabled={cmdBusy}
              >
                Xem SQL
              </button>
              <button
                type="button"
                className="btn primary"
                onClick={() => void runCommandExecute()}
                disabled={cmdBusy || !plannedSql}
              >
                Thực thi đã duyệt
              </button>
            </div>
            {plannedSql ? (
              <pre className="sql-block">
                <code>{plannedSql}</code>
              </pre>
            ) : null}
            {cmdAnswer ? <div className="cmd-answer">{cmdAnswer}</div> : null}
          </div>
        ) : (
          <div className="admin-config">
            <div className="config-group">
              <label htmlFor="api-key">Google Gemini API Key</label>
              <div className="input-with-hint">
                <input
                  id="api-key"
                  type="password"
                  value={apiKey}
                  onChange={(e) => setApiKey(e.target.value)}
                  placeholder={maskedKey || 'Chưa có mã Key'}
                  disabled={saveLoading}
                />
                <small className="hint">Mã Key hiện tại: {maskedKey || 'Trống'}</small>
              </div>
            </div>

            <div className="modal-actions">
              <button
                type="button"
                className="btn primary"
                onClick={() => void handleSaveConfig()}
                disabled={saveLoading || !apiKey.trim()}
              >
                {saveLoading ? 'Đang lưu...' : 'Lưu cấu hình'}
              </button>
            </div>

            {saveMsg ? (
              <div className={`msg-banner ${saveMsg.type === 'ok' ? 'success' : 'error'}`}>
                {saveMsg.text}
              </div>
            ) : null}
          </div>
        )}
      </div>
    </div>
  )
}
