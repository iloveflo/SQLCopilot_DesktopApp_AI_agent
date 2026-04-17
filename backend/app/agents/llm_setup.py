from langchain_google_genai import ChatGoogleGenerativeAI
from app.core.config import settings

MODEL_TASK_MAP = {
    "planner": "gemma-4-31b-it",        
    "sql_generation": "gemma-4-31b-it", 
    "interpreter": "gemma-4-31b-it",  
    "visualizer": "gemma-4-31b-it",   
    "admin": "gemma-4-31b-it",          
    "router": "gemini-3.1-flash-lite-preview",
    "default": "gemma-4-31b-it",
}

DEFAULT_MAX_TOKENS = {
    "planner": 1024,
    "sql_generation": 2048, # Tăng lên để chứa được các câu SQL phức tạp + Comment
    "interpreter": 2048, 
    "visualizer": 512,
    "admin": 1024,
    "router": 100,
    "default": 1024,
}

def get_llm(task: str = "default", temperature: float = 0.0, max_tokens: int | None = None):
    """
    Khởi tạo instance Google Gemini LLM dựa trên tác vụ cụ thể.
    Sử dụng API Key từ lớp settings tập trung.
    """
    model_name = MODEL_TASK_MAP.get(task, MODEL_TASK_MAP["default"])
    
    if max_tokens is None:
        max_tokens = DEFAULT_MAX_TOKENS.get(task, DEFAULT_MAX_TOKENS["default"])

    if not settings.GOOGLE_API_KEY:
        raise ValueError("Chưa cấu hình Google API Key. Vui lòng vào phần 'Quản trị' -> 'Cấu hình' để nhập Key trước khi bắt đầu.")

    return ChatGoogleGenerativeAI(
        model=model_name,
        google_api_key=settings.GOOGLE_API_KEY, # Truy xuất trực tiếp từ settings
        temperature=temperature,
        max_output_tokens=max_tokens,
        # Tránh lỗi Safety Filter của Google làm gián đoạn câu SQL 
        safety_settings=None 
    )