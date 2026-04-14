from fastapi import APIRouter, HTTPException
from typing import List
from app.schemas.connection_schema import ConnectRequest, UseDatabaseRequest, SelectDatabasesRequest
from app.db.connection import connection_manager
import logging

router = APIRouter(prefix="/connection", tags=["Database Management"])
logger = logging.getLogger(__name__)

@router.get("/status", summary="Trạng thái kết nối hiện tại (dùng cho Status Bar)")
def get_connection_status():
    """
    Trả về toàn bộ thông tin kết nối hiện tại.
    Frontend gọi API này khi khởi động app hoặc sau khi đổi kết nối 
    để cập nhật thanh trạng thái (status bar) phía dưới màn hình.
    """
    is_connected = connection_manager.engine is not None
    ping = connection_manager.ping() if is_connected else {"status": "error"}
    return {
        "is_connected": is_connected,
        "server": f"{connection_manager.current_host}:{connection_manager.current_port}" if is_connected else None,
        "current_user": connection_manager.current_user,
        "is_admin": connection_manager.is_admin if is_connected else False,
        "active_databases": connection_manager.get_active_databases(),
        "health": ping.get("status"),
        "message": ping.get("message", "Chưa kết nối.")
    }

@router.post("/connect", summary="Thiết lập kết nối Server")
def connect_to_server(req: ConnectRequest):
    """
    Connect tới MySQL Server với credentials do user cung cấp.
    """
    try:
        connection_manager.connect(
            host=req.host,
            port=req.port,
            user=req.user,
            password=req.password,
            database=req.database or ""
        )
        # Fetch the databases available instantly
        dbs = connection_manager.get_databases()
        return {
            "message": "Kết nối Server thành công",
            "databases": dbs,
            "current_db": req.database or ""
        }
    except Exception as e:
        logger.error(f"Lỗi connect server: {e}")
        raise HTTPException(status_code=400, detail=f"Không thể kết nối Server: {str(e)}")

@router.post("/use_db", summary="Chuyển CSDL đang làm việc")
def switch_database(req: UseDatabaseRequest):
    """
    Giống lệnh USE database_name; 
    Switch ngữ cảnh AI sang một Database khác hiện có trên server.
    """
    try:
        connection_manager.use_database(req.database)
        return {
            "message": f"Đã chuyển sang không gian lưu trữ: {req.database}",
            "current_db": req.database
        }
    except Exception as e:
        logger.error(f"Lỗi chuyển DB: {e}")
        raise HTTPException(status_code=400, detail=f"Không thể chuyển DB: {str(e)}")

@router.get("/list", response_model=List[str], summary="Lấy danh sách DB hiện tại")
def list_databases():
    """Lấy lại danh sách DB mà ko cần đăng nhập lại từ đầu."""
    try:
        dbs = connection_manager.get_databases()
        return dbs
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Lỗi: {str(e)}")

@router.post("/disconnect", summary="Ngắt kết nối khỏi Database")
def disconnect_server():
    """Đăng xuất, xóa toàn bộ thông tin đăng nhập trong phiên làm việc."""
    try:
        connection_manager.disconnect()
        return {"message": "Đã ngắt kết nối an toàn."}
    except Exception as e:
        logger.error(f"Lỗi ngắt kết nối: {e}")
        raise HTTPException(status_code=400, detail=f"Lỗi ngắt kết nối: {str(e)}")

@router.post("/select_databases", summary="Chọn một hoặc nhiều DB để phân tích (Cross-DB Mode)")
def select_databases(req: SelectDatabasesRequest):
    """
    Cho phép User tick chọn nhiều Database cùng lúc để AI phân tích xuyên suốt.
    Khi đó AI sẽ gom Schema của tất cả các DB được chọn và có thể viết câu SQL
    kiểu: SELECT * FROM `db1`.`orders` JOIN `db2`.`customers` ON ...
    """
    try:
        connection_manager.set_active_databases(req.databases)
        mode = "Multi-Database" if len(req.databases) > 1 else "Single-Database"
        return {
            "message": f"Đã chuyển sang chế độ {mode}.",
            "active_databases": req.databases,
            "mode": mode
        }
    except Exception as e:
        logger.error(f"Lỗi khi chọn databases: {e}")
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/active_databases", response_model=List[str], summary="Xem danh sách DB đang được chọn")
def get_active_databases():
    """Trả về danh sách DB đang được AI phân tích hiện tại."""
    return connection_manager.get_active_databases()
