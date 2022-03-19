from __future__ import annotations

import zoneinfo

import discord

from ..interactions import error


__all__ = ("ZoneInfoTransformer",)


class ZoneInfoTransformer(discord.app_commands.Transformer):
    @classmethod
    async def transform(cls, interaction: discord.Interaction, value: str) -> zoneinfo.ZoneInfo:

        try:
            return zoneinfo.ZoneInfo(value)
        except Exception:  # catch all due to BPO: 41530
            await error(interaction, f'Time Zone "{value}" not found.')
            raise ValueError(f'Time Zone "{value}" not found.')
