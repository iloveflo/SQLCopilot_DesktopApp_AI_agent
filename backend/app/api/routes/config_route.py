from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from app.core.config import settings
from typing import Optional

router = APIRouter(prefix="/admin/config", tags=["Admin Configuration"])

class ConfigResponse(BaseModel):
    google_api_key_masked: str
    is_key_set: bool

class ConfigUpdateRequest(BaseModel):
    google_api_key: str

def mask_key(key: Optional[str]) -> str:
    if not key:
        return ""
    if len(key) <= 8:
        return "*" * len(key)
    return f"{key[:4]}...{key[-4:]}"

@router.get("", response_model=ConfigResponse)
async def get_config():
    """Lấy trạng thái cấu hình hiện tại (đã ẩn mã)."""
    return {
        "google_api_key_masked": mask_key(settings.GOOGLE_API_KEY),
        "is_key_set": bool(settings.GOOGLE_API_KEY)
    }

@router.post("")
async def update_config(req: ConfigUpdateRequest):
    """Cập nhật cấu hình mới và lưu trữ."""
    if not req.google_api_key.strip():
        raise HTTPException(status_code=400, detail="API Key không được để trống")
    
    # Cập nhật vào bộ nhớ
    settings.GOOGLE_API_KEY = req.google_api_key.strip()
    
    # Lưu vào file JSON để dùng cho lần sau
    try:
        settings.save_to_json()
        return {"status": "success", "message": "Cấu hình đã được lưu và áp dụng"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi khi lưu file: {str(e)}")
