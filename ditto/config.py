from __future__ import annotations

import os
import pathlib
from collections.abc import Callable
from typing import Any, Optional, Union

import discord
import yaml

from .utils.files import get_base_dir

__all__ = (
    "CONFIG",
    "load_config",
    "load_global_config",
)

MISSING: Any = discord.utils.MISSING


BASE_DIR = get_base_dir()


_bot: discord.Client = MISSING


class Object(discord.Object):
    def __init__(self, id: int, func: Callable[..., Any]) -> None:
        self._func = func
        super().__init__(id)

    def __getattribute__(self, name: str) -> Any:
        if name in ("_func", "id", "created_at"):
            return object.__getattribute__(self, name)
        return getattr(self._func(), name)

    def __repr__(self) -> str:
        return getattr(self._func(), "__repr__", super().__repr__)()


def _get_object(*getters: tuple[Callable[[Any, int], Any], int]) -> Any:
    obj = _bot
    for func, id in getters:
        obj = func(obj, id)
        if obj is None:
            return discord.Object(id=id)
    return obj


def env_var_constructor(loader: yaml.Loader, node: yaml.ScalarNode) -> Optional[str]:
    if node.id != "scalar":
        raise TypeError("Expected a string")

    value = loader.construct_scalar(node)
    key = str(value)

    return os.getenv(key)


def generate_constructor(func: Callable[..., Any]) -> Callable[[yaml.Loader, yaml.ScalarNode], discord.abc.Snowflake]:
    def constructor(loader: yaml.Loader, node: yaml.ScalarNode) -> Object:
        ids = [int(x) for x in loader.construct_scalar(node).split()]  # type: ignore
        return Object(ids[-1], lambda: func(*ids))

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


def load_config(file: Union[str, pathlib.Path], bot: discord.Client) -> Config:
    with open(file, encoding="utf-8") as f:
        config = yaml.load(f, Loader=yaml.FullLoader)
    config._bot = bot
    return config


def update_config(config: Config, file: Union[str, pathlib.Path]) -> None:
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
DISCORD_CONSTRUCTORS: dict[str, Callable[..., Any]] = {
    "Emoji": lambda e: _get_object((discord.Client.get_emoji, e)),
    "Guild": lambda g: _get_object((discord.Client.get_guild, g)),
    "User": lambda u: _get_object((discord.Client.get_user, u)),
    "Channel": lambda g, c: _get_object((discord.Client.get_guild, g), (discord.Guild.get_channel, c)),
    "Member": lambda g, m: _get_object((discord.Client.get_guild, g), (discord.Guild.get_member, m)),
    "Role": lambda g, r: _get_object((discord.Client.get_guild, g), (discord.Guild.get_role, r)),
    "Message": lambda g, c, m: discord.PartialMessage(
        channel=_get_object((discord.Client.get_guild, g), (discord.Guild.get_channel, c)), id=m
    ),
}

for key, func in DISCORD_CONSTRUCTORS.items():
    yaml.FullLoader.add_constructor(f"!{key}", generate_constructor(func))
