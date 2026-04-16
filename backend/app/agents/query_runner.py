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

def execute_safe_query(sql: str) -> dict:
    """Thực thi SQL và bắt exception chuyên sâu."""
    if not check_safety(sql):
        return {"success": False, "error": "Bảo mật: Truy vấn chứa từ khóa bị cấm (chỉ hỗ trợ SELECT)."}

    try:
        if not connection_manager.engine:
            return {"success": False, "error": "Chưa kết nối tới cơ sở dữ liệu."}
            
        with connection_manager.engine.connect() as conn:
            # --- BẢN VÁ BẮT ĐẦU TỪ ĐÂY ---
            # 1. Lấy danh sách database đang được active (ví dụ: ['florentic'])
            active_dbs = connection_manager.get_active_databases()
            
            # 2. Nếu có DB được chọn, ép MySQL chuyển Context vào DB đó trước
            if active_dbs:
                target_db = active_dbs[0]
                conn.execute(text(f"USE `{target_db}`;"))
            # --- KẾT THÚC BẢN VÁ ---
            
            # 3. Chạy câu lệnh SQL thực tế do Gemma 4 sinh ra
            result = conn.execute(text(sql))
            
            # Convert kết quả thành List of Dictionaries
            columns = result.keys()
            data = [dict(zip(columns, row)) for row in result.fetchall()]
            return {"success": True, "data": data, "error": None}
            
    except Exception as e:
        # Bắt lỗi Syntax hoặc Column not found để feed lại cho Agent 2
        return {"success": False, "error": str(e), "data": None}