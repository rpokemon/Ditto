from __future__ import annotations

import asyncio
import datetime
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

import asyncpg
import discord
from discord.ext import tasks

from .tables import Events

if TYPE_CHECKING:
    from typing_extensions import Self

    from ..core.bot import BotBase


__all__ = ("ScheduledEvent", "EventSchedulerMixin")


@dataclass
class ScheduledEvent:
    id: int | None
    created_at: datetime.datetime
    scheduled_for: datetime.datetime
    event_type: str
    args: list[Any]
    kwargs: dict[str, Any]

    @classmethod
    def from_record(cls, record: asyncpg.Record) -> Self:
        return cls(
            record["id"],
            record["created_at"],
            record["scheduled_for"],
            record["event_type"],
            record["data"]["args"],
            record["data"]["kwargs"],
        )

    def dispatch(self, client: discord.Client) -> None:
        client.dispatch(self.event_type, *self.args, *self.kwargs)


class EventSchedulerMixin:
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        # this is a hack because >circular imports<
        from ..config import CONFIG

        super().__init__(*args, **kwargs)

        if CONFIG.DATABASE.DISABLED:
            return

        self.__event_scheduler__active: asyncio.Event = asyncio.Event()
        self.__event_scheduler__current: ScheduledEvent | None = None
        self._dispatch_task.add_exception_type(asyncpg.exceptions.PostgresConnectionError)

    async def setup_hook(self):
        # this is a hack because >circular imports<
        from ..config import CONFIG

        if not CONFIG.DATABASE.DISABLED:
            self._dispatch_task.start()
        await super().setup_hook()  # type: ignore

    async def schedule_event(self, time: datetime.datetime, type: str, /, *args: Any, **kwargs: Any) -> ScheduledEvent:
        if TYPE_CHECKING:
            assert isinstance(self, BotBase)

        now = datetime.datetime.now(tz=datetime.timezone.utc)

        if time < now:
            raise RuntimeError("Cannot schedule an event in the past.")

        event = ScheduledEvent(None, now, time, type, list(args), dict(kwargs))

        async with self.pool.acquire() as connection:
            (event.id,) = await Events.insert(
                connection,
                returning=(Events.id,),
                scheduled_for=time,
                event_type=type,
                data={"args": list(args), "kwargs": dict(kwargs)},
            )

        self.__event_scheduler__active.set()

        # Check if the new event is scheduled for before the current one
        if self.__event_scheduler__current is not None and time < self.__event_scheduler__current.scheduled_for:
            self.restart_scheduler()

        return event

    def restart_scheduler(self):
        self._dispatch_task.restart()

    @property
    def next_scheduled_event(self) -> ScheduledEvent | None:
        return self.__event_scheduler__current

    async def _wait_for_event(self) -> ScheduledEvent:
        if TYPE_CHECKING:
            assert isinstance(self, BotBase)

        record = await Events.fetch_row(order_by=(Events.scheduled_for, "ASC"))

        if record is not None:
            self.__event_scheduler__active.set()
            return ScheduledEvent.from_record(record)

        self.__event_scheduler__active.clear()
        self.__event_scheduler__current = None
        await self.__event_scheduler__active.wait()
        return await self._wait_for_event()

    @tasks.loop(seconds=0)
    async def _dispatch_task(self) -> None:
        if TYPE_CHECKING:
            assert isinstance(self, BotBase)

        event = self.__event_scheduler__current = await self._wait_for_event()
        await discord.utils.sleep_until(event.scheduled_for)

        if event.id is not None:
            async with self.pool.acquire() as connection:
                await Events.delete(connection, id=event.id)

        event.dispatch(self)

    @_dispatch_task.before_loop
    async def _before_dispatch_task(self):
        if TYPE_CHECKING:
            assert isinstance(self, BotBase)
        await self.wait_until_ready()
