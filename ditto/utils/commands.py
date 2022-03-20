from typing import TypeVar

from discord.ext import commands

from .. import Context

__all__ = ("auto_help",)


_CT = TypeVar("_CT", bound=commands.Command)
_GT = TypeVar("_GT", bound=commands.Group)


async def _call_help(ctx: Context):
    assert ctx.command is not None
    assert ctx.command.parent is not None
    await ctx.send_help(ctx.command.parent)


def auto_help(group: _GT, *, cls: type[_CT] = commands.Command) -> _GT:
    if not isinstance(group, commands.Group):
        raise TypeError("Auto help can only be applied to groups.")
    command = cls(_call_help, name="help", hidden=True)
    group.add_command(command)
    return group
