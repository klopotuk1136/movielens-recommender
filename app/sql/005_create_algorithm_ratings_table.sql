CREATE TABLE IF NOT EXISTS algorithm_ratings (
  id SERIAL PRIMARY KEY,
  movie_id INTEGER NOT NULL,
  algorithm_index INTEGER NOT NULL,
  algorithm_name TEXT,
  score INTEGER NOT NULL CHECK (score BETWEEN 1 AND 5),
  created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW()
);