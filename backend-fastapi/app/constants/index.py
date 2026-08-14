import enum

# Các enum này được dùng trong model, schema,
# và cả frontend. Nếu thay đổi giá trị enum thì
# phải update cả frontend để tránh lỗi decode.

class Role(str, enum.Enum):
    ADMIN = "admin"
    TEACHER = "teacher"
    STUDENT = "student"

class Term(str, enum.Enum):
    """Học kỳ mà lớp học phần này chạy."""
    HK1 = "hk1"
    HK2 = "hk2"
    CA_NAM = "ca_nam"  # môn dạy suốt năm, không chia học kỳ

class CourseStatus(str, enum.Enum):
    ACTIVE = "active"
    ARCHIVED = "archived"  # hết học kỳ: ẩn khỏi danh sách chính, giữ nguyên dữ liệu

