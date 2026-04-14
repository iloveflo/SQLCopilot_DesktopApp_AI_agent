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
    """Trả về schema rút gọn, ưu tiên các bảng/columns liên quan đến câu hỏi."""
    schema_text = get_multi_db_schema_context()
    if len(schema_text) <= MAX_SCHEMA_CHARS:
        return schema_text

    if question:
        terms = set(re.findall(r"[A-Za-z0-9_]+", question.lower()))
        filtered_lines = []
        for line in schema_text.splitlines():
            lower_line = line.lower()
            if any(keyword in lower_line for keyword in ["hệ quản trị", "chế độ", "database", "schema", "table", "columns", "relationships"]):
                filtered_lines.append(line)
                continue
            if any(term in lower_line for term in terms):
                filtered_lines.append(line)
        if filtered_lines:
            trimmed = "\n".join(filtered_lines)
            return _truncate_text(trimmed, MAX_SCHEMA_CHARS)

    return _summarize_schema(schema_text)