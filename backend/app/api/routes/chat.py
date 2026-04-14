from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
import logging
import json
import asyncio
from app.schemas.chat_schema import ChatRequest, ChatResponse, ChatHistoryResponse
from app.agents.orchestrator import stream_copilot, clear_session, get_session_history
from app.db.session_store import increment_message_count

router = APIRouter(prefix="/chat", tags=["AI Copilot"])
logger = logging.getLogger(__name__)

@router.post("/ask", summary="Gửi câu hỏi bằng ngôn ngữ tự nhiên (Streaming)")
async def ask_database(request: ChatRequest):
    """
    Nhận câu hỏi tiếng Việt, stream các bước suy nghĩ của AI qua SSE.
    Dùng async def để hỗ trợ StreamingResponse tốt nhất.
    """
    try:
        session_id = request.session_id or "default_session"
        increment_message_count(session_id)

        async def event_generator():
            # Chạy generator từ orchestrator (vì nó là sync generator, ta bao bọc nó)
            # Lưu ý: stream_copilot trong orchestrator là sync generator
            from app.agents.orchestrator import stream_copilot
            
            loop = asyncio.get_event_loop()
            gen = stream_copilot(
                question=request.query,
                session_id=session_id,
                is_approved=request.is_approved,
                plan_feedback=request.plan_feedback
            )
            
            # Chúng ta sẽ chạy generator này và yield từng chunk
            # Trong thực tế, có thể cần run_in_executor nếu nó nặng, 
            # nhưng LangGraph stream thường nhẹ nhàng
            for update in gen:
                # Gói dữ liệu vào chuẩn SSE, dùng default=str để xử lý Decimal/Datetime
                yield f"data: {json.dumps(update, ensure_ascii=False, default=str)}\n\n"
                await asyncio.sleep(0.01) # Mẹo nhỏ để ép flush

        return StreamingResponse(event_generator(), media_type="text/event-stream")

    except Exception as e:
        logger.error(f"Lỗi nghiêm trọng trong luồng Streaming: {e}")
        raise HTTPException(status_code=500, detail=f"Internal Agent Error: {str(e)}")

@router.delete("/session/{session_id}", summary="Xóa bộ nhớ của một phiên chat")
def delete_chat_session(session_id: str):
    """
    Xóa toàn bộ lịch sử trò chuyện của một session_id khỏi ổ cứng SQLite.
    Giúp người dùng dọn dẹp ngữ cảnh để bắt đầu luồng mới hoàn toàn sạc.
    """
    if clear_session(session_id):
        return {"message": "Đã xóa lịch sử trò chuyện thành công.", "session_id": session_id, "is_success": True}
    else:
        raise HTTPException(status_code=500, detail="Lỗi khi xóa lịch sử trên Database.")

@router.get("/history/{session_id}", response_model=ChatHistoryResponse, summary="Lấy toàn bộ lịch sử chat (cả biểu đồ)")
def get_chat_history(session_id: str):
    """
    Trả về toàn bộ tin nhắn đã chat, bao gồm cục bộ dữ liệu `raw_data` và `chart_config`
    để Frontend có thể vẽ lại giao diện cũ mà không cần query lại DB.
    """
    try:
        messages = get_session_history(session_id)
        return ChatHistoryResponse(
            session_id=session_id,
            messages=messages
        )
    except Exception as e:
        logger.error(f"Lỗi khi lấy lịch sử chat: {e}")
        raise HTTPException(status_code=500, detail=f"Lỗi truy xuất lịch sử: {str(e)}")