import { useState, useEffect } from 'react'
import { api } from '../api/sqlCopilot'
import { ApiError } from '../api/http'

type Props = {
  open: boolean
  onClose: () => void
  sessionId: string | null
  currentSelection: string[]
  onApplied: () => void
}

export function DatabasePickerModal({
  open,
  onClose,
  sessionId,
  currentSelection,
  onApplied,
}: Props) {
  const [list, setList] = useState<string[]>([])
  const [sel, setSel] = useState<Set<string>>(new Set())
  const [busy, setBusy] = useState(false)
  const [err, setErr] = useState<string | null>(null)

  useEffect(() => {
    if (!open) return
    setSel(new Set(currentSelection))
    setErr(null)
    void (async () => {
      try {
        const dbs = await api.listDatabases()
        setList(dbs)
      } catch (e) {
        setErr(e instanceof ApiError ? e.message : 'Không đọc được danh sách DB')
        setList([])
      }
    })()
  }, [open, currentSelection])

  if (!open) return null

  const toggle = (name: string) => {
    setSel((prev) => {
      const n = new Set(prev)
      if (n.has(name)) n.delete(name)
      else n.add(name)
      return n
    })
  }

  const apply = async () => {
    const dbs = [...sel]
    if (dbs.length < 1) {
      setErr('Chọn ít nhất một database.')
      return
    }
    setBusy(true)
    setErr(null)
    try {
      await api.selectDatabases({ databases: dbs })
      if (sessionId) {
        await api.sessionUpdateDatabases(sessionId, { databases: dbs })
      }
      onApplied()
      onClose()
    } catch (e) {
      setErr(e instanceof ApiError ? e.message : 'Lỗi cập nhật')
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="modal-backdrop" role="presentation">
      <div className="modal panel" role="dialog" onClick={(e) => e.stopPropagation()}>
        <h2>Chọn database</h2>
        <ul className="db-checklist">
          {list.map((name) => (
            <li key={name}>
              <label>
                <input type="checkbox" checked={sel.has(name)} onChange={() => toggle(name)} />
                {name}
              </label>
            </li>
          ))}
        </ul>
        {err ? <p className="form-error">{err}</p> : null}
        <div className="modal-actions">
          <button type="button" className="btn secondary" onClick={onClose}>
            Đóng
          </button>
          <button type="button" className="btn primary" disabled={busy} onClick={apply}>
            {busy ? 'Đang lưu…' : 'Áp dụng'}
          </button>
        </div>
      </div>
    </div>
  )
}
