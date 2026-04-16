import re
from app.db.metadata import get_multi_db_schema_context

MAX_SCHEMA_CHARS = 7000


def _truncate_text(text: str, max_chars: int) -> str:
    if len(text) <= max_chars:
        return text
    return text[:max_chars].rsplit("\n", 1)[0] + "\n\n...[Schema đã bị cắt để giảm chi phí token]"


def _summarize_schema(schema_text: str) -> str:
    """Tóm tắt schema thành dạng nhỏ gọn chỉ còn table & column names."""
    summary_lines = []
    include_columns = False

    for line in schema_text.splitlines():
        if line.startswith("Hệ quản trị") or line.startswith("Chế độ:") or line.startswith("CSDL đang phân tích:"):
            summary_lines.append(line)
            continue
        if line.startswith("📦 DATABASE") or line.startswith("Table:"):
            summary_lines.append(line)
            include_columns = True
            continue
        if line.startswith("  - ") and include_columns:
            column_name = line[4:].split(" [", 1)[0]
            summary_lines.append(f"  - {column_name}")
            continue
        if line.startswith("Relationships:"):
            include_columns = False
            continue

    summary_text = "\n".join(summary_lines)
    if len(summary_text) <= MAX_SCHEMA_CHARS:
        return summary_text

    table_names = [line for line in summary_lines if line.startswith("Table:")]
    fallback = "\n".join(summary_lines[:3] + table_names[:20])
    return _truncate_text(fallback, MAX_SCHEMA_CHARS)


def get_optimized_schema(question: str = "") -> str:
    """Trả về schema rút gọn, ưu tiên các bảng/columns liên quan bằng RAG Selection (Pillar 2)."""
    schema_text = get_multi_db_schema_context()
    
    # 1. Nếu schema nhỏ, trả về luôn để tiết kiệm token/time
    if len(schema_text) <= MAX_SCHEMA_CHARS:
        return schema_text

    # 2. Nếu schema lớn, dùng 'Schema Selector' (RAG nội bộ)
    try:
        from app.agents.llm_setup import get_llm
        llm = get_llm(task="admin", temperature=0) # Dùng mode admin/nhanh cho tác vụ lọc
        
        # Lấy danh sách tên bảng hiện có
        table_names = re.findall(r"Table: ([A-Za-z0-9_.]+)", schema_text)
        
        selector_prompt = f"""Dựa vào danh sách các bảng dưới đây và câu hỏi của người dùng, hãy liệt kê tối đa 10 tên bảng cần thiết nhất để trả lời câu hỏi.
Chỉ trả về danh sách tên bảng, phân tách bằng dấu phẩy. Không giải thích.

Danh sách bảng: {', '.join(table_names)}
Câu hỏi: {question}
"""
        response = llm.invoke(selector_prompt)
        # Sửa lỗi: LangChain có thể trả về content dạng list nếu model output phức tạp
        content = response.content
        if isinstance(content, list):
            selected_tables_text = "".join([part.get("text", "") if isinstance(part, dict) else str(part) for part in content])
        else:
            selected_tables_text = str(content)
            
        selected_tables = [t.strip() for t in selected_tables_text.split(",") if t.strip()]
        
        # Lọc schema chỉ lấy các bảng đã chọn
        filtered_lines = []
        include_table = False
        for line in schema_text.splitlines():
            # Luôn giữ lại thông tin meta
            if any(k in line.lower() for k in ["hệ quản trị", "chế độ", "database", "relationships"]):
                filtered_lines.append(line)
                continue
            
            # Check bắt đầu block table
            if line.startswith("Table: "):
                t_name = line[7:]
                include_table = any(t in t_name for t in selected_tables)
            
            if include_table:
                filtered_lines.append(line)

        if filtered_lines:
            return _truncate_text("\n".join(filtered_lines), MAX_SCHEMA_CHARS)

    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"Lỗi RAG Schema Selector: {e}")

    # Fallback về summarize cơ bản nếu AI lỗi
    return _summarize_schema(schema_text)