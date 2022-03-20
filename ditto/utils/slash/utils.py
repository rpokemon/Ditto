from __future__ import annotations

from functools import wraps
from typing import TYPE_CHECKING, Any, Callable, List, NoReturn, Optional, Type, TypeVar, Union

import discord

from ...types import SlashCommand
from ..interactions import error
from ..views import Prompt

if TYPE_CHECKING:
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
    "transformer_error",
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
        command.__ditto_cog__ = cog  # type: ignore
        return command

    return decorator


def available_commands(
    tree: discord.app_commands.CommandTree, guild: Optional[discord.Guild] = None
) -> List[Union[discord.app_commands.Command[Any, ..., Any], discord.app_commands.Group]]:

    # Global commands
    commands = tree.get_commands(guild=None)

    # Guild specific commands
    if guild is not None:
        commands.extend(tree.get_commands(guild=guild))

    return commands


def transformer_error(transformer: Type[discord.app_commands.Transformer], value: Any, exc: BaseException) -> NoReturn:
    raise discord.app_commands.TransformerError(value, transformer.type(), transformer) from exc
