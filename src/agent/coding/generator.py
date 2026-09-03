"""Generate Python modules and tests from a parsed coding goal."""

from __future__ import annotations

from typing import Dict

from agent.coding.goal_spec import CodingGoalSpec, FunctionSpec


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
