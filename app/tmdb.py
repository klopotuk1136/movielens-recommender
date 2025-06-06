import requests
import os


API_TOKEN = os.environ.get("TMDB_API_TOKEN", "a3c51992e634917c008b8f2eea669b3d")
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

def get_synopsis_from_tmdb(tmdb_id: int) -> str:
    base_url = "https://api.themoviedb.org/3/movie"
    url = f"{base_url}/{tmdb_id}"
    params = {
        "api_key": API_TOKEN,
        "language": "en-US"
    }
    resp = requests.get(url, params=params, timeout=10)
    resp.raise_for_status()
    data = resp.json()
    if "overview" not in data:
        raise ValueError(f"No 'overview' field in TMDB response for ID {tmdb_id}. Full response:\n{data!r}")
    return data["overview"] or ""  # If overview is None, return empty string

if __name__ == "__main__":
    data = get_synopsis_from_tmdb(550)
    print(data)