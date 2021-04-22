import pathlib


def get_base_dir() -> pathlib.Path:
    return pathlib.Path(__file__).parent.parent
