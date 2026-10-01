import asyncpg

from app.domain.models import CatalogEntry


class CatalogRepository:
    def __init__(self, pool: asyncpg.Pool) -> None:
        self._pool = pool
        self.cache: dict[str, CatalogEntry] = {}

    async def load_all(self) -> None:
        rows = await self._pool.fetch("SELECT gloss, glb_animation_path FROM catalog")

        self.cache = {
            row["gloss"]: CatalogEntry(gloss=row["gloss"], glb_path=row["glb_animation_path"])
            for row in rows
        }

    def search(self, gloss: str) -> CatalogEntry | None:
        return self.cache.get(gloss)
