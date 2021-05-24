import asyncio
import datetime

from collections import Counter
from typing import Any, NamedTuple, Optional

import asyncpg
import discord
from discord.ext import commands, menus, tasks
from donphan.connection import MaybeAcquire

from ... import BotBase, Cog, Context, CONFIG
from ...db.tables import Commands

from ...utils.paginator import EmbedPaginator
from ...utils.time import human_friendly_timestamp


class CommandInvoke(NamedTuple):
    mssage_id: int
    guild_id: int
    channel_id: int
    user_id: int
    invoked_at: datetime.datetime
    prefix: str
    command: str
    failed: bool


class Stats(Cog):
    def __init__(self, bot: BotBase) -> None:
        super().__init__(bot)
        self._socket_stats: Counter[Optional[str]] = Counter()
        self._batch_lock = asyncio.Lock()
        self._batch_data: list[CommandInvoke] = []

        self.bulk_insert.add_exception_type(asyncpg.exceptions.PostgresConnectionError)
        self.bulk_insert.start()

    async def cog_check(self, ctx: Context) -> bool:
        return await commands.is_owner().predicate(ctx)

    @commands.command()
    async def command_history(self, ctx: Context) -> None:
        embed = EmbedPaginator[discord.Embed](colour=ctx.me.colour, max_fields=10)
        embed.set_author(name="Command History:", icon_url=self.bot.user.avatar.url)

        async with ctx.db as connection:
            commands = await Commands.fetch(connection, order_by=(Commands.invoked_at, "DESC"), limit=100)

        if commands:
            for command in commands:
                user = self.bot.get_user(command["user_id"]) or "Unknown user"
                embed.add_field(
                    name=f'{user} ({command["user_id"]}) @ {human_friendly_timestamp(command["invoked_at"])}',
                    value=f'`{command["prefix"]}{command["command"]}`',
                    inline=False,
                )
        else:
            embed.add_line("No commands used.")

        await menus.MenuPages(embed, delete_message_after=True).start(ctx)

    @commands.command()
    async def socket_status(self, ctx: Context) -> None:
        """Displays basic information about socket statistics."""
        total_occurunces = sum(self._socket_stats.values())
        total_per_min = total_occurunces / (self.bot.uptime.total_seconds() / 60)

        embed = discord.Embed(
            colour=ctx.me.colour, description=f"Observed {total_occurunces} socket events. ({total_per_min:.2f}/min)"
        ).set_author(name=f"{self.bot.user.name} socket event stats:", icon_url=self.bot.user.avatar.url)

        for event, occurunces in self._socket_stats.most_common(25):
            per_minute = occurunces / (self.bot.uptime.total_seconds() / 60)
            embed.add_field(name=f"`{event}`", value=f"{occurunces} ({per_minute:.2f}/min)", inline=True)

        await ctx.send(embed=embed)

    @commands.Cog.listener()
    async def on_socket_response(self, msg: dict[str, Any]):
        self._socket_stats[msg.get("t")] += 1

    @commands.Cog.listener("on_command_completion")
    @commands.Cog.listener("on_command_error")
    async def on_command(self, ctx: Context, error: BaseException = None) -> None:
        command = ctx.command

        if command is None:
            return

        guild_id = getattr(ctx.guild, "id", None)

        invoke = CommandInvoke(
            ctx.message.id,
            guild_id,
            ctx.channel.id,
            ctx.author.id,
            ctx.message.created_at,
            ctx.prefix,
            command.qualified_name,
            ctx.command_failed,
        )

        async with self._batch_lock:
            self._batch_data.append(invoke)

    @tasks.loop(seconds=15)
    async def bulk_insert(self) -> None:
        async with self._batch_lock:
            if self._batch_data:
                async with MaybeAcquire(pool=self.bot.pool) as connection:
                    await Commands.insert_many(connection, Commands._columns, *self._batch_data)
                self._batch_data.clear()


def setup(bot: BotBase):
    if CONFIG.DATABASE.DISABLED:
        return
    bot.add_cog(Stats(bot))
