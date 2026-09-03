"""Generate Python modules and tests from a parsed coding goal."""

from __future__ import annotations

import ast
import os
import re
from typing import Dict, List, Optional, Tuple

from agent.coding.goal_spec import CodingGoalSpec, FunctionSpec

_ASSERT_RE = re.compile(r"assert\s+([A-Za-z_][A-Za-z0-9_]*)\(([^)]*)\)\s*==\s*(.+)")


def _infer_body(args: tuple, expected: object) -> Optional[Tuple[str, str]]:
    if len(args) == 2:
        a, b = args
        try:
            if a + b == expected:
                return "a, b", "return a + b"
            if a - b == expected:
                return "a, b", "return a - b"
            if a * b == expected:
                return "a, b", "return a * b"
            if b and a / b == expected:
                return "a, b", "return a / b"
            if min(a, b) == expected:
                return "a, b", "return min(a, b)"
            if max(a, b) == expected:
                return "a, b", "return max(a, b)"
        except Exception:
            return None
    if len(args) == 1 and args[0] == expected:
        return "value", "return value"
    if len(args) == 3:
        value, lo, hi = args
        try:
            if max(lo, min(hi, value)) == expected:
                return "value, lo, hi", "return max(lo, min(hi, value))"
        except Exception:
            return None
    return None


def infer_spec_from_workspace(workspace_dir: str) -> Optional[CodingGoalSpec]:
    """Rebuild implementations from existing pytest assertions (test-driven repair)."""
    cases: Dict[str, List[tuple]] = {}
    for name in os.listdir(workspace_dir):
        if not (name.startswith("test_") and name.endswith(".py")):
            continue
        text = open(os.path.join(workspace_dir, name), encoding="utf-8").read()
        for match in _ASSERT_RE.finditer(text):
            func = match.group(1)
            try:
                args = ast.literal_eval(f"({match.group(2)})")
                if not isinstance(args, tuple):
                    args = (args,)
                expected = ast.literal_eval(match.group(3).strip())
            except (ValueError, SyntaxError):
                continue
            cases.setdefault(func, []).append((args, expected))
    if not cases:
        return None
    functions: List[FunctionSpec] = []
    for func, rows in cases.items():
        inferred = None
        for args, expected in rows:
            body = _infer_body(args, expected)
            if body is None:
                inferred = None
                break
            if inferred and inferred != body:
                inferred = None
                break
            inferred = body
        if inferred is None:
            continue
        argspec, body = inferred
        functions.append(FunctionSpec(name=func, args=argspec, body=body, cases=rows))
    if not functions:
        return None
    module_name = "module.py"
    for name in os.listdir(workspace_dir):
        if name.endswith(".py") and not name.startswith("test_"):
            text = open(os.path.join(workspace_dir, name), encoding="utf-8").read()
            if any(f"def {fn.name}(" in text for fn in functions):
                module_name = name
                break
    return CodingGoalSpec(functions=functions, module_name=module_name, test_name="test_module.py")


def _format_arg(value: object) -> str:
    return repr(value)


def _call_args(spec: FunctionSpec, inputs: tuple) -> str:
    return ", ".join(_format_arg(item) for item in inputs)


def generate_module_source(spec: CodingGoalSpec) -> str:
    lines = ['"""Generated workspace module implementing the requested functions."""', ""]
    for fn in spec.functions:
        lines.append(f"def {fn.name}({fn.args}):")
        lines.append(f"    {fn.body}")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def generate_test_source(spec: CodingGoalSpec) -> str:
    names = ", ".join(fn.name for fn in spec.functions)
    lines = [f"from {spec.module_name[:-3]} import {names}", ""]
    for fn in spec.functions:
        for index, (inputs, expected) in enumerate(fn.cases, start=1):
            lines.append(f"def test_{fn.name}_{index}():")
            lines.append(f"    assert {fn.name}({_call_args(fn, inputs)}) == {_format_arg(expected)}")
            lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def generate_workspace_files(spec: CodingGoalSpec) -> Dict[str, str]:
    return {
        spec.module_name: generate_module_source(spec),
        spec.test_name: generate_test_source(spec),
    }
