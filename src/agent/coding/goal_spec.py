"""Parse coding goals into a structured spec without prompt-specific special cases."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import List, Optional


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
    project: bool = False


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


def _spec_for_name(name: str) -> Optional[FunctionSpec]:
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
        "larger": FunctionSpec("larger", "a, b", "return max(a, b)", [((3, 1), 3), ((8, 2), 8)]),
        "smaller": FunctionSpec("smaller", "a, b", "return min(a, b)", [((3, 1), 1), ((8, 2), 2)]),
        "abs_value": FunctionSpec("abs_value", "value", "return abs(value)", [((-3,), 3), ((4,), 4)]),
        "abs": FunctionSpec("abs_value", "value", "return abs(value)", [((-3,), 3), ((4,), 4)]),
        "square": FunctionSpec("square", "value", "return value * value", [((3,), 9), ((4,), 16)]),
        "double": FunctionSpec("double", "value", "return value * 2", [((3,), 6), ((4,), 8)]),
        "negate": FunctionSpec("negate", "value", "return -value", [((3,), -3), ((-2,), 2)]),
        "clamp": FunctionSpec("clamp", "value, lo, hi", "return max(lo, min(hi, value))", [((5, 0, 10), 5), ((-1, 0, 10), 0)]),
        "celsius_to_fahrenheit": FunctionSpec(
            "celsius_to_fahrenheit",
            "celsius",
            "return celsius * 9 / 5 + 32",
            [((0,), 32.0), ((100,), 212.0)],
        ),
        "fahrenheit_to_celsius": FunctionSpec(
            "fahrenheit_to_celsius",
            "fahrenheit",
            "return (fahrenheit - 32) * 5 / 9",
            [((32,), 0.0), ((212,), 100.0)],
        ),
        "km_to_miles": FunctionSpec(
            "km_to_miles",
            "kilometers",
            "return kilometers * 0.621371",
            [((1,), 0.621371)],
        ),
        "miles_to_km": FunctionSpec(
            "miles_to_km",
            "miles",
            "return miles / 0.621371",
            [((1,), 1.6093444978927313)],
        ),
    }
    if canonical in catalog:
        spec = catalog[canonical]
        return FunctionSpec(name=name if name in catalog else canonical, args=spec.args, body=spec.body, cases=spec.cases)
    return None


def is_identity_stub(spec: FunctionSpec) -> bool:
    return spec.body.strip() == "return value" and spec.args.strip() == "value"


def _is_generic_module_request(goal: str) -> bool:
    lower = goal.lower()
    if infer_conversions(goal) or infer_comparisons(goal):
        return False
    if re.search(r"\b(program|project|package|convert|greeting)\b", lower):
        return False
    return bool(re.search(r"\b(python module|create python|write python)\b", lower))


def infer_conversions(goal: str) -> List[FunctionSpec]:
    """Infer unit-conversion functions from the requested outcome."""
    lower = goal.lower()
    found: List[FunctionSpec] = []
    pairs = (
        (("celsius", "centigrade"), ("fahrenheit",), "celsius_to_fahrenheit"),
        (("fahrenheit",), ("celsius", "centigrade"), "fahrenheit_to_celsius"),
        (("kilometer", "kilometre", "km"), ("mile",), "km_to_miles"),
        (("mile",), ("kilometer", "kilometre", "km"), "miles_to_km"),
    )

    def _first_index(tokens: tuple) -> int | None:
        hits = [lower.find(token) for token in tokens if token in lower]
        return min(hits) if hits else None

    for sources, targets, name in pairs:
        source_at = _first_index(sources)
        target_at = _first_index(targets)
        if source_at is None or target_at is None or source_at >= target_at:
            continue
        spec = _spec_for_name(name)
        if spec is None:
            continue
        if spec.name not in {item.name for item in found}:
            found.append(spec)
    return found


def infer_comparisons(goal: str) -> List[FunctionSpec]:
    """Infer comparison helpers when the goal describes selecting among values."""
    lower = goal.lower()
    found: List[FunctionSpec] = []
    if re.search(r"\b(larger|greater|biggest|highest) of\b", lower) or re.search(
        r"\blarger of two\b", lower
    ):
        spec = _spec_for_name("larger")
        if spec is not None:
            found.append(spec)
    if re.search(r"\b(smaller|lesser|lowest|smallest) of\b", lower):
        spec = _spec_for_name("smaller")
        if spec is not None:
            found.append(spec)
    return found


def parse_coding_goal(goal: str) -> CodingGoalSpec:
    functions: List[FunctionSpec] = []
    seen = set()
    unknown: List[str] = []
    for spec in infer_conversions(goal) + infer_comparisons(goal):
        if spec.name not in seen:
            functions.append(spec)
            seen.add(spec.name)
    for name in extract_function_names(goal):
        if name in seen:
            continue
        spec = _spec_for_name(name)
        if spec is None:
            unknown.append(name)
            continue
        functions.append(spec)
        seen.add(name)
    # Named functions we cannot implement must not become identity stubs
    # that generate their own passing tests.
    if unknown:
        return CodingGoalSpec(functions=[], project=False)
    if not functions and _is_generic_module_request(goal):
        fallback = _spec_for_name("add")
        if fallback is not None:
            functions = [fallback]
    project = bool(re.search(r"\b(project|package|multi-file|multiple files)\b", goal, flags=re.IGNORECASE))
    return CodingGoalSpec(functions=functions, project=project)
