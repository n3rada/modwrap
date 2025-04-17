**modwrap** is a pure standard library (no external deps) Python3 module wrapper for dynamically loading modules and invoking their functions. 🐍


## 🔧 Programmatic Usage

Use `modwrap` directly in your Python code to load modules, validate function signatures, and execute them safely:


```python
from modwrap.core import ModuleWrapper

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

