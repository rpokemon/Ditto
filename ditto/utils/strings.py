import datetime
from itertools import cycle

from typing import Any, Literal, TypeVar, Union

from .collections import chunk


__all__ = (
    "codeblock",
    "yes_no",
    "as_columns",
    "utc_offset",
    "ordinal",
)


T = TypeVar("T")


ZWSP = "\u200B"


def codeblock(text, *, language: str = "") -> str:
    return f"```{language}\n{text}\n```"


def yes_no(obj: Any) -> Literal["Yes", "No"]:
    return "Yes" if bool(obj) else "No"


def _items_in_col(n_items, cols):
    at_least_per_col = n_items // cols
    num_filled_in_last = n_items % cols
    return (at_least_per_col + 1,) * num_filled_in_last + (at_least_per_col,) * (cols - num_filled_in_last)


def _transpose(items: list[T], columns: int) -> list[T]:
    result = []

    *per_col, _ = _items_in_col(len(items), columns)
    per_col = (*per_col, per_col[0])
    to_skip = cycle(per_col)
    i = 0
    for (_, ts) in zip(range(len(items)), to_skip):
        result.append(items[i])
        i = (i + ts) % len(items)

    return result


def as_columns(items: list[str], /, columns: int = 2, transpose: bool = False, fill: str = " ") -> str:

    if transpose:
        items = _transpose(items, columns)

    result = ""

    max_sizes = [0 for _ in range(columns)]

    chunks = list(chunk(items, columns))

    for line in chunks:
        for column, item in enumerate(line):
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
