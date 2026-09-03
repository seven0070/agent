"""Outcome-based task intent classification for Layer 5 planning.

This is not a new architecture layer. It maps the user's requested outcome
onto capabilities the agent actually has, instead of requiring cue words
such as "file", "code", or "calculate".
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


WRITE_TEXT = "write_text"
READ_TEXT = "read_text"
READ_THEN_WRITE = "read_then_write"
COMPUTE = "compute"
BUILD_PROGRAM = "build_program"
CHANGE_PROGRAM = "change_program"
QUERY_DATA = "query_data"
CONVERSE = "converse"
UNSUPPORTED = "unsupported"

CAPABILITY_UNAVAILABLE = "capability-unavailable"

# Hyphen glued to digits (ticket-14-1788, 3-4pm) is not subtraction. Require
# spaces around '-' or a non-hyphen operator.
_ARITH_TOKEN = (
    r"(\d+(?:\.\d+)?\s*[\+\*/]\s*\d+(?:\.\d+)?|"
    r"\d+(?:\.\d+)?\s+-\s+\d+(?:\.\d+)?)"
)
_FILENAME = r"[A-Za-z0-9][A-Za-z0-9._-]*\.[A-Za-z0-9]+"
_WORK_HINT = re.compile(
    r"\b(email|e-mail|send|download|install|deploy|browse|tweet|slack|sms|purchase|buy|pay|"
    r"delete|remove|erase|wipe|upload|summarize|translate|search the web|google)\b",
    flags=re.IGNORECASE,
)


@dataclass
class Intent:
    kind: str
    confidence: float
    slots: Dict[str, Any] = field(default_factory=dict)


def _workspace_names(workspace_dir: Optional[str]) -> List[str]:
    if not workspace_dir or not os.path.isdir(workspace_dir):
        return []
    names: List[str] = []
    for root, _, files in os.walk(workspace_dir):
        for name in files:
            names.append(name)
    return names


def _safe_filename(name: Optional[str]) -> Optional[str]:
    if not name:
        return None
    if ".." in name or "/" in name or "\\" in name:
        return None
    return name


def _extract_spoken_content(goal: str) -> str:
    patterns = (
        r"(?:saying|that says|that reads)\s+(.+)$",
        r"to say\s+(.+)$",
        r"remind me(?:\s+to)?\s+(.+)$",
        r"(?:note|reminder|memo|message)\s+(?:on\s+\S+\s+)?(?:that\s+|to\s+)?(.+)$",
        r"jot down\s+(?:that\s+)?(.+)$",
        r"[\"'](.+?)[\"']",
    )
    for pattern in patterns:
        match = re.search(pattern, goal, flags=re.IGNORECASE | re.DOTALL)
        if match:
            text = match.group(1).strip()
            text = re.split(r"\b(?:verify|then|report)\b", text, maxsplit=1, flags=re.IGNORECASE)[0]
            return text.strip(" \t\r\n.,;:")
    return ""


def _artifact_filename(goal: str) -> str:
    lower = goal.lower()
    if "remind" in lower or "reminder" in lower:
        return "reminder.txt"
    if "memo" in lower:
        return "memo.txt"
    if "message" in lower:
        return "message.txt"
    return "note.txt"


def _spoken_math(goal: str) -> Optional[str]:
    match = re.search(_ARITH_TOKEN, goal)
    if match:
        return match.group(1).strip()
    spoken = re.sub(r"\b(times|multiplied by)\b", "*", goal, flags=re.IGNORECASE)
    spoken = re.sub(r"\b(plus|added to)\b", "+", spoken, flags=re.IGNORECASE)
    spoken = re.sub(r"\b(minus|subtracted from|less)\b", "-", spoken, flags=re.IGNORECASE)
    spoken = re.sub(r"\b(divided by|over)\b", "/", spoken, flags=re.IGNORECASE)
    match = re.search(_ARITH_TOKEN, spoken)
    if match:
        return match.group(1).strip()
    return None


def _software_outcome(lower: str, names: List[str]) -> bool:
    if re.search(r"\b(python module|jcode|pytest|unit test)\b", lower):
        return True
    if "python" in lower and re.search(r"\b(function|functions|module|test|tests)\b", lower):
        return True
    if re.search(r"\b(debug|fix|repair|failing)\b", lower) and re.search(
        r"\b(python|test|tests|implementation|code)\b", lower
    ):
        return True
    if re.search(r"\b(program|script|software|project)\b", lower):
        return True
    if re.search(r"\b(python|code)\b", lower) and re.search(r"\bpackage\b", lower):
        return True
    if re.search(r"\bfunctions?\b", lower):
        return True
    has_py = any(n.lower().endswith(".py") for n in names)
    if has_py and re.search(r"\b(change|update|edit|replace|greeting|repair)\b", lower):
        return True
    if re.search(r"\bconvert(?:s|ing)?\b", lower) and re.search(
        r"\b(program|script|python|function|celsius|fahrenheit|kilometer|mile|pound|kg)\b", lower
    ):
        return True
    if re.search(r"\b(larger|smaller|greater|lesser) of\b", lower):
        return True
    return False


def _change_existing_software(lower: str, names: List[str]) -> bool:
    has_py = any(n.lower().endswith(".py") for n in names)
    if re.search(r"\b(debug|fix|repair|failing|broken)\b", lower):
        return True
    if has_py and re.search(r"\b(change|update|edit|replace|greeting|existing)\b", lower):
        return True
    return False


def _data_query_outcome(lower: str, names: List[str]) -> bool:
    has_data = any(n.lower().endswith(".json") or n.lower().endswith(".csv") for n in names)
    mentions_data = bool(re.search(r"\b(json|csv)\b", lower)) or has_data
    aggregating = bool(
        re.search(
            r"\b(highest|lowest|which|who has|max|min|largest|smallest|average|mean|"
            r"how many|count|total|sum|summarize|summary)\b",
            lower,
        )
    )
    return mentions_data and aggregating


def _persist_outcome(lower: str, filename_in_goal: bool) -> bool:
    if re.search(r"\bjot down\b", lower) or re.search(r"\bremind me\b", lower):
        return True
    write_verb = bool(
        re.search(
            r"\b(put|leave|jot|drop|save|pin|write|create|make|edit|replace|update|overwrite|change)\b",
            lower,
        )
    )
    artifact = bool(re.search(r"\b(note|reminder|memo|message)\b", lower))
    mentions_file = bool(re.search(r"\bfiles?\b", lower))
    if not write_verb:
        return False
    return artifact or filename_in_goal or mentions_file


def _read_outcome(lower: str, filename_in_goal: bool, names: List[str]) -> bool:
    look = bool(re.search(r"\b(what'?s in|what's inside|look at|show me|open|read)\b", lower))
    if re.search(r"\b(read file|open file|cat )\b", lower):
        return True
    if look and (filename_in_goal or names):
        return True
    return False


def _converse_outcome(lower: str) -> bool:
    return bool(re.search(r"\b(hello|hi |hey|thanks|thank you|explain)\b", lower))


def _first_data_file(names: List[str]) -> Optional[str]:
    for name in names:
        lower = name.lower()
        if lower.endswith(".json") or lower.endswith(".csv"):
            return os.path.basename(name)
    return None


def _explicit_calculation(lower: str) -> bool:
    return bool(
        re.search(
            r"\b(calculate|what is|what's|whats|how much is|times|multiplied|divided by|plus|minus)\b",
            lower,
        )
    )


def _read_then_write_pair(goal: str, lower: str) -> Optional[tuple]:
    files = re.findall(_FILENAME, goal)
    unique = []
    for name in files:
        if name not in unique:
            unique.append(name)
    if len(unique) < 2:
        return None
    if not re.search(r"\b(read|look at|open|what's in|whats in|what's inside)\b", lower):
        return None
    if not re.search(r"\b(write|save|put|copy)\b", lower):
        return None
    return unique[0], unique[-1]


def classify_intent(goal: str, workspace_dir: Optional[str] = None) -> Intent:
    """Map the user's requested outcome onto an implemented capability."""
    text = goal.strip()
    lower = text.lower()
    names = _workspace_names(workspace_dir)
    math = _spoken_math(text)
    filename_match = re.search(_FILENAME, text)
    filename_in_goal = filename_match is not None
    software = _software_outcome(lower, names)

    from agent.orchestration.planner import extract_file_content, extract_filename

    pair = _read_then_write_pair(text, lower)
    if pair:
        return Intent(
            kind=READ_THEN_WRITE,
            confidence=3.0,
            slots={"source": pair[0], "dest": pair[1]},
        )

    persist = _persist_outcome(lower, filename_in_goal)
    if math and not software and not (persist and not _explicit_calculation(lower)):
        slots: Dict[str, Any] = {"expression": math}
        save_name = _safe_filename(extract_filename(text))
        if save_name or re.search(r"\b(save|write|report)\b", lower):
            slots["save_as"] = save_name or "calc_result.txt"
        return Intent(kind=COMPUTE, confidence=3.0, slots=slots)

    if software:
        kind = CHANGE_PROGRAM if _change_existing_software(lower, names) else BUILD_PROGRAM
        return Intent(
            kind=kind,
            confidence=3.0,
            slots={
                "goal": text,
                "project": bool(re.search(r"\b(project|package|multi-file|multiple files)\b", lower)),
            },
        )

    if _data_query_outcome(lower, names):
        named = _safe_filename(filename_match.group(0) if filename_match else None)
        return Intent(
            kind=QUERY_DATA,
            confidence=3.0,
            slots={"filename": named or _first_data_file(names), "query": text},
        )

    if persist:
        named = _safe_filename(extract_filename(text)) or (
            _safe_filename(filename_match.group(0)) if filename_match else None
        )
        content = extract_file_content(text) or _extract_spoken_content(text)
        return Intent(
            kind=WRITE_TEXT,
            confidence=3.0,
            slots={"filename": named or _artifact_filename(text), "content": content},
        )

    if _read_outcome(lower, filename_in_goal, names):
        named = _safe_filename(filename_match.group(0) if filename_match else None)
        if named is None:
            path_match = re.search(r"((?:\.\./)+[\w./-]+|/[\w./-]+|[\w./-]+\.\w+)", text)
            named = path_match.group(1) if path_match else (text.strip() or None)
        return Intent(kind=READ_TEXT, confidence=3.0, slots={"filename": named})

    if _converse_outcome(lower) and not _WORK_HINT.search(lower):
        return Intent(kind=CONVERSE, confidence=2.0, slots={})

    if _WORK_HINT.search(lower):
        return Intent(kind=UNSUPPORTED, confidence=2.0, slots={"goal": text})

    return Intent(kind=CONVERSE, confidence=0.5, slots={})
