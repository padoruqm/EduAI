# Quy trình viết Migration (Alembic)

Tài liệu này trả lời đúng một câu hỏi: **ERD và models đã viết xong rồi, giờ làm gì để có bảng thật dưới PostgreSQL?**

Đọc kèm: [`ARCHITECTURE.md`](ARCHITECTURE.md) (cây thư mục), [`database/erd/schema.dbml`](../database/erd/schema.dbml) (sơ đồ).

---

## 0. Nguyên tắc bất biến

Luồng thay đổi schema chỉ đi **một chiều**, không bao giờ đi ngược:

```
database/erd/schema.dbml  →  app/models/*.py  →  alembic/versions/*.py  →  PostgreSQL
      (để vẽ, bàn bạc)        (khai báo bảng)      (lệnh đổi schema)        (dữ liệu thật)
```

| Câu hỏi | Trả lời |
|---|---|
| Nguồn sự thật của schema là gì? | `alembic/versions/` — chuỗi migration. Chạy hết từ đầu là ra đúng DB hiện tại |
| Còn `schema.dbml`? | Chỉ để **vẽ và thảo luận**. Nó không sinh ra bảng, và không phải mọi ràng buộc đều vẽ được (CHECK, partial index) |
| Còn `app/models/`? | Là **mô tả mong muốn**. Alembic so sánh models với DB thật để sinh lệnh chênh lệch |

> **Ba điều cấm.** Vi phạm là schema thật và migration lệch nhau, sau đó mọi lần `--autogenerate` đều sinh ra rác:
>
> 1. **Không** gõ `ALTER TABLE` / `CREATE TABLE` thẳng vào psql hay DBeaver. Đổi gì cũng phải qua migration (NFR-O-02).
> 2. **Không** viết `CREATE TABLE` vào [`database/init/`](../database/init/). Thư mục đó chỉ dành cho extension, và chỉ chạy đúng một lần lúc volume postgres còn rỗng.
> 3. **Không** sửa file migration **đã push lên remote**. Người khác đã chạy nó rồi. Muốn đổi thì viết migration mới.

---

# PHẦN A — Setup một lần

Hiện tại hạ tầng Alembic của repo **chưa chạy được**. Bảng dưới là trạng thái thật và việc phải làm:

| File | Trạng thái | Việc |
|---|---|---|
| `backend-fastapi/requirements.txt` | chưa có | tạo mới (§A.1) |
| `backend-fastapi/.env` | chưa có (mới chỉ có `.env.example`) | copy + điền mật khẩu (§A.2) |
| `app/**/__init__.py` | chỉ `app/models/` có | tạo cho các package còn thiếu (§A.3) |
| `app/core/config/database.py` | **có file nhưng rỗng 0 byte** | viết `DatabaseSettings` (§A.4) |
| `backend-fastapi/alembic.ini` | chưa có | tạo mới (§A.5) |
| `alembic/script.py.mako` | chưa có | tạo mới — thiếu file này thì `alembic revision` báo lỗi (§A.6) |
| `alembic/env.py` | **có file nhưng rỗng 0 byte** | file quan trọng nhất (§A.7) |
| `alembic/versions/` | rỗng | sẽ có file sau Phần B |

### Mẹo: lấy file mẫu từ chính Alembic

`alembic init` không ghi đè lên thư mục `alembic/` đã tồn tại, nên sinh ra chỗ tạm rồi bê file sang:

```bash
cd backend-fastapi
alembic init _tmp                  # sinh ./alembic.ini và ./_tmp/{env.py,script.py.mako,versions/}
cp _tmp/script.py.mako alembic/    # lấy nguyên file này
rm -rf _tmp                        # env.py và alembic.ini thì tự sửa theo §A.5, §A.7
```

---

## A.1 — `backend-fastapi/requirements.txt`

Repo hiện chưa khai báo dependency ở đâu cả. Tạo file này trước, nếu không mọi lệnh `alembic` đều `command not found`.

