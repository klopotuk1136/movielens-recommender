import os
import requests
import psycopg2
import torch
import clip
from PIL import Image
from io import BytesIO

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
    conn = psycopg2.connect(DB_URL)
    try:
        # 1) Download image
        if poster_path is None:
            return
        img = fetch_poster_image(poster_path)
        
        # 2) Compute CLIP embedding
        emb = get_clip_embedding(img)  # torch.Tensor of shape (512,)
        
        # 3) Connect to Postgres and store
        store_embedding_in_pg(movie_id, emb, conn)
    except Exception:
        print(f"Couldn't get an embedding for movie: {movie_id}")
    finally:
        conn.close()
