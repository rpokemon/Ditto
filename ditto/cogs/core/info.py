import datetime
import inspect
import pathlib

from typing import cast, get_args, Optional, Union

import discord
import ditto
import jishaku
from discord.ext import commands
from PIL import Image

from ... import BotBase, Cog, Context, CONFIG as BOT_CONFIG
from ...types import DiscordObject, VocalGuildChannel, GuildChannel, User, DiscordEmoji, Message
from ...utils.collections import summarise_list
from ...utils.files import get_base_dir
from ...utils.images import to_bytes
from ...utils.strings import codeblock, yes_no, as_columns
from ...utils.time import readable_timestamp


COLOUR_INFO_IMAGE_SIZE = 128

GITHUB_URL = "https://github.com/"

ListGuildChannel = Union[
    list[discord.TextChannel],
    list[discord.CategoryChannel],
    list[discord.VoiceChannel],
    list[discord.StageChannel],
    list[discord.StoreChannel],
]


class Info(Cog):
    @commands.command()
    async def about(self, ctx: Context):
        """Display some basic information about the bot."""
        if self.bot.owner is not None:
            owner = str(self.bot.owner)
        else:
            owner = ", ".join(str(owner) for owner in self.bot.owners)  # type: ignore

        await ctx.send(
            embed=discord.Embed(
                colour=ctx.me.colour,
                description=f"I am {self.bot.user}, a bot made by {owner}. My prefix is {self.bot.prefix}.",
            ).set_author(name=f"About {self.bot.user.name}:", icon_url=self.bot.user.avatar.url)
        )

    # region: Object Info

    @classmethod
    def summarise_roles(cls, *roles: discord.Role, max_items: int = 5, skip_first: bool = True) -> str:
        return summarise_list(*roles, func=lambda role: role.mention, max_items=max_items, skip_first=skip_first)

    @classmethod
    def summarise_members(cls, *members: discord.Member, max_items: int = 10, skip_first: bool = False) -> str:
        return summarise_list(*members, func=lambda member: member.mention, max_items=max_items, skip_first=skip_first)

    @classmethod
    def summarise_channels(cls, *channels: GuildChannel, max_items: int = 4, skip_first: bool = False) -> str:
        return summarise_list(
            *channels, func=lambda channel: channel.mention, max_items=max_items, skip_first=skip_first
        )

    @classmethod
    def summarise_emoji(cls, emojis: list[discord.Emoji], *, max_items: int = 4, skip_first: bool = False) -> str:
        return summarise_list(
            *emojis,
            func=lambda emoji: f"<{'a' if emoji.animated else ''}:_:{emoji.id}>",
            max_items=max_items,
            skip_first=skip_first,
        )

    @staticmethod
    def _object_info(item: DiscordObject) -> discord.Embed:
        embed = discord.Embed()

        embed.set_author(name=f"Information on {item}:")

        embed.add_field(name="ID:", value=str(item.id), inline=False)
        embed.add_field(
            name="Created At:",
            value=readable_timestamp(item.created_at) if item.created_at else "Unknown",
            inline=False,
        )

        return embed

    @classmethod
    def _server_object_info(cls, item: Union[discord.Role, GuildChannel]) -> discord.Embed:
        embed = cls._object_info(item)
        embed.add_field(name="Server:", value=str(item.guild))

        return embed

    @commands.command()
    async def server_info(self, ctx: Context, *, server: Optional[discord.Guild] = None) -> None:
        """Get information on a server.

        `server[Optional]`: The server to get information on by name, or ID. If none specified it defaults to the server you're in.
        """
        server = server or ctx.guild

        if server is None:
            raise commands.BadArgument("You did not specify a server.")

        if server != ctx.guild and not await ctx.user_in_guild(server):
            raise commands.BadArgument("You cannot retrieve information on a server you are not in.")

        embed = self._object_info(server)
        embed.set_thumbnail(url=server.icon.url)

        embed.add_field(name="Voice Region:", value=str(server.region))

        owner = server.owner
        if owner is None:
            owner = await server.fetch_member(server.owner_id)
        embed.add_field(name="Owner:", value=owner.mention)

        embed.add_field(name="Members:", value=str(server.member_count))

        vocal_channels = [channel for channel in server.channels if isinstance(channel, get_args(VocalGuildChannel))]
        store_channels = [channel for channel in server.channels if isinstance(channel, discord.StoreChannel)]
        channels = f"""{len(server.channels)}
    - Categories: {self.summarise_channels(*server.categories)}
    - Text: {self.summarise_channels(*server.text_channels)}
    - Vocal: {len(vocal_channels)}
    --- Voice: {self.summarise_channels(*server.voice_channels)}
    --- Stage: {self.summarise_channels(*server.stage_channels)}
    - Store: {self.summarise_channels(*store_channels)}"""
        embed.add_field(name="Channels:", value=channels, inline=False)

        embed.add_field(name="Roles:", value=self.summarise_roles(*server.roles), inline=False)

        static_emoji = [emoji for emoji in server.emojis if not emoji.animated]
        animated_emoji = [emoji for emoji in server.emojis if emoji.animated]
        emojis = f"""{len(server.emojis)}
    Static: {self.summarise_emoji(static_emoji)}
    Animated: {self.summarise_emoji(animated_emoji)}"""
        embed.add_field(name="Emoji:", value=emojis, inline=False)

        if server.chunked:
            nitro_boosters = [member for member in server.members if member.premium_since is not None]
            embed.add_field(name="Nitro Boosters:", value=self.summarise_members(*nitro_boosters), inline=False)
        else:
            embed.add_field(name="Nitro Boosters:", value=str(server.premium_subscription_count))

        embed.add_field(
            name="Features:",
            value=codeblock(
                as_columns([feature.replace("_", " ").title() for feature in server.features], transpose=True)
            ),
            inline=False,
        )

        await ctx.send(embed=embed)

    @commands.command()
    async def role_info(self, ctx: Context, *, role: discord.Role) -> None:
        """Get information on a role.

        `role`: The role to get information on by name, ID, or mention.
        """

        embed = self._server_object_info(role)
        if role.colour.value:
            embed.colour = role.colour

        embed.add_field(
            name="Permissions:",
            value=f"[Permissions list](https://discordapi.com/permissions.html#{role.permissions.value})",
        )
        embed.add_field(name="Displayed Separately:", value=yes_no(role.hoist))
        embed.add_field(name="Is Mentionable:", value=yes_no(role.mentionable))
        embed.add_field(name="Colour:", value=str(role.colour) if role.colour.value else "None")

        if role.guild.chunked:
            embed.add_field(name="Members:", value=self.summarise_members(*role.members), inline=False)

        await ctx.send(embed=embed)

    @classmethod
    def _channel_info(cls, channel: GuildChannel) -> discord.Embed:
        embed = cls._server_object_info(channel)

        embed.add_field(name="Position", value=str(channel.position))

        if not isinstance(channel, discord.CategoryChannel):
            embed.add_field(name="Category", value=str(channel.category))

        if not isinstance(channel, get_args(VocalGuildChannel)):
            embed.add_field(name="Is NSFW:", value=str(channel.is_nsfw()))

        return embed

    @commands.command(hidden=True)
    async def text_channel_info(self, ctx: Context, *, channel: Optional[discord.TextChannel] = None) -> None:
        """Get information on a text channel.

        `channel[Optional]`: The text channel to get information on by name, ID, or mention. If none specified it defaults to the channel you're in.
        """
        channel = channel or cast(discord.TextChannel, ctx.channel)

        if channel.guild != ctx.guild and not await ctx.user_in_guild(channel.guild):
            raise commands.BadArgument("You cannot retrieve information on a server you are not in.")

        embed = self._channel_info(channel)

        embed.add_field(name="Topic", value=str(channel.topic) or "None Set", inline=False)

        slowmode_delay = f"{channel.slowmode_delay} seconds" if channel.slowmode_delay else "Disabled"
        embed.add_field(name="Slowmode Delay", value=slowmode_delay)

        await ctx.send(embed=embed)

    @classmethod
    def _vocal_channel_info(cls, channel: VocalGuildChannel) -> discord.Embed:
        embed = cls._channel_info(channel)

        embed.add_field(name="Voice Region:", value=str(channel.rtc_region or "Automatic"))
        embed.add_field(name="Bitrate", value=f"{channel.bitrate//1024}Kbps")
        embed.add_field(name="User Limit", value=str(channel.user_limit))

        if channel.guild.chunked:
            embed.add_field(name="Members:", value=cls.summarise_members(*channel.members), inline=False)
        else:
            embed.add_field(name="Members:", value=str(len(channel.voice_states)))

        return embed

    @commands.command(hidden=True)
    async def voice_channel_info(self, ctx: Context, *, channel: Optional[discord.VoiceChannel]) -> None:
        """Get information on a voice channel.

        `channel[Optional]`: The voice channel to get information on by name, ID, or mention. If none specified it defaults to the channel you're in.
        """
        if channel is None:
            user = cast(discord.Member, ctx.author)
            if user.voice is not None:
                channel = cast(Optional[discord.VoiceChannel], user.voice.channel)

        if not isinstance(channel, discord.VoiceChannel):
            raise commands.BadArgument("You are currently not in a voice channel.")

        if channel.guild != ctx.guild and not await ctx.user_in_guild(channel.guild):
            raise commands.BadArgument("You cannot retrieve information on a server you are not in.")

        embed = self._vocal_channel_info(channel)

        await ctx.send(embed=embed)

    @commands.command(hidden=True)
    async def stage_channel_info(self, ctx: Context, *, channel: Optional[discord.StageChannel]) -> None:
        """Get information on a stage channel.

        `channel[Optional]`: The stage channel to get information on by name, ID, or mention. If none specified it defaults to the channel you're in.
        """
        if channel is None:
            user = cast(discord.Member, ctx.author)
            if user.voice is not None:
                channel = cast(Optional[discord.StageChannel], user.voice.channel)

        if not isinstance(channel, discord.StageChannel):
            raise commands.BadArgument("You are currently not in a stage channel.")

        if channel.guild != ctx.guild and not await ctx.user_in_guild(channel.guild):
            raise commands.BadArgument("You cannot retrieve information on a server you are not in.")

        embed = self._vocal_channel_info(channel)

        await ctx.send(embed=embed)

    @commands.command(hidden=True)
    async def vocal_channel_info(self, ctx: Context, *, channel: Optional[VocalGuildChannel]) -> None:
        """Get information on a vocal channel.

        `channel[Optional]`: The vocal channel to get information on by name, ID, or mention. If none specified it defaults to the channel you're in.
        """
        if channel is None:
            user = cast(discord.Member, ctx.author)
            if user.voice is not None:
                channel = cast(Optional[Union[discord.VoiceChannel, discord.StageChannel]], user.voice.channel)

        if channel is None:
            raise commands.BadArgument("You are currently not in a vocal channel.")

        if isinstance(channel, discord.VoiceChannel):
            return await ctx.invoke(self.voice_channel_info, channel=channel)

        if isinstance(channel, discord.StageChannel):
            return await ctx.invoke(self.stage_channel_info, channel=channel)

        raise commands.BadArgument(f"Could not find information on: {channel}")

    @commands.command(hidden=True)
    async def category_channel_info(self, ctx: Context, *, channel: Optional[discord.CategoryChannel]) -> None:
        """Get information on a channel category.

        `channel[Optional]`: The channel category to get information on by name, ID, or mention, If none specified it defaults to the category of the channel you're in, if one exists.
        """
        channel = channel or cast(discord.TextChannel, ctx.channel).category

        if channel is None:
            raise commands.BadArgument(
                "You did not specify a channel category, or the text channel you are in is not part of a category."
            )

        if channel.guild != ctx.guild and not await ctx.user_in_guild(channel.guild):
            raise commands.BadArgument("You cannot retrieve information on a server you are not in.")

        embed = self._channel_info(channel)

        vocal_channels = [channel for channel in channel.channels if isinstance(channel, get_args(VocalGuildChannel))]
        store_channels = [channel for channel in channel.channels if isinstance(channel, discord.StoreChannel)]
        channels = f"""{len(channel.channels)}
    - Text: {self.summarise_channels(*channel.text_channels)}
    - Vocal: {len(vocal_channels)}
    --- Voice: {self.summarise_channels(*channel.voice_channels)}
    --- Stage: {self.summarise_channels(*channel.stage_channels)}
    - Store: {self.summarise_channels(*store_channels)}"""
        embed.add_field(name="Channels:", value=channels, inline=False)

        await ctx.send(embed=embed)

    @commands.command(hidden=True)
    @commands.guild_only()
    async def store_channel_info(self, ctx: Context, *, channel: discord.StoreChannel) -> None:
        """Get information on a store channel.

        `channel`: The store channel to get information on by name, ID, or mention.
        """

        if channel.guild != ctx.guild and not await ctx.user_in_guild(channel.guild):
            raise commands.BadArgument("You cannot retrieve information on a server you are not in.")

        embed = self._channel_info(channel)

        await ctx.send(embed=embed)

    @commands.command()
    @commands.guild_only()
    async def channel_info(self, ctx: Context, *, channel: Optional[GuildChannel] = None) -> None:
        """Get information on a channel.

        `channel[Optional]`: The channel to get information on by name, ID, or mention. If none specified it defaults to the text channel you're in.
        """

        if isinstance(channel, discord.TextChannel):
            return await ctx.invoke(self.text_channel_info, channel=channel)

        if isinstance(channel, get_args(VocalGuildChannel)):
            return await ctx.invoke(self.vocal_channel_info, channel=channel)

        if isinstance(channel, discord.CategoryChannel):
            return await ctx.invoke(self.category_channel_info, channel=channel)

        if isinstance(channel, discord.StoreChannel):
            return await ctx.invoke(self.store_channel_info, channel=channel)

        raise commands.BadArgument(f"Could not find information on: {channel}")

    @classmethod
    def _user_info(cls, user: User) -> discord.Embed:
        embed = cls._object_info(user)
        embed.set_thumbnail(url=user.avatar.url)
        embed.add_field(name="Is Bot:", value=yes_no(user.bot))
        return embed

    @commands.command(hidden=True)
    @commands.guild_only()
    async def member_info(self, ctx: Context, *, member: Optional[discord.Member] = None) -> None:
        """Get information on a member.

        `member[Optional]`: The member to get information on by name, ID, or mention. If none specified it defaults to you.
        """
        member = member or cast(discord.Member, ctx.author)

        if member.guild != ctx.guild:
            raise commands.BadArgument("You can only retrieve information on members in the current server.")

        embed = self._user_info(member)
        embed.colour = member.colour if bool(member.colour.value) else discord.Embed.Empty

        embed.add_field(
            name="Joined Server:",
            value=readable_timestamp(member.joined_at) if member.joined_at else "Unknown",
            inline=False,
        )

        if member.nick:
            embed.add_field(name="Nickname:", value=member.nick)

        if member.premium_since:
            embed.add_field(name="Nitro Boosting Since:", value=readable_timestamp(member.premium_since), inline=False)

        embed.add_field(name="Roles:", value=self.summarise_roles(*member.roles), inline=False)

        await ctx.send(embed=embed)

    @commands.command()
    async def user_info(self, ctx: Context, *, user: Optional[User] = None) -> None:
        """Get information on a user.

        `user[Optional]`: The user to get information on by name, ID, or mention. If none specified it defaults to you.
        """
        user = user or cast(User, ctx.author)

        if isinstance(user, discord.Member) and user.guild == ctx.guild:
            return await ctx.invoke(self.member_info, member=user)

        embed = self._user_info(user)
        await ctx.send(embed=embed)

    @commands.command()
    async def emoji_info(self, ctx: Context, *, emoji: DiscordEmoji) -> None:
        """Get information on an emoji.

        `emoji`: The emoji to get information on by name, ID or by the emoji itself.
        """

        if isinstance(emoji, discord.PartialEmoji) and emoji.is_unicode_emoji():
            raise commands.BadArgument("Cannot retrieve information on Unicode emoji.")

        embed = self._object_info(emoji)
        embed.set_thumbnail(url=emoji.url)

        if isinstance(emoji, discord.Emoji):
            embed.add_field(name="Server:", value=str(emoji.guild))

        embed.add_field(name="Animated:", value=yes_no(emoji.animated))

        await ctx.send(embed=embed)

    @commands.command()
    async def message_info(self, ctx: Context, *, message: Optional[Message] = None) -> None:
        """Get information on a message.

        `message`: The message to get information on, either by ID, or the jump url. If none specified defaults to the message sent to invoke this command or the message it replied to.
        """

        if message is None:
            reference = ctx.message.reference
            if reference is not None:
                if reference.message_id is not None:
                    message = await ctx.channel.fetch_message(reference.message_id)
                else:
                    raise commands.BadArgument("Could not resolve message reference.")
            else:
                message = ctx.message
            message = cast(discord.Message, message)

        embed = self._object_info(message)
        embed.set_author(name="Information on message:")

        embed.add_field(name="Server:", value=str(message.guild or "Direct Message"))
        embed.add_field(name="Channel:", value=str(message.channel))

        if isinstance(message, discord.Message):
            embed.add_field(name="Sent By:", value=str(message.author))
            embed.add_field(name="Has attachment(s):", value=yes_no(message.attachments))
            embed.add_field(name="Has embed(s):", value=yes_no(message.embeds))

            embed.add_field(name="Is Pinned:", value=yes_no(message.pinned))

            if message.reference:
                embed.add_field(name="References:", value=f"[Jump!]({message.reference.jump_url})")

            # TODO: Stickers?

        embed.add_field(name="Jump URL:", value=f"[Jump!]({message.jump_url})")

        await ctx.send(embed=embed)

    @commands.command()
    async def invite_info(self, ctx: Context, *, invite: discord.Invite) -> None:
        """Get information on a server invite.

        `invite`: The server invite to get information on, either by name, or the url.
        """

        embed = self._object_info(invite)
        embed.set_author(name=f"Information on invite to {invite.guild}:")
        embed.set_thumbnail(
            url=invite.guild.icon.url if isinstance(invite.guild, discord.guild.Guild) else discord.Embed.Empty
        )

        embed.add_field(name="Created By:", value=str(invite.inviter))
        embed.add_field(
            name="Expires At:",
            value=readable_timestamp(invite.created_at + datetime.timedelta(seconds=invite.max_age))
            if invite.max_age
            else "Never",
            inline=False,
        )
        embed.add_field(
            name="Channel:",
            value=str(invite.channel) if isinstance(invite.channel, get_args(GuildChannel)) else "Unknown",
        )
        embed.add_field(name="Uses:", value=str(invite.uses or "Unknown"))
        embed.add_field(name="Max Uses:", value=str(invite.max_uses or "Infinite"))

        await ctx.send(embed=embed)

    @commands.command()
    async def colour_info(self, ctx: Context, *, colour: Optional[discord.Colour] = None) -> None:
        """Get information on a colour.

        `colour:` The colour to get information on by hex or integer value. defaults to a random colour.
        """
        colour = colour or discord.Colour.random()

        size = (COLOUR_INFO_IMAGE_SIZE, COLOUR_INFO_IMAGE_SIZE)
        image = to_bytes(Image.new("RGB", size, colour.to_rgb()))
        filename = f"{colour.value:0>6x}.png"

        embed = discord.Embed(colour=colour)
        embed.set_author(name=f"Information on: {colour}")

        embed.add_field(name="Hex:", value=str(colour))
        embed.add_field(name="RGB:", value=", ".join(str(channel) for channel in colour.to_rgb()))
        embed.set_thumbnail(url=f"attachment://{filename}")

        await ctx.send(embed=embed, file=discord.File(image, filename))

    @commands.command()
    async def get(self, ctx: Context, *, item: Union[DiscordObject, discord.Colour]) -> None:
        """Get information on something.

        `item`: The item to get information on; items are looked in the following order: Guild, Role, Channel, User, Emoji, Message, Invite, Colour.
        """

        if isinstance(item, discord.Guild):
            return await ctx.invoke(self.server_info, server=item)

        elif isinstance(item, discord.Role):
            return await ctx.invoke(self.role_info, role=item)

        elif isinstance(item, get_args(GuildChannel)):
            return await ctx.invoke(self.channel_info, channel=item)

        elif isinstance(item, get_args(User)):
            return await ctx.invoke(self.user_info, user=item)

        elif isinstance(item, get_args(DiscordEmoji)):
            return await ctx.invoke(self.emoji_info, emoji=item)

        elif isinstance(item, get_args(Message)):
            return await ctx.invoke(self.message_info, message=item)

        elif isinstance(item, discord.Invite):
            return await ctx.invoke(self.invite_info, invite=item)

        elif isinstance(item, discord.Colour):
            return await ctx.invoke(self.colour_info, colour=item)

        raise commands.BadArgument(f"Could not find information on: {item}")

    # endregion: Object info

    @commands.command()
    async def source(self, ctx: Context, *, command: commands.Command = None):
        if command is None:
            return await ctx.send(f"<{GITHUB_URL}{BOT_CONFIG.SOURCE.CUSTOM}>")

        if command.name == "help":
            code = type(self.bot.help_command)
        else:
            code = command.callback.__code__

        filename = inspect.getsourcefile(code)

        if filename is None:
            raise commands.BadArgument(f'Could not find source for command: "{command.qualified_name}"')

        file = pathlib.Path(filename).relative_to(pathlib.Path.cwd())

        module_dirs = ((get_base_dir(ditto), BOT_CONFIG.SOURCE.DITTO), (get_base_dir(jishaku), "gorialis/jishaku"))

        lines, first_line = inspect.getsourcelines(code)
        last_line = first_line + len(lines) - 1

        repository = None
        commit_hash = "master"  # todo: Add commit to version.
        for dir, repo in module_dirs:
            if str(file).startswith(str(dir)):
                repository = repo
                filename = str(file.relative_to(dir.parent)).replace("\\", "/")
                break

        if repository is None:
            repository = BOT_CONFIG.SOURCE.CUSTOM
            filename = str(file).replace("\\", "/")

        await ctx.send(f"<{GITHUB_URL}{repository}/blob/{commit_hash}/{filename}#L{first_line}-#L{last_line}>")


def setup(bot: BotBase):
    bot.add_cog(Info(bot))
