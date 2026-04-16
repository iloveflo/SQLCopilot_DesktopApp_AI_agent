import json
import re
import logging
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field
from app.agents.llm_setup import get_llm

logger = logging.getLogger(__name__)

class SQLGenerationOutput(BaseModel):
    query: str = Field(description="Câu lệnh SQL chuẩn xác, có thể chạy ngay.")
    explanation: str = Field(description="Giải thích ngắn gọn logic bằng tiếng Việt.")

# =====================================================================
# BỘ LỌC CHUYÊN DỤNG CHO GEMMA 4 VÀ CÁC REASONING MODELS
# =====================================================================
def _extract_gemma_content(raw_content) -> str:
    """
    Bóc tách phần 'text' thực sự từ mảng chứa 'thinking block' của AI.
    Nếu là mô hình thường (trả về chuỗi), nó sẽ ép kiểu an toàn về str.
    """
    if isinstance(raw_content, list):
        # Duyệt qua mảng, vứt bỏ {'type': 'thinking'}, chỉ giữ {'type': 'text'}
        return "".join([
            block.get("text", "") 
            for block in raw_content 
            if isinstance(block, dict) and block.get("type") == "text"
        ])
    return str(raw_content)

def _extract_json_object(text: str) -> dict | None:
    """Hàm 'vét máng': Bóc tách vỏ Markdown rác của các Local Model để lấy JSON."""
    clean_text = text.replace("```json", "").replace("```sqlite", "").replace("```sql", "").replace("```", "").strip()
    
    braces = [m.start() for m in re.finditer(r"\{", clean_text)]
    for start in reversed(braces[-50:]):
        candidate = clean_text[start:]
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            continue
    return None

# =====================================================================
# AGENT 1: SQL GENERATOR
# =====================================================================
def generate_sql(question: str, schema: str, error_feedback: str = None, chat_history: str = "", plan_feedback: str = None) -> SQLGenerationOutput:
    llm = get_llm(task="sql_generation")
    
    plan_instruction = ""
    if plan_feedback:
        plan_instruction = f"\nƯU TIÊN TUYỆT ĐỐI làm theo bản kế hoạch đã chốt với người dùng dưới đây:\n[BẢN KẾ HOẠCH]\n{plan_feedback}\n[KẾT THÚC BẢN KẾ HOẠCH]\n"

    system_prompt = f"""Bạn là một Kiến trúc sư Cơ sở dữ liệu (Database Architect) và Chuyên gia SQL cấp cao.
Nhiệm vụ của bạn là dịch các yêu cầu tự nhiên bằng tiếng Việt thành các câu lệnh SQL chính xác 100%.{plan_instruction}

=== LƯỢC ĐỒ CƠ SỞ DỮ LIỆU (SCHEMA) ===
{{schema}}

=== MỆNH LỆNH TỐI THƯỢNG (BẮT BUỘC TUÂN THỦ 100%) ===
1. TRUNG THÀNH TUYỆT ĐỐI VỚI SCHEMA (CHỐNG ẢO GIÁC): BẢT BUỘC chỉ dùng cột/bảng có thật. KHÔNG tự bịa.
2. QUY TẮC KẾT NỐI (JOIN): Bắt buộc nối đúng cột khóa ngoại đã định nghĩa.
3. ĐỊNH DẠNG TÊN BẢNG: (Chế độ Multi-Database) Bắt buộc phải có tiền tố Database. Ví dụ: `ten_db`.`ten_bang`.
4. XỬ LÝ LỖI (SELF-CORRECTION): {{error_feedback}}. Nếu có lỗi, PHẢI đối chiếu lại và sửa.

=== TỐI ƯU HÓA HIỆU NĂNG TỐC ĐỘ (ĐỌC KỸ) ===
ĐỂ TỐI ƯU TỐC ĐỘ PHẢN HỒI, BẠN PHẢI TUÂN THỦ CÁC LUẬT IM LẶNG:
- BẠN BẮT BUỘC CHỈ TRẢ VỀ DUY NHẤT MỘT KHỐI MÃ ` ```sql ... ``` ` CHỨA CÂU LỆNH SQL.
- NGHIÊM CẤM TẠO CẤU TRÚC JSON.
- NGHIÊM CẤM GIẢI THÍCH, KHÔNG CHÀO HỎI, KHÔNG TRÌNH BÀY DÀI DÒNG DƯỚI MỌI HÌNH THỨC. Chỉ xuất Code!
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
    except Exception as e:
        logger.error(f"Lỗi khi kết nối với LLM Local: {e}")
        return SQLGenerationOutput(query="", explanation="Lỗi kết nối tới mô hình AI.")

    # BƯỚC 2: Rút trích trực tiếp khối mã Markdown SQL thay vì parse JSON chậm chạp
    sql_match = re.search(r"```(?:sql|sqlite)?\n(.*?)\n```", raw_text, re.IGNORECASE | re.DOTALL)
    if sql_match:
        return SQLGenerationOutput(query=sql_match.group(1).strip(), explanation="Đã sinh SQL Thành Công.")
    
    # Fallback mài tìm SELECT
    if "SELECT" in raw_text.upper():
        sql_match_plain = re.search(r"(SELECT.*?)(?:\n\n|\s*$)", raw_text, re.IGNORECASE | re.DOTALL)
        if sql_match_plain:
            return SQLGenerationOutput(query=sql_match_plain.group(1).strip(), explanation="Trích xuất SQL thuần.")

    logger.error(f"Lỗi định dạng SQL Output: {raw_text}")
    return SQLGenerationOutput(query="", explanation=f"Không thể định vị được câu lệnh SQL. Phản hồi: {raw_text[:200]}")