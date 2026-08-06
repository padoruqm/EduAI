"""Bảng `subjects` — danh mục môn học (Toán, Lý, Hoá...).

Khoá chính là uuid giống mọi bảng khác; mã môn nằm ở cột `code` có unique. Dùng
mã môn làm khoá chính thì đổi mã sẽ kéo theo phải sửa mọi khoá ngoại trỏ tới.
"""

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import String, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.course import Course


class Subject(Base, TimestampMixin):
    __tablename__ = "subjects"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )

    code: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        unique=True,
        comment="Mã ngắn, ví dụ TOAN — dùng để hiển thị và import danh sách",
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)

    courses: Mapped[list["Course"]] = relationship(back_populates="subject")

    def __repr__(self) -> str:
        return f"<Subject {self.code} {self.name!r}>"
