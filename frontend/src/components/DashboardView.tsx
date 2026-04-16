import { useEffect, useState } from 'react'
import { api } from '../api/sqlCopilot'
import type { PinnedMetric } from '../types/api'
import { ChartPlot } from './ChartPlot'

export function DashboardView() {
  const [metrics, setMetrics] = useState<PinnedMetric[]>([])
  const [loading, setLoading] = useState(true)

  const fetchMetrics = async () => {
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
    void fetchMetrics()
  }, [])

  const handleUnpin = async (id: number) => {
    try {
      await api.dashboardUnpin(id)
      setMetrics((prev) => prev.filter((m) => m.id !== id))
    } catch {
      alert('Lỗi khi bỏ ghim biểu đồ.')
    }
  }

  if (loading) {
    return <div className="p-8 text-center text-[var(--text-dim)]">Đang tải biểu đồ...</div>
  }

  if (metrics.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center h-full p-8 text-center" style={{ color: 'var(--text-dim)' }}>
        <span style={{ fontSize: '3rem', marginBottom: '1rem', display: 'block' }}>📌</span>
        <h2>Chưa có biểu đồ nào được ghim</h2>
        <p>Hãy hỏi Copilot vẽ biểu đồ và bấm "Ghim lên Dashboard" để tạo bảng điều khiển riêng của bạn.</p>
      </div>
    )
  }

  return (
    <div className="dashboard-container" style={{ padding: '2rem', overflowY: 'auto', height: '100%', background: 'rgba(15, 23, 42, 0.4)' }}>
      <h2 style={{ fontSize: '1.5rem', fontWeight: 600, color: 'var(--text-bright)', marginBottom: '2rem' }}>
        📊 Bảng Điều Khiển Tổng Quan
      </h2>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(500px, 1fr))', gap: '2rem' }}>
        {metrics.map((m) => (
          <div key={m.id} className="bubble assistant" style={{ display: 'block', maxWidth: 'none', background: 'rgba(30, 41, 59, 0.7)' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
              <h3 style={{ fontSize: '1.1rem', margin: 0, color: 'var(--accent-color)' }}>{m.title}</h3>
              <button 
                className="btn secondary" 
                style={{ fontSize: '0.8rem', padding: '4px 8px' }}
                onClick={() => handleUnpin(m.id)}
                title="Bỏ ghim khỏi Dashboard"
              >
                ✕ Bỏ ghim
              </button>
            </div>
            
            {m.chart_config && (
              <div style={{ background: 'rgba(0,0,0,0.2)', borderRadius: '12px', overflow: 'hidden' }}>
                 <ChartPlot config={m.chart_config} />
              </div>
            )}
            
            {/* Ẩn data table trên dashboard cho gọn, nếu người dùng muốn có thể hiện nút xem data */}
          </div>
        ))}
      </div>
    </div>
  )
}
