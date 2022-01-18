import discord

from .utils import error, check

__all__ = (
    "guild_only",
    "dm_only",
)


@check
async def guild_only(interaction: discord.Interaction) -> bool:
    if interaction.guild_id is None:
        await error(interaction, "This command must be used in a server.")
        return False
    return True


@check
async def dm_only(interaction: discord.Interaction) -> bool:
    if interaction.guild_id is not None:
        await error(interaction, "This command can only be used in private messages.")
        return False
    return True
