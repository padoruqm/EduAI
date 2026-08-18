# Hạ tầng chạy bằng Docker

Tài liệu này trả lời hai câu hỏi: **tại sao project bắt buộc phải có Docker**, và **gõ lệnh gì để chạy**.

Đọc kèm: [`ARCHITECTURE.md`](ARCHITECTURE.md) (cây thư mục), [`MIGRATION.md`](MIGRATION.md) (Alembic — cần DB chạy trước mới làm được).

---

## 0. Vì sao không cài PostgreSQL thẳng vào máy?

Cài trực tiếp thì vẫn chạy được, nhưng sẽ vấp bốn thứ:

| Vấn đề | Cài thẳng vào máy | Dùng Docker |
|---|---|---|
| **Extension `pgvector`** | Phải build/cài riêng, mỗi OS một kiểu. Thiếu nó là cột `vector(1536)` của Module 3-4 không tạo được | Image `pgvector/pgvector:pg16` đã có sẵn |
| **Đồng đội chạy khác version** | Máy A dùng PG 17, máy B dùng PG 14 → migration chạy được ở đây, lỗi ở kia | Ai cũng đúng PG 16, ghim trong `docker-compose.yaml` |
| **4 service, không chỉ DB** | Còn Redis, RabbitMQ, MinIO — cài tay từng cái, cấu hình từng cái | Một lệnh `docker compose up -d` |
| **Gỡ ra khi hỏng** | Gỡ sạch PostgreSQL khỏi macOS khá phiền | `docker compose down -v` là biến mất hoàn toàn |

Điểm mấu chốt: `docker-compose.yaml` **chính là tài liệu mô tả hạ tầng**. Đọc file đó là biết hệ thống cần gì, không phải hỏi ai.

> **Docker chỉ chạy HẠ TẦNG, không chạy code của bạn.** Ở giai đoạn hiện tại, backend FastAPI và frontend Vue vẫn chạy trực tiếp trên máy (`uvicorn`, `npm run dev`). Các service `api` / `worker` / `beat` / `frontend` / `nginx` đang bị comment ở cuối `docker-compose.yaml`, sẽ bật từ Tuần 2 khi đã có Dockerfile.

---

## 1. Trong `docker-compose.yaml` có gì

| Service | Image | Cổng (máy → container) | Dùng để làm gì |
|---|---|---|---|
| `postgres` | `pgvector/pgvector:pg16` | `5432` | Dữ liệu nghiệp vụ **và** vector embedding, chung một DB |
| `redis` | `redis:7-alpine` | `6379` | Cache câu trả lời AI, refresh token, rate limit, Celery result backend |
| `rabbitmq` | `rabbitmq:3.13-management-alpine` | `5672`, `15672` (UI) | Broker cho tác vụ nặng: embedding tài liệu, chấm bài hàng loạt |
| `minio` | `minio/minio:latest` | `9000` (API), `9001` (Console) | Lưu file gốc: PDF, Word, Slide, video, ảnh bài làm. Tương thích S3 |
| `minio-init` | `minio/mc:latest` | — | Chạy một lần rồi thoát, tạo sẵn 3 bucket |

> **`minio-init` hiện `Exited (0)` là ĐÚNG**, không phải lỗi. Nó là container dùng-một-lần: tạo bucket xong thì tự tắt.

Tất cả nối chung mạng `eduai-net`, nên **giữa các container** chúng gọi nhau bằng tên service (`postgres:5432`), còn **từ máy bạn** thì gọi qua `localhost:5432`.

### Credential lấy từ đâu

`docker-compose.yaml` không chứa mật khẩu nào. Nó đọc từ [`.env`](../.env) ở thư mục gốc:

```
project_EduAI/.env              → docker compose đọc (POSTGRES_PASSWORD, REDIS_PASSWORD...)
backend-fastapi/.env            → FastAPI + Alembic đọc (DATABASE_URL, DATABASE_URL_SYNC...)
```

Hai file **khác nhau** nhưng mật khẩu phải **khớp nhau**. `POSTGRES_PASSWORD` ở file gốc chính là mật khẩu nằm trong `DATABASE_URL_SYNC` ở file backend. Lệch nhau là `password authentication failed`.

---

## 2. Chạy lần đầu

```bash
# 1. Bật Docker Desktop (nó KHÔNG tự chạy cùng máy)
open -a Docker

# 2. Tạo file credential nếu chưa có
cd /Users/quangminh/Desktop/project_EduAI
cp .env.example .env                      # rồi điền các giá trị CHANGE_ME

# 3. Dựng toàn bộ hạ tầng
docker compose up -d

# 4. Xem trạng thái, chờ tới khi cột STATUS ghi (healthy)
docker compose ps
```

`-d` = detached, chạy nền và trả lại con trỏ dòng lệnh. Bỏ `-d` thì log đổ thẳng ra màn hình và `Ctrl-C` sẽ tắt hết.

Lần đầu phải tải image nên mất vài phút. Những lần sau là vài giây.

Muốn chạy **chỉ mỗi Postgres** (đủ để làm việc với Alembic, đỡ tốn RAM):

```bash
docker compose up -d postgres
```

### Chuyện xảy ra ở lần chạy đầu tiên

Khi volume `eduai_postgres_data` còn rỗng, Postgres tự làm hai việc:

1. Tạo user + database theo `POSTGRES_USER` / `POSTGRES_PASSWORD` / `POSTGRES_DB`
2. Chạy mọi file `.sql` trong [`database/init/`](../database/init/) — hiện có [`01_extensions.sql`](../database/init/01_extensions.sql) bật `vector`, `pg_trgm`, `pgcrypto`, `unaccent`

