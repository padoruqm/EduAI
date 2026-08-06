# EduAI — Cấu trúc thư mục

Tài liệu tra cứu nhanh: **mỗi thư mục dùng để làm gì** và **file code mới nên đặt ở đâu**.

> Cần biết **code cái gì** (chức năng theo vai trò, use case, luồng lỗi, tiêu chí xong)?
> Xem bộ đặc tả yêu cầu: [srs/README.md](srs/README.md).

---

## 1. Luồng dữ liệu & quy tắc vàng

Backend chia theo layer, dữ liệu đi **một chiều**, không được nhảy cóc:

```
HTTP request
    │
    ├─→ api/v1/routers/     nhận request, validate input, kiểm tra quyền
    │       │
    │       ├─→ services/           business logic (tính điểm, gọi AI, kiểm tra hạn nộp...)
    │       │       │
    │       │       ├─→ repositories/       câu truy vấn DB
    │       │       │       └─→ models/     bảng thật trong PostgreSQL
    │       │       │
    │       │       ├─→ integrations/       MinIO, SMTP, Google OAuth
    │       │       └─→ workers/tasks/      đẩy việc nặng sang RabbitMQ
    │       │
    │       └─← schemas/            JSON trả về cho client
```

**Ba điều cấm** (vi phạm là kiến trúc layer mất tác dụng):

| Cấm | Lý do |
|---|---|
| Router truy vấn DB trực tiếp | Logic rò rỉ ra tầng HTTP, không test được nếu không dựng cả web server |
| Repository chứa business logic | Repository chỉ biết "lấy/ghi dữ liệu", không biết "điểm dưới 5 là học sinh yếu" |
| Service import `Request` / raise `HTTPException` | Service phải dùng được cả từ router lẫn từ Celery worker. Hãy raise exception riêng ở `core/exceptions.py`, router mới dịch sang mã HTTP |

---

## 2. `backend-fastapi/`

| Thư mục | Đặt gì vào đây | Ví dụ file |
|---|---|---|
| `app/api/v1/routers/` | Endpoint HTTP, **1 file cho 1 module nghiệp vụ** | `auth.py`, `users.py`, `courses.py`, `documents.py`, `chat.py`, `quizzes.py`, `submissions.py`, `analytics.py` |
| `app/api/deps/` | Dependency dùng lại ở nhiều route | `db.py` (`get_db`), `auth.py` (`get_current_user`, `require_role(Role.TEACHER)`) |
| `app/core/` | Cấu hình & hạ tầng chung, **không dính nghiệp vụ** | `config.py` (đọc `.env` bằng Pydantic Settings), `security.py` (hash mật khẩu, ký JWT), `exceptions.py`, `logging.py`, `rate_limit.py` |
| `app/db/` | Kết nối database | `session.py` (async engine + session factory), `base.py` (DeclarativeBase) |
| `app/models/` | **Bảng thật trong PostgreSQL** (SQLAlchemy ORM). `__init__.py` import mọi model — thiếu một dòng là Alembic không thấy bảng đó | `user.py`, `teacher_profile.py`, `student_profile.py`, `school_class.py`, `class_student.py`, `subject.py`, `course.py`, `document.py`, `chunk.py`, `quiz.py`, `submission.py` |
| `app/schemas/` | Hình dạng JSON vào/ra (Pydantic v2) | `user.py` chứa `UserCreate`, `UserUpdate`, `UserOut` |
| `app/repositories/` | Câu truy vấn DB thuần (SELECT/INSERT/UPDATE) | `user_repository.py`, `document_repository.py`, `chunk_repository.py` (search vector) |
| `app/services/` | Business logic — nơi viết nhiều code nhất | `auth_service.py`, `course_service.py`, `document_service.py`, `grading_service.py` |
| `app/services/ai/llm/` | Bọc lời gọi OpenAI: retry, streaming, đếm token & chi phí | `openai_client.py`, `cost_tracker.py` |
| `app/services/ai/embedding/` | Sinh embedding theo batch cho tài liệu | `embedder.py` |
| `app/services/ai/rag/` | Cắt chunk, tìm top-k trong pgvector, cache câu hỏi trùng | `chunker.py`, `retriever.py`, `cache.py` |
| `app/services/ai/prompts/` | Template prompt, tách khỏi code để sửa không cần đụng logic | `chat_prompt.py`, `quiz_prompt.py`, `grading_prompt.py` |
| `app/workers/tasks/` | Việc chạy nền qua RabbitMQ (file lớn, gọi LLM hàng loạt) | `ingest_document.py`, `grade_submission.py`, `send_notification.py`, `compute_analytics.py` |
| `app/integrations/` | Nói chuyện với hệ thống bên ngoài | `storage/minio_client.py`, `oauth/google.py`, `email/smtp.py`, `ocr/` (giai đoạn 2) |
| `app/utils/` | Hàm tiện ích thuần, không phụ thuộc DB/HTTP | `slugify.py`, `datetime.py`, `file_type.py` |
| `alembic/versions/` | Migration — **mọi thay đổi bảng đều phải đi qua đây** | Sinh bằng `alembic revision --autogenerate -m "add users table"` |
| `tests/unit/` | Test 1 hàm/1 service, mock hết DB và API ngoài | `test_grading_service.py` |
| `tests/integration/` | Test chạm DB/Redis thật, gọi qua HTTP client | `test_auth_flow.py` |
| `scripts/` | Script chạy tay | `seed_demo_data.py` |

