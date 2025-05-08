CREATE TABLE IF NOT EXISTS clip_embeddings (
    id SERIAL PRIMARY KEY,
    clip_embedding VECTOR(512) NOT NULL
);