> **Cả hai việc trên CHỈ chạy đúng một lần.** Volume đã có dữ liệu thì Postgres bỏ qua hoàn toàn. Nên đổi `POSTGRES_PASSWORD` trong `.env` sau đó **không** đổi được mật khẩu DB thật, và thêm file vào `database/init/` cũng không được chạy. Muốn áp dụng thì phải xoá volume: `docker compose down -v` (mất sạch dữ liệu).
>
> Đây cũng là lý do **không** viết `CREATE TABLE` vào `database/init/` — bảng thuộc quyền quản lý của Alembic. Xem [`MIGRATION.md`](MIGRATION.md).

---

## 3. Lệnh dùng hằng ngày

```bash
docker compose up -d              # bật (đã tắt trước đó)
docker compose ps                 # service nào đang chạy, healthy chưa
docker compose stop               # tắt, GIỮ nguyên dữ liệu
docker compose down               # tắt + xoá container, VẪN giữ dữ liệu (volume còn)
docker compose logs -f postgres   # xem log, Ctrl-C để thoát
docker compose restart postgres   # khởi động lại một service
```

Vào thẳng database bằng psql trong container (không cần cài psql trên máy):

```bash
docker compose exec postgres psql -U eduai -d eduai
```

Trong psql: `\dt` liệt kê bảng, `\dx` liệt kê extension, `\q` để thoát.

### Lệnh cần cân nhắc

```bash
docker compose down -v            # XOÁ SẠCH cả volume → mất toàn bộ dữ liệu
```

Dùng khi muốn về trạng thái trắng tinh: đổi mật khẩu trong `.env`, thêm file vào `database/init/`, hoặc DB đã rối quá. Sau lệnh này phải chạy lại migration từ đầu (`alembic upgrade head`).

---

## 4. Dữ liệu nằm ở đâu

Dữ liệu **không** nằm trong container mà nằm ở volume riêng, nên xoá container không mất gì:

| Volume | Chứa |
|---|---|
| `eduai_postgres_data` | Toàn bộ database |
| `eduai_redis_data` | Cache AI (bật AOF nên restart không mất) |
| `eduai_rabbitmq_data` | Hàng đợi |
| `eduai_minio_data` | File đã upload |

```bash
docker volume ls --filter name=eduai
```

Chỉ có `down -v` mới xoá chúng. `stop`, `down`, restart máy đều an toàn.

---

## 5. Giao diện web có sẵn

| Địa chỉ | Là gì | Đăng nhập bằng |
|---|---|---|
| http://localhost:15672 | RabbitMQ Management | `RABBITMQ_DEFAULT_USER` / `RABBITMQ_DEFAULT_PASS` trong `.env` |
| http://localhost:9001 | MinIO Console | `MINIO_ROOT_USER` / `MINIO_ROOT_PASSWORD` trong `.env` |

---

## 6. Gỡ rối

### `Connection refused` ở cổng 5432

Container không chạy. Nguyên nhân phổ biến nhất: **Docker Desktop đã tắt** — nó không tự bật khi khởi động máy, nên lỗi này quay lại sau mỗi lần reboot.

```bash
docker info                       # báo "Cannot connect to the Docker daemon" = Desktop đang tắt
open -a Docker                    # đợi ~20-30s
docker compose up -d postgres
```

### `port is already allocated` / `address already in use`

Có thứ khác đang giữ cổng đó. Thủ phạm hay gặp trên macOS là PostgreSQL cài bằng Homebrew:

```bash
lsof -nP -iTCP:5432 -sTCP:LISTEN  # xem ai đang giữ cổng
brew services stop postgresql@17  # tắt bản brew đi
```

Nếu cần giữ cả hai, đổi cổng phía máy trong [`.env`](../.env) — `POSTGRES_PORT=5433` — rồi sửa cổng tương ứng trong `backend-fastapi/.env` (`DATABASE_URL` và `DATABASE_URL_SYNC`). Đổi biến này **không** cần xoá volume vì nó chỉ ánh xạ cổng ra ngoài, không đụng dữ liệu.

### `password authentication failed for user "eduai"`

Mật khẩu trong `backend-fastapi/.env` không khớp mật khẩu container đã tạo lúc khởi tạo volume. Đối chiếu `POSTGRES_PASSWORD` ở `.env` gốc với chuỗi trong `DATABASE_URL_SYNC`.

Lưu ý: sửa `POSTGRES_PASSWORD` rồi restart **không** đổi được mật khẩu DB (xem §2). Muốn đổi thật thì hoặc `docker compose down -v`, hoặc đổi ngay trong DB:

```bash
docker compose exec postgres psql -U eduai -d eduai -c "ALTER USER eduai WITH PASSWORD 'matkhaumoi';"
```

### `docker compose ps` thấy `(unhealthy)` hoặc restart liên tục

```bash
docker compose logs postgres      # đọc log để biết lý do
```

### Container chạy rồi mà `alembic` vẫn lỗi

Nếu lỗi là `ModuleNotFoundError` chứ không phải lỗi kết nối thì **không liên quan tới Docker**. Đó là chưa activate virtualenv — lệnh `alembic` đang bắt phải bản cài toàn cục:

```bash
cd backend-fastapi
source .venv/bin/activate
which alembic                     # phải thấy .venv trong đường dẫn
```

---

## 7. Quy trình mỗi ngày

```bash
# Bật hạ tầng
cd /Users/quangminh/Desktop/project_EduAI
docker compose up -d postgres

# Làm việc với backend
cd backend-fastapi
source .venv/bin/activate
alembic current
uvicorn app.main:app --reload
```

Xong việc thì `docker compose stop` cho nhẹ máy, hoặc cứ để đấy — `restart: unless-stopped` sẽ tự bật lại cùng Docker Desktop ở lần sau.
