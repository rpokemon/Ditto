from __future__ import annotations

import datetime
from typing import Any, Callable, Optional, TYPE_CHECKING
import uuid

from aiohttp.web import Request, Response
from aiohttp_session import AbstractStorage, Session

from discord.utils import _to_json, _from_json
from donphan import MaybeAcquire


from ..db.tables import HTTPSessions

if TYPE_CHECKING:
    from ..core.bot import BotBase


class PostgresStorage(AbstractStorage):
    def __init__(
        self,
        bot: BotBase,
        *,
        cookie_name: str = "AIOHTTP_SESSION",
        domain: Optional[str] = None,
        max_age: Optional[int] = None,
        path: Optional[str] = "/",
        secure: Optional[bool] = True,
        httponly: Optional[bool] = None,
        encoder: Callable[[str], Any] = _from_json,
        decoder: Callable[[Any], str] = _to_json,
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

        async with MaybeAcquire(pool=self.bot.pool) as conn:
            session = await HTTPSessions.fetch_row(conn, key=key, expires_at__gt=now)

        if session is None:
            return Session(None, data=None, new=True, max_age=self.max_age)

        return Session(
            key, data=session["data"], new=False, max_age=int((session["expires_at"] - now).total_seconds())
        )

    async def save_session(self, request: Request, response: Response, session: Session) -> None:
        key = session.identity
        if key is None:
            key = uuid.uuid4()
            self.save_cookie(response, key, max_age=session.max_age)
        else:
            if session.empty:
                self.save_cookie(response, "", max_age=session.max_age)
            else:
                key = str(key)
                self.save_cookie(response, key, max_age=session.max_age)

        data = self._get_session_data(session)
        expires = (
            datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(seconds=session.max_age)
            if session.max_age
            else None
        )
        async with MaybeAcquire(pool=self.bot.pool) as conn:
            await HTTPSessions.insert(conn, key=key, data=data, expires_at=expires)
