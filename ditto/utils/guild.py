import asyncio
import datetime

from typing import Optional, Union

import discord

from .time import normalise_timedelta
from ..types import User


__all__ = (
    "user_in_guild",
    "fetch_audit_log_entry",
)


SLEEP_FOR = 3


async def fetch_audit_log_entry(
    guild: discord.Guild,
    *,
    time: Optional[datetime.datetime] = None,
    user: Optional[User] = None,
    moderator: Optional[User] = None,
    action: Optional[discord.AuditLogAction] = None,
    delta: Union[float, datetime.timedelta] = 10,
    retry: int = 3,
) -> Optional[discord.AuditLogEntry]:

    time = time or datetime.datetime.now(datetime.timezone.utc)

    delta = normalise_timedelta(delta)

    async for entry in guild.audit_logs(action=action, user=moderator):
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
            delta=delta,
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
