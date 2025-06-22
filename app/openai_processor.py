import os
import openai
from pydantic import BaseModel
import psycopg2
from dotenv import load_dotenv

from db import get_movie_metadata, search_movies_by_title

# Look for a .env file
load_dotenv()

# Extract OpenAI API key
openai.api_key = os.getenv("OPENAI_API_KEY")

DB_URL = "postgresql://postgres:pass@localhost:5432/postgres"


def get_openai_embedding(text: str, model: str = "text-embedding-3-small") -> list[float]:
    """
    Call OpenAI’s Embeddings API and return a 1536-dim list of floats.
    """
    # Request the embedding
    #resp = openai.Embedding.create(
    #    model=model,
    #    input=text
    #)
    client = openai.OpenAI()
    resp = client.embeddings.create(
        input=text,
        model=model
    )
    # Extract embedding
    embedding: list[float] = resp.data[0].embedding
    # L2-normalize
    norm = sum(x * x for x in embedding) ** 0.5
    return [x / norm for x in embedding]


def store_embedding_in_pg(movie_id: int, openai_embedding: list[float], conn: psycopg2.extensions.connection):
    """
    Inserts (or upserts) a 1536-dim OpenAI embedding into Postgres (pgvector).
    Assumes a table called "movie_embeddings_table(
        id integer PRIMARY KEY,
        clip_embedding vector(512),
        openai_embedding vector(1536)
        )".
    """
    with conn:
        with conn.cursor() as cur:
            # Upsert: if movie_id already exists, replace; otherwise insert.
            cur.execute(
                """
                INSERT INTO movie_embeddings_table (id, openai_embedding)
                VALUES (%s, %s)
                ON CONFLICT (id) DO UPDATE
                  SET openai_embedding = EXCLUDED.openai_embedding
                """,
                (movie_id, openai_embedding)
            )


def compute_and_store_description_embedding(movie_id: int, description: str):
    """
    1. Computes the OpenAI embedding for a movie description
    2. Stores it in PostgreSQL (pgvector) under movie_id

    Raises on any network/DB/CLIP errors.
    """
    if not description:
        return

    conn = psycopg2.connect(DB_URL)

    try:
        # Get embedding
        emb = get_openai_embedding(description)
        # Connect to Postgres and store
        
        store_embedding_in_pg(movie_id, emb, conn)
    except Exception as e:
        print(e.with_traceback())
        print(f"Couldn't get an embedding for movie: {movie_id}")
    finally:
        conn.close()

class RecommendationsList(BaseModel):
    recommended_titles: list[str]

def get_chatgpt_predictions(movie_title):
    client = openai.OpenAI()

    response = client.responses.parse(
        model="gpt-4o-2024-08-06",
        input=[
            {
                "role": "system",
                "content": """
                    You are a movie recommender expert.
                    Your goal is to recommend movies you think the user will like if they liked the movie you were provided.
                    Return a list of at least 10 movies that are similar to the one that the user told you.
                """,
            },
            {
                "role": "user",
                "content": f"I like {movie_title}. Can you recommend something similar?"
            },
        ],
        text_format=RecommendationsList,
    )
    recommended_titles = response.output_parsed.recommended_titles
    return recommended_titles


if __name__ == '__main__':
    recommended_titles = get_chatgpt_predictions("Finding Nemo")
    print(recommended_titles)