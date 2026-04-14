from fastapi import APIRouter, HTTPException
from sqlalchemy import text
import logging
from app.schemas.admin_schema import AdminCommandRequest, AdminCommandResponse
from app.agents.admin_agent import generate_admin_sql
from app.db.connection import connection_manager

router = APIRouter(prefix="/admin", tags=["Admin — User Management"])
logger = logging.getLogger(__name__)

def _require_admin():
    """Guard function: chặn non-admin truy cập các endpoint nhạy cảm."""
    if not connection_manager.engine:
        raise HTTPException(status_code=401, detail="Chưa kết nối tới Database Server.")
    if not connection_manager.is_admin:
        raise HTTPException(
            status_code=403,
            detail="Truy cập bị từ chối. Chỉ tài khoản Root hoặc Admin mới có quyền thực hiện thao tác này."
        )

@router.post("/command", response_model=AdminCommandResponse, summary="Lập kế hoạch lệnh quản trị (HITL)")
def admin_command(req: AdminCommandRequest):
    """
    Nhận lệnh tiếng Việt từ Root Admin, sinh ra SQL quản trị user MySQL.
    
    Luồng hoạt động (luôn bắt buộc HITL):
    - Bước 1: Gọi với is_approved=False → nhận SQL kế hoạch để xem trước.
    - Bước 2: Sau khi Root kiểm tra SQL, gọi lại với is_approved=True + planned_sql để thực thi.
    """
    _require_admin()

    # Bước 2: Thực thi SQL đã được Root duyệt
    if req.is_approved:
        if not req.planned_sql:
            raise HTTPException(status_code=400, detail="Thiếu planned_sql để thực thi. Vui lòng truyền lại SQL đã duyệt.")
        try:
            # Admin queries có thể chứa nhiều statements, tách bởi ;
            statements = [s.strip() for s in req.planned_sql.split(";") if s.strip()]
            with connection_manager.engine.connect() as conn:
                for stmt in statements:
                    conn.execute(text(stmt))
                conn.commit()
            return AdminCommandResponse(
                answer=f"✅ Đã thực thi thành công {len(statements)} lệnh SQL quản trị.",
                planned_sql=req.planned_sql,
                needs_approval=False,
                is_success=True
            )
        except Exception as e:
            logger.error(f"Lỗi thực thi admin SQL: {e}")
            return AdminCommandResponse(
                answer="❌ Lỗi khi thực thi lệnh SQL quản trị.",
                planned_sql=req.planned_sql,
                needs_approval=False,
                is_success=False,
                error_message=str(e)
            )

    # Bước 1: Lập kế hoạch SQL (chưa thực thi)
    result = generate_admin_sql(req.command)

    if not result.sql_statements:
        return AdminCommandResponse(
            answer=result.explanation,
            needs_approval=False,
            is_success=False,
            error_message=result.warning or "Không thể tạo SQL cho yêu cầu này."
        )

    answer_parts = [f"📋 **Kế hoạch SQL:**\n```sql\n{result.sql_statements}\n```\n"]
    answer_parts.append(f"📝 **Giải thích:** {result.explanation}")
    if result.warning:
        answer_parts.append(f"⚠️ **Cảnh báo:** {result.warning}")
    answer_parts.append("\n✋ Vui lòng kiểm tra kỹ SQL trên trước khi duyệt thực thi.")

    return AdminCommandResponse(
        answer="\n".join(answer_parts),
        planned_sql=result.sql_statements,
        needs_approval=True,
        is_success=True
    )

@router.get("/users", summary="Liệt kê tất cả MySQL users")
def list_db_users():
    """Lấy danh sách tất cả tài khoản MySQL đang tồn tại trên Server."""
    _require_admin()
    try:
        with connection_manager.engine.connect() as conn:
            result = conn.execute(text("SELECT User, Host, account_locked FROM mysql.user ORDER BY User"))
            users = [{"user": row[0], "host": row[1], "locked": row[2] == "Y"} for row in result.fetchall()]
        return {"users": users, "total": len(users)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi lấy danh sách users: {str(e)}")
