import datetime

import logging
import logging.handlers
import traceback

from collections.abc import Callable
from typing import Any, Optional

import asyncpg
import discord

from discord.ext import commands
from discord.ext.alternatives import converter_dict as converter_dict
from discord.ext.commands.errors import NoEntryPointError

from .context import Context
from .help import EmbedHelpCommand
from ..config import CONFIG, load_global_config
from ..db import setup_database, EventSchedulerMixin
from ..types import CONVERTERS
from ..utils.logging import WebhookHandler
from ..utils.strings import codeblock


__all__ = (
    "BotBase",
    "Bot",
    "AutoShardedBot",
)


ONE_KILOBYTE = 1024
ONE_MEGABYTE = ONE_KILOBYTE * 1024


class BotBase(commands.bot.BotBase, EventSchedulerMixin, discord.Client):
    converters: dict[type, Callable[..., Any]]
    pool: asyncpg.pool.Pool

    owner: Optional[discord.User]
    owners: Optional[list[discord.User]]

    def __init__(self, *args, **kwargs) -> None:
        CONFIG = load_global_config(self)

        self.start_time = datetime.datetime.now(datetime.timezone.utc)

        # Setup logging
        self.log = logging.getLogger(__name__)
        if CONFIG.LOGGING.LOG_LEVEL is not None:
            self.log.setLevel(CONFIG.LOGGING.LOG_LEVEL)

        global_log = logging.getLogger()
        if CONFIG.LOGGING.GLOBAL_LOG_LEVEL is not None:
            global_log.setLevel(CONFIG.LOGGING.GLOBAL_LOG_LEVEL)

        if CONFIG.LOGGING.LOG_TO_FILE:
            handler = logging.handlers.RotatingFileHandler(f"{CONFIG.APP_NAME}.log", maxBytes=ONE_MEGABYTE, encoding="utf-8")
            global_log.addHandler(handler)

        if CONFIG.LOGGING.WEBHOOK_URI is not None:
            handler = WebhookHandler(CONFIG.LOGGING.WEBHOOK_URI)
            global_log.addHandler(handler)

        global_log.addHandler(logging.StreamHandler())

        allowed_mentions = discord.AllowedMentions.none()  # <3 Moogy

        # Set intents
        if hasattr(CONFIG.BOT, "INTENTS"):
            intents = discord.Intents(**CONFIG.BOT.INTENTS)
        else:
            intents = discord.Intents.default()

        # Setup bot instance.
        allow_mentions_as_prefix = getattr(CONFIG.BOT, "ALLOW_MENTIONS_AS_PREFIX", False)
        self.prefix = getattr(CONFIG.BOT, "PREFIX", None)
        if self.prefix is None:
            if not allow_mentions_as_prefix:
                raise RuntimeError("No prefix has been set, set one with a config override.")
            prefix = commands.when_mentioned
        else:
            prefix = commands.when_mentioned_or(self.prefix) if allow_mentions_as_prefix else self.prefix

        super().__init__(
            *args,
            command_prefix=prefix,
            help_command=EmbedHelpCommand(),
            allowed_mentions=allowed_mentions,
            intents=intents,
            **kwargs,
        )

        # Add extra converters
        self.converters |= CONVERTERS

        # Add extensions
        for extension in CONFIG.EXTENSIONS.keys():
            try:
                self.load_extension(extension)
            except (commands.ExtensionError, ImportError):
                self.log.exception(f"Failed to load extension {extension}")

    @property
    def uptime(self) -> datetime.timedelta:
        return datetime.datetime.now(datetime.timezone.utc) - self.start_time

    async def on_ready(self) -> None:
        print(self.user)
        self.log.info(f"Succesfully logged in as {self.user} ({self.user.id})")
        await self.is_owner(self.user)  # fetch owner id
        if self.owner_id:
            self.owner = await self.fetch_user(self.owner_id)
            self.owners = []
        if self.owner_ids:
            self.owner = None
            self.owners = [await self.fetch_user(id) for id in self.owner_ids]

    async def on_command_error(self, ctx: Context, error: BaseException) -> Optional[discord.Message]:
        if isinstance(error, commands.CommandNotFound):
            return None

        if isinstance(
            error,
            (
                commands.CheckFailure,
                commands.UserInputError,
                commands.CommandOnCooldown,
                commands.MaxConcurrencyReached,
                commands.DisabledCommand,
            ),
        ):
            return await ctx.send(
                embed=discord.Embed(
                    color=discord.Colour.red(),
                    title=f"Error with command {ctx.command.qualified_name}",
                    description=str(error),
                )
            )

        if error.__cause__ is None:
            return None

        error = error.__cause__

        await ctx.send(
            embed=discord.Embed(
                colour=discord.Colour.dark_red(),
                title=f"Unexpected error with command {ctx.command.qualified_name}",
                description=codeblock(f"{type(error).__name__}: {error}", language="py"),
            )
        )

        tb = "".join(traceback.format_exception(type(error), error, error.__traceback__))
        self.log.error(
            f"Unhandled exception in command: {ctx.command.qualified_name}\n\n{type(error).__name__}: {error}\n\n{tb}"
        )
        return None

    async def process_commands(self, message: discord.Message) -> None:
        if CONFIG.BOT.IGNORE_BOTS and message.author.bot:
            return

        if message.author == self.user:
            return

        ctx = await self.get_context(message, cls=Context)
        await self.invoke(ctx)

    async def setup_database(self):
        self.pool = await setup_database()

    async def connect(self, *args, **kwargs):
        await self.setup_database()
        return await super().connect(*args, **kwargs)

    def run(self):
        if CONFIG.BOT.TOKEN is None:
            raise RuntimeError("You haven't set your bots token, do so with a config override.")

        super().run(CONFIG.BOT.TOKEN)

    async def close(self):
        if not CONFIG.DATABASE.DISABLED:
            await self.pool.close()
        await super().close()


class Bot(BotBase, commands.Bot):
    ...


class AutoShardedBot(BotBase, commands.AutoShardedBot):
    ...
