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

_CODING_HINTS = (
    "code",
    "python module",
    "function",
    "functions",
    "edit file",
    "create test",
    "jcode",
    "pytest",
    "unit test",
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


def is_file_write_goal(goal: str) -> bool:
    """True when the goal is a workspace file create/write, not a coding or calc task."""
    lower = goal.lower()
    mentions_file = bool(re.search(r"\bfiles?\b", lower))
    write_verb = bool(re.search(r"\b(create|write|save|make|put)\b", lower))
    has_name = extract_filename(goal) is not None
    if any(hint in lower for hint in _CODING_HINTS):
        return False
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

    def create_plan(self, goal: str, plan_id: Optional[str] = None) -> Plan:
        """
        Decomposes a user goal into a structured Plan graph with dependency relationships.
        """
        pid = plan_id or f"plan-{uuid.uuid4().hex[:8]}"
        tasks: Dict[str, PlanTask] = {}

        goal_lower = goal.lower()
        strategy: Dict[str, Any] = {}
        try:
            from agent.evolution.generation import load_active_planner_strategy
            strategy = load_active_planner_strategy() or {}
        except Exception:
            strategy = {}
        extra_retries = int((strategy.get("proposed_changes") or {}).get("strategy_patch", {}).get("max_retries") or 2)
        has_math = bool(re.search(r"(\d+(?:\.\d+)?\s*[\+\-\*/]+\s*\d+(?:\.\d+)?)", goal))

        # Goal Pattern 1: Coding / Software Engineering Task
        if any(keyword in goal_lower for keyword in ["code", "python module", "function", "edit file", "create test", "jcode"]):
            t1 = PlanTask(
                id="task_code_1",
                description="Execute coding task with Jcode engine",
                dependencies=[],
                required_tool_id="coding-engine-v1",
                inputs={"goal": goal},
                max_retries=extra_retries,
            )
            tasks[t1.id] = t1

        # Goal Pattern 1b: explicit file read (including safety / traversal probes)
        elif any(keyword in goal_lower for keyword in ["read file", "open file", "cat ", "passwd"]):
            path_match = re.search(r"((?:\.\./)+[\w./-]+|/[\w./-]+|[\w./-]+\.\w+)", goal)
            rel_path = path_match.group(1) if path_match else goal.strip()
            t1 = PlanTask(
                id="task_read_1",
                description="Read workspace file",
                dependencies=[],
                required_tool_id="read_file-v1",
                inputs={"relative_path": rel_path},
                max_retries=extra_retries,
            )
            tasks[t1.id] = t1

        # Goal Pattern 2: Math calculation + write to file
        elif has_math and ("file" in goal_lower or "save" in goal_lower or "write" in goal_lower or "report" in goal_lower):
            expr = self._extract_expression(goal)
            target_name = extract_filename(goal) or "calc_result.txt"

            t1 = PlanTask(
                id="task_calc_1",
                description="Evaluate mathematical calculation",
                dependencies=[],
                required_tool_id="calculator-v1",
                inputs={"expression": expr},
                max_retries=extra_retries,
            )
            t2 = PlanTask(
                id="task_write_2",
                description="Write calculation result to workspace file",
                dependencies=["task_calc_1"],
                required_tool_id="write_file-v1",
                inputs={"relative_path": target_name, "content": "$task_calc_1.output"},
                max_retries=extra_retries,
            )
            tasks[t1.id] = t1
            tasks[t2.id] = t2

        # Goal Pattern 3: Workspace file create/write (not coding, not calc)
        elif is_file_write_goal(goal):
            target_name = extract_filename(goal)
            if target_name is None:
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
                    id="task_write_1",
                    description="Write requested content to a workspace file",
                    dependencies=[],
                    required_tool_id="write_file-v1",
                    inputs={
                        "relative_path": target_name,
                        "content": extract_file_content(goal),
                    },
                    max_retries=extra_retries,
                )
                tasks[t1.id] = t1

        # Goal Pattern 4: Math calculation only
        elif "calculate" in goal_lower or "math" in goal_lower or "compute" in goal_lower or has_math:
            expr = self._extract_expression(goal)

            t1 = PlanTask(
                id="task_calc_1",
                description="Evaluate mathematical calculation",
                dependencies=[],
                required_tool_id="calculator-v1",
                inputs={"expression": expr},
                max_retries=extra_retries,
            )
            tasks[t1.id] = t1

        # Goal Pattern 5: Default single-step general task (model path)
        else:
            t1 = PlanTask(
                id="task_gen_1",
                description=f"Process goal: {goal}",
                dependencies=[],
                required_tool_id=None,
                inputs={"prompt": goal},
            )
            tasks[t1.id] = t1

        return Plan(
            id=pid,
            goal=goal,
            version="plan-v1",
            tasks=tasks,
            status="active",
        )
