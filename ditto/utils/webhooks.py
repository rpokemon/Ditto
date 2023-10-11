import asyncio

import aiohttp
import discord
from discord.ext import tasks

__all__ = ("EmbedWebhookLogger",)


class EmbedWebhookLogger:
    _to_log: list[discord.Embed]
    _files_to_log: list[discord.File]

    def __init__(self, webhool_url: str) -> None:
        self.loop = asyncio.get_event_loop()
        self._webhook_url = webhool_url
        self._to_log = []
        self._files_to_log=[]

        self._session = aiohttp.ClientSession()
        self._webhook = discord.Webhook.from_url(self._webhook_url, session=self._session)

        # setup loop
        self._loop.start()

    def log(self, embed: discord.Embed,files: list[discord.File]=[]) -> None:
        self._to_log.append(embed)
        self._files_to_log.extend(files)

    @tasks.loop(seconds=5)
    async def _loop(self) -> None:
        while self._to_log:
            embeds = [self._to_log.pop(0) for _ in range(min(10, len(self._to_log)))]
            files=[self._files_to_log.pop(0) for _ in range(min(10,len(self._files_to_log)))]
            await self._webhook.send(embeds=embeds,files=files if files else [])
