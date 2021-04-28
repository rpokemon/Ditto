import datetime
from itertools import cycle

from typing import Any, Literal, TypeVar, Union

import discord


__all__ = (
    "ZWSP",
    "codeblock",
    "yes_no",
    "as_columns",
    "utc_offset",
    "ordinal",
    "regional_indicator",
    "keycap_digit",
    "plural",
    "truncate",
    "rank_medal",
)


T = TypeVar("T")


ZWSP = "\u200B"


def codeblock(text, *, language: str = "") -> str:
    return f"```{language}\n{text}\n```"


def yes_no(obj: Any) -> Literal["Yes", "No"]:
    return "Yes" if obj else "No"


def _items_in_col(n_items, cols):
    at_least_per_col = n_items // cols
    num_filled_in_last = n_items % cols
    return (at_least_per_col + 1,) * num_filled_in_last + (at_least_per_col,) * (cols - num_filled_in_last)


def _transpose(items: list[T], columns: int) -> list[T]:
    result = []
    num_items = len(items)

    per_col = _items_in_col(num_items, columns)
    to_skip = cycle(per_col)

    i = 0
    for _ in items:
        result.append(items[i])
        i += next(to_skip)
        if i >= num_items:
            i += 1
            i %= num_items

    return result


def as_columns(items: list[str], /, columns: int = 2, transpose: bool = False, fill: str = " ") -> str:

    if transpose:
        items = _transpose(items, columns)

    result = ""

    max_sizes = [0 for _ in range(columns)]

    chunks = list(discord.utils.as_chunks((i for i in items), columns))

    if not chunks:
        return ""

    max_columns = len(chunks[0])

    for line in chunks:
        for column, item in enumerate(line):
            if column + 1 < max_columns and column + 1 == len(line):
                continue
            max_sizes[column] = max(len(item), max_sizes[column])

    for line in chunks:
        row = ""

        for item, max_size in zip(line, max_sizes):
            row += item.ljust(max_size + 1, fill)

        result += row.strip() + "\n"

    return result


def utc_offset(offset: Union[float, datetime.timedelta, datetime.tzinfo], /) -> str:
    if isinstance(offset, (int, float)):
        offset = datetime.timedelta(seconds=offset)
    elif isinstance(offset, datetime.tzinfo):
        now = datetime.datetime.now(datetime.timezone.utc)
        offset = offset.utcoffset(now) or datetime.timedelta(seconds=0)

    return datetime.timezone(offset).tzname(None)  # type: ignore[return-value]


def ordinal(number: int, /) -> str:
    return f'{number}{"tsnrhtdd"[(number // 10 % 10 != 1) * (number % 10 < 4) * number % 10 :: 4]}'


def regional_indicator(c: str) -> str:
    """Returns a regional indicator emoji given a character."""
    return chr(0x1F1E6 - ord("A") + ord(c.upper()))


def keycap_digit(c: Union[int, str]) -> str:
    """Returns a keycap digit emoji given a character."""
    c = int(c)
    if 0 < c < 10:
        return str(c) + "\U0000FE0F\U000020E3"
    elif c == 10:
        return "\U000FE83B"
    raise ValueError("Invalid keycap digit")


class plural:
    def __init__(self, value: int) -> None:
        self.value = value

    def __format__(self, format_spec: str) -> str:
        singular, _, plural = format_spec.partition("|")
        plural = plural or f"{singular}s"
        return f"{self.value} {plural if abs(self.value) != 1 else singular}"


class truncate:
    def __init__(self, value: str) -> None:
        self.value = value

    def __format__(self, format_spec: str) -> str:
        max_len = int(format_spec)

        if len(self.value) <= max_len:
            return self.value
        return f"{self.value[:max_len - 3]}..."


def rank_medal(rank: int, *, one_indexed: bool = False) -> str:
    return {
        0: "\N{FIRST PLACE MEDAL}",
        1: "\N{SECOND PLACE MEDAL}",
        2: "\N{THIRD PLACE MEDAL}",
    }.get(rank - one_indexed, "\N{SPORTS MEDAL}")
