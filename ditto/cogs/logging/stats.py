import asyncio
import datetime
from collections import Counter
from typing import Any, TypedDict

import asyncpg
import discord
from discord.ext import commands, menus, tasks

from ... import CONFIG, BotBase, Cog, Context
from ...db.tables import Commands
from ...utils.paginator import EmbedPaginator
from ...utils.time import human_friendly_timestamp


class CommandInvoke(TypedDict):
    message_id: int
    guild_id: int | None
    channel_id: int
    user_id: int
    invoked_at: datetime.datetime
    prefix: str
    command: str
    failed: bool


class Stats(Cog, hidden=True):
    """Bot stats commands."""

    @property
    def display_emoji(self) -> discord.PartialEmoji:
        return discord.PartialEmoji(name="\N{BAR CHART}")

    def __init__(self, bot: BotBase) -> None:
        super().__init__(bot)
        self._command_stats: Counter[str] = Counter()
        self._socket_stats: Counter[str | None] = Counter()
        self._batch_lock = asyncio.Lock()
        self._batch_data: list[CommandInvoke] = []

        self.bulk_insert_task.add_exception_type(asyncpg.exceptions.PostgresConnectionError)
        self.bulk_insert_task.start()

    async def cog_check(self, ctx: Context) -> bool:
        return await commands.is_owner().predicate(ctx)

    @commands.command()
    async def command_history(self, ctx: Context) -> None:
        """Shows recent command invoke history."""
        embed = EmbedPaginator[discord.Embed](colour=ctx.me.colour, max_fields=10)
        embed.set_author(name="Command History:", icon_url=ctx.me.display_avatar.url)

        async with self.bot.pool.acquire() as connection:
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
    async def command_stats(self, ctx: Context) -> None:
        """Displays basic information about command invocation statistics."""
        total_occurunces = sum(self._command_stats.values())
        total_per_min = total_occurunces / (self.bot.uptime.total_seconds() / 60)

        embed = discord.Embed(
            colour=ctx.me.colour,
            description=f"Processed {total_occurunces} command invokes. ({total_per_min:.2f}/min)",
        ).set_author(name=f"{ctx.me} command stats:", icon_url=ctx.me.display_avatar.url)

        for event, occurunces in self._command_stats.most_common(25):
            per_minute = occurunces / (self.bot.uptime.total_seconds() / 60)
            embed.add_field(name=f"`{event}`", value=f"{occurunces} ({per_minute:.2f}/min)", inline=True)

        await ctx.send(embed=embed)

    @commands.command()
    async def socket_stats(self, ctx: Context) -> None:
        """Displays basic information about socket statistics."""
        total_occurunces = sum(self._socket_stats.values())
        total_per_min = total_occurunces / (self.bot.uptime.total_seconds() / 60)

        embed = discord.Embed(
            colour=ctx.me.colour, description=f"Observed {total_occurunces} socket events. ({total_per_min:.2f}/min)"
        ).set_author(name=f"{ctx.me.name} socket event stats:", icon_url=ctx.me.display_avatar.url)

        for event, occurunces in self._socket_stats.most_common(25):
            per_minute = occurunces / (self.bot.uptime.total_seconds() / 60)
            embed.add_field(name=f"`{event}`", value=f"{occurunces} ({per_minute:.2f}/min)", inline=True)

        await ctx.send(embed=embed)

    @commands.Cog.listener()
    async def on_socket_response(self, msg: dict[str, Any]):
        self._socket_stats[msg.get("t")] += 1

    @commands.Cog.listener("on_command_completion")
    @commands.Cog.listener("on_command_error")
    async def on_command(self, ctx: Context, error: BaseException | None = None) -> None:
        assert ctx.prefix is not None

        if ctx.command is None:
            return

        guild_id = getattr(ctx.guild, "id", None)

        self._command_stats[ctx.command.qualified_name] += 1

        async with self._batch_lock:
            self._batch_data.append(
                {
                    "message_id": ctx.message.id,
                    "guild_id": guild_id,
                    "channel_id": ctx.channel.id,
                    "user_id": ctx.author.id,
                    "invoked_at": ctx.message.created_at,
                    "prefix": ctx.prefix,
                    "command": ctx.command.qualified_name,
                    "failed": ctx.command_failed,
                }
            )

    @tasks.loop(seconds=15)
    async def bulk_insert_task(self) -> None:
        async with self._batch_lock:
            if self._batch_data:
                async with self.bot.pool.acquire() as connection:
                    await Commands.insert_many(connection, None, *self._batch_data)  # type: ignore
                    self._batch_data.clear()

    @bulk_insert_task.before_loop
    async def before_bulk_insert_task(self):
        await self.bot.wait_until_ready()


async def setup(bot: BotBase):
    if CONFIG.DATABASE.DISABLED:
        return
    await bot.add_cog(Stats(bot))
