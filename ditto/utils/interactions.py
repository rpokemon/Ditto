from __future__ import annotations

import asyncio
from contextlib import suppress

from typing import Any, Coroutine, TYPE_CHECKING, get_args


import discord

if TYPE_CHECKING:
    from discord.types.interactions import (
        ApplicationCommandInteractionData as ApplicationCommandInteractionDataPayload,
    )


__all___ = (
    "delete_after",
    "error",
    "send_message",
)


def send_message(interaction: discord.Interaction, *args: Any, **kwargs: Any) -> Coroutine[Any, Any, Any]:
    send_func = interaction.followup.send if interaction.response.is_done() else interaction.response.send_message
    if send_func is interaction.followup.send:
        kwargs.pop("ephemeral")
    return send_func(*args, **kwargs)


async def _delete_after(interaction: discord.Interaction, after: float) -> None:
    await asyncio.sleep(after)
    with suppress(discord.NotFound):
        await interaction.delete_original_message()


def delete_after(interaction: discord.Interaction, after: float) -> None:
    asyncio.create_task(_delete_after(interaction, after))


def error(interaction: discord.Interaction, message: str) -> Coroutine[Any, Any, Any]:
    if TYPE_CHECKING:
        assert isinstance(interaction.data, get_args(ApplicationCommandInteractionDataPayload))
    return send_message(
        interaction,
        embed=discord.Embed(
            colour=discord.Colour.red(),
            title=f"Error with command {interaction.data['name']}",  # type: ignore
            description=message,
        ),
        ephemeral=True,
    )
