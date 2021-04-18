import datetime
from functools import cmp_to_key
import zoneinfo

from typing import cast, Optional, Union, get_args

import discord
from discord.ext import commands

from ditto import BotBase, Context, Cog
from ditto.types import User
from ditto.db import Time_Zones

from ditto.utils.strings import utc_offset, human_friendly_timestamp


class Timezone(Cog):
    @commands.group(aliases=["time"], invoke_without_command=True)
    async def timezone(self, ctx: Context, *, argument: Optional[Union[zoneinfo.ZoneInfo, User]] = None) -> None:
        if argument is None:
            argument = zoneinfo.ZoneInfo("UTC")

        if isinstance(argument, get_args(User)):
            return await ctx.invoke(self.timezone_get, user=argument)

        argument = cast(zoneinfo.ZoneInfo, argument)

        embed = discord.Embed(title=human_friendly_timestamp(datetime.datetime.now(tz=argument)))
        embed.set_author(name=f"Time in {argument}:")

        await ctx.reply(embed=embed)

    @timezone.command(name="get")
    async def timezone_get(self, ctx: Context, *, user: Optional[User] = None) -> None:
        if user is None:
            user = ctx.author

        timezone = await Time_Zones.get_timezone(user)

        if timezone is None:
            raise commands.BadArgument(f"{user.mention} does not have a time zone set.")

        embed = discord.Embed(title=human_friendly_timestamp(datetime.datetime.now(tz=timezone)))
        embed.set_author(name=f"Time for {user.display_name}:", icon_url=str(user.avatar_url))
        embed.set_footer(text=f"{timezone} ({utc_offset(timezone)})")

        await ctx.reply(embed=embed)

    @timezone.command(name="set")
    async def timezone_set(self, ctx: Context, *, timezone: zoneinfo.ZoneInfo) -> None:
        await Time_Zones.insert(user_id=ctx.author.id, time_zone=str(timezone), update_on_conflict=Time_Zones.time_zone)  # type: ignore

        embed = discord.Embed(title=str(datetime.datetime.now(tz=timezone)))
        embed.set_author(name=f"Timezone set to {timezone}")

        await ctx.reply(embed=embed)


def setup(bot: BotBase):
    bot.add_cog(Timezone(bot))
