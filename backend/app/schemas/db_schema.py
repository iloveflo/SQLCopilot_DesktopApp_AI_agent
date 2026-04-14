from pydantic import BaseModel, Field
from typing import List

class ColumnSchema(BaseModel):
    """Định nghĩa cấu trúc của một cột trong CSDL."""
    name: str = Field(..., description="Tên cột")
    type: str = Field(..., description="Kiểu dữ liệu (VD: VARCHAR(255), INT)")
    nullable: bool = Field(..., description="Cho phép giá trị NULL hay không")
    comment: str = Field(None, description="Mô tả/Ghi chú của cột từ Database")

class ForeignKeySchema(BaseModel):
    """Định nghĩa cấu trúc của khóa ngoại để LLM biết cách JOIN."""
    constrained_columns: List[str] = Field(..., description="Cột chứa khóa ngoại ở bảng hiện tại")
    referred_table: str = Field(..., description="Tên bảng được tham chiếu tới")
    referred_columns: List[str] = Field(..., description="Tên cột được tham chiếu tới ở bảng đích")

class TableSchema(BaseModel):
    """Định nghĩa toàn bộ cấu trúc của một bảng."""
    table_name: str = Field(..., description="Tên bảng")
    db_name: str = Field(None, description="Tên Database chứa bảng này")
    columns: List[ColumnSchema] = Field(default_factory=list, description="Danh sách các cột")
    primary_keys: List[str] = Field(default_factory=list, description="Danh sách các Primary Keys")
    foreign_keys: List[ForeignKeySchema] = Field(default_factory=list, description="Danh sách các Foreign Keys")

class DatabaseSchemaResponse(BaseModel):
    """Schema tổng bọc toàn bộ cơ sở dữ liệu."""
    tables: List[TableSchema] = Field(default_factory=list, description="Danh sách toàn bộ các bảng trong DB")
    
    def to_llm_context(self) -> str:
        """
        Utility function: Tự động parse schema Pydantic này thành chuỗi String tinh gọn 
        để bơm vào Prompt của Agent 2 (NL2SQL).
        """
        context = []
        for table in self.tables:
            context.append(f"Table: {table.table_name}")
            
            # Liệt kê cột và đánh dấu PK
            cols = []
            for col in table.columns:
                pk_flag = "[PK] " if col.name in table.primary_keys else ""
                cols.append(f"  - {pk_flag}{col.name} ({col.type})")
            context.append("\n".join(cols))
            
            # Liệt kê khóa ngoại
            if table.foreign_keys:
                context.append("  Relationships:")
                for fk in table.foreign_keys:
                    context.append(
                        f"    - {','.join(fk.constrained_columns)} -> "
                        f"{fk.referred_table}({','.join(fk.referred_columns)})"
                    )
            context.append("\n")
            
        return "\n".join(context)