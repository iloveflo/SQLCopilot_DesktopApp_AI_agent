use tauri::Manager;
use tauri_plugin_shell::ShellExt;
use std::sync::Mutex;

// Cấu trúc để lưu trữ Handle của Backend Sidecar
struct SidecarState(Mutex<Option<tauri_plugin_shell::process::CommandChild>>);

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .manage(SidecarState(Mutex::new(None))) // Khởi tạo state trống
        .setup(|app| {
            // Dọn dẹp cổng trước khi khởi động
            #[cfg(windows)]
            {
                let _ = std::process::Command::new("powershell")
                    .args(["-Command", "Get-NetTCPConnection -LocalPort 8000 -ErrorAction SilentlyContinue | ForEach-Object { Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue }"])
                    .status();
            }
            #[cfg(not(windows))]
            {
                let _ = std::process::Command::new("fuser")
                    .args(["-k", "8000/tcp"])
                    .status();
            }

            // Khởi chạy Backend Sidecar tự động
            let sidecar_command = app.shell().sidecar("sql-copilot-backend");
            
            let (mut rx, child) = match sidecar_command.spawn() {
                Ok(res) => res,
                Err(e) => {
                    log::error!("Failed to spawn sidecar: {e}");
                    // Trên bản Release, chúng ta báo lỗi trực tiếp để User biết
                    return Err(Box::new(std::io::Error::new(
                        std::io::ErrorKind::Other,
                        format!("Không thể khởi động Backend Engine (Sidecar).\nLỗi: {}\nVui lòng kiểm tra file cài đặt.", e)
                    )));
                }
            };

            // Lưu Handle vào state của App
            let state = app.state::<SidecarState>();
            *state.0.lock().unwrap() = Some(child);

            // Pipe logs từ sidecar ra terminal để debug
            tauri::async_runtime::spawn(async move {
                while let Some(event) = rx.recv().await {
                    if let tauri_plugin_shell::process::CommandEvent::Stdout(line) = event {
                        println!("BACKEND: {}", String::from_utf8_lossy(&line).trim());
                    } else if let tauri_plugin_shell::process::CommandEvent::Stderr(line) = event {
                        eprintln!("BACKEND ERROR: {}", String::from_utf8_lossy(&line).trim());
                    }
                }
            });

            if cfg!(debug_assertions) {
                app.handle().plugin(
                    tauri_plugin_log::Builder::default()
                        .level(log::LevelFilter::Info)
                        .build(),
                )?;
            }
            Ok(())
        })
        .on_window_event(|window, event| {
            if let tauri::WindowEvent::CloseRequested { .. } = event {
                // Giải phóng Handle và kill child process
                let child = {
                    let state = window.state::<SidecarState>();
                    let x = state.0.lock().unwrap().take();
                    x
                };

                if let Some(c) = child {
                    let _ = c.kill();
                    
                    // Kill bổ sung theo cổng để chắc chắn (đặc biệt quan trọng trên Windows nếu sidecar spawn sub-process)
                    #[cfg(windows)]
                    {
                        let _ = std::process::Command::new("powershell")
                            .args(["-Command", "Get-NetTCPConnection -LocalPort 8000 -ErrorAction SilentlyContinue | ForEach-Object { Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue }"])
                            .status();
                    }
                    #[cfg(not(windows))]
                    {
                        let _ = std::process::Command::new("fuser")
                            .args(["-k", "8000/tcp"])
                            .status();
                    }
                    println!("Tauri: Backend sidecar terminated and port 8000 cleared.");
                }
            }
        })
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
