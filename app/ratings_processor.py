import psycopg2
import pandas as pd
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity


def calculate_rating_similarities(conn):
    query = "SELECT movieid, userid, rating FROM ratings"
    ratings_df = pd.read_sql(query, conn)

    sample_users = sample_k_users(ratings_df, user_count=100_000)
    ratings_df = ratings_df[ratings_df['userid'].isin(sample_users)]

    rating_matrix = ratings_df.pivot(index='movieid', columns='userid', values='rating').astype('float16') 
    rating_matrix = rating_matrix.apply(
        lambda row: row.fillna(row.mean()),
        axis=1
    ) # Fill nulls with row-wise mean values

    print("Calculating pairwise similarities...")
    cosine_sim = cosine_similarity(rating_matrix)

    return rating_matrix, cosine_sim

def sample_k_users(ratings_df, user_count=20000):
    all_users = ratings_df['userid'].unique()
    sample_users = np.random.choice(all_users, size=20_000, replace=False)
    return sample_users

def get_similar_movies(rating_matrix, cosine_sim):
    similar_movies = {}
    movie_ids = rating_matrix.index.tolist()
    print("Searching for similar movies...")
    for idx, movie_id in enumerate(movie_ids):
        sim_scores = cosine_sim[idx]
        sim_indices = np.argsort(-sim_scores)[1:6]
        similar_movies[movie_id] = [(movie_ids[i], sim_scores[i]) for i in sim_indices]
    
    return similar_movies

def store_similar_movies_in_pg(conn, similar_movies):
    cur = conn.cursor()

    insert_query = """
    INSERT INTO similar_rating_movies (movie_id, similar_movie_id, similarity)
    VALUES (%s, %s, %s)
    """
    
    print("Inserting similar movies to database...")
    for movie_id, sim_list in similar_movies.items():
        for sim_movie_id, similarity in sim_list:
            cur.execute(insert_query, (movie_id, sim_movie_id, float(similarity)))

    conn.commit()
    cur.close()
    conn.close()

def compute_and_store_rating_similar_movies(conn):
    rating_matrix, cosine_sim = calculate_rating_similarities(conn)
    similar_movies = get_similar_movies(rating_matrix, cosine_sim)
    store_similar_movies_in_pg(conn, similar_movies)

def main():
    DB_URL = "postgresql://postgres:pass@localhost:5432/postgres"

    conn = psycopg2.connect(DB_URL)
    compute_and_store_rating_similar_movies(conn)


if __name__ == '__main__':
    main()