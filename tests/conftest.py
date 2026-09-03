"""Isolate tests from the developer's live data directory."""

from __future__ import annotations

import os
import tempfile

if "AGENT_DATA_DIR" not in os.environ:
    os.environ["AGENT_DATA_DIR"] = tempfile.mkdtemp(prefix="agent-pytest-")
