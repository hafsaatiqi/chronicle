import httpx

from app.core.config import settings
from app.models.enums import Medium
from app.schemas.work import WorkCreate

TMDB_BASE_URL = "https://api.themoviedb.org/3"
TMDB_POSTER_URL = "https://image.tmdb.org/t/p/w300{poster_path}"


class TMDBService:
    async def search(self, query: str) -> list[WorkCreate]:
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(
                    f"{TMDB_BASE_URL}/search/movie",
                    params={"api_key": settings.tmdb_api_key, "query": query},
                )
                response.raise_for_status()
                docs = response.json().get("results", [])

                genre_map = await self._get_genre_map(client)
                return [await self._map_doc(client, doc, genre_map) for doc in docs if self._is_mappable(doc)]
        except httpx.HTTPError:
            return []

    def _is_mappable(self, doc: dict) -> bool:
        return doc.get("id") is not None and bool(doc.get("title"))

    async def _get_genre_map(self, client: httpx.AsyncClient) -> dict[int, str]:
        response = await client.get(f"{TMDB_BASE_URL}/genre/movie/list", params={"api_key": settings.tmdb_api_key})
        response.raise_for_status()
        return {genre["id"]: genre["name"] for genre in response.json().get("genres", [])}

    async def _map_doc(self, client: httpx.AsyncClient, doc: dict, genre_map: dict[int, str]) -> WorkCreate:
        tmdb_id = doc["id"]
        poster_path = doc.get("poster_path")
        cover_url = TMDB_POSTER_URL.format(poster_path=poster_path) if poster_path else None
        subjects = [genre_map[gid] for gid in doc.get("genre_ids", []) if gid in genre_map]

        return WorkCreate(
            medium=Medium.FILM.value,
            title=doc["title"],
            creator=await self._get_director(client, tmdb_id) or "Unknown",
            external_id=str(tmdb_id),
            synopsis=doc.get("overview") or None,
            cover_url=cover_url,
            subjects=subjects,
        )

    async def _get_director(self, client: httpx.AsyncClient, tmdb_id: int) -> str | None:
        response = await client.get(
            f"{TMDB_BASE_URL}/movie/{tmdb_id}/credits", params={"api_key": settings.tmdb_api_key}
        )
        if response.status_code != 200:
            return None
        director = next(
            (member for member in response.json().get("crew", []) if member.get("job") == "Director"), None
        )
        return director.get("name") if director else None
