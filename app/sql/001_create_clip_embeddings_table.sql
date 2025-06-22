CREATE TABLE IF NOT EXISTS movie_embeddings_table (
    id SERIAL PRIMARY KEY,
    clip_embedding VECTOR(512) NOT NULL,
    openai_embedding VECTOR(1536) NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_movie_embeddings_cosine_hnsw
  ON movie_embeddings_table
  USING hnsw (clip_embedding vector_cosine_ops);

CREATE INDEX IF NOT EXISTS idx_movie_embeddings_cosine_hnsw
  ON movie_embeddings_table
  USING hnsw (openai_embedding vector_cosine_ops);