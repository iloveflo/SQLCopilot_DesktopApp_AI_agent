import { useState } from 'react'
import type { ConnectRequest } from '../types/api'
import { api } from '../api/sqlCopilot'
import { ApiError } from '../api/http'

type Props = {
  open: boolean
  onClose: () => void
  onConnected: () => void
}

export function ConnectionModal({ open, onClose, onConnected }: Props) {
  const [step, setStep] = useState<'credentials' | 'databases'>('credentials')
  const [host, setHost] = useState('127.0.0.1')
  const [port, setPort] = useState(3306)
  const [user, setUser] = useState('root')
  const [password, setPassword] = useState('')
  const [database, setDatabase] = useState('')
  const [serverDbs, setServerDbs] = useState<string[]>([])
  const [selectedDbs, setSelectedDbs] = useState<Set<string>>(new Set())
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)

  if (!open) return null

  const resetForm = () => {
    setStep('credentials')
    setServerDbs([])
    setSelectedDbs(new Set())
    setError(null)
  }

  const handleConnect = async (e: React.FormEvent) => {
    e.preventDefault()
    setBusy(true)
    setError(null)
    const body: ConnectRequest = {
      host: host.trim(),
      port: Number(port) || 3306,
      user: user.trim(),
      password,
      database: database.trim() || undefined,
    }
    try {
      const res = await api.connect(body)
      setServerDbs(res.databases)
      const initial = new Set<string>()
      if (res.current_db) initial.add(res.current_db)
      else if (res.databases.length === 1) initial.add(res.databases[0])
      setSelectedDbs(initial)
      setStep('databases')
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Kết nối thất bại.')
    } finally {
      setBusy(false)
    }
  }

  const toggleDb = (name: string) => {
    setSelectedDbs((prev) => {
      const next = new Set(prev)
      if (next.has(name)) next.delete(name)
      else next.add(name)
      return next
    })
  }

  const handleConfirmDbs = async () => {
    const list = [...selectedDbs]
    if (list.length < 1) {
      setError('Chọn ít nhất một database.')
      return
    }
    setBusy(true)
    setError(null)
    try {
      await api.selectDatabases({ databases: list })
      resetForm()
      onConnected()
      onClose()
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Không thể áp dụng lựa chọn DB.')
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="modal-backdrop" role="presentation">
      <div
        className="modal panel"
        role="dialog"
        aria-labelledby="conn-title"
        onClick={(ev) => ev.stopPropagation()}
      >
        <h2 id="conn-title">Kết nối MySQL</h2>
        <p className="modal-hint">Vui lòng nhập thông tin kết nối tới máy chủ Database của bạn.</p>

        {step === 'credentials' ? (
          <form onSubmit={handleConnect} className="form-grid">
            <label>
              Host
              <input value={host} onChange={(e) => setHost(e.target.value)} required />
            </label>
            <label>
              Cổng
              <input
                type="number"
                value={port}
                onChange={(e) => setPort(Number(e.target.value))}
                min={1}
                max={65535}
              />
            </label>
            <label>
              User
              <input value={user} onChange={(e) => setUser(e.target.value)} required />
            </label>
            <label>
              Mật khẩu
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                autoComplete="off"
              />
            </label>
            <label className="span-2">
              Database ban đầu (tùy chọn)
              <input
                value={database}
                onChange={(e) => setDatabase(e.target.value)}
                placeholder="Để trống nếu chỉ cần liệt kê DB"
              />
            </label>
            {error ? <p className="form-error span-2">{error}</p> : null}
            <div className="modal-actions span-2">
              <button type="button" className="btn secondary" onClick={onClose}>
                Hủy
              </button>
              <button type="submit" className="btn primary" disabled={busy}>
                {busy ? 'Đang kết nối…' : 'Kết nối'}
              </button>
            </div>
          </form>
        ) : (
          <div className="db-pick">
            <p>Chọn một hoặc nhiều database để AI phân tích (cross-DB).</p>
            <ul className="db-checklist">
              {serverDbs.map((name) => (
                <li key={name}>
                  <label>
                    <input
                      type="checkbox"
                      checked={selectedDbs.has(name)}
                      onChange={() => toggleDb(name)}
                    />
                    {name}
                  </label>
                </li>
              ))}
            </ul>
            {error ? <p className="form-error">{error}</p> : null}
            <div className="modal-actions">
              <button
                type="button"
                className="btn secondary"
                onClick={() => {
                  setStep('credentials')
                  setError(null)
                }}
              >
                Quay lại
              </button>
              <button type="button" className="btn primary" disabled={busy} onClick={handleConfirmDbs}>
                {busy ? 'Đang lưu…' : 'Xác nhận'}
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
