import requests


API_TOKEN = "a3c51992e634917c008b8f2eea669b3d"
TMDB_IMAGE_BASE = "https://image.tmdb.org/t/p/w500"

def get_poster_path(tmdbid: int):
    poster_url = None
    tmdb_resp = requests.get(
        f"https://api.themoviedb.org/3/movie/{tmdbid}",
        params={"api_key": API_TOKEN, "language": "en-US"},
        timeout=5
    )
    if tmdb_resp.ok:
        data = tmdb_resp.json()
        path = data.get("poster_path")
        if path:
            poster_url = f"{TMDB_IMAGE_BASE}{path}"
    return poster_url

    