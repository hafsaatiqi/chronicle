import httpx

from app.models.enums import Medium
from app.schemas.work import WorkCreate

OPEN_LIBRARY_SEARCH_URL = "https://openlibrary.org/search.json"
OPEN_LIBRARY_COVER_URL = "https://covers.openlibrary.org/b/id/{cover_id}-M.jpg"


class OpenLibraryService:
    async def search(self, query: str) -> list[WorkCreate]:
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(OPEN_LIBRARY_SEARCH_URL, params={"q": query, "limit": 10})
                response.raise_for_status()
        except httpx.HTTPError:
            return []

        docs = response.json().get("docs", [])
        return [self._map_doc(doc) for doc in docs if self._map_doc(doc) is not None]

    def _map_doc(self, doc: dict) -> WorkCreate | None:
        external_id = doc.get("key")
        title = doc.get("title")
        if not external_id or not title:
            return None

        authors = doc.get("author_name") or []
        creator = ", ".join(authors) if authors else "Unknown"

        cover_id = doc.get("cover_i")
        cover_url = OPEN_LIBRARY_COVER_URL.format(cover_id=cover_id) if cover_id else None

        return WorkCreate(
            medium=Medium.BOOK.value,
            title=title,
            creator=creator,
            external_id=external_id,
            synopsis=None,
            cover_url=cover_url,
        )
