import { useEffect, useState } from 'react'
import { api } from '../api/sqlCopilot'
import type { PinnedMetric } from '../types/api'
import { ChartPlot } from './ChartPlot'

type Props = {
  isOpen: boolean
  onClose: () => void
  version?: number
  onAddToast?: (message: string, type: 'success' | 'error' | 'info') => void
}

export function DashboardView({ isOpen, onClose, version = 0, onAddToast }: Props) {
  const [metrics, setMetrics] = useState<PinnedMetric[]>([])
  const [loading, setLoading] = useState(false)

  const fetchMetrics = async () => {
    setLoading(true)
    try {
      const data = await api.dashboardMetrics()
      setMetrics(data)
    } catch {
      // ignore
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    if (isOpen) {
      void fetchMetrics()
    }
  }, [isOpen, version])

  const handleUnpin = async (id: number) => {
    // Để giữ tính an toàn, confirm vẫn có thể dùng nhưng lý tưởng là một modal đẹp.
    // Tạm thời tôi chuyển sang Toast cho phần thông báo kết quả.
    if (!confirm('Bạn có chắc chắn muốn xóa biểu đồ này khỏi Dashboard?')) return
    try {
      await api.dashboardUnpin(id)
      setMetrics((prev) => prev.filter((m) => m.id !== id))
      if (onAddToast) onAddToast('Đã xóa biểu đồ khỏi Dashboard.', 'info')
    } catch {
      if (onAddToast) onAddToast('Lỗi khi bỏ ghim biểu đồ.', 'error')
    }
  }

  return (
    <>
      <div className={`dashboard-overlay ${isOpen ? 'open' : ''}`} onClick={onClose} />
      <div className={`dashboard-sidebar ${isOpen ? 'open' : ''}`}>
        <div className="dashboard-header">
          <h2>📊 Dashboard Của Bạn</h2>
          <button type="button" className="btn icon" onClick={onClose} title="Đóng">✕</button>
        </div>
        <div className="dashboard-content">
          {loading ? (
            <p className="chart-loading">Đang tải biểu đồ...</p>
          ) : metrics.length === 0 ? (
            <p className="empty-hint" style={{ textAlign: 'center', marginTop: '20px' }}>
              Chưa có biểu đồ nào được ghim. Hãy hỏi AI một câu hỏi có biểu đồ và bấm "Ghim Dashboard".
            </p>
          ) : (
            metrics.map((m) => (
              <div key={m.id} className="dashboard-card">
                <div className="dashboard-card-actions">
                  <button 
                    type="button"
                    className="btn danger small"
                    onClick={() => handleUnpin(m.id)}
                    title="Xóa khỏi Dashboard"
                  >
                     ✕ Bỏ ghim
                  </button>
                </div>
                <h3 className="dashboard-card-title">{m.title || 'Biểu đồ'}</h3>
                <div className="dashboard-card-date">
                  {new Date(m.created_at).toLocaleString('vi-VN')}
                </div>
                {/* Cho phép hiển thị raw_data trong tooltip/Plotly */}
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
    </>
  )
}
