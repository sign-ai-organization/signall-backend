import asyncpg


async def _warm_up_connection(conn: asyncpg.Connection) -> None:
    # Resolve the pgvector type once per connection, so the first real
    # semantic_cache query does not pay asyncpg's type introspection.
    await conn.fetchval("SELECT $1::vector IS NULL", "[0]")


async def create_pool(
    database_url: str,
    min_size: int,
    max_size: int,
    max_inactive_connection_lifetime: float = 0,
) -> asyncpg.Pool:
    return await asyncpg.create_pool(
        database_url,
        min_size=min_size,
        max_size=max_size,
        max_inactive_connection_lifetime=max_inactive_connection_lifetime,
        init=_warm_up_connection,
    )
