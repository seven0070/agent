"""
Standalone PyInstaller Entrypoint for Agent Desktop Backend Process.
Allows PyInstaller / cx_Freeze to package the Agent FastAPI service into a self-contained executable.
"""

import sys
import argparse
import os
import uvicorn
from agent.config import get_settings
from agent.logging import get_logger

logger = get_logger("agent.backend.standalone")

def main():
    parser = argparse.ArgumentParser(description="Agent Standalone Desktop Backend Executable")
    parser.add_argument("--port", type=int, default=8000, help="Port to bind (default: 8000)")
    parser.add_argument("--host", type=str, default="127.0.0.1", help="Host address (default: 127.0.0.1)")
    args = parser.parse_args()

    settings = get_settings()
    host = "127.0.0.1"  # Enforce localhost security boundary
    port = args.port

    logger.info(f"Starting Standalone Agent Backend Executable v{settings.agent_version} on http://{host}:{port} (Data Dir: {settings.data_dir})")

    # Import app inside entrypoint to ensure PyInstaller bundle imports initialize properly
    from agent.api.app import app

    uvicorn.run(
        app,
        host=host,
        port=port,
        log_level=settings.log_level.lower(),
        reload=False,
    )

if __name__ == "__main__":
    main()
