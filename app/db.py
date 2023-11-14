from typing import Optional, AsyncGenerator
from contextlib import asynccontextmanager

import asyncpg
from loguru import logger

from app.settings import settings

pool: Optional[asyncpg.Pool] = None


async def create_pool() -> asyncpg.Pool:
    global pool

    if pool is None:
        pool = await asyncpg.create_pool(settings.pg_dsn)
        if pool is None:
            raise Exception("Failed to create pool")
        return pool
    else:
        logger.warning("Attempt to create pool when pool already exists")
        return pool


async def close_pool() -> None:
    global pool

    if pool is None:
        raise Exception("Attempt to close pool with no pool")
    else:
        await pool.close()


async def get_pool() -> asyncpg.Pool:
    global pool

    if pool is None:
        raise Exception("Attempt to get pool with no pool")
    else:
        return pool


@asynccontextmanager
async def get_connection_from_pool() -> AsyncGenerator[asyncpg.Connection, None]:
    pool = await get_pool()
    async with pool.acquire() as connection:
        try:
            yield connection
        finally:
            await connection.close()


async def get_connection() -> asyncpg.Connection:
    logger.info("Getting connection to Postgres")
    return await asyncpg.connect(settings.pg_dsn)


async def create_db_schema(connection: asyncpg.Connection):
    logger.info("Creating DB Schema...")
    await connection.execute(
        """
        CREATE TABLE IF NOT EXISTS tracks(
            id SERIAL PRIMARY KEY,
            name TEXT NOT NULL,
            geometry GEOMETRY(MULTILINESTRING, 4326) NOT NULL,
            activity TEXT
        )
    """
    )
    logger.info("Created DB Schema")
