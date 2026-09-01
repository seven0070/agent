"""
Basic File Management Skill Implementation.
Composes file inspection, creation, and verification workflows.
"""

from typing import Dict, Any
from agent.capabilities.spec import SkillSpec
from agent.capabilities.broker import CapabilityBroker
from agent.capabilities.models import CapabilityResult

class BasicFileManagementSkill:
    """
    Skill composing write_file and read_file operations to safely create and verify files.
    """

    def __init__(self, broker: CapabilityBroker) -> None:
        self.broker = broker
        self.spec = SkillSpec(
            id="file-management-skill-v1",
            name="Basic File Management",
            description="Composes workspace file creation, reading, and post-write verification",
            tool_ids=["read_file-v1", "write_file-v1"],
        )

    def create_and_verify_file(self, relative_path: str, content: str) -> CapabilityResult:
        """
        Executes composed workflow: writes file content, then reads and verifies content match.
        """
        # Step 1: Write File
        write_res = self.broker.execute_tool("write_file-v1", {"relative_path": relative_path, "content": content})
        if not write_res.success:
            return write_res

        # Step 2: Read File for Verification
        read_res = self.broker.execute_tool("read_file-v1", {"relative_path": relative_path})
        if not read_res.success:
            return read_res

        # Step 3: Verify Content Match
        if read_res.output == content:
            return CapabilityResult(
                tool_id=self.spec.id,
                success=True,
                output=f"Skill '{self.spec.id}': File '{relative_path}' created and verified successfully.",
                metadata={"file_size": len(content), "verified": True},
            )
        else:
            return CapabilityResult(
                tool_id=self.spec.id,
                success=False,
                error=f"Skill '{self.spec.id}': Content verification failed for '{relative_path}'.",
            )
