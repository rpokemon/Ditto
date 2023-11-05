from __future__ import annotations

import datetime
import uuid
from collections.abc import Callable
from typing import TYPE_CHECKING, Any

from aiohttp.web import Request, Response
from aiohttp_session import AbstractStorage, Session
from discord.utils import _from_json, _to_json

from ..db.tables import HTTPSessions

if TYPE_CHECKING:
    from ..core.bot import BotBase


class InMemoryStorage(AbstractStorage):
    def __init__(
        self,
        *,
        cookie_name: str = "AIOHTTP_SESSION",
        domain: str | None = None,
        max_age: int | None = None,
        path: str = "/",
        secure: bool | None = True,
        httponly: bool = True,
        encoder: Callable[[Any], str] = _to_json,
        decoder: Callable[[str], Any] = _from_json,
    ):
        self.storage: dict[uuid.UUID, dict[str, Any]] = {}

        super().__init__(
            cookie_name=cookie_name,
            domain=domain,
            max_age=max_age,
            path=path,
            secure=secure,
            httponly=httponly,
            encoder=encoder,
            decoder=decoder,
        )

    async def load_session(self, request: Request) -> Session:
        cookie = self.load_cookie(request)

        if cookie is None:
            return Session(None, data=None, new=True, max_age=self.max_age)

        key = uuid.UUID(str(cookie))
        now = datetime.datetime.now(datetime.timezone.utc)

        session = self.storage.get(key)

        if session is None or session["expires_at"] is not None and session["expires_at"] < now:
            return Session(None, data=None, new=True, max_age=self.max_age)

        if session["expires_at"] is not None:
            max_age = int((session["expires_at"] - now).total_seconds())
        else:
            max_age = None

        return Session(key, data=session["data"], new=False, max_age=max_age)

    async def save_session(self, request: Request, response: Response, session: Session) -> None:
        key = session.identity
        if key is None:
            key = uuid.uuid4()
            self.save_cookie(response, str(key), max_age=session.max_age)
        else:
            if session.empty:
                self.save_cookie(response, "", max_age=session.max_age)
            else:
                self.save_cookie(response, str(key), max_age=session.max_age)

        data = self._get_session_data(session)
        expires = (
            datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(seconds=session.max_age)
            if session.max_age
            else None
        )

        self.storage[key] = {"data": data, "expires_at": expires}


class PostgresStorage(AbstractStorage):
    def __init__(
        self,
        bot: BotBase,
        *,
        cookie_name: str = "AIOHTTP_SESSION",
        domain: str | None = None,
        max_age: int | None = None,
        path: str = "/",
        secure: bool | None = True,
        httponly: bool = True,
        encoder: Callable[[Any], str] = _to_json,
        decoder: Callable[[str], Any] = _from_json,
    ):
        self.bot: BotBase = bot
        super().__init__(
            cookie_name=cookie_name,
            domain=domain,
            max_age=max_age,
            path=path,
            secure=secure,
            httponly=httponly,
            encoder=encoder,
            decoder=decoder,
        )

    async def load_session(self, request: Request) -> Session:
        cookie = self.load_cookie(request)

        if cookie is None:
            return Session(None, data=None, new=True, max_age=self.max_age)

        key = uuid.UUID(str(cookie))
        now = datetime.datetime.now(datetime.timezone.utc)

        async with self.bot.pool.acquire() as conn:
            # WHERE (expires_at is NULL or expires_at > NOW()) AND key = key
            session = await HTTPSessions.fetch_row(conn, expires_at=None, or_expires_at__gt=now, key=key)

        if session is None:
            return Session(None, data=None, new=True, max_age=self.max_age)

        if session["expires_at"] is not None:
            max_age = int((session["expires_at"] - now).total_seconds())
        else:
            max_age = None

        return Session(key, data=session["data"], new=False, max_age=max_age)

    async def save_session(self, request: Request, response: Response, session: Session) -> None:
        key = session.identity
        if key is None:
            key = uuid.uuid4()
            self.save_cookie(response, str(key), max_age=session.max_age)
        else:
            if session.empty:
                self.save_cookie(response, "", max_age=session.max_age)
            else:
                self.save_cookie(response, str(key), max_age=session.max_age)

        data = self._get_session_data(session)
        expires = (
            datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(seconds=session.max_age)
            if session.max_age
            else None
        )

        async with self.bot.pool.acquire() as conn:
            await HTTPSessions.insert(
                conn,
                key=key,
                data=data,
                expires_at=expires,
                update_on_conflict=[HTTPSessions.data, HTTPSessions.expires_at],
            )
