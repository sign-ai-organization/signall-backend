import asyncpg

from app.domain.models import CatalogEntry


class CatalogRepository:
    def __init__(self, database_url: str) -> None:
        self._database_url = database_url
        self.cache: dict[str, CatalogEntry] = {}

    async def load_all(self) -> None:
        conn = await asyncpg.connect(self._database_url)
        try:
            rows = await conn.fetch("SELECT gloss, glb_animation_path FROM catalog")
        finally:
            await conn.close()

        self.cache = {
            row["gloss"]: CatalogEntry(gloss=row["gloss"], glb_path=row["glb_animation_path"])
            for row in rows
        }

    def search(self, gloss: str) -> CatalogEntry | None:
        return self.cache.get(gloss)
