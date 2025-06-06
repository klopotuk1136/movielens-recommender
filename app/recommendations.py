import psycopg2

def get_dummy_recommendations(movie_id):
    return list(range(movie_id+1, movie_id+7))

def get_clip_recommendations(conn, movie_id: int, top_k: int = 5):
    """
    Returns a list of (movie_id, cosine_distance) for the top_k nearest neighbors 
    (by cosine distance) to the embedding of target_movie_id.
    """
    with conn.cursor() as cur:
        cur.execute(
            "SELECT clip_embedding FROM clip_embeddings WHERE id = %s;",
            (movie_id,)
        )
        row = cur.fetchone()
        if row is None:
            raise ValueError(f"No embedding found for id={movie_id}")
        target_embedding = row[0]
        
        sql = """
            SELECT
                id as movie_id
            FROM
                clip_embeddings
            WHERE
                id <> %s
            ORDER BY
                clip_embedding <=> %s ASC
            LIMIT %s;
        """
        cur.execute(sql, (movie_id, target_embedding, top_k))
        return [row[0] for row in cur.fetchall()]
    
def get_openai_recommendations(conn, movie_id: int, top_k: int = 5):
    """
    Returns a list of (movie_id, cosine_distance) for the top_k nearest neighbors 
    (by cosine distance) to the embedding of target_movie_id.
    """
    with conn.cursor() as cur:
        cur.execute(
            "SELECT openai_embedding FROM openai_embeddings WHERE id = %s;",
            (movie_id,)
        )
        row = cur.fetchone()
        if row is None:
            raise ValueError(f"No embedding found for id={movie_id}")
        target_embedding = row[0]
        
        sql = """
            SELECT
                id as movie_id
            FROM
                openai_embeddings
            WHERE
                id <> %s
            ORDER BY
                openai_embedding <=> %s ASC
            LIMIT %s;
        """
        cur.execute(sql, (movie_id, target_embedding, top_k))
        return [row[0] for row in cur.fetchall()]