import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, CheckConstraint, DateTime, Enum, Index, String, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, TimestampMixin
from app.constants.index import Role

if TYPE_CHECKING:
    from app.models.student_profile import StudentProfile
    from app.models.teacher_profile import TeacherProfile

class User(Base, TimestampMixin):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        # gen_random_uuid() đến từ extension pgcrypto, đã bật sẵn ở
        # database/init/01_extensions.sql.
        server_default=text("gen_random_uuid()"),
    )

    # --- Định danh & hồ sơ ---------------------------------------------------
    email: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        unique=True,
        # index=True là thừa: unique=True đã tự tạo index rồi.
        # Email là thứ tra cứu ở MỌI lần đăng nhập nên bắt buộc phải có index.
        comment="Luôn lưu chữ thường — chuẩn hoá ở service trước khi ghi (BR-AUTH-01)",
    )
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    avatar_url: Mapped[str | None] = mapped_column(String(512), nullable=True)

    role: Mapped[Role] = mapped_column(
        Enum(
            Role,
            name="user_role",
            # Mặc định SQLAlchemy lưu TÊN của member ("ADMIN"), không phải giá trị.
            # values_callable ép nó lưu đúng "admin" như trong ERD và trong JWT.
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
        ),
        nullable=False,
        default=Role.STUDENT,
        server_default=Role.STUDENT.value,
        comment="Đăng ký tự do luôn ra student; chỉ Admin đổi được (BR-AUTH-06)",
    )

    # --- Phương thức đăng nhập -----------------------------------------------
    hashed_password: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        comment="NULL khi user chỉ đăng nhập bằng Google (BR-AUTH-07)",
    )
    google_id: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        unique=True,
        comment="Trường 'sub' của Google. NULL = chưa liên kết (FR-AUTH-05/06)",
    )

    # --- Trạng thái ----------------------------------------------------------
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default=text("true"),
        comment="false = bị Admin khoá, không đăng nhập được (FR-AUTH-11)",
    )
    last_login_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Hiển thị ở màn Admin quản lý người dùng (UC-CRS-11)",
    )

    teacher_profile: Mapped["TeacherProfile | None"] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    student_profile: Mapped["StudentProfile | None"] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )

    __table_args__ = (
        # Chỉ giữ lại Index hỗ trợ trang Admin lọc cho nhanh
        Index(None, "role", "is_active"),
        CheckConstraint(
        "hashed_password IS NOT NULL OR google_id IS NOT NULL",
        name="has_login_method",
        )
    )

    def __repr__(self) -> str:
        # Không bao giờ đưa hashed_password vào repr — repr xuất hiện trong log
        # và trong trace của Sentry.
        return f"<User id={self.id} email={self.email!r} role={self.role.value}>"
