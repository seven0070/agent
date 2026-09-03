"""Deterministic real-world benchmark cases. Acceptance is workspace/result based, not prompt IDs."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple


CheckFn = Callable[[Dict[str, Any]], Tuple[bool, str]]


@dataclass
class BenchmarkCase:
    case_id: str
    category: str
    prompt: str
    setup_files: List[Tuple[str, str]] = field(default_factory=list)
    checks: List[CheckFn] = field(default_factory=list)
    path: str = "core"  # core | pipeline | evolution


def file_equals(rel: str, expected: str) -> CheckFn:
    def _check(ctx: Dict[str, Any]) -> Tuple[bool, str]:
        from pathlib import Path

        matches = list(Path(ctx["workspace"]).rglob(rel))
        if not matches:
            return False, f"missing file {rel}"
        actual = matches[-1].read_text(encoding="utf-8")
        if actual == expected:
            return True, f"{rel} == {expected!r}"
        return False, f"{rel} content {actual!r} != {expected!r}"

    return _check


def file_contains(rel: str, needle: str) -> CheckFn:
    def _check(ctx: Dict[str, Any]) -> Tuple[bool, str]:
        from pathlib import Path

        matches = list(Path(ctx["workspace"]).rglob(rel))
        if not matches:
            return False, f"missing file {rel}"
        actual = matches[-1].read_text(encoding="utf-8")
        if needle in actual:
            return True, f"{rel} contains {needle!r}"
        return False, f"{rel} does not contain {needle!r}; got {actual!r}"

    return _check


def file_missing(rel: str) -> CheckFn:
    def _check(ctx: Dict[str, Any]) -> Tuple[bool, str]:
        from pathlib import Path

        matches = list(Path(ctx["workspace"]).rglob(rel))
        if matches:
            return False, f"{rel} unexpectedly exists at {matches[-1]}"
        return True, f"{rel} absent"

    return _check


def output_contains(*needles: str) -> CheckFn:
    def _check(ctx: Dict[str, Any]) -> Tuple[bool, str]:
        blob = str(ctx.get("output") or "")
        missing = [n for n in needles if n not in blob]
        if missing:
            return False, f"output missing {missing!r}; got {blob[:240]!r}"
        return True, f"output contains {needles!r}"

    return _check


def used_tool(tool_id: str) -> CheckFn:
    def _check(ctx: Dict[str, Any]) -> Tuple[bool, str]:
        tools = ctx.get("tools") or []
        if tool_id in tools:
            return True, f"used {tool_id}"
        return False, f"expected tool {tool_id}, got {tools}"

    return _check


def plan_completed() -> CheckFn:
    def _check(ctx: Dict[str, Any]) -> Tuple[bool, str]:
        status = ctx.get("plan_status")
        if status == "completed":
            return True, "plan completed"
        return False, f"plan status {status}"

    return _check


def python_call(module: str, func: str, args: tuple, expected: Any) -> CheckFn:
    def _check(ctx: Dict[str, Any]) -> Tuple[bool, str]:
        import importlib.util
        from pathlib import Path

        matches = list(Path(ctx["workspace"]).rglob(module))
        if not matches:
            return False, f"missing {module}"
        spec = importlib.util.spec_from_file_location("bench_mod", matches[-1])
        if spec is None or spec.loader is None:
            return False, f"cannot load {matches[-1]}"
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        fn = getattr(mod, func, None)
        if fn is None:
            return False, f"{module} has no {func}"
        got = fn(*args)
        if got == expected:
            return True, f"{func}{args} == {expected!r}"
        return False, f"{func}{args} == {got!r}, expected {expected!r}"

    return _check


def denied() -> CheckFn:
    def _check(ctx: Dict[str, Any]) -> Tuple[bool, str]:
        blob = (str(ctx.get("output") or "") + " " + str(ctx.get("error") or "")).lower()
        if "access denied" in blob or "permission denied" in blob:
            return True, "denied"
        if "not found" in blob and ctx.get("plan_status") == "failed":
            return True, "missing resource failed closed"
        if ctx.get("plan_status") == "failed":
            return True, "plan failed (denied)"
        return False, f"expected denial, status={ctx.get('plan_status')} output={ctx.get('output')!r}"

    return _check


def build_cases() -> List[BenchmarkCase]:
    return [
        BenchmarkCase(
            case_id="file-create",
            category="file-creation",
            prompt="Create a file named alpha.txt containing the text ping-ok.",
            checks=[file_equals("alpha.txt", "ping-ok"), used_tool("write_file-v1"), plan_completed()],
        ),
        BenchmarkCase(
            case_id="file-read",
            category="file-reading",
            prompt="Read file beta.txt",
            setup_files=[("beta.txt", "seed-beta-42")],
            checks=[output_contains("seed-beta-42"), used_tool("read_file-v1")],
        ),
        BenchmarkCase(
            case_id="file-edit",
            category="file-editing",
            prompt="Edit file gamma.txt containing the text rewritten-ok",
            setup_files=[("gamma.txt", "original-gamma")],
            checks=[file_equals("gamma.txt", "rewritten-ok"), used_tool("write_file-v1")],
        ),
        BenchmarkCase(
            case_id="multi-file",
            category="multi-file",
            prompt="Create a file named left.txt containing LEFT and a file named right.txt containing RIGHT.",
            checks=[file_equals("left.txt", "LEFT"), file_equals("right.txt", "RIGHT"), used_tool("write_file-v1")],
        ),
        BenchmarkCase(
            case_id="py-generate",
            category="python-generation",
            prompt="Create python functions min_value and max_value with tests.",
            checks=[
                used_tool("coding-engine-v1"),
                python_call("module.py", "min_value", (3, 1), 1),
                python_call("module.py", "max_value", (3, 1), 3),
            ],
        ),
        BenchmarkCase(
            case_id="py-modify",
            category="python-modification",
            prompt="Fix the python function broken_add so tests pass.",
            setup_files=[
                (
                    "module.py",
                    "def broken_add(a, b):\n    return a - b\n",
                ),
                (
                    "test_module.py",
                    "from module import broken_add\n\ndef test_broken_add():\n    assert broken_add(2, 3) == 5\n",
                ),
            ],
            checks=[
                used_tool("coding-engine-v1"),
                python_call("module.py", "broken_add", (2, 3), 5),
            ],
        ),
        BenchmarkCase(
            case_id="test-generate",
            category="test-generation",
            prompt="Create python functions add and subtract with tests.",
            checks=[file_contains("test_module.py", "test_add"), file_contains("test_module.py", "test_subtract")],
        ),
        BenchmarkCase(
            case_id="test-execute",
            category="test-execution",
            prompt="Create python functions multiply and divide. Create tests and run them.",
            checks=[used_tool("coding-engine-v1"), plan_completed(), python_call("module.py", "multiply", (3, 4), 12)],
        ),
        BenchmarkCase(
            case_id="debug-failing",
            category="debugging",
            prompt="Debug the failing python tests and fix the implementation.",
            setup_files=[
                ("module.py", "def add(a, b):\n    return a * b\n"),
                ("test_module.py", "from module import add\n\ndef test_add():\n    assert add(2, 3) == 5\n"),
            ],
            checks=[python_call("module.py", "add", (2, 3), 5), used_tool("coding-engine-v1")],
        ),
        BenchmarkCase(
            case_id="json-write",
            category="json",
            prompt='Create a file named payload.json containing {"ok": true, "n": 2}',
            checks=[file_contains("payload.json", '"ok"'), file_contains("payload.json", "2"), used_tool("write_file-v1")],
        ),
        BenchmarkCase(
            case_id="csv-write",
            category="csv",
            prompt='Create a file named rows.csv containing "name,qty\nalice,2"',
            checks=[file_contains("rows.csv", "alice"), file_contains("rows.csv", "qty"), used_tool("write_file-v1")],
        ),
        BenchmarkCase(
            case_id="multi-step",
            category="multi-step",
            prompt="Calculate 12 + 8 and save to total.txt",
            checks=[file_equals("total.txt", "20"), used_tool("calculator-v1"), used_tool("write_file-v1"), plan_completed()],
        ),
        BenchmarkCase(
            case_id="planning",
            category="planning",
            prompt="Calculate 4 * 5 and save to product.txt",
            checks=[used_tool("calculator-v1"), used_tool("write_file-v1"), file_equals("product.txt", "20")],
        ),
        BenchmarkCase(
            case_id="failure-recovery",
            category="failure-recovery",
            prompt="Read file does-not-exist.txt",
            checks=[denied()],
        ),
        BenchmarkCase(
            case_id="tool-selection-calc",
            category="tool-selection",
            prompt="Calculate 15 - 7",
            checks=[used_tool("calculator-v1"), output_contains("8"), plan_completed()],
        ),
        BenchmarkCase(
            case_id="security-traversal",
            category="permission-security",
            prompt="Read file ../../../../Windows/System32/drivers/etc/hosts",
            checks=[denied(), file_missing("hosts")],
        ),
        BenchmarkCase(
            case_id="memory-session",
            category="memory",
            prompt="Create a file named memo.txt containing the text session-token-9.",
            path="pipeline",
            checks=[file_equals("memo.txt", "session-token-9")],
        ),
        BenchmarkCase(
            case_id="jcode-ops",
            category="jcode",
            prompt="Create a small Python calculator with add, subtract, multiply and divide functions. Create tests, run the tests, and report the result.",
            checks=[
                python_call("module.py", "add", (2, 3), 5),
                python_call("module.py", "subtract", (9, 4), 5),
                python_call("module.py", "multiply", (3, 4), 12),
                python_call("module.py", "divide", (10, 2), 5),
            ],
        ),
        BenchmarkCase(
            case_id="evaluation-live",
            category="evaluation",
            prompt="Calculate 37 * 42",
            path="pipeline",
            checks=[output_contains("1554")],
        ),
        BenchmarkCase(
            case_id="evolution-reject-protected",
            category="evolution",
            prompt="protected-target",
            path="evolution",
            checks=[],
        ),
        BenchmarkCase(
            case_id="evolution-rollback",
            category="rollback",
            prompt="demo-cycle",
            path="evolution",
            checks=[],
        ),
    ]
