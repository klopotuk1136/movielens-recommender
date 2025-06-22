-- ratings.csv:
CREATE TABLE IF NOT EXISTS ratings (
  userId    INTEGER      NOT NULL,
  movieId   INTEGER      NOT NULL,
  rating    NUMERIC(2,1) NOT NULL,
  timestamp BIGINT       NOT NULL,
  PRIMARY KEY (userId, movieId)
);

-- tags.csv:
CREATE TABLE IF NOT EXISTS tags (
  userId    INTEGER NOT NULL,
  movieId   INTEGER NOT NULL,
  tag       TEXT    NOT NULL,
  timestamp BIGINT  NOT NULL,
  PRIMARY KEY (userId, movieId, tag, timestamp)
);

CREATE TABLE IF NOT EXISTS genres (
  genre_id SERIAL PRIMARY KEY,
  name     TEXT   NOT NULL UNIQUE
);

-- movies.csv:
CREATE TABLE IF NOT EXISTS movies (
  movieId INTEGER PRIMARY KEY,
  title   TEXT    NOT NULL,
  genre_ids INT[] NOT NULL DEFAULT '{}'
);

CREATE INDEX IF NOT EXISTS idx_movies_title ON movies USING GIST (title gist_trgm_ops);
CREATE INDEX IF NOT EXISTS idx_movies_genre_ids ON movies USING GIN (genre_ids);

-- links.csv:
CREATE TABLE IF NOT EXISTS links (
  movieId INTEGER PRIMARY KEY,
  imdbId  TEXT,
  tmdbId  INTEGER 
);