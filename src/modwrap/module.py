# modwrap/core.py

# Built-in imports
import ast
import inspect
import sys
from pathlib import Path
from types import ModuleType
from typing import Dict, List, Optional, Union, get_type_hints
from collections.abc import Callable
from importlib.util import spec_from_file_location, module_from_spec


class ModuleWrapper:
    """
    Dynamic and safe Python module loader.

    Supports:
    - Standalone modules
    - Packages and namespace packages
    - pyproject.toml discovery
    - src layout
    - uv / pipx compatibility
    - Relative imports
    """

    # Constants

    MAX_BYTES: int = 1_000_000

    # Constructor

    def __init__(
        self, module_path: Union[str, Path], allow_large_file: bool = False
    ) -> None:
        if not isinstance(module_path, (str, Path)):
            raise TypeError("module_path must be a string or Path")

        self._path = Path(module_path).expanduser().resolve(strict=True)

        if not self._path.exists():
            raise FileNotFoundError(f"File not found: {self._path}")

        if not self._path.is_file():
            raise IsADirectoryError(f"Not a file: {self._path}")

        if not allow_large_file and self._path.stat().st_size > self.MAX_BYTES:
            raise ValueError(f"File too large: {self._path}")

        self._validate_source()

        self._name: str = self._path.stem
        self._module: ModuleType = self._load_module()

    # Dunder methods

    def __repr__(self) -> str:
        return f"ModuleWrapper(path={self._path!s}, name={self._name!r})"

    def __str__(self) -> str:
        return str(self._path)

    # Properties

    @property
    def module(self) -> ModuleType:
        """Loaded module object."""
        return self._module

    @property
    def path(self) -> Path:
        """Absolute file path."""
        return self._path

    @property
    def name(self) -> str:
        """Resolved module name."""
        return self._name

    # Public API

    def get_callable(self, name: str) -> Callable:
        """Return callable by name (supports Class.method)."""
        return self._resolve_callable(name)

    def has_callable(self, name: str) -> bool:
        """Check whether callable exists."""
        try:
            self._resolve_callable(name)
            return True
        except Exception:
            return False

    def validate_args(self, func_name: str, expected: List[str]) -> None:
        """Validate function has given arguments."""
        fn = self._resolve_callable(func_name)
        sig = inspect.signature(fn)
        names = {p.name for p in sig.parameters.values() if p.name != "self"}

        for arg in expected:
            if arg not in names:
                raise TypeError(f"Missing expected argument: {arg}")

    def has_args(self, func_name: str, expected: List[str]) -> bool:
        """Non-raising version of validate_args()."""
        try:
            self.validate_args(func_name, expected)
            return True
        except Exception:
            return False

    def validate_signature(
        self,
        func_name: str,
        expected: Union[Dict[str, type], List[Union[str, tuple]]],
    ) -> None:
        """Validate callable signature and types."""
        fn = self._resolve_callable(func_name)
        sig = inspect.signature(fn)
        params = sig.parameters
        annotations = fn.__annotations__

        if isinstance(expected, dict):
            for k, t in expected.items():
                if k not in params:
                    raise TypeError(f"Missing parameter: {k}")
                if annotations.get(k) != t:
                    raise TypeError(
                        f"Bad type for {k}: expected {t}, got {annotations.get(k)}"
                    )

        elif isinstance(expected, list):
            for item in expected:
                if isinstance(item, tuple):
                    name, t = item
                else:
                    name, t = item, None

                if name not in params:
                    raise TypeError(f"Missing parameter: {name}")
                if t and annotations.get(name) != t:
                    raise TypeError(
                        f"Bad type for {name}: expected {t}, got {annotations.get(name)}"
                    )

        else:
            raise TypeError("expected must be dict or list")

    def has_signature(
        self,
        func_name: str,
        expected: Union[Dict[str, type], List],
    ) -> bool:
        """Non-raising version of validate_signature()."""
        try:
            self.validate_signature(func_name, expected)
            return True
        except Exception:
            return False

    def get_class(
        self, name: Optional[str] = None, must_inherit: Optional[type] = None
    ) -> Optional[type]:
        """Return matching class defined in module."""
        for obj in self._module.__dict__.values():
            if not isinstance(obj, type):
                continue
            if obj.__module__ != self._module.__name__:
                continue
            if name and obj.__name__ != name:
                continue
            if must_inherit and not issubclass(obj, must_inherit):
                continue
            return obj
        return None

    def get_doc(self, func_name: str) -> Optional[str]:
        """Return full docstring of a callable."""
        fn = self._resolve_callable(func_name)
        doc = inspect.getdoc(fn)
        return doc.strip() if doc else None

    def get_doc_summary(self, func_name: str) -> Optional[str]:
        """Return first line of callable docstring."""
        doc = self.get_doc(func_name)
        return doc.splitlines()[0].strip() if doc else None

    def get_signature(self, func_path: str) -> Dict[str, Dict[str, object]]:
        """
        Extract the signature of a callable as a structured mapping.

        Args:
            func_path: Name of the function or 'Class.method'.

        Returns:
            Dict[str, Dict[str, object]]: Mapping of argument names to:
                - "type": stringified type annotation or "Any"
                - "default": default value or None if no default
        """
        fn = self._resolve_callable(func_path)
        sig = inspect.signature(fn)
        hints = get_type_hints(fn)

        signature: Dict[str, Dict[str, object]] = {}
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

    def get_dependencies(self) -> Dict[str, List[str]]:
        """Categorize imports as stdlib / third-party / missing."""
        tree = ast.parse(self._path.read_text(), filename=str(self._path))
        imports = set()

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for n in node.names:
                    imports.add(n.name.split(".")[0])
            elif isinstance(node, ast.ImportFrom):
                if node.module and node.level == 0:
                    imports.add(node.module.split(".")[0])

        stdlib = set()
        third = set()
        missing = set()

        for name in imports:
            try:
                __import__(name)
                mod = sys.modules.get(name)
                if mod and getattr(mod, "__file__", "").startswith(sys.base_prefix):
                    stdlib.add(name)
                else:
                    third.add(name)
            except ImportError:
                missing.add(name)

        return {
            "stdlib": sorted(stdlib),
            "third_party": sorted(third),
            "missing": sorted(missing),
        }

    # Internal helpers

    def _resolve_callable(self, name: str) -> Callable:
        if "." in name:
            cls, func = name.split(".", 1)
            obj = self.get_class(cls)
            if not obj:
                raise AttributeError(cls)
            fn = getattr(obj, func, None)
        else:
            fn = getattr(self._module, name, None)

        if not callable(fn):
            raise TypeError(f"{name} is not callable")

        return fn

    def _validate_source(self) -> None:
        try:
            ast.parse(self._path.read_text(), filename=str(self._path))
        except SyntaxError as exc:
            raise ValueError(f"Invalid Python syntax in {self._path}") from exc

    def _load_module(self) -> ModuleType:
        name = self._resolve_module_name()

        spec = spec_from_file_location(
            name,
            str(self._path),
            submodule_search_locations=None if "." not in name else [],
        )

        if spec is None or spec.loader is None:
            raise ImportError(f"Unable to load module: {name}")

        module = module_from_spec(spec)
        sys.modules[name] = module
        spec.loader.exec_module(module)
        return module

    def _resolve_module_name(self) -> str:
        root = self._find_project_root()

        if not root:
            return self._path.stem

        for base in (root / "src", root):
            try:
                rel = self._path.relative_to(base).with_suffix("")
                return ".".join(rel.parts)
            except ValueError:
                continue

        return self._path.stem

    def _find_project_root(self) -> Optional[Path]:
        p = self._path.parent
        while p != p.parent:
            if (p / "pyproject.toml").exists():
                return p
            p = p.parent
        return None
