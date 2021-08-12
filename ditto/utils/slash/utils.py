from __future__ import annotations

from functools import wraps
from typing import TYPE_CHECKING, Callable, Optional, TypeVar

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


__all__ = ("confirm",)


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
