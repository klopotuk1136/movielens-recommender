CREATE TABLE IF NOT EXISTS ratings (
  userId    INTEGER      NOT NULL,
  movieId   INTEGER      NOT NULL,
  rating    NUMERIC(2,1) NOT NULL,    -- half-star increments 0.5–5.0
  timestamp BIGINT       NOT NULL,    -- seconds since 1970-01-01 UTC
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
  title   TEXT    NOT NULL,  -- includes year in parentheses
  genre_ids INT[] NOT NULL DEFAULT '{}'
);

CREATE INDEX IF NOT EXISTS idx_movies_genre_ids ON movies USING GIN (genre_ids);

-- links.csv: external IDs for each movie
CREATE TABLE IF NOT EXISTS links (
  movieId INTEGER PRIMARY KEY,
  imdbId  TEXT,
  tmdbId  INTEGER 
);