from __future__ import annotations

from functools import wraps
from typing import TYPE_CHECKING, Any, Callable, Coroutine, Optional, TypeVar, Type, List

import discord
from discord.slash.command import BaseCommand

from ...types import SlashCommand
from ..interactions import error
from ..views import Prompt

if TYPE_CHECKING:
    from ...core.bot import BotBase
    from typing_extensions import ParamSpec


T = TypeVar("T")
C = TypeVar("C", bound=discord.Client)
CommandT = TypeVar("CommandT", bound=BaseCommand)

Coro = Coroutine[Any, Any, T]

if TYPE_CHECKING:
    P = ParamSpec("P")

    from ...core import Cog


__all__ = (
    "confirm",
    "with_cog",
    "available_commands",
    "check",
)


def confirm(
    message: str, ephemeral: bool = True
) -> Callable[[SlashCommand[C, P, T]], SlashCommand[C, P, Optional[T]]]:
    def inner(func: SlashCommand[C, P, T]) -> SlashCommand[C, P, Optional[T]]:
        @wraps(func)
        async def wrapper(
            interaction: discord.Interaction, client: C, *args: P.args, **kwargs: P.kwargs
        ) -> Optional[T]:
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

            return await func(interaction, client, *args, **kwargs)

        return wrapper

    return inner


def with_cog(cog: Type[Cog]) -> Callable[[T], T]:
    def decorator(command: T) -> T:
        command._cog = cog  # type: ignore
        return command

    return decorator


def available_commands(bot: BotBase, guild: Optional[discord.Guild] = None) -> List[discord.PartialCommand]:
    commands = []

    # Global commands
    for command in bot.application_commands:
        commands.append(command)

    return commands


def check(
    check_coro: Callable[[discord.Interaction], Coro[bool]]
) -> Callable[[Callable[[CommandT, discord.Interaction], Coro[T]]], Callable[[CommandT, discord.Interaction], Coro[Optional[T]]]]:
    
    def decorator(coro: Callable[[CommandT, discord.Interaction], Coro[T]]) -> Callable[[CommandT, discord.Interaction], Coro[Optional[T]]]:
        
        @wraps(coro)
        async def wrapper(self: CommandT, interaction: discord.Interaction) -> Optional[T]:
            if await check_coro(interaction):
                return await coro(self, interaction)

        return wrapper

    return decorator
