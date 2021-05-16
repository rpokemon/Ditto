import pathlib
import types

from typing import Optional


def get_base_dir(module: Optional[types.ModuleType] = None) -> pathlib.Path:
    if module is None:
        file = __file__
    else:
        file = module.__file__
    return pathlib.Path(file).parent.parent.relative_to(pathlib.Path.cwd())
