"""Bảng `teacher_profiles` — dữ liệu riêng của giáo viên.

Quan hệ 1-1 với `users`, dùng luôn `user_id` làm khoá chính: một user có tối đa
một hồ sơ giáo viên, và không cần thêm một cột `id` thứ hai để định danh cùng
một con người.

Sự tồn tại của dòng trong bảng này chính là điều kiện để được phân công dạy —
`courses.teacher_id` và `classes.homeroom_teacher_id` đều trỏ về đây chứ không
trỏ về `users.id`, nên Postgres tự chặn việc xếp một học sinh đi dạy.
"""

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.course import Course
    from app.models.school_class import SchoolClass
    from app.models.user import User

class TeacherProfile(Base, TimestampMixin):
    __tablename__ = "teacher_profiles"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
        unique=True,
        comment="Vừa là khoá chính vừa là khoá ngoại — quan hệ 1-1 với users",
    )

    address: Mapped[str | None] = mapped_column(String(255))

    phone: Mapped[str | None] = mapped_column(String(20))

    specialization: Mapped[str | None] = mapped_column(
        String(255),
        comment="Bộ môn chính, ví dụ Toán"
    )

    office: Mapped[str] = mapped_column(String(255))

    # ORM relationship với User. Không dùng `uselist=False` vì SQLAlchemy tự nhận ra
    # quan hệ 1-1 dựa trên khoá chính user_id.
    user: Mapped["User"] = relationship(back_populates="teacher_profile")

    # Danh sách chứ không phải một: Một giáo viên chủ nhiệm có thể
    # chủ nhiệm nhiều lớp qua nhiều năm. Giới hạn "tối đa một lớp" chỉ áp dụng TRONG
    # MỘT NĂM HỌC, do unique (homeroom_teacher_id, academic_year) đảm nhiệm.
    homeroom_classes: Mapped[list["SchoolClass"]] = relationship(
        back_populates="homeroom_teacher"
    )

    courses: Mapped[list["Course"]] = relationship(back_populates="teacher")

    def __repr__(self) -> str:
        return f"<TeacherProfile user_id={self.user_id}>"
