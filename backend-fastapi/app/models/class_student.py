"""Bảng `class_students` — danh sách học sinh của một lớp.

NGUỒN SỰ THẬT DUY NHẤT về "ai học lớp này". Danh sách gắn vào LỚP, không gắn vào
từng môn: lớp 10A1 có 40 học sinh thì cả 12 môn đều là đúng 40 em đó. Ghi danh
theo từng môn sẽ lặp lại 12 lần cùng một danh sách, và chỉ cần quên một dòng là
học sinh mất quyền vào một môn.

Học sinh của một `Course` = học sinh của `course.class_id` trong bảng này.
"""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Index, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.school_class import SchoolClass
    from app.models.student_profile import StudentProfile

class ClassStudent(Base, TimestampMixin):
    __tablename__ = "class_students"

    # Khoá chính ghép — chặn ghi danh trùng ở tầng DB, không cần cột id thừa.
    class_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("classes.id", ondelete="CASCADE"),
        primary_key=True,
    )
    
    student_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("student_profiles.id", ondelete="CASCADE"),
        primary_key=True,
    )

    enrolled_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        comment="Ngày được xếp vào lớp",
    )
    
    left_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        comment="NULL = đang học. Có giá trị = đã chuyển lớp hoặc thôi học",
    )

    # name=None để NAMING_CONVENTION tự sinh (ix_class_students_student_id).
    __table_args__ = (Index(None, "student_id"),)

    # Không có cột `status`. Đang học = `left_at IS NULL`. Status suy ra được từ
    # left_at, thêm vào là tự tạo ra hai nguồn sự thật cho cùng một câu hỏi.
    #
    # Học sinh rời lớp = ghi left_at, KHÔNG xoá dòng: bài nộp và điểm phải được
    # giữ lại để còn đối chiếu và thống kê về sau.
    #
    # Quy tắc "một học sinh chỉ thuộc một lớp đang hoạt động trong mỗi năm học"
    # KHÔNG đặt được bằng UniqueConstraint ở đây, vì academic_year nằm ở bảng
    # classes chứ không nằm ở bảng này. Phải kiểm ở service khi xếp lớp.

    school_class: Mapped["SchoolClass"] = relationship(back_populates="students")
    student: Mapped["StudentProfile"] = relationship(back_populates="class_memberships")

    @property
    def is_active(self) -> bool:
        """Còn đang học lớp này hay không."""
        return self.left_at is None

    def __repr__(self) -> str:
        state = "active" if self.left_at is None else f"left at {self.left_at}"
        return f"<ClassStudent class={self.class_id} student={self.student_id} ({state})>"