```
# --- Core ---
fastapi
uvicorn[standard]
pydantic
pydantic-settings

# --- Database ---
sqlalchemy[asyncio]>=2.0
alembic>=1.13
asyncpg                 # driver BẤT ĐỒNG BỘ  -> app chạy runtime dùng
psycopg[binary]>=3.1    # driver ĐỒNG BỘ      -> Alembic dùng
pgvector                # cột Vector(1536) của M3, khai báo sẵn
tzdata                  # cần khi alembic.ini bật timezone, image python slim không có sẵn
```

> **`psycopg` (v3) khác `psycopg2`.** Chuỗi kết nối phải là `postgresql+psycopg://`. Nếu copy nhầm hướng dẫn cũ trên mạng thành `postgresql+psycopg2://` mà lại cài `psycopg[binary]` thì Alembic báo `ModuleNotFoundError: No module named 'psycopg2'`.

Vì sao cài **cả hai** driver: app FastAPI chạy async (`asyncpg`), còn Alembic chạy đồng bộ (`psycopg`). Hai thứ dùng chung một database nhưng không dùng chung engine.

```bash
cd backend-fastapi
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

## A.2 — `backend-fastapi/.env`

```bash
cp .env.example .env
```

Rồi điền các giá trị `CHANGE_ME`. Hai dòng Alembic quan tâm:

```ini
DATABASE_URL=postgresql+asyncpg://eduai:<mat_khau>@localhost:5432/eduai      # app dùng
DATABASE_URL_SYNC=postgresql+psycopg://eduai:<mat_khau>@localhost:5432/eduai # Alembic dùng
```

Mật khẩu phải **khớp `POSTGRES_PASSWORD`** trong file `.env` ở thư mục gốc (file mà `docker-compose.yaml` đọc). Sai mật khẩu thì lỗi ra rất muộn, ở tận bước `alembic upgrade`.

## A.3 — Các file `__init__.py` còn thiếu

Hiện chỉ `app/models/__init__.py` tồn tại. Python 3 vẫn import được nhờ namespace package, nhưng đó là may mắn chứ không phải thiết kế: chỉ cần một thư mục trùng tên nằm trên `sys.path` là import đi sai chỗ, và mypy/pytest hay báo lỗi khó hiểu.

Tạo **file rỗng** ở: `app/__init__.py`, `app/core/__init__.py`, `app/core/config/__init__.py`, `app/database/__init__.py`, `app/constants/__init__.py`.

## A.4 — `app/core/config/database.py` *(đang rỗng)*

Alembic **không tự đọc `.env`**. Nó đọc qua module này. Đây cũng là chỗ duy nhất trong code biết tới chuỗi kết nối.

Các khối cần viết:

```python
"""Cấu hình kết nối database, đọc từ .env bằng Pydantic Settings."""

from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class DatabaseSettings(BaseSettings):
    # extra="ignore": .env có ~60 biến của các module khác (JWT, S3, OpenAI...),
    # không khai báo ở đây thì Pydantic sẽ báo lỗi "extra inputs not permitted".
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str        # asyncpg — app dùng
    database_url_sync: str   # psycopg  — Alembic dùng
    db_pool_size: int = 10
    db_max_overflow: int = 20
    db_echo: bool = False


@lru_cache
def get_db_settings() -> DatabaseSettings:
    # lru_cache: đọc file .env đúng một lần cho cả tiến trình.
    return DatabaseSettings()


db_settings = get_db_settings()
```

Tên field viết thường có gạch dưới, tự khớp với biến `DATABASE_URL_SYNC` trong `.env` (Pydantic không phân biệt hoa thường).

> `env_file=".env"` là đường dẫn **tương đối theo thư mục đang đứng**. Vì vậy mọi lệnh `alembic` đều phải chạy từ `backend-fastapi/`. Muốn chạy từ đâu cũng được thì đổi thành đường dẫn tuyệt đối tính từ `__file__`.

## A.5 — `backend-fastapi/alembic.ini`

```ini
[alembic]
script_location = alembic

# Thiếu dòng này là "ModuleNotFoundError: No module named 'app'" khi env.py import model.
# Dấu chấm = thư mục backend-fastapi, nơi gõ lệnh alembic.
prepend_sys_path = .

