# EduAI
open:
cd /Users/quangminh/Desktop/project_EduAI
docker compose up -d postgres          # Docker Desktop phải đang mở

cd backend-fastapi
source .venv/bin/activate           
alembic current


1. Kiến trúc phân tầng: Router → Service → Repository → Model và phản hồi qua Schema. Không bỏ qua layer.

2. Không:
    - Router không truy vấn DB trực tiếp.
    - Repository chỉ chứa truy vấn dữ liệu, không chứa business logic.
    - Service không phụ thuộc HTTP (Request, HTTPException), chỉ ném custom exception trong core/exceptions.py.
  
3. Phân biệt rõ models và schemas:
    - models/ = SQLAlchemy ORM (bảng PostgreSQL).
    - schemas/ = Pydantic v2 (request/response).
    - Không trả ORM model trực tiếp ra API.

4. AI module tách riêng:
   - services/ai/llm/
   - services/ai/embedding/
   - services/ai/rag/
   - services/ai/prompts/
  
Tác vụ nền luôn đặt trong workers/tasks/.
Tích hợp hệ thống ngoài (MinIO, OAuth, SMTP...) đặt trong integrations/.

5. Frontend Vue 3:
views = màn hình có route.
components = UI tái sử dụng.
api chỉ gọi backend.
stores dùng Pinia.
types phải khớp schemas của backend.

6. User thống nhất:
Chỉ có một bảng users. Phân quyền bằng role (ADMIN, TEACHER, STUDENT).
Không tách bảng teacher/student. Dữ liệu riêng của từng vai trò nằm ở bảng hồ sơ 1-1
(teacher_profiles, student_profiles) dùng chính user_id làm khoá chính.

7. Mô hình lớp học là trường phổ thông, không phải MOOC:
    - Nhà trường xếp lớp. Học sinh không tự đăng ký, không có mã mời.
    - classes = lớp chính quy 10A1 của MỘT năm học, sĩ số cố định, 1 giáo viên chủ nhiệm.
    - courses = lớp học phần "10A1 học Toán HK1, thầy Nam dạy". Mọi module AI treo vào đây.
    - class_students = danh sách học sinh, gắn vào LỚP chứ không gắn vào từng môn.
      Học sinh của một course chính là class_students của course.class_id.
    - Giáo viên chủ nhiệm tối đa 1 lớp MỖI NĂM HỌC, nhưng dạy được nhiều môn ở nhiều lớp.
Sơ đồ đầy đủ: database/erd/schema.dbml

8. Thêm module mới sẽ theo đúng checklist:
Model
Alembic migration
Schema
Repository
Service
Router
Đăng ký router
Test
rồi mới tới frontend (types → api → store → views → router).

9. Quy ước đặt tên sẽ được giữ thống nhất:
Python: snake_case
Model: số ít (trùng từ khoá Python thì thêm tiền tố: school_class.py → class SchoolClass, bảng classes)
Router: số nhiều
Vue Component: PascalCase.vue
View: PascalCaseView.vue
Composable: useXxx.ts
Bảng DB: số nhiều
Endpoint: kebab-case