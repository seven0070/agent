"""
Abstract Coding Engine Interface Contract.
"""

from abc import ABC, abstractmethod
from agent.coding.models import CodingTask, CodingResult

class CodingEngineInterface(ABC):
    """
    Abstract interface decoupling Main Agent from Jcode engine implementation.
    """

    @abstractmethod
    def execute_coding_task(self, task: CodingTask) -> CodingResult:
        """Executes a coding task and returns a structured CodingResult."""
        pass
