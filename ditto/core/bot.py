from __future__ import annotations

import datetime
import json
import logging
import logging.handlers
import traceback
from collections.abc import Callable
from contextlib import suppress
from typing import Any

import asyncpg
import discord
from discord.ext import commands

from ..config import CONFIG, load_global_config
from ..db import EmojiCacheMixin, EventSchedulerMixin, setup_database
from ..types import CONVERTERS
from ..utils.interactions import error
from ..utils.logging import WebhookHandler
from ..utils.strings import codeblock
from ..web import WebServerMixin
from .cog import Cog
from .context import Context
from .help import ViewHelpCommand, help

__all__ = (
    "BotBase",
    "Bot",
    "AutoShardedBot",
)


ONE_KILOBYTE = 1024
ONE_MEGABYTE = ONE_KILOBYTE * 1024


class BotBase(commands.bot.BotBase, WebServerMixin, EmojiCacheMixin, EventSchedulerMixin, discord.Client):
    converters: dict[type[Any], Callable[..., Any]]
    pool: asyncpg.pool.Pool

    cogs: dict[str, Cog]
    owner: discord.User | None
    owners: list[discord.User] | None

    def __init__(self, *args, **kwargs) -> None:
        CONFIG = load_global_config(self)
        self._sync: bool = True

        self.start_time = datetime.datetime.now(datetime.timezone.utc)

        # Setup logging
        self.log = logging.getLogger(__name__)
        if CONFIG.LOGGING.LOG_LEVEL is not None:
            self.log.setLevel(CONFIG.LOGGING.LOG_LEVEL)

        global_log = logging.getLogger()
        if CONFIG.LOGGING.GLOBAL_LOG_LEVEL is not None:
            global_log.setLevel(CONFIG.LOGGING.GLOBAL_LOG_LEVEL)

        handler: logging.Handler

        if CONFIG.LOGGING.LOG_TO_FILE:
            handler = logging.handlers.RotatingFileHandler(f"{CONFIG.APP_NAME}.log", maxBytes=ONE_MEGABYTE, encoding="utf-8")
            handler.setFormatter(logging.Formatter("{asctime} - {module}:{levelname} - {message}", style="{"))
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

        if CONFIG.APPLICATION.ID is not None:
            kwargs["application_id"] = CONFIG.APPLICATION.ID

        super().__init__(
            *args,
            command_prefix=prefix,
            help_command=ViewHelpCommand(),
            allowed_mentions=allowed_mentions,
            intents=intents,
            **kwargs,
        )
        self.tree.error(self.on_application_command_error)

        # Add extra converters
        self.converters |= CONVERTERS

    async def sync_commands(self) -> None:
        try:
            with open(CONFIG.APPLICATION.COMMANDS_CACHE_PATH, "r") as f:
                command_cache = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            command_cache = {}

        guilds: set[discord.Object | None] = {None}

        for guild_id in set(self.tree._guild_commands.keys()):
            guilds.add(discord.Object(id=guild_id))

        for guild in guilds:
            payload = [cmd.to_dict(self.tree) for cmd in self.tree.get_commands(guild=guild)]
            guild_id = str(guild.id) if guild is not None else "-1"

            if command_cache.get(guild_id) != payload:
                try:
                    await self.tree.sync(guild=guild)
                    command_cache[guild_id] = payload
                except discord.HTTPException:
                    self.log.exception(f"Failed syncing for guild {guild}: ")
                    self.log.error(f"Payload: {json.dumps(payload, indent=4)}")

        with open(CONFIG.APPLICATION.COMMANDS_CACHE_PATH, "w") as f:
            json.dump(command_cache, f, indent=4)

    async def setup_hook(self) -> None:
        # we need to do this later because asyncio.loop doesn't exist at before this point
        global_log = logging.getLogger()
        if CONFIG.LOGGING.WEBHOOK_URI is not None:
            handler = WebhookHandler(CONFIG.LOGGING.WEBHOOK_URI)
            global_log.addHandler(handler)

        await self.is_owner(discord.Object(id=0))  # type: ignore

        # Add help command
        self.tree.add_command(help)

        # Add extensions
        for extension in CONFIG.EXTENSIONS.keys():
            try:
                await self.load_extension(extension)
            except (commands.ExtensionError, ImportError, SyntaxError):
                self.log.exception(f"Failed to load extension {extension}")

        self.pool = await setup_database()

        # sync slash commands
        if CONFIG.APPLICATION.AUTO_SYNC_COMMANDS:
            await self.sync_commands()

        await super().setup_hook()

    @property
    def uptime(self) -> datetime.timedelta:
        return datetime.datetime.now(datetime.timezone.utc) - self.start_time

    async def on_ready(self) -> None:
        self.log.info(f"Succesfully logged in as {self.user} ({getattr(self.user, 'id')})")

        if self.owner_id:
            self.owner = await self.fetch_user(self.owner_id)
            self.owners = []
        if self.owner_ids:
            self.owner = None
            self.owners = [await self.fetch_user(id) for id in self.owner_ids]

    async def on_application_command_error(
        self: BotBase,
        interaction: discord.Interaction,
        exception: BaseException,
    ) -> None:
        colour = discord.Colour.dark_red()
        with suppress(Exception):
            if interaction.command is None:
                title = "Unexpected error"
            else:
                if isinstance(exception, discord.app_commands.CheckFailure):
                    if interaction.response.is_done():
                        return
                    title = "You don't have permission to use this command."
                    colour = discord.Colour.red()
                elif isinstance(exception, discord.app_commands.TransformerError):
                    title = "Invalid value for argument."
                    colour = discord.Colour.orange()
                    exception = exception.__cause__ or Exception("Unknown error")
                else:
                    title = f"Unexpected error with command {interaction.command.name}"

            await error(
                interaction,
                message=codeblock(f"{type(exception).__name__}: {exception}", language="py"),
                title=title,
                colour=colour,
            )

        if colour == discord.Colour.dark_red():
            tb = "".join(traceback.format_exception(type(exception), exception, exception.__traceback__))
            self.log.error(
                f"Unhandled exception in command: {interaction.command.name if interaction.command is not None else 'UNKNOWN'}\n\n{type(error).__name__}: {error}\n\n{tb}"
            )

    async def on_command_error(self, ctx: Context, error: BaseException) -> None:
        if isinstance(error, commands.CommandNotFound) or ctx.command is None:
            return

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
            await ctx.send(
                embed=discord.Embed(
                    color=discord.Colour.red(),
                    title=f"Error with command {ctx.command.qualified_name}",
                    description=str(error),
                )
            )
            return

        if error.__cause__ is None:
            return

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

    async def process_commands(self, message: discord.Message) -> None:
        if CONFIG.BOT.IGNORE_BOTS and message.author.bot:
            return

        if message.author == self.user:
            return

        ctx = await self.get_context(message, cls=Context)
        await self.invoke(ctx)

    def run(self):
        if CONFIG.BOT.TOKEN is None:
            raise RuntimeError("You haven't set your bots token, do so with a config override.")

        super().run(CONFIG.BOT.TOKEN)

    async def close(self):
        if not CONFIG.DATABASE.DISABLED:
            await self.pool.close()
        await super().close()


class Bot(BotBase, commands.Bot): ...


class AutoShardedBot(BotBase, commands.AutoShardedBot): ...
