from pydantic import BaseModel, Field
from typing import Optional, List

class ConnectRequest(BaseModel):
    host: str = Field(default="localhost")
    port: int = Field(default=3306)
    user: str = Field(...)
    password: str = Field(...)
    database: Optional[str] = Field(default="")

class UseDatabaseRequest(BaseModel):
    database: str = Field(...)

class SelectDatabasesRequest(BaseModel):
    databases: List[str] = Field(..., min_length=1, description="Danh sách tên các Database muốn phân tích cùng lúc. Bắt buộc ít nhất 1 DB.")