# Tên file migration gắn timestamp -> versions/ tự sắp xếp theo thời gian khi ls.
# Chỉ có revision id thì nhìn thư mục không đoán được cái nào viết trước.
# Phải viết %% vì file .ini dùng % cho cú pháp nội suy của riêng nó.
file_template = %%(year)d%%(month).2d%%(day).2d_%%(hour).2d%%(minute).2d-%%(rev).8s_%%(slug)s

timezone = Asia/Ho_Chi_Minh

# sqlalchemy.url ĐỂ TRỐNG - CỐ Ý.
# Điền vào đây là commit mật khẩu database lên git. env.py sẽ nạp URL từ .env.
sqlalchemy.url =

[loggers]
keys = root,sqlalchemy,alembic

[handlers]
keys = console

[formatters]
keys = generic

[logger_root]
level = WARNING
handlers = console
qualname =

[logger_sqlalchemy]
level = WARNING
handlers =
qualname = sqlalchemy.engine

[logger_alembic]
level = INFO
handlers =
qualname = alembic

[handler_console]
class = StreamHandler
args = (sys.stderr,)
level = NOTSET
formatter = generic

[formatter_generic]
format = %(levelname)-5.5s [%(name)s] %(message)s
datefmt = %H:%M:%S
```

Muốn nhìn thấy đúng câu SQL Alembic gửi đi (lúc debug): đổi `logger_sqlalchemy` thành `level = INFO`.

## A.6 — `alembic/script.py.mako`

Khuôn để sinh ra mỗi file migration. Lấy bản chuẩn bằng `alembic init _tmp` (xem mẹo ở đầu Phần A), rồi thêm **một dòng import** vào phần đầu:

```mako
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql   # <- thêm: gần như migration nào cũng cần
${imports if imports else ""}
```

Các biến trong template: `${up_revision}` (id của bản này), `${down_revision}` (id bản trước — đây là thứ tạo nên chuỗi migration), `${upgrades}` / `${downgrades}` (chỗ Alembic đổ lệnh sinh tự động vào).

Tới M3, khi có cột `Vector(1536)` cho pgvector, thêm tiếp `import pgvector.sqlalchemy` vào đây — autogenerate render đúng kiểu `pgvector.sqlalchemy.Vector(dim=1536)` nhưng **không tự thêm import**, thiếu là `NameError` lúc chạy.

## A.7 — `alembic/env.py` *(đang rỗng — file quan trọng nhất)*

Đây là chỗ Alembic biết "bảng nào là mong muốn" và "database nằm ở đâu". Viết theo sáu khối:

### Khối 1 — nạp toàn bộ metadata

```python
import app.models  # noqa: F401  <- KHÔNG được xoá dù linter kêu "unused"
from app.database.base import Base

target_metadata = Base.metadata
```

Alembic chỉ nhìn thấy bảng nào đã nằm trong `Base.metadata`. Một dòng `import app.models` kéo theo cả 7 model, vì [`app/models/__init__.py`](../backend-fastapi/app/models/__init__.py) import sẵn tất cả.

> **Hệ quả nếu quên:** thêm model mới mà quên thêm dòng import vào `app/models/__init__.py` thì bảng đó vô hình với Alembic. Lần đầu: migration không tạo bảng. Lần sau, nếu bảng đã có dưới DB: Alembic tưởng nó thừa và **sinh ra `DROP TABLE`**.

### Khối 2 — nạp URL từ `.env`

```python
from app.core.config.database import db_settings

