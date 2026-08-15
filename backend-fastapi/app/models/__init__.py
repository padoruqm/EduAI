"""Nơi đăng ký toàn bộ model của hệ thống.

Alembic autogenerate chỉ nhìn thấy những bảng đã được nạp vào `Base.metadata`.
Model nào không được import ở đây thì `alembic revision --autogenerate` sẽ coi
như không tồn tại — tệ hơn nữa, nếu bảng đó đã có dưới DB thì Alembic tưởng nó
thừa và sinh ra lệnh DROP TABLE.

Thêm model mới thì PHẢI thêm một dòng import vào đây.

Việc import cả cụm cũng giải quyết luôn quan hệ khai báo bằng chuỗi
(`Mapped["Course"]`): SQLAlchemy chỉ tra được tên đó khi class tương ứng đã được
nạp, nên chỉ cần `import app.models` là mọi quan hệ đều phân giải được.
"""

from app.constants.index import CourseStatus, Role, Term
from app.database.base import Base
from app.models.class_student import ClassStudent
from app.models.course import Course
from app.models.school_class import SchoolClass
from app.models.student_profile import StudentProfile
from app.models.subject import Subject
from app.models.teacher_profile import TeacherProfile
from app.models.user import User

__all__ = [
    "Base",
    "ClassStudent",
    "Course",
    "CourseStatus",
    "Role",
    "SchoolClass",
    "StudentProfile",
    "Subject",
    "TeacherProfile",
    "Term",
    "User",
]
