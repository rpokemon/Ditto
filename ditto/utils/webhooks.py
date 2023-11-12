import asyncio

import aiohttp
import discord
from discord.ext import tasks

__all__ = ("EmbedWebhookLogger",)


MAX_MESSAGE_LENGTH = 6000
MAX_EMBEDS = 10

class EmbedWebhookLogger:
    _to_log: list[discord.Embed]

    def __init__(self, webhool_url: str) -> None:
        self.loop = asyncio.get_event_loop()
        self._webhook_url = webhool_url
        self._to_log = []

        self._session = aiohttp.ClientSession()
        self._webhook = discord.Webhook.from_url(self._webhook_url, session=self._session)

        # setup loop
        self._loop.add_exception_type(discord.HTTPException)
        self._loop.start()

    def log(self, embed: discord.Embed) -> None:
        self._to_log.append(embed)

    @tasks.loop(seconds=5)
    async def _loop(self) -> None:
        while self._to_log:
            embeds = []

            while len(embeds) < MAX_EMBEDS and self._to_log:
                next = self._to_log[0]
                if sum(map(len, embeds)) + len(next) > MAX_MESSAGE_LENGTH:
                    break
                embeds.append(self._to_log.pop(0))

            await self._webhook.send(embeds=embeds)
