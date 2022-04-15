from __future__ import annotations

import io
from typing import TYPE_CHECKING, Literal, overload

import discord

from ..types import User

if TYPE_CHECKING:
    from discord.asset import ValidAssetFormatTypes, ValidStaticFormatTypes


__all__ = ("download_avatar",)


@overload
async def download_avatar(
    user: User, size: int = 256, static: Literal[True] = ..., format: ValidStaticFormatTypes = "png"
) -> io.BytesIO:
    ...


@overload
async def download_avatar(
    user: User, size: int = 256, static: bool = ..., format: ValidAssetFormatTypes = "png"
) -> io.BytesIO:
    ...


async def download_avatar(
    user: User, size: int = 256, static: bool = False, format: ValidAssetFormatTypes = "png"
) -> io.BytesIO:
    avatar = io.BytesIO()
    if static:
        try:
            await user.display_avatar.replace(size=size, static_format=format).save(avatar)  # type: ignore
        except discord.NotFound:
            await user.default_avatar.replace(size=size, static_format=format).save(avatar)  # type: ignore
    else:
        try:
            await user.display_avatar.replace(size=size, format=format).save(avatar)
        except discord.NotFound:
            await user.default_avatar.replace(size=size, format=format).save(avatar)
    return avatar
