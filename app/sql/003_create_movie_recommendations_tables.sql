CREATE TABLE IF NOT EXISTS similar_rating_movies (
    movie_id   INTEGER      NOT NULL,
    similar_movie_id INTEGER      NOT NULL,
    similarity FLOAT NOT NULL
);
