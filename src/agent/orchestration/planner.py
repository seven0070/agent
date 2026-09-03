"""
Planner Interface and Dynamic Plan Decomposer.
"""

import uuid
import re
from typing import Dict, Any, Optional, List
from agent.orchestration.models import Plan, PlanTask, TaskState

_FILENAME_TOKEN = r"[A-Za-z0-9][A-Za-z0-9._-]*\.[A-Za-z0-9]+"

_FILENAME_PATTERNS = (
    rf"(?:named|called)\s+[\"']?({_FILENAME_TOKEN})[\"']?",
    rf"(?:file(?:name)?)\s+[\"']?({_FILENAME_TOKEN})[\"']?",
    rf"(?:save|write|output)\s+(?:it\s+)?(?:to|into)\s+[\"']?({_FILENAME_TOKEN})[\"']?",
    rf"[\"']({_FILENAME_TOKEN})[\"']",
)

_CONTENT_PATTERNS = (
    r"containing(?:\s+the)?(?:\s+text)?\s+[\"'](.+?)[\"']",
    r"containing(?:\s+the)?(?:\s+text)?\s+(.+?)(?:\.(?:\s|$)|$)",
    r"with(?:\s+the)?(?:\s+(?:text|content|contents))\s+[\"'](.+?)[\"']",
    r"with(?:\s+the)?(?:\s+(?:text|content|contents))\s+(.+?)(?:\.(?:\s|$)|$)",
    r"that says\s+[\"'](.+?)[\"']",
    r"that says\s+(.+?)(?:\.(?:\s|$)|$)",
)

_PAIR_PATTERN = re.compile(
    rf"(?:named|called)\s+({_FILENAME_TOKEN})\s+containing(?:\s+the)?(?:\s+text)?\s+(?:[\"'](.+?)[\"']|(.+?))(?=\s+and\s+(?:a\s+)?file\b|\s+and\s+(?:create|write|named)\b|$)",
    flags=re.IGNORECASE | re.DOTALL,
)


def extract_filename(goal: str) -> Optional[str]:
    """Pull a workspace-relative filename out of a natural-language goal."""
    for pattern in _FILENAME_PATTERNS:
        match = re.search(pattern, goal, flags=re.IGNORECASE)
        if not match:
            continue
        name = match.group(1).strip()
        if ".." in name or "/" in name or "\\" in name:
            continue
        return name
    return None


def extract_file_content(goal: str) -> str:
    """Pull literal file contents out of a natural-language goal."""
    for pattern in _CONTENT_PATTERNS:
        match = re.search(pattern, goal, flags=re.IGNORECASE | re.DOTALL)
        if not match:
            continue
        text = match.group(1).strip()
        text = re.split(r"\b(?:verify|then|report|and then)\b", text, maxsplit=1, flags=re.IGNORECASE)[0]
        return text.strip(" \t\r\n.,;:")
    return ""


def extract_file_write_ops(goal: str) -> List[tuple]:
    """Extract one or more (filename, content) pairs from a create/write goal."""
    ops: List[tuple] = []
    seen = set()
    for match in _PAIR_PATTERN.finditer(goal):
        name = match.group(1).strip()
        raw = (match.group(2) or match.group(3) or "").strip()
        raw = re.split(r"\b(?:verify|then|report|and then)\b", raw, maxsplit=1, flags=re.IGNORECASE)[0]
        content = raw.strip(" \t\r\n.,;:")
        if ".." in name or "/" in name or "\\" in name or name in seen:
            continue
        seen.add(name)
        ops.append((name, content))
    if not ops:
        name = extract_filename(goal)
        if name:
            ops.append((name, extract_file_content(goal)))
    return ops


def is_coding_goal(goal: str) -> bool:
    """True when the goal should go to the coding engine rather than file I/O."""
    lower = goal.lower()
    if any(token in lower for token in ("python module", "jcode", "pytest", "unit test", "create test")):
        return True
    if "python" in lower and any(token in lower for token in ("function", "functions", "module", "debug", "fix", "test")):
        return True
    if re.search(r"\b(debug|fix)\b", lower) and re.search(r"\b(python|test|tests|code|implementation)\b", lower):
        return True
    if "function" in lower or "functions" in lower:
        return True
    if re.search(r"\bcode\b", lower) and not re.search(r"\bfiles?\b", lower):
        return True
    return False


def is_file_write_goal(goal: str) -> bool:
    """True when the goal is a workspace file create/write/edit, not a coding or calc task."""
    if is_coding_goal(goal):
        return False
    lower = goal.lower()
    mentions_file = bool(re.search(r"\bfiles?\b", lower))
    write_verb = bool(re.search(r"\b(create|write|save|make|put|edit|replace|update|overwrite)\b", lower))
    has_name = extract_filename(goal) is not None
    return (mentions_file and write_verb) or (has_name and write_verb and mentions_file)


