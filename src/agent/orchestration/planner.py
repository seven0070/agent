"""
Planner Interface and Dynamic Plan Decomposer.
"""

import uuid
import re
from typing import Dict, Any, Optional, List
from agent.orchestration.models import Plan, PlanTask

_FILENAME_TOKEN = r"[A-Za-z0-9][A-Za-z0-9._-]*\.[A-Za-z0-9]+"

_FILENAME_PATTERNS = (
    rf"(?:named|called)\s+[\"']?({_FILENAME_TOKEN})[\"']?",
    rf"(?:file(?:name)?)\s+[\"']?({_FILENAME_TOKEN})[\"']?",
    rf"(?:save|write|output)\s+(?:(?:it|the\s+answer|the\s+result)\s+)?(?:to|into|in)\s+[\"']?({_FILENAME_TOKEN})[\"']?",
    rf"[\"']({_FILENAME_TOKEN})[\"']",
)

_CONTENT_PATTERNS = (
    r"containing(?:\s+the)?(?:\s+text)?\s+[\"'](.+?)[\"']",
    r"containing(?:\s+the)?(?:\s+text)?\s+(.+?)(?:\.(?:\s|$)|$)",
    r"with(?:\s+the)?(?:\s+(?:text|content|contents))\s+[\"'](.+?)[\"']",
    r"with(?:\s+the)?(?:\s+(?:text|content|contents))\s+(.+?)(?:\.(?:\s|$)|$)",
    r"that says\s+[\"'](.+?)[\"']",
    r"that says\s+(.+?)(?:\.(?:\s|$)|$)",
    r"to say\s+[\"'](.+?)[\"']",
    r"to say\s+(.+?)(?:\.(?:\s|$)|$)",
)

_PAIR_PATTERN = re.compile(
    rf"(?:(?:a\s+)?file\s+(?:named|called)\s+)?({_FILENAME_TOKEN})\s+containing(?:\s+the)?(?:\s+text)?\s+(?:[\"'](.+?)[\"']|(.+?))(?=\s+and\s+(?:a\s+)?file\b|\s+and\s+(?:create|write|named)\b|\s+and\s+{_FILENAME_TOKEN}|$)",
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


def last_result_text(raw: str) -> str:
    """Pick a follow-up write payload from a prior agent turn."""
    text = (raw or "").strip()
    if not text:
        return ""
    lines = [
        line.strip()
        for line in text.splitlines()
        if line.strip() and not line.strip().lower().startswith("file '")
    ]
    return lines[-1] if lines else text


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

    def create_plan(
        self,
        goal: str,
        plan_id: Optional[str] = None,
        workspace_dir: Optional[str] = None,
        session_hints: Optional[Dict[str, Any]] = None,
    ) -> Plan:
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

        from agent.orchestration.decompose import assign_ids_and_placeholders, compose_operations
        from agent.orchestration.intent import classify_intent

        intent = classify_intent(goal, workspace_dir=workspace_dir)
        ops = assign_ids_and_placeholders(compose_operations(goal, workspace_dir=workspace_dir))
        if session_hints and session_hints.get("last_output"):
            prior = last_result_text(str(session_hints.get("last_output") or ""))
            for op in ops:
                content = str(op.inputs.get("content") or "")
                if op.kind == "write" and not content.strip() and "$" not in content:
                    op.inputs["content"] = prior

        prev_id = None
        for op in ops:
            deps: List[str] = []
            for value in op.inputs.values():
                if isinstance(value, str):
                    for match in re.finditer(r"\$([A-Za-z0-9_]+)\.output", value):
                        dep = match.group(1)
                        if dep not in deps:
                            deps.append(dep)
            if not deps and prev_id and op.kind == "write":
                deps = [prev_id]
            tasks[op.id] = PlanTask(
                id=op.id,
                description=op.description,
                dependencies=deps,
                required_tool_id=op.tool_id,
                inputs=dict(op.inputs),
                max_retries=0 if op.kind == "unavailable" else extra_retries,
            )
            prev_id = op.id

        return Plan(
            id=pid,
            goal=goal,
            version="plan-v1",
            tasks=tasks,
            status="active",
            metadata={
                "intent": intent.kind,
                "intent_confidence": intent.confidence,
                "op_count": len(ops),
            },
        )
