import asyncio
import datetime
from dataclasses import dataclass

from typing import (
    Any,
    Optional,
    Type,
    TypeVar,
)
import asyncpg

import discord
from discord.ext import tasks
from donphan import Table, SQLType, Column


__all__ = ("ScheduledEvent", "EventSchedulerMixin")


T = TypeVar("T", bound="ScheduledEvent")


class Events(Table, schema="core"):  # type: ignore[call-arg]
    id: SQLType.Serial = Column(primary_key=True)
    created_at: datetime.datetime = Column(default="NOW()")
    scheduled_for: datetime.datetime = Column(index=True)
    event_type: str = Column(nullable=False, index=True)
    data: dict = Column(default="'{}'::jsonb")


@dataclass
class ScheduledEvent:
    id: Optional[int]
    created_at: datetime.datetime
    scheduled_for: datetime.datetime
    type: str
    args: list[Any]
    kwargs: dict[str, Any]

    @classmethod
    def from_record(cls: Type[T], record: asyncpg.Record) -> T:
        return cls(
            record["id"],
            record["created_at"],
            record["scheduled_for"],
            record["event_type"],
            record["data"]["args"],
            record["data"]["kwargs"],
        )

    def dispatch(self, client: discord.Client) -> None:
        client.dispatch(self.type, *self.args, *self.kwargs)


class EventSchedulerMixin(discord.Client):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.__event_scheduler__active = asyncio.Event()
        self.__event_scheduler__current = None
        self._dispatch_task.add_exception_type(asyncpg.exceptions.PostgresConnectionError)
        self._dispatch_task.start()

    async def schedule_event(self, time: datetime.datetime, type: str, /, *args: Any, **kwargs: Any) -> ScheduledEvent:

        now = datetime.datetime.now(tz=datetime.timezone.utc)

        if time < now:
            raise RuntimeError("Cannot schedule an event in the past.")

        event = ScheduledEvent(None, now, time, type, list(args), dict(kwargs))

        (event.id,) = await Events.insert(
            returning=Events.id,
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
    def next_scheduled_event(self) -> Optional[ScheduledEvent]:
        return self.__event_scheduler__current

    async def _wait_for_event(self) -> ScheduledEvent:
        record = await Events.fetchrow(order_by="scheduled_for ASC")

        if record is not None:
            self.__event_scheduler__active.set()
            return ScheduledEvent.from_record(record)

        self.__event_scheduler__active.clear()
        self.__event_scheduler__current = None
        await self.__event_scheduler__active.wait()
        return await self._wait_for_event()

    @tasks.loop(seconds=0)
    async def _dispatch_task(self) -> None:
        while not self.is_closed():
            event = self.__event_scheduler__current = await self._wait_for_event()

            now = datetime.datetime.now(tz=datetime.timezone.utc)

            # if event is scheduled for the future
            if event.scheduled_for >= now:
                await discord.utils.sleep_until(event.scheduled_for)

            if event.id is not None:
                await Events.delete_where("id = $1", event.id)

            event.dispatch(self)

    @_dispatch_task.before_loop
    async def _before_dispatch_task(self):
        await self.wait_until_ready()
