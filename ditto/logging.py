import datetime
import logging

import discord

from .utils.webhooks import EmbedWebhookLogger

__all__ = ("WebhookHandler",)


ZWSP = "\N{ZERO WIDTH SPACE}"


class WebhookHandler(logging.Handler):
    _colours = {
        logging.DEBUG: discord.Colour.light_grey(),
        logging.INFO: discord.Colour.gold(),
        logging.WARNING: discord.Colour.orange(),
        logging.ERROR: discord.Colour.red(),
        logging.CRITICAL: discord.Colour.dark_red(),
    }

    def __init__(self, webhook_url: str, level: int = logging.NOTSET) -> None:
        super().__init__(level)
        self._webhook_logger = EmbedWebhookLogger(webhook_url)

    def emit(self, record: logging.LogRecord) -> None:
        self.format(record)

        message = f'{record.message}\n{record.exc_text or ""}'
        message = message[:1987] + "..." if len(message) > 1987 else message

        self._webhook_logger.log(
            discord.Embed(
                colour=self._colours.get(record.levelno, discord.Embed.Empty),
                title=record.name,
                description=f"```py\n{message}\n```",
                timestamp=datetime.datetime.fromtimestamp(record.created),
            ).add_field(name=ZWSP, value=f"{record.filename}:{record.lineno}")
        )
