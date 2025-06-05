import os
import requests
import psycopg2
import torch
import clip
from PIL import Image
from io import BytesIO

# ─── CONFIGURATION ───────────────────────────────────────────────────────────────
# Make sure you have these environment variables set (or change to your own literals):
#   TMDB_API_KEY       (not strictly needed for images, but good to have on hand)
#   TMDB_IMAGE_BASE    e.g. "https://image.tmdb.org/t/p/original"  (or “/w500”, etc.)
#   DATABASE_URL       e.g. "postgresql://user:pass@host:port/dbname"
#
# Also, make sure:
#   • You have installed the CLIP package and its dependencies:
#       pip install torch torchvision
#       pip install git+https://github.com/openai/CLIP.git
#   • You have installed psycopg2 (or psycopg2-binary) in order to connect to PostgreSQL:
#       pip install psycopg2-binary
#
# The target table (e.g. "movie_embeddings") must already exist and have a `vector(512)` column.
# Here is an example SQL DDL you might run once:
#
#   CREATE EXTENSION IF NOT EXISTS vector;
#   CREATE TABLE IF NOT EXISTS movie_embeddings (
#       movie_id    INTEGER PRIMARY KEY,
#       embedding   VECTOR(512)
#   );
#
# You can change names/dtypes to suit your own schema, but the column storing the CLIP vector
# must be of type VECTOR(512) (pgvector) so that INSERT … VALUES (%s, %s) with a Python list
# or NumPy array works out of the box.
# ───────────────────────────────────────────────────────────────────────────────────

TMDB_IMAGE_BASE = "https://image.tmdb.org/t/p/w500"
DB_URL = "postgresql://postgres:pass@localhost:5432/postgres"

# Establish CLIP model & preprocessing once at import
device = "cuda" if torch.cuda.is_available() else "cpu"
_clip_model, _clip_preprocess = clip.load("ViT-B/32", device=device)


def fetch_poster_image(poster_path: str) -> Image.Image:
    """
    Given a TMDB poster_path (e.g. "/abcd1234.jpg"), download the image from TMDB 
    and return it as a PIL.Image.
    """
    if not poster_path.startswith(TMDB_IMAGE_BASE):
        raise ValueError(f"poster_path should start with {TMDB_IMAGE_BASE}: got {poster_path!r}")
    resp = requests.get(poster_path, timeout=10)
    resp.raise_for_status()
    return Image.open(BytesIO(resp.content)).convert("RGB")


def get_clip_embedding(img: Image.Image) -> torch.Tensor:
    """
    Given a PIL.Image, run CLIP preprocessing and encode to a 512-dim embedding (torch.Tensor).
    Returns a float32 tensor of shape (512,).
    """
    # Preprocess (centers/crops/resizes) + batch dim
    img_tensor = _clip_preprocess(img).unsqueeze(0).to(device)  # shape: (1, 3, 224, 224)
    with torch.no_grad():
        emb = _clip_model.encode_image(img_tensor)             # shape: (1, 512)
        emb = emb / emb.norm(dim=-1, keepdim=True)             # (optional) L2 normalize
    return emb.squeeze(0).cpu()  # return as: torch.Tensor(shape=(512,), dtype=float32)


def store_embedding_in_pg(movie_id: int, embedding: torch.Tensor, conn: psycopg2.extensions.connection):
    """
    Inserts (or upserts) a 512-dim embedding into Postgres (pgvector).
    Assumes a table called "clip_embeddings(id integer PRIMARY KEY, clip_embeddings vector(512))".
    """
    # Convert torch.Tensor → Python list of floats
    embed_list = embedding.tolist()  # length 512
    
    with conn.cursor() as cur:
        # Upsert: if movie_id already exists, replace; otherwise insert.
        # Change table/column names if yours differ.
        sql = """
        INSERT INTO clip_embeddings (id, clip_embedding)
        VALUES (%s, %s)
        ON CONFLICT (id) DO UPDATE
          SET clip_embedding = EXCLUDED.clip_embedding
        """
        cur.execute(sql, (movie_id, embed_list))
    conn.commit()


def compute_and_store_poster_embedding(movie_id: int, poster_path: str):
    """
    High-level helper: 
      1. Downloads the poster from TMDB
      2. Computes CLIP embedding
      3. Stores it into PostgreSQL (pgvector) under movie_id
      
    Raises on any network/DB/CLIP errors.
    """
    # 1) Download image
    img = fetch_poster_image(poster_path)
    
    # 2) Compute CLIP embedding
    emb = get_clip_embedding(img)  # torch.Tensor of shape (512,)
    
    # 3) Connect to Postgres and store
    conn = psycopg2.connect(DB_URL)
    try:
        store_embedding_in_pg(movie_id, emb, conn)
    finally:
        conn.close()


if __name__ == "__main__":
    # Example usage:
    # Suppose you already have movie_id=123 and poster_path="/xyz789.jpg"
    # You could call:
    #
    #    compute_and_store_poster_embedding(123, "/xyz789.jpg")
    #
    # and it will download the image at
    #    https://image.tmdb.org/t/p/original/xyz789.jpg
    # embed it via CLIP, then upsert into your movie_embeddings table.
    
    # For demonstration, you could parse arguments or just hardcode:
    import argparse

    parser = argparse.ArgumentParser(
        description="Download a TMDB poster, get CLIP embedding, store into Postgres+pgvector"
    )
    parser.add_argument("--movie_id", type=int, required=True, help="The integer movie ID in your DB")
    parser.add_argument("--poster_path", type=str, required=True, help="The TMDB poster_path, e.g. /abc123.jpg")
    args = parser.parse_args()

    compute_and_store_poster_embedding(args.movie_id, args.poster_path)
    print(f"✅ Stored embedding for movie_id={args.movie_id}")
