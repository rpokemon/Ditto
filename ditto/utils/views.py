from typing import Generic, Optional, TypeVar

import discord

from ..types import User
from ..utils.strings import ZWSP
from .interactions import error
from .paginator import PaginatorSource

__all__ = ("disable_view", "Prompt", "PageView", "EmbedPageView")


EmbedT = TypeVar("EmbedT", bound=discord.Embed)


def disable_view(view: discord.ui.View) -> None:
    for item in view.children:
        if isinstance(item, discord.ui.Button):
            item.disabled = True
        elif isinstance(item, discord.ui.Select):
            item.options.clear()
            item.add_option(label=ZWSP, value=ZWSP, default=True)


class Private(discord.ui.View):
    def __init__(self, user: User, *, timeout: Optional[float] = 60):
        super().__init__(timeout=timeout)
        self.user = user

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user != self.user:
            await error(interaction, "You are not the user who initiated this interaction.")
            return False
        return True


class Prompt(Private):
    def __init__(self, user: User, *, timeout: Optional[float] = 60):
        super().__init__(user, timeout=timeout)
        self.response: Optional[bool] = None

    async def disable(self, interaction: discord.Interaction) -> None:
        disable_view(self)
        await interaction.response.edit_message(view=self)
        self.stop()

    @discord.ui.button(label="Yes", style=discord.ButtonStyle.red)
    async def yes(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        self.response = True
        await self.disable(interaction)

    @discord.ui.button(label="No", style=discord.ButtonStyle.blurple)
    async def no(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        self.response = False
        await self.disable(interaction)


class PageView(Private):
    def __init__(
        self,
        source: PaginatorSource[str],
        user: User,
        *,
        timeout: Optional[float] = 60,
        ephemeral: bool = False,
    ) -> None:
        super().__init__(user, timeout=timeout)
        self.source: PaginatorSource[str] = source
        self.current_page = 0
        self.ephemeral: bool = ephemeral

        self.clear_items()
        self.add_pagination_items()

    def add_pagination_items(self) -> None:
        items = (self.first, self.previous, self.current, self.next, self.last)
        if not self.ephemeral:
            items += (self.quit,)
        for item in items:
            self.add_item(item)

    async def change_source(self, interaction: discord.Interaction, source: PaginatorSource[str]) -> None:
        self.source = source
        await self.go_to_page(interaction, 0)

    @property
    def current_page(self) -> int:
        return self._current_page

    @current_page.setter
    def current_page(self, value: int) -> None:
        self._current_page = value
        self._update()

    def _update(self) -> None:
        self.first.disabled = self.previous.disabled = self.current_page == 0
        self.last.disabled = self.next.disabled = self.current_page == self.source.get_max_pages() - 1

        if self.previous.disabled:
            self.previous.label = "…"
        else:
            self.previous.label = str(self.current_page)

        self.current.label = str(self.current_page + 1)

        if self.next.disabled:
            self.next.label = "…"
        else:
            self.next.label = str(self.current_page + 2)

    async def show_page(self, interaction: discord.Interaction, page: str) -> None:
        await interaction.response.edit_message(content=page, view=self)

    async def go_to_page(self, interaction: discord.Interaction, page_number: int) -> None:
        page = await self.source.get_page(page_number)
        self.current_page = page_number
        await self.show_page(interaction, page)

    @discord.ui.button(label="First", style=discord.ButtonStyle.gray)
    async def first(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Go to the first page."""
        await self.go_to_page(interaction, 0)

    @discord.ui.button(label="Previous", style=discord.ButtonStyle.gray)
    async def previous(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Go to the previous page."""
        await self.go_to_page(interaction, max(0, self.current_page - 1))

    @discord.ui.button(label="Current", style=discord.ButtonStyle.gray, disabled=True)
    async def current(self, interaction: discord.Interaction, button: discord.ui.Button):
        """The current page."""
        await interaction.response.send_message("How'd you do that?", ephemeral=True)

    @discord.ui.button(label="Next", style=discord.ButtonStyle.gray)
    async def next(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Go to the next page"""
        await self.go_to_page(interaction, min(self.source.get_max_pages() - 1, self.current_page + 1))

    @discord.ui.button(label="Last", style=discord.ButtonStyle.gray)
    async def last(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Go to the last page"""
        await self.go_to_page(interaction, self.source.get_max_pages() - 1)

    @discord.ui.button(label="Quit", style=discord.ButtonStyle.red)
    async def quit(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Quits this menu."""
        await interaction.response.defer()
        await interaction.delete_original_response()
        self.stop()


class EmbedPageView(PageView, Generic[EmbedT]):
    source: PaginatorSource[EmbedT]

    def __init__(
        self,
        source: PaginatorSource[EmbedT],
        user: User,
        *,
        timeout: Optional[float] = 60,
        ephemeral: bool = False,
    ) -> None:
        super().__init__(source, user, timeout=timeout, ephemeral=ephemeral)  # type: ignore

    async def change_source(self, interaction: discord.Interaction, source: PaginatorSource[EmbedT]) -> None:
        await super().change_source(interaction, source)  # type: ignore

    async def show_page(self, interaction: discord.Interaction, page: EmbedT) -> None:
        await interaction.response.edit_message(embed=page, view=self)
