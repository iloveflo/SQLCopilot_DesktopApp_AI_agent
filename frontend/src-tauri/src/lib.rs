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

            // 1. Xác định thư mục lưu Log (Ưu tiên thư mục hiện tại, fallback ra Desktop)
            let mut log_dir = std::env::current_dir().unwrap_or_else(|_| std::path::PathBuf::from(".")).join("logs");
            
            // Kiểm tra quyền ghi bằng cách thử tạo folder
            if std::fs::create_dir_all(&log_dir).is_err() {
                // Nếu không có quyền (ví dụ trong Program Files), chuyển ra Desktop
                if let Ok(desktop) = app.path().desktop_dir() {
                    log_dir = desktop.join("SQLCopilot_Logs");
                }
            }
            let _ = std::fs::create_dir_all(&log_dir);

            // 2. Kích hoạt Logging System cho cả bản Release
            app.handle().plugin(
                tauri_plugin_log::Builder::default()
                    .targets([
                        tauri_plugin_log::Target::new(tauri_plugin_log::TargetKind::Stdout),
                        tauri_plugin_log::Target::new(tauri_plugin_log::TargetKind::Folder {
                            path: log_dir.clone(),
                            file_name: None,
                        }),
                        tauri_plugin_log::Target::new(tauri_plugin_log::TargetKind::Webview),
                    ])
                    .level(log::LevelFilter::Info)
                    .build(),
            )?;

            log::info!("Tauri App starting up... Logs stored at: {:?}", log_dir);

            // 2. Tự động dọn dẹp các tiến trình backend cũ bị treo trên Windows
            #[cfg(windows)]
            {
                let _ = std::process::Command::new("powershell")
                    .args(["-Command", "Get-NetTCPConnection -LocalPort 8000 -ErrorAction SilentlyContinue | ForEach-Object { Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue }"])
                    .status();
            }

            // 3. Khởi chạy Backend Sidecar tự động
            let sidecar_command = app.shell().sidecar("sql-copilot-backend")?;
            
            let (mut rx, child) = match sidecar_command.spawn() {
                Ok(res) => res,
                Err(e) => {
                    log::error!("CRITICAL: Failed to spawn sidecar: {e}");
                    return Err(Box::new(std::io::Error::new(
                        std::io::ErrorKind::Other,
                        format!("Không thể khởi chạy Backend Engine.\nLỗi: {}\nChi tiết đã được ghi vào log.", e)
                    )));
                }
            };

            // Lưu Handle vào state của App
            let state = app.state::<SidecarState>();
            *state.0.lock().unwrap() = Some(child);

            // 4. Pipe logs từ sidecar vào hệ thống log của Tauri
            tauri::async_runtime::spawn(async move {
                log::info!("Backend monitoring loop started.");
                while let Some(event) = rx.recv().await {
                    match event {
                        tauri_plugin_shell::process::CommandEvent::Stdout(line) => {
                            log::info!("BACKEND: {}", String::from_utf8_lossy(&line).trim());
                        }
                        tauri_plugin_shell::process::CommandEvent::Stderr(line) => {
                            log::error!("BACKEND ERROR: {}", String::from_utf8_lossy(&line).trim());
                        }
                        tauri_plugin_shell::process::CommandEvent::Terminated(payload) => {
                            log::warn!("BACKEND TERMINATED! Code: {:?}, Signal: {:?}", payload.code, payload.signal);
                        }
                        _ => {}
                    }
                }
                log::warn!("Backend monitoring loop exited.");
            });
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
