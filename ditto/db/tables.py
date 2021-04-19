import zoneinfo

from typing import Optional

import asyncpg  # type: ignore

from donphan import Column, Table, SQLType  # type: ignore

from ..types import User


__all__ = ("Time_Zones",)


class Time_Zones(Table):
    user_id: SQLType.BigInt = Column(primary_key=True)  # type: ignore
    time_zone: str = Column(nullable=False)  # type: ignore

    @classmethod
    async def get_timezone(
        cls, user: User, /, *, connection: Optional[asyncpg.Connection] = None
    ) -> Optional[zoneinfo.ZoneInfo]:
        record = await cls.fetchrow(user_id=user.id, connection=connection)
        return zoneinfo.ZoneInfo(record["time_zone"]) if record is not None else None
