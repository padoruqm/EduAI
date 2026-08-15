"""Bảng `courses` — lớp học phần: "lớp 10A1 học môn Toán học kỳ 1, thầy Nam dạy".

Đây là đơn vị dạy học, và là thứ mà mọi module AI treo vào: `documents`,
`quizzes`, `chat_sessions`, `analytics_snapshots` của M3..M9 đều có khoá ngoại
`course_id` trỏ về bảng này.

Học sinh của một lớp học phần KHÔNG có bảng riêng — đó chính là `class_students`
của `course.class_id`. Lớp có sĩ số cố định, học môn nào cũng là nhóm học sinh đó.
"""
import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Enum, ForeignKey, Index, Text, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin
from app.constants.index import CourseStatus, Term

if TYPE_CHECKING:
    from app.models.school_class import SchoolClass
    from app.models.subject import Subject
    from app.models.teacher_profile import TeacherProfile

class Course(Base, TimestampMixin):
    __tablename__ = "courses"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )

    class_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("classes.id", ondelete="CASCADE"),
        nullable=False,
        comment="Lớp nào học",
    )
    subject_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        # RESTRICT: còn lớp đang dạy môn này thì không xoá được môn học.
        ForeignKey("subjects.id", ondelete="RESTRICT"),
        nullable=False,
        comment="Môn gì",
    )
    teacher_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("teacher_profiles.user_id", ondelete="RESTRICT"),
        nullable=False,
        comment="Ai dạy — đúng một giáo viên (BR-CRS-01)",
    )

    term: Mapped[Term] = mapped_column(
        Enum(
            Term,
            name="term",
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
        ),
        nullable=False,
        default=Term.CA_NAM,
        server_default=Term.CA_NAM.value,
    )
    description: Mapped[str | None] = mapped_column(Text)
    status: Mapped[CourseStatus] = mapped_column(
        Enum(
            CourseStatus,
            name="course_status",
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
        ),
        nullable=False,
        default=CourseStatus.ACTIVE,
        server_default=CourseStatus.ACTIVE.value,
    )

    school_class: Mapped[list["SchoolClass"]] = relationship(back_populates="courses")
    subject: Mapped["Subject"] = relationship(back_populates="courses")
    teacher: Mapped["TeacherProfile"] = relationship(back_populates="courses")

    def __repr__(self) -> str:
        return f"<Course class={self.class_id} subject={self.subject_id} {self.term.value}>"