config = context.config
config.set_main_option(
    "sqlalchemy.url",
    db_settings.database_url_sync.replace("%", "%%"),
)
```

`.replace("%", "%%")` không phải cho đẹp: `alembic.ini` do ConfigParser đọc, mà ConfigParser hiểu `%` là cú pháp nội suy. Mật khẩu có ký tự `%` (rất hay gặp khi generate mật khẩu ngẫu nhiên) sẽ làm cả lệnh chết với `InterpolationSyntaxError`.

### Khối 3 — các option so sánh

```python
context.configure(
    connection=connection,
    target_metadata=target_metadata,
    compare_type=True,             # phát hiện đổi kiểu cột: String(100) -> String(255)
    compare_server_default=True,   # phát hiện đổi server_default
    include_object=include_object,
    process_revision_directives=process_revision_directives,
)
```

Hai option `compare_*` mặc định **tắt**. Không bật thì sửa `String(100)` thành `String(255)` trong model sẽ được autogenerate lặng lẽ bỏ qua, và bạn tưởng là đã migrate xong.

Naming convention khai báo ở [`app/database/base.py`](../backend-fastapi/app/database/base.py) chỉ phát huy tác dụng khi chính `Base.metadata` này được truyền vào `target_metadata` — nhờ nó mọi index/constraint có tên xác định (`ix_users_role_is_active`, `uq_users_email`), thay vì tên do Postgres tự chế mà không đoán trước được.

### Khối 4 — `include_object`: lọc thứ không thuộc quyền Alembic

```python
def include_object(obj, name, type_, reflected, compare_to):
    """Trả False = Alembic coi như không thấy đối tượng này."""
    # Bảng do extension tạo ra, không phải bảng nghiệp vụ.
    if type_ == "table" and name in {"spatial_ref_sys"}:
        return False
    return True
```

Chưa cần lọc gì ở M1/M2, nhưng phải có sẵn hook: khi M3 bật thêm extension, hoặc khi có bảng do công cụ ngoài quản lý, đây là chỗ duy nhất chặn Alembic sinh `DROP TABLE` cho chúng.

### Khối 5 — chặn migration rỗng

```python
def process_revision_directives(context_, revision, directives):
    if getattr(config.cmd_opts, "autogenerate", False):
        if directives[0].upgrade_ops.is_empty():
            directives[:] = []
            print("Không có thay đổi nào so với DB — bỏ qua, không tạo file rỗng.")
```

Không có khối này, mỗi lần gõ nhầm lệnh là `versions/` lại thêm một file `pass` vô nghĩa, và chuỗi revision dài ra vô ích.

### Khối 6 — hai chế độ chạy

```python
def run_migrations_offline() -> None:
    """Không kết nối DB, chỉ in ra SQL: alembic upgrade head --sql > migration.sql"""
    context.configure(
        url=config.get_main_option("sqlalchemy.url"),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Chế độ thường dùng: kết nối thật và chạy."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,   # migration chạy xong là thoát, không cần pool
    )
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata, ...)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
```

Chế độ offline dùng khi lên production mà DBA yêu cầu xem trước SQL, hoặc khi tài khoản app không có quyền DDL.

### Kiểm tra setup xong chưa

```bash
cd backend-fastapi
alembic current      # phải chạy không lỗi (in ra rỗng vì chưa có migration nào)
alembic heads        # rỗng
```

`alembic current` chạy được nghĩa là: import được `app`, đọc được `.env`, kết nối được Postgres. Ba thứ khó nhất đã xong.

---

# PHẦN B — Migration đầu tiên (baseline M1 + M2)

### B.1 — Dựng database và kiểm tra extension

```bash
docker compose up -d postgres
docker compose exec postgres psql -U eduai -d eduai -c '\dx'
```

Phải thấy `pgcrypto`, `vector`, `pg_trgm`, `unaccent`. Thiếu `pgcrypto` là mọi bảng chết ngay, vì `id` của `users`/`classes`/`courses`/`subjects` đều dùng `server_default=text("gen_random_uuid()")`.

Nếu thiếu: volume đã được tạo từ trước khi có [`database/init/01_extensions.sql`](../database/init/01_extensions.sql) — file đó chỉ chạy trên volume rỗng. Chạy `docker compose down -v && docker compose up -d` (xoá sạch dữ liệu), hoặc để bước B.2 lo.

### B.2 — Migration `0000`: bật extension (viết tay)

```bash
alembic revision -m "enable postgres extensions"     # KHÔNG có --autogenerate
```

Mở file vừa sinh trong `alembic/versions/`, viết:

```python
def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")
    op.execute("CREATE EXTENSION IF NOT EXISTS unaccent")


def downgrade() -> None:
    # Cố tình KHÔNG DROP EXTENSION: có thể có schema khác trong cùng DB đang dùng.
    pass
