# SQL Copilot Pro AI

Ứng dụng desktop hỗ trợ hỏi đáp dữ liệu bằng ngôn ngữ tự nhiên, chuyển câu hỏi thành SQL, thực thi truy vấn trên MySQL và trả về kết quả kèm bảng dữ liệu, biểu đồ và lịch sử hội thoại.

Project được tổ chức theo kiến trúc:

- `frontend/`: React + Vite + Tauri desktop shell.
- `backend/`: FastAPI + LangGraph + SQLAlchemy + Google Gemini.
- `frontend/src-tauri/`: phần native của Tauri, đồng thời chạy backend như sidecar process khi đóng gói desktop app.

## Mục tiêu chính

- Cho phép người dùng kết nối tới MySQL server.
- Chọn một hoặc nhiều database để AI phân tích.
- Sinh kế hoạch truy vấn trước khi chạy thật theo mô hình HITL.
- Tạo SQL từ tiếng Việt.
- Thực thi SQL an toàn theo luồng backend.
- Diễn giải kết quả và sinh cấu hình biểu đồ Plotly.
- Lưu session chat và ngữ cảnh để có thể mở lại.
- Hỗ trợ một số thao tác quản trị MySQL cho tài khoản admin/root.

## Tính năng hiện có

### 1. Chat với database bằng tiếng Việt

Người dùng nhập câu hỏi tự nhiên, backend sẽ đi qua chuỗi agent:

1. Đọc schema liên quan.
2. Lập kế hoạch truy vấn.
3. Chờ người dùng duyệt hoặc chỉnh kế hoạch.
4. Sinh SQL.
5. Thực thi truy vấn.
6. Diễn giải kết quả.
7. Đề xuất biểu đồ nếu phù hợp.

### 2. Human-in-the-loop cho truy vấn

Luồng chat mặc định không nhảy thẳng vào chạy SQL ngay. Hệ thống sẽ trả về plan trước, sau đó frontend cho phép người dùng:

- duyệt kế hoạch hiện tại
- chỉnh feedback cho kế hoạch
- tiếp tục sang bước tạo SQL và chạy query

### 3. Multi-database analysis

Người dùng có thể chọn nhiều database đang tồn tại trên cùng một MySQL server. Backend sẽ ghi nhớ danh sách database đang active và dùng chúng khi:

- đọc schema
- sinh SQL dạng cross-database
- khôi phục lại session cũ

### 4. Session chat và lịch sử hội thoại

Mỗi phiên chat có:

- `session_id`
- tên session
- danh sách database đang dùng
- số lượng tin nhắn
- lịch sử chat và dữ liệu kết quả

Lịch sử này được lưu trên SQLite để có thể mở lại ở lần chạy sau.

### 5. Admin panel

Nếu user hiện tại có quyền admin/root trên MySQL, giao diện sẽ mở được khu vực quản trị:

- xem danh sách MySQL users
- nhập câu lệnh quản trị bằng tiếng Việt
- xem trước SQL quản trị
- duyệt rồi mới thực thi
- cấu hình Google Gemini API key

### 6. Desktop packaging và release theo tag

Workflow release GitHub Actions sẽ build desktop app cho nhiều nền tảng. Phiên bản artifact được đồng bộ theo tag `vX.Y.Z` trước khi build.

Ví dụ:

- tag `v1.0.8`
- artifact sẽ mang version `1.0.8`

## Kiến trúc tổng quan

### Frontend

Stack chính:

- React 19
- TypeScript
- Vite
- Tauri 2
- Plotly

Frontend đảm nhiệm:

- quản lý kết nối MySQL
- chọn database
- quản lý session sidebar
- render chat thread
- render bảng dữ liệu và biểu đồ
- hiển thị tiến trình từng bước của agent qua SSE
- mở panel quản trị

### Backend

Stack chính:

- FastAPI
- SQLAlchemy
- LangGraph
- LangChain Google GenAI
- SQLite cho memory/session

Backend đảm nhiệm:

