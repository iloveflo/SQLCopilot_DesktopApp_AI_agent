from fastapi import APIRouter, HTTPException
import json
from pydantic import BaseModel
from typing import List, Optional
from app.db.session_store import _get_conn, _now_iso
from app.db.connection import connection_manager

router = APIRouter(prefix="/dashboard", tags=["Dashboard — Analytics"])

class PinRequest(BaseModel):
    title: str
    chart_config: dict
    raw_data: Optional[list] = None

@router.post("/pin", summary="Ghim biểu đồ vào Dashboard")
def pin_metric(req: PinRequest):
    conn = _get_conn()
    now = _now_iso()
    user_id = connection_manager.get_user_identifier()
    try:
        conn.execute(
            "INSERT INTO pinned_metrics (title, chart_config, raw_data, created_at, user_id) VALUES (?,?,?,?,?)",
            (req.title, json.dumps(req.chart_config), json.dumps(req.raw_data), now, user_id)
        )
        conn.commit()
        return {"is_success": True, "message": "Đã ghim biểu đồ vào Dashboard."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/metrics", summary="Lấy danh sách các biểu đồ đã ghim")
def get_pinned_metrics():
    conn = _get_conn()
    user_id = connection_manager.get_user_identifier()
    cursor = conn.execute(
        "SELECT id, title, chart_config, raw_data, created_at FROM pinned_metrics WHERE user_id = ? ORDER BY id DESC",
        (user_id,)
    )
    rows = cursor.fetchall()
    result = []
    for row in rows:
        result.append({
            "id": row[0],
            "title": row[1],
            "chart_config": json.loads(row[2]),
            "raw_data": json.loads(row[3]) if row[3] else None,
            "created_at": row[4]
        })
    return result

@router.delete("/metrics/{metric_id}", summary="Xóa biểu đồ khỏi Dashboard")
def unpin_metric(metric_id: int):
    conn = _get_conn()
    user_id = connection_manager.get_user_identifier()
    cursor = conn.execute("DELETE FROM pinned_metrics WHERE id = ? AND user_id = ?", (metric_id, user_id))
    conn.commit()
    return {"is_success": cursor.rowcount > 0}
