CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS documents (
  id SERIAL PRIMARY KEY,
  url TEXT NOT NULL,
  title TEXT,
  content TEXT NOT NULL,
  meta JSONB,
  embedding vector(384),  -- اندازه را بعداً بر اساس مدل امبدینگ تنظیم می‌کنیم
  created_at TIMESTAMP DEFAULT now()
);

-- ایندکس برداری اولیه (با رشد داده می‌توان lists را بیشتر کرد)
DROP INDEX IF EXISTS idx_documents_embedding;
CREATE INDEX idx_documents_embedding
  ON documents USING ivfflat (embedding vector_l2_ops)
  WITH (lists = 100);

CREATE INDEX IF NOT EXISTS idx_documents_url ON documents (url);

ANALYZE documents;
