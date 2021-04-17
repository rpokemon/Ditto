from discord.ext import commands

from ditto import BotBase, Context, Cog


class Timezone(Cog):
    @commands.command()
    async def get(self, ctx: Context):
        ...


def setup(bot: BotBase):
    bot.add_cog(Timezone(bot))
