from __future__ import annotations

from typing import TYPE_CHECKING, Any, Callable, Coroutine, TypeVar, Union

import discord

if TYPE_CHECKING:
    from typing_extensions import Concatenate, ParamSpec


T = TypeVar("T")

C = TypeVar("C", bound=discord.Client)

if TYPE_CHECKING:
    P = ParamSpec("P")
else:
    P = TypeVar("P")

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
    "Mentionable",
    "DiscordObject",
    "SlashCommand",
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


Mentionable = Union[
    User,
    discord.Role,
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
    GuildChannel,
    Mentionable,
    DiscordEmoji,
    Message,
    discord.Invite,
    discord.Command,
]

if TYPE_CHECKING:
    SlashCommand = Callable[Concatenate[C, discord.Interaction, P], Coroutine[Any, Any, T]]
else:
    SlashCommand = Union[C, P, T]
