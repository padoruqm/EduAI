"""Lớp Base của SQLAlchemy — mọi model trong `app/models/` đều kế thừa từ đây.

File này KHÔNG chứa bảng nào cả, chỉ chứa:
  - `Base`: DeclarativeBase mang sẵn quy ước đặt tên ràng buộc
  - `TimestampMixin`: hai cột `created_at` / `updated_at` dùng lại ở mọi bảng
"""

from datetime import datetime

from sqlalchemy import DateTime, MetaData, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

# Quy ước đặt tên ràng buộc.
#
# Postgres tự đặt tên cho index / unique / foreign key nếu mình không đặt, và
# tên nó sinh ra không đoán trước được. Hậu quả: `alembic revision --autogenerate`
# sẽ thấy tên trong DB khác tên trong model rồi sinh ra migration drop/create
# vô nghĩa, còn muốn viết `op.drop_constraint(...)` thì không biết truyền tên gì.
#
# Khai báo convention NGAY TỪ ĐẦU (trước migration đầu tiên) để mọi ràng buộc
# đều có tên xác định. Thêm sau khi DB đã có dữ liệu thì phải đi đổi tên thủ công.
NAMING_CONVENTION = {
    "ix": "ix_%(table_name)s_%(column_0_N_name)s",
    "uq": "uq_%(table_name)s_%(column_0_N_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}

# Lớp cha cho các model ORM
class Base(DeclarativeBase):
    """Base chung. Alembic đọc `Base.metadata` để so sánh model với DB thật."""
    metadata = MetaData(naming_convention=NAMING_CONVENTION)

class TimestampMixin:
    """Hai cột thời gian mà bảng nào cũng cần.

    `server_default=func.now()` để mặc định do Postgres sinh — dòng thêm bằng
    SQL tay hay bằng seed script cũng có giá trị, không riêng gì qua ORM.

    `onupdate=func.now()` chỉ chạy khi UPDATE **đi qua ORM**. Chạy
    `UPDATE users SET ...` trực tiếp trong psql sẽ không cập nhật cột này; muốn
    chặt chẽ tuyệt đối thì phải viết trigger trong migration.
    """

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
