import asyncio

from app.config.settings import settings
from app.validation.catalog_repository import CatalogRepository


async def main() -> None:
    repo = CatalogRepository(settings.database_url)
    await repo.load_all()

    print(f"entries loaded: {len(repo.cache)}")
    for gloss, entry in repo.cache.items():
        print(f"  {gloss}: {entry.model_dump()}")

    hit = repo.search("CASA")
    print(f"search('CASA') -> {hit}")

    miss = repo.search("EDIFICIO")
    print(f"search('EDIFICIO') -> {miss}")

    miss = repo.search("CUADERNO")
    print(f"search('CUADERNO') -> {miss}")


if __name__ == "__main__":
    asyncio.run(main())
