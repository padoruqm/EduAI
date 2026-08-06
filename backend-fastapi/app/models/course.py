"""Bảng `courses` — lớp học phần: "lớp 10A1 học môn Toán học kỳ 1, thầy Nam dạy".

Đây là đơn vị dạy học, và là thứ mà mọi module AI treo vào: `documents`,
`quizzes`, `chat_sessions`, `analytics_snapshots` của M3..M9 đều có khoá ngoại
`course_id` trỏ về bảng này.

Học sinh của một lớp học phần KHÔNG có bảng riêng — đó chính là `class_students`
của `course.class_id`. Lớp có sĩ số cố định, học môn nào cũng là nhóm học sinh đó.
"""

import enum
import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Enum, ForeignKey, Index, Text, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.school_class import SchoolClass
    from app.models.subject import Subject
    from app.models.teacher_profile import TeacherProfile


class Term(str, enum.Enum):
    """Học kỳ mà lớp học phần này chạy."""

    HK1 = "hk1"
    HK2 = "hk2"
    CA_NAM = "ca_nam"  # môn dạy suốt năm, không chia học kỳ


class CourseStatus(str, enum.Enum):
    ACTIVE = "active"
    ARCHIVED = "archived"  # hết học kỳ: ẩn khỏi danh sách chính, giữ nguyên dữ liệu


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
        # Trỏ về teacher_profiles chứ không phải users: Postgres tự chặn việc
        # phân công một học sinh đi dạy. RESTRICT còn chặn luôn việc hạ role một
        # giáo viên đang có lớp — hạ role phải xoá teacher_profiles, và thao tác
        # đó vướng khoá ngoại này. Ràng buộc nghiệp vụ được thực thi miễn phí ở
        # tầng DB thay vì trông chờ service nhớ kiểm tra.
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

    __table_args__ = (
        # Một lớp không có hai giáo viên cùng dạy một môn trong cùng học kỳ.
        UniqueConstraint("class_id", "subject_id", "term"),
        # Danh sách lớp một giáo viên đang dạy (UC-CRS-02).
        Index(None, "teacher_id", "status"),
        Index(None, "class_id"),
    )

    # Không có cột academic_year: suy ra từ school_class.academic_year. Lưu ở hai
    # nơi là sẽ có ngày lệch nhau, và lúc đó không biết bên nào đúng.
    #
    # Không có cột name: tên hiển thị "Toán 10A1 HK1" ghép từ subject.name +
    # school_class.class_name + term ở tầng schema (CourseOut), không lưu xuống DB.

    school_class: Mapped["SchoolClass"] = relationship(back_populates="courses")
    subject: Mapped["Subject"] = relationship(back_populates="courses")
    teacher: Mapped["TeacherProfile"] = relationship(back_populates="courses")

    def __repr__(self) -> str:
        return f"<Course class={self.class_id} subject={self.subject_id} {self.term.value}>"