### Điểm dễ nhầm nhất: `models/` vs `schemas/`

| | `models/user.py` | `schemas/user.py` |
|---|---|---|
| Là gì | Bảng `users` dưới PostgreSQL | JSON mà client nhìn thấy |
| Thư viện | SQLAlchemy | Pydantic v2 |
| Có gì | `id`, `email`, `hashed_password`, `role`, `created_at` | `UserOut` chỉ có `id`, `email`, `role` |

> **Không bao giờ trả thẳng model ra API** — sẽ lộ `hashed_password`. Luôn đi qua schema.

---

## 3. `frontend-vue3/`

| Thư mục | Đặt gì vào đây | Ví dụ file |
|---|---|---|
| `src/api/` | Gọi backend. `client.ts` cấu hình axios + interceptor tự refresh token, còn lại 1 file/module | `client.ts`, `auth.ts`, `course.ts`, `document.ts`, `chat.ts` |
| `src/types/` | Interface TypeScript, khớp 1-1 với `schemas/` bên backend | `user.ts`, `course.ts`, `quiz.ts` |
| `src/stores/` | State dùng chung nhiều màn hình (Pinia) | `auth.ts` (user đang đăng nhập), `course.ts` |
| `src/views/` | Màn hình **gắn với 1 route**, chia theo role | `auth/LoginView.vue`, `teacher/DocumentListView.vue`, `student/ChatView.vue`, `admin/UserListView.vue` |
| `src/components/` | Mảnh UI tái dùng, **không gắn route** | `common/BaseButton.vue`, `chat/MessageBubble.vue`, `quiz/QuestionEditor.vue` |
| `src/layouts/` | Khung bao ngoài (sidebar, header) theo từng role | `AuthLayout.vue`, `TeacherLayout.vue`, `StudentLayout.vue` |
| `src/composables/` | Logic tái dùng viết dạng hàm | `useAuth.ts`, `useSSE.ts` (nhận chat streaming), `useUpload.ts` (progress bar) |
| `src/router/` | Khai báo route + guard chặn theo role | `index.ts`, `guards.ts` |
| `src/utils/` | Hàm thuần | `formatDate.ts`, `formatScore.ts` |
| `src/assets/` | Ảnh, CSS/SCSS toàn cục | `styles/main.scss` |
| `public/` | File tĩnh copy nguyên si, không qua build | `favicon.ico` |
| `tests/unit/`, `tests/e2e/` | Test component / test luồng qua trình duyệt | `LoginView.spec.ts` |

