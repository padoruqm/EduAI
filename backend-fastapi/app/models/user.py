import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, CheckConstraint, DateTime, Enum, Index, String, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin
from app.constants import Role

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

    __table_args__ = (
        # Chốt chặn ở tầng DB cho BR-AUTH-01. Service vẫn phải tự .lower(), nhưng
        # nếu có chỗ nào quên thì INSERT sẽ nổ ngay thay vì lặng lẽ tạo ra hai tài
        # khoản "An@gmail.com" và "an@gmail.com" trỏ về cùng một người.
        CheckConstraint("email = lower(email)", name="email_lowercase"),
        # Không cho tồn tại tài khoản không còn lối vào nào: gỡ liên kết Google
        # khi chưa đặt mật khẩu sẽ bị chặn tại đây (BR-AUTH-12).
        CheckConstraint(
            "hashed_password IS NOT NULL OR google_id IS NOT NULL",
            name="has_login_method",
        ),
        # Màn hình Admin lọc theo role + trạng thái (UC-CRS-11).
        Index(None, "role", "is_active"),
        # Tìm kiếm bỏ dấu (BR-CRS-13) cần index trên biểu thức unaccent(full_name).
        # unaccent() không IMMUTABLE nên Postgres từ chối đưa vào index; phải bọc
        # bằng một hàm wrapper IMMUTABLE, viết thẳng op.execute(...) trong migration.
    )

    # Hồ sơ riêng theo vai trò, quan hệ 1-1. Kiểu `X | None` nói cho SQLAlchemy
    # biết đây là quan hệ một-một (không phải danh sách) — không cần uselist=False.
    #
    # Một user chỉ có hồ sơ ứng với role của mình: role=teacher thì có
    # teacher_profile, role=student thì có student_profile, role=admin thì không
    # có hồ sơ nào. DB không tự ép được điều này, service phải tạo và xoá hồ sơ
    # khi Admin đổi role (UC-CRS-13).
    teacher_profile: Mapped["TeacherProfile | None"] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    student_profile: Mapped["StudentProfile | None"] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        # Không bao giờ đưa hashed_password vào repr — repr xuất hiện trong log
        # và trong trace của Sentry.
        return f"<User id={self.id} email={self.email!r} role={self.role.value}>"
