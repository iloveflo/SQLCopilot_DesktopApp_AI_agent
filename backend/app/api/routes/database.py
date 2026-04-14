from fastapi import APIRouter, HTTPException
from typing import List
import logging
from app.db.connection import connection_manager
from app.db.metadata import get_all_tables, get_table_schema
from app.schemas.db_schema import TableSchema

router = APIRouter(prefix="/db", tags=["Database Management"])
logger = logging.getLogger(__name__)

@router.get("/health", summary="Kiểm tra trạng thái kết nối Cơ sở dữ liệu")
def check_db_health():
    """
    Ping CSDL. Frontend gọi API này định kỳ (ví dụ mỗi 30s) hoặc 
    khi khởi động app để hiển thị đèn trạng thái (Xanh/Đỏ).
    """
    result = connection_manager.ping()
    if result["status"] == "error":
        raise HTTPException(status_code=503, detail=result["message"])
    return result

@router.get("/schema", response_model=List[TableSchema], summary="Trích xuất toàn bộ Lược đồ CSDL")
def get_full_schema():
    """
    Duyệt qua tất cả các bảng của TẤT CẢ Database đang chọn và trả về cấu trúc chi tiết.
    Thích hợp để Frontend render một thanh Sidebar chứa Data Dictionary.
    """
    try:
        # Lấy danh sách DB đang được active (đã chọn ở Sidebar)
        active_dbs = connection_manager.get_active_databases()
        schema_list = []
        
        if not active_dbs:
            # Nếu chưa chọn DB nào, không cần quét (tránh crash)
            return []

        for db_name in active_dbs:
            tables = get_all_tables(schema=db_name)
            for table_name in tables:
                table_info = get_table_schema(table_name, db_name=db_name)
                if table_info:
                    schema_list.append(TableSchema(**table_info))
                    
        return schema_list
    except Exception as e:
        logger.error(f"Lỗi khi lấy schema: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail="Không thể đọc Lược đồ Cơ sở dữ liệu.")