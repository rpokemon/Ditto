from __future__ import annotations

from functools import wraps
from typing import TYPE_CHECKING, Any, Callable, Coroutine, Optional, TypeVar

import discord
from ditto import CONFIG
from ditto.types import User
from ditto.utils.slash.utils import error

if TYPE_CHECKING:
    from typing_extensions import Concatenate, ParamSpec


T = TypeVar("T")

C = TypeVar("C", bound=discord.Client)

if TYPE_CHECKING:
    P = ParamSpec("P")

    SlashCommand = Callable[Concatenate[C, discord.Interaction, P], Coroutine[Any, Any, T]]


__all__ = (
    "Prompt",
    "confirm",
)


class Prompt(discord.ui.View):
    def __init__(self, user: User, *, timeout: Optional[float] = 60):
        super().__init__(timeout=timeout)
        self.user: User = user
        self.response: Optional[bool] = None

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user != self.user:
            await error(interaction, "You are notthe user who initiated this interaction.")
            return False
        return True

    async def disable(self, interaction: discord.Interaction) -> None:
        for item in self.children:
            if isinstance(item, discord.ui.Button):
                item.disabled = True
        await interaction.response.edit_message(view=self)
        self.stop()

    @discord.ui.button(label="Yes", style=discord.ButtonStyle.red)
    async def yes(self, button: discord.ui.Button, interaction: discord.Interaction) -> None:
        self.response = True
        await self.disable(interaction)

    @discord.ui.button(label="No", style=discord.ButtonStyle.blurple)
    async def no(self, button: discord.ui.Button, interaction: discord.Interaction) -> None:
        self.response = False
        await self.disable(interaction)


def confirm(
    message: str, ephemeral: bool = True
) -> Callable[[SlashCommand[C, P, T]], SlashCommand[C, P, Optional[T]]]:
    def inner(func: SlashCommand[C, P, T]) -> SlashCommand[C, P, Optional[T]]:
        @wraps(func)
        async def wrapper(
            client: C, interaction: discord.Interaction, *args: P.args, **kwargs: P.kwargs
        ) -> Optional[T]:
            assert interaction.user is not None

            prompt = Prompt(interaction.user)
            await interaction.response.send_message(message, view=prompt, ephemeral=ephemeral)
            await prompt.wait()

            if prompt.response is None:
                return await error(interaction, "Timed-out while waiting for a response.")
            if prompt.response is False:
                return await error(interaction, "Canceled.")

            return await func(client, interaction, *args, **kwargs)

        return wrapper

    return inner
