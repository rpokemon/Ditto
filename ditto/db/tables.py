import zoneinfo

from typing import Optional

import asyncpg

from donphan import Column, Table, SQLType

from ..types import User


__all__ = (
    "Commands",
    "Time_Zones",
)


class Commands(Table, schema="logging"):  # type: ignore[call-arg]
    message_id: SQLType.BigInt = Column(primary_key=True)
    guild_id: SQLType.BigInt = Column(index=True)
    channel_id: SQLType.BigInt = Column(index=True)
    user_id: SQLType.BigInt = Column(index=True)
    invoked_at: SQLType.Timestamp
    prefix: SQLType.Text
    command: SQLType.Text
    failed: SQLType.Boolean


class Time_Zones(Table, schema="core"):  # type: ignore[call-arg]
    user_id: SQLType.BigInt = Column(primary_key=True)
    time_zone: SQLType.Text = Column(nullable=False)

    @classmethod
    async def get_timezone(
        cls, user: User, /, *, connection: Optional[asyncpg.Connection] = None
    ) -> Optional[zoneinfo.ZoneInfo]:
        record = await cls.fetchrow(user_id=user.id, connection=connection)
        return zoneinfo.ZoneInfo(record["time_zone"]) if record is not None else None
