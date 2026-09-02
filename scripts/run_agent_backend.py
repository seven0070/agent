"""
Standalone Desktop Agent Backend Launcher Script.
Launches the FastAPI backend server on localhost for desktop shell execution.
"""

import sys
import uvicorn
from agent.config import get_settings
from agent.logging import get_logger

logger = get_logger("agent.backend.launcher")

def main():
    settings = get_settings()
    logger.info(f"Starting Agent Backend Server v{settings.agent_version} on http://127.0.0.1:8000 (Data Dir: {settings.data_dir})")
    uvicorn.run(
        "agent.api.app:app",
        host="127.0.0.1",
        port=8000,
        log_level=settings.log_level.lower(),
        reload=False,
    )

if __name__ == "__main__":
    main()
