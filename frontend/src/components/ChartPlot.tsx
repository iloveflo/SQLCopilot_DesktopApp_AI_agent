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
  
  // Logic xử lý khi click vào cột/mảng trên biểu đồ (Drill-down)
  const handleChartClick = (data: any) => {
    if (!data.points || data.points.length === 0) return;
    const point = data.points[0];
    const label = point.label || point.x; // Tùy loại biểu đồ Pie hay Bar
    
    // Phát sự kiện Drill-down cho hệ thống (được ChatThread bắt lấy)
    const drillDownEvent = new CustomEvent('app:drilldown', {
      detail: { label, value: point.value || point.y }
    });
    window.dispatchEvent(drillDownEvent);
  };

  // 1. Tùy chỉnh màu sắc cho Data (Tô màu các cột)
  const styledData = (config.data as Data[]).map(trace => ({
    ...trace,
    marker: {
      color: 'rgba(99, 102, 241, 0.7)', // Indigo-500 pastel
      line: {
        color: 'rgba(79, 70, 229, 1)',
        width: 1.5
      }
    }
  }));

  const layout = (config.layout ?? {}) as Partial<Layout>
  
  return (
    <Suspense fallback={<div className="chart-loading p-4 text-center text-gray-400 animate-pulse">Đang vẽ biểu đồ…</div>}>
      <Plot
        data={styledData}
        onClick={handleChartClick} // <--- Kích hoạt tính năng Drill-down
        layout={{
          ...layout,
          autosize: true,
          margin: { l: 60, r: 24, t: 56, b: 120 }, 
          paper_bgcolor: 'transparent',
          plot_bgcolor: 'transparent',
          hovermode: 'closest', // Giúp click chính xác hơn
          font: { 
            color: '#cbd5e1', 
            family: 'Inter, sans-serif'
          },
          xaxis: {
            ...layout.xaxis,
            tickangle: -45,
            automargin: true,
            gridcolor: '#334155',
            zerolinecolor: '#475569'
          },
          yaxis: {
            ...layout.yaxis,
            gridcolor: '#334155',
            zerolinecolor: '#475569'
          }
        }}
        style={{ width: '100%', minHeight: 450 }} 
        useResizeHandler
        config={{ responsive: true, displayModeBar: false }}
      />
    </Suspense>
  )
}