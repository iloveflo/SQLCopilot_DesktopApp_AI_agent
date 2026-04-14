from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional

class ChatRequest(BaseModel):
    """
    Schema định nghĩa dữ liệu đầu vào (Payload) từ Frontend gửi lên Backend.
    """
    query: str = Field(
        ..., 
        min_length=2, 
        description="Câu hỏi ngôn ngữ tự nhiên bằng tiếng Việt từ người dùng. VD: 'Tháng trước sản phẩm nào bán chạy nhất?'"
    )
    user_id: Optional[str] = Field(
        default="guest_user", 
        description="ID của người dùng để định danh hoặc lưu lịch sử hội thoại."
    )
    session_id: Optional[str] = Field(
        default=None, 
        description="ID của phiên chat để Agent có thể nhớ ngữ cảnh các câu hỏi trước đó (Memory)."
    )
    is_approved: bool = Field(
        default=False,
        description="Cờ báo hiệu User đã duyệt bản kế hoạch hay chưa."
    )
    plan_feedback: Optional[str] = Field(
        default=None,
        description="Bản kế hoạch đã được User chỉnh sửa hoặc comment."
    )

class ChatResponse(BaseModel):
    """
    Schema định nghĩa dữ liệu đầu ra (Response) từ Backend trả về cho Frontend.
    """
    answer: str = Field(
        ..., 
        description="Câu trả lời đã được Agent biên dịch sang ngôn ngữ tự nhiên."
    )
    plan: Optional[str] = Field(
        default=None,
        description="Bản kế hoạch bằng tiếng Việt trả về để User duyệt."
    )
    needs_approval: bool = Field(
        default=False,
        description="Cờ báo hiệu Frontend cần hiển thị giao diện duyệt Kế hoạch."
    )
    sql_query: Optional[str] = Field(
        default=None, 
        description="Câu lệnh SQL thô mà LLM đã sinh ra. Trả về để UI hiển thị cho user xem/debug."
    )
    raw_data: Optional[List[Dict[str, Any]]] = Field(
        default=None, 
        description="Tập dữ liệu thô (JSON Array) trả về từ CSDL (tối đa N dòng để tránh tràn RAM Frontend)."
    )
    chart_config: Optional[Dict[str, Any]] = Field(
        default=None, 
        description="Cấu hình JSON tương thích với thư viện Plotly.js để render biểu đồ động."
    )
    is_success: bool = Field(
        default=True,
        description="Cờ đánh dấu request có xử lý thành công toàn trình hay không."
    )
    error_message: Optional[str] = Field(
        default=None,
        description="Thông báo lỗi chi tiết nếu có bất kỳ Agent nào thất bại."
    )

class ChatMessage(BaseModel):
    role: str
    content: str
    sql_query: Optional[str] = None
    raw_data: Optional[List[Dict[str, Any]]] = None
    chart_config: Optional[Dict[str, Any]] = None

class ChatHistoryResponse(BaseModel):
    session_id: str
    messages: List[ChatMessage]