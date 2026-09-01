"""
Coding Workspace Root Enforcement and Path Traversal Security Restrictor.
"""

import os

class CodingWorkspaceRestrictor:
    """
    Ensures all file reads, writes, edits, and test commands occur strictly within the assigned workspace directory.
    """

    def __init__(self, workspace_dir: str = "data/workspace") -> None:
        self.workspace_dir = os.path.abspath(workspace_dir)
        os.makedirs(self.workspace_dir, exist_ok=True)

    def validate_and_resolve(self, relative_path: str) -> str:
        """
        Resolves a relative path and verifies it resides within the approved workspace.
        Raises PermissionError if path traversal is detected.
        """
        clean_path = relative_path.lstrip("/\\")
        target_path = os.path.abspath(os.path.join(self.workspace_dir, clean_path))

        try:
            common = os.path.commonpath([self.workspace_dir, target_path])
        except ValueError:
            raise PermissionError(f"Access Denied: Path '{relative_path}' escapes coding workspace root.")

        if common != self.workspace_dir:
            raise PermissionError(f"Access Denied: Path '{relative_path}' escapes coding workspace root.")

        return target_path
