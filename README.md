**modwrap** is a pure Python 3 utility (no external dependencies) that lets you dynamically load and execute functions from any Python module — either via code or command line. 🐍

## 📦 Installation
Install directly from [PyPI](https://pypi.org/project/modwrap/):
```shell
pip install modwrap
```

## 🔧 Programmatic Usage

Use `modwrap` directly in your Python code to load modules, validate function signatures, and execute them safely:


```python
from modwrap import ModuleWrapper

wrapper = ModuleWrapper("./tests/plugin.py")

# Optional: Validate the function signature before calling
wrapper.validate_signature("execute", {"command": str})

# Load and call the function
func = wrapper.get_callable("execute")
result = func(command="whoami")
print(result)
```

## 💻 CLI Usage

`modwrap` comes with a command-line interface to easily inspect and interact with any Python module.


### List available callables and their signatures

```shell
modwrap list tests/plugin.py
```

### Call a function with positional arguments

```shell
modwrap call tests/plugin.py execute "ls -tAbl"
```

### Call a function with keyword arguments

```shell
modwrap call tests/plugin.py execute --kwargs '{"command": "ls -tAbl"}'
```

