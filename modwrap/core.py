import inspect
from pathlib import Path
from types import ModuleType
from typing import Callable, Union, List, Tuple, Dict, get_type_hints
from importlib.util import spec_from_file_location, module_from_spec


class ModuleWrapper:
    def __init__(self, module_path: str):

        if module_path is None:
            raise ValueError("Module path cannot be None.")

        if not isinstance(module_path, (str, Path)):
            raise TypeError("Module path must be a string or a Path object.")

        self.__module_path = Path(module_path).expanduser().resolve(strict=True)

        if not self.__module_path.exists():
            raise FileNotFoundError(f"File not found: {self.__module_path}")

        if not self.__module_path.is_file():
            raise IsADirectoryError(f"Path is not a file: {self.__module_path}")

        if self.__module_path.suffix != ".py":
            raise ValueError(f"Not a .py file: {self.__module_path}")

        self.__module_name = self.__module_path.stem
        self.__module = self._load_module()

    def _load_module(self) -> ModuleType:
        spec = spec_from_file_location(self.__module_name, str(self.__module_path))
        if spec is None or spec.loader is None:
            raise ImportError(
                f"Could not create module spec for '{self.__module_name}'"
            )

        module = module_from_spec(spec)
        try:
            spec.loader.exec_module(module)
        except Exception as exc:
            raise ImportError(
                f"Failed to import module '{self.__module_name}'. Try running it directly first to debug."
            ) from exc
        return module

    def get_callable(self, func_name: str) -> Callable:
        if not hasattr(self.__module, func_name):
            raise AttributeError(f"Function '{func_name}' not found in module.")
        func = getattr(self.__module, func_name)
        if not callable(func):
            raise TypeError(f"'{func_name}' is not a callable.")
        return func

    def validate_signature(
        self,
        func_name: str,
        expected_args: Union[List[Tuple[str, type]], Dict[str, type]],
    ) -> None:
        """
        Validates that a callable within the loaded module has all expected argument
        names and type annotations.

        This method ensures that the specified function exists, is callable, and
        contains all required parameters with the correct type annotations,
        regardless of their order.

        Args:
            func_name (str): The name of the function to validate inside the loaded module.
            expected_args (Union[List[Tuple[str, type]], Dict[str, type]]):
                A list of (arg_name, type) tuples or a dictionary of {arg_name: type}
                representing the expected parameters and their types.

        Raises:
            AttributeError: If the specified function does not exist in the module.
            TypeError: If the specified function is not callable.
            TypeError: If `expected_args` is neither a list of tuples nor a dictionary.
            TypeError: If the function is missing one or more expected parameters.
            TypeError: If the type annotation of any parameter does not match the expected type.
        """
        func = self.get_callable(func_name)
        sig = inspect.signature(func)
        params = list(sig.parameters.values())
        type_hints = get_type_hints(func)

        if isinstance(expected_args, dict):
            for name, expected_type in expected_args.items():
                match = next((p for p in params if p.name == name), None)
                if not match:
                    raise TypeError(f"Missing expected argument: '{name}'")
                actual_type = type_hints.get(name)
                if actual_type != expected_type:
                    raise TypeError(
                        f"Argument '{name}' has type {actual_type}, expected {expected_type}"
                    )

        elif isinstance(expected_args, list):
            for expected_name, expected_type in expected_args:
                param = next((p for p in params if p.name == expected_name), None)
                if not param:
                    raise TypeError(f"Missing expected argument: '{expected_name}'")

                actual_type = type_hints.get(expected_name)
                if actual_type != expected_type:
                    raise TypeError(
                        f"Argument '{expected_name}' has type {actual_type}, expected {expected_type}"
                    )
        else:
            raise TypeError(
                "expected_args must be a dict or list of (name, type) pairs."
            )

    def is_signature_valid(
        self,
        func_name: str,
        expected_args: Union[List[Tuple[str, type]], Dict[str, type]],
    ) -> bool:
        try:
            self.validate_signature(func_name, expected_args)
            return True
        except (TypeError, AttributeError):
            return False
