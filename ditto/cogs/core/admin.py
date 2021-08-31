import discord
from discord.ext import commands
from jishaku.codeblocks import Codeblock

from ... import BotBase, Cog, Context
from ...config import load_global_config
from ...types import Extension


class Admin(Cog, hidden=True):
    """Bot administration commands."""

    async def cog_check(self, ctx: Context) -> bool:
        return await commands.is_owner().predicate(ctx)

    @property
    def display_emoji(self) -> discord.PartialEmoji:
        return discord.PartialEmoji(name="\N{GEAR}")

    @commands.command()
    async def eval(self, ctx: Context, *, code: Codeblock) -> None:
        """Evaluates python code.
        `code`: Python code to run.
        """
        jsk_py = self.bot.get_command("jsk python")
        if jsk_py is None:
            raise commands.CommandNotFound()
        else:
            await ctx.invoke(jsk_py, argument=code)  # type: ignore

    @commands.command(aliases=["sh"])
    async def shell(self, ctx: Context, *, code: Codeblock) -> None:
        """Executes a command in the shell.
        `code`: The command to run.
        """
        jsk_py = self.bot.get_command("jsk sh")
        if jsk_py is None:
            raise commands.CommandNotFound()
        else:
            await ctx.invoke(jsk_py, argument=code)  # type: ignore

    @commands.command()
    async def git(self, ctx: Context, *, code: Codeblock) -> None:
        """Executes a git command.
        `code`: The command to run.
        """
        jsk_git = self.bot.get_command("jsk git")
        if jsk_git is None:
            raise commands.CommandNotFound()
        else:
            await ctx.invoke(jsk_git, argument=code)  # type: ignore

    @commands.command()
    async def poetry(self, ctx: Context, *, code: Codeblock) -> None:
        """Executes a poetry command.
        `code`: The command to run.
        """
        jsk_git = self.bot.get_command("jsk sh")
        if jsk_git is None:
            raise commands.CommandNotFound()
        else:
            await ctx.invoke(jsk_git, argument=Codeblock(None, f"poetry {code.content}"))  # type: ignore

    @commands.command()
    async def pip(self, ctx: Context, *, code: Codeblock) -> None:
        """Executes a pip command.
        `code`: The command to run.
        """
        jsk_git = self.bot.get_command("jsk sh")
        if jsk_git is None:
            raise commands.CommandNotFound()
        else:
            await ctx.invoke(jsk_git, argument=Codeblock(None, f"poetry run pip {code.content}"))  # type: ignore

    @commands.command()
    async def load(self, ctx: Context, *extensions: Extension) -> None:
        """Load extensions.
        `extensions`: The extensions to load.
        """
        jsk_load = self.bot.get_command("jsk load")
        if jsk_load is None:
            raise commands.CommandNotFound()
        else:
            await ctx.invoke(jsk_load, *extensions)  # type: ignore

    @commands.command()
    async def unload(self, ctx: Context, *extensions: Extension) -> None:
        """Unload extensions.
        `extensions`: The extensions to unload.
        """
        jsk_unload = self.bot.get_command("jsk unload")
        if jsk_unload is None:
            raise commands.CommandNotFound()
        else:
            await ctx.invoke(jsk_unload, *extensions)  # type: ignore

    @commands.group(invoke_without_command=False)
    async def reload(self, ctx: Context, *extensions: Extension) -> None:
        """Reload extensions.
        `extensions`: The extensions to reload.
        """
        jsk_reload = self.bot.get_command("jsk reload")
        if jsk_reload is None:
            raise commands.CommandNotFound()
        else:
            await ctx.invoke(jsk_reload, *extensions)  # type: ignore

    @reload.command(name="config")
    async def reload_config(self, ctx: Context):
        """Reload the bot configuration."""
        load_global_config(self.bot)

    @commands.command(aliases=["logout", "exit"])
    async def restart(self, ctx: Context):
        """Restarts the bot."""
        jsk_shutdown = self.bot.get_command("jsk shutdown")
        if jsk_shutdown is None:
            await self.bot.close()
            return
        else:
            await ctx.invoke(jsk_shutdown)  # type: ignore


def setup(bot: BotBase):
    bot.add_cog(Admin(bot))
