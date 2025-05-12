import os
from fastapi import FastAPI, Depends, HTTPException
from psycopg2 import pool
import psycopg2
from pgvector.psycopg2 import register_vector

app = FastAPI()

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:pass@db:5432/postgres")

@app.on_event("startup")
def on_startup():
    """
    - Create a psycopg2 connection pool
    - Register the pgvector type on one connection (so the driver knows about VECTOR)
    """
    # minconn=1, maxconn=5 should be plenty for a light workload
    app.state.db_pool = pool.SimpleConnectionPool(
        minconn=1,
        maxconn=5,
        dsn=DATABASE_URL,
    )

    # initialize vector type on one connection
    conn = app.state.db_pool.getconn()
    try:
        register_vector(conn)
    finally:
        app.state.db_pool.putconn(conn)


@app.on_event("shutdown")
def on_shutdown():
    """Close all open connections on shutdown."""
    app.state.db_pool.closeall()


def get_conn():
    """
    Dependency that checks out a connection,
    yields it to the path operation, then returns it.
    """
    conn = app.state.db_pool.getconn()
    try:
        yield conn
    finally:
        app.state.db_pool.putconn(conn)


@app.get("/health")
def health_check(conn=Depends(get_conn)):
    """Simple health check to verify DB connectivity."""
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT 1;")
            cur.fetchone()
        return {"status": "ok"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/documents/{doc_id}/embed")
def upsert_embedding(doc_id: int, embedding: list[float], conn=Depends(get_conn)):
    """
    Insert or update a 1536-dim vector.
    Make sure you’ve already run your CREATE TABLE migrations.
    """
    if len(embedding) != 1536:
        raise HTTPException(
            status_code=400,
            detail=f"Expected 1536-dim vector, got {len(embedding)}",
        )

    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO documents (id, embedding)
            VALUES (%s, %s)
            ON CONFLICT (id) DO UPDATE
              SET embedding = EXCLUDED.embedding;
            """,
            (doc_id, embedding),
        )
    conn.commit()
    return {"status": "saved", "id": doc_id}


@app.post("/search")
def search(embedding: list[float], limit: int = 5, conn=Depends(get_conn)):
    """
    Nearest-neighbour search using cosine distance.
    Assumes you’ve indexed documents.embedding WITH vector_cosine_ops.
    """
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT id, content, embedding <=> %s AS distance
            FROM documents
            ORDER BY distance
            LIMIT %s;
            """,
            (embedding, limit),
        )
        rows = cur.fetchall()

    return [
        {"id": r[0], "content": r[1], "distance": r[2]}
        for r in rows
    ]


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000)