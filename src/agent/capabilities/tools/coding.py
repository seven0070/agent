"""
Coding Engine Tool Wrapper for Layer 4 CapabilityBroker Integration.
"""

from typing import Dict, Any, Optional
from agent.coding.models import CodingTask, CodingResult

class CodingEngineToolWrapper:
    """
    Wraps JcodeAdapter as a versioned tool ('coding-engine-v1') executable via CapabilityBroker.
    """

    def __init__(self, adapter: Optional[Any] = None) -> None:
        self._adapter = adapter

    @property
    def adapter(self) -> Any:
        if self._adapter is None:
            from agent.coding.jcode.adapter import JcodeAdapter
            self._adapter = JcodeAdapter()
        return self._adapter

    def execute(self, kwargs: Dict[str, Any]) -> CodingResult:
        """Executes coding task through JcodeAdapter."""
        task_id = kwargs.get("task_id", "coding-task-auto")
        goal = kwargs.get("goal", kwargs.get("prompt", "Create python module"))
        workspace_dir = kwargs.get("workspace_dir", self.adapter.workspace_restrictor.workspace_dir)
        test_command = kwargs.get("test_command", "pytest")

        task = CodingTask(
            task_id=task_id,
            goal=goal,
            workspace_dir=workspace_dir,
            test_command=test_command,
        )
        return self.adapter.execute_coding_task(task)
