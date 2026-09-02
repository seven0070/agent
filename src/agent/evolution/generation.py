"""
Versioned generation artifact store.

Promoted evolution candidates become generations under data/generations/<version>/.
The active Agent reads these artifacts; the Evolution Controller never mutates src/.
"""

from __future__ import annotations

import json
import os
import shutil
from typing import Any, Dict, Optional

from agent.config import get_settings
from agent.logging import get_logger

logger = get_logger("agent.evolution.generation")

GENERATION_ENV = "AGENT_GENERATION_DIR"
ACTIVE_POINTER_FILE = "ACTIVE_GENERATION"


def generations_root(data_dir: Optional[str] = None) -> str:
    root = os.path.join(data_dir or get_settings().data_dir, "generations")
    os.makedirs(root, exist_ok=True)
    return root


def generation_path(version: str, data_dir: Optional[str] = None) -> str:
    path = os.path.join(generations_root(data_dir), version)
    os.makedirs(path, exist_ok=True)
    return path


def get_active_generation_dir(data_dir: Optional[str] = None, version: Optional[str] = None) -> Optional[str]:
    env_dir = os.environ.get(GENERATION_ENV)
    if env_dir and os.path.isdir(env_dir):
        return os.path.realpath(env_dir)
    if version:
        path = generation_path(version, data_dir)
        return path if os.path.isdir(path) else None
    pointer = os.path.join(generations_root(data_dir), ACTIVE_POINTER_FILE)
    if os.path.isfile(pointer):
        with open(pointer, "r", encoding="utf-8") as handle:
            active = handle.read().strip()
        if active:
            path = os.path.join(generations_root(data_dir), active)
            if os.path.isdir(path):
                return path
    return None


def set_active_generation_dir(version: str, data_dir: Optional[str] = None) -> None:
    pointer = os.path.join(generations_root(data_dir), ACTIVE_POINTER_FILE)
    with open(pointer, "w", encoding="utf-8") as handle:
        handle.write(version)


def load_artifact(target: str, data_dir: Optional[str] = None, version: Optional[str] = None) -> Dict[str, Any]:
    gen_dir = get_active_generation_dir(data_dir=data_dir, version=version)
    if not gen_dir:
        return {}
    artifact = os.path.join(gen_dir, f"{target}.json")
    if not os.path.isfile(artifact):
        return {}
    with open(artifact, "r", encoding="utf-8") as handle:
        return json.load(handle)


def load_active_planner_strategy() -> Dict[str, Any]:
    return load_artifact("planner_strategy")


def promote_candidate_artifacts(candidate_dir: str, version: str, data_dir: Optional[str] = None) -> str:
    dest = generation_path(version, data_dir)
    artifacts_src = os.path.join(candidate_dir, "artifacts")
    if os.path.isdir(artifacts_src):
        for name in os.listdir(artifacts_src):
            src = os.path.join(artifacts_src, name)
            if os.path.isfile(src):
                shutil.copy2(src, os.path.join(dest, name))
    set_active_generation_dir(version, data_dir)
    logger.info(f"Promoted candidate artifacts from '{candidate_dir}' to generation '{version}'")
    return dest


def rollback_generation(parent_version: str, data_dir: Optional[str] = None) -> str:
    dest = generation_path(parent_version, data_dir)
    set_active_generation_dir(parent_version, data_dir)
    logger.info(f"Rolled generation pointer back to '{parent_version}'")
    return dest
