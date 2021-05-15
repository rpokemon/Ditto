from typing import Any, Generic, NamedTuple, TypeVar, TypedDict

import discord
from discord.ext import commands, menus


__all__ = (
    "EmbedPaginator",
    "PaginatorSource",
)


T = TypeVar("T")
EmbT = TypeVar("EmbT", bound=discord.Embed)


class Field(TypedDict):
    name: str
    value: str
    inline: bool


class EmbedPage(NamedTuple):
    description: list[str]
    fields: list[Field]


class PaginatorSource(commands.Paginator, menus.PageSource, Generic[T]):
    pages: list[T]

    def get_max_pages(self) -> int:
        return len(self._pages) + (self._count != 0)

    def is_paginating(self) -> bool:
        return self.get_max_pages() > 1

    async def get_page(self, page_number: int) -> T:
        return self.pages[page_number]


class EmbedPaginator(discord.Embed, PaginatorSource[EmbT]):
    def __init__(
        self,
        *,
        max_size: int = 5000,
        max_description: int = 2048,
        max_fields: int = 25,
        cls: type[EmbT] = discord.Embed,
        **kwargs: Any,
    ) -> None:
        description = kwargs.pop("description", "")  # type: str

        self.cls = cls
        cls.__init__(self, **kwargs)

        self.prefix = None
        self.suffix = None

        self.max_size = max_size
        self.max_description = max_description
        self.max_fields = max_fields

        self.clear()

        for line in description.split("\n"):
            self.add_line(line)

    def clear(self) -> None:
        self._current_page = EmbedPage([], [])
        self._description_count = 0
        self._count = 0
        self._pages = []  # type: list[EmbedPage]

    def add_line(self, line: str = "", *, empty: bool = False) -> None:
        line_len = len(line)

        if line_len > self.max_description:
            raise RuntimeError(f"Line exceeds maximum description size ({self.max_description})")

        if self._count + line_len + empty >= self.max_size:
            self.close_page()

        if self._description_count + line_len + empty >= self.max_description:
            self.close_page()

        self._count += line_len + 1 + empty
        self._description_count += line_len + 1 + empty
        self._current_page.description.append(line)

        if empty:
            self._current_page.description.append("")

    def add_field(self, *, name: str, value: str, inline: bool = False) -> None:
        name_len = len(name)
        value_len = len(value)

        if name_len + value_len > self.max_size:
            raise RuntimeError(f"Field exceeds maximum page size ({self.max_size})")

        if len(self._current_page.fields) >= self.max_fields:
            self.close_page()

        if self._count + name_len + value_len > self.max_size:
            self.close_page()

        self._count += name_len + value_len
        self._current_page.fields.append(Field(name=name, value=value, inline=inline))

    def close_page(self) -> None:
        self._pages.append(self._current_page)
        self._current_page = EmbedPage([], [])
        self._description_count = 0
        self._count = 0

    def _format_page(self, page: EmbedPage) -> EmbT:
        embed = self.cls.from_dict(self.to_dict())
        embed.description = "\n".join(page.description)

        for field in page.fields:
            embed.add_field(**field)

        if self._pages.index(page) >= 1 and isinstance(embed.author.name, str):
            embed.author.name += " cont."

        return embed

    async def format_page(self, menu: Any, page: EmbT) -> EmbT:
        return page

    @property
    def pages(self) -> list[EmbT]:  # type: ignore[return-value, override]
        if len(self._current_page.description) or len(self._current_page.fields) > 0:
            self.close_page()

        return [self._format_page(page) for page in self._pages]

    @property
    def fields(self) -> list[discord.embeds.EmbedProxy]:
        fields = []
        for page in self._pages:
            for field in page.fields:
                fields.append(discord.embeds.EmbedProxy(field))  # type: ignore
        return fields

    def __repr__(self) -> str:
        return f"<EmbedPaginator cls: {self.cls} max_size: {self.max_size}>"
