from __future__ import annotations

import os
import pathlib
from collections.abc import Callable
from typing import TYPE_CHECKING, Any, Generic, TypeVar

import discord
import yaml
from discord.utils import MISSING

from .utils.files import get_base_dir

if TYPE_CHECKING:
    from _typeshed import StrPath

__all__ = (
    "CONFIG",
    "load_config",
    "load_global_config",
)

S = TypeVar("S", bound=discord.abc.Snowflake)


BASE_DIR = get_base_dir()


_bot: discord.Client = MISSING


class Object(Generic[S]):
    def __init__(self, id: int, type: type[S], func: Callable[[], S | None]) -> None:
        self._inner: discord.Object = discord.Object(id=id, type=type)
        self._func: Callable[[], S | None] = func

    def __getattr__(self, name: str) -> Any:
        res = self._func()
        if res is not None:
            return getattr(res, name)
        return getattr(self._inner, name)

    @property
    def __class__(self):
        return self._inner.type

    def __hash__(self) -> int:
        return self._inner.__hash__()

    def __repr__(self) -> str:
        return self.__getattr__("__repr__")()

    def __eq__(self, other: object) -> bool:
        return self.__getattr__("__eq__")(other)


def _get_object(type_: type[S], *getters: tuple[Callable[[Any, int], S | None], int]) -> Any:
    obj = _bot
    for func, id in getters:
        obj = func(obj, id)
        if obj is None:
            return discord.Object(id=id, type=type_)
    return obj


def env_var_constructor(loader: yaml.Loader, node: yaml.ScalarNode) -> str | None:
    if node.id != "scalar":
        raise TypeError("Expected a string")

    value = loader.construct_scalar(node)
    key = str(value)

    return os.getenv(key)


def generate_constructor(type_: type[S], func: Callable[..., S]) -> Callable[[yaml.Loader, yaml.ScalarNode], Object[S]]:
    def constructor(loader: yaml.Loader, node: yaml.ScalarNode) -> Object:
        ids = [int(x) for x in loader.construct_scalar(node).split()]  # type: ignore
        return Object(ids[-1], type_, lambda: func(*ids))

    return constructor


class Config(yaml.YAMLObject):
    yaml_tag = "!Config"
    _bot: discord.Client

    def __init__(self, **kwargs):
        for name, value in kwargs:
            setattr(self, name, value)

    def update(self, other: Config) -> None:
        for key in other.__dict__:
            if (
                key == "EXTENSIONS" and isinstance(other.__dict__[key], dict) and isinstance(self.__dict__.get(key), dict)
            ) or (isinstance(other.__dict__[key], Config) and isinstance(self.__dict__.get(key), Config)):
                other.__dict__[key] = self.__dict__[key] | other.__dict__[key]

        self.__dict__ |= other.__dict__

    def __or__(self, other) -> Config:
        config = Config()
        config.__dict__ |= self.__dict__ | other.__dict__
        return config

    def __repr__(self):
        return f'<Config {" ".join(f"{key}={repr(value)}" for key, value in self.__dict__.items())}>'


CONFIG: Any = Config()


def load_config(file: StrPath, bot: discord.Client) -> Config:
    with open(file, encoding="utf-8") as f:
        config = yaml.load(f, Loader=yaml.FullLoader)
    config._bot = bot
    return config


def update_config(config: Config, file: StrPath) -> None:
    with open(file, encoding="utf-8") as f:
        config.update(yaml.load(f, Loader=yaml.FullLoader))


def load_global_config(bot: discord.Client) -> Any:
    global _bot
    _bot = bot

    update_config(CONFIG, BASE_DIR / "res/config.yml")

    for override_file in pathlib.Path().glob("config*.yml"):
        update_config(CONFIG, override_file)

    return CONFIG


# Add constructors
yaml.FullLoader.add_constructor("!Config", Config.from_yaml)
yaml.FullLoader.add_constructor("!ENV", env_var_constructor)

# Add discord specific constructors
DISCORD_CONSTRUCTORS: dict[
    str, tuple[type[discord.abc.Snowflake], Callable[..., Object[discord.abc.Snowflake] | discord.PartialMessage]]
] = {
    "Emoji": (
        discord.Emoji,
        lambda e: _get_object(discord.Emoji, (discord.Client.get_emoji, e)),
    ),
    "Guild": (
        discord.Guild,
        lambda g: _get_object(discord.Guild, (discord.Client.get_guild, g)),
    ),
    "User": (
        discord.User,
        lambda u: _get_object(discord.User, (discord.Client.get_user, u)),
    ),
    "Channel": (
        discord.abc.GuildChannel,
        lambda g, c: _get_object(discord.abc.GuildChannel, (discord.Client.get_guild, g), (discord.Guild.get_channel, c)),
    ),
    "Member": (
        discord.Member,
        lambda g, m: _get_object(discord.Member, (discord.Client.get_guild, g), (discord.Guild.get_member, m)),
    ),
    "Role": (
        discord.Role,
        lambda g, r: _get_object(discord.Role, (discord.Client.get_guild, g), (discord.Guild.get_role, r)),
    ),
    "Message": (
        discord.Message,
        lambda g, c, m: discord.PartialMessage(
            channel=_get_object(discord.abc.GuildChannel, (discord.Client.get_guild, g), (discord.Guild.get_channel, c)),
            id=m,
        ),
    ),
}

for key, (type_, func) in DISCORD_CONSTRUCTORS.items():
    yaml.FullLoader.add_constructor(f"!{key}", generate_constructor(type_, func))
