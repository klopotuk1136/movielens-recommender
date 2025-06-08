import os
from fastapi import FastAPI, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from psycopg2 import pool
from pgvector.psycopg2 import register_vector

from tmdb import get_poster_path, get_movie_full_metadata
from db import get_movie_metadata, search_movies_by_title
from recommendations import prepare_recommendations

app = FastAPI()

templates = Jinja2Templates(directory="static")

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:pass@localhost:5432/postgres")
#DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:pass@db:5432/postgres")

ALGORITHMS = ["clip", "dummy", "clip", "dummy", "dummy", "clip"]


@app.on_event("startup")
def on_startup():
    """
    - Create a psycopg2 connection pool
    - Register the pgvector type on one connection
    """
    app.state.db_pool = pool.SimpleConnectionPool(
        minconn=1,
        maxconn=5,
        dsn=DATABASE_URL,
    )
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

@app.get("/search")
async def search_movies(query: str, conn=Depends(get_conn)):
    print(query)
    if not query:
        raise HTTPException(400, detail="Query cannot be empty")
    resulting_movie_ids = search_movies_by_title(conn, query)
    results = []
    for movie_id in resulting_movie_ids:
        movie_metadata = get_movie_metadata(conn, movie_id)
        poster_url = None
        if movie_metadata.get('tmdbid'):
            poster_url = get_poster_path(movie_metadata.get('tmdbid'))
        movie_metadata['poster_url'] = poster_url

        results.append(movie_metadata)
    return JSONResponse(results)

@app.get("/", response_class=HTMLResponse, include_in_schema=False)
async def root(request: Request):
    """The index page where the user selects the movie ID"""
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/movies/{movie_id}/", response_class=HTMLResponse)
async def get_movie_page(request: Request, movie_id: int, conn=Depends(get_conn)):
    """The movie page where the user sees the movie details as well as recommendations"""
    movie_metadata = get_movie_metadata(conn, movie_id)
    movie_additional_info = get_movie_full_metadata(movie_metadata.get('tmdbid'))

    poster_url = None
    if movie_metadata.get('tmdbid'):
        poster_url = get_poster_path(movie_metadata.get('tmdbid'))

    movie_metadata['poster_url'] = poster_url

    recommendations = prepare_recommendations(conn, movie_id, ALGORITHMS)
    return templates.TemplateResponse("movie.html", {
        "request":     request,
        "movie": movie_additional_info,
        'recommendations': recommendations
    })


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000)