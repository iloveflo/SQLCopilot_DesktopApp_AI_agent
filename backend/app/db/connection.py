import logging
from sqlalchemy import create_engine, text, inspect
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import SQLAlchemyError
from urllib.parse import quote_plus
from app.core.config import settings

logger = logging.getLogger(__name__)

class ConnectionManager:
    def __init__(self):
        self.engine = None
        self.SessionLocal = None
        self.current_db = None
        self.current_user = None
        self.current_password = None
        self.current_host = None
        self.current_port = None
        self.selected_databases: list[str] = []  # Danh sách DB đang được chọn để phân tích

    @property
    def is_admin(self) -> bool:
        """Trả về True nếu đang kết nối bằng tài khoản root hoặc có quyền super."""
        if not self.current_user:
            return False
        # Root luôn là admin
        if self.current_user.lower() == "root":
            return True
        # Kiểm tra quyền CREATE USER qua SHOW GRANTS
        try:
            from sqlalchemy import text
            with self.engine.connect() as conn:
                result = conn.execute(text("SHOW GRANTS FOR CURRENT_USER()"))
                grants = " ".join([str(row[0]) for row in result.fetchall()]).upper()
                return "ALL PRIVILEGES" in grants or "CREATE USER" in grants or "SUPER" in grants
        except Exception:
            return False
        
        # Thử kết nối mặc định nếu có trong .env (Cho dev nhanh)
        if settings.LOCAL_DB_URL:
            try:
                self.engine = create_engine(
                    settings.LOCAL_DB_URL,
                    pool_pre_ping=True,
                    pool_size=5,
                    max_overflow=10,
                    echo=False
                )
                self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
                # Parse DB name từ URL cho vào current_db
                db_name = self.engine.url.database or ""
                self.current_db = db_name
            except Exception as e:
                logger.warning(f"Không thể khởi tạo engine mặc định: {e}")

    def connect(self, host: str, port: int, user: str, password: str, database: str = "") -> bool:
        """Tạo kết nối mới hoàn toàn tới server."""
        try:
            pwd = quote_plus(password)
            url = f"mysql+pymysql://{user}:{pwd}@{host}:{port}/{database}"
            new_engine = create_engine(
                url,
                pool_pre_ping=True,
                pool_size=5,
                max_overflow=10,
                echo=False
            )
            # Test kết nối ngay
            with new_engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            
            # Nếu thành công, áp dụng vào Instance
            if self.engine:
                self.engine.dispose()
                
            self.engine = new_engine
            self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
            self.current_db = database
            self.current_user = user
            self.current_password = password
            self.current_host = host
            self.current_port = port
            
            return True
        except Exception as e:
            logger.error(f"Lỗi khởi tạo Database Engine: {e}")
            raise e
            
    def use_database(self, database: str) -> bool:
        """Đổi database trên kết nối hiện đang dùng."""
        if not self.current_user or not self.current_host:
            raise Exception("Chưa có kết nối nào đến Server. Vui lòng login trước.")
        return self.connect(
            host=self.current_host, 
            port=self.current_port, 
            user=self.current_user, 
            password=self.current_password, 
            database=database
        )

    def get_databases(self) -> list[str]:
        """Lấy danh sách databases từ server hiện tại."""
        if not self.engine:
            raise Exception("Chưa kết nối tới cơ sở dữ liệu.")
        try:
            inspector = inspect(self.engine)
            return inspector.get_schema_names()
        except Exception as e:
            logger.error(f"Lỗi khi lấy danh sách Schema: {e}")
            raise e

    def ping(self) -> dict:
        if not self.engine:
            return {"status": "error", "message": "Chưa có kết nối nào được thiết lập."}
        try:
            with self.engine.connect() as connection:
                connection.execute(text("SELECT 1"))
            db_info = f" (Database: {self.current_db})" if self.current_db else " (Root Server)"
            return {"status": "success", "message": f"Kết nối Cơ sở dữ liệu thành công{db_info}."}
        except SQLAlchemyError as e:
            logger.error(f"Ping DB thất bại: {e}")
            return {"status": "error", "message": f"Lỗi kết nối CSDL: {str(e)}"}

    def disconnect(self) -> bool:
        """Ngắt kết nối hoàn toàn khỏi hệ thống để đăng xuất."""
        try:
            if self.engine:
                self.engine.dispose()
            self.engine = None
            self.SessionLocal = None
            self.current_db = None
            self.current_user = None
            self.current_password = None
            self.current_host = None
            self.current_port = None
            self.selected_databases = []
            return True
        except Exception as e:
            logger.error(f"Lỗi khi ngắt kết nối: {e}")
            raise e

    def set_active_databases(self, db_list: list[str]) -> None:
        """Cài đặt danh sách DB đang được chọn để phân tích (Single hoặc Multi)."""
        if not self.engine:
            raise Exception("Chưa có kết nối nào đến Server. Vui lòng đăng nhập trước.")
        # Xác thực rằng các DB này tồn tại
        available = self.get_databases()
        invalid = [db for db in db_list if db not in available]
        if invalid:
            raise Exception(f"Các CSDL không tồn tại trên server: {invalid}")
        self.selected_databases = db_list

    def get_active_databases(self) -> list[str]:
        """Trả về danh sách DB đang được chọn. Fallback về current_db nếu chưa chọn."""
        if self.selected_databases:
            return self.selected_databases
        if self.current_db:
            return [self.current_db]
        return []

    def get_user_identifier(self) -> str:
        """Trả về định danh duy nhất của người dùng hiện tại: user@host."""
        if not self.current_user:
            return "guest_user"
        host = self.current_host or "localhost"
        return f"{self.current_user}@{host}"

connection_manager = ConnectionManager()