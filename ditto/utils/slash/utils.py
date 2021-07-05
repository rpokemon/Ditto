from typing import Any, Coroutine

import discord
from discord.types.interactions import ApplicationCommandInteractionData as ApplicationCommandInteractionDataPayload


def send_message(interaction: discord.Interaction, *args: Any, **kwargs: Any) -> Coroutine[Any, Any, Any]:
    send_func = interaction.followup.send if interaction.response.is_done() else interaction.response.send_message
    if send_func is interaction.followup.send:
        kwargs.pop("ephemeral")
    return send_func(*args, **kwargs)


def error(interaction: discord.Interaction, message: str) -> Coroutine[Any, Any, Any]:
    assert isinstance(interaction.data, ApplicationCommandInteractionDataPayload)
    return send_message(
        interaction,
        embed=discord.Embed(
            colour=discord.Colour.red(),
            title=f"Error with command {interaction.data['name']}",
            description=message,
        ),
        ephemeral=True,
    )
