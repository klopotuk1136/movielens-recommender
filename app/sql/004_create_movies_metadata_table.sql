CREATE TABLE IF NOT EXISTS movies_metadata (
  id           INTEGER       PRIMARY KEY,    
  title        TEXT          NOT NULL,
  sinopsis     TEXT,                         -- movie description
  genres       TEXT[],                       -- array of genre names, e.g. ['Action','Comedy']
  poster_path  TEXT,                         
  avg_rating   NUMERIC(4,3),                 
  actors         TEXT[],                     -- array of cast member names
  tmdb_url     TEXT                          -- full URL to the TMDB page
);
