import asyncio
import aiohttp

import discord
from discord.ext import tasks

__all__ = ("EmbedWebhookLogger",)


class EmbedWebhookLogger:
    _to_log: list[discord.Embed]

    def __init__(self, webhool_url: str, *, loop: asyncio.BaseEventLoop = None) -> None:
        self.loop = loop or asyncio.get_event_loop()
        self._webhook_url = webhool_url
        self._to_log = []

        self._session = aiohttp.ClientSession()
        self._webhook = discord.Webhook.from_url(self._webhook_url, adapter=discord.AsyncWebhookAdapter(self._session))

        # setup loop
        self._loop.start()

    def log(self, embed: discord.Embed) -> None:
        self._to_log.append(embed)

    @tasks.loop(seconds=5)
    async def _loop(self) -> None:
        while self._to_log:
            embeds = [self._to_log.pop(0) for _ in range(min(10, len(self._to_log)))]
            await self._webhook.send(embeds=embeds)
