from __future__ import annotations

from collections.abc import Callable, Coroutine
from typing import TYPE_CHECKING, Any, TypeAlias, TypeVar

import discord

if TYPE_CHECKING:
    from typing_extensions import Concatenate, ParamSpec


T = TypeVar("T")

if TYPE_CHECKING:
    P = ParamSpec("P")
else:
    P = TypeVar("P")

__all__ = (
    "DiscordEmoji",
    "Emoji",
    "TextChannel",
    "VocalGuildChannel",
    "PrivateChannel",
    "MessageableGuildChannel",
    "NonVocalGuildChannel",
    "GuildChannel",
    "User",
    "Message",
    "Mentionable",
    "DiscordObject",
    "ChatInputCommand",
    "AppCommand",
    "AppCommandFunc",
    "AppCommandChannel",
)


DiscordEmoji: TypeAlias = discord.Emoji | discord.PartialEmoji
Emoji: TypeAlias = DiscordEmoji | str
PrivateChannel: TypeAlias = discord.DMChannel | discord.GroupChannel
VocalGuildChannel: TypeAlias = discord.VoiceChannel | discord.StageChannel
NonVocalMessageableGuildChannel: TypeAlias = discord.TextChannel | discord.Thread
MessageableGuildChannel: TypeAlias = NonVocalMessageableGuildChannel | discord.VoiceChannel
NonVocalGuildChannel: TypeAlias = NonVocalMessageableGuildChannel | discord.CategoryChannel | discord.ForumChannel
GuildChannel: TypeAlias = VocalGuildChannel | NonVocalGuildChannel
AppCommandChannel: TypeAlias = discord.app_commands.AppCommandChannel | discord.app_commands.AppCommandThread
TextChannel: TypeAlias = PrivateChannel | MessageableGuildChannel | discord.abc.Messageable
User: TypeAlias = discord.Member | discord.User
Mentionable: TypeAlias = User | discord.Role
Message: TypeAlias = discord.Message | discord.PartialMessage

DiscordObject: TypeAlias = (
    discord.Guild | GuildChannel | Mentionable | DiscordEmoji | Message | discord.Invite | AppCommandChannel
)

ChatInputCommand: TypeAlias = discord.app_commands.Command[Any, ..., Any] | discord.app_commands.Group
AppCommand: TypeAlias = ChatInputCommand | discord.app_commands.ContextMenu

if TYPE_CHECKING:
    AppCommandFunc: TypeAlias = Callable[Concatenate[discord.Interaction, P], Coroutine[Any, Any, T]]
else:
    AppCommandFunc = P | T

CheckFunc: TypeAlias = Callable[[discord.Interaction], Coroutine[Any, Any, bool]]
