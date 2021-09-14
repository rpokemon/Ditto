from __future__ import annotations

from typing import TYPE_CHECKING, Annotated, Any, DefaultDict, Dict, List, Optional, Union

import discord
from discord.ext import commands

from .context import Context
from ..utils.paginator import PaginatorSource, EmbedPaginator
from ..utils.views import EmbedPageView
from ..utils.interactions import error
from ..utils.slash.utils import available_commands

from ..types import User
from .cog import Cog

if TYPE_CHECKING:
    from .bot import BotBase
else:
    BotBase = Any


__all__ = ("HelpView", "SlashHelpView", "ViewHelpCommand", "help")


MISSING: Any = discord.utils.MISSING


Command = Union[commands.Command[Any, Any, Any], discord.slash.Command]


class HelpEmbed(discord.Embed):
    def __init__(self, bot: BotBase, command_prefix: str, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._set(self, bot, command_prefix)

    @staticmethod
    def _set(
        embed: discord.Embed,
        bot: BotBase,
        command_prefix: str,
    ) -> None:
        assert bot.user is not None
        embed.set_author(name=f"{bot.user} Help Manual", icon_url=bot.user.display_avatar.url)
        embed.set_footer(text=f"Use {command_prefix}help for more information on commands.")


class FrontPage(PaginatorSource[discord.Embed]):
    def __init__(self, bot: BotBase, command_prefix: str, *args: Any, **kwargs: Any) -> None:
        self.bot: BotBase = bot
        self.command_prefix: str = command_prefix
        super().__init__(*args, **kwargs)

    def is_paginating(self) -> bool:
        return True

    def get_max_pages(self) -> Optional[int]:
        return 1

    async def get_page(self, page_number: int) -> discord.Embed:
        if self.command_prefix == "/":
            command_syntax = "/help command:<command_name>"
        else:
            command_syntax = f"{self.command_prefix}help <command_name>"

        return HelpEmbed(self.bot, self.command_prefix or "/").add_field(
            name="How to navigate:",
            value=f"Use the dropdown menu to select a category, then naviate through available commands page-by page.\n\
You can use `{command_syntax}` to retrieve more information on a specific command.",
        )


class CommandListSource(EmbedPaginator):
    def __init__(self, bot: BotBase, command_prefix: str, commands: List[Command]) -> None:
        super().__init__(
            max_size=6000,
            max_description=4096,
            max_fields=8,
            colour=discord.Colour.blurple(),
        )
        HelpEmbed._set(self, bot, command_prefix)

        for command in commands:
            if isinstance(command, discord.slash.Command):
                name = f"/{command.name}"
                description = command.description
            else:
                name = command.name
                description = command.short_doc

            self.add_field(name=name, value=description)


class HelpSelect(discord.ui.Select["HelpView"]):
    def __init__(self, bot: BotBase, command_prefix: str, cogs: Dict[Optional[Cog], List[Command]]) -> None:
        self.commands: Dict[Optional[Cog], List[Command]] = cogs
        self.cogs: Dict[str, Optional[Cog]] = {}
        self.bot: BotBase = bot
        self.command_prefix: str = command_prefix

        super().__init__(placeholder="Select a category...", min_values=1, max_values=1, row=0)
        self.fill_options()

    def fill_options(self) -> None:
        for cog, _ in self.commands.items():
            if cog is None:
                name = "Uncategorized"
                description = "Uncategorized commands."
                emoji = None
            elif not isinstance(cog, Cog):
                # Cog is external. e.g. Jishaku
                continue
            else:
                name = cog.qualified_name
                description = cog.description.split("\n", 1)[0] or None
                try:
                    emoji = cog.display_emoji
                except NotImplementedError:
                    emoji = None

            self.cogs[name] = cog
            self.add_option(label=name, value=name, description=description, emoji=emoji)

    async def callback(self, interaction: discord.Interaction) -> None:
        assert self.view is not None
        value = self.values[0]
        cog = self.cogs[value]
        commands = self.commands[cog]
        source = CommandListSource(self.bot, self.command_prefix, commands)
        await self.view.change_source(interaction, source)


class HelpView(EmbedPageView):
    def __init__(
        self,
        bot: BotBase,
        command_prefix: str,
        user: User,
        source: PaginatorSource[discord.Embed],
        *,
        cogs: Dict[Optional[Cog], List[Command]] = MISSING,
        timeout: Optional[float] = 180,
        ephemeral: bool = False,
    ) -> None:
        self.client: BotBase = bot
        self.command_prefix: str = command_prefix

        super().__init__(source, user=user, timeout=timeout, ephemeral=ephemeral)

        if isinstance(source, FrontPage):
            self.clear_items()
            self.add_item(HelpSelect(bot, command_prefix, cogs))
            self.add_pagination_items()

    @classmethod
    async def send(
        cls,
        ctx: Context,
        source: Optional[PaginatorSource[discord.Embed]] = None,
        *,
        cogs: Dict[Optional[Cog], List[Command]] = MISSING,
        dm_help: bool = False,
    ) -> None:
        channel = ctx.channel if not dm_help else ctx.author
        view = cls(
            bot=ctx.bot,
            command_prefix=ctx.clean_prefix,
            cogs=cogs,
            user=ctx.author,
            source=source or FrontPage(ctx.bot, command_prefix=ctx.clean_prefix),
        )
        page = await view.source.get_page(0)
        await channel.send(embed=page, view=view)


class SlashHelpView(HelpView):
    @classmethod
    async def send(
        cls,
        interaction: discord.Interaction,
        bot: BotBase,
        source: PaginatorSource[discord.Embed],
        *,
        cogs: Dict[Optional[Cog], List[Command]] = MISSING,
        ephemeral: bool = True,
    ) -> None:
        assert interaction.user is not None
        view = cls(
            bot=bot,
            command_prefix="/",
            cogs=cogs,
            user=interaction.user,
            source=source,
            ephemeral=ephemeral,
        )
        page = await view.source.get_page(0)
        await interaction.response.send_message(embed=page, view=view, ephemeral=ephemeral)


class ViewHelpCommand(commands.HelpCommand):
    context: Context

    def __init__(self, **options: Any) -> None:
        self.dm_help: bool = options.pop("dm_help", False)
        super().__init__(
            command_attrs={
                "help": "Displays help about the bot, a command, or a category",
            }
        )

    async def send_bot_help(self, mapping):

        cogs = DefaultDict[Optional[Cog], List[commands.Command]](list)

        for command in await self.filter_commands(self.context.bot.commands, sort=True):
            cogs[command.cog].append(command)

        await HelpView.send(self.context, cogs=cogs, dm_help=self.dm_help)  # type: ignore

    async def send_cog_help(self, cog):
        commands = await self.filter_commands(cog.get_commands(), sort=True)

        source = CommandListSource(self.context.bot, self.context.clean_prefix, commands)
        await HelpView.send(self.context, source, dm_help=self.dm_help)

    async def send_command_help(self, command: commands.Command) -> None:
        embed = HelpEmbed(
            self.context.bot,
            self.context.clean_prefix,
            title=command.name,
            description=f"{self.get_command_signature(command)}\n\n{command.help}",
        )

        if self.dm_help:
            target = self.context.author
        else:
            target = self.context.channel
        await target.send(embed=embed)

    async def send_group_help(self, group):
        subcommands = group.commands
        if len(subcommands) == 0:
            return await self.send_command_help(group)

        commands = await self.filter_commands(subcommands, sort=True)
        if len(commands) == 0:
            return await self.send_command_help(group)

        source = CommandListSource(self.context.bot, self.context.clean_prefix, commands)
        await HelpView.send(self.context, source, dm_help=self.dm_help)

    def get_command_signature(self, command: commands.Command) -> str:
        signature = super().get_command_signature(command)
        return f"Syntax: `{signature}`"


def slash_command_help(bot: BotBase, command: discord.slash.Command) -> discord.Embed:
    assert bot.user is not None

    syntax = f"/{command.name}"

    options = ""
    for option in command.options:
        options += f"{option.name} ({option.type.name}): {option.description}\n"

    return HelpEmbed(
        bot, "/", title=command.name, description=f"Syntax: `{syntax}`\n\n{command.description}\n{options}"
    )


@discord.slash.command()
async def help(
    interaction: discord.Interaction,
    bot: BotBase,
    command: Annotated[Optional[str], "The command or category to get help on."] = None,
    private: Annotated[bool, "Whether to invoke this command privately"] = True,
) -> None:
    """Displays help about the bot, a command, or a category"""
    cogs = DefaultDict[Optional[Cog], List[discord.slash.Command]](list)

    application_commands = available_commands(bot, interaction.guild)
    for application_command in application_commands:
        if application_command.type is discord.CommandType.chat_input:
            if application_command.name == command:
                # TODO: Display group command subcommands?
                return await interaction.response.send_message(
                    embed=slash_command_help(bot, application_command), ephemeral=private
                )

            cog = getattr(application_command, "_cog", None)
            if cog is not None:
                cog = bot.cogs.get(cog.__cog_name__, None)
            cogs[cog].append(application_command)  # type: ignore

    # Send Bot Help
    if command is None:
        source = FrontPage(bot, command_prefix="/")
        return await SlashHelpView.send(interaction, bot, source, cogs=cogs, ephemeral=private)  # type: ignore

    # Send Cog Help
    if command in bot.cogs:
        commands = cogs[bot.cogs[command]]  # type: ignore
        if commands:
            source = CommandListSource(bot, "/", commands)  # type: ignore
            await SlashHelpView.send(interaction, bot, source, ephemeral=private)  # type: ignore

    return await error(interaction, f'Could not find command or category with name "{command}"')
