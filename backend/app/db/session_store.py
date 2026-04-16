import sqlite3
import uuid
import json
import logging
from datetime import datetime, timezone
from typing import List, Optional

logger = logging.getLogger(__name__)

# Dùng lại kết nối SQLite từ orchestrator (cùng 1 file)
def _get_conn() -> sqlite3.Connection:
    """Trả về connection tới chat_memory.sqlite3 (thread-safe)."""
    from app.agents.orchestrator import sqlite_conn
    return sqlite_conn

def setup_sessions_table() -> None:
    """Khởi tạo bảng chat_sessions nếu chưa tồn tại, hỗ trợ nâng cấp schema."""
    conn = _get_conn()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS chat_sessions (
            session_id   TEXT PRIMARY KEY,
            name         TEXT NOT NULL,
            created_at   TEXT NOT NULL,
            updated_at   TEXT NOT NULL,
            databases    TEXT DEFAULT '[]',
            message_count INTEGER DEFAULT 0,
            user_id      TEXT DEFAULT 'guest_user'
        )
    """)
    # Nâng cấp schema nếu thiếu cột user_id
    try:
        conn.execute("ALTER TABLE chat_sessions ADD COLUMN user_id TEXT DEFAULT 'guest_user'")
    except sqlite3.OperationalError:
        # Cột đã tồn tại hoặc lỗi khác (như bảng không tồn tại - sẽ được tạo bởi CREATE TABLE bên trên)
        pass
    conn.commit()

def setup_dashboard_table() -> None:
    """Khởi tạo bảng pinned_metrics để lưu trữ các biểu đồ đã ghim."""
    conn = _get_conn()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS pinned_metrics (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            title        TEXT NOT NULL,
            chart_config TEXT NOT NULL,
            raw_data     TEXT,
            created_at   TEXT NOT NULL
        )
    """)
    conn.commit()

def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()

def create_session(name: str = None, databases: List[str] = None) -> dict:
    """Tạo session mới, gán cho user hiện tại, trả về metadata session."""
    from app.db.connection import connection_manager
    user_id = connection_manager.get_user_identifier()
    session_id = str(uuid.uuid4())
    now = _now_iso()
    session_name = name or f"\u0110oạn chat {now[:10]}"
    db_json = json.dumps(databases or [], ensure_ascii=False)

    conn = _get_conn()
    conn.execute(
        "INSERT INTO chat_sessions (session_id, name, created_at, updated_at, databases, message_count, user_id) VALUES (?,?,?,?,?,0,?)",
        (session_id, session_name, now, now, db_json, user_id)
    )
    conn.commit()
    return {
        "session_id": session_id,
        "name": session_name,
        "created_at": now,
        "updated_at": now,
        "databases": databases or [],
        "message_count": 0,
        "user_id": user_id
    }

def list_sessions() -> List[dict]:
    """Lấy danh sách sessions c\u1ee7a user hi\u1ec7n t\u1ea1i, mới nhất lên đầu."""
    from app.db.connection import connection_manager
    user_id = connection_manager.get_user_identifier()
    
    conn = _get_conn()
    cursor = conn.execute(
        "SELECT session_id, name, created_at, updated_at, databases, message_count, user_id FROM chat_sessions WHERE user_id = ? ORDER BY updated_at DESC",
        (user_id,)
    )
    rows = cursor.fetchall()
    result = []
    for row in rows:
        result.append({
            "session_id": row[0],
            "name": row[1],
            "created_at": row[2],
            "updated_at": row[3],
            "databases": json.loads(row[4] or "[]"),
            "message_count": row[5],
            "user_id": row[6]
        })
    return result

def rename_session(session_id: str, new_name: str) -> bool:
    """Đổi tên đoạn chat."""
    conn = _get_conn()
    cursor = conn.execute(
        "UPDATE chat_sessions SET name = ?, updated_at = ? WHERE session_id = ?",
        (new_name, _now_iso(), session_id)
    )
    conn.commit()
    return cursor.rowcount > 0

def increment_message_count(session_id: str) -> None:
    """Tăng bộ đếm tin nhắn, cập nhật updated_at và đồng bộ databases/user đang chọn."""
    from app.db.connection import connection_manager
    current_dbs = connection_manager.get_active_databases()
    user_id = connection_manager.get_user_identifier()
    db_json = json.dumps(current_dbs, ensure_ascii=False)
    conn = _get_conn()
    existing = conn.execute(
        "SELECT session_id FROM chat_sessions WHERE session_id = ?", (session_id,)
    ).fetchone()

    if existing:
        conn.execute(
            "UPDATE chat_sessions SET message_count = message_count + 1, updated_at = ?, databases = ? WHERE session_id = ?",
            (_now_iso(), db_json, session_id)
        )
    else:
        # Auto-tạo session nếu Frontend gọi /chat/ask mà không tạo session trước
        now = _now_iso()
        conn.execute(
            "INSERT INTO chat_sessions (session_id, name, created_at, updated_at, databases, message_count, user_id) VALUES (?,?,?,?,?,1,?)",
            (session_id, f"\u0110oạn chat {now[:10]}", now, now, db_json, user_id)
        )
    conn.commit()

def update_session_databases(session_id: str, databases: List[str]) -> bool:
    """Cập nhật danh sách DB đang dùng cho một session cụ thể."""
    conn = _get_conn()
    db_json = json.dumps(databases, ensure_ascii=False)
    cursor = conn.execute(
        "UPDATE chat_sessions SET databases = ?, updated_at = ? WHERE session_id = ?",
        (db_json, _now_iso(), session_id)
    )
    conn.commit()
    return cursor.rowcount > 0

def delete_session_metadata(session_id: str) -> bool:
    """Xóa metadata session khỏi bảng chat_sessions."""
    conn = _get_conn()
    cursor = conn.execute("DELETE FROM chat_sessions WHERE session_id = ?", (session_id,))
    conn.commit()
    return cursor.rowcount > 0

def get_session(session_id: str) -> Optional[dict]:
    """Lấy thông tin 1 session cụ thể."""
    conn = _get_conn()
    row = conn.execute(
        "SELECT session_id, name, created_at, updated_at, databases, message_count, user_id FROM chat_sessions WHERE session_id = ?",
        (session_id,)
    ).fetchone()
    if not row:
        return None
    return {
        "session_id": row[0],
        "name": row[1],
        "created_at": row[2],
        "updated_at": row[3],
        "databases": json.loads(row[4] or "[]"),
        "message_count": row[5],
        "user_id": row[6]
    }

# Tự động khởi tạo bảng khi module được import
setup_sessions_table()
setup_dashboard_table()