```

Vì sao vẫn cần dù `database/init/` đã có: cơ chế `docker-entrypoint-initdb.d` **chỉ tồn tại ở docker compose local**. Database trên CI, staging, production, hay Postgres cài trực tiếp đều không chạy thư mục đó. Migration là thứ duy nhất chạy ở mọi môi trường.

### B.3 — Sinh migration cho 7 bảng

```bash
alembic revision --autogenerate -m "create m1 m2 tables"
```

### B.4 — ĐỌC LẠI FILE VỪA SINH (bước hay bị bỏ qua nhất)

Autogenerate là **bản nháp**, không phải kết quả. Với đúng 7 model hiện tại, soát theo checklist này:

**a) Thứ tự tạo bảng** — phải theo phụ thuộc khoá ngoại:

```
users → teacher_profiles, student_profiles → subjects
      → classes (FK teacher_profiles)
      → class_students (FK classes, student_profiles)
      → courses (FK classes, subjects, teacher_profiles)
```

**b) Ba enum type.** Model dùng `values_callable` để lưu **chữ thường**, nhưng tham số đó **không được ghi vào file migration**. Phải tự mắt kiểm tra:

```python
sa.Enum('admin', 'teacher', 'student', name='user_role')        # ĐÚNG
sa.Enum('ADMIN', 'TEACHER', 'STUDENT', name='user_role')        # SAI - sửa tay ngay
```

Ba type cần có: `user_role` (admin/teacher/student), `term` (hk1/hk2/ca_nam), `course_status` (active/archived). Sai chữ hoa/thường ở đây là JWT và frontend đọc role ra giá trị lạ.

**c) `downgrade()` phải tự thêm `DROP TYPE`.** Alembic tạo enum type kèm `create_table` nhưng **không xoá** khi drop bảng. Chạy `downgrade` rồi `upgrade` lại sẽ chết với `type "user_role" already exists`. Thêm vào cuối `downgrade()`:

```python
sa.Enum(name="user_role").drop(op.get_bind(), checkfirst=False)
sa.Enum(name="term").drop(op.get_bind(), checkfirst=False)
sa.Enum(name="course_status").drop(op.get_bind(), checkfirst=False)
```

**d) Partial unique index của `class_students`** — ràng buộc "một học sinh chỉ đang học một lớp" nằm ở đây, mất nó là mất luôn ràng buộc:

```python
op.create_index(
    "uq_class_students_active_student", "class_students", ["student_id"],
    unique=True, postgresql_where=sa.text("left_at IS NULL"),
)
```

**e) CHECK constraint của `users`** — `ck_users_has_login_method`:

```python
sa.CheckConstraint("hashed_password IS NOT NULL OR google_id IS NOT NULL",
                   name="has_login_method")
```

**f) Tên index/constraint** phải theo naming convention, đối chiếu:

| Bảng | Phải có |
|---|---|
| `users` | `pk_users`, `uq_users_email`, `uq_users_google_id`, `ix_users_role_is_active`, `ck_users_has_login_method` |
| `subjects` | `uq_subjects_code` |
| `classes` | `uq_classes_class_name_academic_year`, `uq_classes_homeroom_teacher_id_academic_year` |
| `class_students` | `pk_class_students` (ghép 2 cột), `uq_class_students_active_student`, `ix_class_students_student_id` |
| `courses` | `uq_courses_class_id_subject_id_term`, `ix_courses_teacher_id`, `ix_courses_subject_id` |

Thấy tên kiểu `users_email_key` (Postgres tự đặt) nghĩa là convention chưa được áp — quay lại kiểm tra `target_metadata` ở `env.py`.

**g) `ondelete` khớp phần `Ref` trong dbml:**

| Khoá ngoại | Phải là |
|---|---|
| `teacher_profiles.user_id`, `student_profiles.user_id` → `users.id` | `CASCADE` |
| `classes.homeroom_teacher_id` | `SET NULL` |
| `class_students.class_id` | `CASCADE` |
| `class_students.student_id` | `RESTRICT` |
| `courses.class_id` | `CASCADE` |
| `courses.subject_id`, `courses.teacher_id` | `RESTRICT` |

Sai `RESTRICT` thành `CASCADE` là xoá một môn học kéo theo mất sạch lớp học phần — loại lỗi chỉ phát hiện ra khi đã mất dữ liệu.

**h) Viết docstring đầu file** giải thích migration này làm gì và vì sao, theo văn phong các file trong `app/models/`.

### B.5 — Chạy

```bash
alembic upgrade head
```

### B.6 — Nghiệm thu

```bash
alembic current                                             # in ra revision id
alembic check                                               # "No new upgrade operations detected"
docker compose exec postgres psql -U eduai -d eduai -c '\d+ users'
docker compose exec postgres psql -U eduai -d eduai -c '\dt'
```

`alembic check` là bài kiểm tra thật sự: nó so models với DB và báo lỗi nếu còn chênh. Ra "no new operations" nghĩa là DB đúng bằng models.

### B.7 — Thử `downgrade` (chỉ ở máy dev)

```bash
alembic downgrade base && alembic upgrade head
```

Đây là lúc duy nhất phát hiện `downgrade()` viết sai (thường là vụ `DROP TYPE` ở mục **c**). Không thử bây giờ thì lúc cần rollback trên production mới biết là nó hỏng.

### B.8 — Commit

Model và migration **đi chung một commit**. Tách ra là có một commit ở giữa mà `alembic check` fail, và ai checkout đúng commit đó sẽ không dựng được môi trường.

```bash
git add backend-fastapi/alembic backend-fastapi/alembic.ini backend-fastapi/requirements.txt \
        backend-fastapi/app/core/config/database.py backend-fastapi/app/models
