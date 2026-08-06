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

from app.db.base import Base, TimestampMixin

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

    # Không truyền name= cho UniqueConstraint và Index: để NAMING_CONVENTION ở
    # db/base.py tự sinh tên (uq_classes_class_name_academic_year...). Đặt tên tay
    # thì SQLAlchemy dùng nguyên tên đó, bỏ qua convention, và schema sẽ có hai
    # kiểu đặt tên lẫn lộn.
    __table_args__ = (
        # Tên 10A1 lặp lại mỗi năm là hợp lệ; trùng trong cùng một năm thì không.
        UniqueConstraint("class_name", "academic_year"),
        # "Một giáo viên chủ nhiệm tối đa một lớp" là ràng buộc TRONG MỘT NĂM HỌC.
        # Bỏ academic_year ra khỏi ràng buộc này là hỏng: giáo viên đã chủ nhiệm
        # 10A1 năm nay sẽ vĩnh viễn không chủ nhiệm được lớp nào ở các năm sau.
        # Cột homeroom_teacher_id nullable nên Postgres coi các NULL là khác nhau
        # — nhiều lớp chưa phân công chủ nhiệm vẫn cùng tồn tại được.
        UniqueConstraint("homeroom_teacher_id", "academic_year"),
    )

    homeroom_teacher: Mapped["TeacherProfile | None"] = relationship(
        back_populates="homeroom_classes"
    )
    students: Mapped[list["ClassStudent"]] = relationship(
        back_populates="school_class", cascade="all, delete-orphan"
    )
    courses: Mapped[list["Course"]] = relationship(
        back_populates="school_class", cascade="all, delete-orphan"
    )

    # Không có thuộc tính number_of_students. Sĩ số là dữ liệu dẫn xuất
    # (COUNT class_students WHERE left_at IS NULL) — repository đếm bằng SQL,
    # đừng len(self.students) vì nó nạp cả danh sách về Python chỉ để đếm, và
    # cũng đếm nhầm cả những em đã chuyển lớp.

    def __repr__(self) -> str:
        return f"<SchoolClass {self.class_name!r} {self.academic_year}>"
