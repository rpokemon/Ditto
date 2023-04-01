from __future__ import annotations

from functools import wraps
from typing import TYPE_CHECKING, Any, Callable, Iterable, List, NoReturn, Optional, Type, TypeVar, Union

import discord
from discord.utils import MISSING

from ...types import AppCommand, ChatInputCommand
from ..interactions import error
from ..views import Prompt
from . import checks as checks

if TYPE_CHECKING:
    from typing_extensions import ParamSpec


T = TypeVar("T")

C = TypeVar("C", bound=discord.Client)

if TYPE_CHECKING:
    P = ParamSpec("P")

    from ...core import BotBase, Cog


__all__ = (
    "confirm",
    "with_cog",
    "available_commands",
)


def confirm(message: str, ephemeral: bool = True) -> Callable[[T], T]:
    @discord.app_commands.check
    async def check(interaction: discord.Interaction) -> bool:
        assert interaction.user is not None

        prompt = Prompt(interaction.user)
        await interaction.response.send_message(message, view=prompt, ephemeral=ephemeral)
        await prompt.wait()

        try:
            await interaction.delete_original_response()
        except discord.HTTPException:
            pass

        if prompt.response is None:
            await error(interaction, "Timed-out while waiting for a response.")
        if prompt.response is False:
            await error(interaction, "Canceled.")

        return prompt.response is True

    return check


def with_cog(cog: Type[Cog]) -> Callable[[T], T]:
    def decorator(command: T) -> T:
        command.__ditto_cog__ = cog  # type: ignore
        return command

    return decorator


def available_commands(
    tree: discord.app_commands.CommandTree, guild: Optional[discord.Guild] = None
) -> List[ChatInputCommand]:
    # Global commands
    commands = tree.get_commands(guild=None, type=discord.AppCommandType.chat_input)

    # Guild specific commands
    if guild is not None:
        commands.extend(tree.get_commands(guild=guild, type=discord.AppCommandType.chat_input))

    return commands


def add_commands(
    bot: BotBase,
    commands: Iterable[AppCommand],
    *,
    guild: Optional[discord.abc.Snowflake] = MISSING,
    guilds: List[discord.abc.Snowflake] = MISSING,
) -> None:
    for command in commands:
        bot.tree.add_command(command, guild=guild, guilds=guilds)


def remove_commands(
    bot: BotBase,
    commands: Iterable[AppCommand],
    *,
    guild: Optional[discord.abc.Snowflake] = None,
) -> None:
    for command in commands:
        bot.tree.remove_command(
            command.name,
            type=getattr(command, "type", discord.AppCommandType.chat_input),
            guild=guild,
        )
