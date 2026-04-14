import os
import google.generativeai as genai
from dotenv import load_dotenv

# Load biến môi trường từ file .env (chứa GOOGLE_API_KEY)
load_dotenv()

# Cấu hình thư viện gốc của Google
api_key = os.environ.get("GOOGLE_API_KEY")
if not api_key:
    print("❌ Lỗi: Không tìm thấy GOOGLE_API_KEY.")
    exit()

genai.configure(api_key=api_key)

print("🔍 Đang truy vấn danh sách các Models khả dụng cho API Key của bạn...\n")
print("-" * 50)

# Liệt kê tất cả các mô hình có khả năng sinh chữ (generateContent)
count = 0
for m in genai.list_models():
    if 'generateContent' in m.supported_generation_methods:
        print(f"✅ API ID: {m.name}")
        count += 1

print("-" * 50)
print(f"Tổng cộng có {count} mô hình khả dụng.")