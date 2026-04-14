import json
import re
import logging
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field
from langchain_core.output_parsers import PydanticOutputParser
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
    parser = PydanticOutputParser(pydantic_object=SQLGenerationOutput)
    
    plan_instruction = ""
    if plan_feedback:
        plan_instruction = f"\nƯU TIÊN TUYỆT ĐỐI làm theo bản kế hoạch đã chốt với người dùng dưới đây:\n[BẢN KẾ HOẠCH]\n{plan_feedback}\n[KẾT THÚC BẢN KẾ HOẠCH]\n"

    system_prompt = f"""Bạn là một Kiến trúc sư Cơ sở dữ liệu (Database Architect) và Chuyên gia SQL cấp cao.
Nhiệm vụ của bạn là dịch các yêu cầu tự nhiên bằng tiếng Việt thành các câu lệnh SQL chính xác 100%.{plan_instruction}

=== LƯỢC ĐỒ CƠ SỞ DỮ LIỆU (SCHEMA) ===
{{schema}}

=== MỆNH LỆNH TỐI THƯỢNG (BẮT BUỘC TUÂN THỦ 100%) ===
1. TRUNG THÀNH TUYỆT ĐỐI VỚI SCHEMA (CHỐNG ẢO GIÁC): 
   - CHỈ ĐƯỢC PHÉP sử dụng các bảng và cột tồn tại chính xác từng ký tự trong Schema trên. 
   - TUYỆT ĐỐI KHÔNG tự bịa ra, suy đoán, hoặc tự ý thêm bớt tiền tố/hậu tố cho tên cột/tên bảng.
   - CẢNH BÁO: Không bao giờ được mặc định các cột phổ biến như `id`, `name`, `status` luôn tồn tại. (Ví dụ: Nếu schema ghi là `title`, bắt buộc dùng `title`, tuyệt đối không tự "dịch" thành `name` hay `ten_san_pham`).

2. QUY TẮC KẾT NỐI (JOIN) CƠ HỌC & NGHIÊM NGẶT: 
   - Phải phân tích kỹ định nghĩa Khóa chính (PK) và Khóa ngoại (FK) trực tiếp từ Schema trước khi JOIN.
   - CẢNH BÁO: Không được tự động thêm hậu tố `_id` vào tên một bảng để ép nó làm khóa chính. (Ví dụ: Đừng mặc định bảng `KhachHang` thì khóa là `khach_hang_id`, nó có thể chỉ là `id` hoặc `ma_kh`). Bắt buộc nối đúng cột theo quan hệ thực tế được định nghĩa.

3. ĐỊNH DẠNG TÊN BẢNG (PREFIX RULE BẮT BUỘC):
   - Chế độ "Multi-Database Analysis Mode": Tên bảng BẮT BUỘC phải có tiền tố là tên database chứa nó. (Ví dụ chuẩn: SELECT * FROM `ten_database_a`.`ten_bang_b`). KHÔNG ĐƯỢC BỎ TIỀN TỐ.
   - Chế độ "Single-Database Mode": Dùng tên bảng gốc, KHÔNG CẦN tiền tố.

4. XỬ LÝ LỖI (SELF-CORRECTION CHUYÊN SÂU): 
   - Thông báo lỗi từ hệ thống (nếu có): {{error_feedback}}
   - Nếu có lỗi, bạn PHẢI đối chiếu lại nguyên nhân với Schema hiện tại và viết lại câu lệnh mới. Tuyệt đối không nhắm mắt lặp lại câu SQL đã gây lỗi.

5. CÚ PHÁP TIÊU CHUẨN: 
   - Trả về mã SQL tương thích chuẩn mực với Hệ quản trị CSDL được cung cấp. 
   - Riêng với các truy vấn về siêu dữ liệu (đếm số bảng, liệt kê các cột...), sử dụng cú pháp tra cứu chuẩn (như truy vấn vào `information_schema`).

=== ĐỊNH DẠNG ĐẦU RA (OUTPUT FORMAT) ===
{{format_instructions}}

LƯU Ý KỸ THUẬT QUAN TRỌNG VỀ JSON:
- KHÔNG sử dụng ký tự escape ngược (\\) cho chuỗi bên trong JSON. 
- ĐÚNG: "query": "SELECT * FROM users WHERE name = 'John'"
- SAI: "query": "SELECT * FROM users WHERE name = \\'John\\'"
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
        "chat_history": chat_history or "Không có lịch sử",
        "format_instructions": parser.get_format_instructions()
    }

    try:
        raw_response = llm_chain.invoke(inputs)
        # BƯỚC 1 (ĐÃ VÁ): Lọc nội dung qua màng lọc Gemma 4 trước khi gán vào raw_text
        raw_text = _extract_gemma_content(getattr(raw_response, "content", raw_response))
    except Exception as e:
        logger.error(f"Lỗi khi kết nối với LLM Local: {e}")
        return SQLGenerationOutput(query="", explanation="Lỗi kết nối tới mô hình AI.")

    # BƯỚC 2: Thử phân tích JSON bằng Pydantic Parser chuẩn
    try:
        return parser.parse(raw_text)
    except Exception as e:
        logger.warning(f"Langchain Parser thất bại, tiến hành lọc thủ công cấp độ 3...")
        
        # BƯỚC 3: Fallback - Tự bóc tách JSON thủ công
        json_obj = _extract_json_object(raw_text)
        if json_obj is not None:
            query = json_obj.get("query", json_obj.get("sql", json_obj.get("sql_query", "")))
            if query.strip(): 
                explanation = json_obj.get("explanation", "Dưới đây là truy vấn SQL tôi vừa tạo.")
                return SQLGenerationOutput(query=query.strip(), explanation=explanation)
            
        # BƯỚC 4: Fallback cuối cùng - Bỏ qua mọi thể loại JSON, dùng Regex Moi móc SQL
        if "SELECT" in raw_text.upper():
            sql_match = re.search(r"```sql\n(.*?)\n```", raw_text, re.DOTALL)
            if sql_match:
                return SQLGenerationOutput(query=sql_match.group(1).strip(), explanation="Đã trích xuất SQL từ Markdown.")
            
            sql_match_plain = re.search(r"(SELECT.*?)(?:\n|\s*$)", raw_text, re.IGNORECASE | re.DOTALL)
            if sql_match_plain:
                return SQLGenerationOutput(query=sql_match_plain.group(1).strip(), explanation="Đã trích xuất SQL từ văn bản thuần.")
        
        # BƯỚC 5: Nếu không moi được SQL, trả về lỗi chi tiết để Debug
        logger.error(f"LLM trả về định dạng không thể xử lý: {raw_text}")
        return SQLGenerationOutput(query="", explanation=f"Lỗi định dạng: Mô hình trả về nội dung không phải SQL. Nội dung: {raw_text[:200]}...")