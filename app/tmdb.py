import requests
import os


API_TOKEN = os.environ.get("TMDB_API_TOKEN", "a3c51992e634917c008b8f2eea669b3d")
TMDB_IMAGE_BASE = "https://image.tmdb.org/t/p/w500"
API_VERSION = '3'
BASE_URL = 'https://api.themoviedb.org'


def get_poster_path(tmdbid: int) -> str:
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


def get_overview(tmdbid: int) -> str:
    poster_url = None
    tmdb_resp = requests.get(
        f"https://api.themoviedb.org/3/movie/{tmdbid}",
        params={"api_key": API_TOKEN, "language": "en-US"},
        timeout=5
    )
    if tmdb_resp.ok:
        data = tmdb_resp.json()
        path = data.get("overview")
        if path:
            poster_url = f"{TMDB_IMAGE_BASE}{path}"
    return poster_url


def get_movie_data(tmdb_id: int) -> dict:
    base_url = "https://api.themoviedb.org/3/movie"
    url = f"{base_url}/{tmdb_id}"
    params = {
        "api_key": API_TOKEN,
        "language": "en-US"
    }
    resp = requests.get(url, params=params, timeout=10)
    resp.raise_for_status()
    data = resp.json()
    return data

def get_movie_full_metadata(tmdb_id: int) -> dict:  
    meta = {}
    try:
        # Retrieve main movie details
        params = {
            "api_key": API_TOKEN,
            "language": "en-US"
        }

        url = f"{BASE_URL}/{API_VERSION}/movie/{tmdb_id}"
        response = requests.get(url, params=params)

        if response.status_code != 200:
            raise ValueError(f"Failed to fetch movie details for ID {tmdb_id}: {response.status_code} - {response.text}")

        movie_data = response.json()
        meta['title'] = movie_data.get('original_title', 'Unknown Title')
        meta['sinopsis'] = movie_data.get('overview', 'No synopsis available.')
        # Retrieving name of the genre (we don't need its ID)
        meta['genres'] = [g.get('name') for g in movie_data.get('genres', [])]
        meta['poster_path'] = movie_data.get('poster_path')
        meta['avg_rating'] = movie_data.get('vote_average')

        # Retrieve cast info
        url = f"{BASE_URL}/{API_VERSION}/movie/{tmdb_id}/credits"
        response = requests.get(url, params=params)

        if response.status_code != 200:
            raise ValueError(f"Failed to fetch credits for movie ID {tmdb_id}: {response.status_code} - {response.text}")

        credits_data = response.json()
        top_cast = credits_data.get('cast', [])[:5]
        
        # Retrieving name of the actor (we don't need their ID)
        meta['cast'] = [actor.get('name', 'Unknown') for actor in top_cast]

        # Add a link to the tmdb page
        meta['tmdb_url'] = f"https://www.themoviedb.org/movie/{tmdb_id}"

    except requests.exceptions.RequestException as e:
        raise ConnectionError(f"Network-related error occurred while fetching movie metadata: {e}")

    except ValueError as e:
        raise RuntimeError(f"Data error: {e}")

    except Exception as e:
        raise RuntimeError(f"Unexpected error while fetching metadata for movie ID {tmdb_id}: {e}")

    return meta

if __name__ == "__main__":
    data = get_movie_full_metadata(550)
    print(data)