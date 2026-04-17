import sqlite3
import hashlib
import json
import logging
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger(__name__)

# File DB riêng cho Cache để tránh làm chậm chat_memory
cache_db_path = Path.home() / ".sqlcopilot_cache.sqlite3"

def _get_cache_conn():
    conn = sqlite3.connect(str(cache_db_path), check_same_thread=False, timeout=10)
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA synchronous=NORMAL;")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS semantic_cache (
            q_hash      TEXT PRIMARY KEY,
            question    TEXT NOT NULL,
            sql_query   TEXT NOT NULL,
            plan        TEXT,
            created_at  TEXT NOT NULL
        )
    """)
    conn.commit()
    return conn

cache_conn = _get_cache_conn()

def _hash_question(question: str, db_context: str = "") -> str:
    """Chuẩn hóa và băm câu hỏi kèm theo ngữ cảnh Database để tránh nhầm lẫn."""
    clean_q = question.strip().lower()
    # Key = DatabaseContext|Question
    total_key = f"{db_context}|{clean_q}"
    return hashlib.md5(total_key.encode()).hexdigest()

def get_cached_response(question: str, db_context: str = "") -> dict | None:
    """Tìm kiếm câu trả lời trong cache với ngữ cảnh Database cụ thể."""
    q_hash = _hash_question(question, db_context)
    cursor = cache_conn.execute(
        "SELECT sql_query, plan FROM semantic_cache WHERE q_hash = ?", (q_hash,)
    )
    row = cursor.fetchone()
    if row:
        logger.info(f"Semantic Cache Hit for: {question} (Context: {db_context})")
        return {"sql_query": row[0], "plan": row[1]}
    return None

def set_cached_response(question: str, sql: str, plan: str = None, db_context: str = "") -> None:
    """Lưu kết quả vào cache với ngữ cảnh Database cụ thể."""
    q_hash = _hash_question(question, db_context)
    now = datetime.now(timezone.utc).isoformat()
    try:
        cache_conn.execute(
            "INSERT OR REPLACE INTO semantic_cache (q_hash, question, sql_query, plan, created_at) VALUES (?,?,?,?,?)",
            (q_hash, question, sql, plan, now)
        )
        cache_conn.commit()
    except Exception as e:
        logger.error(f"Lỗi khi lưu Cache: {e}")