### Điểm dễ nhầm: `views/` vs `components/`

Có route trỏ tới → đặt ở `views/`. Không có route, được dùng lại ở nhiều nơi → đặt ở `components/`.

---

## 4. `database/`

| Thư mục | Đặt gì vào đây |
|---|---|
| `init/` | Script SQL **chỉ chạy đúng 1 lần** lúc container postgres tạo volume rỗng. Hiện có `01_extensions.sql` bật pgvector, pg_trgm, pgcrypto, unaccent |
| `seeds/` | Dữ liệu mẫu cho demo (1 lớp học, vài chục học sinh giả lập) |
| `erd/` | Sơ đồ quan hệ các bảng |

> **Không viết `CREATE TABLE` vào `database/init/`.** Bảng do Alembic bên `backend-fastapi/alembic/`
> quản lý. Nếu tạo bảng ở hai nơi, schema thật và migration sẽ lệch nhau.
>
> Muốn chạy lại `init/`: `docker compose down -v && docker compose up -d` (xoá sạch dữ liệu).

---

## 5. Teacher, Student, Admin đặt ở đâu?

**Không tạo 3 file `teacher.py` / `student.py` / `admin.py`.** Cả ba là **cùng một** entity `User`,
phân biệt bằng cột `role`:

```python
# app/models/user.py
class Role(str, enum.Enum):
    ADMIN = "admin"
    TEACHER = "teacher"
    STUDENT = "student"

class User(Base):
    __tablename__ = "users"
    id: Mapped[uuid.UUID]
    email: Mapped[str]
    hashed_password: Mapped[str | None]   # None nếu đăng nhập bằng Google OAuth
    role: Mapped[Role]
```

Dữ liệu **riêng** của từng vai trò (mã học sinh, bộ môn giảng dạy, phòng làm việc) nằm ở bảng hồ sơ
1-1, dùng luôn `user_id` làm khoá chính: `teacher_profiles` và `student_profiles`. Đây **không phải**
tách bảng `users` — vẫn chỉ có một bảng tài khoản, một email, một lần đăng nhập.

Hai bảng hồ sơ còn là chốt chặn ở tầng DB: `courses.teacher_id` và `classes.homeroom_teacher_id`
trỏ về `teacher_profiles.user_id` chứ không trỏ về `users.id`, nên Postgres tự từ chối việc phân
công một học sinh đi dạy.

Các file liên quan tới user:

| File | Vai trò |
|---|---|
| `app/models/user.py` | Bảng `users` + enum `Role` |
| `app/models/teacher_profile.py` | Bảng `teacher_profiles` — bộ môn, phòng làm việc |
| `app/models/student_profile.py` | Bảng `student_profiles` — mã học sinh |
| `app/schemas/user.py` | `UserCreate`, `UserOut`, `UserUpdate` |
| `app/repositories/user_repository.py` | `get_by_email`, `list_students_in_class` |
| `app/services/auth_service.py` | Đăng ký, đăng nhập, cấp JWT |
| `app/api/v1/routers/users.py` | Endpoint CRUD user |
| `app/api/deps/auth.py` | `get_current_user`, `require_role(Role.TEACHER)` — nơi phân quyền |
| `frontend-vue3/src/types/user.ts` | Interface `User` + type `Role` |
| `frontend-vue3/src/stores/auth.ts` | Lưu user đang đăng nhập, dùng để ẩn/hiện menu theo role |

### Mô hình lớp học: trường phổ thông, không phải MOOC

Nhà trường xếp lớp. Học sinh **không** tự đăng ký, **không** có mã mời. Một lớp có sĩ số cố định và
đúng một giáo viên chủ nhiệm; lớp đó học nhiều môn, mỗi môn một giáo viên bộ môn khác nhau dạy.

