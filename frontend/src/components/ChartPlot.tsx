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

export function ChartPlot({ config }: { config: unknown }) {
  if (!isPlotlyConfig(config)) return null
  
  // 1. Tùy chỉnh màu sắc cho Data (Tô màu các cột)
  const styledData = (config.data as Data[]).map(trace => ({
    ...trace,
    marker: {
      color: 'rgba(59, 130, 246, 0.7)', // Màu xanh da trời pastel (Tailwind blue-500)
      line: {
        color: 'rgba(37, 99, 235, 1)',  // Viền cột đậm hơn chút
        width: 1.5
      }
    }
  }));

  const layout = (config.layout ?? {}) as Partial<Layout>
  
  return (
    <Suspense fallback={<div className="chart-loading p-4 text-center text-gray-400 animate-pulse">Đang vẽ biểu đồ…</div>}>
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
    </Suspense>
  )
}