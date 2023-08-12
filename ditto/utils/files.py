import pathlib
import types


def get_base_dir(module: types.ModuleType | None = None) -> pathlib.Path:
    if module is None:
        file = pathlib.Path(__file__).parent
    else:
        file = module.__file__
    if file is None:
        raise RuntimeError("Could not determine the base directory.")
    return pathlib.Path(file).parent.relative_to(pathlib.Path.cwd())