git commit -m "feat(db): setup alembic + migration baseline M1 M2"
```

---

# PHẦN C — Vòng lặp cho mỗi lần đổi schema

Từ đây về sau, **mọi** thay đổi schema đều đi đúng 8 bước này:

| # | Việc | Lệnh / File |
|---|---|---|
| 1 | Sửa ERD trước | `database/erd/schema.dbml` |
| 2 | Sửa / thêm model | `app/models/<ten>.py` |
| 3 | **Thêm import nếu là model mới** | `app/models/__init__.py` (quên = Alembic sinh `DROP TABLE`) |
| 4 | Sinh migration | `alembic revision --autogenerate -m "add avatar_url to users"` |
| 5 | **Đọc và sửa tay file vừa sinh** | checklist Phần D |
| 6 | Chạy | `alembic upgrade head` |
| 7 | Nghiệm thu | `alembic check` → phải sạch |
| 8 | Commit chung model + migration | |

Ba quy tắc kèm theo:

- **Một migration = một ý định.** "Thêm bảng documents" và "đổi kiểu cột phone" là hai migration, kể cả khi làm trong cùng một buổi. Rollback mới tách bạch được.
- **Không sửa migration đã push.** Viết cái mới.
- **Message viết bằng tiếng Anh, dạng động từ + đối tượng:** `create documents table`, `add avatar_url to users`, `drop unused column`. Message này chui thẳng vào tên file.

---

# PHẦN D — Những thứ autogenerate KHÔNG tự thấy

Đây là bảng phải liếc qua mỗi lần chạy `--autogenerate`. Cột phải là việc phải làm tay.

| Thay đổi | Autogenerate làm gì | Phải làm gì |
|---|---|---|
| **Đổi tên cột / bảng** | Sinh `drop_column` + `add_column` → **mất sạch dữ liệu cột đó** | Xoá hai lệnh đó, thay bằng `op.alter_column("users", "ten_cu", new_column_name="ten_moi")` hoặc `op.rename_table(...)` |
| **Thêm giá trị vào enum** | Không thấy gì | `op.execute("ALTER TYPE course_status ADD VALUE 'draft'")`. Postgres 16 cho chạy trong transaction, nhưng **giá trị mới chưa dùng được ở cùng transaction đó** — cần backfill thì tách làm hai migration |
| **Xoá giá trị khỏi enum** | Không thấy gì | Postgres không hỗ trợ. Phải tạo type mới, `ALTER TABLE ... TYPE ... USING`, drop type cũ |
| **Thêm / xoá CHECK constraint** | Không thấy gì (chỉ thấy lúc `create_table` lần đầu) | `op.create_check_constraint("ten", "bang", "dieu_kien")` / `op.drop_constraint(...)` |
| **Đổi điều kiện partial index** | Thường không thấy | `op.drop_index` rồi `op.create_index` với `postgresql_where` mới |
| **Đổi kiểu cột cần chuyển đổi dữ liệu** | Sinh `alter_column` trần → lỗi `cannot be cast automatically` | Thêm `postgresql_using="cot::integer"` |
| **Thêm cột `NOT NULL` vào bảng đã có dữ liệu** | Sinh đúng lệnh nhưng **chạy sẽ lỗi** | Ba bước: thêm cột nullable → backfill dữ liệu → `alter_column(nullable=False)` |
| **Backfill / sửa dữ liệu** | Không bao giờ | Viết tay, xem §D.1 |
| **Cột `Vector(1536)` của pgvector** | Render đúng kiểu nhưng **thiếu dòng import** | Thêm `import pgvector.sqlalchemy` vào đầu file migration (hoặc vào `script.py.mako`) |
| **Extension, trigger, view, function** | Không thấy gì | `op.execute("CREATE ...")` |
| **Index đặc thù Postgres (GIN, IVFFlat cho vector)** | Thường không thấy | `op.create_index(..., postgresql_using="ivfflat", postgresql_ops={...})` |

## D.1 — Data migration: quy tắc quan trọng nhất

> **Không bao giờ `import app.models` bên trong file migration.**

Lý do: migration là ảnh chụp schema **tại thời điểm viết**, còn model thì thay đổi mãi. Migration tháng 3 mà import `User` sẽ dùng định nghĩa `User` của tháng 12 — trong đó có những cột mà lúc migration này chạy còn chưa tồn tại. Kết quả: dựng lại DB từ đầu thì chết ở giữa chuỗi.

Cách đúng — khai báo bảng "nhẹ", chỉ liệt kê đúng những cột migration này cần:

```python
def upgrade() -> None:
    op.add_column("users", sa.Column("display_name", sa.String(255), nullable=True))

    # Bảng tạm chỉ để chạy UPDATE, độc lập hoàn toàn với app/models/user.py
    users = sa.table(
        "users",
        sa.column("display_name", sa.String),
        sa.column("full_name", sa.String),
    )
    op.execute(users.update().values(display_name=users.c.full_name))

    op.alter_column("users", "display_name", nullable=False)
