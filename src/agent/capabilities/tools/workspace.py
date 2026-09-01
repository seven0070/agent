"""
Workspace-Restricted File I/O Tools with Path Traversal Prevention.
"""

import os
from typing import Optional

class WorkspaceManager:
    """
    Manages workspace directory boundaries and enforces path traversal prevention.
    """

    def __init__(self, workspace_dir: str = "data/workspace") -> None:
        self.workspace_dir = os.path.abspath(workspace_dir)
        os.makedirs(self.workspace_dir, exist_ok=True)

    def resolve_path(self, relative_path: str) -> str:
        """
        Resolves a relative file path inside the workspace directory.
        Raises PermissionError if path traversal outside workspace is attempted.
        """
        # Remove leading slashes to prevent absolute path override
        clean_path = relative_path.lstrip("/\\")
        target_path = os.path.abspath(os.path.join(self.workspace_dir, clean_path))

        # Commonpath check ensuring target_path resides within workspace_dir
        try:
            common = os.path.commonpath([self.workspace_dir, target_path])
        except ValueError:
            raise PermissionError(f"Access Denied: Path '{relative_path}' traverses outside workspace boundary.")

        if common != self.workspace_dir:
            raise PermissionError(f"Access Denied: Path '{relative_path}' traverses outside workspace boundary.")

        return target_path

    def read_file(self, relative_path: str) -> str:
        """Reads content from a workspace file."""
        target_path = self.resolve_path(relative_path)
        if not os.path.exists(target_path):
            raise FileNotFoundError(f"File '{relative_path}' not found in workspace.")
        with open(target_path, "r", encoding="utf-8") as f:
            return f.read()

    def write_file(self, relative_path: str, content: str) -> str:
        """Writes content to a workspace file."""
        target_path = self.resolve_path(relative_path)
        os.makedirs(os.path.dirname(target_path), exist_ok=True)
        with open(target_path, "w", encoding="utf-8") as f:
            f.write(content)
        return f"File '{relative_path}' successfully written to workspace."
