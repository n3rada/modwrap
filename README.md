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

You can also access the raw module object:

```shell
mod = wrapper.module
print(mod.execute("whoami"))
```


## 💻 CLI Usage

`modwrap` comes with a command-line interface to easily inspect and interact with any Python module.


### List available callables and their signatures

```shell
modwrap list ./examples/shell.py
```
Returns a JSON-formatted list of top-level functions with argument type hints.


### Get docstrings

```shell
modwrap doc ./examples/shell.py --full
```

### Call a function with positional arguments

```shell
modwrap call ./examples/shell.py execute "ls -tAbl"
```

### Call a function with keyword arguments

```shell
modwrap call ./examples/shell.py execute --kwargs '{"command": "ls -tAbl"}'
```

