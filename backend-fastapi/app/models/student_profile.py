"""Bảng `student_profiles` — dữ liệu riêng của học sinh.

Quan hệ 1-1 với `users`, `user_id` làm khoá chính (xem lý do ở
`teacher_profile.py`).

KHÔNG có cột `class_id`. Học sinh thuộc lớp nào là việc của bảng
`class_students`: thông tin đó thay đổi theo từng năm học và phải giữ được lịch
sử. Một cột `class_id` chỉ lưu được lớp HIỆN TẠI — sang năm cập nhật sang lớp
mới là danh sách lớp năm cũ rỗng, kéo theo không tra được điểm và bài nộp của
năm học trước.
"""

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.class_student import ClassStudent
    from app.models.user import User

class StudentProfile(Base, TimestampMixin):
    __tablename__ = "student_profiles"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default="gen_random_uuid()",
        unique=True,
        comment="Id học sinh từng lớp"
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        comment="Vừa là khoá chính vừa là khoá ngoại — quan hệ 1-1 với users"
    )

    user: Mapped["User"] = relationship(back_populates="student_profile")

    class_memberships: Mapped[list["ClassStudent"]] = relationship(
        back_populates="student"
    )

    def __repr__(self) -> str:
        return f"<StudentProfile user_id={self.user_id} class_id={self.class_id}>"
