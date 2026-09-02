"""
Standalone Desktop Agent Backend Launcher Script.
Launches the FastAPI backend server on localhost for desktop shell execution with health wait contract.
"""

import sys
import time
import urllib.request
import uvicorn
from agent.config import get_settings
from agent.logging import get_logger

logger = get_logger("agent.backend.launcher")

def wait_for_health(host: str = "127.0.0.1", port: int = 8000, timeout_seconds: int = 15) -> bool:
    """Waits for backend server health endpoint to respond on localhost."""
    url = f"http://{host}:{port}/health"
    start = time.time()
    while time.time() - start < timeout_seconds:
        try:
            with urllib.request.urlopen(url, timeout=2) as response:
                if response.status == 200:
                    logger.info(f"Agent backend health check succeeded on {url}")
                    return True
        except Exception:
            time.sleep(0.2)
    logger.error(f"Agent backend health check timed out on {url}")
    return False

def main():
    settings = get_settings()
    host = "127.0.0.1"
    port = 8000

    logger.info(f"Starting Agent Backend Server v{settings.agent_version} on http://{host}:{port} (Data Dir: {settings.data_dir})")

    uvicorn.run(
        "agent.api.app:app",
        host=host,
        port=port,
        log_level=settings.log_level.lower(),
        reload=False,
    )

if __name__ == "__main__":
    main()
