import zoneinfo

from typing import Optional

import asyncpg

from donphan import Column, Table, SQLType

from ..types import User


__all__ = (
    "Commands",
    "TimeZones",
    "Events",
    "Emoji",
    "UserEmoji",
)


class Commands(Table, schema="logging"):
    message_id: Column[SQLType.BigInt] = Column(primary_key=True)
    guild_id: Column[SQLType.BigInt] = Column(index=True)
    channel_id: Column[SQLType.BigInt] = Column(index=True)
    user_id: Column[SQLType.BigInt] = Column(index=True)
    invoked_at: Column[SQLType.Timestamp]
    prefix: Column[SQLType.Text]
    command: Column[SQLType.Text]
    failed: Column[SQLType.Boolean]


class TimeZones(Table, schema="core"):
    user_id: Column[SQLType.BigInt] = Column(primary_key=True)
    time_zone: Column[SQLType.Text] = Column(nullable=False)

    @classmethod
    async def get_timezone(cls, connection: asyncpg.Connection, /, user: User) -> Optional[zoneinfo.ZoneInfo]:
        record = await cls.fetch_row(connection, user_id=user.id)
        return zoneinfo.ZoneInfo(record["time_zone"]) if record is not None else None


class Events(Table, schema="core"):
    id: Column[SQLType.Serial] = Column(primary_key=True)
    created_at: Column[SQLType.Timestamp] = Column(default="NOW()")
    scheduled_for: Column[SQLType.Timestamp] = Column(index=True)
    event_type: Column[SQLType.Text] = Column(nullable=False, index=True)
    data: Column[SQLType.JSONB] = Column(default="'{}'::jsonb")


class Emoji(Table, schema="core"):
    emoji_id: Column[SQLType.BigInt] = Column(primary_key=True)
    guild_id: Column[SQLType.BigInt] = Column(index=True, nullable=False)
    last_fetched: Column[SQLType.Timestamp] = Column(default="NOW()")


class UserEmoji(Table, schema="core"):
    emoji_id: Column[SQLType.BigInt] = Column(primary_key=True, references=Emoji.emoji_id, cascade=True)
    user_id: Column[SQLType.BigInt] = Column(index=True, unique=True)
