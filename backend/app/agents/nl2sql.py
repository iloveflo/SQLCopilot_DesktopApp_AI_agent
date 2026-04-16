import json
import re
import logging
from typing import Optional
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field
from app.agents.llm_setup import get_llm

logger = logging.getLogger(__name__)

class SQLResponse(BaseModel):
    query: str
    explanation: str
    plan: Optional[str] = None

# =====================================================================
# BỘ LỌC CHUYÊN DỤNG CHO GEMMA 4 VÀ CÁC REASONING MODELS
# =====================================================================
def _extract_gemma_content(raw_content) -> str:
    if isinstance(raw_content, list):
        return "".join([
            block.get("text", "") 
            for block in raw_content 
            if isinstance(block, dict) and block.get("type") == "text"
        ])
    return str(raw_content)

def _extract_gemma_plan(text: str) -> str:
    match = re.search(r"\[KẾ HOẠCH\](.*?)\[KẾT THÚC KẾ HOẠCH\]", text, re.DOTALL)
    if match:
        return match.group(1).strip()
    return ""

def _extract_sql(text: str) -> str:
    match = re.search(r"```(?:sql|sqlite)?\n(.*?)\n```", text, re.IGNORECASE | re.DOTALL)
    if match:
        return match.group(1).strip()
    # Fallback mài tìm SELECT
    if "SELECT" in text.upper():
        sql_match_plain = re.search(r"(SELECT.*?)(?:\n\n|\s*$)", text, re.IGNORECASE | re.DOTALL)
        if sql_match_plain:
            return sql_match_plain.group(1).strip()
    return text.strip()

# =====================================================================
# AGENT: SQL GENERATOR (PRE-EMPTIVE PLANNING)
# =====================================================================
def generate_sql(
    question: str, 
    schema: str, 
    error_feedback: str = None, 
    chat_history: str = "", 
    plan_feedback: str = None
) -> SQLResponse:
    llm = get_llm(task="sql_generation")
    
    plan_instruction = ""
    if plan_feedback:
        plan_instruction = f"\nƯU TIÊN TUYỆT ĐỐI làm theo bản kế hoạch đã chốt với người dùng dưới đây:\n[BẢN KẾ HOẠCH]\n{plan_feedback}\n[KẾT THÚC BẢN KẾ HOẠCH]\n"

    from app.db.session_store import get_few_shot_examples
    few_shot_context = get_few_shot_examples(limit=5)

    system_prompt = f"""Bạn là một Kiến trúc sư Cơ sở dữ liệu (Database Architect) và Chuyên gia SQL cấp cao.
Nhiệm vụ của bạn là:
1. LUÔN LUÔN lập một bản kế hoạch ngắn gọn (Chain-of-Thought) phân tích yêu cầu.
2. Dịch yêu cầu thành các câu lệnh SQL chính xác 100%.{plan_instruction}

{few_shot_context}

=== LƯỢC ĐỒ CƠ SỞ DỮ LIỆU (SCHEMA) ===
{{schema}}

=== MỆNH LỆNH TỐI THƯỢNG (BẮT BUỘC TUÂN THỦ 100%) ===
1. TRUNG THÀNH TUYỆT ĐỐI VỚI SCHEMA: BẢT BUỘC chỉ dùng cột/bảng có thật. KHÔNG tự bịa.
2. ĐỊNH DẠNG TÊN BẢNG: Bắt buộc phải có tiền tố Database. Ví dụ: `ten_db`.`ten_bang`.
3. XỬ LÝ LỖI (SELF-CORRECTION): {{error_feedback}}.
4. CẤU TRÚC PHẢN HỒI (KHÔNG ĐƯỢC SAI):
   - Đầu tiên là khối: [KẾ HOẠCH] ... nội dung kế hoạch ngắn gọn ... [KẾT THÚC KẾ HOẠCH]
   - Sau đó là duy nhất một khối mã: ```sql ... ```
   
=== TỐI ƯU HÓA HIỆU NĂNG TỐC ĐỘ ===
- KHÔNG giải thích dông dài ngoài 2 khối trên.
- KHÔNG tạo cấu trúc JSON.
"""
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        ("human", "Lịch sử cuộc hội thoại (từ cũ đến mới):\n{chat_history}\n\nYêu cầu hiện tại: {question}")
    ])
    
    llm_chain = prompt | llm
    inputs = {
        "schema": schema,
        "question": question,
        "error_feedback": error_feedback or "Không có",
        "chat_history": chat_history or "Không có lịch sử"
    }

    try:
        raw_response = llm_chain.invoke(inputs)
        raw_text = _extract_gemma_content(getattr(raw_response, "content", raw_response))
        
        plan = _extract_gemma_plan(raw_text)
        sql = _extract_sql(raw_text)
        
        return SQLResponse(query=sql, explanation="Đã tạo SQL và kế hoạch.", plan=plan)
    except Exception as e:
        logger.error(f"Lỗi khi kết nối với LLM Local: {e}")
        return SQLResponse(query="", explanation="Lỗi kết nối tới mô hình AI.")