import { useState, useEffect, useRef } from 'react'

type Props = {
  open: boolean
  onClose: () => void
  onSave: (newName: string) => void
  initialName: string
}

export function RenameModal({ open, onClose, onSave, initialName }: Props) {
  const [name, setName] = useState(initialName)
  const inputRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    if (open) {
      setName(initialName)
      setTimeout(() => inputRef.current?.focus(), 100)
    }
  }, [open, initialName])

  if (!open) return null

  const handleSave = () => {
    if (name.trim()) {
      onSave(name.trim())
      onClose()
    }
  }

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal panel rename-modal" onClick={(e) => e.stopPropagation()}>
        <div className="modal-head">
          <h2 id="rename-title">Đổi tên đoạn chat</h2>
          <button type="button" className="btn icon" onClick={onClose} aria-label="Đóng">
            ×
          </button>
        </div>
        
        <div className="modal-body" style={{ marginTop: '16px' }}>
          <label htmlFor="session-name" style={{ fontSize: '0.82rem', marginBottom: '8px', display: 'block' }}>
            Tên mới
          </label>
          <input
            id="session-name"
            ref={inputRef}
            type="text"
            className="form-input"
            value={name}
            onChange={(e) => setName(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter') handleSave()
              if (e.key === 'Escape') onClose()
            }}
            style={{
              width: '100%',
              padding: '10px',
              borderRadius: '8px',
              border: '1px solid var(--border)',
              background: 'var(--bg)',
              color: 'var(--text-h)',
              font: 'inherit'
            }}
          />
        </div>

        <div className="modal-actions" style={{ marginTop: '20px' }}>
          <button type="button" className="btn secondary" onClick={onClose}>
            Hủy
          </button>
          <button type="button" className="btn primary" onClick={handleSave} disabled={!name.trim()}>
            Lưu thay đổi
          </button>
        </div>
      </div>
    </div>
  )
}
