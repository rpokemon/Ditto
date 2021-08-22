import asyncio
import datetime
from io import DEFAULT_BUFFER_SIZE
from typing import Any, Optional, Union

import discord

from ..types import User
from .time import normalise_timedelta

MISSING: Any = discord.utils.MISSING

__all__ = (
    "user_in_guild",
    "fetch_audit_log_entry",
)


SLEEP_FOR = 5


async def fetch_audit_log_entry(
    guild: discord.Guild,
    *,
    time: Optional[datetime.datetime] = None,
    user: Optional[User] = None,
    moderator: Optional[User] = None,
    action: Optional[discord.AuditLogAction] = None,
    delta: Union[float, datetime.timedelta] = 1,
    retry: int = 3,
) -> Optional[discord.AuditLogEntry]:

    time = time or datetime.datetime.now(datetime.timezone.utc)
    delta = normalise_timedelta(delta)

    async for entry in guild.audit_logs(action=action, user=moderator):  # type: ignore
        if (time - entry.created_at) < delta and (user is None or entry.target == user):
            return entry

    if retry > 0:
        await asyncio.sleep(SLEEP_FOR)
        return await fetch_audit_log_entry(
            guild,
            time=time,
            user=user,
            moderator=moderator,
            action=action,
            delta=delta + datetime.timedelta(seconds=SLEEP_FOR),
            retry=retry - 1,
        )

    return None


async def user_in_guild(guild: discord.Guild, user: User) -> bool:
    if guild.get_member(user.id) is not None:
        return True

    try:
        await guild.fetch_member(user.id)
    except discord.NotFound:
        return False

    return True
