"""
Resource Limits Policy Configuration.
"""

from pydantic import BaseModel, Field

class ResourceLimits(BaseModel):
    """
    Process and execution resource limits.
    """
    timeout_seconds: float = Field(default=10.0, description="Process execution timeout limit in seconds")
    max_memory_mb: int = Field(default=512, description="Maximum memory allocation limit in MB")
    max_output_bytes: int = Field(default=1048576, description="Maximum output buffer limit in bytes (1MB)")
    max_processes: int = Field(default=5, description="Maximum concurrent process limit")
