from fastapi import APIRouter, HTTPException
from typing import List
import logging
from app.schemas.session_schema import SessionCreate, SessionRename, SessionResponse
from app.schemas.connection_schema import SelectDatabasesRequest
from app.db.session_store import (
    create_session, list_sessions, rename_session,
    delete_session_metadata, get_session, update_session_databases
)
from app.agents.orchestrator import clear_session
from app.db.connection import connection_manager

router = APIRouter(prefix="/sessions", tags=["Chat Sessions"])
logger = logging.getLogger(__name__)

@router.post("", response_model=SessionResponse, summary="Tạo đoạn chat mới")
def new_session(req: SessionCreate):
    """
    Tạo một đoạn chat mới, trả về session_id.
    Frontend dùng session_id này để bắt đầu nhắn tin.
    Gọi API này khi user bấm nút '+' hoặc 'Đoạn chat mới'.
    """
    try:
        session = create_session(name=req.name, databases=req.databases)
        return SessionResponse(**session)
    except Exception as e:
        logger.error(f"Lỗi tạo session: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("", response_model=List[SessionResponse], summary="Lấy danh sách tất cả đoạn chat")
def get_sessions():
    """
    Trả về danh sách tất cả các đoạn chat đã tạo, mới nhất lên đầu.
    Frontend dùng để render sidebar (giống danh sách chat bên trái của ChatGPT).
    """
    try:
        return [SessionResponse(**s) for s in list_sessions()]
    except Exception as e:
        logger.error(f"Lỗi lấy danh sách sessions: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{session_id}", response_model=SessionResponse, summary="Lấy thông tin một đoạn chat")
def get_session_info(session_id: str):
    """Lấy metadata của một đoạn chat cụ thể."""
    session = get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Không tìm thấy đoạn chat này.")
    return SessionResponse(**session)

@router.patch("/{session_id}", response_model=SessionResponse, summary="Đổi tên đoạn chat")
def update_session_name(session_id: str, req: SessionRename):
    """
    Đổi tên đoạn chat. Frontend gọi khi user double-click vào tên
    hoặc chọn 'Đổi tên' từ menu ngữ cảnh (right-click).
    """
    success = rename_session(session_id, req.name)
    if not success:
        raise HTTPException(status_code=404, detail="Không tìm thấy đoạn chat để đổi tên.")
    session = get_session(session_id)
    return SessionResponse(**session)

@router.delete("/{session_id}", summary="Xóa đoạn chat")
def delete_session(session_id: str):
    """
    Xóa hoàn toàn đoạn chat: xóa metadata VÀ toàn bộ nội dung hội thoại khỏi LangGraph SQLite.
    """
    clear_session(session_id)
    delete_session_metadata(session_id)
    return {"message": "Đã xóa đoạn chat thành công.", "session_id": session_id}

@router.post("/{session_id}/restore", summary="Khôi phục kết nối DB của đoạn chat")
def restore_session_context(session_id: str):
    """
    Khi user chuyển sang một đoạn chat cũ, gọi API này để Backend trỏ lại
    đúng Database mà đoạn chat đó đang dùng lần cuối.
    
    Luồng Frontend:
    1. User click vào đoạn chat trong Sidebar
    2. Frontend gọi POST /sessions/{id}/restore
    3. Backend đọc databases của session đó → set vào connection_manager
    4. Frontend load lịch sử chat từ GET /chat/history/{id}
    """
    session = get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Không tìm thấy đoạn chat này.")
    
    saved_dbs = session.get("databases", [])
    restored = []
    failed = []
    
    if saved_dbs and connection_manager.engine:
        # Chỉ restore những DB vẫn còn tồn tại trên server
        try:
            available = connection_manager.get_databases()
            restored = [db for db in saved_dbs if db in available]
            failed = [db for db in saved_dbs if db not in available]
            if restored:
                connection_manager.set_active_databases(restored)
        except Exception as e:
            logger.warning(f"Không thể restore DB context: {e}")
    
    return {
        "session_id": session_id,
        "restored_databases": restored,
        "unavailable_databases": failed,
        "message": f"Đã khôi phục ngữ cảnh: {restored}" if restored else "Không có DB nào được lưu trong đoạn chat này."
    }

@router.put("/{session_id}/databases", response_model=SessionResponse, summary="Cập nhật DB đang dùng trong đoạn chat")
def update_session_db(session_id: str, req: SelectDatabasesRequest):
    """
    Cho phép user thay đổi Database đang dùng ngay trong đoạn chat hiện tại.
    Vừa cập nhật metadata session VÀ connection_manager cùng lúc.
    """
    if not connection_manager.engine:
        raise HTTPException(status_code=400, detail="Chưa kết nối tới Server.")
    try:
        connection_manager.set_active_databases(req.databases)
        update_session_databases(session_id, req.databases)
        session = get_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Không tìm thấy đoạn chat.")
        return SessionResponse(**session)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
