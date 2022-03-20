from typing import Generic, Optional, TypeVar

import discord
from discord.ext import menus

from .. import Context

T = TypeVar("T")


class BaseChoiceMenu(menus.Menu, Generic[T]):
    options: list[T]

    def __init__(self, options: list[T]) -> None:
        super().__init__(delete_message_after=True)

        if len(options) > 9:
            raise RuntimeError("Too many options for choice menu.")

        self.options = options
        self.selection: Optional[T] = None

        for i, _ in enumerate(self.options, 1):
            emoji = f"{i}\ufe0f\N{COMBINING ENCLOSING KEYCAP}"
            self.add_button(menus.Button(emoji, self.choose))

    async def send_initial_message(self, ctx: Context, channel: discord.TextChannel) -> discord.Message:
        raise NotImplementedError

    async def choose(self, payload: discord.RawReactionActionEvent):
        self.selection = self.options[int(str(payload.emoji)[0]) - 1]
        self.stop()

    async def start(self, ctx, *, channel=None) -> Optional[T]:
        await super().start(ctx, channel=channel, wait=True)
        return self.selection

    @menus.button("\N{BLACK SQUARE FOR STOP}\ufe0f", position=menus.Last(0))
    async def cancel(self, payload):
        self.stop()
