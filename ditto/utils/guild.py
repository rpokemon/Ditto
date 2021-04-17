import discord

from ditto.types import User


__all__ = ("user_in_guild",)


async def user_in_guild(guild: discord.Guild, user: User) -> bool:
    if guild.get_member(user.id) is not None:
        return True

    try:
        await guild.fetch_member(user.id)
    except discord.NotFound:
        return False

    return True
