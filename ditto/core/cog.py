from discord.ext import commands

from .bot import BotBase

__all__ = ("Cog",)


class Cog(commands.Cog):
    def __init__(self, bot: BotBase) -> None:
        self.bot = bot