class RuleBasedPlanner:
    """
    Decomposes user goals into versioned structured execution plans (Plan DAG).
    """

    def _extract_expression(self, text: str) -> str:
        """Extracts mathematical expression pattern e.g. '37 * 42' or '12 + 12'."""
        match = re.search(r'(\d+(?:\.\d+)?\s*[\+\-\*/\*\*]+\s*\d+(?:\.\d+)?)', text)
        if match:
            return match.group(1).strip()
        return "37 * 42"

    def create_plan(self, goal: str, plan_id: Optional[str] = None, workspace_dir: Optional[str] = None) -> Plan:
        """
        Decomposes a user goal into a structured Plan graph with dependency relationships.
        """
        pid = plan_id or f"plan-{uuid.uuid4().hex[:8]}"
        tasks: Dict[str, PlanTask] = {}

        strategy: Dict[str, Any] = {}
        try:
            from agent.evolution.generation import load_active_planner_strategy
            strategy = load_active_planner_strategy() or {}
        except Exception:
            strategy = {}
        extra_retries = int((strategy.get("proposed_changes") or {}).get("strategy_patch", {}).get("max_retries") or 2)

        from agent.orchestration.intent import (
            BUILD_PROGRAM,
            CAPABILITY_UNAVAILABLE,
            CHANGE_PROGRAM,
            COMPUTE,
            CONVERSE,
            QUERY_DATA,
            READ_TEXT,
            WRITE_TEXT,
            classify_intent,
        )

        intent = classify_intent(goal, workspace_dir=workspace_dir)
        kind = intent.kind
        slots = intent.slots

        if kind in (BUILD_PROGRAM, CHANGE_PROGRAM):
            t1 = PlanTask(
                id="task_code_1",
                description="Execute coding task with Jcode engine",
                dependencies=[],
                required_tool_id="coding-engine-v1",
                inputs={"goal": goal},
                max_retries=extra_retries,
            )
            tasks[t1.id] = t1

        elif kind == READ_TEXT:
            rel_path = slots.get("filename") or goal.strip()
            t1 = PlanTask(
                id="task_read_1",
                description="Read workspace file",
                dependencies=[],
                required_tool_id="read_file-v1",
                inputs={"relative_path": rel_path},
                max_retries=extra_retries,
            )
            tasks[t1.id] = t1

        elif kind == QUERY_DATA:
            rel_path = slots.get("filename")
            if not rel_path:
                t1 = PlanTask(
                    id="task_unavailable_1",
                    description="Structured data file is required but was not found",
                    dependencies=[],
                    required_tool_id=CAPABILITY_UNAVAILABLE,
                    inputs={"goal": goal},
                    max_retries=0,
                )
                tasks[t1.id] = t1
            else:
                t1 = PlanTask(
                    id="task_inspect_1",
                    description="Inspect structured workspace data",
                    dependencies=[],
                    required_tool_id="inspect_data-v1",
                    inputs={"relative_path": rel_path, "query": slots.get("query") or goal},
                    max_retries=extra_retries,
                )
                tasks[t1.id] = t1

        elif kind == COMPUTE:
            expr = slots.get("expression") or self._extract_expression(goal)
            t1 = PlanTask(
                id="task_calc_1",
                description="Evaluate mathematical calculation",
                dependencies=[],
                required_tool_id="calculator-v1",
                inputs={"expression": expr},
                max_retries=extra_retries,
            )
            tasks[t1.id] = t1
            save_as = slots.get("save_as")
            if save_as:
                t2 = PlanTask(
                    id="task_write_2",
                    description="Write calculation result to workspace file",
                    dependencies=["task_calc_1"],
                    required_tool_id="write_file-v1",
                    inputs={"relative_path": save_as, "content": "$task_calc_1.output"},
                    max_retries=extra_retries,
                )
                tasks[t2.id] = t2

        elif kind == WRITE_TEXT:
            ops = extract_file_write_ops(goal)
            if not ops:
                target_name = slots.get("filename") or "note.txt"
                content = slots.get("content") or extract_file_content(goal)
                ops = [(target_name, content)]
            prev = None
            for index, (target_name, content) in enumerate(ops, start=1):
                tid = f"task_write_{index}"
                t = PlanTask(
                    id=tid,
                    description="Write requested content to a workspace file",
                    dependencies=[prev] if prev else [],
                    required_tool_id="write_file-v1",
                    inputs={"relative_path": target_name, "content": content},
                    max_retries=extra_retries,
                )
                tasks[tid] = t
                prev = tid

        elif kind == CONVERSE:
            t1 = PlanTask(
                id="task_gen_1",
                description=f"Process goal: {goal}",
                dependencies=[],
                required_tool_id=None,
                inputs={"prompt": goal},
            )
            tasks[t1.id] = t1

        else:
            t1 = PlanTask(
                id="task_unavailable_1",
                description="Requested capability is not available",
                dependencies=[],
                required_tool_id=CAPABILITY_UNAVAILABLE,
                inputs={"goal": goal},
                max_retries=0,
            )
            tasks[t1.id] = t1

        return Plan(
            id=pid,
            goal=goal,
            version="plan-v1",
            tasks=tasks,
            status="active",
            metadata={"intent": kind, "intent_confidence": intent.confidence},
        )
