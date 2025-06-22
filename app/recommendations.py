import psycopg2

from db import get_movie_metadata
from tmdb import get_poster_path

SUPPORTED_ALGORITHMS = ["dummy", "clip", "ratings"]

def prepare_recommendations(conn, movie_id, algorithms):
    recommendations = []
    for method in algorithms:
        try:
            recommendation_ids = get_recommendations(conn, movie_id, method)
            algorithm_recommendations = []
            for rec_id in recommendation_ids:
                rec_metadata = get_movie_metadata(conn, rec_id)
                rec_poster_url = None
                if rec_metadata.get('tmdbid'):
                    rec_poster_url = get_poster_path(rec_metadata.get('tmdbid'))
                algorithm_recommendations.append(
                    {   
                        'movie_id': rec_id,
                        'title': rec_metadata.get('title'),
                        'poster_url': rec_poster_url
                    }
                )
            recommendations.append(algorithm_recommendations)
        except Exception:
            continue
    return recommendations

def get_recommendations(conn, movie_id: int, algorithm: str):
    if algorithm not in SUPPORTED_ALGORITHMS:
        raise KeyError(f"Provided algorithm {algorithm} is not supported. Supported list of algorithms: {SUPPORTED_ALGORITHMS}")
    if algorithm == 'dummy':
        return get_dummy_recommendations(movie_id)
    elif algorithm == "clip":
        return get_clip_recommendations(conn, movie_id)
    elif algorithm == "ratings":
        return get_rating_item2item_recommendation(conn, movie_id)
    else:
        raise KeyError(f"Provided algorithm {algorithm} is not supported. Supported list of algorithms: {SUPPORTED_ALGORITHMS}")


def get_dummy_recommendations(movie_id: int):
    return list(range(movie_id+1, movie_id+6))

def get_clip_recommendations(conn, movie_id: int, top_k: int = 5):
    """
    Returns a list of (movie_id, cosine_distance) for the top_k nearest neighbors 
    (by cosine distance) to the embedding of target_movie_id.
    """
    with conn.cursor() as cur:
        cur.execute(
            "SELECT clip_embedding FROM movie_embeddings_table WHERE id = %s;",
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
                movie_embeddings_table
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
    
def get_rating_item2item_recommendation(conn, movie_id: int, top_k: int = 5):
    with conn.cursor() as cur:
        sql = """SELECT
                    similar_movie_id as id
                FROM similar_rating_movies
                where movie_id = %s
                LIMIT %s;
        """
        cur.execute(sql, (movie_id, top_k))
        return [row[0] for row in cur.fetchall()]