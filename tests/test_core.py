# Standard libraries
import unittest
from pathlib import Path

# Local libraries
from modwrap import ModuleWrapper


class TestModuleWrapper(unittest.TestCase):
    def setUp(self):
        self.plugin_path = Path(__file__).parent / "plugin.py"

    def test_load_and_validate_execute(self):
        wrapper = ModuleWrapper(self.plugin_path)
        wrapper.validate_signature("execute", {"command": str, "timeout": float})
        result = wrapper.get_callable("execute")("hello", 2.5)
        self.assertEqual(result, "Executed: hello in 2.5s")


if __name__ == "__main__":
    unittest.main()
