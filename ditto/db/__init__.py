import asyncpg

from donphan import create_pool, create_types, create_tables, create_views, MaybeAcquire, TYPE_CODECS, OPTIONAL_CODECS

from ..config import CONFIG
from .tables import *
from .scheduler import *


async def setup_database() -> asyncpg.pool.Pool:

    if getattr(CONFIG.DATABASE, "DSN", None):
        dsn = CONFIG.DATABASE.DSN
    else:
        dsn = f"postgres://{CONFIG.DATABASE.USERNAME}:{CONFIG.DATABASE.PASSWORD}@{CONFIG.DATABASE.HOSTNAME}/{CONFIG.DATABASE.DATABASE}"

    # Connect to the DB
    pool = await create_pool(
        dsn, TYPE_CODECS | OPTIONAL_CODECS, server_settings={"application_name": CONFIG.DATABASE.APPLICATION_NAME}
    )
    async with MaybeAcquire(pool=pool) as conn:
        await create_types(conn)
        await create_tables(conn)
        await create_views(conn)

    return pool
