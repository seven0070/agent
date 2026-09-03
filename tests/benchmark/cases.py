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


def not_mocked() -> CheckFn:
    def _check(ctx: Dict[str, Any]) -> Tuple[bool, str]:
        blob = str(ctx.get("output") or "")
        if "Mocked AgentScope response content" in blob:
            return False, "silent mock fallback"
        return True, "not mocked"

    return _check


def used_intent(kind: str) -> CheckFn:
    def _check(ctx: Dict[str, Any]) -> Tuple[bool, str]:
        plan = ctx.get("plan")
        metadata = getattr(plan, "metadata", None) or {}
        got = metadata.get("intent")
        if got == kind:
            return True, f"intent {kind}"
        return False, f"intent {got!r} != {kind!r}"

    return _check


def failed_honestly() -> CheckFn:
    def _check(ctx: Dict[str, Any]) -> Tuple[bool, str]:
        blob = (str(ctx.get("output") or "") + " " + str(ctx.get("error") or "")).lower()
        if "mocked agentscope response content" in blob:
            return False, "mock presented as success"
        if ctx.get("plan_status") == "failed" and (
            "unavailable" in blob
            or "no real operation" in blob
            or "not implemented" in blob
            or "could not determine the requested program" in blob
            or "no files were changed" in blob
        ):
            return True, "honest failure"
        return False, f"expected honest failure, status={ctx.get('plan_status')} output={ctx.get('output')!r}"

    return _check


def python_any_call(func: str, args: tuple, expected: Any) -> CheckFn:
    def _check(ctx: Dict[str, Any]) -> Tuple[bool, str]:
        import importlib.util
        from pathlib import Path

        matches = [
            path
            for path in Path(ctx["workspace"]).rglob("*.py")
            if path.name != "test_module.py" and not path.name.startswith("test_")
        ]
        if not matches:
            return False, "no python module found"
        last_error = "function not found"
        for path in matches:
            spec = importlib.util.spec_from_file_location("bench_mod", path)
            if spec is None or spec.loader is None:
                continue
            mod = importlib.util.module_from_spec(spec)
            try:
                spec.loader.exec_module(mod)
            except Exception as exc:  # noqa: BLE001
                last_error = str(exc)
                continue
            fn = getattr(mod, func, None)
            if fn is None:
                continue
            got = fn(*args)
            if got == expected:
                return True, f"{path.name}:{func}{args} == {expected!r}"
            last_error = f"{func}{args} == {got!r}, expected {expected!r}"
        return False, last_error

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


