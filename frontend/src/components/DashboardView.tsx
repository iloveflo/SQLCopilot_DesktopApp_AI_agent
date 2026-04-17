import { useEffect, useState, useRef } from 'react'
import { api } from '../api/sqlCopilot'
import type { PinnedMetric } from '../types/api'
import { ChartPlot } from './ChartPlot'
import { ConfirmModal } from './ConfirmModal'

type Props = {
  isOpen: boolean
  onClose: () => void
  userId: string
  refreshVersion?: number
  onUnpinMetric?: (id: number) => void
  onAddToast?: (msg: string, type?: 'success' | 'error' | 'info') => void
}

export function DashboardView({ 
  isOpen, 
  onClose, 
  userId, 
  refreshVersion = 0,
  onUnpinMetric,
  onAddToast
}: Props) {
  const [metrics, setMetrics] = useState<PinnedMetric[]>([])
  const [loading, setLoading] = useState(false)
  
  // Custom Confirmation State
  const [confirmDeleteId, setConfirmDeleteId] = useState<number | null>(null)
  
  // Resizing State
  const [sidebarWidth, setSidebarWidth] = useState(500)
  const [isResizing, setIsResizing] = useState(false)
  const sidebarRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (isOpen) {
      void fetchMetrics()
    }
  }, [isOpen, userId, refreshVersion])

  const fetchMetrics = async () => {
    setLoading(true)
    try {
      const data = await api.dashboardMetrics()
      setMetrics(data)
    } catch (err) {
      console.error('Lỗi khi tải Dashboard:', err)
    } finally {
      setLoading(false)
    }
  }

  const handleDelete = async (id: number) => {
    try {
      const res = await api.dashboardUnpin(id)
      if (res.is_success) {
        setMetrics(prev => prev.filter(m => m.id !== id))
        onUnpinMetric?.(id)
        onAddToast?.('Đã xóa biểu đồ khỏi Dashboard', 'info')
      }
    } catch (err) {
      onAddToast?.('Lỗi khi xóa biểu đồ', 'error')
    } finally {
      setConfirmDeleteId(null)
    }
  }

  // Resizing Logic
  const startResizing = (e: React.MouseEvent) => {
    e.preventDefault()
    setIsResizing(true)
  }

  useEffect(() => {
    const handleMouseMove = (e: MouseEvent) => {
      if (!isResizing) return
      // Tính toán chiều rộng mới từ bên phải màn hình
      const newWidth = window.innerWidth - e.clientX
      if (newWidth >= 400 && newWidth <= window.innerWidth * 0.9) {
        setSidebarWidth(newWidth)
      }
    }
    const handleMouseUp = () => setIsResizing(false)

    if (isResizing) {
      window.addEventListener('mousemove', handleMouseMove)
      window.addEventListener('mouseup', handleMouseUp)
    }
    return () => {
      window.removeEventListener('mousemove', handleMouseMove)
      window.removeEventListener('mouseup', handleMouseUp)
    }
  }, [isResizing])

  return (
    <>
      <div className={`dashboard-overlay ${isOpen ? 'open' : ''}`} onClick={onClose} />
      <div 
        ref={sidebarRef}
        className={`dashboard-sidebar ${isOpen ? 'open' : ''} ${isResizing ? 'resizing' : ''}`}
        style={{ width: `${sidebarWidth}px`, right: isOpen ? '0' : `-${sidebarWidth}px` }}
      >
        {/* Resize Handle */}
        <div 
          className={`resize-handle ${isResizing ? 'active' : ''}`} 
          onMouseDown={startResizing}
        />

        <div className="dashboard-header">
          <h2>📊 Dashboard của tôi</h2>
          <button className="btn-close" onClick={onClose}>&times;</button>
        </div>
        
        <div className="dashboard-content">
          {loading && metrics.length === 0 ? (
            <div className="loading-spinner">Đang tải...</div>
          ) : metrics.length === 0 ? (
            <div className="empty-state">Chưa có biểu đồ nào được ghim.</div>
          ) : (
            metrics.map(m => (
              <div key={m.id} className="dashboard-card shadow-sm">
                <h3 className="dashboard-card-title">{m.title || 'Biểu đồ'}</h3>
                <div className="dashboard-card-date">
                  Ghim lúc: {new Date(m.created_at).toLocaleString('vi-VN')}
                </div>
                <div className="dashboard-card-actions">
                  <button 
                    className="btn-icon danger" 
                    title="Xóa khỏi Dashboard"
                    onClick={() => setConfirmDeleteId(m.id)}
                  >
                    &times;
                  </button>
                </div>
                {m.chart_config && (
                  <div style={{ marginTop: '10px' }}>
                    <ChartPlot config={m.chart_config} rawData={m.raw_data} />
                  </div>
                )}
              </div>
            ))
          )}
        </div>
      </div>

      <ConfirmModal 
        isOpen={confirmDeleteId !== null}
        title="Xác nhận xóa"
        message="Bạn có chắc chắn muốn xóa biểu đồ này khỏi Dashboard của mình không?"
        confirmLabel="Xóa ngay"
        cancelLabel="Để sau"
        type="danger"
        onConfirm={() => confirmDeleteId && handleDelete(confirmDeleteId)}
        onCancel={() => setConfirmDeleteId(null)}
      />
    </>
  )
}
