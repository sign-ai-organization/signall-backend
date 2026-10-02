import asyncio

from app.config.settings import settings
from app.persistence.database import create_pool
from app.domain.models import PhraseType, Segment
from app.validation.catalog_repository import CatalogRepository
from app.validation.validator_service_impl import ValidatorServiceImpl


async def main() -> None:
    pool = await create_pool(settings.database_url, settings.db_pool_min_size, settings.db_pool_max_size)
    repo = CatalogRepository(pool)
    await repo.load_all()
    await pool.close()
    validator = ValidatorServiceImpl(repo)

    segments = [
        Segment(type=PhraseType.AFFIRMATIVE, glosses=["CASA", "NO_EXISTE"]),
        Segment(type=PhraseType.NEGATIVE, glosses=["COMER"]),
    ]

    validated_segments = validator.validate(segments)
    for validated_segment in validated_segments:
        print(validated_segment.model_dump())


if __name__ == "__main__":
    asyncio.run(main())
