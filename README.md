**modwrap** is a pure Python 3 utility (no external dependencies) that lets you dynamically load and execute functions from any Python module — either via code or command line. 🐍

## 📦 Installation

Install directly from [PyPI](https://pypi.org/project/modwrap/):
```shell
pip install modwrap
```

## 🔧 Programmatic Usage

Use `modwrap` in your Python code to load modules, introspect callable signatures, and execute functions dynamically:

```python
from modwrap import ModuleWrapper

wrapper = ModuleWrapper("./examples/shell.py")

# Optional: Validate the function signature before calling
wrapper.validate_signature("execute", {"command": str})

# Load and call the function
func = wrapper.get_callable("execute")
result = func(command="whoami")
print(result)
```

