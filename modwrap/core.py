import inspect
from pathlib import Path
from types import ModuleType
from typing import Callable, get_type_hints, Union, List, Dict, Optional
from importlib.util import spec_from_file_location, module_from_spec
from functools import lru_cache


class ModuleWrapper:
    def __init__(self, module_path: str):
        """
        Initializes the ModuleWrapper with a path to a Python module.

        Args:
            module_path (str): Path to the .py file.

        Raises:
            ValueError, TypeError, FileNotFoundError, IsADirectoryError, ValueError
        """
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

    def __str__(self) -> str:
        """
        Returns a string representation of the ModuleWrapper instance.
        """
        return f"{self.__module_name} ({self.__module_path})"

    def __repr__(self) -> str:
        return (
            f"ModuleWrapper(module_path={repr(str(self.__module_path))}, "
            f"module_name={repr(self.__module_name)})"
        )

    @property
    def module(self) -> ModuleType:
        """
        Returns the loaded module object.

        Returns:
            ModuleType: The loaded Python module object.
        """
        return self.__module

    @property
    def path(self) -> Path:
        """
        Returns the absolute, resolved file system path to the loaded Python module.

        This is the path provided during initialization, validated to be a `.py` file.

        Returns:
            Path: The resolved `Path` object pointing to the module file.
        """
        return self.__module_path

    @lru_cache(maxsize=128)
    def _load_module(self) -> ModuleType:
        """
        Dynamically loads and returns a Python module from the file path provided during initialization.

        Uses importlib to load the module in a way that is isolated from the system's global namespace.

        Raises:
            ImportError: If the module spec could not be created or the module could not be executed.

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

    @lru_cache(maxsize=128)
    def _resolve_callable(self, name: str) -> Callable:
        """
        Resolves a callable from the module. Supports 'function' and 'Class.method'.

        Args:
            name (str): Either a function name or a dotted 'Class.method'.

        Returns:
            Callable: The callable object.

        Raises:
            AttributeError or TypeError if not found or not callable.
        """
        if "." in name:
            class_name, method_name = name.split(".", 1)
            cls = self.get_class(class_name)
            if not hasattr(cls, method_name):
                raise AttributeError(
                    f"Method '{method_name}' not found in class '{class_name}'"
                )
            func = getattr(cls, method_name)
        else:
            if not hasattr(self.__module, name):
                raise AttributeError(f"Function '{name}' not found in module.")
            func = getattr(self.__module, name)

        if not callable(func):
            raise TypeError(f"'{name}' is not a callable.")

        return func

    def get_callable(self, name: str) -> Callable:
        """
        Retrieves a callable from the module by name.
        Supports both 'function' and 'Class.method' formats.

        Args:
            name (str): Function name or 'Class.method'.

        Returns:
            Callable: The callable object.
        """
        return self._resolve_callable(name)

    def get_class(
        self, name: Optional[str] = None, must_inherit: Optional[type] = None
    ) -> Optional[type]:
        """
        Retrieves a class from the loaded module.

        If `name` is provided, returns the class with that exact name.
        If `name` is not provided, returns the first class found in the module.

        Optionally, if `must_inherit` is specified, the returned class must be a subclass
        of the given type.

        Only classes defined in the target module (not imported ones) are considered.

        Args:
            name (Optional[str]): The name of the class to retrieve. If None, any matching class is returned.
            must_inherit (Optional[type]): If provided, only classes that inherit from this type are considered.

        Returns:
            Optional[type]: The matching class object, or None if no match is found.
        """

        for _, obj in self.module.__dict__.items():
            if not isinstance(obj, type):
                continue

            # Only consider classes defined in this module (not imported ones)
            if obj.__module__ != self.module.__name__:
                continue

            if name and obj.__name__ != name:
                continue

            if must_inherit and not issubclass(obj, must_inherit):
                continue

            return obj  # first match

        return None

    def get_doc(self, func_name: str) -> Optional[str]:
        """
        Retrieves the docstring for a given function in the module.

        Args:
            func_name (str): The name of the function to inspect.

        Returns:
            str | None: Full docstring if available, else None.
        """
        func = self._resolve_callable(func_name)
        doc = inspect.getdoc(func)
        return doc.strip() if doc else None

    def get_doc_summary(self, func_name: str) -> Optional[str]:
        """
        Retrieves the summary line of the docstring for a given function in the module.

        Args:
            func_name (str): The name of the function to inspect.

        Returns:
            str | None: Summary line if available, else None.
        """
        doc = self.get_doc(func_name)
        return doc.splitlines()[0].strip() if isinstance(doc, str) else None

    def get_signature(self, func_path: str) -> Dict[str, Dict[str, object]]:
        """
        Extracts the function signature from a callable.

        Args:
            func_path (str): Name of the function or 'Class.method'.

        Returns:
            dict[str, dict[str, object]]: Mapping of argument names to their type and default.
        """
        func = self._resolve_callable(func_path)
        sig = inspect.signature(func)
        hints = get_type_hints(func)

        signature = {}
        for param in sig.parameters.values():
            if param.name == "self":
                continue
            signature[param.name] = {
                "type": str(hints.get(param.name, "Any")),
                "default": (
                    None if param.default is inspect.Parameter.empty else param.default
                ),
            }

        return signature

    def validate_signature(
        self,
        func_name: str,
        expected_args: Union[List[Union[str, tuple]], Dict[str, type]],
    ) -> None:
        """
        Validates that a function from the loaded module matches the expected argument names
        and (optionally) their type annotations.

        Args:
            func_name (str): The name of the function to validate.
            expected_args (list or dict): Expected arguments and their types.

        Raises:
            TypeError: If validation fails.
        """
        func = self._resolve_callable(func_name)
        sig = inspect.signature(func)
        params = {p.name: p for p in sig.parameters.values()}
        type_hints = get_type_hints(func)

        if isinstance(expected_args, dict):
            self._validate_dict_signature(expected_args, params, type_hints)
        elif isinstance(expected_args, list):
            self._validate_list_signature(expected_args, params, type_hints)
        else:
            raise TypeError(
                "expected_args must be a dict or list of (name, type) pairs."
            )

    def is_signature_valid(
        self,
        func_name: str,
        expected_args: Union[List, Dict],
    ) -> bool:
        """
        Checks whether a function in the loaded module matches the given argument names
        and (optionally) their expected types.

        This is a non-raising alternative to `validate_signature()`.

        Returns:
            bool: True if valid, False otherwise.
        """
        try:
            self.validate_signature(func_name, expected_args)
            return True
        except (TypeError, AttributeError):
            return False

    def _validate_dict_signature(
        self,
        expected_args: Dict[str, type],
        params: Dict[str, inspect.Parameter],
        type_hints: Dict[str, type],
    ) -> None:
        """
        Validates that each argument in `expected_args` exists in the actual function signature
        (`params`) and matches the expected type from `type_hints`.

        This is used to verify that a function's signature aligns with a dictionary-based
        specification of argument names and types.

        Args:
            expected_args (Dict[str, type]): A mapping of expected argument names to expected types.
            params (Dict[str, inspect.Parameter]): Actual parameters from the target function's signature.
            type_hints (Dict[str, type]): Type hints extracted from the function to validate against.

        Raises:
            TypeError: If an expected argument is missing from the function's signature.
            TypeError: If the actual type hint for an argument does not match the expected type.
        """
        for name, expected_type in expected_args.items():
            if name not in params:
                raise TypeError(f"Missing expected argument: '{name}'")
            actual_type = type_hints.get(name)
            if actual_type != expected_type:
                raise TypeError(
                    f"Argument '{name}' has type {actual_type}, expected {expected_type}"
                )

    def _validate_list_signature(
        self,
        expected_args: List[Union[str, tuple]],
        params: Dict[str, inspect.Parameter],
        type_hints: Dict[str, type],
    ) -> None:
        """
        Validates that each expected argument is present in the actual function parameters
        and (optionally) matches the expected type.

        This version accepts a list of expected argument names (as strings) or
        (name, type) tuples. If only a name is provided, the type hint from the function
        itself is used for comparison.

        Args:
            expected_args (List[Union[str, tuple]]): List of argument names or (name, type) pairs.
            params (Dict[str, inspect.Parameter]): Parameters from the function's signature.
            type_hints (Dict[str, type]): Type hints extracted from the function.

        Raises:
            TypeError: If an expected argument is missing from the function signature.
            TypeError: If the actual type hint for an argument does not match the expected type.
            TypeError: If an item in the expected_args list is neither a string nor a (name, type) tuple.
        """
        for item in expected_args:
            if isinstance(item, tuple) and len(item) == 2:
                expected_name, expected_type = item
            elif isinstance(item, str):
                expected_name = item
                expected_type = type_hints.get(expected_name)
            else:
                raise TypeError(f"Invalid item in expected_args list: {item}")

            if expected_name not in params:
                raise TypeError(f"Missing expected argument: '{expected_name}'")

            if expected_type is not None:
                actual_type = type_hints.get(expected_name)
                if actual_type != expected_type:
                    raise TypeError(
                        f"Argument '{expected_name}' has type {actual_type}, expected {expected_type}"
                    )
