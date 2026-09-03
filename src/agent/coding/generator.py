"""Generate Python modules and tests from a parsed coding goal."""

from __future__ import annotations

import ast
import os
import re
from typing import Any, Dict, List, Optional, Tuple

from agent.coding.goal_spec import CodingGoalSpec, FunctionSpec

_ASSERT_RE = re.compile(r"assert\s+([A-Za-z_][A-Za-z0-9_]*)\(([^)]*)\)\s*==\s*(.+)")


def _fact(n: object) -> object:
    if not isinstance(n, int) or n < 0 or n > 12:
        raise ValueError("factorial domain")
    result = 1
    for item in range(2, n + 1):
        result *= item
    return result


def _unary_templates() -> List[Tuple[str, str, Any]]:
    return [
        ("value", "return value", lambda n: n),
        ("value", "return -value", lambda n: -n),
        ("value", "return abs(value)", lambda n: abs(n)),
        ("value", "return value + 1", lambda n: n + 1),
        ("value", "return value - 1", lambda n: n - 1),
        ("value", "return value * 2", lambda n: n * 2),
        ("value", "return value * 3", lambda n: n * 3),
        ("value", "return value * 4", lambda n: n * 4),
        ("value", "return value * value", lambda n: n * n),
        ("value", "return value * value * value", lambda n: n * n * n),
        ("value", "return value ** 2", lambda n: n ** 2),
        ("value", "return value ** 3", lambda n: n ** 3),
        ("celsius", "return celsius * 9 / 5 + 32", lambda n: n * 9 / 5 + 32),
        ("fahrenheit", "return (fahrenheit - 32) * 5 / 9", lambda n: (n - 32) * 5 / 9),
        ("n", "return 1 if n <= 1 else n * factorial(n - 1)", _fact),
    ]


def _binary_templates() -> List[Tuple[str, str, Any]]:
    return [
        ("a, b", "return a + b", lambda a, b: a + b),
        ("a, b", "return a - b", lambda a, b: a - b),
        ("a, b", "return a * b", lambda a, b: a * b),
        ("a, b", "return a / b", lambda a, b: a / b),
        ("a, b", "return min(a, b)", lambda a, b: min(a, b)),
        ("a, b", "return max(a, b)", lambda a, b: max(a, b)),
        ("a, b", "return a ** b", lambda a, b: a ** b),
    ]


def _matches_all(fn: Any, rows: List[tuple]) -> bool:
    for args, expected in rows:
        try:
            got = fn(*args)
        except Exception:
            return False
        if got != expected:
            return False
    return True


def _infer_body(args: tuple, expected: object) -> Optional[Tuple[str, str]]:
    inferred = _infer_body_from_cases([(args, expected)])
    return inferred


def _infer_body_from_cases(rows: List[tuple]) -> Optional[Tuple[str, str]]:
    if not rows:
        return None
    arity = len(rows[0][0])
    if any(len(args) != arity for args, _expected in rows):
        return None
    templates: List[Tuple[str, str, Any]]
    if arity == 1:
        templates = _unary_templates()
    elif arity == 2:
        templates = _binary_templates()
    elif arity == 3:
        templates = [
            ("value, lo, hi", "return max(lo, min(hi, value))", lambda value, lo, hi: max(lo, min(hi, value))),
        ]
    else:
        return None
    matches = [(argspec, body) for argspec, body, fn in templates if _matches_all(fn, rows)]
    if not matches:
        return None
    matches.sort(key=lambda item: len(item[1]))
    return matches[0]


def iter_python_files(workspace_dir: str) -> List[str]:
    found: List[str] = []
    for dirpath, dirnames, filenames in os.walk(workspace_dir):
        dirnames[:] = [name for name in dirnames if name not in {".git", "__pycache__", ".venv", "node_modules"}]
        for filename in filenames:
            if filename.endswith(".py"):
                found.append(os.path.join(dirpath, filename))
    return found


def _is_test_file(path: str) -> bool:
    name = os.path.basename(path)
    return name.startswith("test_") or name.endswith("_test.py")


def infer_spec_from_workspace(workspace_dir: str) -> Optional[CodingGoalSpec]:
    """Rebuild implementations from existing pytest assertions (test-driven repair)."""
    cases: Dict[str, List[tuple]] = {}
    test_name = "test_module.py"
    for path in iter_python_files(workspace_dir):
        if not _is_test_file(path):
            continue
        text = open(path, encoding="utf-8").read()
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
            test_name = os.path.relpath(path, workspace_dir).replace("\\", "/")
    if not cases:
        return None
    functions: List[FunctionSpec] = []
    for func, rows in cases.items():
        inferred = _infer_body_from_cases(rows)
        if inferred is None:
            continue
        argspec, body = inferred
        functions.append(FunctionSpec(name=func, args=argspec, body=body, cases=rows))
    if not functions:
        return None
    module_name = "module.py"
    for path in iter_python_files(workspace_dir):
        if _is_test_file(path):
            continue
        text = open(path, encoding="utf-8").read()
        if any(re.search(rf"def {re.escape(fn.name)}\s*\(", text) for fn in functions):
            module_name = os.path.relpath(path, workspace_dir).replace("\\", "/")
            break
    return CodingGoalSpec(functions=functions, module_name=module_name, test_name=test_name)


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