```

---

# PHẦN E — Cheat sheet lệnh

Mọi lệnh chạy từ `backend-fastapi/`, đã `source .venv/bin/activate`.

| Lệnh | Dùng khi |
|---|---|
| `alembic revision --autogenerate -m "..."` | Sinh migration từ chênh lệch model ↔ DB |
| `alembic revision -m "..."` | Sinh file rỗng để viết tay (extension, data migration, trigger) |
| `alembic upgrade head` | Chạy hết migration còn thiếu |
| `alembic upgrade +1` | Chạy đúng một bước — dùng khi soi từng migration |
| `alembic downgrade -1` | Lùi một bước |
| `alembic downgrade base` | Xoá sạch schema (chỉ ở dev) |
| `alembic current` | DB đang ở revision nào |
| `alembic heads` | Có mấy nhánh đầu — ra **nhiều hơn 1 là có vấn đề**, xem Phần F |
| `alembic history --verbose` | Xem cả chuỗi migration |
| `alembic check` | **Models và DB đã khớp chưa** — chạy trước mỗi lần commit và trong CI |
| `alembic upgrade head --sql` | In SQL ra thay vì chạy, để review hoặc bàn giao |
| `alembic stamp head` | Đánh dấu "DB này coi như đã chạy hết" mà không chạy gì — xem Phần F |
| `alembic merge -m "..." heads` | Gộp hai nhánh migration |

---

# PHẦN F — Sự cố thường gặp

| Triệu chứng | Nguyên nhân | Cách xử lý |
|---|---|---|
| `ModuleNotFoundError: No module named 'app'` | Thiếu `prepend_sys_path = .`, hoặc đang gõ lệnh từ thư mục khác | Thêm dòng đó vào `alembic.ini`, `cd backend-fastapi` rồi chạy lại |
| `ModuleNotFoundError: No module named 'psycopg2'` | URL viết `postgresql+psycopg2://` nhưng cài `psycopg` v3 | Sửa `DATABASE_URL_SYNC` thành `postgresql+psycopg://` |
| `Target database is not up to date` | Đang định autogenerate trong khi DB còn thiếu migration | `alembic upgrade head` trước, rồi mới autogenerate |
| `Multiple head revisions are present` | Hai nhánh git cùng tạo migration từ một cha, merge code xong thành hai đầu | `alembic merge -m "merge migration branches" heads` rồi `upgrade head` |
| `Can't locate revision identified by '<id>'` | Đã xoá file migration mà DB vẫn ghi id đó trong `alembic_version` | Khôi phục file từ git. Bất đắc dĩ: sửa tay bảng `alembic_version` (biết chắc mình đang làm gì mới làm) |
| `type "user_role" already exists` | `downgrade()` thiếu `DROP TYPE` | Xem Phần B.4 mục **c** |
| Autogenerate **luôn** sinh ra diff dù không sửa gì | Thường do `compare_server_default` so `now()` với `CURRENT_TIMESTAMP`, hoặc enum, hoặc model chưa được import | Đọc kỹ diff. Nếu đúng là false-positive lặp lại, thêm ngoại lệ trong `include_object` |
| Autogenerate sinh `DROP TABLE` cho bảng đang dùng | Model chưa được import vào `app/models/__init__.py` | Thêm dòng import. **Đừng chạy migration đó** |
| `password authentication failed` | Mật khẩu trong `backend-fastapi/.env` khác `POSTGRES_PASSWORD` ở `.env` gốc | Sửa cho khớp |
| `InterpolationSyntaxError` | Mật khẩu có ký tự `%` | `.replace("%", "%%")` ở `env.py` (Phần A.7 khối 2) |
| DB đã có sẵn bảng nhưng chưa có `alembic_version` | Bảng được tạo bằng tay trước khi dùng Alembic | `alembic stamp head` — nhưng phải chắc chắn schema thật khớp migration, sai là lệch vĩnh viễn |
| `alembic init` báo thư mục đã tồn tại | `alembic/` đã có sẵn trong repo | Dùng mẹo `alembic init _tmp` ở đầu Phần A |

