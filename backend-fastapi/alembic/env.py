import logging
from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool
from alembic import context

# 1. Nạp config từ alembic.ini
config = context.config

if config.config_file_name:
    fileConfig(config.config_file_name)

logger = logging.getLogger("alembic.env")

# 2. Nạp URL từ .env
from app.core.config.database import db_settings

config.set_main_option(
    "sqlalchemy.url",
    db_settings.database_url_sync.replace("%", "%%"),
)

# 3. Nạp toàn bộ metadata
import app.models
from app.database.base import Base

target_metadata = Base.metadata


# 4. Định nghĩa các Callback Functions (Phải định nghĩa TRƯỚC khi dùng)
def include_object(obj, name, type_, reflected, compare_to):
    """Trả về False = Alembic coi như không thấy đối tượng này."""
    # Lọc các bảng do extension tạo ra (ví dụ PostGIS spatial_ref_sys)
    if type_ == "table" and name in {"spatial_ref_sys"}:
        return False
    return True


def process_revision_directives(context_, revision, directives):
    """Chặn tạo file migration rỗng khi dùng --autogenerate."""
    if getattr(config.cmd_opts, "autogenerate", False):
        if directives[0].upgrade_ops.is_empty():
            directives[:] = []
            logger.info("Không có thay đổi nào so với DB — bỏ qua, không tạo file rỗng.")


# 5. Các cấu hình so sánh chung
COMMON_CONFIGURE_OPTS = {
    "target_metadata": target_metadata,
    "compare_type": True,             # Phát hiện đổi kiểu cột: String(100) -> String(255)
    "compare_server_default": True,   # Phát hiện đổi server_default
    "include_object": include_object,
    "process_revision_directives": process_revision_directives,
}


# 6. Định nghĩa 2 chế độ chạy
def run_migrations_offline() -> None:
    """Không kết nối DB, chỉ xuất ra SQL: alembic upgrade head --sql > migration.sql"""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        **COMMON_CONFIGURE_OPTS,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Kết nối trực tiếp vào DB để thực thi migration."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,  # Giải phóng kết nối ngay sau khi hoàn thành
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            **COMMON_CONFIGURE_OPTS,
        )

        with context.begin_transaction():
            context.run_migrations()


# 7. Điều hướng luồng thực thi
if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()