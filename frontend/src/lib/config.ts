/**
 * FastAPI chạy ngoài Tauri webview. Build desktop: set VITE_API_BASE nếu backend không ở 127.0.0.1:8000.
 */
export function getApiBase(): string {
  const v = import.meta.env.VITE_API_BASE
  if (v != null && String(v).trim() !== '') {
    return String(v).replace(/\/$/, '')
  }
  return 'http://127.0.0.1:8000'
}
