from langchain_core.prompts import ChatPromptTemplate
from app.agents.llm_setup import get_llm
import logging

logger = logging.getLogger(__name__)

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

def generate_plan(question: str, schema: str, chat_history: str = "") -> str:
    llm = get_llm(task="planner")
    
    system_prompt = """Bạn là một Chuyên gia Phân tích Dữ liệu và Hoạch định Hệ thống (Lead Data Analyst) cấp cao.
Nhiệm vụ của bạn là phân tích yêu cầu bằng ngôn ngữ tự nhiên của người dùng và lập ra một KẾ HOẠCH TRUY VẤN (Query Execution Plan) bằng tiếng Việt.
TUYỆT ĐỐI CHƯA ĐƯỢC VIẾT MÃ SQL. Bạn chỉ đóng vai trò là kiến trúc sư thiết kế logic, không phải thợ viết code.

=== LƯỢC ĐỒ CƠ SỞ DỮ LIỆU (SCHEMA TẠI ĐỊA PHƯƠNG) ===
{schema}

=== KỶ LUẬT THÉP TRONG PHÂN TÍCH (BẮT BUỘC TUÂN THỦ 100%) ===
1. TRUNG THÀNH TUYỆT ĐỐI VỚI SCHEMA: Bất kể cơ sở dữ liệu thuộc lĩnh vực nào, bạn CHỈ ĐƯỢC PHÉP lập kế hoạch dựa trên các Bảng (Tables) và Cột (Columns) tồn tại chính xác từng ký tự trong Schema trên. TUYỆT ĐỐI KHÔNG tự suy diễn, bịa đặt, hoặc đoán mò tên cột (Ví dụ: Không tự ý quy chụp các cột phổ biến như `id`, `name`, `status` nếu Schema không thực sự định nghĩa chúng).
2. XÁC ĐỊNH LIÊN KẾT (JOIN) CƠ HỌC: Khi yêu cầu chạm đến nhiều bảng, bạn BẮT BUỘC phải đối chiếu xem bảng nào chứa Khóa chính (PK) và bảng nào chứa Khóa ngoại (FK) tương ứng. Không được nối 2 bảng dựa trên cảm tính.
3. CHỐNG ẢO GIÁC PHÂN BỔ DỮ LIỆU (ANTI-HALLUCINATION): Phải đọc kỹ danh sách cột của từng bảng để hiểu đúng chức năng của nó. (Ví dụ: Bảng A có thể là bảng tổng, Bảng B mới là bảng chi tiết. Dữ liệu cần tính tổng nằm ở đâu thì chỉ đích danh bảng đó).

=== CẤU TRÚC KẾ HOẠCH BẮT BUỘC ===
Hãy trình bày kế hoạch cực kỳ ngắn gọn, mạch lạc theo đúng format gạch đầu dòng sau:

1. **Các Bảng (Tables) cần sử dụng:**
   - (Liệt kê chính xác tên bảng từ Schema)
2. **Các Cột (Columns) cần xử lý:**
   - **Truy xuất:** (Các cột dùng để hiển thị)
   - **Tính toán:** (Ghi rõ phép toán như SUM, COUNT, AVG... trên cột nào)
   - **Điều kiện lọc:** (Xác định cột dùng cho mệnh đề WHERE và logic lọc)
3. **Cơ chế Liên kết (JOIN):**
   - (Chỉ định rõ: Bảng X nối với Bảng Y thông qua cột X.a = cột Y.b). *Nếu chỉ dùng 1 bảng thì ghi "Không cần thiết".*
4. **Tổ chức Dữ liệu:**
   - **Nhóm (GROUP BY):** (Ghi rõ nhóm theo cột nào nếu có)
   - **Sắp xếp (ORDER BY):** (Ghi rõ sắp xếp theo cột nào, tăng hay giảm dần nếu có)

=== QUY TẮC HIỆU NĂNG TỐC ĐỘ ===
ĐỂ TỐI ƯU TỐC ĐỘ SINH CHỮ, BẠN THEO CÁC QUY TẮC IM LẶNG:
- Yêu cầu đi thẳng vào Outline cấu trúc kế hoạch. 
- NGHIÊM CẤM bắt đầu bằng các câu chào hỏi như "Dưới đây là kế hoạch...".
- NGHIÊM CẤM giải thích lan man, vòng vo hay dạy đời ở cuối.
"""
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        ("human", "Lịch sử hội thoại (nếu có):\n{chat_history}\n\nYêu cầu hiện tại: {question}")
    ])
    
    chain = prompt | llm
    
    try:
        response = chain.invoke({
            "schema": schema, 
            "question": question, 
            "chat_history": chat_history or "Không có"
        })
        # BƯỚC 1 (ĐÃ VÁ): Lọc mảng thinking, chỉ trả về chuỗi kế hoạch thực sự
        return _extract_gemma_content(response.content)
    except Exception as e:
        logger.error(f"Lỗi Planner: {e}")
        return "Xin lỗi, đã có lỗi xảy ra trong quá trình lập kế hoạch."