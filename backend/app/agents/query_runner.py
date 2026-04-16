import re
from sqlalchemy import text
from app.db.connection import connection_manager

FORBIDDEN_KEYWORDS = [
    r"\bDROP\b", r"\bDELETE\b", r"\bUPDATE\b", r"\bINSERT\b", 
    r"\bALTER\b", r"\bTRUNCATE\b", r"\bGRANT\b", r"\bREVOKE\b"
]

def check_safety(sql: str) -> bool:
    """Quét query bằng Regex để chặn các lệnh DDL/DML."""
    sql_upper = sql.upper()
    for keyword in FORBIDDEN_KEYWORDS:
        if re.search(keyword, sql_upper):
            return False
    return True

def mask_data(data: list, columns: list) -> list:
    """Bôi đen các cột chứa dữ liệu nhạy cảm."""
    SENSITIVE_PATTERNS = [
        "email", "password", "pwd", "token", "secret", "bank", "account", 
        "phone", "sdt", "mat_khau", "cccd", "identity", "salary"
    ]
    
    masked_cols = [col for col in columns if any(p in col.lower() for p in SENSITIVE_PATTERNS)]
    if not masked_cols:
        return data

    new_data = []
    for row in data:
        new_row = dict(row)
        for col in masked_cols:
            if col in new_row and new_row[col] is not None:
                new_row[col] = "********"
        new_data.append(new_row)
    return new_data

def execute_safe_query(sql: str, session_id: str = "default", question: str = "") -> dict:
    """Thực thi SQL, áp dụng Data Masking và ghi Audit Log."""
    import time
    from app.db.session_store import log_query_execution
    
    start_time = time.time()
    
    if not check_safety(sql):
        log_query_execution(session_id, question, sql, 0, "security_blocked")
        return {"success": False, "error": "Bảo mật: Truy vấn chứa từ khóa bị cấm (chỉ hỗ trợ SELECT)."}

    try:
        if not connection_manager.engine:
            return {"success": False, "error": "Chưa kết nối tới cơ sở dữ liệu."}
            
        with connection_manager.engine.connect() as conn:
            # 1. Lấy danh sách database đang được active
            active_dbs = connection_manager.get_active_databases()
            
            # 2. Nếu có DB được chọn, ép MySQL chuyển Context vào DB đó trước
            if active_dbs:
                target_db = active_dbs[0]
                conn.execute(text(f"USE `{target_db}`;"))
            
            # 3. Chạy câu lệnh SQL
            result = conn.execute(text(sql))
            
            # 4. Convert kết quả thành List of Dictionaries
            columns = list(result.keys())
            raw_data = [dict(zip(columns, row)) for row in result.fetchall()]
            
            # 5. Áp dụng Data Masking (Pillar 1 - Security)
            final_data = mask_data(raw_data, columns)
            
            # 6. Ghi Audit Log (Pillar 1 - Audit)
            duration_ms = int((time.time() - start_time) * 1000)
            log_query_execution(session_id, question, sql, duration_ms, "success")
            
            return {"success": True, "data": final_data, "error": None}
            
    except Exception as e:
        duration_ms = int((time.time() - start_time) * 1000)
        log_query_execution(session_id, question, sql, duration_ms, "error")
        return {"success": False, "error": str(e), "data": None}