from __future__ import annotations

from typing import TYPE_CHECKING, Any, Callable, Coroutine, TypeVar, Union

import discord

if TYPE_CHECKING:
    from typing_extensions import Concatenate, ParamSpec


T = TypeVar("T")

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
    "ChatInputCommand",
    "AppCommand",
    "AppCommandFunc",
    "AppCommandChannel",
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
    discord.ForumChannel,
]


GuildChannel = Union[
    VocalGuildChannel,
    NonVocalGuildChannel,
]


AppCommandChannel = Union[
    discord.app_commands.AppCommandChannel,
    discord.app_commands.AppCommandThread,
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
    AppCommandChannel,
]


ChatInputCommand = Union[discord.app_commands.Command[Any, ... if TYPE_CHECKING else Any, Any], discord.app_commands.Group]

AppCommand = Union[
    ChatInputCommand,
    discord.app_commands.ContextMenu,
]


if TYPE_CHECKING:
    AppCommandFunc = Callable[Concatenate[discord.Interaction, P], Coroutine[Any, Any, T]]
else:
    AppCommandFunc = Union[P, T]


CheckFunc = Callable[[discord.Interaction], Coroutine[Any, Any, bool]]
