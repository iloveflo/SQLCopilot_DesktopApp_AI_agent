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
            
            # 3. Chạy các câu lệnh SQL. Hỗ trợ đa truy vấn tách bằng dấu ;
            # Loại bỏ các khoảng trắng và dòng trống
            statements = [s.strip() for s in sql.split(';') if s.strip()]
            
            all_data = []
            last_error = None
            
            for stmt in statements:
                try:
                    result = conn.execute(text(stmt))
                    # Nếu là lệnh SELECT hoặc trả về hàng
                    if result.returns_rows:
                        columns = result.keys()
                        rows = [dict(zip(columns, row)) for row in result.fetchall()]
                        all_data.append({
                            "sql": stmt,
                            "data": rows,
                            "success": True
                        })
                except Exception as stmt_e:
                    last_error = str(stmt_e)
                    all_data.append({
                        "sql": stmt,
                        "data": [],
                        "success": False,
                        "error": last_error
                    })

            if not all_data and last_error:
                return {"success": False, "error": last_error, "data": None}

            return {
                "success": True, 
                "data": all_data[0]["data"] if len(all_data) == 1 else all_data, 
                "multi_data": all_data if len(all_data) > 1 else None,
                "error": None
            }
            
    except Exception as e:
        # Bắt lỗi Syntax hoặc Column not found để feed lại cho Agent 2
        return {"success": False, "error": str(e), "data": None}