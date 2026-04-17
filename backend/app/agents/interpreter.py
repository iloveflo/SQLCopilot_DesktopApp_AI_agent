from langchain_core.prompts import ChatPromptTemplate
from app.agents.llm_setup import get_llm
import json
import logging

logger = logging.getLogger(__name__)

def _extract_gemma_content(raw_content) -> str:
    """Bóc tách phần 'text' thực sự từ mảng chứa 'thinking block' của Gemma 4."""
    if isinstance(raw_content, list):
        return "".join([
            block.get("text", "") 
            for block in raw_content 
            if isinstance(block, dict) and block.get("type") == "text"
        ])
    return str(raw_content)

def interpret_results(question: str, sql: str, raw_data: list) -> str:
    llm = get_llm(task="interpreter", temperature=0.3)
    
    # Tránh nhồi quá nhiều data làm tràn Context Window
    safe_data = raw_data[:50] if raw_data else []
    data_str = json.dumps(safe_data, ensure_ascii=False, default=str)
    
    system_prompt = """Bạn là một Chuyên gia Phân tích Dữ liệu Cao cấp (Senior Executive Data Analyst).
Nhiệm vụ của bạn là biến dữ liệu thô từ SQL thành một báo cáo kinh doanh có chiều sâu, chuyên nghiệp và dễ hiểu.

=== DỮ LIỆU ĐẦU VÀO ===
- Truy vấn SQL: {sql}
- Dữ liệu thô: {data}

=== CẤU TRÚC BÁO CÁO (BẮT BUỘC) ===
1. **Tóm tắt điều hành (Executive Summary):** 1-2 câu tóm gọn kết quả quan trọng nhất.
2. **Bảng dữ liệu (Data Evidence):** Sử dụng Markdown Table để hiển thị dữ liệu nếu có >= 2 dòng. Đặt tên cột tiếng Việt dễ hiểu.
3. **Phân tích chuyên sâu (Insights):** Sử dụng danh sách (bullet points) để chỉ ra các xu hướng, điểm bất thường, hoặc tỷ trọng đáng chú ý. 
4. **Gợi ý/Dự báo (Actionable Advice):** Một nhận xét ngắn về ý nghĩa kinh doanh của kết quả này.

=== KỶ LUẬT TRÌNH BÀY ===
- **Sử dụng Markdown chuẩn:** BẮT BUỘC dùng bảng (| --- |), in đậm (**số liệu**), và danh sách (- ).
- **Tư duy Business:** Đừng chỉ đọc số, hãy giải thích số đó nói lên điều gì về tình hình hiện tại.
- **Ngôn ngữ:** Tiếng Việt chuyên nghiệp, quyết đoán nhưng lịch sự.
- **Độ dài:** Không giới hạn cứng, nhưng cần súc tích. Tập trung vào chất lượng Insight hơn là số lượng chữ.
"""
    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        ("human", "{question}")
    ])
    
    chain = prompt | llm
    
    try:
        # 1. Gọi AI
        response = chain.invoke({
            "data": data_str, 
            "sql": sql, 
            "question": question
        })
        
        # 2. BƯỚC QUAN TRỌNG: Đưa qua màng lọc bóc tách suy nghĩ trước khi return
        clean_answer = _extract_gemma_content(getattr(response, "content", response))
        return clean_answer
        
    except Exception as e:
        logger.error(f"Lỗi Interpreter: {e}")
        return "Xin lỗi, đã có lỗi xảy ra trong quá trình phân tích và đọc dữ liệu."