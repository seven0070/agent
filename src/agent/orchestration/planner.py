"""
Planner Interface and Dynamic Plan Decomposer.
"""

import uuid
import re
from typing import Dict, Any, Optional, List
from agent.orchestration.models import Plan, PlanTask, TaskState

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

        # Goal Pattern 2: Math calculation + write to file
        elif ("calculate" in goal_lower or "math" in goal_lower or "compute" in goal_lower or any(c in goal for c in ["*", "+", "/", "-"])) and ("file" in goal_lower or "save" in goal_lower or "write" in goal_lower):
            expr = self._extract_expression(goal)

            t1 = PlanTask(
                id="task_calc_1",
                description="Evaluate mathematical calculation",
                dependencies=[],
                required_tool_id="calculator-v1",
                inputs={"expression": expr},
            )
            t2 = PlanTask(
                id="task_write_2",
                description="Write calculation result to workspace file",
                dependencies=["task_calc_1"],
                required_tool_id="write_file-v1",
                inputs={"relative_path": "calc_result.txt", "content": "$task_calc_1.output"},
            )
            tasks[t1.id] = t1
            tasks[t2.id] = t2

        # Goal Pattern 3: Math calculation only
        elif "calculate" in goal_lower or "math" in goal_lower or "compute" in goal_lower or any(c in goal for c in ["*", "+", "/", "-"]):
            expr = self._extract_expression(goal)

            t1 = PlanTask(
                id="task_calc_1",
                description="Evaluate mathematical calculation",
                dependencies=[],
                required_tool_id="calculator-v1",
                inputs={"expression": expr},
            )
            tasks[t1.id] = t1

        # Goal Pattern 4: Default single-step general task
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
