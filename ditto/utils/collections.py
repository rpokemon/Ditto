from collections.abc import Iterable, Iterator

from typing import Callable, TypeVar


__all__ = ("summarise_list",)


T = TypeVar("T")


def summarise_list(
    list: list[T], /, func: Callable[[T], str], *, max_items: int = 10, skip_first: bool = False
) -> str:
    count = len(list)
    if count <= skip_first:
        return "None"

    max_items += skip_first
    info = ", ".join(func(item) for item in list[skip_first:max_items])
    if count > max_items:
        info += f" (+{count - max_items} More)"
    return info


def chunk(iterable: Iterable[T], /, size: int) -> Iterator[list[T]]:
    lst = list(iterable)
    for i in range(0, len(lst), size):
        yield lst[i : i + size]
