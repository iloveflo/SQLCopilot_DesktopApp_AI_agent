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

def interpret_results(question: str, sql: str, raw_data: list, has_chart: bool = False) -> str:
    llm = get_llm(task="interpreter", temperature=0.3)
    
    # Tránh nhồi quá nhiều data làm tràn Context Window
    safe_data = raw_data[:50] if raw_data else []
    data_str = json.dumps(safe_data, ensure_ascii=False, default=str)
    
    system_prompt = f"""Bạn là một Chuyên gia Phân tích Dữ liệu Cao cấp (Senior Executive Data Analyst).
Nhiệm vụ của bạn là nhận xét về dữ liệu thô từ SQL.

=== DỮ LIỆU ĐẦU VÀO ===
- Truy vấn SQL: {{sql}}
- Dữ liệu thô: {{data}}
- Có biểu đồ đi kèm: {"Có" if has_chart else "Không"}

=== QUY TẮC THÍCH ỨNG (BẮT BUỘC) ===
1. **TRƯỜNG HỢP DANH SÁCH THÔ (LISTING):** Nếu người dùng chỉ yêu cầu liệt kê danh sách (ví dụ: "Danh sách khách hàng", "Xem các đơn hàng..."):
   - TUYỆT ĐỐI KHÔNG tạo bảng Markdown (UI đã có bảng chuyên dụng).
   - Chỉ trả lời duy nhất 1-2 câu tóm tắt (Ví dụ: "Đây là danh sách 10 khách hàng mới nhất trong hệ thống.").

2. **TRƯỜNG HỢP CÓ BIỂU ĐỒ (HAS CHART):** 
   - Nếu có biểu đồ đi kèm (`has_chart=True`), hãy tập trung vào biểu đồ.
   - Trả lời cực kỳ ngắn gọn (tối đa 2 câu). Không lặp lại số liệu đã có trên biểu đồ.

3. **TRƯỜNG HỢP PHÂN TÍCH CHUYÊN SÂU (ADVANCED ANALYSIS):** 
   - Chỉ khi người dùng yêu cầu phân tích, so sánh, hoặc tìm xu hướng mà KHÔNG có biểu đồ:
   - Hãy trình bày chuyên sâu với: Tóm tắt -> Nhận xét Insights (Bullet points) -> Gợi ý.
   - Ưu tiên dùng chữ in đậm (**số liệu**) để làm nổi bật.

=== KỶ LUẬT ===
- Ngôn ngữ: Tiếng Việt chuyên nghiệp.
- Không chào hỏi, không rườm rà.
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