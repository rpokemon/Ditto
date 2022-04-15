from __future__ import annotations

from functools import wraps
from typing import TYPE_CHECKING, Any, Callable, Iterable, List, NoReturn, Optional, Type, TypeVar, Union

import discord
from discord.utils import MISSING

from ...types import AppCommandFunc, ChatInputCommand, AppCommand
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
    "transformer_error",
)


def confirm(message: str, ephemeral: bool = True) -> Callable[[AppCommandFunc[P, T]], AppCommandFunc[P, Optional[T]]]:
    def inner(func: AppCommandFunc[P, T]) -> AppCommandFunc[P, Optional[T]]:
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
        command.__ditto_cog__ = cog  # type: ignore
        return command

    return decorator


def available_commands(
    tree: discord.app_commands.CommandTree, guild: Optional[discord.Guild] = None
) -> List[ChatInputCommand]:

    # Global commands
    commands = tree.get_commands(guild=None)

    # Guild specific commands
    if guild is not None:
        commands.extend(tree.get_commands(guild=guild))

    return commands


def transformer_error(transformer: Type[discord.app_commands.Transformer], value: Any, exc: BaseException) -> NoReturn:
    raise discord.app_commands.TransformerError(value, transformer.type(), transformer) from exc


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
