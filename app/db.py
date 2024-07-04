from typing import Optional, AsyncGenerator
from contextlib import asynccontextmanager

import bcrypt
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


async def get_connection_from_pool():
    pool = await get_pool()
    async with pool.acquire() as connection:
        try:
            yield connection
        finally:
            await connection.close()


async def get_connection() -> asyncpg.Connection:
    logger.info("Getting connection to Postgres")
    return await asyncpg.connect(settings.pg_dsn)


async def create_user(
    con: asyncpg.Connection, username: str, email: str, password: str, role: str
):
    hashed_password = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt())

    user_id = await con.fetchval(
        """
        INSERT INTO users (username, email, password_hash, role)
        VALUES ($1, $2, $3, $4)
        RETURNING id
        """,
        username,
        email,
        hashed_password,
        role,
    )

    if user_id is None:
        raise Exception("Failed to insert user")

    return user_id


def check_password(password: str, hashed_password: bytes) -> bool:
    return bcrypt.checkpw(password.encode("utf-8"), hashed_password)
