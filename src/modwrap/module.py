# Built-in imports
import ast
import inspect
import sys
from pathlib import Path
from types import ModuleType
from typing import Dict, List, Optional, Union
from collections.abc import Callable
from importlib.util import spec_from_file_location, module_from_spec


class ModuleWrapper:
    """
    Robust dynamic Python module loader.

    Supports:
    • Standalone scripts
    • Package-aware imports
    • src layout
    • Namespace packages
    • uv / pipx / editable installs
    • Correct relative import resolution

    A module is considered part of a package if it lies under a project
    root containing a `pyproject.toml` file.
    """

    MAX_BYTES: int = 1_000_000

    # Constructor

    def __init__(
        self, module_path: Union[str, Path], allow_large: bool = False
    ) -> None:
        """
        Initialize module loader.

        Args:
            module_path: Path to Python file.
            allow_large: Disable size safeguard for large files.

        Raises:
            ValueError, TypeError, FileNotFoundError, IsADirectoryError
        """
        if not isinstance(module_path, (str, Path)):
            raise TypeError("module_path must be a string or Path")

        self._path = Path(module_path).expanduser().resolve(strict=True)

        if not self._path.is_file():
            raise IsADirectoryError(f"Not a file: {self._path}")

        if not allow_large and self._path.stat().st_size > self.MAX_BYTES:
            raise ValueError(f"File too large: {self._path}")

        self._validate_source()

        self._name: str = self._path.stem
        self._module: ModuleType = self._load_module()

    # Properties

    @property
    def module(self) -> ModuleType:
        """Return the loaded Python module."""
        return self._module

    @property
    def path(self) -> Path:
        """Return absolute module file path."""
        return self._path

    @property
    def name(self) -> str:
        """Return resolved module name."""
        return self._name

    # Public methods

    def get_callable(self, name: str) -> Callable:
        """Return a callable by name."""
        return self._resolve_callable(name)

    def has_callable(self, name: str) -> bool:
        """Check whether callable exists."""
        try:
            self._resolve_callable(name)
            return True
        except Exception:
            return False

    def get_class(
        self,
        name: Optional[str] = None,
        must_inherit: Optional[type] = None,
    ) -> Optional[type]:
        """
        Return first class matching constraints.

        Args:
            name: Class name filter.
            must_inherit: Base class constraint.
        """
        for obj in self._module.__dict__.values():
            if isinstance(obj, type) and obj.__module__ == self._module.__name__:
                if name and obj.__name__ != name:
                    continue
                if must_inherit and not issubclass(obj, must_inherit):
                    continue
                return obj
        return None

    def get_dependencies(self) -> Dict[str, List[str]]:
        """
        Analyze imports as stdlib / third-party / missing.

        Returns:
            Dict with keys: stdlib, third_party, missing
        """
        tree = ast.parse(self._path.read_text(), filename=str(self._path))
        imports = set()

        for node in ast.walk(tree):
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                for name in getattr(node, "names", []):
                    imports.add(name.name.split(".")[0])
                if node.module and node.level == 0:
                    imports.add(node.module.split(".")[0])

        stdlib, third, missing = set(), set(), set()

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

    # Private methods

    def _resolve_callable(self, name: str) -> Callable:
        if "." in name:
            cls, attr = name.split(".", 1)
            obj = self.get_class(cls)
            if not obj or not hasattr(obj, attr):
                raise AttributeError
            fn = getattr(obj, attr)
        else:
            fn = getattr(self._module, name, None)

        if not callable(fn):
            raise TypeError
        return fn

    def _validate_source(self) -> None:
        try:
            ast.parse(self._path.read_text(), filename=str(self._path))
        except SyntaxError as exc:
            raise ValueError(f"Invalid Python code: {self._path}") from exc

    def _load_module(self) -> ModuleType:
        name = self._resolve_module_name()
        spec = spec_from_file_location(
            name,
            str(self._path),
            submodule_search_locations=None if "." not in name else [],
        )

        if spec is None or spec.loader is None:
            raise ImportError(f"Unable to load {name}")

        module = module_from_spec(spec)
        sys.modules[name] = module  # Critical for relative imports

        spec.loader.exec_module(module)
        return module

    def _resolve_module_name(self) -> str:
        project = self._find_project_root()
        if not project:
            return self._path.stem

        for base in (project / "src", project):
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
