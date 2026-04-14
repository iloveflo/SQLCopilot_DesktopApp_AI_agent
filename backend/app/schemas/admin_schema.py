from pydantic import BaseModel, Field
from typing import Optional

class AdminCommandRequest(BaseModel):
    command: str = Field(..., description="Lệnh quản trị bằng tiếng Việt. Vd: 'Tạo tài khoản analyst01, chỉ được xem DB florentic'")
    is_approved: bool = Field(default=False, description="False = chỉ lập kế hoạch SQL. True = thực thi thật.")
    planned_sql: Optional[str] = Field(default=None, description="Câu SQL đã được Root duyệt ở bước trước.")

class AdminCommandResponse(BaseModel):
    answer: str
    planned_sql: Optional[str] = None
    needs_approval: bool = False
    is_success: bool = True
    error_message: Optional[str] = None
