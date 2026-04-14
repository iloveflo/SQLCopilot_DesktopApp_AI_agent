from pydantic import BaseModel, Field
from typing import List, Optional

class SessionCreate(BaseModel):
    name: Optional[str] = Field(default=None, description="Tên đoạn chat. Nếu không truyền sẽ tự sinh.")
    databases: Optional[List[str]] = Field(default=None, description="Danh sách DB đang chọn lúc tạo session.")

class SessionRename(BaseModel):
    name: str = Field(..., min_length=1, description="Tên mới cho đoạn chat.")

class SessionResponse(BaseModel):
    session_id: str
    name: str
    created_at: str
    updated_at: str
    databases: List[str] = []
    message_count: int = 0
