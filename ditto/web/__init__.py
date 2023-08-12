from __future__ import annotations

import sys
from collections.abc import Callable, Coroutine
from functools import cached_property
from typing import TYPE_CHECKING, Any, TypeVar
from urllib.parse import quote

import aiohttp
import aiohttp_jinja2
import aiohttp_security
import aiohttp_session
import discord
import jinja2
from aiohttp.web import Application, AppRunner, HTTPFound, Request, Response, get, normalize_path_middleware, static
from aiohttp.web_runner import TCPSite

from ..config import CONFIG
from .auth import AUTH_URI, USER_AGENT, DiscordAuthorizationPolicy, validate_login
from .storage import PostgresStorage

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

        self.storage: PostgresStorage = PostgresStorage(self, cookie_name="session")
        aiohttp_session.setup(self.app, self.storage)

        self.user_agent: str = USER_AGENT.format(
            CONFIG.APP_NAME, CONFIG.URL, CONFIG.VERSION, sys.version_info, aiohttp.__version__
        )

        self.policy: DiscordAuthorizationPolicy = DiscordAuthorizationPolicy(self)
        aiohttp_security.setup(self.app, aiohttp_security.SessionIdentityPolicy(), self.policy)

        self.app.add_routes(
            [
                static("/static", CONFIG.WEB.STATIC_DIR),
                get("/login", self._web_login),
                get("/logout", self._web_logout),
            ]
        )

        aiohttp_jinja2.setup(self.app, enable_async=True, loader=jinja2.FileSystemLoader(CONFIG.WEB.TEMPLATE_DIR))

    @cached_property
    def auth_uri(self) -> str:
        if TYPE_CHECKING:
            assert isinstance(self, BotBase)
        return AUTH_URI.format(self.application_id, quote(CONFIG.APPLICATION.REDIRECT_URI))

    async def connect(self, *args: Any, **kwargs: Any) -> None:
        if TYPE_CHECKING:
            assert isinstance(self, BotBase)

        if not CONFIG.WEB.DISABLED:
            self._web_runner: AppRunner = AppRunner(self.app)
            await self._web_runner.setup()

            self._web_site = TCPSite(self._web_runner, CONFIG.WEB.HOST, CONFIG.WEB.PORT)
            await self._web_site.start()

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
