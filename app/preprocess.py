import os
import pandas as pd
import psycopg2
import glob
from psycopg2 import extras
from tqdm import tqdm

from clip_processor import compute_and_store_poster_embedding
from tmdb import get_poster_path

DB_URL = "postgresql://postgres:pass@localhost:5432/postgres"

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Paths to CSV files
DATA_PATH = os.path.join(ROOT, r"data\ml-20m\ml-20m")
MOVIES_CSV = os.path.join(DATA_PATH, 'movies.csv')
RATINGS_CSV = os.path.join(DATA_PATH, 'ratings.csv')
TAGS_CSV   = os.path.join(DATA_PATH, 'tags.csv')
LINKS_CSV  = os.path.join(DATA_PATH, 'links.csv')


def connect():
    return psycopg2.connect(DB_URL)


def run_migrations(cur):
    # Makes sure that the extension is loaded before all other queries
    cur.execute("CREATE EXTENSION IF NOT EXISTS vector;")

    for path in sorted(glob.glob(os.path.join(ROOT, "app", "sql", "*.sql"))):
        sql = open(path).read()
        cur.execute(sql)


def insert_genres(cur, genre_list):
    """
    1. Truncate the genres table and bulk-insert all genres from genre_list.
    """
    print(f"Inserting {len(genre_list)} genres into genres table...")
    cur.execute("TRUNCATE genres RESTART IDENTITY CASCADE;")
    extras.execute_values(
        cur,
        "INSERT INTO genres (name) VALUES %s",
        [(name,) for name in genre_list]
    )

def fetch_genre_mapping(cur):
    """
    2. Query the genres table and build a mapping {genre_name: genre_id}.
    Returns:
        dict: mapping from genre name to genre_id
    """
    cur.execute("SELECT genre_id, name FROM genres;")
    return {name: gid for (gid, name) in cur.fetchall()}

def insert_movies(cur, movies_raw, mapping):
    """
    3. Prepare a DataFrame of movies with an array of genre_ids,
       then truncate and bulk-insert into the movies table.
    """
    print("Preparing movies data with genre_ids array...")
    movies_df = pd.DataFrame({
        'movieId': movies_raw['movieId'],
        'title':    movies_raw['title'],
        'genre_ids': movies_raw['genres'].apply(
            lambda s: [mapping[g] for g in s.split('|') if g in mapping]
        )
    })

    print(f"Inserting {len(movies_df)} movies into movies table...")
    cur.execute("TRUNCATE movies RESTART IDENTITY CASCADE;")

    movie_values = [
        (int(row.movieId), row.title, row.genre_ids)
        for row in movies_df.itertuples(index=False)
    ]
    extras.execute_values(
        cur,
        "INSERT INTO movies (movieid, title, genre_ids) VALUES %s",
        movie_values,
        template="(%s, %s, %s)"
    )

def copy_tags(cur, tags_csv_path):
    """
    4. Truncate the tags table and bulk-load from a CSV using COPY.
    """
    print("Copying tags (utf-8 decoding)...")
    cur.execute("TRUNCATE tags RESTART IDENTITY CASCADE;")
    with open(tags_csv_path, 'r', encoding='utf-8', errors='replace') as f:
        cur.copy_expert(
            "COPY tags (userid, movieid, tag, timestamp) FROM STDIN WITH CSV HEADER",
            f
        )

def copy_links(cur, links_csv_path):
    """
    5. Truncate the links table and bulk-load from a CSV using COPY.
    """
    print("Copying links (utf-8 decoding)...")
    cur.execute("TRUNCATE links RESTART IDENTITY CASCADE;")
    with open(links_csv_path, 'r', encoding='utf-8', errors='replace') as f:
        cur.copy_expert(
            "COPY links (movieid, imdbid, tmdbid) FROM STDIN WITH CSV HEADER",
            f
        )

def preprocess_clip_embeddings(cur, truncate=False, limit=None):

    if truncate:
        cur.execute("TRUNCATE clip_embeddings CASCADE;")
    print("Processing movie poster paths")

    cur.execute("SELECT count(*) from links")
    movie_number = cur.fetchone()[0]

    sql = "SELECT movieid, tmdbid FROM links"
    if limit:
        sql += f' limit {limit}'
        movie_number = limit
    cur.execute(sql)

    for movieid, tmdbid in tqdm(cur, total=movie_number):
        poster_path = get_poster_path(tmdbid)
        compute_and_store_poster_embedding(movieid, poster_path)


# Main load logic
def main():
    conn = connect()

    conn.autocommit = True
    cur = conn.cursor()
    
    run_migrations(cur)

    # Read raw movies to extract genres
    print("Reading movies CSV to extract genres...")
    movies_raw = pd.read_csv(MOVIES_CSV)
    # Getting all distinct genres from the movie list
    all_genres = set(g for sub in movies_raw['genres'].str.split('|') for g in sub if g != '(no genres listed)')
    genre_list = sorted(all_genres)

    # 1. Load genres lookup
    insert_genres(cur, genre_list)

    # 2. Fetch mapping of genre name -> genre_id
    genre_mapping = fetch_genre_mapping(cur)

    # 3. Load movies with genre_ids array
    insert_movies(cur, movies_raw, genre_mapping)

    # 4. Bulk load tags
    copy_tags(cur, TAGS_CSV)

    # 5. Bulk load links
    copy_links(cur, LINKS_CSV)

    # 6. Calculate clip embeddings for posters and save them
    preprocess_clip_embeddings(cur)
    cur.close()
    conn.close()
    print("MovieLens data loaded successfully.")

if __name__ == '__main__':
    main()