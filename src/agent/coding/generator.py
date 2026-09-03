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
    if len(args) == 1:
        value = args[0]
        try:
            if value * 9 / 5 + 32 == expected:
                return "celsius", "return celsius * 9 / 5 + 32"
            if (value - 32) * 5 / 9 == expected:
                return "fahrenheit", "return (fahrenheit - 32) * 5 / 9"
        except Exception:
            pass
        if value == expected:
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
    if spec.project:
        return generate_project_files(spec)
    return {
        spec.module_name: generate_module_source(spec),
        spec.test_name: generate_test_source(spec),
    }


def generate_project_files(spec: CodingGoalSpec) -> Dict[str, str]:
    """Emit a small multi-file package plus tests for a project-style coding goal."""
    names = ", ".join(fn.name for fn in spec.functions)
    tests = generate_test_source(spec).replace(
        f"from {spec.module_name[:-3]} import {names}",
        f"from pkg.core import {names}",
    )
    return {
        "pkg/__init__.py": "",
        "pkg/core.py": generate_module_source(spec),
        "tests/test_core.py": tests,
        spec.module_name: generate_module_source(spec),
        spec.test_name: generate_test_source(spec),
    }


def extract_replacement_text(goal: str) -> str:
    patterns = (
        r"should say\s+[\"'](.+?)[\"']",
        r"should say\s+(.+?)(?:\.(?:\s|$)|$)",
        r"to say\s+[\"'](.+?)[\"']",
        r"to say\s+(.+?)(?:\.(?:\s|$)|$)",
        r"now reads\s+[\"'](.+?)[\"']",
        r"now reads\s+(.+?)(?:\.(?:\s|$)|$)",
    )
    for pattern in patterns:
        match = re.search(pattern, goal, flags=re.IGNORECASE | re.DOTALL)
        if match:
            text = match.group(1).strip()
            text = re.split(r"\b(?:verify|then|report)\b", text, maxsplit=1, flags=re.IGNORECASE)[0]
            return text.strip(" \t\r\n.,;:")
    return ""


def patch_existing_source_files(workspace_dir: str, goal: str) -> Optional[Dict[str, str]]:
    """Patch greeting/title/message strings in existing Python files."""
    replacement = extract_replacement_text(goal)
    if not replacement:
        return None
    lower = goal.lower()
    if not re.search(r"\b(greeting|title|message|hello|script)\b", lower):
        return None
    assign_re = re.compile(
        r'(?P<pre>^\s*(?:GREETING|greeting|TITLE|title|MESSAGE|message)\s*=\s*)(?P<q>["\'])(?P<val>.*?)(?P=q)',
        flags=re.MULTILINE,
    )
    result: Dict[str, str] = {}
    for name in os.listdir(workspace_dir):
        if not name.endswith(".py") or name.startswith("test_"):
            continue
        path = os.path.join(workspace_dir, name)
        if not os.path.isfile(path):
            continue
        text = open(path, encoding="utf-8").read()
        new_text, count = assign_re.subn(
            lambda match: f"{match.group('pre')}{match.group('q')}{replacement}{match.group('q')}",
            text,
            count=1,
        )
        if count == 0 and re.search(r"\b(greeting|GREETING)\b", text):
            new_text, count = re.subn(
                r'(["\'])([^"\']+)\1',
                lambda match: f"{match.group(1)}{replacement}{match.group(1)}",
                text,
                count=1,
            )
        if count:
            result[name] = new_text
    return result or None
