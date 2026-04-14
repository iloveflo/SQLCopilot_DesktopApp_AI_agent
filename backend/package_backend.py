import os
import subprocess
import sys
import shutil

def get_target_triple():
    """Nhận diện cấu trúc hệ thống để đặt tên sidecar đúng chuẩn Tauri."""
    try:
        # Chạy lệnh rustc để lấy triple nếu có
        result = subprocess.check_output(['rustc', '-vV'], stderr=subprocess.STDOUT).decode()
        for line in result.splitlines():
            if line.startswith('host:'):
                return line.split(':')[1].strip()
    except Exception:
        # Fallback nếu chưa có rust
        import platform
        machine = platform.machine()
        system = platform.system().lower()
        if system == "linux":
            return f"{machine}-unknown-linux-gnu"
        elif system == "darwin":
            return f"{machine}-apple-darwin"
        elif system == "windows":
            return f"{machine}-pc-windows-msvc"
    return "unknown"

def build_sidecar():
    triple = get_target_triple()
    sidecar_name = f"sql-copilot-backend-{triple}"
    
    # Xác định đuôi file theo hệ điều hành
    app_ext = ".exe" if sys.platform == "win32" else ""
    source_filename = f"{sidecar_name}{app_ext}"
    
    print(f"--- Packaging Backend for target: {triple} ---")
    
    dist_path = os.path.join(os.getcwd(), "dist")
    if os.path.exists(dist_path):
        shutil.rmtree(dist_path)
        
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--onefile",
        "--name", sidecar_name, # PyInstaller tự hiểu có thêm .exe hay không
        "--hidden-import", "pymysql",
        "--hidden-import", "uvicorn.logging",
        "--hidden-import", "uvicorn.loops",
        "--hidden-import", "uvicorn.loops.auto",
        "--hidden-import", "uvicorn.protocols",
        "--hidden-import", "uvicorn.protocols.http",
        "--hidden-import", "uvicorn.protocols.http.auto",
        "--hidden-import", "uvicorn.protocols.websockets",
        "--hidden-import", "uvicorn.protocols.websockets.auto",
        "--collect-all", "langgraph",
        "--collect-all", "langgraph.checkpoint.sqlite",
        "--collect-all", "langchain_google_genai",
        "app/main.py"
    ]
    
    try:
        subprocess.check_call(cmd)
        print(f"\n[OK] Packaging successful: dist/{source_filename}")
        
        target_dir = os.path.join("..", "frontend", "src-tauri", "binaries")
        os.makedirs(target_dir, exist_ok=True)
        
        # Copy file có đuôi chuẩn sang thư mục tauri
        shutil.copy(
            os.path.join("dist", source_filename), 
            os.path.join(target_dir, source_filename)
        )
        print(f"[OK] Copied Sidecar to: {target_dir}")
        
    except subprocess.CalledProcessError as e:
        print(f"[ERROR] Error during packaging: {e}")
        sys.exit(1)
        
if __name__ == "__main__":
    build_sidecar()
