from typing import Any, NoReturn

import asyncpg
from discord.utils import MISSING
from donphan import OPTIONAL_CODECS, MaybeAcquire, create_db, create_pool

from .emoji import *
from .scheduler import *
from .tables import *


class NoDatabase(MaybeAcquire):
    def __init__(self, *args: Any, **kwargs: Any):
        pass

    def __aenter__(self) -> NoReturn:
        raise RuntimeError("No database connection was setup.")

    def __aexit__(self, *exc) -> NoReturn:
        raise RuntimeError("No database connection was setup.")


async def setup_database() -> asyncpg.pool.Pool:
    # this is a hack because >circular imports<
    from ..config import CONFIG

    if CONFIG.DATABASE.DISABLED:
        return MISSING

    if hasattr(CONFIG.DATABASE, "DSN"):
        dsn = CONFIG.DATABASE.DSN
    else:
        if not getattr(CONFIG.DATABASE, "HOSTNAME", False):
            raise RuntimeError("No valid database login credentials provided, set some with a config override.")

        dsn = f"postgres://{CONFIG.DATABASE.USERNAME}:{CONFIG.DATABASE.PASSWORD}@{CONFIG.DATABASE.HOSTNAME}/{CONFIG.DATABASE.DATABASE}"

    # Connect to the DB
    pool = await create_pool(dsn, OPTIONAL_CODECS, server_settings={"application_name": CONFIG.APP_NAME}, set_as_default=True)
    async with MaybeAcquire(pool=pool) as connection:
        await create_db(connection, if_not_exists=True, with_transaction=False)
    return pool
