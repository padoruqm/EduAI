-- EduAI - PostgreSQL extensions
--
-- File nay chi chay MOT LAN duy nhat, luc container postgres khoi tao volume rong
-- (co che /docker-entrypoint-initdb.d). Neu da co du lieu trong volume, file se bi bo qua.
-- Muon chay lai: docker compose down -v && docker compose up -d
--
-- Schema/bang do Alembic quan ly (backend-fastapi/alembic), KHONG viet tay o day.
-- Vector search cho RAG (Module 3-4): luu embedding cua cac chunk tai lieu.
-- Embedding model: OpenAI text-embedding-3-small -> cot kieu vector(1536).
CREATE EXTENSION IF NOT EXISTS vector;

-- Tim kiem gan dung theo ten tai lieu / ten hoc sinh (ILIKE + similarity).
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- gen_random_uuid() cho khoa chinh dang UUID.
CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- Bo qua dau tieng Viet khi search (vi du: "toan" khop "toán").
CREATE EXTENSION IF NOT EXISTS unaccent;