import os
import pandas as pd
import psycopg2
import glob
from psycopg2 import extras

DB_URL = "postgresql://postgres:pass@localhost:5432/postgres"

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Paths to CSV files
DATA_PATH = os.path.join(ROOT, r"data\ml-20m\ml-20m")
MOVIES_CSV = os.path.join(DATA_PATH, 'movies.csv')
RATINGS_CSV = os.path.join(DATA_PATH, 'ratings.csv')
TAGS_CSV   = os.path.join(DATA_PATH, 'tags.csv')
LINKS_CSV  = os.path.join(DATA_PATH, 'links.csv')


# Read raw movies to extract genres
print("Reading movies CSV to extract genres...")
movies_raw = pd.read_csv(MOVIES_CSV)
# Getting all distinct genres from the movie list
all_genres = set(g for sub in movies_raw['genres'].str.split('|') for g in sub if g != '(no genres listed)')
genre_list = sorted(all_genres)

def connect():
    return psycopg2.connect(DB_URL)



def run_migrations(cur):
    # Makes sure that the extension is loaded before all other queries
    cur.execute("CREATE EXTENSION IF NOT EXISTS vector;")

    for path in sorted(glob.glob(os.path.join(ROOT, "app", "sql", "*.sql"))):
        sql = open(path).read()
        cur.execute(sql)

# Main load logic
def main():
    conn = connect()

    conn.autocommit = True
    cur = conn.cursor()
    
    run_migrations(cur)

    # 1. Load genres lookup
    print(f"Inserting {len(genre_list)} genres into genres table...")
    cur.execute("TRUNCATE genres RESTART IDENTITY CASCADE;")
    extras.execute_values(
        cur,
        "INSERT INTO genres (name) VALUES %s",
        [(name,) for name in genre_list]
    )

    # Fetch mapping of name -> genre_id
    cur.execute("SELECT genre_id, name FROM genres;")
    mapping = {name: gid for gid, name in cur.fetchall()}

    # 2. Load movies with genre_ids array
    print("Preparing movies data with genre_ids array...")
    movies_df = pd.DataFrame({
        'movieId': movies_raw['movieId'],
        'title': movies_raw['title'],
        'genre_ids': movies_raw['genres'].apply(lambda s: [mapping[g] for g in s.split('|') if g in mapping])
    })
    print(f"Inserting {len(movies_df)} movies into movies table...")
    cur.execute("TRUNCATE movies RESTART IDENTITY CASCADE;")

    movie_values = [(
        int(row.movieId),
        row.title,
        row.genre_ids
    ) for row in movies_df.itertuples(index=False)]
    extras.execute_values(
        cur,
        "INSERT INTO movies (movieid, title, genre_ids) VALUES %s",
        movie_values,
        template="(%s, %s, %s)"
    )


    # 4. Bulk load tags
    print("Copying tags (utf-8 decoding)...")
    cur.execute("TRUNCATE tags RESTART IDENTITY CASCADE;")
    with open(TAGS_CSV, 'r', encoding='utf-8', errors='replace') as f:
        cur.copy_expert(
            "COPY tags (userid, movieid, tag, timestamp) FROM STDIN WITH CSV HEADER",
            f
        )

    # 5. Bulk load links
    print("Copying links (utf-8 decoding)...")
    cur.execute("TRUNCATE links RESTART IDENTITY CASCADE;")
    with open(LINKS_CSV, 'r', encoding='utf-8', errors='replace') as f:
        cur.copy_expert(
            "COPY links (movieid, imdbid, tmdbid) FROM STDIN WITH CSV HEADER",
            f
        )

    cur.close()
    conn.close()
    print("MovieLens data loaded successfully.")

if __name__ == '__main__':
    main()