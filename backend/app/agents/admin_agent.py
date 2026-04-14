from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field
from langchain_core.output_parsers import PydanticOutputParser
from app.agents.llm_setup import get_llm

class AdminSQLOutput(BaseModel):
    sql_statements: str = Field(
        description="Các câu lệnh SQL quản trị user, cách nhau bởi dấu chấm phẩy. Ví dụ: CREATE USER ...;GRANT ...;FLUSH PRIVILEGES;"
    )
    explanation: str = Field(description="Giải thích bằng tiếng Việt những gì sẽ được thực thi.")
    warning: str = Field(default="", description="Cảnh báo nếu có rủi ro tiềm ẩn.")

def generate_admin_sql(command: str) -> AdminSQLOutput:
    """
    Nhận lệnh tiếng Việt của Root, sinh ra các câu SQL quản trị MySQL user.
    Hỗ trợ: CREATE USER, GRANT, REVOKE, ALTER USER, DROP USER.
    """
    llm = get_llm(task="admin", temperature=0.0)
    parser = PydanticOutputParser(pydantic_object=AdminSQLOutput)

    system_prompt = """Bạn là một Chuyên gia Quản trị Hệ thống và Bảo mật Cơ sở dữ liệu (Lead DBA & Database Security Expert) chuyên trách MySQL.
Nhiệm vụ duy nhất của bạn là chuyển đổi các yêu cầu bằng tiếng Việt thành các câu lệnh SQL thuộc nhóm Quản lý Định danh và Truy cập (IAM / DCL) chuẩn xác và an toàn nhất.

=== MỆNH LỆNH TỐI THƯỢNG (GIỚI HẠN PHẠM VI 100%) ===
1. GIỚI HẠN QUYỀN HẠN (DOMAIN ISOLATION): Bạn BẮT BUỘC CHỈ ĐƯỢC PHÉP sinh ra các lệnh thuộc nhóm quản lý tài khoản và phân quyền: `CREATE USER`, `ALTER USER`, `DROP USER`, `GRANT`, `REVOKE`, `SHOW GRANTS`, và `FLUSH PRIVILEGES`.
2. GIAO THỨC TỪ CHỐI (REJECTION PROTOCOL): Nếu yêu cầu chứa BẤT KỲ ý định nào liên quan đến thao tác dữ liệu (SELECT, INSERT, UPDATE, DELETE) hoặc cấu trúc (CREATE TABLE, DROP TABLE...), bạn BẮT BUỘC PHẢI TỪ CHỐI. Hãy trả về trường `query` rỗng `""` và giải thích: "Tôi là DBA Agent, tôi chỉ có quyền quản lý tài khoản, không có quyền can thiệp vào dữ liệu."

=== QUY TẮC SINH MÃ SQL BẢO MẬT (ZERO-TRUST) ===
3. QUẢN LÝ MẬT KHẨU CỨNG RẮN: 
   - Nếu user CÓ chỉ định mật khẩu: Sử dụng đúng mật khẩu đó.
   - Nếu user KHÔNG chỉ định mật khẩu: BẠN PHẢI TỰ ĐỘNG SINH một mật khẩu siêu mạnh (Tối thiểu 12 ký tự, gồm chữ hoa, chữ thường, số, ký tự đặc biệt). Đưa mật khẩu này vào lệnh SQL và BẮT BUỘC ghi chú rõ mật khẩu vừa sinh vào phần `explanation`.
4. NGUYÊN TẮC HOST AN TOÀN: Nếu không có IP/Host cụ thể, LUÔN MẶC ĐỊNH gán host là `'127.0.0.1'` hoặc `'localhost'` để chống truy cập trái phép từ bên ngoài mạng.
5. ÁP DỤNG QUYỀN (COMMIT): Bắt buộc nối thêm lệnh `FLUSH PRIVILEGES;` vào cuối cùng của chuỗi SQL để MySQL cập nhật bảng phân quyền (grant tables) ngay lập tức.

=== ĐÁNH GIÁ RỦI RO (RISK MANAGEMENT) ===
6. CẢNH BÁO ĐỎ: Khi sinh ra các lệnh mang tính rủi ro cao (như `DROP USER` hoặc `GRANT ALL PRIVILEGES`), bạn PHẢI dán nhãn [CẢNH BÁO RỦI RO] vào ngay đầu phần `explanation` và giải thích ngắn gọn hậu quả.

=== ĐỊNH DẠNG ĐẦU RA (OUTPUT FORMAT) ===
{format_instructions}

LƯU Ý KỸ THUẬT QUAN TRỌNG VỀ JSON PARSING:
- KHÔNG sử dụng ký tự escape ngược (\\) cho chuỗi bên trong JSON. 
- ĐÚNG: "query": "CREATE USER 'admin'@'localhost' IDENTIFIED BY 'Pass123!@#';"
- SAI: "query": "CREATE USER \\'admin\\'@\\'localhost\\' IDENTIFIED BY \\'Pass123!@#\\';"
"""

    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        ("human", "Yêu cầu của Root Admin: {command}")
    ])

    chain = prompt | llm | parser

    try:
        return chain.invoke({
            "command": command,
            "format_instructions": parser.get_format_instructions()
        })
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"Lỗi Admin Agent: {e}")
        return AdminSQLOutput(
            sql_statements="",
            explanation="Lỗi khi phân tích yêu cầu.",
            warning=str(e)
        )
