import zoneinfo
from typing import ClassVar

import asyncpg
from donphan import CachedTable, Column, SQLType, Table

from ..types import User

__all__ = (
    "Commands",
    "TimeZones",
    "Events",
    "Emoji",
    "UserEmoji",
    "HTTPSessions",
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


class TimeZones(CachedTable, schema="core", max_cache_size=128, cache_no_record=True):
    user_id: Column[SQLType.BigInt] = Column(primary_key=True)
    time_zone: Column[SQLType.Text] = Column(nullable=False)

    @classmethod
    async def set_timezone(cls, connection: asyncpg.Connection, /, user: User, timezone: zoneinfo.ZoneInfo | None) -> None:
        if timezone is not None:
            await TimeZones.insert(
                connection,
                update_on_conflict=(TimeZones.time_zone,),
                returning=None,
                user_id=user.id,
                time_zone=str(timezone),
            )
        else:
            await TimeZones.delete(connection, user_id=user.id)

    @classmethod
    async def get_timezone(cls, connection: asyncpg.Connection, /, user: User) -> zoneinfo.ZoneInfo | None:
        record = await cls.fetch_row(connection, user_id=user.id)
        return zoneinfo.ZoneInfo(record["time_zone"]) if record is not None else None


class Events(Table, schema="core"):
    id: Column[SQLType.Serial] = Column(primary_key=True)
    created_at: Column[SQLType.Timestamp] = Column(default="NOW()")
    scheduled_for: Column[SQLType.Timestamp] = Column(index=True)
    event_type: Column[SQLType.Text] = Column(nullable=False, index=True)
    data: Column[SQLType.JSONB] = Column(default="'{}'::jsonb")


class Emoji(CachedTable, schema="core"):
    emoji_id: Column[SQLType.BigInt] = Column(primary_key=True)
    last_fetched: Column[SQLType.Timestamp] = Column(default="NOW()")

    @classmethod
    async def count(cls, connection: asyncpg.Connection) -> int:
        return await connection.fetchval(f"SELECT COUNT(*) FROM {cls._name}")  # type: ignore


class UserEmoji(CachedTable, schema="core"):
    emoji_id: Column[SQLType.BigInt] = Column(primary_key=True, references=Emoji.emoji_id, cascade=True)
    user_id: Column[SQLType.BigInt] = Column(index=True, unique=True)
    avatar_hash: Column[SQLType.Text] = Column(nullable=True)


class HTTPSessions(CachedTable, schema="web", max_cache_size=128):
    key: Column[SQLType.UUID] = Column(primary_key=True)
    data: Column[SQLType.JSONB] = Column(default="'{}'::jsonb")
    expires_at: Column[SQLType.Timestamp] = Column(nullable=True, index=True)