def build_open_ended_cases() -> List[BenchmarkCase]:
    """Natural-language tasks without implementation cue phrases."""
    return [
        BenchmarkCase(
            case_id="oe-note-desktop",
            category="write-text",
            prompt="Put a note on my desktop saying I need to call John.",
            checks=[
                used_intent("write_text"),
                used_tool("write_file-v1"),
                file_contains("note.txt", "I need to call John"),
                not_mocked(),
                plan_completed(),
            ],
        ),
        BenchmarkCase(
            case_id="oe-celsius-program",
            category="build-program",
            prompt="Make a small program that converts Celsius to Fahrenheit.",
            checks=[
                used_intent("build_program"),
                used_tool("coding-engine-v1"),
                python_any_call("celsius_to_fahrenheit", (0,), 32.0),
                python_any_call("celsius_to_fahrenheit", (100,), 212.0),
                not_mocked(),
            ],
        ),
        BenchmarkCase(
            case_id="oe-greeting-change",
            category="change-program",
            prompt="The greeting in the existing Python script should say Good evening.",
            setup_files=[
                (
                    "greet.py",
                    'GREETING = "Hello"\n\ndef greet():\n    return GREETING\n',
                )
            ],
            checks=[
                used_intent("change_program"),
                used_tool("coding-engine-v1"),
                file_contains("greet.py", "Good evening"),
                not_mocked(),
            ],
        ),
        BenchmarkCase(
            case_id="oe-json-highest",
            category="query-data",
            prompt="Look at this JSON and tell me which user has the highest score.",
            setup_files=[
                (
                    "players.json",
                    '[{"user": "sam", "score": 10}, {"user": "ada", "score": 42}, {"user": "lee", "score": 7}]',
                )
            ],
            checks=[
                used_intent("query_data"),
                used_tool("inspect_data-v1"),
                output_contains("ada", "42"),
                not_mocked(),
                plan_completed(),
            ],
        ),
        BenchmarkCase(
            case_id="oe-reminder",
            category="write-text",
            prompt="Leave a reminder that the meeting moved to Thursday.",
            checks=[
                used_intent("write_text"),
                used_tool("write_file-v1"),
                file_contains("reminder.txt", "meeting moved to Thursday"),
                not_mocked(),
            ],
        ),
        BenchmarkCase(
            case_id="oe-spoken-math",
            category="compute",
            prompt="What is 18 times 7?",
            checks=[
                used_intent("compute"),
                used_tool("calculator-v1"),
                output_contains("126"),
                not_mocked(),
                plan_completed(),
            ],
        ),
        BenchmarkCase(
            case_id="oe-jot",
            category="write-text",
            prompt="Jot down that the package arrives tomorrow.",
            checks=[
                used_intent("write_text"),
                used_tool("write_file-v1"),
                file_contains("note.txt", "package arrives tomorrow"),
                not_mocked(),
            ],
        ),
        BenchmarkCase(
            case_id="oe-project-add",
            category="build-program",
            prompt="Make a tiny project that can add two numbers and prove it with tests.",
            checks=[
                used_intent("build_program"),
                used_tool("coding-engine-v1"),
                file_contains("pkg/core.py", "def add("),
                python_any_call("add", (2, 3), 5),
                not_mocked(),
            ],
        ),
        BenchmarkCase(
            case_id="oe-repair-failing",
            category="change-program",
            prompt="The existing tests are failing — repair the implementation.",
            setup_files=[
                ("module.py", "def add(a, b):\n    return a * b\n"),
                ("test_module.py", "from module import add\n\ndef test_add():\n    assert add(2, 3) == 5\n"),
            ],
            checks=[
                used_intent("change_program"),
                used_tool("coding-engine-v1"),
                python_call("module.py", "add", (2, 3), 5),
                not_mocked(),
            ],
        ),
        BenchmarkCase(
            case_id="oe-division",
            category="compute",
            prompt="How much is 144 divided by 12?",
            checks=[
                used_intent("compute"),
                used_tool("calculator-v1"),
                output_contains("12"),
                not_mocked(),
            ],
        ),
        BenchmarkCase(
            case_id="oe-show-json",
            category="read-text",
            prompt="What's inside roster.json?",
            setup_files=[("roster.json", '{"team": "okapi", "n": 3}')],
            checks=[
                used_intent("read_text"),
                used_tool("read_file-v1"),
                output_contains("okapi"),
                not_mocked(),
            ],
        ),
        BenchmarkCase(
            case_id="oe-larger",
            category="build-program",
            prompt="A program that reports the larger of two numbers, with tests.",
            checks=[
                used_intent("build_program"),
                used_tool("coding-engine-v1"),
                python_any_call("larger", (3, 1), 3),
                not_mocked(),
            ],
        ),
        BenchmarkCase(
            case_id="oe-email-unavailable",
            category="failure-reporting",
            prompt="Email this report to the whole team.",
            checks=[
                used_intent("unsupported"),
                failed_honestly(),
                not_mocked(),
            ],
        ),
        BenchmarkCase(
            case_id="oe-unknown-functions",
            category="failure-reporting",
            prompt="A program with scale and offset helpers, with tests.",
            checks=[
                used_intent("build_program"),
                used_tool("coding-engine-v1"),
                failed_honestly(),
                not_mocked(),
                file_missing("module.py"),
            ],
        ),
        BenchmarkCase(
            case_id="oe-json-average",
            category="query-data",
            prompt="What is the average score in this JSON?",
            setup_files=[
                (
                    "totals.json",
                    '[{"user": "sam", "score": 10}, {"user": "ada", "score": 20}, {"user": "lee", "score": 30}]',
                )
            ],
            checks=[
                used_intent("query_data"),
                used_tool("inspect_data-v1"),
                output_contains("20"),
                not_mocked(),
                plan_completed(),
            ],
        ),
        BenchmarkCase(
            case_id="oe-delete-unavailable",
            category="failure-reporting",
            prompt="Delete the note from my desktop.",
            checks=[
                used_intent("unsupported"),
                failed_honestly(),
                not_mocked(),
            ],
        ),
    ]
