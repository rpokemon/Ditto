import json
from typing import Optional, Literal, Union

import discord

from ditto.types import GuildChannel

@discord.slash.command()
async def bar(
    interaction,
    client,
    channel: Optional[GuildChannel],
):
    """Description"""
    options = json.dumps(interaction.data.get('options', []))
    resolved = json.dumps(interaction.data.get('resolved', {}))
    await interaction.response.send_message(f"`{options}\n{resolved}`")


print(bar.options)