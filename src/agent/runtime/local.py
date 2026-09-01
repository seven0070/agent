"""
Local AgentScope Runtime Implementation managing LocalWorkspace containers.
"""

import os
import uuid
import asyncio
from typing import Dict, Optional, Any
from agentscope.workspace import LocalWorkspace
from agent.runtime.models import RuntimeSession, RuntimeStatus, NetworkPolicy
from agent.runtime.policy import ResourceLimits
from agent.runtime.sandbox import RuntimeSandbox
from agent.logging import get_logger

logger = get_logger("agent.runtime.local")

class LocalAgentScopeRuntime:
    """
    Local runtime managing AgentScope LocalWorkspace containers and sandboxed execution sessions.
    """

    def __init__(self, base_workspace_dir: str = "data/workspace") -> None:
        self.base_workspace_dir = os.path.abspath(base_workspace_dir)
        os.makedirs(self.base_workspace_dir, exist_ok=True)
        self.sessions: Dict[str, RuntimeSession] = {}
        self.sandboxes: Dict[str, RuntimeSandbox] = {}
        self.agent_workspaces: Dict[str, LocalWorkspace] = {}

    def create_session(
        self,
        session_id: Optional[str] = None,
        network_policy: NetworkPolicy = NetworkPolicy.DENY,
        limits: Optional[ResourceLimits] = None,
    ) -> RuntimeSession:
        """
        Creates and initializes a new sandboxed runtime session with AgentScope LocalWorkspace.
        """
        sid = session_id or f"sess-{uuid.uuid4().hex[:8]}"
        ws_id = f"ws-{sid}"
        ws_dir = os.path.join(self.base_workspace_dir, sid)
        os.makedirs(ws_dir, exist_ok=True)

        session = RuntimeSession(
            session_id=sid,
            workspace_id=ws_id,
            workspace_dir=ws_dir,
            status=RuntimeStatus.INITIALIZED,
            network_policy=network_policy,
            limits=limits or ResourceLimits(),
        )

        sandbox = RuntimeSandbox(session=session)
        agent_ws = LocalWorkspace(workdir=ws_dir, workspace_id=ws_id)

        self.sessions[sid] = session
        self.sandboxes[sid] = sandbox
        self.agent_workspaces[sid] = agent_ws

        sandbox._emit_event("SANDBOX_CREATED", "session_create", "initialized")
        logger.info(f"Created LocalAgentScopeRuntime session '{sid}' in workspace '{ws_dir}'")
        return session

    def get_sandbox(self, session_id: str) -> Optional[RuntimeSandbox]:
        """Retrieves active RuntimeSandbox for a session ID."""
        return self.sandboxes.get(session_id)

    async def close_session_async(self, session_id: str) -> bool:
        """
        Asynchronously closes and cleans up a runtime session.
        """
        if session_id in self.sessions:
            session = self.sessions[session_id]
            sandbox = self.sandboxes.get(session_id)
            agent_ws = self.agent_workspaces.get(session_id)

            if agent_ws:
                await agent_ws.close()

            if sandbox:
                sandbox._emit_event("SESSION_CLOSED", "session_close", "closed")

            session.status = RuntimeStatus.CLOSED
            logger.info(f"Closed Runtime session '{session_id}'")
            return True
        return False

    def close_session(self, session_id: str) -> bool:
        """
        Closes and cleans up a runtime session synchronously or via event loop.
        """
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(self.close_session_async(session_id))
            return True
        except RuntimeError:
            return asyncio.run(self.close_session_async(session_id))

    def cleanup_all(self) -> None:
        """Closes all active sessions and releases workspace handles."""
        for sid in list(self.sessions.keys()):
            self.close_session(sid)
