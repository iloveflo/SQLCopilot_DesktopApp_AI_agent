import logging
import traceback
import time
from sqlalchemy import inspect
from app.db.connection import connection_manager

logger = logging.getLogger(__name__)

# Cache biến toàn cục cho Schema để giảm thiểu truy vấn Database
SCHEMA_CACHE_DATA = None
SCHEMA_CACHE_DBS = None
SCHEMA_CACHE_TIME = 0
SCHEMA_CACHE_TTL = 300  # 5 phút

def invalidate_schema_cache():
    """Xóa bỏ schema cache hiện tại để buộc nạp lại từ CSDL."""
    global SCHEMA_CACHE_DATA, SCHEMA_CACHE_DBS, SCHEMA_CACHE_TIME
    SCHEMA_CACHE_DATA = None
    SCHEMA_CACHE_DBS = None
    SCHEMA_CACHE_TIME = 0
    logger.info("Đã xóa Schema Cache.")

def get_all_tables(schema: str = None) -> list[str]:
    """
    Lấy danh sách tất cả các bảng trong Database.
    FIX: Tránh crash khi schema=None và Engine chưa trỏ vào DB nào.
    """
    try:
        if not connection_manager.engine:
            return []
            
        # Nếu không truyền schema VÀ kết nối hiện tại cũng chưa có DB mặc định -> Trả về []
        # Điều này tránh việc SQLAlchemy (MySQL dialect) cố gắng quote None gây crash.
        if schema is None and not connection_manager.current_db:
            logger.warning("get_all_tables gọi mà không có schema và không có current_db.")
            return []

        inspector = inspect(connection_manager.engine)
        # Đảm bảo schema là string hoặc None, tránh các kiểu dữ liệu lạ
        safe_schema = str(schema) if schema else None
        
        # Nếu safe_schema là string rỗng, cũng nên coi là None hoặc bỏ qua tùy dialect
        # Với MySQL, None sẽ lấy tables của current_db được set trong URL.
        tables = inspector.get_table_names(schema=safe_schema)
        return list(tables) if tables is not None else []
    except Exception as e:
        logger.error(f"Lỗi khi lấy danh sách bảng: {str(e)}")
        logger.error(traceback.format_exc())
        return []

def get_table_schema(table_name: str, db_name: str = None) -> dict:
    """
    Trích xuất siêu dữ liệu (Metadata) chi tiết của một bảng cụ thể.
    """
    try:
        if not connection_manager.engine:
            return {}
        inspector = inspect(connection_manager.engine)
        
        # 1. Lấy thông tin các cột
        columns_info = []
        # BẢN VÁ: Xử lý an toàn nếu get_columns trả về None
        columns = inspector.get_columns(table_name, schema=db_name) or []
        for col in columns:
            # FIX LỖI NoneType: Ép kiểu về chuỗi một cách an toàn
            comment = col.get('comment')
            clean_comment = str(comment or "").replace("_", " ")
            
            columns_info.append({
                "name": str(col.get('name', '')),
                "type": str(col.get('type', '')),
                "nullable": bool(col.get('nullable', True)),
                "comment": clean_comment 
            })
            
        # 2. Lấy Primary Keys
        pk_constraint = inspector.get_pk_constraint(table_name, schema=db_name) or {}
        primary_keys = pk_constraint.get('constrained_columns') or []

        # 3. Lấy Foreign Keys
        foreign_keys = []
        fks = inspector.get_foreign_keys(table_name, schema=db_name) or []
        for fk in fks:
            foreign_keys.append({
                "constrained_columns": fk.get('constrained_columns', []),
                "referred_table": fk.get('referred_table', ''),
                "referred_columns": fk.get('referred_columns', [])
            })

        return {
            "table_name": table_name,
            "db_name": db_name,
            "columns": columns_info,
            "primary_keys": primary_keys,
            "foreign_keys": foreign_keys
        }
    except Exception as e:
        logger.error(f"Lỗi khi đọc schema của bảng {table_name}: {str(e)}")
        logger.error(traceback.format_exc())
        return {}

