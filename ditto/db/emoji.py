import datetime
import io
import random
import re

from typing import Any, Optional, TYPE_CHECKING, cast

import asyncpg
import discord
from discord.client import Client
from donphan import MaybeAcquire

from PIL import Image, ImageChops, ImageDraw

from .tables import Emoji, UserEmoji
from ..types import User
from ..utils.users import download_avatar


CONFIG: Any = None


__all__ = ("EmojiCacheMixin",)


async def create_user_image(user: User) -> io.BytesIO:

    avatar = Image.open(await download_avatar(user, size=128, static=True))

    if avatar.mode != "RGBA":
        avatar = avatar.convert("RGBA")

    # Apply circular mask to image
    _, _, _, alpha = avatar.split()
    if alpha.mode != "L":
        alpha = alpha.convert("L")

    mask = Image.new("L", avatar.size)
    draw = cast(ImageDraw.ImageDraw, ImageDraw.Draw(mask))
    draw.ellipse((0, 0) + avatar.size, fill=255)

    mask = ImageChops.darker(mask, alpha)
    avatar.putalpha(mask)

    # Save to FP
    out_fp = io.BytesIO()
    avatar.save(out_fp, format="png")
    out_fp.seek(0)

    return out_fp


class EmojiCacheMixin:
    if TYPE_CHECKING:
        pool: asyncpg.pool.Pool

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        global CONFIG
        # this is a hack because >circular imports<
        from ..config import CONFIG as CONFIG

        super().__init__(*args, **kwargs)

        self._not_found_emoji: discord.Emoji = CONFIG.EMOJI.NOT_FOUND

    async def _find_guild(self, *, connection: Optional[asyncpg.Connection] = None) -> discord.Guild:
        assert isinstance(self, discord.Client)
        async with MaybeAcquire(connection, pool=self.pool) as connection:
            free_spaces = {}
            for guild in CONFIG.EMOJI.GUILDS:
                total_free = guild.emoji_limit - sum(not e.animated for e in guild.emojis)
                if total_free > CONFIG.EMOJI.LEAVE_FREE:
                    free_spaces[guild] = total_free

            if free_spaces:
                guilds = random.sample(list(free_spaces.keys()), counts=list(free_spaces.values()), k=1)
                return guilds[0]

            # Otherwise delete the oldest emoji
            record = await Emoji.fetch_row(connection, order_by=(Emoji.last_fetched, "ASC"))
            if record is None:
                raise RuntimeError("Emoji cache simultaneously empty and full.")
            await self.delete_emoji(record["emoji_id"], connection=connection)

            return await self._find_guild(connection=connection)

    async def create_emoji(
        self, name: str, image: io.BytesIO, *, connection: Optional[asyncpg.Connection] = None
    ) -> discord.Emoji:
        async with MaybeAcquire(connection, pool=self.pool) as connection:
            guild = await self._find_guild(connection=connection)
            emoji = await guild.create_custom_emoji(name=name, image=image.read())

            await Emoji.insert(connection, emoji_id=emoji.id, guild_id=guild.id)

        return emoji

    async def create_user_emoji(self, user: User, *, connection: Optional[asyncpg.Connection] = None) -> discord.Emoji:
        name = re.sub(r"[^A-Za-z0-9_]", "", user.name[:28]) + str(user.discriminator)
        image = await create_user_image(user)

        async with MaybeAcquire(connection, pool=self.pool) as connection:
            emoji = await self.create_emoji(name, image, connection=connection)
            await UserEmoji.insert(connection, emoji_id=emoji.id, user_id=user.id)

        return emoji

    async def fetch_emoji(
        self, emoji_id: Optional[int], *, connection: Optional[asyncpg.Connection] = None
    ) -> discord.Emoji:
        assert isinstance(self, discord.Client)
        if emoji_id is None:
            return self._not_found_emoji

        async with MaybeAcquire(connection, pool=self.pool) as connection:
            record = await Emoji.fetch_row(connection, emoji_id=emoji_id)
            if record is None:
                raise ValueError(f"Emoji with ID: {emoji_id} not in cache.")

            await Emoji.update_record(connection, record, last_fetched=datetime.datetime.now(datetime.timezone.utc))

            emoji = self.get_emoji(emoji_id)
            if emoji is None:
                await Emoji.delete_record(connection, record)
                raise RuntimeError("Emoji in cache was deleted.")

        return emoji

    async def fetch_user_emoji(
        self, user: Optional[User], *, connection: Optional[asyncpg.Connection] = None
    ) -> discord.Emoji:
        if user is None:
            return await self.fetch_emoji(None, connection=connection)

        async with MaybeAcquire(connection, pool=self.pool) as connection:
            record = await UserEmoji.fetch_row(connection, user_id=user.id)

            if record is not None:
                try:
                    return await self.fetch_emoji(record["emoji_id"], connection=connection)
                except RuntimeError:
                    await UserEmoji.delete_record(connection, record)

            return await self.create_user_emoji(user, connection=connection)

    async def delete_emoji(self, emoji_id: int, *, connection: Optional[asyncpg.Connection] = None) -> None:
        assert isinstance(self, discord.Client)
        async with MaybeAcquire(connection, pool=self.pool) as connection:
            record = await Emoji.fetch_row(connection, emoji_id=emoji_id)
            if record is None:
                raise ValueError(f"Emoji with ID: {emoji_id} not in cache.")

            emoji = self.get_emoji(emoji_id)
            if emoji is not None:
                await emoji.delete()

            await Emoji.delete_record(connection, record)
