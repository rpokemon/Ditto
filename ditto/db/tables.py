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
    message_id: Column[SQLType.BigInt] = Column(primary_key=True)
    guild_id: Column[SQLType.BigInt] = Column(index=True)
    channel_id: Column[SQLType.BigInt] = Column(index=True)
    user_id: Column[SQLType.BigInt] = Column(index=True)
    invoked_at: Column[SQLType.Timestamp]
    prefix: Column[SQLType.Text]
    command: Column[SQLType.Text]
    failed: Column[SQLType.Boolean]


class Time_Zones(Table, schema="core"):  # type: ignore[call-arg]
    user_id: Column[SQLType.BigInt] = Column(primary_key=True)
    time_zone: Column[SQLType.Text] = Column(nullable=False)

    @classmethod
    async def get_timezone(cls, connection: asyncpg.Connection, /, user: User) -> Optional[zoneinfo.ZoneInfo]:
        record = await cls.fetch_row(connection, user_id=user.id)
        return zoneinfo.ZoneInfo(record["time_zone"]) if record is not None else None
