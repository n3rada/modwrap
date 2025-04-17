# Standard libraries
import unittest
from pathlib import Path

# Local libraries
from modwrap import ModuleWrapper


class TestModuleWrapper(unittest.TestCase):
    def setUp(self):
        self.plugin_path = Path(__file__).parent / "plugin.py"

    def test_signature_with_dict(self):
        wrapper = ModuleWrapper(self.plugin_path)
        wrapper.validate_signature("execute", {"command": str})

    def test_signature_with_list_of_tuples(self):
        wrapper = ModuleWrapper(self.plugin_path)
        wrapper.validate_signature("execute", [("command", str)])

    def test_get_callable_and_call(self):
        wrapper = ModuleWrapper(self.plugin_path)
        func = wrapper.get_callable("execute")
        result = func("echo")
        self.assertEqual(result, "Simulated execution: echo")

    def test_direct_callable_access(self):
        wrapper = ModuleWrapper(self.plugin_path)
        result = wrapper.module.execute("ping")
        self.assertEqual(result, "Simulated execution: ping")

    def test_invalid_arg_type(self):
        wrapper = ModuleWrapper(self.plugin_path)
        func = wrapper.get_callable("execute")
        with self.assertRaises(TypeError):
            func(123)  # Not a string

    def test_missing_signature_param(self):
        wrapper = ModuleWrapper(self.plugin_path)
        with self.assertRaises(TypeError):
            wrapper.validate_signature("execute", {"command": str, "extra": int})

    def test_wrong_type_in_signature(self):
        wrapper = ModuleWrapper(self.plugin_path)
        with self.assertRaises(TypeError):
            wrapper.validate_signature("execute", {"command": int})  # should be str


if __name__ == "__main__":
    unittest.main()