- kết nối MySQL server
- lấy schema
- sinh plan / SQL / diễn giải / biểu đồ
- stream tiến trình xử lý qua Server-Sent Events
- quản lý session chat
- quản lý cấu hình API key
- hỗ trợ lệnh quản trị cho user admin

### Tauri sidecar

Desktop app không nhúng backend vào web frontend trực tiếp. Thay vào đó:

- backend Python được đóng gói bằng PyInstaller
- binary backend được copy vào `frontend/src-tauri/`
- Tauri khởi chạy sidecar khi app mở
- frontend gọi API tới `http://127.0.0.1:8000`

## Công nghệ và dependency chính

### Backend

- `fastapi`
- `uvicorn`
- `sqlalchemy`
- `pymysql`
- `langgraph`
- `langchain`
- `langchain-google-genai`
- `python-dotenv`
- `pyinstaller`

### Frontend

- `react`
- `react-dom`
- `typescript`
- `vite`
- `@tauri-apps/cli`
- `plotly.js`
- `react-plotly.js`

## Yêu cầu môi trường

### Bắt buộc

- Python 3.12 hoặc tương đương
- Node.js 20+
- npm
- Rust toolchain stable
- MySQL server để kết nối dữ liệu
- Google Gemini API key

### Khi build desktop

- Windows: Visual Studio Build Tools / môi trường Rust phù hợp
- macOS: Xcode Command Line Tools
- Linux: các package Tauri/WebKitGTK tương ứng

Workflow CI hiện cài thêm trên Ubuntu:

- `libwebkit2gtk-4.1-dev`
- `libappindicator3-dev`
- `librsvg2-dev`
- `patchelf`

## Cài đặt project

### 1. Clone source

```bash
git clone <your-repo-url>
cd sql-copilot-build
```

### 2. Cài backend

```bash
cd backend
python -m venv .venv
```

Windows:

```bash
.venv\Scripts\activate
pip install -r requirements.txt
```

macOS/Linux:

```bash
source .venv/bin/activate
pip install -r requirements.txt
```

### 3. Cài frontend

```bash
cd ../frontend
npm install
```

## Cấu hình

### Cấu hình AI

Code hiện tại dùng `GOOGLE_API_KEY` cho Google Gemini.

Có 2 cách cấu hình:

- nhập trực tiếp trong giao diện `Admin -> Cấu hình`
- tạo file `backend/.env`

Ví dụ:

```env
ENVIRONMENT=development
LOG_LEVEL=INFO
APP_NAME="SQLCopilot API Engine"
GOOGLE_API_KEY=your_google_api_key_here
```

Lưu ý:

- file `backend/.env.example` hiện còn nội dung cũ liên quan `GROQ_API_KEY`
- nhưng code backend hiện tại thực tế dùng `GOOGLE_API_KEY`

### Cấu hình kết nối database

Thông tin kết nối MySQL được nhập trực tiếp trên giao diện desktop/web thông qua modal kết nối:

- host
- port
- user
- password
- database mặc định tùy chọn

Backend hiện tại sử dụng driver `PyMySQL`, nên luồng chính đang nhắm tới MySQL.

## Chạy local cho backend + frontend

### Chạy backend riêng

Từ thư mục `backend/`:

```bash
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Tài liệu OpenAPI:

- `http://127.0.0.1:8000/docs`

### Chạy frontend web riêng

Từ thư mục `frontend/`:

```bash
npm run dev
```

Frontend mặc định gọi backend tại:

- `http://127.0.0.1:8000`

Có thể override bằng biến môi trường:

```bash
VITE_API_BASE=http://127.0.0.1:8000
```

## Chạy desktop app bằng Tauri

### Cách ổn định nhất

1. Đóng gói backend sidecar.
2. Chạy Tauri app.

Từ thư mục `backend/`:

```bash
python package_backend.py
```

Script này sẽ:

- build backend bằng PyInstaller
- tạo binary theo target triple
- copy binary sang `frontend/src-tauri/`

Sau đó từ thư mục `frontend/`:

```bash
npx tauri dev
```

### Lưu ý về script npm

Trong `frontend/package.json` hiện có:

- `npm run tauri:package-backend`
- `npm run tauri:dev`
- `npm run tauri:build`

