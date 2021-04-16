import discord
from discord.ext import commands

from ditto import BotBase, Cog, Context


class Info(Cog):
    @commands.command()
    async def about(self, ctx: Context):
        """Display some basic information about the bot."""
        await ctx.send(
            embed=discord.Embed(
                colour=ctx.me.colour,
                description=f"I am {self.bot.user}, a bot made by {self.bot.owner}. My prefix is {self.bot.prefix}.",
            ).set_author(
                name=f"About {self.bot.user.name}:", icon_url=self.bot.user.avatar_url  # type: ignore
            )
        )


def setup(bot: BotBase):
    bot.add_cog(Info(bot))