```
users ──1:1── teacher_profiles ──┬──1:N──→ classes.homeroom_teacher_id  (tối đa 1 lớp MỖI NĂM HỌC)
      │                          └──1:N──→ courses.teacher_id           (dạy nhiều môn, nhiều lớp)
      └──1:1── student_profiles ───N:M qua class_students──→ classes

classes (10A1 năm 2025-2026) ──┬─< class_students   DANH SÁCH HỌC SINH
                               └─< courses          mỗi môn một dòng
subjects ──< courses
```

**Teacher và Student liên hệ với nhau qua lớp học**, không phải quan hệ trực tiếp giữa hai user.

Ba điều dễ làm sai nhất ở mô hình này:

| Điều | Vì sao |
|---|---|
| Học sinh của một `Course` **không có bảng riêng** — đó là `class_students` của `course.class_id` | Lớp sĩ số cố định thì học môn nào cũng là nhóm học sinh đó. Ghi danh theo từng môn sẽ lặp lại cùng một danh sách cho 12 môn, quên một dòng là học sinh mất quyền vào một môn |
| Mỗi dòng `classes` gắn với **một năm học** | Lớp 10A1 năm 2025-2026 và 11A1 năm 2026-2027 là hai dòng khác nhau. Nhờ vậy danh sách lớp cũ không bị ghi đè khi học sinh lên lớp, và vẫn tra được điểm của năm trước |
| Ràng buộc "1 giáo viên chủ nhiệm 1 lớp" phải unique trên **(giáo viên, năm học)** | Chỉ unique trên cột giáo viên thì người đã chủ nhiệm 10A1 năm nay sẽ vĩnh viễn không chủ nhiệm được lớp nào ở các năm sau |

Sơ đồ đầy đủ kèm lý do từng ràng buộc: [`database/erd/schema.dbml`](../database/erd/schema.dbml).

---

## 6. Checklist thêm 1 module mới

Làm đúng thứ tự này để không bỏ sót file. Ví dụ thêm module Course:

**Backend**

1. `app/models/course.py` — định nghĩa bảng
2. `alembic revision --autogenerate -m "add courses table"` — sinh migration, rồi `alembic upgrade head`
3. `app/schemas/course.py` — `CourseCreate`, `CourseOut`
4. `app/repositories/course_repository.py` — truy vấn
5. `app/services/course_service.py` — logic (ai được phân công dạy lớp này, lớp đã lưu trữ chưa)
6. `app/api/v1/routers/courses.py` — endpoint
7. Đăng ký router vào `app/main.py`
8. `tests/` — ít nhất 1 test cho service

**Frontend**

1. `src/types/course.ts` — copy đúng field từ `CourseOut`
2. `src/api/course.ts` — hàm gọi API
3. `src/stores/course.ts` — nếu nhiều màn hình cùng dùng
4. `src/views/teacher/CourseListView.vue` + khai báo route trong `src/router/index.ts`

---

## 7. Quy ước đặt tên

| Loại | Quy ước | Ví dụ |
|---|---|---|
| File Python | `snake_case.py` | `user_repository.py` |
| File model | **số ít** | `user.py` → `class User`, bảng `users` |
| File model trùng từ khoá Python | thêm tiền tố cho rõ nghĩa | `school_class.py` → `class SchoolClass`, bảng `classes`. Không đặt `class.py`: `from app.models.class import ...` là lỗi cú pháp |
| File router | **số nhiều** (khớp URL) | `courses.py` → `/api/v1/courses` |
| Repository / Service | hậu tố `_repository.py` / `_service.py` | `course_service.py` |
| Celery task | động từ, mô tả hành động | `ingest_document.py` |
| Component Vue | `PascalCase.vue` | `MessageBubble.vue` |
| View Vue | `PascalCase` + hậu tố `View` | `CourseListView.vue` |
| Composable | `useXxx.ts` | `useAuth.ts` |
| File TS khác | `camelCase.ts` | `formatDate.ts` |
| Bảng DB | `snake_case`, **số nhiều** | `users`, `quiz_questions` |
| Endpoint | `kebab-case`, số nhiều | `/api/v1/quiz-questions` |