Nhưng script `tauri:package-backend` đang dùng đường dẫn Python venv kiểu Windows:

- `..\\backend\\.venv\\Scripts\\python.exe`

Nếu chạy trên macOS/Linux, nên dùng trực tiếp:

```bash
cd backend && python package_backend.py
cd ../frontend && npx tauri dev
```

## Build production desktop app

Từ thư mục `backend/`:

```bash
python package_backend.py
```

Từ thư mục `frontend/`:

```bash
npx tauri build
```

Hoặc trên Windows có thể dùng:

```bash
npm run tauri:build
```

Artifact build sẽ nằm trong output của Tauri tương ứng với từng nền tảng.

## GitHub Release flow

Workflow release nằm tại:

- [`.github/workflows/release.yml`](./.github/workflows/release.yml)

Trigger:

- push tag dạng `v*`
- chạy tay qua `workflow_dispatch`

Luồng release:

1. checkout source
2. setup Python
3. install backend dependencies
4. package backend sidecar
5. setup Node
6. install frontend dependencies
7. đồng bộ app version từ tag
8. setup Rust
9. build và draft release qua `tauri-action`

### Quy tắc version

Workflow hiện tại sẽ tự chuyển:

- `v1.0.8` -> `1.0.8`

và cập nhật version vào:

- `frontend/package.json`
- `frontend/package-lock.json`
- `frontend/src-tauri/tauri.conf.json`
- `frontend/src-tauri/Cargo.toml`

Script thực hiện việc này:

- [`frontend/scripts/sync-version.mjs`](./frontend/scripts/sync-version.mjs)

## Cấu trúc thư mục

```text
sql-copilot-build/
├─ backend/
│  ├─ app/
│  │  ├─ agents/           # planner, nl2sql, interpreter, visualizer, admin
│  │  ├─ api/routes/       # route FastAPI
│  │  ├─ core/             # settings và config trung tâm
│  │  ├─ db/               # connection manager, metadata, session store
│  │  ├─ schemas/          # Pydantic schema
│  │  └─ main.py           # entrypoint FastAPI
│  ├─ package_backend.py   # đóng gói backend sidecar bằng PyInstaller
│  └─ requirements.txt
├─ frontend/
│  ├─ src/
│  │  ├─ api/              # client gọi backend
│  │  ├─ components/       # UI chính
│  │  ├─ lib/
│  │  ├─ types/
│  │  └─ App.tsx
│  ├─ src-tauri/
│  │  ├─ src/              # mã Rust cho Tauri
│  │  ├─ icons/
│  │  ├─ tauri.conf.json
│  │  └─ Cargo.toml
│  ├─ scripts/
│  │  └─ sync-version.mjs
│  └─ package.json
└─ .github/workflows/
   └─ release.yml
```

## Luồng xử lý chat

Khi người dùng gửi một câu hỏi:

1. Frontend gọi `POST /chat/ask`.
2. Backend stream tiến trình qua SSE.
3. LangGraph workflow chạy theo state machine:
   - `reader`
   - `planner`
   - `sql_coder`
   - `db_executor`
   - `data_teller`
4. Nếu chưa được duyệt, luồng dừng sau planner.
5. Sau khi duyệt, backend sinh SQL và chạy query.
6. Kết quả được diễn giải và trả về kèm:
   - `answer`
   - `sql_query`
   - `raw_data`
   - `chart_config`

## API chính

### System

- `GET /`

### Database

- `GET /db/health`
- `GET /db/schema`

### Connection

- `GET /connection/status`
- `POST /connection/connect`
- `POST /connection/use_db`
- `GET /connection/list`
- `POST /connection/disconnect`
- `POST /connection/select_databases`
- `GET /connection/active_databases`

### Sessions

- `POST /sessions`
- `GET /sessions`
- `GET /sessions/{session_id}`
- `PATCH /sessions/{session_id}`
- `DELETE /sessions/{session_id}`
- `POST /sessions/{session_id}/restore`
- `PUT /sessions/{session_id}/databases`

### Chat

