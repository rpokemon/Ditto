from __future__ import annotations

import inspect
from collections.abc import Callable
from typing import get_type_hints, Any
from types import FunctionType

from discord.ext import commands
from discord.ext.commands import converter, Context, Converter, IDConverter

__all__ = ()

_BUILTINS = (
    bool,
    str,
    int,
    float,
)

_CONVERTERS: dict[type[Any], Callable[..., Any]] = {}

for n in converter.__all__:
    c = getattr(converter, n)
    if inspect.isclass(c) and issubclass(c, Converter) and c not in (Converter, IDConverter):
        _CONVERTERS[get_type_hints(c.convert)["return"]] = c

for b in _BUILTINS:
    _CONVERTERS[b] = b


class _ConverterDict(dict[type[Any], Callable[..., Any]]):
    def __init__(self):
        super().__init__(_CONVERTERS)

    def __setitem__(self, k: type[Any], v: Callable[..., Any]) -> None:
        if not isinstance(v, FunctionType) or inspect.isclass(v) and issubclass(v, (*_BUILTINS, Converter)):
            raise TypeError(f"Excepted value of type 'Converter' or built-in, got {v.__name__}")
        super().__setitem__(k, v)


_GLOBAL_CONVERTERS: _ConverterDict = _ConverterDict()

commands.bot.BotBase.converters = _GLOBAL_CONVERTERS  # type: ignore

_old_actual_conversion = commands.converter._actual_conversion


async def _actual_conversion(ctx: Context[Any], converter: Any, argument: str, param: inspect.Parameter) -> Any:
    converter = _GLOBAL_CONVERTERS.get(converter, converter)
    return await _old_actual_conversion(ctx, converter, argument, param)


commands.converter._actual_conversion = _actual_conversion
