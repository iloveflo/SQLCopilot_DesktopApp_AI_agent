import json
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field
from langchain_core.prompts import ChatPromptTemplate
from app.agents.llm_setup import get_llm

class ChartConfig(BaseModel):
    should_visualize: bool = Field(description="True nếu dữ liệu phù hợp để vẽ biểu đồ (có ít nhất 1 cột số và 1 cột phân loại/thời gian). False nếu chỉ là text hoặc 1 con số đơn lẻ.")
    chart_type: str = Field(description="Loại biểu đồ. Chỉ được chọn 1 trong: 'bar', 'line', 'pie', 'area', 'scatter'. Trả về 'none' nếu không thể vẽ.")
    x_column: Optional[str] = Field(description="Tên cột dùng cho trục X (hoặc labels cho pie chart). Thường là danh mục hoặc thời gian.")
    y_column: Optional[str] = Field(description="Tên cột dùng cho trục Y (hoặc values cho pie chart). Bắt buộc phải là cột chứa số liệu (int/float/decimal).")
    title: str = Field(description="Tiêu đề biểu đồ tiếng Việt ngắn gọn, chuyên nghiệp.")

def generate_chart_config(question: str, raw_data: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """Phân tích raw_data và sinh ra cấu hình JSON cho Plotly.js."""
    if not raw_data or len(raw_data) == 0:
        return None
        
    # Chỉ lấy 3 dòng đầu tiên để LLM phân tích cấu trúc, tránh tốn token
    sample_data = raw_data[:3]
    data_str = json.dumps(sample_data, ensure_ascii=False, default=str)
    columns = list(raw_data[0].keys())

    system_prompt = """Bạn là một Chuyên gia Trực quan hóa Dữ liệu (Lead Data Visualization Architect).
Nhiệm vụ của bạn là phân tích cấu trúc dữ liệu đầu vào, quyết định xem có đủ điều kiện để vẽ biểu đồ hay không, và nếu có thì phải thiết lập cấu hình chuẩn xác nhất.

=== DỮ LIỆU ĐẦU VÀO ===
- Danh sách các cột hiện có: {columns}
- Dữ liệu mẫu (3 dòng đầu): {data}

=== KỶ LUẬT TRỰC QUAN HÓA (BẮT BUỘC TUÂN THỦ 100%) ===
1. BỘ LỌC ĐIỀU KIỆN (VISUALIZATION GATES):
   - CHỈ quyết định vẽ biểu đồ (`should_visualize: true`) NẾU dữ liệu là một mảng có chứa ít nhất 1 cột Danh mục/Thời gian VÀ 1 cột Số liệu (Int/Float).
   - TỪ CHỐI vẽ biểu đồ (`should_visualize: false` và `chart_type: "none"`) NẾU dữ liệu chỉ trả về 1 con số đơn lẻ (Ví dụ: đếm tổng số user), hoặc toàn bộ là văn bản không chứa dữ liệu để đo lường.

3. QUY TẮC CHỌN LOẠI BIỂU ĐỒ (ƯU TIÊN SỰ ĐA DẠNG VÀ CHÍNH XÁC):
   - TRUY VẤN THỜI GIAN (Time-series): 
       + BẮT BUỘC dùng `line` hoặc `area`. Dùng `area` nếu muốn nhấn mạnh vào độ lớn của tổng thể tích lũy theo thời gian.
   - SO SÁNH DANH MỤC (Categorical):
       + Nếu số lượng danh mục <= 10 và muốn so sánh độ lớn -> Dùng `bar`.
       + Nếu muốn xem Tỷ trọng/Cơ cấu (%) VÀ số danh mục ít (<= 6) -> ƯU TIÊN dùng `pie`.
   - TƯƠNG QUAN & PHÂN BỔ (Relationship/Distribution):
       + Nếu có 2 cột số liệu muốn so sánh tương quan HOẶC số lượng điểm dữ liệu rất lớn (> 30 điểm) -> ƯU TIÊN dùng `scatter` để tránh làm rối biểu đồ cột.
   - XU HƯỚNG TĂNG TRƯỞNG: Nếu dữ liệu thể hiện sự tăng/giảm liên tục -> Nên dùng `line` thay vì `bar`.

4. QUY TẮC GHÉP CỘT (AXIS MAPPING):
   - `x_column`: BẮT BUỘC chọn đúng 1 tên cột chứa Danh mục hoặc Thời gian.
   - `y_column`: BẮT BUỘC chọn đúng 1 tên cột chứa Số liệu để tính toán (Ví dụ: sum, count, total...).
   - Tên cột BẮT BUỘC phải copy y nguyên từng ký tự từ phần "Danh sách các cột hiện có" ở trên. Tuyệt đối không tự bịa ra tên cột.

4. TIÊU ĐỀ (TITLE):
   - Đặt một tiêu đề tiếng Việt chuyên nghiệp, ngắn gọn, phản ánh đúng dữ liệu. (Ví dụ: "Biểu đồ Thống kê Doanh thu theo Ngày").
"""
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        ("human", "Câu hỏi gốc của user: {question}\nHãy xác định cấu hình biểu đồ.")
    ])
    
    llm = get_llm(task="visualizer", temperature=0.0).with_structured_output(ChartConfig)
    chain = prompt | llm
    
    try:
        # Gọi LLM để suy luận cấu trúc
        result: ChartConfig = chain.invoke({
            "columns": columns,
            "data": data_str,
            "question": question
        })

        if not result.should_visualize or result.chart_type == "none" or not result.x_column or not result.y_column:
            return None
            
        # --- BẢN VÁ: Dọn dẹp thói quen viết hoa/viết thừa của AI ---
        # Chuyển "Bar Chart", "PIE", "Line chart" -> "bar", "pie", "line"
        safe_chart_type = result.chart_type.lower().replace(" chart", "").strip()
            
        # --- BẢN VÁ: Gộp dữ liệu trùng lặp (Aggregation) ---
        # Tránh việc Plotly vẽ chồng nhiều cột cùng tên (Vd: Túi Tote Da, 10 và Túi Tote Da, 48)
        # làm người dùng bối rối vì Tooltip không khớp chiều cao cột.
        from collections import defaultdict
        
        aggregated = defaultdict(float)
        for row in raw_data:
            x_val = row.get(result.x_column)
            if x_val is None: continue # Bỏ qua hàng không có nhãn
            
            y_val = row.get(result.y_column)
            try:
                val = float(y_val) if y_val is not None else 0
                aggregated[str(x_val)] += val
            except (ValueError, TypeError):
                # Bỏ qua nếu cột Y không phải là số hợp lệ
                continue
        
        # Chuyển dữ liệu đã gộp thành list cho Plotly
        x_data = list(aggregated.keys())
        y_data = list(aggregated.values())

        plotly_type = safe_chart_type
        fill_mode = None
        mode = None
        
        if safe_chart_type == 'area':
            plotly_type = 'scatter'
            fill_mode = 'tozeroy'
            mode = 'lines'
        elif safe_chart_type == 'scatter':
            plotly_type = 'scatter'
            mode = 'markers'

        plotly_config = {
            "data": [
                {
                    "x": x_data if safe_chart_type != 'pie' else None,
                    "y": y_data if safe_chart_type != 'pie' else None,
                    "labels": x_data if safe_chart_type == 'pie' else None,
                    "values": y_data if safe_chart_type == 'pie' else None,
                    "type": plotly_type,
                    "fill": fill_mode,
                    "mode": mode,
                    "name": result.y_column
                }
            ],
            "layout": {
                "title": result.title,
                "xaxis": {"title": result.x_column} if safe_chart_type != 'pie' else None,
                "yaxis": {"title": result.y_column} if safe_chart_type != 'pie' else None,
            }
        }
        
        # Lọc bỏ các key None để config gọn nhẹ
        plotly_config["data"][0] = {k: v for k, v in plotly_config["data"][0].items() if v is not None}
        plotly_config["layout"] = {k: v for k, v in plotly_config["layout"].items() if v is not None}
        
        return plotly_config

    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"Lỗi khi sinh cấu hình biểu đồ: {e}")
        return None