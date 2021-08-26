from __future__ import annotations

from typing import TYPE_CHECKING, Any, ClassVar, TypeVar, Type, List

import discord
from discord.ext import commands

if TYPE_CHECKING:
    from .bot import BotBase

__all__ = ("Cog",)


CogT = TypeVar("CogT", bound="Cog")


class CogMeta(commands.CogMeta):
    __cog_hidden__: ClassVar[bool]

    def __new__(cls: Type[CogMeta], *args: Any, **kwargs: Any) -> CogMeta:
        name, bases, attrs = args

        hidden = kwargs.pop("hidden", False)
        attrs["__cog_hidden__"] = hidden

        return super().__new__(cls, name, bases, attrs, **kwargs)  # type: ignore

    @property
    def hidden(self) -> bool:
        """:class:`bool`: Whether this cog is hidden from help."""
        return self.__cog_hidden__


class Cog(commands.Cog, metaclass=CogMeta):
    __cog_hidden__: ClassVar[bool]

    def __init__(self, bot: BotBase) -> None:
        self.bot = bot

    @property
    def display_emoji(self) -> discord.PartialEmoji:
        raise NotImplementedError