def get_multi_db_schema_context() -> str:
    """
    Hàm tổng hợp toàn bộ cấu trúc DB. Nhúng vào Prompt cho AI.
    """
    if not connection_manager.engine:
        return "Chưa có kết nối CSDL nào được thiết lập."

    active_dbs = connection_manager.get_active_databases()
    if not active_dbs:
        return "Chưa chọn CSDL nào để phân tích. Vui lòng chọn ít nhất một Database."

    global SCHEMA_CACHE_DATA, SCHEMA_CACHE_DBS, SCHEMA_CACHE_TIME
    current_time = time.time()

    # Kiểm tra cache hợp lệ
    if (
        SCHEMA_CACHE_DATA is not None 
        and SCHEMA_CACHE_DBS == active_dbs
        and (current_time - SCHEMA_CACHE_TIME) < SCHEMA_CACHE_TTL
    ):
        logger.info("Using cached schema context.")
        return SCHEMA_CACHE_DATA

    dialect = connection_manager.engine.dialect.name
    host = getattr(connection_manager, 'current_host', 'localhost')
    port = getattr(connection_manager, 'current_port', 3306)

    # Header thông tin
    if len(active_dbs) > 1:
        mode = "Multi-Database Analysis Mode"
        db_list_str = ", ".join([f"`{db}`" for db in active_dbs])
    else:
        mode = "Single-Database Mode"
        db_list_str = f"`{active_dbs[0]}`"

    schema_text = (
        f"Hệ quản trị CSDL: {dialect} | Server: {host}:{port}\n"
        f"Chế độ: {mode}\n"
        f"CSDL đang phân tích: {db_list_str}\n\n"
    )

    schema_text += "=== DATABASE SCHEMA ===\n\n"

    # Dùng hàm get_all_tables đã sửa để lấy bảng an toàn
    for db_name in active_dbs:
        schema_text += f"📦 DATABASE: `{db_name}`\n" + "─" * 40 + "\n"
        
        tables = get_all_tables(schema=db_name)
        
        if not tables:
            schema_text += "  (Không có bảng nào hoặc lỗi đọc quyền)\n\n"
            continue

        for table in tables:
            schema = get_table_schema(table, db_name=db_name)
            if not schema:
                continue

            full_table_name = f"`{db_name}`.`{table}`" if len(active_dbs) > 1 else f"`{table}`"
            schema_text += f"Table: {full_table_name}\n"

            # Format Columns (Đưa thêm comment vào để AI hiểu ngữ nghĩa)
            cols_str = []
            for col in schema['columns']:
                pk_mark = " (PK)" if col['name'] in schema['primary_keys'] else ""
                comment_mark = f" - {col['comment']}" if col['comment'] else ""
                cols_str.append(f"  - {col['name']} [{col['type']}]{pk_mark}{comment_mark}")
            schema_text += "Columns:\n" + "\n".join(cols_str) + "\n"

            # Format Foreign Keys
            if schema['foreign_keys']:
                fk_str = []
                for fk in schema['foreign_keys']:
                    local_cols = ", ".join(fk['constrained_columns'])
                    ref_cols = ", ".join(fk['referred_columns'])
                    ref_table = f"`{db_name}`.`{fk['referred_table']}`" if len(active_dbs) > 1 else f"`{fk['referred_table']}`"
                    fk_str.append(f"  - FK ({local_cols}) → {ref_table}({ref_cols})")
                schema_text += "Relationships:\n" + "\n".join(fk_str) + "\n"

            schema_text += "\n"

        schema_text += "\n"

    # Lưu vào cache
    SCHEMA_CACHE_DATA = schema_text
    SCHEMA_CACHE_DBS = active_dbs
    SCHEMA_CACHE_TIME = current_time

    return schema_text