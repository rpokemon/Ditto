from typing import Union

import discord


__all__ = (
    "Emoji",
    "TextChannel",
    "VocalGuildChannel",
    "GuildChannel",
    "User",
    "DiscordEmoji",
    "Message",
    "DiscordObject",
)

Emoji = Union[
    discord.Emoji,
    str,
]


TextChannel = Union[
    discord.TextChannel,
    discord.DMChannel,
    discord.abc.Messageable,
]


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


DiscordEmoji = Union[
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
    DiscordEmoji,
    Message,
    discord.Invite,
]
