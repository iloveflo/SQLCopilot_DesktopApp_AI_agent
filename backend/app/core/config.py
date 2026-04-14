import json
import os
from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache
from typing import Optional
from pathlib import Path

class Settings(BaseSettings):
    """Quản lý tập trung toàn bộ cấu hình hệ thống."""
    # App Info
    APP_NAME: str = "SQLCopilot AI Engine"
    ENVIRONMENT: str = "development"
    LOG_LEVEL: str = "INFO"

    # Google Gemini API Key (Bắt buộc để chạy AI)
    GOOGLE_API_KEY: Optional[str] = None 
    
    # Database
    LOCAL_DB_URL: Optional[str] = None # Cho phép None nếu app chưa kết nối DB
    
    # Pydantic v2 Config
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore" 
    )

    def get_persistence_path(self) -> Path:
        """Đường dẫn lưu trữ cấu hình tại thư mục người dùng."""
        return Path.home() / ".sqlcopilot_settings.json"

    def save_to_json(self):
        """Lưu các cấu hình quan trọng vào file JSON."""
        path = self.get_persistence_path()
        data = {
            "GOOGLE_API_KEY": self.GOOGLE_API_KEY,
            "LOCAL_DB_URL": self.LOCAL_DB_URL
        }
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)

    def load_from_json(self):
        """Nạp cấu hình từ file JSON nếu tồn tại, hỗ trợ fallback thông minh."""
        path = self.get_persistence_path()
        if path.exists():
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if data.get("GOOGLE_API_KEY"):
                        self.GOOGLE_API_KEY = data["GOOGLE_API_KEY"]
                    if data.get("LOCAL_DB_URL"):
                        self.LOCAL_DB_URL = data["LOCAL_DB_URL"]
            except Exception as e:
                print(f"Lỗi khi nạp file cấu hình JSON: {e}")
        
        # Nếu chưa có Key, thử tìm kiếm thông minh từ .env hoặc môi trường
        if not self.GOOGLE_API_KEY:
            # 1. Thử lấy từ môi trường hệ thống trực tiếp
            env_key = os.getenv("GOOGLE_API_KEY")
            
            # 2. Nếu không có, "lùng sục" file .env ở các thư mục cha (hữu ích khi chạy Sidecar)
            if not env_key:
                current_dir = Path.cwd()
                # Tìm ngược lên tối đa 5 cấp thư mục để tìm .env
                for _ in range(5):
                    env_path = current_dir / ".env"
                    if env_path.exists():
                        try:
                            from dotenv import load_dotenv
                            load_dotenv(env_path)
                            env_key = os.getenv("GOOGLE_API_KEY")
                            if env_key: break
                        except ImportError:
                            # Nếu không có python-dotenv, thử đọc thủ công
                            with open(env_path, "r") as f:
                                for line in f:
                                    if line.startswith("GOOGLE_API_KEY="):
                                        env_key = line.split("=", 1)[1].strip().strip('"').strip("'")
                                        if env_key: break
                    current_dir = current_dir.parent
                    if current_dir == current_dir.parent: break

            if env_key:
                self.GOOGLE_API_KEY = env_key
                print(f"Hệ thống: Tự động phát hiện và nạp API Key từ môi trường.")
                self.save_to_json() # Lưu lại để lần sau không cần "lùng sục" nữa

@lru_cache()
def get_settings() -> Settings:
    s = Settings()
    s.load_from_json() # Nạp từ file khi khởi tạo
    return s

settings = get_settings()