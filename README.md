**modwrap** is a pure Python 3 utility (no external dependencies) that lets you dynamically load and execute functions from any Python module. 🐍

## 📦 Installation

Install directly from [PyPI](https://pypi.org/project/modwrap/):
```shell
pip install modwrap
```

Could be add to your project using `poetry`:
```shell
poetry add modwrap
```

## 🔧 Programmatic Usage

Use `modwrap` in your Python code to load modules, introspect callable signatures, and execute functions dynamically:

### Basic Usage

```python
from modwrap import ModuleWrapper

wrapper = ModuleWrapper("./examples/shell.py")

# Load and call a function
func = wrapper.get_callable("execute")
result = func(command="whoami")
print(result)

# Access the raw module object
mod = wrapper.module
print(mod.execute("whoami"))
```

### Signature Validation

Validate function signatures with type checking:

```python
# Validate with type hints
wrapper.validate_signature("execute", {"command": str, "timeout": float})

# Or use the non-raising version
if wrapper.has_signature("execute", {"command": str}):
    func = wrapper.get_callable("execute")
    result = func(command="ls")
```

Validate only argument names (no type checking):

```python
# Validate argument names only
wrapper.validate_args("execute", ["command", "timeout"])

# Or use the non-raising version
if wrapper.has_args("execute", ["command", "timeout"]):
    func = wrapper.get_callable("execute")
    result = func(command="ls", timeout=30)
```

### Dependency Analysis

Check what packages need to be installed:

```python
deps = wrapper.get_dependencies()

print("Standard library:", deps['stdlib'])
print("Third-party packages:", deps['third_party'])
print("Local imports:", deps['local'])

# Check for missing dependencies
if deps['missing']:
    print(f"Install missing packages: pip install {' '.join(deps['missing'])}")
```

### Introspection

```python
# Get function signature details
sig = wrapper.get_signature("execute")
print(sig)  # {'command': {'type': 'str', 'default': None}, ...}

# Get docstrings
doc = wrapper.get_doc("execute")  # Full docstring
summary = wrapper.get_doc_summary("execute")  # First line only

# Check if callable exists
if wrapper.has_callable("execute"):
    print("Function exists!")

# Get classes from module
cls = wrapper.get_class("MyClass")  # Get specific class
cls = wrapper.get_class(must_inherit=BaseClass)  # Get class by inheritance
```

### Working with Classes

```python
# Load and call class methods
wrapper.get_callable("MyClass.method_name")

# Get a class and instantiate it
MyClass = wrapper.get_class("MyClass")
instance = MyClass()
```

### Utility Functions

Discover all modules in a directory:

```python
from modwrap import list_modules, iter_modules

# Get all modules as a list
modules = list_modules("./my_modules")
for wrapper in modules:
    print(wrapper.name)

# Or iterate lazily (memory efficient)
for wrapper in iter_modules("./my_modules"):
    if wrapper.has_callable("main"):
        wrapper.get_callable("main")()
```

