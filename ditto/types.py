from jishaku.codeblocks import codeblock_converter, Codeblock  # type: ignore
from jishaku.modules import ExtensionConverter  # type: ignore

__all__ = (
    "CONVERTERS",
    "Extension",
)


class Extension(str):
    ...


CONVERTERS = {
    Codeblock: codeblock_converter,
    Extension: ExtensionConverter,
}