- `POST /chat/ask`
- `DELETE /chat/session/{session_id}`
- `GET /chat/history/{session_id}`

### Admin

- `POST /admin/command`
- `GET /admin/users`
- `GET /admin/config`
- `POST /admin/config`

## Nơi lưu dữ liệu cục bộ

### Session memory và lịch sử chat

LangGraph checkpoint và metadata session hiện được lưu trong SQLite tại các vị trí:

- `~/.sqlcopilot_chat.sqlite3`
- bảng `chat_sessions` cho metadata session

Ngoài ra trong repo hiện cũng có một số file SQLite phục vụ dev/test.

### Cấu hình người dùng

Settings quan trọng được lưu tại:

- `~/.sqlcopilot_settings.json`

Hiện file này dùng để lưu:

- `GOOGLE_API_KEY`
- `LOCAL_DB_URL`

### Log

Backend và Tauri đều có cơ chế ghi log.

Thư mục log được ưu tiên:

- `./logs` tính theo thư mục chạy app

Nếu không có quyền ghi, app fallback ra:

- Desktop của người dùng
- thư mục `SQLCopilot_Logs`

## Bảo mật và quyền

- Password MySQL được nhập từ frontend và giữ trong memory của backend trong suốt phiên làm việc.
- Các endpoint admin bị chặn nếu user hiện tại không có quyền admin/root.
- Luồng admin command bắt buộc xem trước SQL trước khi thực thi.
- Luồng chat thông thường có bước plan approval để giảm rủi ro chạy truy vấn sai ý.

## Test

Trong `backend/` hiện có một số file test/thử nghiệm:

- `test_main.py`
- `test_db.py`
- `test_sqlite.py`

Tuy nhiên project hiện chưa có một README test workflow chuẩn hóa hoặc test runner tập trung. Nếu cần CI test rõ ràng hơn, nên bổ sung thêm pytest config và test command thống nhất.

## Giới hạn hiện tại

- Luồng kết nối thực tế hiện đang tập trung vào MySQL qua `PyMySQL`.
- `backend/.env.example` chưa đồng bộ hoàn toàn với code hiện tại vì còn nhắc `GROQ_API_KEY`.
- Một số text giao diện/log trong source còn encoding cũ, không ảnh hưởng trực tiếp logic nhưng nên dọn lại.
- Frontend mặc định luôn gọi backend ở `127.0.0.1:8000`, nên nếu đổi cổng cần cấu hình `VITE_API_BASE`.
- Script npm cho đóng gói backend đang thuận tiện nhất trên Windows.

## Troubleshooting

### 1. Frontend mở lên nhưng không gọi được backend

Kiểm tra:

- backend có đang chạy ở `127.0.0.1:8000` không
- hoặc sidecar có được đóng gói và copy đúng vào `frontend/src-tauri/` không

### 2. Chat báo thiếu API key

Nguyên nhân:

- chưa cấu hình `GOOGLE_API_KEY`

Khắc phục:

- vào `Admin -> Cấu hình` để lưu key
- hoặc đặt `GOOGLE_API_KEY` trong `backend/.env`

### 3. Kết nối MySQL thất bại

Kiểm tra:

- host, port, user, password
- user có quyền truy cập từ máy hiện tại
- MySQL server đang chạy
- firewall hoặc bind-address của MySQL

### 4. Build desktop lỗi ở bước Rust/Tauri

Kiểm tra:

- Rust toolchain đã cài chưa
- các system dependency của Tauri đã đủ chưa
- backend sidecar đã package thành công chưa

## Hướng mở rộng đề xuất

- chuẩn hóa test và CI test
- đồng bộ lại `.env.example` với code hiện tại
- bổ sung tài liệu API chi tiết hơn cho từng payload
- hỗ trợ thêm PostgreSQL hoặc SQL Server nếu thực sự cần
- chuẩn hóa script dev/build đa nền tảng
- thêm migration cho SQLite metadata/session

## License

Chưa có file license riêng trong repo hiện tại. Nếu project sẽ public hoặc phát hành thương mại, nên bổ sung `LICENSE` rõ ràng.
