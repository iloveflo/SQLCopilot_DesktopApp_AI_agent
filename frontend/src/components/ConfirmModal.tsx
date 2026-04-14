type Props = {
  open: boolean
  title: string
  message: string
  onClose: () => void
  onConfirm: () => void
  confirmText?: string
  isDanger?: boolean
}

export function ConfirmModal({
  open,
  title,
  message,
  onClose,
  onConfirm,
  confirmText = 'Xác nhận',
  isDanger = true,
}: Props) {
  if (!open) return null

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal panel confirm-modal" onClick={(e) => e.stopPropagation()} style={{ maxWidth: '400px' }}>
        <div className="modal-head">
          <h2 style={{ color: isDanger ? '#dc2626' : 'inherit' }}>{title}</h2>
          <button type="button" className="btn icon" onClick={onClose} aria-label="Đóng">
            ×
          </button>
        </div>
        
        <div className="modal-body" style={{ marginTop: '12px', fontSize: '0.92rem', lineHeight: 1.5 }}>
          {message}
        </div>

        <div className="modal-actions" style={{ marginTop: '24px' }}>
          <button type="button" className="btn secondary" onClick={onClose}>
            Hủy
          </button>
          <button
            type="button"
            className={`btn ${isDanger ? 'danger' : 'primary'}`}
            onClick={() => {
              onConfirm()
              onClose()
            }}
          >
            {confirmText}
          </button>
        </div>
      </div>
    </div>
  )
}
