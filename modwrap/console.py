import inspect
import typing
import argparse
import ast
import json
import sys

# Local libraries
from modwrap.core import ModuleWrapper


def cmd_list(args):
    wrapper = ModuleWrapper(args.module)
    funcs = []

    for name in dir(wrapper.module):
        obj = getattr(wrapper.module, name)
        if callable(obj) and not name.startswith("_"):
            funcs.append({"name": name, "args": wrapper.get_signature(name)})

    print(json.dumps(funcs, indent=2))


def cmd_call(args):

    wrapper = ModuleWrapper(args.module)
    func = wrapper.get_callable(args.function)

    # Positional args
    parsed_args = []
    for arg in args.args or []:
        try:
            parsed_args.append(ast.literal_eval(arg))
        except Exception:
            parsed_args.append(arg)

    # Keyword args
    kwargs = {}
    if args.kwargs:
        try:
            kwargs = ast.literal_eval(args.kwargs)
            if not isinstance(kwargs, dict):
                raise ValueError
        except Exception:
            print("Arguments must be a valid Python dict, e.g.: '{\"x\": 1}'")
            sys.exit(1)

    result = func(*parsed_args, **kwargs)
    print(result)


def cmd_doc(args):
    wrapper = ModuleWrapper(args.module)

    if args.full:
        doc = wrapper.get_doc(args.function)
    else:
        doc = wrapper.get_doc_summary(args.function)

    if doc:
        print(doc)
    else:
        print(f"No docstring found for function '{args.function}'.")


def run():
    parser = argparse.ArgumentParser(
        prog="modwrap", add_help=True, description="Python dynamic module wrapper"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    p_list = subparsers.add_parser("list", help="List callables in the module")
    p_list.add_argument("module", help="Path to the .py file")
    p_list.set_defaults(func=cmd_list)

    p_call = subparsers.add_parser("call", help="Call a function with args/kwargs")
    p_call.add_argument("module", help="Path to the .py file")
    p_call.add_argument("function", help="Function to call")
    p_call.add_argument("args", nargs="*", help="Positional arguments")
    p_call.add_argument(
        "--kwargs", help="Keyword arguments as a dict string, e.g. '{\"x\": 1}'"
    )
    p_call.set_defaults(func=cmd_call)

    p_doc = subparsers.add_parser("doc", help="Show function docstring")
    p_doc.add_argument("module", help="Path to the .py file")
    p_doc.add_argument("function", help="Function to document")
    p_doc.add_argument(
        "--full", action="store_true", help="Show full docstring instead of summary"
    )
    p_doc.set_defaults(func=cmd_doc)

    args = parser.parse_args()
    args.func(args)
