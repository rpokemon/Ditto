import discord


class RawMessage(discord.Message):
    """Stateless Discord Message object.
    Args:
        client (discord.Client): The client which will alter the message.
        channel (discord.TextChannel): The channel the message is in.
        message_id (int): The message's ID.
    """

    def __init__(self, client: discord.Client, channel: discord.abc.Messageable, message_id: int) -> None:
        self._state = client._connection  # type: ignore
        self.id = message_id
        self.channel = channel  # type: ignore

    def __repr__(self) -> str:
        return f"<RawMessage id={self.id} channel={self.channel}>"
