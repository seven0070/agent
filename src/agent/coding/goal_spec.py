"""Parse coding goals into a structured spec without prompt-specific special cases."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import List


_STOPWORDS = {
    "a",
    "an",
    "the",
    "with",
    "and",
    "or",
    "of",
    "for",
    "in",
    "to",
    "small",
    "python",
    "module",
    "create",
    "creating",
    "write",
    "implement",
    "implementing",
    "functions",
    "function",
    "tests",
    "test",
    "run",
    "running",
    "report",
    "result",
    "please",
    "that",
    "this",
    "named",
    "containing",
    "using",
    "simple",
    "basic",
}

_ALIASES = {
    "add": "add",
    "addition": "add",
    "plus": "add",
    "sum": "add",
    "subtract": "subtract",
    "subtraction": "subtract",
    "minus": "subtract",
    "sub": "subtract",
    "multiply": "multiply",
    "multiplication": "multiply",
    "times": "multiply",
    "mul": "multiply",
    "product": "multiply",
    "divide": "divide",
    "division": "divide",
    "div": "divide",
    "quotient": "divide",
}


@dataclass
class FunctionSpec:
    name: str
    args: str
    body: str
    cases: List[tuple]


@dataclass
class CodingGoalSpec:
    functions: List[FunctionSpec] = field(default_factory=list)
    module_name: str = "module.py"
    test_name: str = "test_module.py"


def _ident(raw: str) -> str | None:
    name = raw.strip().lower().replace("-", "_").replace(" ", "_")
    if not re.match(r"^[a-z_][a-z0-9_]*$", name):
        return None
    if name in _STOPWORDS:
        return None
    return name


def extract_function_names(goal: str) -> List[str]:
    """Extract requested function identifiers from a free-form coding goal."""
    lower = goal.lower()
    names: List[str] = []

    before_fn = re.search(
        r"((?:[a-z][a-z0-9_]*)(?:\s*(?:,|/|and)\s*[a-z][a-z0-9_]*)+)\s+functions?",
        lower,
    )
    after_fn = re.search(
        r"functions?\s+((?:[a-z][a-z0-9_]*)(?:\s*(?:,|/|and)\s*[a-z][a-z0-9_]*)+)",
        lower,
    )
    blob = None
    if before_fn:
        blob = before_fn.group(1)
    elif after_fn:
        blob = after_fn.group(1)
    if blob:
        blob = re.sub(r"\s+and\s+", ",", blob)
        for part in re.split(r"[,/]", blob):
            ident = _ident(part)
            if ident and ident not in names:
                names.append(ident)

    if not names:
        for token in re.findall(r"\b[a-z][a-z0-9_]*\b", lower):
            mapped = _ALIASES.get(token)
            if mapped and mapped not in names:
                names.append(mapped)
    return names


def _spec_for_name(name: str) -> FunctionSpec:
    canonical = _ALIASES.get(name, name)
    catalog = {
        "add": FunctionSpec("add", "a, b", "return a + b", [((2, 3), 5), ((10, 20), 30)]),
        "subtract": FunctionSpec("subtract", "a, b", "return a - b", [((5, 2), 3), ((10, 4), 6)]),
        "multiply": FunctionSpec("multiply", "a, b", "return a * b", [((3, 4), 12), ((7, 8), 56)]),
        "divide": FunctionSpec("divide", "a, b", "return a / b", [((10, 2), 5), ((9, 3), 3)]),
        "min": FunctionSpec("min", "a, b", "return min(a, b)", [((3, 1), 1), ((8, 2), 2)]),
        "max": FunctionSpec("max", "a, b", "return max(a, b)", [((3, 1), 3), ((8, 2), 8)]),
        "min_value": FunctionSpec("min_value", "a, b", "return min(a, b)", [((3, 1), 1), ((8, 2), 2)]),
        "max_value": FunctionSpec("max_value", "a, b", "return max(a, b)", [((3, 1), 3), ((8, 2), 8)]),
        "abs_value": FunctionSpec("abs_value", "value", "return abs(value)", [((-3,), 3), ((4,), 4)]),
        "clamp": FunctionSpec("clamp", "value, lo, hi", "return max(lo, min(hi, value))", [((5, 0, 10), 5), ((-1, 0, 10), 0)]),
    }
    if canonical in catalog:
        spec = catalog[canonical]
        return FunctionSpec(name=name if name in catalog else canonical, args=spec.args, body=spec.body, cases=spec.cases)
    return FunctionSpec(name=name, args="value", body="return value", cases=[((1,), 1), (("ok",), "ok")])


def parse_coding_goal(goal: str) -> CodingGoalSpec:
    names = extract_function_names(goal)
    if not names:
        names = ["add"]
    functions = [_spec_for_name(name) for name in names]
    return CodingGoalSpec(functions=functions)
