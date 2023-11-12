from __future__ import annotations

import sys
from asyncio import wait_for
from collections.abc import Callable, Coroutine
from functools import cached_property
from typing import TYPE_CHECKING, Any, TypeVar
from urllib.parse import quote

import aiohttp
import aiohttp_jinja2
import aiohttp_security
import aiohttp_session
import asyncpg
import discord
from discord.ext import tasks
import jinja2
from aiohttp.web import (
    Application,
    AppRunner,
    HTTPFound,
    HTTPOk,
    HTTPServiceUnavailable,
    Request,
    Response,
    get,
    normalize_path_middleware,
    static,
    json_response,
)
from aiohttp.web_runner import TCPSite

from ..config import CONFIG
from ..db.tables import HTTPSessions
from .auth import AUTH_URI, USER_AGENT, DiscordAuthorizationPolicy, validate_login
from .storage import InMemoryStorage, PostgresStorage

if TYPE_CHECKING:
    from ..core.bot import BotBase


__all__ = ("WebServerMixin",)


T = TypeVar("T")
Coro = Coroutine[Any, Any, T]


class WebServerMixin:
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        if TYPE_CHECKING:
            assert isinstance(self, BotBase)

        super().__init__(*args, **kwargs)

        if CONFIG.WEB.DISABLED:
            return

        self.app: Application = Application(middlewares=[normalize_path_middleware()])
        self._permission_checks: dict[str, Callable[[BotBase, discord.User], Coro[bool]]] = {}

        self.storage: aiohttp_session.AbstractStorage
        if CONFIG.DATABASE.DISABLED:
            self.storage = InMemoryStorage(cookie_name="session")
        else:
            self.storage = PostgresStorage(self, cookie_name="session")

        aiohttp_session.setup(self.app, self.storage)

        self.user_agent: str = USER_AGENT.format(
            CONFIG.APP_NAME, CONFIG.WEB.URL, CONFIG.VERSION, sys.version_info, aiohttp.__version__
        )

        self.policy: DiscordAuthorizationPolicy = DiscordAuthorizationPolicy(self)
        aiohttp_security.setup(self.app, aiohttp_security.SessionIdentityPolicy(), self.policy)

        self.app.add_routes(
            [
                static("/static", CONFIG.WEB.STATIC_DIR),
                get("/login", self._web_login),
                get("/logout", self._web_logout),
                get("/api/appinfo", self._web_appinfo),
                get("/api/health", self._web_health),
                get("/api/health/live", self._web_health_live),
                get("/api/health/ready", self._web_health_ready),
            ]
        )

        aiohttp_jinja2.setup(self.app, enable_async=True, loader=jinja2.FileSystemLoader(CONFIG.WEB.TEMPLATE_DIR))

    @cached_property
    def auth_uri(self) -> str:
        if TYPE_CHECKING:
            assert isinstance(self, BotBase)
            assert CONFIG.APPLICATION.REDIRECT_URI is not None
        return AUTH_URI.format(self.application_id, quote(CONFIG.APPLICATION.REDIRECT_URI))

    async def connect(self, *args: Any, **kwargs: Any) -> None:
        if TYPE_CHECKING:
            assert isinstance(self, BotBase)

        if not CONFIG.WEB.DISABLED:
            self._web_runner: AppRunner = AppRunner(self.app)
            await self._web_runner.setup()

            self._web_site = TCPSite(self._web_runner, CONFIG.WEB.HOST, CONFIG.WEB.PORT)
            await self._web_site.start()

            if not CONFIG.DATABASE.DISABLED:
                self._web_db_cleanup_task.add_exception_type(asyncpg.exceptions.PostgresConnectionError)
                self._web_db_cleanup_task.start()

        await super().connect(*args, **kwargs)  # type: ignore

    async def _web_login(self, request: Request) -> Response:
        if TYPE_CHECKING:
            assert isinstance(self, BotBase)
        user_id = await validate_login(self, request)

        redirect = HTTPFound("/")
        await aiohttp_security.remember(request, redirect, user_id)
        return redirect

    async def _web_logout(self, request: Request) -> Response:
        redirect = HTTPFound("/")
        await aiohttp_security.forget(request, redirect)
        return redirect

    async def _web_appinfo(self, request: Request) -> Response:
        if TYPE_CHECKING:
            assert isinstance(self, BotBase)

        return json_response(
            {
                "name": CONFIG.APP_NAME,
                "version": CONFIG.VERSION,
                "start_time": self.start_time.isoformat(),
            }
        )

    async def _check_db_health(self) -> bool | None:
        if TYPE_CHECKING:
            assert isinstance(self, BotBase)

        if CONFIG.DATABASE.DISABLED:
            return None

        # Check if we can query the database
        try:
            await self.pool.fetchval("SELECT 1")
        except:
            return False

        return True

    async def _check_discord_health(self) -> bool | None:
        if TYPE_CHECKING:
            assert isinstance(self, BotBase)

        if not self.is_ready():
            return None

        # Check if we're receiving socket events
        try:
            await wait_for(self.wait_for("socket_event_type"), 5)
        except:
            return False

        return True

    async def _web_health(self, request: Request) -> Response:
        if TYPE_CHECKING:
            assert isinstance(self, BotBase)

        body = {
            "database": await self._check_db_health(),
            "discord": await self._check_discord_health(),
        }

        status_code = HTTPOk.status_code if all(body.values()) else HTTPServiceUnavailable.status_code
        return json_response(body, status=status_code)

    async def _web_health_live(self, request: Request) -> Response:
        return HTTPOk()

    async def _web_health_ready(self, request: Request) -> Response:
        if await self._check_db_health() is False:
            return HTTPServiceUnavailable()

        if not await self._check_discord_health():
            return HTTPServiceUnavailable()

        return HTTPOk()

    def add_permission_check(self, permission: str, check: Callable[[BotBase, discord.User], Coro[bool]]) -> None:
        self._permission_checks[permission] = check

    def remove_permission_check(self, permission: str) -> None:
        self._permission_checks.pop(permission, None)

    def permission_check(
        self, permission: str
    ) -> Callable[[Callable[[BotBase, discord.User], Coro[bool]]], Callable[[BotBase, discord.User], Coro[bool]]]:
        def decorator(func: Callable[[BotBase, discord.User], Coro[bool]]) -> Callable[[BotBase, discord.User], Coro[bool]]:
            self.add_permission_check(permission, func)
            return func

        return decorator

    @tasks.loop(minutes=15)
    async def _web_db_cleanup_task(self) -> None:
        if TYPE_CHECKING:
            assert isinstance(self, BotBase)

        async with self.pool.acquire() as connection:
            await HTTPSessions.delete_where(connection, "expires_at < NOW()")

    @_web_db_cleanup_task.before_loop
    async def _before_web_db_cleanup_task(self):
        if TYPE_CHECKING:
            assert isinstance(self, BotBase)
        await self.wait_until_ready()
