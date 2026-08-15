"""Bảng `classes` — lớp chính quy (10A1, 11B2...).

Tên file là `school_class.py` chứ không phải `class.py`: `class` là từ khoá
Python, `from app.models.class import ...` là lỗi cú pháp. Tên class Python là
`SchoolClass` cho khớp tên file, còn tên bảng vẫn là `classes` theo quy ước
"bảng DB số nhiều".

Mỗi dòng là một lớp CỦA MỘT NĂM HỌC cụ thể. Lớp 10A1 năm 2025-2026 và lớp 11A1
năm 2026-2027 là hai dòng khác nhau, kể cả khi cùng một nhóm học sinh. Nhờ vậy
danh sách lớp cũ không bao giờ bị ghi đè khi học sinh lên lớp.
"""

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, String, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.class_student import ClassStudent
    from app.models.course import Course
    from app.models.teacher_profile import TeacherProfile

class SchoolClass(Base, TimestampMixin):
    __tablename__ = "classes"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )

    class_name: Mapped[str] = mapped_column(String(100), nullable=False, comment="Ví dụ 10A1")

    academic_year: Mapped[str] = mapped_column(
        String(9), nullable=False, comment="Dạng 2025-2026"
    )

    homeroom_teacher_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("teacher_profiles.user_id", ondelete="SET NULL"),
        comment="Giáo viên chủ nhiệm. NULL khi chưa phân công",
    )

    __table_args__ = (
        # Không thể có hai lớp 10A1 trong cùng một năm học.
        UniqueConstraint("class_name", "academic_year"),
        # Một giáo viên chủ nhiệm tối đa một lớp mỗi năm học. Postgres coi mọi
        # NULL là khác nhau, nên nhiều lớp chưa phân công GVCN vẫn hợp lệ.
        UniqueConstraint("homeroom_teacher_id", "academic_year"),
    )

    homeroom_teacher: Mapped["TeacherProfile | None"] = relationship(
        back_populates="homeroom_classes"
    )
    # ORM relationship với ClassStudent và Course. Cascade "all, delete-orphan" để
    # khi xoá lớp thì xoá luôn các dòng liên quan trong hai bảng kia.
    # Một lớp thì có nhiều học sinh và nhiều môn học, nhưng một học sinh chỉ thuộc một lớp
    students: Mapped[list["ClassStudent"]] = relationship(
        back_populates="school_class", cascade="all, delete-orphan"
    )
    courses: Mapped[list["Course"]] = relationship(
        back_populates="school_class", cascade="all, delete-orphan"
    )


    def __repr__(self) -> str:
        return f"<SchoolClass {self.class_name!r} {self.academic_year}>"
