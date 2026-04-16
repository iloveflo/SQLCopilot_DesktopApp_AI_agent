import { lazy, Suspense, ComponentProps } from 'react'
import type { Data, Layout } from 'plotly.js'
import type { PlotlyChartConfig } from '../types/api'
import PlotlyComponent from 'react-plotly.js'

const Plot = lazy(async () => {
  const mod = await import('react-plotly.js') as any;
  return { default: mod.default?.default || mod.default || mod };
}) as React.FC<ComponentProps<typeof PlotlyComponent>>; 

function isPlotlyConfig(v: unknown): v is PlotlyChartConfig {
  return (
    v != null &&
    typeof v === 'object' &&
    'data' in v &&
    Array.isArray((v as PlotlyChartConfig).data)
  )
}

export function ChartPlot({ config, rawData, onPin }: { config: unknown, rawData?: unknown, onPin?: (config: unknown, data: unknown) => void }) {
  if (!isPlotlyConfig(config)) return null
  
  // Tùy chỉnh màu đa dạng dựa vào loại biểu đồ
  const styledData = (config.data as Data[]).map(trace => {
    let customTrace = { ...trace } as any;
    if (trace.type === 'bar') {
      customTrace.marker = {
        color: 'rgba(59, 130, 246, 0.7)', // Blue
        line: { color: 'rgba(37, 99, 235, 1)', width: 1.5 }
      }
    } else if (trace.type === 'pie') {
      // Dùng bảng màu đa sắc cao cấp cho pie chart (Pastel Vivid)
      customTrace.marker = {
        colors: [
           '#3b82f6', '#10b981', '#f59e0b', '#ef4444', 
           '#8b5cf6', '#ec4899', '#06b6d4', '#f97316'
        ],
        line: { color: '#1e293b', width: 2 }
      }
    } else if (trace.type === 'scatter' && trace.mode === 'lines') {
      // Line or Area chart
      customTrace.line = { color: '#10b981', width: 3 }
      if (trace.fill) {
        customTrace.fillcolor = 'rgba(16, 185, 129, 0.2)'
      }
    } else if (trace.type === 'scatter') {
      // Pure scatter
      customTrace.marker = { color: '#f59e0b', size: 10, line: { color: '#d97706', width: 1 } }
    }
    return customTrace as Data;
  });

  const layout = (config.layout ?? {}) as Partial<Layout>
  
  return (
    <Suspense fallback={<div className="chart-loading p-4 text-center text-gray-400 animate-pulse">Đang vẽ biểu đồ…</div>}>
      <div style={{ position: 'relative' }}>
      {onPin && (
          <button 
            type="button"
            className="btn secondary" 
            style={{ position: 'absolute', top: 10, right: 10, zIndex: 10, padding: '4px 8px', fontSize: '12px', background: 'rgba(0,0,0,0.5)', borderColor: '#475569' }}
            onClick={(e) => { e.preventDefault(); onPin(config, rawData); }}
            title="Ghim biểu đồ này vào Dashboard"
          >
            📌 Ghim Dashboard
          </button>
      )}
      <Plot
        data={styledData}
        layout={{
          ...layout,
          autosize: true,
          // 2. Tăng margin bottom (b) lên 120px để có chỗ chứa chữ nghiêng
          margin: { l: 60, r: 24, t: 56, b: 120 }, 
          paper_bgcolor: 'transparent',
          plot_bgcolor: 'transparent',
          font: { 
            color: '#cbd5e1', // Đổi toàn bộ chữ thành màu xám sáng cho dễ đọc
            family: 'Inter, sans-serif'
          },
          xaxis: {
            ...layout.xaxis,
            tickangle: -45, // 3. Xoay nghiêng chữ 45 độ
            automargin: true, // Tự động đẩy lề nếu chữ quá dài
            gridcolor: '#334155', // Màu lưới dọc chìm, không bị gắt
            zerolinecolor: '#475569'
          },
          yaxis: {
            ...layout.yaxis,
            gridcolor: '#334155', // Màu lưới ngang chìm
            zerolinecolor: '#475569'
          }
        }}
        style={{ width: '100%', minHeight: 450 }} 
        useResizeHandler
        config={{ responsive: true, displayModeBar: false }} // Tắt cái thanh menu rườm rà phía trên
      />
      </div>
    </Suspense>
  )
}