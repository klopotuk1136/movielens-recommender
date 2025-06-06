CREATE TABLE IF NOT EXISTS openai_embeddings (
    id SERIAL PRIMARY KEY,
    openai_embedding VECTOR(1536) NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_openai_embeddings_cosine_hnsw
  ON openai_embeddings
  USING hnsw (openai_embedding vector_cosine_ops);