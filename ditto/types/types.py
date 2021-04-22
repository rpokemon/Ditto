from typing import Union

import discord


__all__ = (
    "VocalGuildChannel",
    "GuildChannel",
    "User",
    "Emoji",
    "Message",
    "DiscordObject",
)

VocalGuildChannel = Union[
    discord.VoiceChannel,
    discord.StageChannel,
]


GuildChannel = Union[
    discord.TextChannel,
    VocalGuildChannel,
    discord.CategoryChannel,
    discord.StoreChannel,
]

User = Union[
    discord.Member,
    discord.User,
]

Emoji = Union[
    discord.Emoji,
    discord.PartialEmoji,
]

Message = Union[
    discord.Message,
    discord.PartialMessage,
]

DiscordObject = Union[
    discord.Guild,
    discord.Role,
    GuildChannel,
    User,
    Emoji,
    Message,
    discord.Invite,
]
