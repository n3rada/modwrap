import inspect
from pathlib import Path
from types import ModuleType
from typing import Callable, Union, Tuple, get_type_hints
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
        """
        Dynamically loads and returns a Python module from the file path provided during initialization.

        Uses importlib to load the module in a way that is isolated from the system's global namespace.

        Raises:
            ImportError: If the module spec could not be created or the module could not be executed.
            ImportError: If the module contains import-time errors or exceptions during loading.

        Returns:
            ModuleType: The loaded Python module object.
        """
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
        """
        Retrieves a callable (function) by name from the loaded module.

        Args:
            func_name (str): The name of the function to retrieve from the module.

        Raises:
            AttributeError: If the function does not exist in the module.
            TypeError: If the attribute exists but is not callable.

        Returns:
            Callable: The function object retrieved from the module.
        """
        if not hasattr(self.__module, func_name):
            raise AttributeError(f"Function '{func_name}' not found in module.")
        func = getattr(self.__module, func_name)
        if not callable(func):
            raise TypeError(f"'{func_name}' is not a callable.")
        return func

    def get_class(self, class_name: str, must_inherit: type = None) -> type:
        """
        Retrieves a class by name from the loaded module, optionally verifying inheritance.

        Args:
            class_name (str): Name of the class to retrieve.
            must_inherit (type, optional): Base class that the target must inherit from.

        Raises:
            AttributeError: If the class is not found in the module.
            TypeError: If the attribute exists but is not a class.
            TypeError: If must_inherit is specified and the class does not inherit from it.

        Returns:
            type: The class object.
        """
        if not hasattr(self.__module, class_name):
            raise AttributeError(f"Class '{class_name}' not found in module.")

        cls = getattr(self.__module, class_name)

        if not isinstance(cls, type):
            raise TypeError(f"'{class_name}' is not a class.")

        if must_inherit is not None and not issubclass(cls, must_inherit):
            raise TypeError(
                f"'{class_name}' must inherit from {must_inherit.__name__}."
            )

        return cls

    def get_doc(self, func_name: str) -> Union[str, None]:
        """
        Retrieves the docstring for a given function in the module.

        Args:
            func_name (str): The name of the function to inspect.

        Returns:
            Union[str, None]: Full docstring if available, else None.
        """
        func = self.get_callable(func_name)
        doc = inspect.getdoc(func)
        if not doc:
            return None
        return doc.strip()

    def get_doc_summary(self, func_name: str) -> Union[str, None]:
        """
        Retrieves the summary line of the docstring for a given function in the module.

        Args:
            func_name (str): The name of the function to inspect.

        Returns:
            Union[str, None]: Summary line if available, else None.
        """
        doc = self.get_doc(func_name)
        if not doc:
            return None
        return doc.splitlines()[0].strip()

    def get_signature(self, func_name: str) -> dict:
        """
        Returns the signature of a function, including parameter names, types, and defaults.

        Args:
            func_name (str): The name of the function to inspect.

        Returns:
            dict: A mapping of parameter names to their type hints as strings.
                Includes default value when available.
        """
        func = self.get_callable(func_name)
        sig = inspect.signature(func)
        hints = get_type_hints(func)

        signature = {}
        for param in sig.parameters.values():
            if param.name == "self":
                continue

            param_type = hints.get(param.name, "Any")
            default = (
                None if param.default is inspect.Parameter.empty else param.default
            )

            signature[param.name] = {
                "type": str(param_type),
                "default": default,
            }

        return signature

    def validate_signature(
        self,
        func_name: str,
        expected_args: Union[list[Tuple[str, type]], dict[str, type]],
    ) -> None:
        """
        Validates that a function from the loaded module matches the expected argument names
        and (optionally) their type annotations.

        Supports both dictionary and list formats for specifying expected arguments:
        - A dictionary of {name: type} enforces both name and type.
        - A list of argument names as strings (e.g., ["x", "y"]) enforces presence.
        - A list of (name, type) tuples enforces both presence and type.

        Args:
            func_name (str): The name of the function to validate from the module.
            expected_args (Union[list[Union[str, Tuple[str, type]]], dict[str, type]]):
                Expected arguments and their types.

        Raises:
            TypeError: If the function does not have the expected arguments.
            TypeError: If a provided argument does not match the expected type.
            TypeError: If expected_args is not a supported format (dict or list).
            TypeError: If a list entry is neither a string nor a (name, type) tuple.
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
            for item in expected_args:
                if isinstance(item, tuple) and len(item) == 2:
                    expected_name, expected_type = item
                elif isinstance(item, str):
                    expected_name = item
                    expected_type = type_hints.get(expected_name)
                else:
                    raise TypeError(f"Invalid item in expected_args list: {item}")

                param = next((p for p in params if p.name == expected_name), None)
                if not param:
                    raise TypeError(f"Missing expected argument: '{expected_name}'")

                if expected_type is not None:
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
        expected_args: Union[list, dict],
    ) -> bool:
        """
        Checks whether a function in the loaded module matches the given argument names
        and (optionally) their expected types.

        This is a non-raising alternative to `validate_signature()`. Returns `True` if
        validation passes, and `False` otherwise.

        Returns:
            bool: True if the function matches the expected signature, False otherwise.
        """
        try:
            self.validate_signature(func_name, expected_args)
            return True
        except (TypeError, AttributeError):
            return False

    # Properties
    @property
    def module(self) -> ModuleType:
        """
        Returns the loaded module object.

        Returns:
            ModuleType: The loaded Python module object.
        """
        return self.__module
