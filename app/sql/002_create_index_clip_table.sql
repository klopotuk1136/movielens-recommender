CREATE INDEX IF NOT EXISTS idx_clip_embeddings_cosine_hnsw
  ON clip_embeddings
  USING hnsw (clip_embedding vector_cosine_ops);