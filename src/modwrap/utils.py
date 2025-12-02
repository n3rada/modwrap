# modwrap/utils.py

# Built-in imports
from pathlib import Path
from typing import Generator

# Local library imports
from .module import ModuleWrapper

def iter_modules(directory: str) -> "Generator[ModuleWrapper, None, None]":
    """
    Lazily iterates over all Python files (.py) in the specified directory
    and yields a `ModuleWrapper` instance for each file.

    This is useful for memory-efficient processing of modules in large directories,
    or when you don't need to load all modules at once.

    Args:
        directory (str): Path to the directory containing Python module files.

    Yields:
        ModuleWrapper: A wrapper instance for each discovered Python file.

    Raises:
        NotADirectoryError: If the provided path is not a valid directory.
    """
    dir_path = Path(directory).expanduser().resolve()
    if not dir_path.is_dir():
        raise NotADirectoryError(f"{dir_path} is not a directory.")

    for file in dir_path.iterdir():
        if file.is_file() and file.suffix == ".py":
            yield ModuleWrapper(file)


def list_modules(directory: str) -> list[ModuleWrapper]:
    """
    Returns a list of `ModuleWrapper` instances for all Python files (.py)
    in the specified directory.

    This eagerly loads and wraps all modules in the directory into a list, which is
    useful when random access or multiple passes are needed.

    Args:
        directory (str): Path to the directory containing Python module files.

    Returns:
        list[ModuleWrapper]: A list of wrapper instances, one for each .py file found.

    Raises:
        NotADirectoryError: If the provided path is not a valid directory.
    """

    return list(iter_modules(directory))
