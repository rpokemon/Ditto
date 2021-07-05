import discord

from .utils import error

__all__ = (
    "guild_only",
    "dm_only",
)


async def guild_only(client: discord.Client, interaction: discord.Interaction) -> bool:
    if interaction.guild_id is None:
        await error(interaction, "This command must be used in a server.")
        return False
    return True


async def dm_only(client: discord.Client, interaction: discord.Interaction) -> bool:
    if interaction.guild_id is not None:
        await error(interaction, "This command can only be used in private messages.")
        return False
    return True
