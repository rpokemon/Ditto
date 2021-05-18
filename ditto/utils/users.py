from __future__ import annotations

import io
from typing import TYPE_CHECKING

import discord

from ..types import User

if TYPE_CHECKING:
    from discord.asset import ValidAssetFormatTypes


__all__ = ("download_avatar",)


async def download_avatar(
    user: User, size: int = 256, static: bool = False, format: ValidAssetFormatTypes = "png"
) -> io.BytesIO:
    avatar = io.BytesIO()
    if static:
        try:
            await user.avatar.replace(size=size, static_format=format).save(avatar)  # type: ignore
        except discord.NotFound:
            await user.default_avatar.replace(size=size, static_format=format).save(avatar)  # type: ignore
    else:
        try:
            await user.avatar.replace(size=size, format=format).save(avatar)
        except discord.NotFound:
            await user.default_avatar.replace(size=size, format=format).save(avatar)  # type: ignore
    return avatar
