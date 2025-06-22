from fastapi.exceptions import HTTPException

def get_movie_metadata(conn, movie_id: int):
    with conn.cursor() as cur:
        cur.execute(f"SELECT title, genre_ids FROM movies WHERE movieid = {movie_id}")
        row = cur.fetchone()
        if not row:
            raise HTTPException(404, f"Movie {movie_id} not found")
        title, genre_ids = row

        cur.execute("SELECT name FROM genres WHERE genre_id = ANY(%s)", (genre_ids,))
        genres = [g[0] for g in cur.fetchall()]

        cur.execute(f"SELECT imdbid, tmdbid FROM links WHERE movieid = {movie_id}")
        link = cur.fetchone()
        imdbid, tmdbid = link if link else (None, None)

    return {
        "id":         movie_id,
        "title":      title,
        "genres":     genres,
        "imdbid":     imdbid,
        "tmdbid":     tmdbid
    }

def search_movies_by_title(conn, query, limit=10):
    with conn.cursor() as cur:
        cur.execute("""
            SELECT movieid AS id
              FROM movies
             ORDER BY title <-> %s
             LIMIT %s;
        """, (query, limit))
        return [row[0] for row in cur.fetchall()]