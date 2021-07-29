from typing import Optional

import discord

from ..types import User
from .interactions import error

__all__ = ("Prompt",)


class Prompt(discord.ui.View):
    def __init__(self, user: User, *, timeout: Optional[float] = 60):
        super().__init__(timeout=timeout)
        self.user: User = user
        self.response: Optional[bool] = None

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user != self.user:
            await error(interaction, "You are notthe user who initiated this interaction.")
            return False
        return True

    async def disable(self, interaction: discord.Interaction) -> None:
        for item in self.children:
            if isinstance(item, discord.ui.Button):
                item.disabled = True
        await interaction.response.edit_message(view=self)
        self.stop()

    @discord.ui.button(label="Yes", style=discord.ButtonStyle.red)
    async def yes(self, button: discord.ui.Button, interaction: discord.Interaction) -> None:
        self.response = True
        await self.disable(interaction)

    @discord.ui.button(label="No", style=discord.ButtonStyle.blurple)
    async def no(self, button: discord.ui.Button, interaction: discord.Interaction) -> None:
        self.response = False
        await self.disable(interaction)
