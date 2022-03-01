from __future__ import annotations

from functools import wraps
from typing import TYPE_CHECKING, Callable, Optional, TypeVar, Type, List

import discord

from ...types import SlashCommand
from ..interactions import error
from ..views import Prompt

if TYPE_CHECKING:
    from ...core.bot import CommandTree
    from typing_extensions import ParamSpec


T = TypeVar("T")

C = TypeVar("C", bound=discord.Client)

if TYPE_CHECKING:
    P = ParamSpec("P")

    from ...core import Cog


__all__ = (
    "confirm",
    "with_cog",
    "available_commands",
)


def confirm(message: str, ephemeral: bool = True) -> Callable[[SlashCommand[P, T]], SlashCommand[P, Optional[T]]]:
    def inner(func: SlashCommand[P, T]) -> SlashCommand[P, Optional[T]]:
        @wraps(func)
        async def wrapper(interaction: discord.Interaction, *args: P.args, **kwargs: P.kwargs) -> Optional[T]:
            assert interaction.user is not None

            prompt = Prompt(interaction.user)
            await interaction.response.send_message(message, view=prompt, ephemeral=ephemeral)
            await prompt.wait()

            try:
                await interaction.delete_original_message()
            except discord.HTTPException:
                pass

            if prompt.response is None:
                return await error(interaction, "Timed-out while waiting for a response.")
            if prompt.response is False:
                return await error(interaction, "Canceled.")

            return await func(interaction, *args, **kwargs)

        return wrapper

    return inner


def with_cog(cog: Type[Cog]) -> Callable[[T], T]:
    def decorator(command: T) -> T:
        command._cog = cog  # type: ignore
        return command

    return decorator


def available_commands(
    tree: CommandTree, guild: Optional[discord.Guild] = None
) -> List[discord.app_commands.AppCommand]:
    commands = []

    # Global commands
    commands.extend(tree.get_commands(guild=None))

    # Guild specific commands
    if guild is not None:
        commands.extend(tree.get_commands(guild=guild))

    return commands
