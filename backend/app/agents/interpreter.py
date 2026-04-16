from langchain_core.prompts import ChatPromptTemplate
from app.agents.llm_setup import get_llm
import json
import re
import logging
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

def _extract_gemma_content(raw_content) -> str:
    if isinstance(raw_content, list):
        return "".join([
            block.get("text", "") 
            for block in raw_content 
            if isinstance(block, dict) and block.get("type") == "text"
        ])
    return str(raw_content)

def _extract_tag(text: str, tag: str) -> str:
    pattern = rf"\[{tag}\](.*?)\[/{tag}\]"
    match = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
    return match.group(1).strip() if match else ""

def interpret_and_visualize(question: str, sql: str, raw_data: list) -> Dict[str, Any]:
    """Gộp báo cáo và vẽ biểu đồ vào 1 lần gọi LLM (Speed Patch 2.0)."""
    llm = get_llm(task="interpreter", temperature=0.1)
    
    safe_data = raw_data[:50] if raw_data else []
    data_str = json.dumps(safe_data, ensure_ascii=False, default=str)
    columns = list(raw_data[0].keys()) if raw_data else []

    system_prompt = """Bạn là một Chuyên gia Phân tích Dữ liệu và Trực quan hóa cấp cao.
Nhiệm vụ: Phân tích dữ liệu và đề xuất cấu hình biểu đồ (nếu phù hợp).

=== QUY TẮC PHẢN HỒI (BẮT BUỘC) ===
Bạn phải trả về 2 khối nội dung theo đúng định dạng sau:

1. Khối phân tích: [ANALYSIS] ... lời giải thích ngắn gọn bằng tiếng Việt ... [/ANALYSIS]
2. Khối biểu đồ: [CHART_CONFIG] { "should_visualize": true/false, "chart_type": "bar"/"line"/"pie", "x_column": "...", "y_column": "...", "title": "..." } [/CHART_CONFIG]

=== KỶ LUẬT PHÂN TÍCH ===
- Chỉ dựa trên dữ liệu thật. Không bịa.
- Nếu không có dữ liệu, set should_visualize: false.
- Biểu đồ: 1 cột số (y) và 1 cột danh mục/thời gian (x).

=== TÀI LIỆU DỮ LIỆU ===
SQL: {sql}
Cột: {columns}
Data (TOP 50): {data}
"""
    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        ("human", "Câu hỏi: {question}")
    ])
    
    chain = prompt | llm
    
    try:
        response = chain.invoke({"data": data_str, "sql": sql, "question": question, "columns": columns})
        raw_text = _extract_gemma_content(getattr(response, "content", response))
        
        analysis = _extract_tag(raw_text, "ANALYSIS")
        config_str = _extract_tag(raw_text, "CHART_CONFIG")
        
        chart_config = None
        if "should_visualize" in config_str.lower():
            try:
                # Ép kiểu an toàn cho JSON
                config_json = json.loads(config_str)
                if config_json.get("should_visualize"):
                    # Sử dụng logic transform cũ để tạo Plotly config
                    chart_config = _build_plotly_config(config_json, raw_data)
            except:
                pass

        return {
            "answer": analysis or raw_text[:500],
            "chart_config": chart_config
        }
        
    except Exception as e:
        logger.error(f"Lỗi Combined Interpreter: {e}")
        return {"answer": "Lỗi phân tích dữ liệu.", "chart_config": None}

def _build_plotly_config(res: dict, raw_data: list) -> Optional[dict]:
    # Logic gộp và tối ưu biểu đồ (tương tự visualizer.py cũ)
    try:
        x_col = res.get("x_column")
        y_col = res.get("y_column")
        c_type = res.get("chart_type", "bar").lower()
        
        from collections import defaultdict
        aggregated = defaultdict(float)
        for row in raw_data:
            x_v = row.get(x_col)
            y_v = row.get(y_col)
            if x_v is not None:
                try: aggregated[str(x_v)] += float(y_v) if y_v is not None else 0
                except: continue
        
        x_data = list(aggregated.keys())
        y_data = list(aggregated.values())
        
        return {
            "data": [{
                "x": x_data if c_type != 'pie' else None,
                "y": y_data if c_type != 'pie' else None,
                "labels": x_data if c_type == 'pie' else None,
                "values": y_data if c_type == 'pie' else None,
                "type": c_type,
                "name": y_col
            }],
            "layout": { "title": res.get("title", "Biểu đồ"), "margin": {"t": 40} }
        }
    except: return None