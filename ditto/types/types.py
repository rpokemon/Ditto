from typing import Union

import discord


__all__ = (
    "Emoji",
    "TextChannel",
    "VocalGuildChannel",
    "PrivateChannel",
    "MessageableGuildChannel",
    "NonVocalGuildChannel",
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


PrivateChannel = Union[
    discord.DMChannel,
    discord.GroupChannel,
]


VocalGuildChannel = Union[
    discord.VoiceChannel,
    discord.StageChannel,
]


MessageableGuildChannel = Union[
    discord.TextChannel,
    discord.Thread,
]


NonVocalGuildChannel = Union[
    MessageableGuildChannel,
    discord.CategoryChannel,
    discord.StoreChannel,
]


GuildChannel = Union[
    VocalGuildChannel,
    NonVocalGuildChannel,
]


TextChannel = Union[
    PrivateChannel,
    MessageableGuildChannel,
    discord.abc.Messageable,
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