---

# PHẦN G — Ranh giới ba thư mục

Hay nhầm nhất là bỏ nhầm thứ vào nhầm chỗ:

| Thư mục | Chứa gì | Chạy khi nào |
|---|---|---|
| [`database/init/`](../database/init/) | **Chỉ** `CREATE EXTENSION` | Một lần duy nhất, lúc container postgres tạo volume rỗng. Không có ở CI/production |
| `backend-fastapi/alembic/versions/` | **Toàn bộ schema**: bảng, cột, index, constraint, type, trigger + extension (thủ để chắc chắn) | `alembic upgrade head`, ở mọi môi trường |
| [`database/seeds/`](../database/seeds/) và `backend-fastapi/scripts/` | Dữ liệu demo: vài lớp, vài chục học sinh giả | Chạy tay khi cần demo |

> **Dữ liệu mẫu không phải migration.** Đừng nhét `INSERT` học sinh giả vào `alembic/versions/` — production rồi cũng sẽ chạy migration đó, và dữ liệu rác sẽ chui vào database thật.
>
> Ngoại lệ hợp lệ duy nhất: dữ liệu **hệ thống bắt buộc phải có** để app chạy — ví dụ danh mục 12 môn học trong `subjects`. Cái đó là schema, không phải seed.

---

# Checklist trước khi commit

- [ ] `alembic upgrade head` chạy sạch
- [ ] `alembic check` báo không còn chênh lệch
- [ ] `alembic downgrade -1` rồi `upgrade head` lại chạy được
- [ ] Đã đọc **từng dòng** file migration, không chỉ liếc qua
- [ ] `app/models/__init__.py` đã có import của model mới
- [ ] `database/erd/schema.dbml` đã cập nhật khớp
- [ ] Model + migration nằm trong **cùng một commit**
- [ ] `alembic heads` chỉ ra đúng **một** dòng
