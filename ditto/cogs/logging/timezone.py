import datetime
import zoneinfo

from typing import Any, cast, Optional, Union, get_args

import discord
from discord.ext import commands, menus

from ... import BotBase, Context, Cog
from ...types import User
from ...db import Time_Zones

from ...utils.paginator import EmbedPaginator
from ...utils.strings import utc_offset
from ...utils.time import MAIN_TIMEZONES, human_friendly_timestamp


class Timezone(Cog):
    @commands.group(aliases=["time"], invoke_without_command=True)
    async def timezone(self, ctx: Context, *, argument: Optional[Union[zoneinfo.ZoneInfo, User]] = None) -> None:
        """Get the current time for a user or time zone."""
        if argument is None:
            argument = zoneinfo.ZoneInfo("UTC")

        if isinstance(argument, get_args(User)):
            return await ctx.invoke(self.timezone_get, user=argument)

        argument = cast(zoneinfo.ZoneInfo, argument)

        embed = discord.Embed(title=human_friendly_timestamp(datetime.datetime.now(tz=argument)))
        embed.set_author(name=f"Time in {argument}")

        await ctx.reply(embed=embed)

    @timezone.command(name="get")
    async def timezone_get(self, ctx: Context, *, user: Optional[User] = None) -> None:
        """Get a user's time zone."""
        if user is None:
            user = ctx.author

        timezone = await Time_Zones.get_timezone(user)

        if timezone is None:
            raise commands.BadArgument(f"{user.mention} does not have a time zone set.")

        embed = discord.Embed(title=human_friendly_timestamp(datetime.datetime.now(tz=timezone)))
        embed.set_author(name=f"Time for {user.display_name}", icon_url=str(user.avatar.url))
        embed.set_footer(text=f"{timezone} ({utc_offset(timezone)})")

        await ctx.reply(embed=embed)

    @timezone.command(name="set")
    async def timezone_set(self, ctx: Context, *, timezone: zoneinfo.ZoneInfo) -> None:
        """Set your time zone."""
        await Time_Zones.insert(
            user_id=ctx.author.id, time_zone=str(timezone), update_on_conflict=Time_Zones.time_zone
        )

        local_time = human_friendly_timestamp(datetime.datetime.now(tz=timezone))
        embed = discord.Embed(title=f"Local Time: {local_time}")
        embed.set_author(name=f"Timezone set to {timezone}")

        await ctx.reply(embed=embed)

    @timezone.command(name="list")
    async def timezone_list(self, ctx: Context) -> None:
        """List all avilable time zones."""
        embed = EmbedPaginator[discord.Embed](max_description=512)

        def get_offset(t: tuple[Any, zoneinfo.ZoneInfo]) -> float:
            _, tzinfo = t

            now = datetime.datetime.now(datetime.timezone.utc)

            offset = tzinfo.utcoffset(now)
            if offset is not None:
                return offset.total_seconds()
            return 0

        for name, tzinfo in sorted(MAIN_TIMEZONES.items(), key=get_offset):
            embed.add_line(f"`{name}` ({utc_offset(tzinfo)})")

        await menus.MenuPages(embed).start(ctx)

    @commands.command()
    async def timezones(self, ctx: Context) -> None:
        return await ctx.invoke(self.timezone_list)

    timezones.__doc__ = timezone_list.__doc__


def setup(bot: BotBase):
    bot.add_cog(Timezone(bot))
