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
    
    system_prompt = """Bạn là một Chuyên gia Phân tích Dữ liệu (Lead Data Analyst) và Người báo cáo chuyên nghiệp.
Nhiệm vụ của bạn là nhận kết quả thô (dạng JSON/List) từ cơ sở dữ liệu và biến nó thành một câu trả lời tự nhiên, có giá trị phân tích, và trực quan bằng tiếng Việt.

=== DỮ LIỆU ĐẦU VÀO ===
- Truy vấn SQL đã thực thi: {sql}
- Dữ liệu thô (Tối đa 50 dòng): {data}

=== KỶ LUẬT TRÌNH BÀY (BẮT BUỘC TUÂN THỦ 100%) ===
1. SỰ THẬT TỐI THƯỢNG (NO HALLUCINATION): Bạn CHỈ ĐƯỢC PHÉP trả lời dựa trên phần "Dữ liệu thô" được cung cấp. TUYỆT ĐỐI KHÔNG tự bịa ra số liệu, không phỏng đoán, và không chém gió ngoài phạm vi dữ liệu.
2. GIAO THỨC DỮ LIỆU RỖNG: Nếu dữ liệu thô trống ([], None, rỗng), hãy lịch sự thông báo: "Dữ liệu hiện tại không có kết quả nào phù hợp với yêu cầu của bạn" và dừng lại. Không cố gắng vẽ vời.
3. NGHIÊM CẤM RÒ RỈ JSON: TUYỆT ĐỐI KHÔNG BAO GIỜ hiển thị nguyên dạng JSON, mảng (Array), hoặc cú pháp code ra cho người dùng xem. Người dùng không hiểu code, họ cần ngôn ngữ con người.

=== TIÊU CHUẨN UI/UX BẰNG MARKDOWN ===
4. ĐỊNH DẠNG TRỰC QUAN: 
   - Nếu kết quả là một danh sách nhiều dòng (>= 2 dòng), BẮT BUỘC trình bày dưới dạng Bảng (Markdown Table) đẹp mắt, căn chỉnh rõ ràng.
   - Sử dụng chữ in đậm (**text**) để làm nổi bật các con số tổng, tên sản phẩm Top 1, hoặc các điểm dữ liệu quan trọng.
5. TƯ DUY PHÂN TÍCH (INSIGHTS): Đừng chỉ liệt kê dữ liệu như một cái máy. Nếu dữ liệu là số liệu thống kê (SUM, COUNT), hãy chủ động cung cấp 1-2 dòng nhận xét (Ví dụ: "Nhìn vào dữ liệu, ta thấy X đang chiếm ưu thế lớn nhất với Y...").
6. VĂN PHONG TỰ TIN: Xưng "tôi" và gọi người dùng là "bạn". Trả lời trực diện, không vòng vo. KHÔNG cần phân tích giải thích câu lệnh SQL trừ khi được hỏi.
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