def _rewrite_body_for_args(argspec: str, body: str) -> str:
    names = [part.strip() for part in argspec.split(",") if part.strip()]
    if len(names) == 1 and names[0] != "value" and "value" in body:
        return re.sub(r"\bvalue\b", names[0], body)
    return body


def _replace_function_source(source: str, spec: FunctionSpec) -> Optional[str]:
    pattern = re.compile(
        rf"(^def {re.escape(spec.name)}\s*\()([^)]*)(\):)(.*?)(?=^def |\Z)",
        flags=re.MULTILINE | re.DOTALL,
    )
    match = pattern.search(source)
    if not match:
        return None
    existing_args = match.group(2).strip() or spec.args
    body = _rewrite_body_for_args(existing_args, spec.body)
    replacement = f"def {spec.name}({existing_args}):\n    {body}\n\n"
    return source[: match.start()] + replacement + source[match.end() :]


def apply_function_patches(workspace_dir: str, spec: CodingGoalSpec) -> Dict[str, str]:
    """Patch existing function bodies in-place; create a module only when missing."""
    result: Dict[str, str] = {}
    remaining = list(spec.functions)
    for path in iter_python_files(workspace_dir):
        if _is_test_file(path):
            continue
        text = open(path, encoding="utf-8").read()
        updated = text
        kept: List[FunctionSpec] = []
        changed = False
        for fn in remaining:
            patched = _replace_function_source(updated, fn)
            if patched is None:
                kept.append(fn)
                continue
            updated = patched
            changed = True
        remaining = kept
        if changed:
            rel = os.path.relpath(path, workspace_dir).replace("\\", "/")
            result[rel] = updated
    if remaining:
        fallback = spec.module_name or "module.py"
        abs_fallback = os.path.join(workspace_dir, fallback)
        base = result.get(fallback)
        if base is None and os.path.isfile(abs_fallback):
            base = open(abs_fallback, encoding="utf-8").read()
        if base is None:
            result[fallback] = generate_module_source(CodingGoalSpec(functions=remaining, module_name=fallback))
        else:
            extra = generate_module_source(CodingGoalSpec(functions=remaining, module_name=fallback))
            result[fallback] = base.rstrip() + "\n\n" + extra
    return result


def _assignment_value_for_label(goal: str, label: str) -> str:
    escaped = re.escape(label)
    patterns = (
        rf"{escaped}\s+to\s+[\"']([^\"']+)[\"']",
        rf"{escaped}\s+to\s+(.+?)(?=\s+and\s+the\s+[A-Za-z_]|\s+and\s+[A-Za-z_][A-Za-z0-9_]*\s+to\b|$)",
        rf"{escaped}\s+should say\s+[\"']([^\"']+)[\"']",
        rf"{escaped}\s+should say\s+(.+?)(?:\.(?:\s|$)|$)",
        rf"{escaped}\s+now reads\s+[\"']([^\"']+)[\"']",
    )
    for pattern in patterns:
        match = re.search(pattern, goal, flags=re.IGNORECASE | re.DOTALL)
        if match:
            text = match.group(1).strip()
            text = re.split(r"\b(?:verify|then|report)\b", text, maxsplit=1, flags=re.IGNORECASE)[0]
            return text.strip(" \t\r\n.,;:")
    return ""


def patch_identifier_assignments(workspace_dir: str, goal: str) -> Optional[Dict[str, str]]:
    """Update NAME = '...' assignments whose identifiers are mentioned in the goal."""
    assign_re = re.compile(
        r'(?P<pre>^\s*(?P<name>[A-Za-z_][A-Za-z0-9_]*)\s*=\s*)(?P<q>["\'])(?P<val>.*?)(?P=q)',
        flags=re.MULTILINE,
    )
    result: Dict[str, str] = {}
    for path in iter_python_files(workspace_dir):
        if _is_test_file(path):
            continue
        text = open(path, encoding="utf-8").read()

        def _sub(match: re.Match[str]) -> str:
            name = match.group("name")
            label = name.lower().strip("_").replace("_", " ")
            if label not in goal.lower() and name.lower() not in goal.lower():
                return match.group(0)
            value = _assignment_value_for_label(goal, label) or _assignment_value_for_label(goal, name.lower())
            if not value:
                return match.group(0)
            return f"{match.group('pre')}{match.group('q')}{value}{match.group('q')}"

        new_text = assign_re.sub(_sub, text)
        if new_text != text:
            rel = os.path.relpath(path, workspace_dir).replace("\\", "/")
            result[rel] = new_text
    return result or None
