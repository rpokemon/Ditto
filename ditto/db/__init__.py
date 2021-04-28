import asyncpg

from typing import Optional, NoReturn

from donphan import create_pool, create_types, create_tables, create_views, MaybeAcquire, TYPE_CODECS, OPTIONAL_CODECS

from ..config import CONFIG
from .tables import *
from .scheduler import *


class NoDatabase:
    def __aenter__(self) -> NoReturn:
        raise RuntimeError("No database connection was setup.")


async def setup_database() -> Optional[asyncpg.pool.Pool]:

    if CONFIG.DATABASE.DISABLED:
        return None

    if hasattr(CONFIG.DATABASE, "DSN"):
        dsn = CONFIG.DATABASE.DSN
    else:
        if not getattr(CONFIG.DATABASE, "HOSTNAME", False):
            raise RuntimeError("No valid database login credentials provided, set some with a config override.")

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
