from fastapi.exceptions import HTTPException

def get_movie_metadata(conn, movie_id: int):
    with conn.cursor() as cur:
        cur.execute("SELECT title, genre_ids FROM movies WHERE movieid = %s", (movie_id,))
        row = cur.fetchone()
        if not row:
            raise HTTPException(404, f"Movie {movie_id} not found")
        title, genre_ids = row

        cur.execute("SELECT name FROM genres WHERE genre_id = ANY(%s)", (genre_ids,))
        genres = [g[0] for g in cur.fetchall()]

        cur.execute("SELECT imdbid, tmdbid FROM links WHERE movieid = %s", (movie_id,))
        link = cur.fetchone()
        imdbid, tmdbid = link if link else (None, None)

    return {
        "id":         movie_id,
        "title":      title,
        "genres":     genres,
        "imdbid":     imdbid,
        "tmdbid":     tmdbid
    }