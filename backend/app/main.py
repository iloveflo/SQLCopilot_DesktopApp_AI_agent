from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.api.routes import database, chat, connection, sessions, admin, config_route
import logging

# Cấu hình Logging cơ bản
logging.basicConfig(
    level=settings.LOG_LEVEL,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

# Khởi tạo App
app = FastAPI(
    title=settings.APP_NAME,
    description="Backend API cho Desktop App SQLCopilot",
    version="1.0.0"
)

# Cấu hình CORS - Rất quan trọng cho kiến trúc Desktop-Webview (Tauri)
# Tauri Webview không chạy trên giao thức http:// localhost thông thường.
# Nó dùng tauri://localhost (macOS/Linux) hoặc http://tauri.localhost (Windows).
origins = [
    "http://localhost:5173",     # Cổng mặc định của frontend React (Vite) khi dev
    "tauri://localhost",         # Tauri production trên macOS/Linux
    "http://tauri.localhost",    # Tauri production trên Windows
    "*"                          # Trong môi trường local isolation, có thể dùng "*" cho tiện lợi
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Đăng ký các Router
app.include_router(database.router)
app.include_router(chat.router)
app.include_router(connection.router)
app.include_router(sessions.router)
app.include_router(admin.router)
app.include_router(config_route.router)

@app.get("/", tags=["System"])
def root_info():
    """Endpoint kiểm tra Backend đã khởi động thành công."""
    return {
        "app": settings.APP_NAME,
        "status": "Running",
        "llm_engine": "Groq Llama 3.3 70B",
        "docs_url": "/docs" # Tự động sinh tài liệu OpenAPI
    }

if __name__ == "__main__":
    import uvicorn
    # Chạy server tại 127.0.0.1:8000
    uvicorn.run(app, host="127.0.0.1", port=8000, log_level="info")