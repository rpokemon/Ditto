from __future__ import annotations

import sys
from functools import cached_property
from urllib.parse import quote
from typing import TYPE_CHECKING, Any, Protocol, runtime_checkable

import aiohttp
import aiohttp_jinja2
import aiohttp_security
import aiohttp_session
from aiohttp.web import Application, AppRunner, normalize_path_middleware, Request, Response, HTTPFound, get, static
from aiohttp.web_runner import TCPSite

import jinja2


from ..config import CONFIG
from .auth import AUTH_URI, USER_AGENT, DiscordAuthorizationPolicy, validate_login
from .storage import PostgresStorage

if TYPE_CHECKING:
    from ..core.bot import BotBase
else:

    @runtime_checkable
    class BotBase(Protocol):
        ...


__all__ = ("WebServerMixin",)


class WebServerMixin:
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        assert isinstance(self, BotBase)

        super().__init__(*args, **kwargs)

        if CONFIG.WEB.DISABLED:
            return

        self.app: Application = Application(middlewares=[normalize_path_middleware()])

        self.storage: PostgresStorage = PostgresStorage(self)
        aiohttp_session.setup(self.app, self.storage)

        self.user_agent: str = USER_AGENT.format(
            CONFIG.APP_NAME, CONFIG.VERSION, sys.version_info, aiohttp.__version__
        )

        self.policy: DiscordAuthorizationPolicy = DiscordAuthorizationPolicy(self)
        aiohttp_security.setup(self.app, aiohttp_security.SessionIdentityPolicy(), self.policy)

        self.app.add_routes(
            [
                static("/static", CONFIG.WEB.STATIC_DIR),
                get("/login", self.web_login),
                get("/logout", self.web_logout),
            ]
        )

        aiohttp_jinja2.setup(self.app, enable_async=True, loader=jinja2.FileSystemLoader(CONFIG.WEB.TEMPLATE_DIR))

    @cached_property
    def auth_uri(self) -> str:
        assert isinstance(self, BotBase)
        return AUTH_URI.format(self.application_id, quote(CONFIG.APPLICATION.REDIRECT_URI))

    async def connect(self, *args: Any, **kwargs: Any) -> None:
        assert isinstance(self, BotBase)

        if CONFIG.WEB.DISABLED:
            return

        self._web_runner: AppRunner = AppRunner(self.app)
        await self._web_runner.setup()

        self._web_site = TCPSite(self._web_runner, CONFIG.WEB.HOST, CONFIG.WEB.PORT)
        await self._web_site.start()

        await super().connect(*args, **kwargs)  # type: ignore

    async def web_login(self, request: Request) -> Response:
        assert isinstance(self, BotBase)
        user_id = await validate_login(self, request)

        redirect = HTTPFound("/")
        await aiohttp_security.remember(request, redirect, user_id)
        return redirect

    async def web_logout(self, request: Request) -> Response:
        redirect = HTTPFound("/")
        await aiohttp_security.forget(request, redirect)
        return redirect
